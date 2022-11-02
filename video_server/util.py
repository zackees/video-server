import urllib.parse

from video_server.settings import SERVER_PORT

def get_video_url(url: str) -> str:
    """Return the video url."""
    if SERVER_PORT == 80:
        return url
    # parse url into parts
    parts = urllib.parse.urlparse(url)
    # replace the port
    new_parts = parts._replace(netloc=f"{parts.hostname}:{SERVER_PORT}")
    # rebuild the url
    url = urllib.parse.urlunparse(new_parts)
    return url
