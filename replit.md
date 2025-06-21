# PodcastPal - Multi-User Podcast RSS Feed Manager

## Overview

PodcastPal is a Flask-based web application that allows users to create and manage podcast RSS feeds. The application provides Google OAuth authentication, dynamic RSS feed generation, and comprehensive episode management capabilities. Users can create multiple podcast feeds, add episodes with media hosting support, and generate valid RSS feeds for distribution to podcast platforms.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with Python 3.11
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Google OAuth 2.0 integration via Flask-Login
- **Session Management**: Flask sessions with secure cookie handling
- **Timezone Handling**: PyTZ with Pacific Time (America/Los_Angeles) as default

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 dark theme
- **Styling**: Bootstrap CSS with custom CSS overrides
- **JavaScript**: Vanilla JavaScript for interactive features (copy buttons, modals)
- **Responsive Design**: Mobile-first responsive layout

## Key Components

### Authentication System
- Google OAuth 2.0 implementation with environment-specific credential handling
- Separate production and development OAuth credentials
- Automatic environment detection based on request host
- User session management with Flask-Login

### Database Models
- **User**: Stores Google OAuth user information and relationships
- **Feed**: Podcast feed metadata with unique URL slugs and user ownership
- **Episode**: Individual episode data with recurring episode support
- **DropboxTraffic**: Traffic analytics for Dropbox media hosting

### RSS Feed Generation
- Dynamic XML RSS feed generation compliant with podcast standards
- iTunes namespace support for podcast-specific metadata
- Feed caching mechanism with scheduled refresh times (3 AM PT daily)
- Support for recurring episodes that automatically reappear annually

### Media URL Processing
- Automatic conversion of Dropbox sharing URLs to direct download URLs
- Google Drive sharing URL conversion to direct download format
- URL validation and formatting utilities

### Database Optimization (Enhanced - June 21, 2025)
- **Connection Pool Optimization**: Reduced pool size to 2 connections, increased recycle time to 1 hour
- **Advanced Caching**: Multi-layer caching system for RSS feeds (1-hour TTL) and query results (5-minute TTL)
- **Session Management**: Efficient session contexts with automatic cleanup and timeout controls
- **Query Optimization**: Bulk operations, single-query joins, and limited result sets for RSS generation
- **Background Maintenance**: Automated ANALYZE operations and connection cleanup every hour
- **Connection Lifecycle**: Automatic cleanup after each request with idle connection termination
- **Lazy loading relationships to prevent N+1 queries
- Database indexes on frequently queried columns
- Batch commit decorators for transaction optimization

## Data Flow

### User Authentication Flow
1. User accesses application and initiates Google OAuth login
2. Application redirects to Google OAuth with environment-specific credentials
3. Google returns authorization code to callback URL
4. Application exchanges code for access token and retrieves user profile
5. User session is established with Flask-Login

### Feed Management Flow
1. Authenticated user creates new feed with metadata
2. System generates unique URL slug using slugify and random suffix
3. Episodes are added with media URLs automatically converted to direct links
4. RSS feed is generated on-demand with caching for performance

### RSS Feed Access Flow
1. External request accesses RSS feed via unique URL slug
2. System checks feed cache and refresh schedule
3. If cache is stale, episodes are fetched and RSS XML is regenerated
4. Generated feed is cached and served to client

## External Dependencies

### Authentication
- Google OAuth 2.0 API for user authentication
- Requires GOOGLE_OAUTH_PROD_CLIENT_ID and GOOGLE_OAUTH_PROD_CLIENT_SECRET environment variables

### Media Hosting
- Dropbox for audio file hosting with direct download URL conversion
- Google Drive support for audio and image hosting
- External media URLs are converted to direct access format

### Database
- PostgreSQL database with connection string via DATABASE_URL environment variable
- Database connection pooling and optimization for reduced compute usage

### Python Dependencies
- Flask ecosystem (Flask, Flask-SQLAlchemy, Flask-Login)
- OAuth library (oauthlib) for Google authentication
- URL processing (requests, urllib) for media URL conversion
- Timezone handling (pytz) for consistent time management

## Deployment Strategy

### Environment Configuration
- Environment-specific OAuth credentials based on request host detection
- Replit-optimized deployment with autoscale target
- Flask development server for local testing, production-ready configuration available

### Database Management
- Automatic database table creation on application startup
- SQLAlchemy migrations for schema changes
- Connection pooling optimized for serverless/autoscale environments

### Performance Optimization
- RSS feed caching to reduce database load
- Scheduled refresh times to minimize compute usage
- Database query optimization with eager loading and indexing
- Connection pool configuration for reduced resource consumption

### Security Considerations
- Environment variable-based configuration for sensitive data
- Secure session management with Flask-Login
- HTTPS enforcement for OAuth callbacks in production
- User-scoped data access with proper authorization checks

## Changelog

```
Changelog:
- June 21, 2025: Initial setup
- June 21, 2025: Implemented comprehensive database optimization to reduce compute hours:
  * Reduced connection pool from 3 to 2 connections
  * Increased connection recycle time from 30min to 1 hour
  * Added multi-layer caching system (RSS: 1hr, queries: 5min)
  * Implemented efficient session management with automatic cleanup
  * Added background maintenance worker for database optimization
  * Optimized RSS feed generation with result limiting and bulk operations
  * Added connection monitoring and idle connection termination
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```