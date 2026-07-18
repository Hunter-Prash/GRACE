import time
import asyncio
import threading
import queue
import pyaudio
import numpy as np
import requests
import json
import os
import webbrowser
from datetime import datetime, timezone, timedelta
from PyQt6.QtCore import Qt

IST = timezone(timedelta(hours=5, minutes=30))
from core.config import (
    STATE_IDLE, STATE_LISTENING, STATE_PROCESSING, STATE_SPEAKING, CHUNK_SIZE,
    API_STATE, LOCAL_API_URL, CLOUD_API_URL
)

def _on_env_toggle(mode):
    if mode == "CLOUD":
        API_STATE["mode"] = "CLOUD"
        API_STATE["url"] = os.environ.get("CLOUD_API_URL", CLOUD_API_URL)
    else:
        API_STATE["mode"] = "LOCAL"
        API_STATE["url"] = LOCAL_API_URL

from core.audio import (
    mic_callback, speaker_callback, mic_queue, oww_model,
    run_live_vad_session, synthesize_speech, play_audio_sync, play_audio_with_interruption, init_audio_models
)
from core.biometrics import init_biometrics, verify_speaker, has_voice_profile
from collections import deque

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

def rag_monitor_thread(hud):
    """Background thread to fetch RAG and DB stats from the backend every 15 seconds."""
    while True:
        try:
            resp = requests.get(f"{API_STATE['url']}/api/rag/stats", timeout=10.0)
            if resp.status_code == 200:
                hud.sig_rag_stats.emit(resp.json())
        except Exception:
            pass
        time.sleep(15)

