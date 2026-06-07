import time
import asyncio
import threading
import queue
import pyaudio
import numpy as np
from google import genai
from google.genai import errors

from core.config import STATE_IDLE, STATE_LISTENING, STATE_PROCESSING, STATE_SPEAKING, CHUNK_SIZE
from core.audio import (
    mic_callback, speaker_callback, mic_queue, oww_model,
    run_live_vad_session, synthesize_speech, play_audio_sync, play_audio_with_interruption, init_audio_models
)
from core.llm import init_llm_client, send_message_with_retry
import core.llm as llm
from core.database import load_chat_history_from_ddb, save_chat_messages_to_ddb

ai_client = None

def latency_monitor_thread(hud):
    """Background thread to measure latency to Google Gemini API servers every 10 seconds."""
    import socket
    while True:
        try:
            start = time.perf_counter()
            s = socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=3.0)
            s.close()
            latency = int((time.perf_counter() - start) * 1000)
            hud.sig_latency.emit(f"{latency}ms")
        except Exception:
            hud.sig_latency.emit("OFFLINE")
        time.sleep(10)

async def pipeline_async(hud):
    global ai_client
    if ai_client is None:
        ai_client = init_llm_client()
        if ai_client is None:
            return

    init_audio_models()
    from core.audio import oww_model

    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=pyaudio.paInt16, channels=1, rate=16000,
        input=True, frames_per_buffer=CHUNK_SIZE, stream_callback=mic_callback)
    spk_stream = audio.open(
        format=pyaudio.paInt16, channels=1, rate=24000,
        output=True, frames_per_buffer=CHUNK_SIZE, stream_callback=speaker_callback)

    # Load session history from DynamoDB
    db_history = load_chat_history_from_ddb("default")
    for msg in db_history:
        speaker = "YOU" if msg["role"] == "user" else "GRACE"
        text = msg["parts"][0]["text"]
        hud.add_message(speaker, text)

    chat_session = ai_client.chats.create(
        model='gemini-2.5-flash-lite',
        history=db_history,
        config=genai.types.GenerateContentConfig(
            system_instruction=(
                "You are Grace, a desktop AI assistant. Dynamically adjust the length of your responses to match the complexity of the user's input: keep greetings, quick updates, or casual remarks short and conversational, but provide deep, structured, and detailed analysis when asked complex questions or for guidance. "
                "Align your personality and feedback with the user's primary objectives and traits:\n\n"
                "USER CONTEXT & TRAITS:\n"
                "- Career: The user is a software engineer in Chennai working at TCS on a Stibo STEP MDM project for Walgreens. His technical background is in Java/OOP, Spring Boot, JPA/Hibernate, and PostgreSQL, along with React/TypeScript. His ultimate career goal is transitioning to a development engineering role at a major tech company. Do NOT refer to him as an SRE or guide him under SRE tracks.\n"
                "- Daily Habits & Learning: Monospace/LeetCode habits (prefers cumulative monthly summaries rather than daily progress updates),  cold showers, Xbox/Steam gamer. \n"
                "- Communication Preferences: Casual, direct, and honest. He will push back if he disagrees. Always offer objective, reality-grounded responses rather than hollow, soothing reassurance.\n"
                "- Anxiety Management: If he spirals into anxiety about AI disruption or the job market, provide calm reality checks paired with concrete, actionable steps.\n\n"
                "ASSISTANT INSTRUCTIONS:\n"
                "1. Keep him inspired and focused on his development engineering goals through clear, logical progression.\n"
                "2. Identify when his focus might drift from this primary path and help him realign.\n"
                "3. Provide actionable assistance (code help, roadmap suggestions, architecture reviews) focused on development engineering.\n"
                "Filter your advice and career-related discussions through this central question: 'How does this bring the user closer to becoming a development engineer at a big tech firm?'"
            ),
            response_modalities=["TEXT"],
        )
    )

    active_session = False
    mic_stream.start_stream()
    spk_stream.start_stream()
    hud.set_state(STATE_IDLE)

    text_input_queue = queue.Queue()
    hud.sig_text_input.connect(lambda t: text_input_queue.put(t))

    try:
        while True:
            user_cmd = None
            is_text_cmd = False

            try:
                user_cmd = text_input_queue.get_nowait()
                active_session = True
                is_text_cmd = True
            except queue.Empty:
                pass

            if not active_session:
                try:
                    data = mic_queue.get(timeout=0.1)
                    pcm  = np.frombuffer(data, dtype=np.int16)
                    pred = oww_model.predict(pcm)
                    if pred['hey_mycroft'] > 0.75:
                        active_session = True
                except queue.Empty:
                    continue

            if active_session:
                if not is_text_cmd:
                    hud.set_state(STATE_LISTENING)
                    user_cmd = run_live_vad_session(hud)

                if not user_cmd:
                    active_session = False
                    hud.set_state(STATE_IDLE)
                    continue

                cleaned  = user_cmd.strip().lower().replace(".", "").replace(",", "")
                hallucinations = {"you", "thank you", "oh", "bye", "yeah", "uh", "um", ""}

                if not is_text_cmd and cleaned in hallucinations:
                    active_session = False
                    hud.set_state(STATE_IDLE)
                    continue

                hud.add_message("YOU", user_cmd)

                is_sleep_cmd = (
                    cleaned in {"sleep", "bye", "goodbye", "stop"} or
                    any(trigger in cleaned for trigger in ["go to sleep", "stop listening"])
                ) and len(cleaned.split()) <= 4

                if is_sleep_cmd:
                    hud.add_message("GRACE", "Going to sleep. Wake me if you need anything!")
                    active_session = False
                    hud.set_state(STATE_IDLE)
                    continue

                hud.set_state(STATE_PROCESSING)

                try:
                    response    = await send_message_with_retry(chat_session, user_cmd, hud)
                    text_answer = response.candidates[0].content.parts[0].text.strip()
                    hud.add_message("GRACE", text_answer)
                    
                    # Track metrics and costs
                    if response.usage_metadata:
                        llm.session_input_tokens += getattr(response.usage_metadata, 'prompt_token_count', 0)
                        llm.session_output_tokens += getattr(response.usage_metadata, 'candidates_token_count', 0)
                        total_cost = (llm.session_input_tokens * 0.075 / 1000000) + (llm.session_output_tokens * 0.30 / 1000000)
                        hud.sig_metrics.emit(llm.session_input_tokens + llm.session_output_tokens, total_cost)
                    
                    # Persist conversation log to DynamoDB
                    save_chat_messages_to_ddb("default", user_cmd, text_answer)

                    hud.set_state(STATE_SPEAKING)
                    audio_bytes  = await synthesize_speech(text_answer)
                    
                    # Attach play button trigger to the latest bubble
                    hud.attach_play_button_to_latest(lambda ab=audio_bytes: threading.Thread(
                        target=play_audio_sync, args=(ab, hud), daemon=True
                    ).start())
                    
                    interrupted  = await play_audio_with_interruption(audio_bytes)

                    if not interrupted:
                        await asyncio.sleep(0.5)
                        with mic_queue.mutex:
                            mic_queue.queue.clear()

                    active_session = True
                    hud.set_state(STATE_LISTENING if interrupted else STATE_IDLE)

                except errors.ClientError as e:
                    msg = "Rate limit hit. Taking a short break." if getattr(e, 'code', None) == 429 else f"API error: {e}"
                    hud.add_message("GRACE", msg)
                    active_session = False
                    hud.set_state(STATE_IDLE)

                except Exception as e:
                    hud.add_message("GRACE", f"Unexpected error: {e}")
                    active_session = False
                    hud.set_state(STATE_IDLE)

    except Exception:
        pass
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        spk_stream.stop_stream()
        spk_stream.close()
        audio.terminate()

def run_pipeline(hud):
    asyncio.run(pipeline_async(hud))
