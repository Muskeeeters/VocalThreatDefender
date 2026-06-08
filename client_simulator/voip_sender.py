import requests
import time
import os

# Ramlah ke backend ka local address (Django default port 8000)
API_URL = "http://127.0.0.1:8000/api/analyze/"

def simulate_live_call(audio_file_path, transcript_text):
    print(f"📞 VoIP Simulator Started...")
    print(f"📂 Loading audio: {audio_file_path}")
    
    if not os.path.exists(audio_file_path):
        print("❌ Error: Audio file not found! First, place a dummy .wav or .mp3 file here.")
        return

    # File ko binary mode ('rb') mein read kar ke package banayen
    with open(audio_file_path, 'rb') as audio_file:
        files = {
            'audio': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
        }
        data = {
            'text': transcript_text
        }
        
        try:
            print("⏳ Sending packet to VishiGuard AI Engine...\n")
            # POST request bhejna
            response = requests.post(API_URL, files=files, data=data)
            
            # Response check karna
            if response.status_code == 200:
                print("✅ [SUCCESS] AI Engine Response Received!")
                print("📊 Danger Evaluation:", response.json())
            else:
                print(f"⚠️ [FAILED] Server returned status code: {response.status_code}")
                print("Detail:", response.text)
                
        except requests.exceptions.ConnectionError:
            print("❌ [CONNECTION ERROR] Could not connect to the AI Engine. Make sure the Django server is running on port 8000.")

if __name__ == "__main__":
    # Test karne ke liye ek dummy file ka path aur fake transcript
    DUMMY_AUDIO = "test_call.mp3" # Tumhe is naam ki ek audio file same folder mein rakhni hogi
    FAKE_TRANSCRIPT = "Hello sir, I am calling from your bank. Your account will be locked if you don't share your PIN."
    
    simulate_live_call(DUMMY_AUDIO, FAKE_TRANSCRIPT)