from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from utils import convert_url_to_dropbox_direct
import urllib.request
import urllib.error
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def get_file_size(url):
    """Get file size in bytes from URL"""
    try:
        response = urllib.request.urlopen(url)
        size = response.headers.get('Content-Length')
        return size if size else "0"
    except urllib.error.URLError as url_err:
        logger.error(f"URLError while getting file size for {url}: {url_err.reason}")
        return "0"
    except urllib.error.HTTPError as http_err:
        logger.error(f"HTTPError {http_err.code} while getting file size for {url}: {http_err.reason}")
        return "0"
    except ValueError as val_err:
        logger.error(f"Invalid URL format for {url}: {val_err}")
        return "0"
    except Exception as e:
        logger.error(f"Unexpected error while getting file size for {url}: {str(e)}", exc_info=True)
        return "0"

def fetch_file_size_concurrent(episodes):
    """Fetch file sizes concurrently for multiple episodes"""
    def get_episode_size(episode):
        try:
            direct_url = convert_url_to_dropbox_direct(episode.audio_url)
            return episode, get_file_size(direct_url)
        except Exception as e:
            logger.error(f"Error getting size for episode {getattr(episode, 'title', 'Unknown')}: {e}")
            return episode, "0"

    with ThreadPoolExecutor(max_workers=5) as executor:
        return list(executor.map(get_episode_size, episodes))

def generate_rss_feed(feed):
    """Generate RSS feed XML for a podcast feed"""
    try:
        logger.debug(f"Starting RSS feed generation for: {feed.name}")
        logger.debug(f"Initial episode count: {len(feed.episodes)}")

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

        # Add website link only if specified
        if feed.website_url:
            link = ET.SubElement(channel, 'link')
            link.text = feed.website_url

        # Add language tag
        language = ET.SubElement(channel, 'language')
        language.text = 'en-us'

        # Add copyright notice
        copyright_text = ET.SubElement(channel, 'copyright')
        copyright_text.text = f'Copyright © {datetime.now().year} {feed.name}'

        try:
            # Add iTunes specific tags
            itunes_author = ET.SubElement(channel, 'itunes:author')
            itunes_author.text = feed.owner.name

            itunes_category = ET.SubElement(channel, 'itunes:category')
            itunes_category.set('text', 'Arts')
        except AttributeError as attr_err:
            logger.error(f"Missing required feed attributes: {attr_err}")
            raise ValueError(f"Invalid feed configuration: {attr_err}")

        # Add podcast image if available
        if feed.image_url:
            try:
                direct_image_url = convert_url_to_dropbox_direct(feed.image_url)
                itunes_image = ET.SubElement(channel, 'itunes:image')
                itunes_image.set('href', direct_image_url)
            except Exception as img_err:
                logger.error(f"Error processing image URL {feed.image_url}: {img_err}")

        # Atom feed link
        atom_link = ET.SubElement(channel, 'atom:link')
        atom_link.set('href', f"https://{feed.owner.email.split('@')[0]}-{feed.url_slug}.repl.dev/feed.xml")
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')

        # Handle episodes with recurring logic
        current_time = datetime.utcnow()
        updated_episodes = []

        for ep in feed.episodes:
            try:
                if hasattr(ep, 'is_recurring') and ep.is_recurring:
                    # Check if the episode is more than 60 days past the release date
                    days_since_release = (current_time - ep.release_date).days

                    # Move the episode to the next year if 60+ days have passed since the last release
                    while days_since_release > 60:
                        # Move the release date to the next year
                        try:
                            ep.release_date = ep.release_date.replace(year=ep.release_date.year + 1)
                        except ValueError:
                            # Handle leap year issue for Feb 29 by setting to Feb 28
                            logger.warning(f"Adjusting leap year date for episode {ep.title}")
                            ep.release_date = ep.release_date.replace(month=2, day=28, year=ep.release_date.year + 1)

                        # Recalculate the days since release
                        days_since_release = (current_time - ep.release_date).days

                # Only include episodes that should be visible (already released)
                if ep.release_date <= current_time:
                    updated_episodes.append(ep)
            except AttributeError as attr_err:
                logger.error(f"Invalid episode data for {getattr(ep, 'title', 'Unknown')}: {attr_err}")
                continue

        # Sort the episodes by the (possibly updated) release date
        sorted_episodes = sorted(updated_episodes, key=lambda x: x.release_date, reverse=True)

        logger.debug(f"Processing {len(updated_episodes)} available episodes")

        # Fetch all file sizes concurrently
        episode_sizes = dict(fetch_file_size_concurrent(sorted_episodes))

        # Episodes
        for episode in sorted_episodes:
            try:
                logger.debug(f"Processing episode: {episode.title}")
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

                # Convert audio URL to direct format if it's a Dropbox URL
                direct_audio_url = convert_url_to_dropbox_direct(episode.audio_url)
                logger.debug(f"Processing audio URL for {episode.title}: {direct_audio_url}")

                # Get file size from pre-fetched sizes
                file_size = episode_sizes.get(episode, "0")
                logger.debug(f"File size for {episode.title}: {file_size}")

                enclosure = ET.SubElement(item, 'enclosure')
                enclosure.set('url', direct_audio_url)
                enclosure.set('type', 'audio/mpeg')
                enclosure.set('length', file_size)
            except AttributeError as ep_err:
                logger.error(f"Missing required episode attributes: {ep_err}")
                continue
            except Exception as item_err:
                logger.error(f"Error processing episode {getattr(episode, 'title', 'Unknown')}: {item_err}", exc_info=True)
                continue

        result = ET.tostring(rss, encoding='unicode', xml_declaration=True)
        logger.debug(f"Successfully generated RSS feed with length: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Critical error generating RSS feed: {str(e)}", exc_info=True)
        raise