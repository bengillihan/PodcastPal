from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from utils import convert_url_to_dropbox_direct
import urllib.request
import urllib.error
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import pytz

logger = logging.getLogger(__name__)

_feed_cache = {}
CACHE_DURATION = timedelta(hours=12)  # Changed from 4 to 12 hours
TIMEZONE = pytz.timezone('America/Los_Angeles')  # Changed to Pacific Time

def should_update_cache(feed_id):
    """Check if the cache for this feed needs to be updated"""
    if feed_id not in _feed_cache:
        logger.info(f"No cache entry found for feed_id: {feed_id}")
        return True
    cache_time, _ = _feed_cache[feed_id]
    is_expired = datetime.now(TIMEZONE) - cache_time > CACHE_DURATION
    if is_expired:
        logger.info(f"Cache expired for feed_id: {feed_id}. Last update: {cache_time}")
    return is_expired

def get_cached_feed(feed_id):
    """Get cached feed content if available and not expired"""
    if feed_id in _feed_cache:
        cache_time, content = _feed_cache[feed_id]
        if datetime.now(TIMEZONE) - cache_time <= CACHE_DURATION:
            logger.info(f"Returning cached RSS feed for feed_id: {feed_id}. Cache age: {datetime.now(TIMEZONE) - cache_time}")
            return content
        logger.info(f"Cache expired for feed_id: {feed_id}. Last update: {cache_time}")
    return None

def cache_feed(feed_id, content):
    """Cache feed content with current timestamp"""
    current_time = datetime.now(TIMEZONE)
    _feed_cache[feed_id] = (current_time, content)
    logger.info(f"Updated RSS feed cache for feed_id: {feed_id} at {current_time}")

