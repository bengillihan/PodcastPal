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


### RSS Feed Generation
- Dynamic XML RSS feed generation compliant with podcast standards
- iTunes namespace support for podcast-specific metadata
- Feed caching mechanism with scheduled refresh times (daily at 3 AM PT)
- Support for recurring episodes that automatically reappear annually
- 24-hour cache TTL to minimize autoscale deployment requests

### Media URL Processing
- Automatic conversion of Dropbox sharing URLs to direct download URLs
- Google Drive sharing URL conversion to direct download format
- URL validation and formatting utilities

### Database Architecture (Updated - June 24, 2025)
- **Database**: Migrated from Replit to Supabase PostgreSQL 17.4
- **Connection Pool**: Optimized for Supabase with 2 connections, 2-hour recycle time
- **Caching Strategy**: Long-term caching with RSS feeds (24-hour TTL) to minimize autoscale requests
- **Refresh Schedule**: Once daily (3 AM PT) to minimize deployment compute costs
- **Session Management**: Efficient session contexts with automatic cleanup
- **Query Optimization**: Bulk operations, single-query joins, and limited result sets
- **Performance**: No database compute cost concerns with Supabase infrastructure
- **Lazy loading relationships to prevent N+1 queries
- Database indexes on frequently queried columns
- Background maintenance and connection cleanup

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
- June 21, 2025: Implemented comprehensive database optimization to reduce compute hours
- June 24, 2025: Migrated database from Replit to Supabase PostgreSQL 17.4
- June 25, 2025: Fixed RSS feed episode display issue:
  * Resolved namedtuple immutability error preventing episode display
  * Implemented proper recurring episode date calculation for 90-day window
  * RSS feeds now correctly show episodes from today and last 90 days
  * Maintained cost-effective caching (24-hour TTL, daily refresh at 3 AM PT)
- July 8, 2025: Fixed database connection conflicts:
  * Eliminated conflicting PG* environment variables (PGDATABASE, PGHOST, etc.)
  * Ensured exclusive use of Supabase via DATABASE_URL in both dev and production
  * Production RSS feeds now correctly serve 67 episodes from Supabase
  * All database operations (reads/writes) confirmed to use Supabase PostgreSQL 17.4
- July 28, 2025: Removed DropboxTraffic database table and analytics:
  * Completely removed DropboxTraffic model from models.py
  * Cleaned up all imports and references in routes.py, main.py, feed_generator.py
  * Removed /dropbox-traffic route and traffic logging functionality
  * Simplified RSS feed generation by removing traffic analytics overhead
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```