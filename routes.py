import pytz
from flask import render_template, redirect, url_for, request, abort, flash
from flask_login import login_required, current_user
from app import app, db
from models import Feed, Episode
from feed_generator import generate_rss_feed, _feed_cache, TIMEZONE, get_next_refresh_time
from datetime import datetime
from slugify import slugify
from utils import convert_url_to_dropbox_direct
from cache_manager import cache_result, CacheManager, RSSCacheManager
from extended_cache import long_term_cache, UltraLongCache
import logging
import csv
from io import StringIO
from werkzeug.utils import secure_filename
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload, selectinload

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
@long_term_cache(hours=2)  # Cache dashboard for 2 hours per user
def dashboard():
    from connection_manager import ConnectionManager
    
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of feeds per page
    
    # Use efficient session context manager
    with ConnectionManager.efficient_session():
        # Single optimized query with subquery for episode counts
        from sqlalchemy import select, func as sql_func
        
        # Create subquery for episode counts
        episode_count_subquery = db.session.query(
            Episode.feed_id,
            sql_func.count(Episode.id).label('episode_count')
        ).group_by(Episode.feed_id).subquery()
        
        # Main query with left join to get feeds and their episode counts
        feeds_query = db.session.query(Feed, episode_count_subquery.c.episode_count) \
            .outerjoin(episode_count_subquery, Feed.id == episode_count_subquery.c.feed_id) \
            .filter(Feed.user_id == current_user.id) \
            .order_by(Feed.created_at.desc())
        
        # Apply pagination
        pagination = feeds_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Extract feeds and attach episode counts
        feeds = []
        for feed, episode_count in pagination.items:
            feed.episode_count = episode_count or 0
            feeds.append(feed)
        
        # Update pagination.items to contain just feeds
        pagination.items = feeds
    
    return render_template('dashboard.html', feeds=feeds, pagination=pagination)

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

            # Parse the date in Pacific Time
            release_date = datetime.strptime(request.form['release_date'], '%Y-%m-%dT%H:%M')
            release_date = TIMEZONE.localize(release_date)

            episode = Episode(
                feed_id=feed_id,
                title=request.form['title'],
                description=request.form['description'],
                audio_url=audio_url,
                release_date=release_date,
                is_recurring=bool(request.form.get('is_recurring'))
            )
            db.session.add(episode)

            if feed_id in _feed_cache:
                del _feed_cache[feed_id]
                logger.info(f"Cleared RSS feed cache for feed_id: {feed_id}")

            db.session.commit()
            flash('Episode added successfully!', 'success')
            return redirect(url_for('feed_details', feed_id=feed_id))
        except Exception as e:
            logger.error(f"Error creating episode: {str(e)}")
            db.session.rollback()
            flash('Error adding episode. Please try again.', 'error')

    return render_template('episode_form.html', feed=feed)

