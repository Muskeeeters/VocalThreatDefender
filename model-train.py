import os
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
dataset = "awsaf49/asvpoof-2019-dataset"
target_folder = "LA/ASVspoof2019_LA_train/flac/"
download_dir = "./vishing_chunk"
os.makedirs(download_dir, exist_ok=True)
print("Connecting to Kaggle to find files...")
files = api.dataset_list_files(dataset).files
flac_files = [str(f) for f in files if str(f).startswith(target_folder) and str(f).endswith('.flac')]
chunk = flac_files[:10]
for filename in chunk:
    print(f"Downloading {filename}...")
    api.dataset_download_file(dataset, filename, path=download_dir)
print("Success! You have your 10 files.")