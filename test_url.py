from utils import convert_url_to_dropbox_direct

# Test URLs
gdrive_urls = [
    "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9/view?usp=sharing",
    "https://drive.google.com/open?id=1a2b3c4d5e6f7g8h9",
]
dropbox_urls = [
    "https://www.dropbox.com/s/abcd1234/file.mp3?dl=0",
    "https://www.dropbox.com/s/efgh5678/audio.mp3?dl=0&rlkey=xyz",
]

print("Testing Google Drive URLs:")
for url in gdrive_urls:
    print(f"Original: {url}")
    print(f"Reformatted: {convert_url_to_dropbox_direct(url)}\n")

print("Testing Dropbox URLs:")
for url in dropbox_urls:
    print(f"Original: {url}")
    print(f"Reformatted: {convert_url_to_dropbox_direct(url)}\n")