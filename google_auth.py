import json
import os
import logging
import base64
import requests
from app import db
from flask import Blueprint, redirect, request, url_for, session
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize blueprint
google_auth = Blueprint("google_auth", __name__)

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

def get_oauth_credentials():
    """Get OAuth credentials based on environment"""
    try:
        # Check if we're in production or development
        is_production = ('replit.app' in request.host
                         or 'railway.app' in request.host
                         or 'bengillihan.com' in request.host)

        if is_production:
            client_id = os.environ.get("GOOGLE_OAUTH_PROD_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_OAUTH_PROD_CLIENT_SECRET")
            env_type = "production"
        else:
            client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
            env_type = "development"

        logger.debug(f"Environment: {env_type}")
        logger.debug(f"Client ID available: {bool(client_id)}")
        logger.debug(f"Client secret available: {bool(client_secret)}")
        logger.debug(f"Request host: {request.host}")

        if not client_id or not client_secret:
            raise ValueError(f"Missing {env_type} OAuth credentials. Please check environment variables.")

        return client_id, client_secret
    except Exception as e:
        logger.error(f"Error loading OAuth credentials: {str(e)}")
        raise

@google_auth.route("/google_login")
def login():
    """Initiates the Google OAuth login flow"""
    try:
        client_id, _ = get_oauth_credentials()

        # Get Google provider configuration
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Initialize client
        client = WebApplicationClient(client_id)

        # Generate and store state parameter
        state = base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
        session['oauth_state'] = state

        # Use https for callback URL
        callback_url = f"https://{request.host}/google_login/callback"
        logger.info(f"Login - Using callback URL: {callback_url}")

        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=callback_url,
            scope=["openid", "email", "profile"],
            state=state
        )

        return redirect(request_uri)

    except ValueError as e:
        logger.error(f"OAuth Configuration Error: {str(e)}")
        return "OAuth configuration is incomplete. Please check your Google OAuth setup in the environment variables.", 500
    except Exception as e:
        logger.error(f"Login Error: {str(e)}")
        return f"Authentication configuration error: {str(e)}", 500

@google_auth.route("/google_login/callback")
def callback():
    """Handles the callback from Google OAuth"""
    try:
        # Verify state parameter
        stored_state = session.pop('oauth_state', None)
        received_state = request.args.get('state')

        if not stored_state or stored_state != received_state:
            logger.error("State parameter mismatch or missing")
            logger.error(f"Stored state: {stored_state}, Received state: {received_state}")
            return "Invalid state parameter. Please try again.", 400

        client_id, client_secret = get_oauth_credentials()
        client = WebApplicationClient(client_id)

        callback_url = f"https://{request.host}/google_login/callback"
        logger.info(f"Callback - Using callback URL: {callback_url}")

        code = request.args.get("code")
        if not code:
            logger.error("No code received from Google")
            return "Error: No code received from Google", 400

        # Get token endpoint
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
        token_endpoint = google_provider_cfg["token_endpoint"]

        # Prepare and send token request
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=callback_url,
            code=code
        )

        if not token_url.startswith("https://"):
            token_url = token_url.replace("http://", "https://", 1)

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(client_id, client_secret),
            timeout=10
        )

        if not token_response.ok:
            logger.error(f"Token response error: {token_response.text}")
            return "Failed to get token from Google", 400

        client.parse_request_body_response(json.dumps(token_response.json()))

        # Get user info
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        if not uri.startswith("https://"):
            uri = uri.replace("http://", "https://", 1)
        userinfo_response = requests.get(uri, headers=headers, data=body, timeout=10)

        if not userinfo_response.ok:
            logger.error(f"Userinfo response error: {userinfo_response.text}")
            return "Failed to get user info from Google", 400

        userinfo = userinfo_response.json()
        if not userinfo.get("email_verified"):
            logger.error("User email not verified by Google")
            return "Google account email not verified", 400

        # Get user data
        google_id = userinfo["sub"]
        email = userinfo["email"]
        name = userinfo.get("name", email.split("@")[0])

        # Find or create user
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User(google_id=google_id, name=name, email=email)
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user created: {email}")
        else:
            logger.info(f"Existing user logged in: {email}")

        login_user(user)
        return redirect(url_for("dashboard"))

    except ValueError as e:
        logger.error(f"OAuth Configuration Error: {str(e)}")
        return "OAuth configuration is incomplete. Please check your Google OAuth setup in the environment variables.", 500
    except Exception as e:
        logger.error(f"Callback Error: {str(e)}")
        return "Authentication failed. Please try again.", 400

@google_auth.route("/logout")
@login_required
def logout():
    """Logs out the current user"""
    logout_user()
    return redirect(url_for("index"))

@google_auth.errorhandler(Exception)
def handle_error(error):
    """Global error handler for the blueprint"""
    logger.error(f"An error occurred: {error}")
    return "An error occurred during authentication", 500