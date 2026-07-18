import os
import sys
import yaml

os.environ["HF_HOME"] = os.path.expanduser("~/.cache/huggingface")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
MY_GEMINI_KEY = None

try:
    with open(CONFIG_PATH, "r") as f:
        config_data = yaml.safe_load(f)
        MY_GEMINI_KEY = config_data.get("GEMINI_API_KEY")
except FileNotFoundError:
    print(f"CRITICAL ERROR: config.yaml not found at {CONFIG_PATH}")
    sys.exit(1)


site_packages = next((p for p in sys.path if 'site-packages' in p), None)
if site_packages:
    cublas_bin = os.path.join(site_packages, "nvidia", "cublas", "bin")
    cudnn_bin  = os.path.join(site_packages, "nvidia", "cudnn",  "bin")
    os.environ["PATH"] = f"{cublas_bin};{cudnn_bin};" + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        if os.path.exists(cublas_bin): os.add_dll_directory(cublas_bin)
        if os.path.exists(cudnn_bin):  os.add_dll_directory(cudnn_bin)

# AUDIO CONSTANTS
SILENCE_THRESHOLD = 250
MAX_SILENCE_CHUNKS = 40
CHUNK_SIZE = 1280
KOKORO_VOICE = "af_sarah"  # Options: af_heart, af_bella, af_sarah, bf_emma
FFMPEG_PATH  = "/usr/bin/ffmpeg"
FFPROBE_PATH = "/usr/bin/ffprobe"

# STATE CONSTANTS
STATE_IDLE       = "IDLE"
STATE_LISTENING  = "LISTENING"
STATE_PROCESSING = "PROCESSING"
STATE_SPEAKING   = "SPEAKING"

# API ENDPOINTS
LOCAL_API_URL = "http://localhost:3000"
CLOUD_API_URL = "https://y32tddvhc0.execute-api.ap-south-1.amazonaws.com/Prod" # Override via CLOUD_API_URL env var
API_STATE = {"url": LOCAL_API_URL, "mode": "LOCAL"}