def get_file_size(url):
    """Get file size in bytes from URL"""
    try:
        response = urllib.request.urlopen(url)
        size = response.headers.get('Content-Length')
        if size:
            from models import DropboxTraffic
            logger.info(f"Logging traffic for URL: {url} with size: {size} bytes")
            DropboxTraffic.log_request(int(size))
            return size
        logger.warning(f"No Content-Length header found for URL: {url}")
        return "0"
    except urllib.error.URLError as url_err:
        logger.error(f"URLError while getting file size for {url}: {url_err.reason}")
        return "0"
    except Exception as e:
        logger.error(f"Failed to get file size for {url}: {str(e)}", exc_info=True)
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
    cached_content = get_cached_feed(feed.id)
    if cached_content:
        return cached_content

    try:
        logger.info(f"Starting RSS feed generation for: {feed.name}")
        logger.debug(f"Initial episode count: {len(feed.episodes)}")

        rss = ET.Element('rss', version='2.0')
        rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
        rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
        rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

        channel = ET.SubElement(rss, 'channel')

        title = ET.SubElement(channel, 'title')
        title.text = feed.name

        description = ET.SubElement(channel, 'description')
        description.text = feed.description

        if feed.website_url:
            link = ET.SubElement(channel, 'link')
            link.text = feed.website_url

        language = ET.SubElement(channel, 'language')
        language.text = 'en-us'

        copyright_text = ET.SubElement(channel, 'copyright')
        copyright_text.text = f'Copyright © {datetime.now(TIMEZONE).year} {feed.name}'

        try:
            itunes_author = ET.SubElement(channel, 'itunes:author')
            itunes_author.text = feed.owner.name

            itunes_category = ET.SubElement(channel, 'itunes:category')
            itunes_category.set('text', 'Arts')
        except AttributeError as attr_err:
            logger.error(f"Missing required feed attributes: {attr_err}")
            raise ValueError(f"Invalid feed configuration: {attr_err}")

        if feed.image_url:
            try:
                direct_image_url = convert_url_to_dropbox_direct(feed.image_url)
                itunes_image = ET.SubElement(channel, 'itunes:image')
                itunes_image.set('href', direct_image_url)
                logger.info(f"Successfully added podcast image for feed '{feed.name}'")
            except Exception as img_err:
                logger.warning(f"Failed to process image URL {feed.image_url}, continuing without image: {img_err}")

        atom_link = ET.SubElement(channel, 'atom:link')
        atom_link.set('href', f"https://{feed.owner.email.split('@')[0]}-{feed.url_slug}.repl.dev/feed.xml")
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')

        current_time = datetime.now(TIMEZONE)
        updated_episodes = []

        for ep in feed.episodes:
            try:
                # Make release_date timezone-aware if it isn't already
                ep_release_date = ep.release_date.replace(tzinfo=TIMEZONE) if ep.release_date.tzinfo is None else ep.release_date

                if hasattr(ep, 'is_recurring') and ep.is_recurring:
                    days_since_release = (current_time - ep_release_date).days
                    max_iterations = 5
                    iterations = 0
                    while days_since_release > 60 and iterations < max_iterations:
                        try:
                            ep_release_date = ep_release_date.replace(year=ep_release_date.year + 1)
                        except ValueError:
                            logger.warning(f"Adjusting leap year date for episode '{ep.title}'")
                            ep_release_date = ep_release_date.replace(month=2, day=28, year=ep_release_date.year + 1)
                        days_since_release = (current_time - ep_release_date).days
                        iterations += 1
                    if iterations == max_iterations:
                        logger.warning(f"Episode '{ep.title}' exceeded max recurrence adjustments")

                # Update episode's release_date with the potentially adjusted timezone-aware date
                ep.release_date = ep_release_date

                if ep_release_date <= current_time:
                    updated_episodes.append(ep)
            except AttributeError as attr_err:
                logger.error(f"Invalid episode data for {getattr(ep, 'title', 'Unknown')}: {attr_err}")
                continue

        sorted_episodes = sorted(updated_episodes, key=lambda x: x.release_date, reverse=True)

        logger.info(f"Processing {len(updated_episodes)} available episodes for feed '{feed.name}'")

        episode_sizes = dict(fetch_file_size_concurrent(sorted_episodes))

        for episode in sorted_episodes:
            try:
                logger.debug(f"Processing episode: {episode.title}")
                item = ET.SubElement(channel, 'item')

                episode_title = ET.SubElement(item, 'title')
                episode_title.text = episode.title

                episode_desc = ET.SubElement(item, 'description')
                episode_desc.text = episode.description

                itunes_summary = ET.SubElement(item, 'itunes:summary')
                itunes_summary.text = episode.description

                pub_date = ET.SubElement(item, 'pubDate')
                pub_date.text = episode.release_date.strftime('%a, %d %b %Y %H:%M:%S %z')

                guid = ET.SubElement(item, 'guid')
                guid.text = f"episode_{episode.id}_{episode.release_date.year}"
                guid.set('isPermaLink', 'false')

                try:
                    direct_audio_url = convert_url_to_dropbox_direct(episode.audio_url)
                    logger.debug(f"Processing audio URL for {episode.title}: {direct_audio_url}")

                    file_size = episode_sizes.get(episode, "0")
                    logger.debug(f"File size for {episode.title}: {file_size}")

                    enclosure = ET.SubElement(item, 'enclosure')
                    enclosure.set('url', direct_audio_url)
                    enclosure.set('type', 'audio/mpeg')
                    enclosure.set('length', file_size)
                except (AttributeError, ValueError, urllib.error.URLError) as e:
                    logger.error(f"Error processing enclosure for episode '{getattr(episode, 'title', 'Unknown')}': {e}")
                    continue

            except AttributeError as ep_err:
                logger.error(f"Missing required episode attributes: {ep_err}")
                continue
            except Exception as item_err:
                logger.error(f"Error processing episode {getattr(episode, 'title', 'Unknown')}: {item_err}", exc_info=True)
                continue

        result = ET.tostring(rss, encoding='unicode', xml_declaration=True)
        logger.info(f"Successfully generated RSS feed for '{feed.name}' with {len(sorted_episodes)} episodes")

        cache_feed(feed.id, result)
        return result
    except Exception as e:
        logger.error(f"Critical error generating RSS feed: {str(e)}", exc_info=True)
        raise