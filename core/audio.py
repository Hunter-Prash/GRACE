import io
import math
import queue
import asyncio
import threading
import pyaudio
import numpy as np
import re
from kokoro import KPipeline
from faster_whisper import WhisperModel
from openwakeword.model import Model
from core.config import (
    SILENCE_THRESHOLD, MAX_SILENCE_CHUNKS, CHUNK_SIZE, KOKORO_VOICE,
    FFMPEG_PATH, FFPROBE_PATH, STATE_IDLE, STATE_SPEAKING
)

mic_queue = queue.Queue()
speaker_queue = queue.Queue()

whisper_model = None
oww_model = None
kokoro_pipeline = None

def init_audio_models():
    global whisper_model, oww_model, kokoro_pipeline
    if whisper_model is None:
        print("Loading Whisper onto RTX 3050...")
        whisper_model = WhisperModel("base.en", device="cuda", compute_type="float16")
    if oww_model is None:
        print("Loading openWakeWord...")
        oww_model = Model(wakeword_models=["hey_mycroft"], inference_framework="onnx")
    if kokoro_pipeline is None:
        print("Loading Kokoro TTS...")
        kokoro_pipeline = KPipeline(lang_code='a')

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
    """Synthesize speech using Kokoro TTS running locally on GPU."""
    def _run_kokoro():
        clean_text = re.sub(r'[*`~_#]', '', text)
        all_audio = []
        generator = kokoro_pipeline(clean_text, voice=KOKORO_VOICE, speed=1.2, split_pattern=r'[.!?]+')
        for _, _, audio in generator:
            if audio is not None and len(audio) > 0:
                all_audio.append(audio)
        if not all_audio:
            return np.zeros(1, dtype=np.float32)
        return np.concatenate(all_audio)

    audio_np = await asyncio.to_thread(_run_kokoro)
    # Kokoro outputs float32 at 24kHz — convert to int16 PCM for pyaudio
    audio_int16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)
    return audio_int16.tobytes()

async def stream_synthesize_and_play(text: str, hud) -> tuple[bool, bytes]:
    """Stream TTS generation directly to speaker_queue and monitor for interruptions."""
    with speaker_queue.mutex:
        speaker_queue.queue.clear()
        
    is_generating = [True]
    interrupted = [False]
    all_bytes = []
    
    def _run_kokoro():
        try:
            clean_text = re.sub(r'[*`~_#]', '', text)
            generator = kokoro_pipeline(clean_text, voice=KOKORO_VOICE, speed=1.2, split_pattern=r'[.!?]+')
            for _, _, audio in generator:
                if interrupted[0]:
                    break
                if audio is not None and len(audio) > 0:
                    # Convert PyTorch tensor to NumPy array
                    if hasattr(audio, "cpu"):
                        audio_np = audio.cpu().numpy()
                    else:
                        audio_np = np.array(audio)
                        
                    audio_int16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)
                    audio_bytes = audio_int16.tobytes()
                    all_bytes.append(audio_bytes)
                    chunk_len = CHUNK_SIZE * 2
                    for i in range(0, len(audio_bytes), chunk_len):
                        speaker_queue.put(audio_bytes[i:i+chunk_len])
        finally:
            is_generating[0] = False

    # Start generator thread
    kokoro_thread = threading.Thread(target=_run_kokoro, daemon=True)
    kokoro_thread.start()
    
    hud.set_state(STATE_SPEAKING)
    
    # Wait for completion while checking for interruptions
    while is_generating[0] or not speaker_queue.empty():
        try:
            mic_data = mic_queue.get_nowait()
            pcm = np.frombuffer(mic_data, dtype=np.int16)
            vol = math.sqrt(sum(int(x)**2 for x in pcm) / max(len(pcm), 1))
            if vol >= SILENCE_THRESHOLD + 150:
                interrupted[0] = True
                with speaker_queue.mutex:
                    speaker_queue.queue.clear()
                break
        except queue.Empty:
            pass
        await asyncio.sleep(0.01)
        
    return interrupted[0], b''.join(all_bytes)

def run_live_vad_session(hud):
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

def play_audio_sync(audio_bytes: bytes, hud):
    import time
    hud.set_state(STATE_SPEAKING)
    with speaker_queue.mutex:
        speaker_queue.queue.clear()
    chunk_len = CHUNK_SIZE * 2
    for i in range(0, len(audio_bytes), chunk_len):
        speaker_queue.put(audio_bytes[i:i+chunk_len])
        
    while not speaker_queue.empty():
        try:
            mic_data = mic_queue.get_nowait()
            pcm = np.frombuffer(mic_data, dtype=np.int16)
            vol = math.sqrt(sum(int(x)**2 for x in pcm) / max(len(pcm), 1))
            if vol >= SILENCE_THRESHOLD + 150:
                with speaker_queue.mutex:
                    speaker_queue.queue.clear()
                break
        except queue.Empty:
            pass
        time.sleep(0.01)
    hud.set_state(STATE_IDLE)
