import librosa
import numpy as np

def extract_acoustic_fingerprint(file_path, max_pad_len=400):
    """
    Extracts MFCCs and Mel-Spectrogram features from an audio file.
    Grounded in digital signal processing to detect synthetic audio anomalies.
    """
    # Load audio (downsample to 16kHz for standardization)
    y, sr = librosa.load(file_path, sr=16000, duration=5.0)
    
    # 1. Extract MFCCs
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
    
    # Pad or truncate to ensure uniform input shape for models
    if mfccs.shape[1] < max_pad_len:
        pad_width = max_pad_len - mfccs.shape[1]
        mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
    else:
        mfccs = mfccs[:, :max_pad_len]
        
    # 2. Extract Mel-Spectrogram
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    return {
        "mfccs": mfccs.tolist(),
        "mel_spectrogram_shape": mel_spec_db.shape,
        "is_synthetic_heuristic": float(np.mean(mfccs[1:4])) > 12.0 # Simple baseline threshold
    }