@app.route('/feed/<string:url_slug>/rss')
@cache_result(ttl_minutes=1440)  # Cache RSS responses for 24 hours to minimize requests
def rss_feed(url_slug):
    from connection_manager import ConnectionManager
    
    try:
        with ConnectionManager.efficient_session():
            # Single query to get feed by slug
            feed = Feed.query.filter_by(url_slug=url_slug).first_or_404()
            
            # RSS feed request logged for analytics
            
            # Check RSS cache first
            cached_xml = RSSCacheManager.get_feed_cache(feed.id)
            if cached_xml:
                xml_content = cached_xml
            else:
                xml_content = generate_rss_feed(feed)
                RSSCacheManager.set_feed_cache(feed.id, xml_content)
        
        response = app.response_class(
            xml_content,
            mimetype='application/rss+xml'
        )
        
        return response
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

            # Clear the cache when feed is updated
            RSSCacheManager.invalidate_feed(feed_id)
            if feed_id in _feed_cache:
                del _feed_cache[feed_id]
                logger.info(f"Cleared RSS feed cache for feed_id: {feed_id}")

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
    # Single query to verify ownership and get episode
    episode = Episode.query.join(Feed).filter(
        Episode.id == episode_id,
        Episode.feed_id == feed_id,
        Feed.user_id == current_user.id
    ).first_or_404()

    try:
        db.session.delete(episode)
        
        # Clear RSS cache for this feed
        RSSCacheManager.invalidate_feed(feed_id)
        if feed_id in _feed_cache:
            del _feed_cache[feed_id]
            logger.info(f"Cleared RSS feed cache for feed_id: {feed_id}")
        
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
    from connection_manager import ConnectionManager
    
    with ConnectionManager.efficient_session():
        # Single query to get feed and verify ownership
        feed = Feed.query.filter_by(id=feed_id, user_id=current_user.id).first_or_404()
            
        # Add pagination for episodes
        page = request.args.get('page', 1, type=int)
        per_page = 15  # Number of episodes per page
        
        # Get episodes with pagination - using single query with all needed data
        episodes_pagination = Episode.query.filter_by(feed_id=feed_id) \
                                   .order_by(Episode.release_date.desc()) \
                                   .paginate(page=page, per_page=per_page, error_out=False)
        
        episodes = episodes_pagination.items
    
    return render_template('feed_details.html', 
                         feed=feed, 
                         episodes=episodes,
                         pagination=episodes_pagination,
                         _feed_cache=_feed_cache,
                         now=datetime.now(TIMEZONE),
                         TIMEZONE=TIMEZONE,
                         get_next_refresh_time=get_next_refresh_time)

@app.route('/feed/<int:feed_id>/delete', methods=['POST'])
@login_required
def delete_feed(feed_id):
    # Verify ownership with single query
    feed = Feed.query.filter_by(id=feed_id, user_id=current_user.id).first_or_404()

    try:
        # Use bulk delete for episodes (more efficient than individual deletes)
        Episode.query.filter_by(feed_id=feed.id).delete()
        
        # Clear RSS cache before deleting feed
        RSSCacheManager.invalidate_feed(feed_id)
        if feed_id in _feed_cache:
            del _feed_cache[feed_id]
            logger.info(f"Cleared RSS feed cache for feed_id: {feed_id}")
        
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
    writer.writerow(['Example Episode', 'Episode description here', 'https://www.dropbox.com/s/example/audio.mp3?dl=0', '2024-01-20 15:30', 'FALSE'])
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
        # Try multiple encodings to handle different CSV file formats
        file_content = file.stream.read()
        encodings = ['utf-8', 'latin-1', 'windows-1252', 'iso-8859-1']
        
        # Try each encoding until one works
        best_encoding = None
        for encoding in encodings:
            try:
                decoded_content = file_content.decode(encoding)
                stream = StringIO(decoded_content, newline=None)
                # Test if we can read it as CSV
                test_reader = csv.DictReader(stream)
                # Read one row to test if it's valid
                next(test_reader, None)
                # Found a working encoding
                best_encoding = encoding
                logger.info(f"Successfully decoded CSV with {encoding} encoding")
                break
            except UnicodeDecodeError:
                logger.debug(f"Failed to decode with {encoding}, trying next encoding")
                continue
            except Exception as e:
                logger.debug(f"Error with {encoding}: {str(e)}")
                continue
        
        if best_encoding:
            # Process the file with the best encoding found
            try:
                stream = StringIO(file_content.decode(best_encoding, errors='replace'), newline=None)
                csv_reader = csv.DictReader(stream)
            except Exception as e:
                logger.error(f"Error creating CSV reader with {best_encoding}: {str(e)}")
                raise
        else:
            # If no encoding worked completely, try error-replacement mode with UTF-8
            logger.warning("No perfect encoding found, using UTF-8 with replacement")
            stream = StringIO(file_content.decode('utf-8', errors='replace'), newline=None)
            csv_reader = csv.DictReader(stream)

        episodes_added = 0
        episodes_failed = 0

        for row in csv_reader:
            try:
                # Try multiple date formats
                date_str = row['release_date'].strip()
                release_date = None
                date_formats = ['%Y-%m-%d %H:%M', '%m/%d/%y %H:%M', '%m/%d/%Y %H:%M']

                for date_format in date_formats:
                    try:
                        release_date = datetime.strptime(date_str, date_format)
                        break
                    except ValueError:
                        continue

                if release_date is None:
                    raise ValueError(f"Could not parse date: {date_str}")

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

