"""Utility functions for URL conversion and other helpers"""
import logging

logger = logging.getLogger(__name__)

def convert_url_to_dropbox_direct(url):
    """Convert Dropbox URL to direct access URL"""
    if not url or "dropbox.com" not in url:
        return url

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
