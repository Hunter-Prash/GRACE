import os
import sys
import yaml
import pyaudio
import numpy as np
from openwakeword.model import Model
from faster_whisper import WhisperModel
from google import genai
from google.genai import errors
import time
import math
import asyncio
import queue
import edge_tts
import io
import threading

from PyQt6.QtWidgets import QApplication
from Grace_gui import GraceHUD

# ══════════════════════════════════════════
# 0. CUDA + CONFIG
# ══════════════════════════════════════════
os.environ["HF_HOME"] = "D:\\PERSONAL\\GRACE\\.cache\\huggingface"

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
try:
    with open(CONFIG_PATH, "r") as f:
        config_data = yaml.safe_load(f)
        MY_GEMINI_KEY = config_data.get("GEMINI_API_KEY")
except FileNotFoundError:
    print("CRITICAL ERROR: config.yaml not found!")
    sys.exit(1)

site_packages = next((p for p in sys.path if 'site-packages' in p), None)
if site_packages:
    cublas_bin = os.path.join(site_packages, "nvidia", "cublas", "bin")
    cudnn_bin  = os.path.join(site_packages, "nvidia", "cudnn",  "bin")
    os.environ["PATH"] = f"{cublas_bin};{cudnn_bin};" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        if os.path.exists(cublas_bin): os.add_dll_directory(cublas_bin)
        if os.path.exists(cudnn_bin):  os.add_dll_directory(cudnn_bin)

# ══════════════════════════════════════════
# 1. PIPELINE CONFIG
# ══════════════════════════════════════════
SILENCE_THRESHOLD = 50
MAX_SILENCE_CHUNKS = 40
CHUNK_SIZE = 1280
EDGE_TTS_VOICE = "en-US-JennyNeural"
FFMPEG_PATH  = r"C:\Users\Prashant\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\Users\Prashant\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe"

mic_queue     = queue.Queue()
speaker_queue = queue.Queue()

STATE_IDLE       = "IDLE"
STATE_LISTENING  = "LISTENING"
STATE_PROCESSING = "PROCESSING"
STATE_SPEAKING   = "SPEAKING"


# ══════════════════════════════════════════
# 2. AUDIO & PIPELINE CALLBACKS
# ══════════════════════════════════════════
def mic_callback(in_data, frame_count, time_info, status):
    mic_queue.put(in_data)
    return (None, pyaudio.paContinue)

def speaker_callback(in_data, frame_count, time_info, status):
    try:
        data = speaker_queue.get_nowait()
        expected = frame_count * 2
        if len(data) < expected:
            data += b'\x00' * (expected - len(data))
    except queue.Empty:
        data = b'\x00' * (frame_count * 2)
    return (data, pyaudio.paContinue)

async def synthesize_speech(text: str) -> bytes:
    from pydub import AudioSegment
    AudioSegment.converter = FFMPEG_PATH
    AudioSegment.ffprobe   = FFPROBE_PATH
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    seg = AudioSegment.from_mp3(buf)
    seg = seg.set_frame_rate(24000).set_channels(1).set_sample_width(2)
    return seg.raw_data

def run_live_vad_session(hud: GraceHUD):
    with mic_queue.mutex:
        mic_queue.queue.clear()
    frames = []
    while True:
        try:
            data = mic_queue.get(timeout=0.1)
            pcm  = np.frombuffer(data, dtype=np.int16)
            vol  = math.sqrt(sum(int(x)**2 for x in pcm) / max(len(pcm), 1))
            if vol >= SILENCE_THRESHOLD:
                frames.extend(pcm)
                break
        except queue.Empty:
            continue

    silent = 0
    while True:
        try:
            data = mic_queue.get(timeout=0.1)
            pcm  = np.frombuffer(data, dtype=np.int16)
            frames.extend(pcm)

            # live waveform feed
            vol = math.sqrt(sum(int(x)**2 for x in pcm) / max(len(pcm), 1))
            norm_bars = [min(1.0, abs(math.sin(i + vol/500)) * (vol/300)) for i in range(20)]
            hud.set_waveform(norm_bars)

            if vol < SILENCE_THRESHOLD:
                silent += 1
            else:
                silent = 0
            if silent > MAX_SILENCE_CHUNKS:
                break
        except queue.Empty:
            continue

    audio_data = np.array(frames, dtype=np.float32) / 32768.0
    segments, _ = whisper_model.transcribe(audio_data, beam_size=5)
    return "".join(s.text for s in segments).strip()

