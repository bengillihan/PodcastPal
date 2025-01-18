from flask import render_template, redirect, url_for, request, abort, flash
from flask_login import login_required, current_user
from app import app, db
from models import Feed, Episode
from feed_generator import generate_rss_feed
from datetime import datetime
from slugify import slugify
from utils import convert_url_to_dropbox_direct
import logging
import csv
from io import StringIO
from werkzeug.utils import secure_filename

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

            # Convert Dropbox URL if present
            if image_url:
                image_url = convert_url_to_dropbox_direct(image_url)

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
                audio_url = convert_url_to_dropbox_direct(audio_url)

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

            if image_url:
                image_url = convert_url_to_dropbox_direct(image_url)

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
                audio_url = convert_url_to_dropbox_direct(audio_url)
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

    return redirect(url_for('feed_details', feed_id=feed_id))

@app.route('/feed/<int:feed_id>')
@login_required
def feed_details(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)
    return render_template('feed_details.html', feed=feed)

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
        reformatted_url = convert_url_to_dropbox_direct(original_url) if original_url else ''
        return render_template('test_url.html', 
                             original_url=original_url, 
                             reformatted_url=reformatted_url)
    return render_template('test_url.html')

@app.route('/episode/template/download')
def download_episode_template():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['title', 'description', 'audio_url', 'release_date', 'is_recurring'])
    writer.writerow(['Example Episode', 'Episode description here', 'https://www.dropbox.com/s/example/audio.mp3?dl=0', '2025-01-20 15:30', 'FALSE'])

    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=episode_template.csv'
    }

@app.route('/feed/<int:feed_id>/upload-csv', methods=['POST'])
@login_required
def upload_episodes_csv(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('feed_details', feed_id=feed_id))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('feed_details', feed_id=feed_id))

    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file', 'error')
        return redirect(url_for('feed_details', feed_id=feed_id))

    try:
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        episodes_added = 0
        episodes_failed = 0

        for row in csv_reader:
            try:
                release_date = datetime.strptime(row['release_date'].strip(), '%Y-%m-%d %H:%M')
                is_recurring = row['is_recurring'].strip().upper() == 'TRUE'
                audio_url = convert_url_to_dropbox_direct(row['audio_url'].strip())

                episode = Episode(
                    feed_id=feed_id,
                    title=row['title'].strip(),
                    description=row['description'].strip(),
                    audio_url=audio_url,
                    release_date=release_date,
                    is_recurring=is_recurring
                )
                db.session.add(episode)
                episodes_added += 1

            except Exception as e:
                logger.error(f"Error adding episode from CSV: {str(e)}")
                episodes_failed += 1
                continue

        db.session.commit()

        if episodes_failed > 0:
            flash(f'Added {episodes_added} episodes, {episodes_failed} failed', 'warning')
        else:
            flash(f'Successfully added {episodes_added} episodes', 'success')

    except Exception as e:
        logger.error(f"Error processing CSV file: {str(e)}")
        db.session.rollback()
        flash('Error processing CSV file. Please check the format and try again.', 'error')

    return redirect(url_for('feed_details', feed_id=feed_id))