async def pipeline_async(hud):
    init_audio_models()
    try:
        init_biometrics()
    except Exception as e:
        print(f"Failed to initialize biometrics: {e}")

    import gc
    import torch
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    from core.audio import oww_model

    audio = pyaudio.PyAudio()
    try:
        mic_stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=16000,
            input=True, frames_per_buffer=CHUNK_SIZE, stream_callback=mic_callback)
        spk_stream = audio.open(
            format=pyaudio.paInt16, channels=1, rate=24000,
            output=True, frames_per_buffer=CHUNK_SIZE, stream_callback=speaker_callback)
    except Exception as e:
        print(f"Warning: Audio device missing. Voice disabled. ({e})")
        mic_stream = None
        spk_stream = None

    # Initial boot text, wait for Node.js API to provide history if needed later
    hud.add_message("GRACE", "Booting system... Connecting to Core Backend.")

    try:
        def fetch_history():
            return requests.get(f"{API_STATE['url']}/api/history/default", timeout=5).json()
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
            hud._loading_history = True
            last_grace_text = None
            for msg in db_history:
                speaker = "YOU" if msg.get("role") == "user" else "GRACE"
                text = ""
                if "parts" in msg and len(msg["parts"]) > 0:
                    text = msg["parts"][0].get("text", "")
                else:
                    text = msg.get("text", "")
                hud.add_message(speaker, text)
                if speaker == "GRACE":
                    last_grace_text = text

            hud.finish_history_load()

            if last_grace_text:
                # Pre-generate audio for the very last message in history so you can replay it
                boot_audio = await synthesize_speech(last_grace_text)
                hud.attach_play_button_to_latest(lambda checked=False, ab=boot_audio: threading.Thread(
                    target=play_audio_sync, args=(ab, hud), daemon=True
                ).start())
    except Exception as e:
        pass

    # ── DAILY BRIEFING ENGINE ──
    # Check if this is the first boot of the day
    try:
        quota_path = "quota.json"
        today_ist = datetime.now(IST).strftime("%Y-%m-%d")
        quota_data = {}
        if os.path.exists(quota_path):
            with open(quota_path, "r") as f:
                quota_data = json.load(f)

        last_briefing = quota_data.get("last_briefing_date", "")
        if last_briefing != today_ist:
            print("[SYSTEM] First boot of the day detected. Initializing Daily Briefing Sequence.")

            # 1. Fetch raw goals data from backend for the UI Side Panel
            def fetch_goals():
                try:
                    return requests.get(f"{API_STATE['url']}/api/goals/active", timeout=5).json()
                except Exception:
                    return None

            goals_data = await asyncio.to_thread(fetch_goals)

            if goals_data:
                # 2. Trigger the Frosted Glass Side Panel
                hud.sig_show_briefing_panel.emit(goals_data)

                # 3. Inject the background system prompt to Grace
                briefing_prompt = (
                    "SYSTEM PROMPT: This is the first boot of the day. Please provide Prashant his morning briefing. "
                    "Use your getActiveGoals tool to estimate completion times, and use your Pinecone memory to "
                    "recall his activities from the past two days. Summarize this briefly and speak naturally."
                )

                # We defer injecting it slightly to let the HUD settle
                async def inject_briefing():
                    await asyncio.sleep(1.0)
                    hud.sig_text_input.emit(briefing_prompt)
                asyncio.create_task(inject_briefing())

                # 4. Save today's date so it doesn't trigger again
                quota_data["last_briefing_date"] = today_ist
                with open(quota_path, "w") as f:
                    json.dump(quota_data, f)
    except Exception as e:
        print(f"Failed to initialize daily briefing: {e}")

    active_session = False
    session_input_tokens = 0
    session_output_tokens = 0
    rate_limit_tracker = deque()
    last_toaster_time = 0
    mic_stream.start_stream()
    spk_stream.start_stream()
    hud.set_state(STATE_IDLE)

  
    text_input_queue = queue.Queue()
    hud.sig_text_input.connect(lambda t: text_input_queue.put(t), type=Qt.ConnectionType.DirectConnection)

    cmd_queue = queue.Queue()
    hud.sig_force_sleep.connect(lambda: cmd_queue.put("SLEEP"), type=Qt.ConnectionType.DirectConnection)
    hud.sig_clear_dynamo.connect(lambda: cmd_queue.put("CLEAR_DYNAMO"), type=Qt.ConnectionType.DirectConnection)
    hud.sig_clear_pinecone.connect(lambda: cmd_queue.put("CLEAR_PINECONE"), type=Qt.ConnectionType.DirectConnection)
    hud.sig_env_toggle.connect(_on_env_toggle, type=Qt.ConnectionType.DirectConnection)
    hud.sig_env_toggle.connect(lambda m: cmd_queue.put("RELOAD_HISTORY"), type=Qt.ConnectionType.DirectConnection)

    # 3-second rolling buffer for speaker verification (approx 40 chunks if 1280 chunk_size)
    audio_buffer = deque(maxlen=40)

    try:
        while True:
            if getattr(hud, "is_enrolling", False):
                await asyncio.sleep(0.1)
                continue

            user_cmd = None
            is_text_cmd = False

            try:
                user_cmd = text_input_queue.get_nowait()
                active_session = True
                is_text_cmd = True
            except queue.Empty:
                pass

            try:
                sys_cmd = cmd_queue.get_nowait()
                if sys_cmd == "SLEEP":
                    active_session = False
                    hud.set_state(STATE_IDLE)
                    audio_buffer.clear()
                    with mic_queue.mutex:
                        mic_queue.queue.clear()
                    hud.add_message("GRACE", "System going to sleep. Say the wake word to activate.")
                    continue
                elif sys_cmd == "CLEAR_DYNAMO":
                    try:
                        resp = requests.delete(f"{API_STATE['url']}/api/history/default", timeout=5)
                        if resp.status_code == 200:
                            hud.add_message("GRACE", "Short-term memory wiped successfully.")
                            hud.sig_clear_context.emit()
                    except Exception as e:
                        hud.add_message("GRACE", f"Failed to clear DynamoDB: {e}")
                    continue
                elif sys_cmd == "RELOAD_HISTORY":
                    hud.sig_clear_context.emit()
                    hud.add_message("GRACE", f"Connecting to {API_STATE['mode']} Backend...")
                    try:
                        def fetch_history():
                            return requests.get(f"{API_STATE['url']}/api/history/default", timeout=5).json()
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
                            hud._loading_history = True
                            for msg in db_history:
                                role = "YOU" if msg.get("role") == "user" else "GRACE"
                                text = ""
                                if "parts" in msg and len(msg["parts"]) > 0:
                                    text = msg["parts"][0].get("text", "")
                                else:
                                    text = msg.get("text", "")
                                hud.add_message(role, text, animate=False)
                            hud.sig_finish_history.emit()
                    except Exception as e:
                        hud.add_message("GRACE", f"Failed to fetch history: {e}")
                    continue
                elif sys_cmd == "CLEAR_PINECONE":
                    try:
                        resp = requests.delete(f"{API_STATE['url']}/api/pinecone", timeout=5)
                        if resp.status_code == 200:
                            hud.add_message("GRACE", "Pinecone Long-Term Context completely wiped.")
                        else:
                            hud.add_message("GRACE", "Failed to clear Pinecone memory.")
                    except Exception as e:
                        hud.add_message("GRACE", f"Error connecting to backend: {e}")
                    continue
            except queue.Empty:
                pass

            if not active_session:
                try:
                    data = mic_queue.get(timeout=0.1)
                    pcm  = np.frombuffer(data, dtype=np.int16)
                    audio_buffer.append(pcm)

                    pred = oww_model.predict(pcm)
                    if pred['hey_mycroft'] > 0.75:
                        if has_voice_profile():
                            # Reconstruct the last ~3 seconds of audio to verify who said the wake word
                            verification_data = np.concatenate(list(audio_buffer))
                            is_match, score = verify_speaker(verification_data)
                            if is_match:
                                active_session = True
                            else:
                                print(f"[!] WAKE WORD REJECTED. Unknown Speaker (Score: {score:.3f})")
                                hud.set_state("REJECTED")
                                audio_buffer.clear()
                                # Pause slightly before returning to IDLE
                                await asyncio.sleep(1.5)
                                hud.set_state(STATE_IDLE)
                        else:
                            active_session = True

                        if active_session:
                            audio_buffer.clear()

                except queue.Empty:
                    continue

            if active_session:
                if not is_text_cmd:
                    hud.set_state(STATE_LISTENING)
                    user_cmd = run_live_vad_session(hud, text_input_queue, cmd_queue)

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
                    # ── Terminal: Pipeline start ──
                    hud.sig_terminal_log.emit("▶ INITIATING GEMINI API REQUEST...", "api")
                    truncated = user_cmd[:80] + "..." if len(user_cmd) > 80 else user_cmd
                    hud.sig_terminal_log.emit(f"  INPUT: \"{truncated}\"", "dim")

                    def make_api_call(text):
                        return requests.post(f"{API_STATE['url']}/api/chat", json={"text": text, "sessionId": "default"}, timeout=120).json()

                    response = await asyncio.to_thread(make_api_call, user_cmd)

                    if "error" in response:
                        hud.sig_terminal_log.emit(f"✗ API ERROR: {response['error'][:60]}", "error")
                        raise Exception(response["error"])

                    tools_used = response.get("toolsUsed", [])
                    text_answer = response.get("text", "").strip()

                    # ── Terminal: Response received ──
                    req_in = response.get("inputTokens", 0)
                    req_out = response.get("outputTokens", 0)
                    hud.sig_terminal_log.emit(f"✓ GEMINI RESPONDED // {req_in + req_out} tokens", "api")

                    # ── Terminal: DynamoDB metrics ──
                    db_lat = response.get("dbLatencyMs", 0)
                    db_items = response.get("dbContextItemsCount", 0)
                    hud.sig_terminal_log.emit(f"▶ DYNAMODB READ // {db_lat}ms // {db_items} context items", "db")

                    # ── Terminal: Tool calls ──
                    for tool in tools_used:
                        hud.sig_terminal_log.emit(f"▶ TOOL INVOKED: {tool}", "tool")

                    hud.add_message("GRACE", text_answer, tools=tools_used)

                    map_data = response.get("mapData")
                    if map_data:
                        hud.sig_map_update.emit(map_data)

                    search_data = response.get("searchData")
                    print(f"[DEBUG] searchData received: {bool(search_data)}, keys: {list(search_data.keys()) if search_data else 'None'}")
                    if search_data:
                        print(f"[DEBUG] Emitting sig_search_update with {len(search_data.get('results', []))} results and {len(search_data.get('images', []))} images")
                        hud.sig_search_update.emit(search_data)
                        
                    calendar_data = response.get("calendarData")
                    if calendar_data:
                        print(f"[DEBUG] Emitting sig_calendar_update with {len(calendar_data.get('events', []))} events")
                        hud.sig_calendar_update.emit(calendar_data)

                    client_commands = response.get("clientCommands", [])
                    for cmd in client_commands:
                        if cmd.get("type") == "openResource":
                            resource_name = cmd.get("resourceName", "")
                            app_dictionary = {
                                "chrome": "chrome", "google chrome": "chrome", "edge": "msedge",
                                "brave": "brave", "vscode": "code", "visual studio code": "code",
                                "terminal": "wt", "command prompt": "cmd", "word": "winword",
                                "excel": "excel", "powerpoint": "powerpnt", "calculator": "calc.exe",
                                "notepad": "notepad", "spotify": "spotify:", "vlc": "vlc",
                                "steam": "steam://", "epic": "com.epicgames.launcher://"
                            }
                            if resource_name.startswith("http"):
                                webbrowser.open(resource_name)
                            else:
                                exe = app_dictionary.get(resource_name.lower().strip())
                                if exe:
                                    os.system(f'start "" "{exe}"')
                        elif cmd.get("type") == "fileOperation":
                            hud.sig_context_scene.emit(cmd.get("data", {}))

                    # Track metrics and costs
                    req_in = response.get("inputTokens", 0)
                    req_out = response.get("outputTokens", 0)
                    session_input_tokens += req_in
                    session_output_tokens += req_out
                    in_cost = (session_input_tokens * 0.075 / 1000000)
                    out_cost = (session_output_tokens * 0.30 / 1000000)
                    total_cost = in_cost + out_cost
                    hud.sig_metrics.emit(session_input_tokens + session_output_tokens, total_cost)

                    # Rate Limit Sliding Window Tracker
                    curr_time = time.time()
                    rate_limit_tracker.append((curr_time, req_in + req_out))
                    while rate_limit_tracker and curr_time - rate_limit_tracker[0][0] > 60:
                        rate_limit_tracker.popleft()

                    rpm = len(rate_limit_tracker)
                    tpm = sum(t for _, t in rate_limit_tracker)
                    if rpm >= 12 or tpm >= 200000:
                        if curr_time - last_toaster_time > 10:
                            msg = f"⚠️ 80% RATE LIMIT REACHED ⚠️\n{rpm}/15 RPM | {tpm:,}/250K TPM"
                            hud.sig_alert_toaster.emit(msg)
                            last_toaster_time = curr_time

                    # Track new telemetry
                    if "dbLatencyMs" in response:
                        hud.sig_db_latency.emit(response["dbLatencyMs"])
                    if "dbContextItemsCount" in response:
                        hud.sig_context_saturation.emit(response["dbContextItemsCount"])

                    if response.get("indexerTriggered"):
                        msg = "🧠 MEMORY INDEXER TRIGGERED 🧠\nCompiling 40-message context to Pinecone."
                        hud.sig_alert_toaster.emit(msg)
                        hud.sig_terminal_log.emit("▶ MEMORY INDEXER FIRED // COMPILING TO PINECONE", "rag")

                    hud.set_state(STATE_SPEAKING)
                    hud.sig_terminal_log.emit("▶ SYNTHESIZING SPEECH VIA KOKORO TTS...", "tts")

                    from core.audio import stream_synthesize_and_play
                    interrupted, audio_bytes = await stream_synthesize_and_play(
                        text_answer, hud, text_input_queue, cmd_queue
                    )

                    # Attach play button trigger to the latest bubble after it finishes generating
                    hud.attach_play_button_to_latest(
                        lambda checked=False, ab=audio_bytes: threading.Thread(
                            target=play_audio_sync, args=(ab, hud), daemon=True
                        ).start()
                    )

                    if not interrupted:
                        await asyncio.sleep(0.5)
                        with mic_queue.mutex:
                            mic_queue.queue.clear()

                    # ── Terminal: Pipeline complete ──
                    hud.sig_terminal_log.emit("✓ PIPELINE COMPLETE // RETURNING TO IDLE", "system")
                    hud.sig_terminal_log.emit("─" * 52, "separator")

                    active_session = True
                    hud.set_state(STATE_LISTENING if interrupted else STATE_IDLE)

                except requests.exceptions.RequestException as e:
                    hud.add_message("GRACE", "Backend Connection Error. Ensure Node.js server is running.")
                    active_session = False
                    hud.set_state(STATE_IDLE)

                except Exception as e:
                    hud.add_message("GRACE", f"Unexpected error: {e}")
                    active_session = False
                    hud.set_state(STATE_IDLE)

    except Exception:
        pass
    finally:
        if mic_stream:
            mic_stream.stop_stream()
            mic_stream.close()
        if spk_stream:
            spk_stream.stop_stream()
            spk_stream.close()
        audio.terminate()

def run_pipeline(hud):
    asyncio.run(pipeline_async(hud))
