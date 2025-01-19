# PodcastPal

PodcastPal is a multi-user podcast RSS feed management application that simplifies podcast content creation, distribution, and discovery. Create and manage your podcast feeds with easy-to-use tools for uploading episodes and generating RSS feeds compatible with major podcast platforms.

## Features

- Google OAuth authentication for secure user management
- Dynamic RSS feed generation with media URL handling
- Support for Dropbox and Google Drive media hosting
- Bulk episode upload via CSV
- Individual episode management
- Personalized podcast feed management
- Responsive web interface

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Google OAuth credentials

### Environment Variables

Set up the following environment variables in your Replit Secrets:

```
DATABASE_URL=postgresql://[username]:[password]@[host]:[port]/[database]
GOOGLE_OAUTH_PROD_CLIENT_ID=[your-google-oauth-client-id]
GOOGLE_OAUTH_PROD_CLIENT_SECRET=[your-google-oauth-client-secret]
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Configure the OAuth consent screen
4. Create OAuth 2.0 Client credentials
5. Add authorized redirect URIs:
   - `https://[your-replit-domain]/google_login/callback`

### Running the Application

The application will automatically start when you run the Replit project. It runs on port 5000 and includes:
- Flask web server
- PostgreSQL database connection
- Google OAuth authentication

## Usage Guide

### Creating a New Podcast Feed

1. Log in using your Google account
2. Click "Create New Feed" on the dashboard
3. Fill in the feed details:
   - Name
   - Description
   - Podcast Image URL (optional)

### Adding Episodes

#### Individual Episodes

1. Navigate to your feed
2. Click "Add Episode"
3. Fill in episode details:
   - Title
   - Description
   - Audio URL (Dropbox or Google Drive)
   - Release Date

#### Bulk Upload via CSV

1. Use the provided CSV template (`episode_template.csv`)
2. Format:
```csv
title,description,audio_url,release_date,is_recurring
Example Episode,Description here,https://your-audio-url.mp3,MM/DD/YY HH:MM,FALSE
```
3. Upload the CSV file through the bulk upload interface

### Managing Audio Files

- **Dropbox Links**: The application automatically converts Dropbox sharing links to direct download URLs
- **File Formats**: Support MP3 audio files
- **File Hosting**: Use Dropbox or Google Drive for hosting audio files

## Troubleshooting

### Common Issues

1. **OAuth Login Errors**
   - Verify Google OAuth credentials are correctly set in environment variables
   - Ensure authorized redirect URIs are properly configured in Google Cloud Console
   - Check if you're using the correct OAuth client ID and secret for your environment

2. **Audio URL Issues**
   - For Dropbox: Ensure sharing is enabled and links are accessible
   - Verify URLs are properly formatted
   - Check if audio files are downloadable without authentication

3. **RSS Feed Problems**
   - Verify all required episode fields are filled
   - Check audio file URLs are accessible
   - Ensure feed image URLs are valid and accessible

### Debugging

- Check the application logs for detailed error messages
- Verify environment variables are properly set
- Ensure database connection is active
- Test audio file URLs in a browser to confirm accessibility

## Support

For additional support or to report issues:
1. Check the troubleshooting guide above
2. Review application logs for specific error messages
3. Ensure all configuration steps are completed
4. Contact support if issues persist
