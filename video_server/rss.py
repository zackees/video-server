"""
Generates an RSS feed from the video library.
"""

from peewee import ModelSelect  # type: ignore
from video_server.models import Video


def _rss_item(vid: Video) -> str:
    views = "0" if vid.views == "?" else vid.views

    def cdata(inner: str) -> str:
        return f"<![CDATA[{inner}]]>"
        # return instr

    description = cdata(vid.description)
    title = cdata(vid.title)
    channel_name = cdata("TODO: CHANNEL NAME")
    return f"""    <item>
      <title>{title}</title>
      <pubDate>{vid.published}</pubDate>
      <lastupdated>{vid.updated}</lastupdated>
      <link>{vid.url}</link>
      <channel_url></channel_url>
      <channel_name>{channel_name}</channel_name>
      <description>{description}</description>
      <thumbnail>{vid.url}/thumbnail.jpg</thumbnail>
      <dc:creator></dc:creator>
      <duration>{vid.duration}</duration>
      <views>{views}</views>
      <host></host>
      <iframe>{vid.iframe}</iframe>
    </item>
"""


def rss(channel_name: str) -> str:
    """
    Returns a list of RSS items as a string.
    """
    out = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
"""
    out += "  <channel>\n"
    out += f"    <title>{channel_name}</title>"

    vids: ModelSelect = Video.select().order_by(Video.published.desc())
    for video in vids:  # pylint: disable=not-an-iterable
        out += _rss_item(video)
    out += "  </channel>\n"
    out += "</rss>"
    return out
