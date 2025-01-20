from datetime import datetime
from xml.etree import ElementTree as ET
from utils import convert_url_to_dropbox_direct
import urllib.request
import logging

logger = logging.getLogger(__name__)

def get_file_size(url):
    """Get file size in bytes from URL"""
    try:
        response = urllib.request.urlopen(url)
        size = response.headers.get('Content-Length')
        return size if size else "0"
    except Exception as e:
        logger.error(f"Error getting file size for {url}: {str(e)}")
        return "0"

def generate_rss_feed(feed):
    """Generate RSS feed XML for a podcast feed"""
    logger.debug(f"Generating RSS feed for: {feed.name}")
    logger.debug(f"Number of episodes: {len(feed.episodes)}")

    # Create RSS element with all required namespaces
    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
    rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = ET.SubElement(rss, 'channel')

    # Required channel elements
    title = ET.SubElement(channel, 'title')
    title.text = feed.name

    description = ET.SubElement(channel, 'description')
    description.text = feed.description

    # Add website link
    link = ET.SubElement(channel, 'link')
    link.text = f"https://{feed.url_slug}.repl.co"

    # Add language tag
    language = ET.SubElement(channel, 'language')
    language.text = 'en-us'

    # Add copyright notice
    copyright_text = ET.SubElement(channel, 'copyright')
    copyright_text.text = f'Copyright © {datetime.now().year} {feed.name}'

    # Add iTunes specific tags
    itunes_author = ET.SubElement(channel, 'itunes:author')
    itunes_author.text = feed.owner.name

    itunes_category = ET.SubElement(channel, 'itunes:category')
    itunes_category.set('text', 'Arts')

    # Add podcast image if available
    if feed.image_url:
        direct_image_url = convert_url_to_dropbox_direct(feed.image_url)
        itunes_image = ET.SubElement(channel, 'itunes:image')
        itunes_image.set('href', direct_image_url)

    # Atom feed link
    atom_link = ET.SubElement(channel, 'atom:link')
    atom_link.set('href', f"https://{feed.url_slug}.repl.co/feed.xml")
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    # Episodes
    for episode in feed.episodes:
        logger.debug(f"Processing episode: {episode.title}")
        if episode.release_date <= datetime.utcnow():
            item = ET.SubElement(channel, 'item')

            episode_title = ET.SubElement(item, 'title')
            episode_title.text = episode.title

            episode_desc = ET.SubElement(item, 'description')
            episode_desc.text = episode.description

            # Add iTunes specific episode description
            itunes_summary = ET.SubElement(item, 'itunes:summary')
            itunes_summary.text = episode.description

            pub_date = ET.SubElement(item, 'pubDate')
            pub_date.text = episode.release_date.strftime('%a, %d %b %Y %H:%M:%S GMT')

            # Add guid for episode
            guid = ET.SubElement(item, 'guid')
            guid.text = f"episode_{episode.id}"
            guid.set('isPermaLink', 'false')

            # Convert audio URL to direct format
            direct_audio_url = convert_url_to_dropbox_direct(episode.audio_url)
            logger.debug(f"Direct audio URL: {direct_audio_url}")

            # Get file size for enclosure tag
            file_size = get_file_size(direct_audio_url)
            logger.debug(f"File size: {file_size}")

            enclosure = ET.SubElement(item, 'enclosure')
            enclosure.set('url', direct_audio_url)
            enclosure.set('type', 'audio/mpeg')
            enclosure.set('length', file_size)

            # Add duration if available
            if hasattr(episode, 'duration'):
                itunes_duration = ET.SubElement(item, 'itunes:duration')
                itunes_duration.text = str(episode.duration)

    result = ET.tostring(rss, encoding='unicode', xml_declaration=True)
    logger.debug(f"Generated RSS feed length: {len(result)}")
    return result