from flask import render_template, redirect, url_for, request, abort, flash
from flask_login import login_required, current_user
from app import app, db
from models import Feed, Episode
from feed_generator import generate_rss_feed
from datetime import datetime
from slugify import slugify
import logging

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    feeds = Feed.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', feeds=feeds)

@app.route('/feed/new', methods=['GET', 'POST'])
@login_required
def new_feed():
    if request.method == 'POST':
        try:
            name = request.form['name']
            description = request.form['description']
            image_url = request.form.get('image_url', '').strip()

            # Convert Google Drive or Dropbox URL if present
            if image_url:
                image_url = convert_google_drive_url(image_url)

            base_slug = slugify(name)

            # Ensure unique slug
            counter = 1
            url_slug = base_slug
            while Feed.query.filter_by(url_slug=url_slug).first() is not None:
                url_slug = f"{base_slug}-{counter}"
                counter += 1

            feed = Feed(
                name=name,
                description=description,
                image_url=image_url if image_url else None,
                url_slug=url_slug,
                user_id=current_user.id
            )
            db.session.add(feed)
            db.session.commit()
            logger.info(f"Created new feed: {feed.name} with slug: {feed.url_slug} and image: {feed.image_url}")
            flash('Feed created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Error creating feed: {str(e)}")
            db.session.rollback()
            flash('Error creating feed. Please try again.', 'error')
            return redirect(url_for('new_feed'))

    return render_template('feed_form.html')

@app.route('/feed/<int:feed_id>/episode/new', methods=['GET', 'POST'])
@login_required
def new_episode(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        try:
            audio_url = request.form['audio_url'].strip()
            if audio_url:
                audio_url = convert_audio_url(audio_url)

            episode = Episode(
                feed_id=feed_id,
                title=request.form['title'],
                description=request.form['description'],
                audio_url=audio_url,
                release_date=datetime.strptime(request.form['release_date'], '%Y-%m-%dT%H:%M'),
                is_recurring=bool(request.form.get('is_recurring'))
            )
            db.session.add(episode)
            db.session.commit()
            flash('Episode added successfully!', 'success')
            return redirect(url_for('feed_details', feed_id=feed_id))
        except Exception as e:
            logger.error(f"Error creating episode: {str(e)}")
            db.session.rollback()
            flash('Error adding episode. Please try again.', 'error')

    return render_template('episode_form.html', feed=feed)

@app.route('/feed/<string:url_slug>/rss')
def rss_feed(url_slug):
    try:
        feed = Feed.query.filter_by(url_slug=url_slug).first_or_404()
        return generate_rss_feed(feed), {'Content-Type': 'application/xml'}
    except Exception as e:
        logger.error(f"Error generating RSS feed: {str(e)}")
        abort(500)

@app.route('/feed/<int:feed_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        try:
            feed.name = request.form['name']
            feed.description = request.form['description']
            image_url = request.form.get('image_url', '').strip()

            # Convert Google Drive or Dropbox URL if present
            if image_url:
                image_url = convert_google_drive_url(image_url)

            feed.image_url = image_url if image_url else None
            db.session.commit()
            logger.info(f"Updated feed: {feed.name} with image: {feed.image_url}")
            flash('Feed updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Error updating feed: {str(e)}")
            db.session.rollback()
            flash('Error updating feed. Please try again.', 'error')

    return render_template('feed_form.html', feed=feed)

@app.route('/feed/<int:feed_id>/episode/<int:episode_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_episode(feed_id, episode_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    episode = Episode.query.get_or_404(episode_id)
    if episode.feed_id != feed_id:
        abort(404)

    if request.method == 'POST':
        try:
            episode.title = request.form['title']
            episode.description = request.form['description']

            audio_url = request.form['audio_url'].strip()
            if audio_url:
                audio_url = convert_audio_url(audio_url)
            episode.audio_url = audio_url

            episode.release_date = datetime.strptime(request.form['release_date'], '%Y-%m-%dT%H:%M')
            episode.is_recurring = bool(request.form.get('is_recurring'))

            db.session.commit()
            flash('Episode updated successfully!', 'success')
            return redirect(url_for('feed_details', feed_id=feed_id))
        except Exception as e:
            logger.error(f"Error updating episode: {str(e)}")
            db.session.rollback()
            flash('Error updating episode. Please try again.', 'error')

    return render_template('episode_form.html', feed=feed, episode=episode)

@app.route('/feed/<int:feed_id>/episode/<int:episode_id>/delete', methods=['POST'])
@login_required
def delete_episode(feed_id, episode_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    episode = Episode.query.get_or_404(episode_id)
    if episode.feed_id != feed_id:
        abort(404)

    try:
        db.session.delete(episode)
        db.session.commit()
        flash('Episode deleted successfully!', 'success')
    except Exception as e:
        logger.error(f"Error deleting episode: {str(e)}")
        db.session.rollback()
        flash('Error deleting episode. Please try again.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/feed/<int:feed_id>')
@login_required
def feed_details(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)
    return render_template('feed_details.html', feed=feed)

def convert_google_drive_url(url):
    """Convert Google Drive or Dropbox URL to direct access URL"""
    if not url:
        return url

    if "dropbox.com" in url:
        # Handle Dropbox URLs similar to audio URLs but specific to images
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
        file_id = None

        # Handle different Google Drive URL formats
        if '/file/d/' in url:
            # Format: https://drive.google.com/file/d/FILE_ID/view
            try:
                file_id = url.split('/file/d/')[1].split('/')[0]
            except IndexError:
                logger.error(f"Invalid Google Drive URL format: {url}")
                return url
        elif 'id=' in url:
            # Format: https://drive.google.com/open?id=FILE_ID
            try:
                file_id = url.split('id=')[1].split('&')[0]
            except IndexError:
                logger.error(f"Invalid Google Drive URL format: {url}")
                return url

        if not file_id:
            logger.error(f"Could not extract file ID from URL: {url}")
            return url

        # For images, use lh3.googleusercontent.com for better performance
        if url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            return f"https://lh3.googleusercontent.com/d/{file_id}"
        # For other file types, use the download export
        else:
            return f"https://drive.google.com/uc?export=download&id={file_id}"

    return url


def convert_audio_url(original_link):
    """Convert audio file URLs from Dropbox or Google Drive to direct download links"""
    if not original_link:
        return original_link

    if "dropbox.com" in original_link:
        # Dropbox link reformatting
        # Keep all query parameters except dl=0
        base_url = original_link.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        if "?" in base_url:
            params = base_url.split("?")[1].split("&")
            # Filter out the dl=0 parameter but keep others (rlkey, st, etc)
            filtered_params = [p for p in params if not p.startswith("dl=")]
            if filtered_params:
                return f"{base_url.split('?')[0]}?{'&'.join(filtered_params)}"
            return base_url.split('?')[0]
        return base_url
    elif "drive.google.com" in original_link:
        # Google Drive link reformatting
        try:
            file_id = None
            if '/file/d/' in original_link:
                # Format: https://drive.google.com/file/d/FILE_ID/view
                file_id = original_link.split('/file/d/')[1].split('/')[0]
            elif 'id=' in original_link:
                # Format: https://drive.google.com/open?id=FILE_ID
                file_id = original_link.split('id=')[1].split('&')[0]

            if not file_id:
                logger.error(f"Could not extract file ID from URL: {original_link}")
                return original_link

            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except IndexError:
            logger.error(f"Invalid Google Drive URL format: {original_link}")
            return original_link
    else:
        return original_link

@app.route('/feed/<int:feed_id>/delete', methods=['POST'])
@login_required
def delete_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    try:
        # Delete associated episodes first
        Episode.query.filter_by(feed_id=feed.id).delete()
        db.session.delete(feed)
        db.session.commit()
        flash('Feed deleted successfully!', 'success')
    except Exception as e:
        logger.error(f"Error deleting feed: {str(e)}")
        db.session.rollback()
        flash('Error deleting feed. Please try again.', 'error')

    return redirect(url_for('dashboard'))

@app.route('/test_url', methods=['GET', 'POST'])
def test_url():
    if request.method == 'POST':
        original_url = request.form.get('url', '').strip()
        reformatted_url = convert_audio_url(original_url) if original_url else ''
        return render_template('test_url.html', 
                             original_url=original_url, 
                             reformatted_url=reformatted_url)
    return render_template('test_url.html')