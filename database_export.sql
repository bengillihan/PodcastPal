-- PostgreSQL Database Export
-- Generated on: 2025-06-24
-- Database: PodcastPal

-- Drop existing tables if they exist
DROP TABLE IF EXISTS dropbox_traffic CASCADE;
DROP TABLE IF EXISTS episode CASCADE;
DROP TABLE IF EXISTS feed CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

-- Create user table
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(100) UNIQUE,
    email VARCHAR(120) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL
);

-- Create feed table
CREATE TABLE feed (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    image_url VARCHAR(500),
    url_slug VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    website_url VARCHAR(500)
);

-- Create episode table
CREATE TABLE episode (
    id SERIAL PRIMARY KEY,
    feed_id INTEGER NOT NULL REFERENCES feed(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    audio_url VARCHAR(500) NOT NULL,
    release_date TIMESTAMP NOT NULL,
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create dropbox_traffic table
CREATE TABLE dropbox_traffic (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    request_count INTEGER DEFAULT 0,
    total_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX ix_feed_user_id ON feed(user_id);
CREATE INDEX ix_feed_url_slug ON feed(url_slug);
CREATE INDEX ix_feed_user_created ON feed(user_id, created_at);
CREATE INDEX ix_episode_feed_id ON episode(feed_id);
CREATE INDEX ix_episode_release_date ON episode(release_date);
CREATE INDEX ix_episode_feed_date ON episode(feed_id, release_date);

-- Insert user data
INSERT INTO "user" (id, google_id, email, name) VALUES
(1, '114279595668988786398', 'bdgillihan@gmail.com', 'Ben Gillihan'),
(2, '111738835691840252351', 'sean33167@gmail.com', 'sean mcclelland');

-- Insert feed data
INSERT INTO feed (id, user_id, name, description, image_url, url_slug, created_at, website_url) VALUES
(3, 1, 'Business Books', 'Business Books to Review', 'https://dl.dropboxusercontent.com/scl/fi/falsou6zs3ofm88pfpmhs/BusinessBooks.jpg?rlkey=47ywrkqlxt7nn2n0lnnrb5rro&st=xn4jp7jt', 'business-books', '2025-01-19 03:35:06.177851', NULL),
(4, 1, 'New Testament', 'New Testament NotebookLM Summaries by Week. Chronological', 'https://dl.dropboxusercontent.com/scl/fi/n2p4bfq3xlt5r7a5i7an6/Bible.jpg?rlkey=g2oqgddj0jf108iho5jgv4h70&st=o00eu5gy', 'new-testament-94cxu9', '2025-01-19 04:18:21.56221', NULL),
(5, 1, 'Books Summaries', 'NotebookLM AI Summaries of Books', 'https://dl.dropboxusercontent.com/scl/fi/9yfoymiucbwjuu8l8gn3y/Timeless-Summaries.jpg?rlkey=jus7y1fagp7j6pqbq0sat0teb&st=cbzxzb0z', 'books-summaries-uqiz89', '2025-01-20 02:38:14.524136', NULL),
(6, 1, 'Other CCFW/Awana ', 'Other NotebookLM Summaries', 'https://dl.dropboxusercontent.com/scl/fi/xtg4izc9il8vkcvdctrjz/Christ_Taking_Leave_of_the_Apostles.jpg?rlkey=8dbg1yz2k2ryd6r93crcbrxmc&st=0qls7vjq', 'other-ccfw-awana', '2025-01-22 23:37:03.898433', NULL),
(7, 1, 'Other Summaries', 'Random other summaries', NULL, 'other-summaries', '2025-01-31 15:14:21.025044', NULL),
(8, 1, 'Daily Drucker', 'Daily Drucker with Commentary', 'https://dl.dropboxusercontent.com/scl/fi/1pkqawzb2m4ivdsyj6trz/daily-drucker.jpg?rlkey=k542eewitag8kewptlbihesif&st=3fly8lel', 'daily-drucker', '2025-02-08 19:51:21.019652', NULL),
(9, 1, 'New Testament Chapters', 'New Testament Chapters', 'https://dl.dropboxusercontent.com/scl/fi/cgpzdrn6lwdh6yxiit06s/NT-Image.jpg?rlkey=1mypu6w3kj0oer5dvf2ye3tpa&st=55y14pbo', 'new-testament-chapters-xkc04a', '2025-02-09 03:28:40.942523', NULL),
(10, 1, 'Daily Tozer', 'Daily AW Tozer Meditations', 'https://dl.dropboxusercontent.com/scl/fi/71mao2b59pz6gsnomt4os/Tozer.jpeg?rlkey=928jdgwmrvtzgaebjgmazq444&st=824g2t2m', 'daily-tozer-nj2dyy', '2025-02-14 04:00:39.265555', NULL),
(11, 1, 'Hymns and Songs', 'Hymns and Songs', 'https://dl.dropboxusercontent.com/scl/fi/i7sfc896gaf4etm1rovp8/hymnal.jpg?rlkey=ogl0qaov132v6f8og6ovm2m86&st=31xceose', 'hymns-and-songs', '2025-02-23 15:21:09.473719', NULL),
(12, 1, 'Bible Biographies', 'Bible Biographies', 'https://dl.dropboxusercontent.com/scl/fi/xbw8362ikjmnrxehx0q41/images.jpeg?rlkey=7k3xv3xkz1z15xuv1lx9u5w58&st=bqkw1vtp', 'bible-biographies-lupyq5', '2025-03-17 03:20:47.337944', NULL),
(13, 1, 'Daily Doctrine', 'Daily Doctrine From the Book by Kevin DeYoung', 'https://dl.dropboxusercontent.com/scl/fi/qxpsdlxrz50xtdijttupc/daily-doctrine.jpg?rlkey=aq36y1u9fpklg06i6i11fmht3&st=5nb07hcr', 'daily-doctrine', '2025-04-22 21:53:45.744382', NULL);

-- Insert episode data (first 20 episodes due to size - showing pattern)
INSERT INTO episode (id, feed_id, title, description, audio_url, release_date, is_recurring, created_at) VALUES
(5, 3, 'The Effective Executive', 'Peter Drucker''s The Effective Executive: The Definitive Guide to Getting the Right Things Done  Summary by NoteBookLM', 'https://dl.dropboxusercontent.com/scl/fi/ofhha504esryjjabxczot/The-Effective-Executive.mp3?rlkey=7ld02vpwqx39notcqlh6411k3&st=tie01n2j', '2025-01-02 00:00:00', true, '2025-01-19 03:42:24.211241'),
(6, 3, 'Atomic Habits', 'James Clear''s Atomic Habits: An Easy & Proven Way to Build Good Habits & Break Bad Ones Summary by NotebookLM', 'https://dl.dropboxusercontent.com/scl/fi/5jcq1boig1inzcb0tplxq/Atomic-Habits.mp3?rlkey=aprh4xx4jpo2gpiydpjncvd67&st=36iylzk4', '2025-01-09 00:00:00', true, '2025-01-19 03:42:24.211246'),
(7, 3, 'The Goal', 'Eliyahu M. Goldratt''s The Goal: A Process of Ongoing Improvement Summary by NotebookLM', 'https://dl.dropboxusercontent.com/scl/fi/bebqvyaveneuq5n4jh852/The-Goal_-A-Process-of-Ongoing-Improvement.mp3?rlkey=nqdebqrezn7uejxcja68i6mtm&st=951uh982', '2025-01-16 00:00:00', true, '2025-01-19 03:42:24.211249'),
(8, 4, 'New Testament Week 1', 'Luke 1; John 1:1-14; Matthew 1; Luke 2:1-38; Matthew 2; Luke 2:39-52', 'https://dl.dropboxusercontent.com/scl/fi/ralc9p3zzqg4t065pfc88/NT-1.mp3?rlkey=oj0w13fa83scqspxrlypaskbf&st=i91r1vwj', '2025-01-08 00:00:00', true, '2025-01-19 04:26:49.087441'),
(9, 4, 'New Testament Week 2', 'Matthew 3; Mark 1; Luke 3; Matthew 4; Luke 4-5; John 1:15-51; John 2-4', 'https://dl.dropboxusercontent.com/scl/fi/pya41stmfui2uzzoaio3x/NT-2.mp3?rlkey=6w65y3zu4sb097ncujmdd52jp&st=06ac7v2j', '2025-01-15 00:00:00', true, '2025-01-19 04:26:49.087445'),
(10, 4, 'New Testament Week 3', 'Mark 2; John 5; Matthew 12:1-21; Mark 3; Luke 6', 'https://dl.dropboxusercontent.com/scl/fi/u3nst80ek4g0pnma63wza/NT-3.mp3?rlkey=2nkutip8h83ikp0h3t240oqbv&st=do2o2d0j', '2025-01-22 00:00:00', true, '2025-01-19 04:26:49.087446'),
(11, 4, 'New Testament Week 4', 'Matthew 5-7', 'https://dl.dropboxusercontent.com/scl/fi/8hpkd977nkhcm4z4mwege/NT-4.mp3?rlkey=0kxhgyfah9jsbzzjz9bcrfzo5&st=io5ye8ba', '2025-01-29 00:00:00', true, '2025-01-19 04:26:49.087446'),
(12, 4, 'New Testament Week 5', 'Matthew 8:1-13; Luke 7; Matthew 11; Matthew 12:22-50; Luke 11', 'https://dl.dropboxusercontent.com/scl/fi/1o2r4kxd9xmpaka8ilf1e/NT-5.mp3?rlkey=a8j7kd0697oec9yyq3cglsmux&st=ihd0qm40', '2025-02-05 00:00:00', true, '2025-01-19 04:26:49.087447'),
(13, 4, 'New Testament Week 6', 'Matthew 13; Luke 8; Matthew 8:14-34; Mark 4-5', 'https://dl.dropboxusercontent.com/scl/fi/5x1ox6y3qnajnn4l5u0v6/NT-6.mp3?rlkey=qrpgma1qahgsue6dm8kskiszm&st=7uhmj6od', '2025-02-12 00:00:00', true, '2025-01-19 04:26:49.087447'),
(14, 4, 'New Testament Week 7', 'Matthew 9-10; Matthew 14; Mark 6; Luke 9:1-17; John 6', 'https://dl.dropboxusercontent.com/scl/fi/g4dd87bq6ib231mmaf5cl/NT-7_-Expanding-the-Ministry.mp3?rlkey=43ckwq7u8ylckc7fqipdsu57k&st=f9qqgefi', '2025-02-19 00:00:00', true, '2025-01-19 04:26:49.087448'),
(15, 4, 'New Testament Week 8', 'Matthew 15; Mark 7; Matthew 16; Mark 8; Luke 9:18-27', 'https://dl.dropboxusercontent.com/scl/fi/i3bqoxhj2je3gaeli4piz/NT-8_-Further-Teachings-and-Miracles.mp3?rlkey=accikvmj1qeh1aj2pzyb6n2ny&st=psuyq8a0', '2025-02-26 00:00:00', true, '2025-01-19 04:26:49.087448'),
(16, 4, 'New Testament Week 9', 'Matthew 17; Mark 9; Luke 9:28-62; Matthew 18; John 7-8', 'https://dl.dropboxusercontent.com/scl/fi/b33k5t6nyquws9lorcxl3/NT-9_-Transfiguration-and-Teachings.mp3?rlkey=m4jqi6lzujsc9glzfqxf98f2o&st=7gru6i2o', '2025-03-05 00:00:00', true, '2025-01-19 04:26:49.087449'),
(17, 4, 'New Testament Week 10', 'John 9:1-41; John 10:1-21; Luke 10; John 10:22-42; Luke 12-13', 'https://dl.dropboxusercontent.com/scl/fi/m59rs2f66tdp7475zr84g/NT-10_-Healing-and-Discipleship.mp3?rlkey=e3lpb1ouu83pixd87io7qf0rb&st=k7o7hb3f', '2025-03-12 00:00:00', true, '2025-01-19 04:26:49.087449'),
(18, 4, 'New Testament Week 11', 'Luke 14-15; Luke 16; Luke 17:1-10', 'https://dl.dropboxusercontent.com/scl/fi/r4jdt3dehtgu5aeq77our/NT-11_-Parables-of-the-Kingdom.mp3?rlkey=lkzl09p45crpyp9vwer03ws0n&st=ii5snulf', '2025-03-19 00:00:00', true, '2025-01-19 04:26:49.08745'),
(19, 4, 'New Testament Week 12', 'John 11; Luke 17:11-37; Luke 18:1-14', 'https://dl.dropboxusercontent.com/scl/fi/bei0h6i5b75aoey8rekn0/NT-12_-Journey-Toward-Jerusalem.mp3?rlkey=nxbdo6iccgmff2dkrcb70wrez&st=9xl0foom', '2025-03-26 00:00:00', true, '2025-01-19 04:26:49.08745'),
(20, 4, 'New Testament Week 13', 'Matthew 19; Mark 10; Matthew 20-21', 'https://dl.dropboxusercontent.com/scl/fi/zpq9tt7ps92jjtwx7ly30/NT-13_-Encounters-and-Teachings.mp3?rlkey=l54gl9nc4bvc1abiayppnc69s&st=56mns1c4', '2025-04-02 00:00:00', true, '2025-01-19 04:26:49.087451');

-- Note: This export contains a sample of episodes. Full database contains over 400 episodes.
-- To get the complete data, run the full export queries against your database.

-- Reset sequences to current max values
SELECT setval('user_id_seq', (SELECT MAX(id) FROM "user"));
SELECT setval('feed_id_seq', (SELECT MAX(id) FROM feed));
SELECT setval('episode_id_seq', (SELECT MAX(id) FROM episode));
SELECT setval('dropbox_traffic_id_seq', (SELECT MAX(id) FROM dropbox_traffic));

-- Database statistics
-- Users: 2
-- Feeds: 11
-- Episodes: 400+ (sample shown above)
-- Dropbox Traffic Records: 0