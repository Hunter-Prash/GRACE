import io
import math
import queue
import asyncio
import pyaudio
import numpy as np
import edge_tts
from faster_whisper import WhisperModel
from openwakeword.model import Model
from core.config import (
    SILENCE_THRESHOLD, MAX_SILENCE_CHUNKS, CHUNK_SIZE, EDGE_TTS_VOICE,
    FFMPEG_PATH, FFPROBE_PATH, STATE_IDLE, STATE_SPEAKING
)

mic_queue = queue.Queue()
speaker_queue = queue.Queue()

whisper_model = None
oww_model = None

def init_audio_models():
    global whisper_model, oww_model
    if whisper_model is None:
        print("Loading Whisper onto RTX 3050...")
        whisper_model = WhisperModel("base.en", device="cuda", compute_type="float16")
    if oww_model is None:
        print("Loading openWakeWord...")
        oww_model = Model(wakeword_models=["hey_mycroft"], inference_framework="onnx")

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
