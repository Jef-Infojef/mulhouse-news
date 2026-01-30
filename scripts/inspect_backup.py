
import zipfile
import os

zip_path = r"P:\Backup\AssosCom-20260125-2259.zip"

try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        print(f"Contents of {zip_path}:")
        for file_info in zip_ref.infolist():
            print(f"- {file_info.filename} ({file_info.file_size} bytes)")
except Exception as e:
    print(f"Error reading zip: {e}")
