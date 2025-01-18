from routes import convert_audio_url

# Test URLs
gdrive_url = "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9/view?usp=sharing"
dropbox_url = "https://www.dropbox.com/s/abcd1234/file.mp3?dl=0"

print("Original Google Drive URL:", gdrive_url)
print("Reformatted Google Drive URL:", convert_audio_url(gdrive_url))
print("\nOriginal Dropbox URL:", dropbox_url)
print("Reformatted Dropbox URL:", convert_audio_url(dropbox_url))
