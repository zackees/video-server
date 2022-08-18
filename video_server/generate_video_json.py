"""
Generates a dictionary that can be used for json serialization.
"""

# pylint: disable=too-many-arguments

from typing import Any


def generate_video_json(
    domain_name: str,
    vidname: str,
    url_slug: str,
    torrentfile: str,
    mp4file: str,
    size_mp4file: int,
    duration: float,
    subtitles: Any,
) -> dict[str, Any]:
    """Generates the video json for the webtorrent player."""
    # schema = "https" if "localhost" not in domain_name else "http"
    # hostname = f"{schema}://{domain_name}"
    data = {
        "note": "This is a sample and should be overriden during the video creation process",
        "name": vidname,
        "urlslug": url_slug,
        "domain": domain_name,
        "webtorrent": {
            "torrent": "https://webtorrent-webseed.onrender.com/indoctrination.mp4.torrent",
            "webseed": "https://webtorrent-webseed.onrender.com/content/indoctrination.mp4",
            "size": 0,
            "duration": duration,
        },
        "desktop": {
            "720": "https://webtorrent-webseed.onrender.com/content/indoctrination.mp4"
        },
        "mobile": "https://webtorrent-webseed.onrender.com/content/indoctrination.mp4",
        "subtitles": subtitles,
        "todo": "Let's also have bitchute: <URL> and rumble <URL>",
    }
    data["webtorrent"]["torrent"] = torrentfile  # type: ignore
    data["webtorrent"]["webseed"] = mp4file  # type: ignore
    data["webtorrent"]["size"] = size_mp4file  # type: ignore
    data["desktop"]["720"] = mp4file  # type: ignore
    data["mobile"] = mp4file  # type: ignore
    return data
