"""Utility functions for URL conversion and other helpers"""
import logging
import re

logger = logging.getLogger(__name__)

def convert_url_to_dropbox_direct(url):
    """Convert Dropbox or Google Drive URL to direct access URL"""
    if not url:
        return url

    try:
        if "dropbox.com" in url:
            # Handle Dropbox URLs: Convert to direct download URL
            base_url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
            if "?" in base_url:
                params = base_url.split("?")[1].split("&")
                # Filter out the dl=0 parameter but keep others (rlkey, st, etc)
                filtered_params = [p for p in params if not p.startswith("dl=")]
                if filtered_params:
                    return f"{base_url.split('?')[0]}?{'&'.join(filtered_params)}"
                return base_url.split('?')[0]
            return base_url

        elif "drive.google.com" in url:
            # Handle Google Drive URLs
            file_id = None

            # Pattern for /file/d/ format
            file_pattern = r"/file/d/([a-zA-Z0-9_-]+)"
            # Pattern for id= format
            id_pattern = r"id=([a-zA-Z0-9_-]+)"

            file_match = re.search(file_pattern, url)
            id_match = re.search(id_pattern, url)

            if file_match:
                file_id = file_match.group(1)
            elif id_match:
                file_id = id_match.group(1)

            if file_id:
                return f"https://drive.google.com/uc?export=download&id={file_id}"

            logger.warning(f"Could not extract Google Drive file ID from URL: {url}")
            return url

        return url
    except Exception as e:
        logger.error(f"Error converting URL: {str(e)}")
        return url