import os
import sys
import yaml

# ==========================================
# 0. BULLETPROOF NVIDIA CUDA & CONFIG LINKING
# ==========================================
os.environ["HF_HOME"] = "D:\\PERSONAL\\GRACE\\.cache\\huggingface"

# Automatically load the API key from your local config.yaml file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
try:
    with open(CONFIG_PATH, "r") as f:
        config_data = yaml.safe_load(f)
        MY_GEMINI_KEY = config_data.get("GEMINI_API_KEY")
except FileNotFoundError:
    print("CRITICAL ERROR: config.yaml file not found in project directory!")
    sys.exit(1)

# Find the site-packages directory to load CUDA DLLs
site_packages = next((p for p in sys.path if 'site-packages' in p), None)
if site_packages:
    cublas_bin = os.path.join(site_packages, "nvidia", "cublas", "bin")
    cudnn_bin = os.path.join(site_packages, "nvidia", "cudnn", "bin")
    os.environ["PATH"] = f"{cublas_bin};{cudnn_bin};" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        if os.path.exists(cublas_bin): os.add_dll_directory(cublas_bin)
        if os.path.exists(cudnn_bin): os.add_dll_directory(cudnn_bin)

import pyaudio
import numpy as np
from openwakeword.model import Model
from faster_whisper import WhisperModel
from google import genai
import time
import math

# ==========================================
# 1. SYSTEM CONFIGURATION
# ==========================================
SILENCE_THRESHOLD = 50      # The volume level considered "quiet"
MAX_SILENCE_CHUNKS = 40     # How long to wait in silence before stopping the recording (~1.5s)
CHUNK_SIZE = 1280           # The number of audio frames processed at a time

print("Initializing Grace Core Architecture...")

# ==========================================
# 2. LOAD AI MODELS (GPU & CPU)
# ==========================================
print("Loading Whisper Model onto RTX 3050 GPU...")
whisper_model = WhisperModel("base.en", device="cuda", compute_type="float16")

print("Loading openWakeWord model...")
oww_model = Model(wakeword_models=["hey_mycroft"], inference_framework="onnx")

print("Connecting to Gemini API...")
ai_client = genai.Client(api_key=MY_GEMINI_KEY)

# ==========================================
# 3. TRANSCRIPTION ENGINE (Live VAD Gate)
# ==========================================
def listen_and_transcribe(audio_stream):
    print("\n[Grace is listening... Take your time.]")
    frames = []
    
    # PHASE 1: The Infinite Wait Gate
    # Grace stays here forever, throwing away silence, until you speak.
    while True:
        data = audio_stream.read(CHUNK_SIZE, exception_on_overflow=False)
        pcm = np.frombuffer(data, dtype=np.int16)
        volume = math.sqrt(sum([int(x)**2 for x in pcm]) / max(len(pcm), 1))
        
        if volume >= SILENCE_THRESHOLD:
            # You started speaking! Save this chunk and move to Phase 2
            frames.extend(pcm)
            break

    # PHASE 2: Recording the Command
    # Now she records until you stop speaking for 1.5 seconds.
    silent_chunks = 0
    while True:
        data = audio_stream.read(CHUNK_SIZE, exception_on_overflow=False)
        pcm = np.frombuffer(data, dtype=np.int16)
        frames.extend(pcm)
        
        volume = math.sqrt(sum([int(x)**2 for x in pcm]) / max(len(pcm), 1))
        
        if volume < SILENCE_THRESHOLD:
            silent_chunks += 1
        else:
            silent_chunks = 0  
            
        if silent_chunks > MAX_SILENCE_CHUNKS:
            break
            
    print("Transcribing on RTX 3050...")
    audio_data = np.array(frames, dtype=np.float32) / 32768.0
    segments, _ = whisper_model.transcribe(audio_data, beam_size=5)
    
    return "".join([segment.text for segment in segments]).strip()

# ==========================================
# 4. MAIN EVENT LOOP WITH CONTINUOUS CHAT
# ==========================================
def main():
    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,         
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    print("\n=== Grace Core Pipeline Online (Gemini 3.5 Powered) ===")
    print("Say 'Hey Mycroft' to trigger the system.")
    
    # This flag tracks if we are in an active back-and-forth conversation
    active_session = False
    
    try:
        while True:
            # Continuously listen to audio chunks for the wake word
            data = mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Feed the audio to the wake word model
            prediction = oww_model.predict(audio_data)
            
            # Trigger if we hear the wake word OR if we are in an active follow-up session
            if prediction['hey_mycroft'] > 0.75 or active_session:
                if not active_session:
                    print(f"\n[{time.strftime('%H:%M:%S')}] Trigger Word Detected!")
                else:
                    print(f"\n[{time.strftime('%H:%M:%S')}] Follow-up conversation window open...")
                
                # Capture and transcribe the voice command
                user_command = listen_and_transcribe(mic_stream)
                
                # Normalize text to filter out Whisper background noise hallucinations
                cleaned_command = user_command.strip().lower().replace(".", "").replace(",", "")
                hallucinations = {"you", "thank you", "oh", "bye", "yeah", "uh", "um", ""}
                
                if user_command and cleaned_command not in hallucinations:
                    print(f"--> You said: \"{user_command}\"")
                    
                    # Check if you want to end the continuous conversation
                    if any(word in cleaned_command for word in ["sleep", "goodbye", "stop listening", "go to sleep"]):
                        print("\n[Grace]: Going to sleep. Wake me if you need anything!")
                        active_session = False
                        print("\nReturning to background listening loop...")
                        continue

                    print("Sending to Gemini 3.5 Flash...")
                    
                    # Send the text to Gemini 3.5 Flash
                    response = ai_client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=user_command,
                        config=genai.types.GenerateContentConfig(
                            system_instruction="You are Grace, a personal desktop AI assistant. Keep responses brief, direct, and conversational."
                        )
                    )
                    
                    print(f"\n[Grace]: {response.text}")
                    
                    # SUCCESS: Keep the conversation window alive for the next sentence!
                    active_session = True
                else:
                    # If it was a false trigger or silence, close the session
                    print("--> [No follow-up speech detected or background noise ignored. Going to sleep...]")
                    active_session = False
                    print("\nReturning to background listening loop...")
                
    except KeyboardInterrupt:
        print("\nShutting down pipeline components...")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        audio.terminate()

if __name__ == '__main__':
    main()