async def play_audio_with_interruption(audio_bytes: bytes) -> bool:
    with speaker_queue.mutex:
        speaker_queue.queue.clear()
    chunk_len = CHUNK_SIZE * 2
    for i in range(0, len(audio_bytes), chunk_len):
        speaker_queue.put(audio_bytes[i:i+chunk_len])
    interrupted = False
    while not speaker_queue.empty():
        try:
            mic_data = mic_queue.get_nowait()
            pcm = np.frombuffer(mic_data, dtype=np.int16)
            vol = math.sqrt(sum(int(x)**2 for x in pcm) / max(len(pcm), 1))
            if vol >= SILENCE_THRESHOLD + 150:
                with speaker_queue.mutex:
                    speaker_queue.queue.clear()
                interrupted = True
                break
        except queue.Empty:
            pass
        await asyncio.sleep(0.01)
    return interrupted

async def pipeline_async(hud: GraceHUD):
    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=pyaudio.paInt16, channels=1, rate=16000,
        input=True, frames_per_buffer=CHUNK_SIZE, stream_callback=mic_callback)
    spk_stream = audio.open(
        format=pyaudio.paInt16, channels=1, rate=24000,
        output=True, frames_per_buffer=CHUNK_SIZE, stream_callback=speaker_callback)

    chat_session = ai_client.chats.create(
        model='gemini-2.5-flash-lite',
        config=genai.types.GenerateContentConfig(
            system_instruction=(
                "You are Grace, a desktop AI assistant. Your responses should be detailed, conversational, and direct, avoiding overly brief or generic answers. "
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

    try:
        while True:
            if not active_session:
                try:
                    data = mic_queue.get(timeout=0.1)
                    pcm  = np.frombuffer(data, dtype=np.int16)
                    pred = oww_model.predict(pcm)
                    if pred['hey_mycroft'] > 0.75:
                        hud.set_state(STATE_LISTENING)
                        active_session = True
                except queue.Empty:
                    continue

            if active_session:
                hud.set_state(STATE_LISTENING)
                user_cmd = run_live_vad_session(hud)
                cleaned  = user_cmd.strip().lower().replace(".", "").replace(",", "")
                hallucinations = {"you", "thank you", "oh", "bye", "yeah", "uh", "um", ""}

                if not user_cmd or cleaned in hallucinations:
                    active_session = False
                    hud.set_state(STATE_IDLE)
                    continue

                hud.add_message("YOU", user_cmd)

                if any(w in cleaned for w in ["sleep", "goodbye", "stop listening", "go to sleep"]):
                    hud.add_message("GRACE", "Going to sleep. Wake me if you need anything!")
                    active_session = False
                    hud.set_state(STATE_IDLE)
                    continue

                hud.set_state(STATE_PROCESSING)

                try:
                    response    = chat_session.send_message(user_cmd)
                    text_answer = response.candidates[0].content.parts[0].text.strip()
                    hud.add_message("GRACE", text_answer)

                    hud.set_state(STATE_SPEAKING)
                    audio_bytes  = await synthesize_speech(text_answer)
                    interrupted  = await play_audio_with_interruption(audio_bytes)

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

def run_pipeline(hud: GraceHUD):
    asyncio.run(pipeline_async(hud))

# ══════════════════════════════════════════
# 3. BOOT
# ══════════════════════════════════════════
print("Loading Whisper onto RTX 3050...")
whisper_model = WhisperModel("base.en", device="cuda", compute_type="float16")
print("Loading openWakeWord...")
oww_model = Model(wakeword_models=["hey_mycroft"], inference_framework="onnx")
print("Connecting to Gemini...")
ai_client = genai.Client(api_key=MY_GEMINI_KEY)
print("Launching HUD...")

app = QApplication(sys.argv)
hud = GraceHUD()
hud.show()

pipeline_thread = threading.Thread(target=run_pipeline, args=(hud,), daemon=True)
pipeline_thread.start()

sys.exit(app.exec())
