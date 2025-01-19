import json
import os
import logging
import requests
from app import db
from flask import Blueprint, redirect, request, url_for, current_app
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get appropriate credentials based on environment
def get_oauth_credentials():
    if 'replit.app' in request.host:
        # Production environment - strictly use production credentials
        client_id = os.environ.get("GOOGLE_OAUTH_PROD_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_OAUTH_PROD_CLIENT_SECRET")
        logger.info("Using production OAuth credentials")
    else:
        # Development environment
        client_id = os.environ.get("GOOGLE_OAUTH_DEV_CLIENT_ID", os.environ.get("GOOGLE_OAUTH_CLIENT_ID"))
        client_secret = os.environ.get("GOOGLE_OAUTH_DEV_CLIENT_SECRET", os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"))
        logger.info("Using development OAuth credentials")

    logger.info(f"Current host: {request.host}")
    return client_id, client_secret

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Initialize blueprint
google_auth = Blueprint("google_auth", __name__)

def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Google provider config: {e}")
        return None

def get_callback_url():
    if 'replit.app' in request.host:
        # Production - use explicit production URL
        callback_url = "https://podcast-pal-bdgillihan.replit.app/google_login/callback"
        logger.info("Using production callback URL")
    else:
        # Development - use dynamic host
        callback_url = f"https://{request.host}/google_login/callback"
        logger.info("Using development callback URL")

    logger.info(f"Generated callback URL: {callback_url}")
    return callback_url

@google_auth.route("/google_login")
def login():
    """Initiates the Google OAuth login flow"""
    client_id, _ = get_oauth_credentials()
    if not client_id:
        logger.error("No Google OAuth client ID available")
        return "OAuth configuration error", 500

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        return "Error: Could not fetch Google provider configuration", 500

    client = WebApplicationClient(client_id)
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    callback_url = get_callback_url()

    logger.info(f"Login - Using callback URL: {callback_url}")
    logger.info(f"Login - Client ID: {client_id}")
    logger.info(f"Login - Request host: {request.host}")

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=callback_url,
        scope=["openid", "email", "profile"],
    )

    logger.info(f"Login - Generated request URI: {request_uri}")
    return redirect(request_uri)

@google_auth.route("/google_login/callback")
def callback():
    """Handles the callback from Google OAuth"""
    client_id, client_secret = get_oauth_credentials()
    if not client_id or not client_secret:
        logger.error("No Google OAuth credentials available")
        return "OAuth configuration error", 500

    code = request.args.get("code")
    if not code:
        logger.error("No code received from Google")
        return "Error: No code received from Google", 400

    client = WebApplicationClient(client_id)
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        return "Error: Could not fetch Google provider configuration", 500

    token_endpoint = google_provider_cfg["token_endpoint"]
    callback_url = get_callback_url()

    logger.info(f"Callback - Using callback URL: {callback_url}")
    logger.info(f"Callback - Request URL: {request.url}")
    logger.info(f"Callback - Request host: {request.host}")

    try:
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=callback_url,
            code=code
        )

        logger.info(f"Token request prepared - URL: {token_url}")

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(client_id, client_secret),
        )

        logger.info(f"Token response status: {token_response.status_code}")

        if not token_response.ok:
            logger.error(f"Token response error: {token_response.text}")
            return "Failed to get token from Google", 400

        client.parse_request_body_response(json.dumps(token_response.json()))

        # Fetch user information
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

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

        # Find existing user or create new one
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User(
                google_id=google_id,
                name=name,
                email=email
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"New user created: {email}")
        else:
            logger.info(f"Existing user logged in: {email}")

        # Log in the user
        login_user(user)
        return redirect(url_for("dashboard"))

    except Exception as e:
        logger.error(f"Error during OAuth flow: {str(e)}")
        return "Authentication failed", 400

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