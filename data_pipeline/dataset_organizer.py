import os
import shutil

# Setting up the directory paths
RAW_FOLDER = "raw_dataset"
READY_FOLDER = "processed_dataset"

def setup_folders():
    """Creates the necessary directory structure for AI training data."""
    os.makedirs(f"{RAW_FOLDER}", exist_ok=True)
    os.makedirs(f"{READY_FOLDER}/safe_human", exist_ok=True)
    os.makedirs(f"{READY_FOLDER}/malicious_ai", exist_ok=True)
    print("📂 Directory structure initialized successfully!")

def sort_audio_files():
    """Scans raw audio files and categorizes them based on naming conventions."""
    if not os.path.exists(RAW_FOLDER):
        print(f"❌ Error: The '{RAW_FOLDER}' directory was not found.")
        return

    files = os.listdir(RAW_FOLDER)
    
    if len(files) == 0:
        print(f"⚠️ Warning: The '{RAW_FOLDER}' folder is empty. Please place your downloaded audio dataset here first.")
        return

    print(f"⏳ Sorting {len(files)} audio files...\n")
    
    for file_name in files:
        source_path = os.path.join(RAW_FOLDER, file_name)
        
        # Logic: Route files containing 'spoof', 'fake', or 'ai' to the malicious folder
        if "spoof" in file_name.lower() or "fake" in file_name.lower() or "ai" in file_name.lower():
            destination = os.path.join(READY_FOLDER, "malicious_ai", file_name)
            shutil.copy(source_path, destination)
            print(f"🚨 [DEEPFAKE DETECTED] Moved to AI directory -> {file_name}")
            
        # Otherwise, route to the safe human folder
        else:
            destination = os.path.join(READY_FOLDER, "safe_human", file_name)
            shutil.copy(source_path, destination)
            print(f"✅ [REAL HUMAN VERIFIED] Moved to Safe directory -> {file_name}")

    print("\n🎉 Dataset curation complete! Files are ready for AI model training.")

if __name__ == "__main__":
    setup_folders()
    sort_audio_files()