from flask import render_template, redirect, url_for, request, abort
from flask_login import login_required, current_user
from app import app, db
from models import Feed, Episode
from feed_generator import generate_rss_feed
from datetime import datetime
from slugify import slugify

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
        name = request.form['name']
        description = request.form['description']
        url_slug = slugify(name)  # Direct use of slugify function

        feed = Feed(
            name=name,
            description=description,
            url_slug=url_slug,
            user_id=current_user.id
        )
        db.session.add(feed)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('feed_form.html')

@app.route('/feed/<int:feed_id>/episode/new', methods=['GET', 'POST'])
@login_required
def new_episode(feed_id):
    feed = Feed.query.get_or_404(feed_id)
    if feed.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        episode = Episode(
            feed_id=feed_id,
            title=request.form['title'],
            description=request.form['description'],
            audio_url=request.form['audio_url'],
            release_date=datetime.strptime(request.form['release_date'], '%Y-%m-%dT%H:%M'),
            is_recurring=bool(request.form.get('is_recurring'))
        )
        db.session.add(episode)
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('episode_form.html', feed=feed)

@app.route('/feed/<string:url_slug>/rss')
def rss_feed(url_slug):
    feed = Feed.query.filter_by(url_slug=url_slug).first_or_404()
    return generate_rss_feed(feed), {'Content-Type': 'application/xml'}