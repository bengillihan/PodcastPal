import json
import os
import logging
import base64
import requests
from app import db
from flask import Blueprint, redirect, request, url_for, session, current_app
from flask_login import login_required, login_user, logout_user
from models import User
from oauthlib.oauth2 import WebApplicationClient

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize blueprint first, before any routes
google_auth = Blueprint("google_auth", __name__)

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Validate required environment variables
required_vars = [
    "GOOGLE_OAUTH_PROD_CLIENT_ID",
    "GOOGLE_OAUTH_PROD_CLIENT_SECRET",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET"
]

for var in required_vars:
    if not os.environ.get(var):
        logger.error(f"Missing {var} environment variable")
        raise RuntimeError(f"Missing required environment variable: {var}")

@google_auth.route("/google_login")
def login():
    """Initiates the Google OAuth login flow"""
    try:
        client_id = os.environ["GOOGLE_OAUTH_PROD_CLIENT_ID"] if 'replit.app' in request.host else os.environ["GOOGLE_OAUTH_CLIENT_ID"]
        logger.info(f"Login - Using client ID: {client_id[:8]}... (truncated)")
        logger.info(f"Login - Current host: {request.host}")

        # Get Google provider configuration with timeout
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Initialize client for this request
        client = WebApplicationClient(client_id)

        # Generate and store state parameter
        state = base64.urlsafe_b64encode(os.urandom(24)).decode('utf-8')
        session['oauth_state'] = state
        logger.info("Generated new OAuth state parameter")

        # Use production redirect URI for replit.app domains
        callback_url = f"https://{request.host}/google_login/callback"
        logger.info(f"Login - Using callback URL: {callback_url}")

        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=callback_url,
            scope=["openid", "email", "profile"],
            state=state
        )
        logger.info(f"Login - Request URI generated: {request_uri[:50]}... (truncated)")

        return redirect(request_uri)
    except KeyError as e:
        logger.error(f"OAuth Credentials Error: {str(e)}")
        return "Missing OAuth credentials. Please check your configuration.", 500
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
            return "Invalid state parameter. Please try again.", 400

        client_id = os.environ["GOOGLE_OAUTH_PROD_CLIENT_ID"] if 'replit.app' in request.host else os.environ["GOOGLE_OAUTH_CLIENT_ID"]
        client_secret = os.environ["GOOGLE_OAUTH_PROD_CLIENT_SECRET"] if 'replit.app' in request.host else os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
        client = WebApplicationClient(client_id)

        callback_url = f"https://{request.host}/google_login/callback"
        logger.info(f"Callback - Using callback URL: {callback_url}")

        code = request.args.get("code")
        if not code:
            logger.error("No code received from Google")
            return "Error: No code received from Google", 400

        # Get token endpoint with timeout
        google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL, timeout=10).json()
        token_endpoint = google_provider_cfg["token_endpoint"]

        # Prepare token request
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url.replace("http://", "https://"),
            redirect_url=callback_url,
            code=code
        )

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

        # Get user info with timeout
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
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

    except Exception as e:
        logger.error(f"Callback Error: {str(e)}")
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