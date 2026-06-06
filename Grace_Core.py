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

# Your explicit API Key. 
# WARNING: Do not push this file to GitHub while this key is here.
MY_GEMINI_KEY = "AIzaSyDaLQFgly32RKBXWSURcmB8FOY0DS7_PY8"

print("Initializing Grace Core Architecture...")

# ==========================================
# 2. LOAD AI MODELS (GPU & CPU)
# ==========================================
# Load Whisper directly into your RTX 3050 VRAM. 
# compute_type="float16" forces it to use native GPU optimizations.
print("Loading Whisper Model onto RTX 3050 GPU...")
whisper_model = WhisperModel("base.en", device="cuda", compute_type="float16")

# Load the local wake word engine. This runs purely on the CPU to save power.
print("Loading openWakeWord model...")
oww_model = Model(wakeword_models=["alexa"], inference_framework="onnx")

# Initialize the Google GenAI SDK using your explicit variable
print("Connecting to Gemini API...")
ai_client = genai.Client(api_key=MY_GEMINI_KEY)

# ==========================================
# 3. TRANSCRIPTION ENGINE
# ==========================================
def listen_and_transcribe(audio_stream):
    print("\n[Grace is listening... Speak your command now]")
    frames = []
    silent_chunks = 0
    
    while True:
        # Pull raw audio data from the microphone
        data = audio_stream.read(CHUNK_SIZE, exception_on_overflow=False)
        
        # Convert the raw bytes into integers the computer can do math on
        pcm = np.frombuffer(data, dtype=np.int16)
        frames.extend(pcm)
        
        # Voice Activity Detection (VAD)
        # Calculate the Root Mean Square (RMS) volume of this tiny audio chunk
        volume = math.sqrt(sum([int(x)**2 for x in pcm]) / max(len(pcm), 1))
        
        # If it's quiet, add to the silence counter. If it's loud, reset the counter.
        if volume < SILENCE_THRESHOLD:
            silent_chunks += 1
        else:
            silent_chunks = 0  
            
        # If we have heard 1.5 seconds of silence, AND we captured some actual audio, break the loop
        if silent_chunks > MAX_SILENCE_CHUNKS and len(frames) > 8000:
            break
            
    print("Transcribing on RTX 3050...")
    
    # Whisper requires a specific data type (float32). We convert our recorded frames here.
    audio_data = np.array(frames, dtype=np.float32) / 32768.0
    
    # Run the transcription on the GPU
    segments, _ = whisper_model.transcribe(audio_data, beam_size=5)
    
    # Stitch the detected words together into a single sentence
    transcript = "".join([segment.text for segment in segments]).strip()
    
    return transcript

# ==========================================
# 4. MAIN EVENT LOOP
# ==========================================
def main():
    # Initialize the microphone hardware stream
    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,         # 16kHz is the standard sampling rate for voice models
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    print("\n=== Grace Core Pipeline Online (Gemini 3.5 Powered) ===")
    print("Say 'Alexa' to trigger the system.")
    
    try:
        # The Infinite Idle Loop
        while True:
            # Continuously listen, processing audio in tiny, memory-safe chunks
            data = mic_stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Feed the audio to the wake word model
            prediction = oww_model.predict(audio_data)
            
            # If the model is more than 50% sure it heard "Alexa", trigger the active loop
            if prediction['alexa'] > 0.5:
                print(f"\n[{time.strftime('%H:%M:%S')}] Trigger Word Detected!")
                
                # Capture and transcribe the voice command
                user_command = listen_and_transcribe(mic_stream)
                
                if user_command:
                    print(f"--> You said: \"{user_command}\"")
                    print("Sending to Gemini 3.5 Flash...")
                    
                    # Send the text to Gemini 3.5 Flash
                    # We pass a system instruction to ensure she knows her persona
                    response = ai_client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=user_command,
                        config=genai.types.GenerateContentConfig(
                            system_instruction="You are Grace, a personal desktop AI assistant. Keep responses brief, direct, and conversational since your output will eventually be read aloud."
                        )
                    )
                    
                    # Print Grace's response
                    print(f"\n[Grace]: {response.text}")
                else:
                    print("--> [No clear audio captured]")
                    
                print("\nReturning to background listening loop...")
                
    except KeyboardInterrupt:
        # Gracefully handle shutting down if you press Ctrl+C in the terminal
        print("\nShutting down pipeline components...")
    finally:
        # Release the microphone so other apps can use it
        mic_stream.stop_stream()
        mic_stream.close()
        audio.terminate()

if __name__ == '__main__':
    main()