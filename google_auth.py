import json
import os
import logging

import requests
from app import db
from flask import Blueprint, redirect, request, url_for
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Get the current Replit domain for the callback URL
REPLIT_DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN")
if not REPLIT_DOMAIN:
    logger.error("REPLIT_DEV_DOMAIN environment variable is not set")

# OAuth 2 client setup
if not GOOGLE_CLIENT_ID:
    logger.error("GOOGLE_OAUTH_CLIENT_ID environment variable is not set")
client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)

def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Google provider config: {e}")
        return None

@google_auth.route("/google_login")
def login():
    """Initiates the Google OAuth login flow"""
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        return "Error: Could not fetch Google provider configuration", 500

    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use consistent callback URL format
    callback_url = f"https://{REPLIT_DOMAIN}/google_login/callback"
    logger.info(f"Using callback URL: {callback_url}")

    # Construct the request URI for Google login
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=callback_url,
        scope=["openid", "email", "profile"],
    )

    logger.info(f"Redirecting to authorization endpoint with redirect_uri: {callback_url}")
    return redirect(request_uri)

@google_auth.route("/google_login/callback")
def callback():
    """Handles the callback from Google OAuth"""
    code = request.args.get("code")
    if not code:
        logger.error("No code received from Google")
        return "Error: No code received from Google", 400

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        return "Error: Could not fetch Google provider configuration", 500

    token_endpoint = google_provider_cfg["token_endpoint"]

    # Use consistent callback URL format
    callback_url = f"https://{REPLIT_DOMAIN}/google_login/callback"
    logger.info(f"Callback endpoint using callback URL: {callback_url}")

    # Prepare and send token request
    try:
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=callback_url,
            code=code,
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        client.parse_request_body_response(json.dumps(token_response.json()))
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return "Error during token exchange", 400

    # Fetch user information
    try:
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        if not userinfo_response.ok:
            logger.error("Failed to get user info from Google")
            return "Failed to get user info from Google", 400

        userinfo = userinfo_response.json()

        if not userinfo.get("email_verified"):
            logger.error("User email not verified by Google")
            return "Google account email not verified", 400

        # Get user data
        google_id = userinfo["sub"]
        email = userinfo["email"]
        name = userinfo.get("name", userinfo.get("given_name", email.split("@")[0]))

        # Find existing user or create new one
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                # Update existing user with Google ID
                user.google_id = google_id
            else:
                # Create new user
                user = User(
                    google_id=google_id,
                    name=name,
                    email=email
                )
                db.session.add(user)

            db.session.commit()
            logger.info(f"User created/updated: {email}")

        # Log in the user
        login_user(user)
        logger.info(f"User logged in: {email}")

        return redirect(url_for("dashboard"))

    except Exception as e:
        logger.error(f"Error during user info retrieval: {e}")
        return "Error retrieving user information", 400

@google_auth.route("/logout")
@login_required
def logout():
    """Logs out the current user"""
    logout_user()
    logger.info("User logged out")
    return redirect(url_for("index"))

@google_auth.errorhandler(Exception)
def handle_error(error):
    """Global error handler for the blueprint"""
    logger.error(f"An error occurred: {error}")
    return "An error occurred during authentication", 500