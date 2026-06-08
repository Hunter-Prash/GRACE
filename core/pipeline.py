import time
import asyncio
import threading
import queue
import pyaudio
import numpy as np
import requests

from core.config import STATE_IDLE, STATE_LISTENING, STATE_PROCESSING, STATE_SPEAKING, CHUNK_SIZE
from core.audio import (
    mic_callback, speaker_callback, mic_queue, oww_model,
    run_live_vad_session, synthesize_speech, play_audio_sync, play_audio_with_interruption, init_audio_models
)

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
    init_audio_models()
    from core.audio import oww_model

    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=pyaudio.paInt16, channels=1, rate=16000,
        input=True, frames_per_buffer=CHUNK_SIZE, stream_callback=mic_callback)
    spk_stream = audio.open(
        format=pyaudio.paInt16, channels=1, rate=24000,
        output=True, frames_per_buffer=CHUNK_SIZE, stream_callback=speaker_callback)

    # Initial boot text, wait for Node.js API to provide history if needed later
    hud.add_message("GRACE", "Booting system... Connecting to Core Backend.")
    
    try:
        def fetch_history():
            return requests.get("http://localhost:3000/api/history/default", timeout=5).json()
        db_response = await asyncio.to_thread(fetch_history)
        if isinstance(db_response, dict) and "history" in db_response:
            db_history = db_response.get("history", [])
            hud.sig_db_latency.emit(db_response.get("dbLatencyMs", 0))
            hud.sig_context_saturation.emit(db_response.get("dbContextItemsCount", len(db_history)))
        elif isinstance(db_response, list):
            db_history = db_response
        else:
            db_history = []
            
        if isinstance(db_history, list):
            last_grace_text = None
            for msg in db_history:
                speaker = "YOU" if msg.get("role") == "user" else "GRACE"
                text = msg.get("parts", [{"text": ""}])[0].get("text", "")
                hud.add_message(speaker, text)
                if speaker == "GRACE":
                    last_grace_text = text
            
            if last_grace_text:
                # Pre-generate audio for the very last message in history so you can replay it
                boot_audio = await synthesize_speech(last_grace_text)
                hud.attach_play_button_to_latest(lambda checked=False, ab=boot_audio: threading.Thread(
                    target=play_audio_sync, args=(ab, hud), daemon=True
                ).start())
    except Exception as e:
        pass

    active_session = False
    session_input_tokens = 0
    session_output_tokens = 0
    mic_stream.start_stream()
    spk_stream.start_stream()
    hud.set_state(STATE_IDLE)

    from PyQt6.QtCore import Qt
    text_input_queue = queue.Queue()
    hud.sig_text_input.connect(lambda t: text_input_queue.put(t), type=Qt.ConnectionType.DirectConnection)

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
                    def make_api_call(text):
                        return requests.post("http://localhost:3000/api/chat", json={"text": text, "sessionId": "default"}, timeout=30).json()

                    response = await asyncio.to_thread(make_api_call, user_cmd)
                    
                    if "error" in response:
                        raise Exception(response["error"])

                    text_answer = response.get("text", "").strip()
                    hud.add_message("GRACE", text_answer)
                    
                    # Track metrics and costs
                    session_input_tokens += response.get("inputTokens", 0)
                    session_output_tokens += response.get("outputTokens", 0)
                    total_cost = (session_input_tokens * 0.075 / 1000000) + (session_output_tokens * 0.30 / 1000000)
                    hud.sig_metrics.emit(session_input_tokens + session_output_tokens, total_cost)
                    
                    # Track new telemetry
                    if "dbLatencyMs" in response:
                        hud.sig_db_latency.emit(response["dbLatencyMs"])
                    if "dbContextItemsCount" in response:
                        hud.sig_context_saturation.emit(response["dbContextItemsCount"])
                    
                    hud.set_state(STATE_SPEAKING)
                    audio_bytes  = await synthesize_speech(text_answer)
                    
                    # Attach play button trigger to the latest bubble
                    hud.attach_play_button_to_latest(lambda checked=False, ab=audio_bytes: threading.Thread(
                        target=play_audio_sync, args=(ab, hud), daemon=True
                    ).start())
                    
                    interrupted  = await play_audio_with_interruption(audio_bytes)

                    if not interrupted:
                        await asyncio.sleep(0.5)
                        with mic_queue.mutex:
                            mic_queue.queue.clear()

                    active_session = True
                    hud.set_state(STATE_LISTENING if interrupted else STATE_IDLE)

                except requests.exceptions.RequestException as e:
                    hud.add_message("GRACE", f"Backend Connection Error. Ensure Node.js server is running.")
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
