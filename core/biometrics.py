import os
import torch
import torchaudio
import numpy as np

# Globals
VERIFICATION_MODEL = None
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "user_voice_profile.pt")
SIMILARITY_THRESHOLD = 0.45  # Lowered to 0.45 to be more forgiving to natural voice variations

def init_biometrics():
    global VERIFICATION_MODEL
    if VERIFICATION_MODEL is None:
        print("Loading SpeechBrain ECAPA-TDNN onto RTX 3050...")
        import pathlib
        import shutil
        
        # Monkey-patch pathlib.Path.symlink_to on Windows to prevent WinError 1314
        _original_symlink = pathlib.Path.symlink_to
        def _safe_symlink(self, target, target_is_directory=False):
            try:
                _original_symlink(self, target, target_is_directory)
            except OSError as e:
                if getattr(e, "winerror", None) == 1314:
                    if pathlib.Path(target).is_dir():
                        shutil.copytree(str(target), str(self))
                    else:
                        shutil.copy(str(target), str(self))
                else:
                    raise
        pathlib.Path.symlink_to = _safe_symlink
        
        from speechbrain.inference.speaker import SpeakerRecognition
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        # Download and load the pre-trained model
        VERIFICATION_MODEL = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="tmpdir",
            run_opts={"device": device}
        )

def get_audio_tensor(audio_data_int16, sample_rate=16000):
    """Convert int16 PCM numpy array to a torch tensor normalized between -1 and 1."""
    audio_float = audio_data_int16.astype(np.float32) / 32768.0
    return torch.tensor(audio_float).unsqueeze(0)  # Shape: (1, num_samples)

def enroll_voice(audio_data_int16, sample_rate=16000):
    """Extract embedding from audio and save it as the user profile."""
    if VERIFICATION_MODEL is None:
        init_biometrics()
    
    waveform = get_audio_tensor(audio_data_int16, sample_rate)
    
    # Extract embedding
    with torch.no_grad():
        # speechbrain ECAPA-TDNN expects 16kHz audio
        embedding = VERIFICATION_MODEL.encode_batch(waveform)
    
    # Save the embedding tensor to file
    torch.save(embedding, PROFILE_PATH)
    print(f"Voice profile saved to {PROFILE_PATH}")
    return True

def has_voice_profile():
    return os.path.exists(PROFILE_PATH)

def verify_speaker(audio_data_int16, sample_rate=16000):
    """
    Compare the given audio snippet against the saved user profile.
    Returns (is_match, similarity_score)
    """
    if not has_voice_profile():
        # If no profile is enrolled, fallback to accepting everyone
        print("No voice profile found, accepting speaker by default.")
        return True, 1.0

    if VERIFICATION_MODEL is None:
        init_biometrics()
        
    waveform = get_audio_tensor(audio_data_int16, sample_rate)
    
    # Load profile embedding
    profile_embedding = torch.load(PROFILE_PATH, weights_only=True)
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    profile_embedding = profile_embedding.to(device)
    
    with torch.no_grad():
        current_embedding = VERIFICATION_MODEL.encode_batch(waveform.to(device))
        
        # Calculate cosine similarity
        # embeddings are usually normalized, but we can use speechbrain's built-in metric
        # or manual cosine similarity. speechbrain provides similarity:
        similarity = VERIFICATION_MODEL.similarity(current_embedding, profile_embedding)
        score = similarity.item()
        
    print(f"Speaker Verification Score: {score:.3f} (Threshold: {SIMILARITY_THRESHOLD})")
    
    return score >= SIMILARITY_THRESHOLD, score