# Add new route for URL regeneration
@app.route('/feed/<int:feed_id>/regenerate-url', methods=['POST'])
@login_required
def regenerate_feed_url(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    try:
        new_slug = feed.regenerate_url_slug()
        flash('Feed URL has been regenerated successfully!', 'success')
    except Exception as e:
        logger.error(f"Error regenerating feed URL: {str(e)}")
        db.session.rollback()
        flash('Error regenerating feed URL. Please try again.', 'error')

    return redirect(url_for('feed_details', feed_id=feed_id))

# Dropbox traffic route removed - traffic analytics no longer tracked

@app.route('/feed/<int:feed_id>/refresh', methods=['POST'])
@login_required
def refresh_feed(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    try:
        # Force clear the cache for this feed (manual refresh)
        if feed_id in _feed_cache:
            del _feed_cache[feed_id]
            logger.info(f"Manually cleared RSS feed cache for feed_id: {feed_id}")

        # Force regenerate feed content by bypassing cache check
        from feed_generator import generate_rss_feed_force
        generate_rss_feed_force(feed)
        flash('Feed refreshed successfully! Changes will be visible immediately.', 'success')
    except Exception as e:
        logger.error(f"Error refreshing feed: {str(e)}")
        flash('Error refreshing feed. Please try again.', 'error')

    return redirect(url_for('feed_details', feed_id=feed_id))


@app.route('/feed/<int:feed_id>/export')
@login_required
def export_episodes(feed_id):
    """Export feed episodes to CSV"""
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    try:
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['title', 'description', 'audio_url', 'release_date', 'is_recurring'])

        # Write episodes
        for episode in feed.episodes:
            writer.writerow([
                episode.title,
                episode.description,
                episode.audio_url,
                episode.release_date.strftime('%Y-%m-%d %H:%M'),
                'TRUE' if episode.is_recurring else 'FALSE'
            ])

        # Prepare the response
        output.seek(0)
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename={feed.url_slug}_episodes.csv'
        }
    except Exception as e:
        logger.error(f"Error exporting episodes: {str(e)}")
        flash('Error exporting episodes. Please try again.', 'error')
        return redirect(url_for('feed_details', feed_id=feed_id))

@app.route('/search', methods=['GET'])
@login_required
def search_episodes():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of search results per page
    
    if query:
        # Search through episodes in user's feeds with pagination
        search_query = (Episode.query
                      .join(Feed)
                      .filter(Feed.user_id == current_user.id)
                      .filter(or_(
                          Episode.title.ilike(f'%{query}%'),
                          Episode.description.ilike(f'%{query}%')
                      ))
                      .order_by(Episode.release_date.desc()))
        
        # Apply pagination
        pagination = search_query.paginate(page=page, per_page=per_page, error_out=False)
        results = pagination.items
        
        logger.info(f"Search query '{query}' returned {pagination.total} total results, showing page {page}")
        
        return render_template('search.html', query=query, results=results, pagination=pagination)
    
    # If no query, just show the empty search page
    return render_template('search.html', query='', results=[])

@app.route('/ping-status')
def ping_status():
    """Simple monitoring route to check database ping status"""
    from database_ping import database_pinger
    from flask import jsonify
    
    try:
        status = database_pinger.get_last_ping_status()
        if status:
            return jsonify({
                'status': 'active',
                'last_ping': status['last_ping'].isoformat() if status['last_ping'] else None,
                'ping_result': status['status'],
                'message': 'Database ping service is running'
            })
        else:
            return jsonify({
                'status': 'running',
                'message': 'Database ping service is active (no ping history yet)'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Could not check ping status: {str(e)}'
        }), 500