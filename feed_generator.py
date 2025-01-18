from datetime import datetime
from xml.etree import ElementTree as ET

def generate_rss_feed(feed):
    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')

    channel = ET.SubElement(rss, 'channel')

    # Feed metadata
    title = ET.SubElement(channel, 'title')
    title.text = feed.name

    description = ET.SubElement(channel, 'description')
    description.text = feed.description

    # Add podcast image if available
    if feed.image_url:
        image = ET.SubElement(channel, 'image')
        img_url = ET.SubElement(image, 'url')
        img_url.text = feed.image_url
        img_title = ET.SubElement(image, 'title')
        img_title.text = feed.name

        # Add iTunes image tag
        itunes_image = ET.SubElement(channel, 'itunes:image')
        itunes_image.set('href', feed.image_url)

    # Episodes
    for episode in feed.episodes:
        if episode.release_date <= datetime.utcnow():
            item = ET.SubElement(channel, 'item')

            episode_title = ET.SubElement(item, 'title')
            episode_title.text = episode.title

            episode_desc = ET.SubElement(item, 'description')
            episode_desc.text = episode.description

            pub_date = ET.SubElement(item, 'pubDate')
            pub_date.text = episode.release_date.strftime('%a, %d %b %Y %H:%M:%S GMT')

            enclosure = ET.SubElement(item, 'enclosure')
            enclosure.set('url', episode.audio_url)
            enclosure.set('type', 'audio/mpeg')

    return ET.tostring(rss, encoding='unicode')