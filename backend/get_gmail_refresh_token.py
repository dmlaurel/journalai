#!/usr/bin/env python3
"""
Helper script to get Gmail API refresh token.

This is a one-time setup. After running this, you'll have a refresh token
that you can use in your environment variables.

Prerequisites:
1. Go to https://console.cloud.google.com/
2. Create a project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download the credentials JSON file

Usage:
    python get_gmail_refresh_token.py --credentials credentials.json
"""

import argparse
import json
import os
import webbrowser
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# OAuth 2.0 configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
REDIRECT_URI = 'http://localhost:8080/callback'
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback"""
    
    def do_GET(self):
        if self.path.startswith('/callback'):
            query = parse_qs(self.path.split('?')[1] if '?' in self.path else '')
            code = query.get('code', [None])[0]
            error = query.get('error', [None])[0]
            
            if error:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f'<html><body><h1>Error: {error}</h1></body></html>'.encode())
                self.server.callback_error = error
            elif code:
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(
                    '<html><body><h1>Success!</h1><p>You can close this window.</p></body></html>'.encode()
                )
                self.server.callback_code = code
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><body><h1>No code received</h1></body></html>'.encode())
        else:
            self.send_response(404)
            self.end_headers()


def get_refresh_token(client_id, client_secret, email):
    """Get refresh token using OAuth 2.0 flow"""
    
    # Step 1: Get authorization code
    params = {
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES),
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent',
    }
    
    auth_url = f"{AUTH_URL}?{urlencode(params)}"
    print(f"\n1. Opening browser for authorization...")
    print(f"   If browser doesn't open, visit: {auth_url}\n")
    webbrowser.open(auth_url)
    
    # Start local server to receive callback
    server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
    server.callback_code = None
    server.callback_error = None
    
    print("2. Waiting for authorization...")
    print("   (This will open a browser window for you to sign in)")
    
    # Wait for callback (timeout after 2 minutes)
    import threading
    timeout = threading.Timer(120, lambda: setattr(server, 'callback_code', 'timeout'))
    timeout.start()
    
    while server.callback_code is None and server.callback_error is None:
        server.handle_request()
    
    timeout.cancel()
    server.server_close()
    
    if server.callback_error:
        raise Exception(f"OAuth error: {server.callback_error}")
    
    if server.callback_code == 'timeout':
        raise Exception("Authorization timed out. Please try again.")
    
    code = server.callback_code
    
    # Step 2: Exchange authorization code for tokens
    print("3. Exchanging authorization code for tokens...")
    
    token_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
    }
    
    response = requests.post(TOKEN_URL, data=token_data)
    
    if response.status_code != 200:
        raise Exception(f"Failed to get tokens: {response.status_code} - {response.text}")
    
    tokens = response.json()
    refresh_token = tokens.get('refresh_token')
    
    if not refresh_token:
        raise Exception("No refresh token received. Make sure you selected 'offline' access type.")
    
    print("\n✅ Success! Here are your credentials:\n")
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={refresh_token}")
    print(f"GMAIL_USER_EMAIL={email}")
    print("\nAdd these to your Render.com environment variables.\n")
    
    return refresh_token


def main():
    parser = argparse.ArgumentParser(description='Get Gmail API refresh token')
    parser.add_argument(
        '--credentials',
        required=True,
        help='Path to Google OAuth credentials JSON file'
    )
    parser.add_argument(
        '--email',
        required=True,
        help='Gmail address to send from'
    )
    
    args = parser.parse_args()
    
    # Load credentials
    if not os.path.exists(args.credentials):
        print(f"Error: Credentials file not found: {args.credentials}")
        return 1
    
    with open(args.credentials, 'r') as f:
        creds = json.load(f)
    
    # Extract client ID and secret
    if 'installed' in creds:
        # Desktop app credentials
        client_id = creds['installed']['client_id']
        client_secret = creds['installed']['client_secret']
    elif 'web' in creds:
        # Web app credentials (will work but Desktop is preferred)
        client_id = creds['web']['client_id']
        client_secret = creds['web']['client_secret']
    else:
        print("Error: Invalid credentials file format")
        print("Expected 'installed' or 'web' key with client_id and client_secret")
        return 1
    
    try:
        get_refresh_token(client_id, client_secret, args.email)
        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())

