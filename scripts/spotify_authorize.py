#!/usr/bin/env python3
"""Authorize Spotify locally; stdout contains only the refresh token on success."""

import base64
import getpass
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
import webbrowser

REDIRECT_URI = 'http://127.0.0.1:8888/callback'
SCOPES = 'user-read-currently-playing user-read-recently-played'


def authorization_url(client_id, state, verifier):
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return 'https://accounts.spotify.com/authorize?' + urlencode({
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPES,
        'state': state,
        'code_challenge_method': 'S256',
        'code_challenge': challenge,
    })


def callback_result(path, state):
    parsed = urlsplit(path)
    if parsed.path != '/callback':
        return 404, None
    query = parse_qs(parsed.query)
    received = query.get('state', [])
    if len(received) != 1 or not secrets.compare_digest(received[0], state):
        return 400, None
    if len(query.get('error', [])) == 1:
        return 400, {'error': 'Authorization denied by Spotify.'}
    codes = query.get('code', [])
    if len(codes) != 1 or not codes[0]:
        return 400, None
    return 200, {'code': codes[0]}


def callback_handler(state):
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            status, result = callback_result(self.path, state)
            if result is not None:
                self.server.oauth_result = result
            body = (b'Authorization received. You can close this tab and return to the terminal.'
                    if status == 200 else b'Authorization not accepted. Return to the terminal.')
            self.send_response(status)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            # Callback URLs contain authorization codes; never log them.
            pass
    return Callback


def exchange_code(client_id, client_secret, code, verifier):
    basic = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    request = Request('https://accounts.spotify.com/api/token', data=urlencode({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': verifier,
    }).encode(), headers={
        'Authorization': f'Basic {basic}',
        'Content-Type': 'application/x-www-form-urlencoded',
    })
    with urlopen(request, timeout=30) as response:
        token = json.loads(response.read()).get('refresh_token')
    if not isinstance(token, str) or not token or any(c.isspace() for c in token):
        raise RuntimeError('Spotify did not return a valid refresh token.')
    return token


def main():
    try:
        client_id = os.environ.get('SPOTIFY_CLIENT_ID') or getpass.getpass('Spotify Client ID: ', stream=sys.stderr)
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET') or getpass.getpass('Spotify Client Secret: ', stream=sys.stderr)
        if not client_id.strip() or not client_secret.strip():
            raise RuntimeError('Client ID and Client Secret are required.')
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        # Bind before opening the browser; another process must not own the callback port.
        with HTTPServer(('127.0.0.1', 8888), callback_handler(state)) as server:
            server.oauth_result = None
            server.timeout = 1
            url = authorization_url(client_id.strip(), state, verifier)
            print(f'Register this redirect URI in your app: {REDIRECT_URI}', file=sys.stderr)
            print(f'Authorize Spotify in your browser. If it does not open, visit:\n{url}', file=sys.stderr)
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                pass
            deadline = time.monotonic() + 300
            while server.oauth_result is None and time.monotonic() < deadline:
                server.handle_request()
            result = server.oauth_result
        if result is None:
            raise RuntimeError('Authorization timed out after 5 minutes.')
        if 'error' in result:
            raise RuntimeError(result['error'])
        token = exchange_code(client_id.strip(), client_secret.strip(), result['code'], verifier)
        print(token)
        return 0
    except HTTPError as error:
        error.close()
        print(f'Spotify token exchange failed: HTTP {error.code}. Check app credentials and redirect URI.', file=sys.stderr)
    except (URLError, OSError, ValueError):
        print('Authorization failed. Check network access and whether local port 8888 is available.', file=sys.stderr)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
    except KeyboardInterrupt:
        print('Authorization cancelled.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
