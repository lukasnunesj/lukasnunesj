"""Local OAuth checks; no browser, Spotify access, or real credentials required."""
import base64
import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import spotify_authorize as auth


class SpotifyAuthorizeTest(unittest.TestCase):
    def test_authorization_url(self):
        query = parse_qs(urlsplit(auth.authorization_url('client', 'state', 'verifier')).query)
        self.assertEqual(query['redirect_uri'], [auth.REDIRECT_URI])
        self.assertEqual(query['scope'], [auth.SCOPES])
        self.assertEqual(query['state'], ['state'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        expected = base64.urlsafe_b64encode(hashlib.sha256(b'verifier').digest()).rstrip(b'=').decode()
        self.assertEqual(query['code_challenge'], [expected])

    def test_callback_validation(self):
        for path in ['/favicon.ico', '/callback?code=secret', '/callback?state=wrong&code=secret', '/callback?state=ok&state=wrong&code=secret', '/callback?state=ok&code=a&code=b']:
            self.assertIsNone(auth.callback_result(path, 'ok')[1])
        self.assertEqual(auth.callback_result('/callback?state=ok&code=abc%2B123', 'ok'), (200, {'code': 'abc+123'}))
        self.assertIn('error', auth.callback_result('/callback?state=ok&error=access_denied', 'ok')[1])

    def test_token_exchange(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'refresh_token': 'only-token'}).encode()
        with patch.object(auth, 'urlopen', return_value=response) as urlopen:
            self.assertEqual(auth.exchange_code('id', 'secret', 'code', 'verifier'), 'only-token')
        request = urlopen.call_args.args[0]
        self.assertEqual(parse_qs(request.data.decode())['code_verifier'], ['verifier'])
        self.assertEqual(request.get_header('Authorization'), 'Basic ' + base64.b64encode(b'id:secret').decode())

    def test_missing_refresh_token_is_rejected(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"access_token":"not-a-refresh-token"}'
        with patch.object(auth, 'urlopen', return_value=response), self.assertRaises(RuntimeError):
            auth.exchange_code('id', 'secret', 'code', 'verifier')

    def test_success_stdout_contains_only_refresh_token(self):
        server = unittest.mock.MagicMock()
        def callback():
            server.oauth_result = {'code': 'received-code'}
        server.handle_request.side_effect = callback
        context = unittest.mock.MagicMock()
        context.__enter__.return_value = server
        with patch.dict(os.environ, {'SPOTIFY_CLIENT_ID': 'id', 'SPOTIFY_CLIENT_SECRET': 'secret'}), patch.object(auth, 'HTTPServer', return_value=context), patch.object(auth.webbrowser, 'open'), patch.object(auth, 'exchange_code', return_value='only-refresh-token'), patch('sys.stdout', new_callable=io.StringIO) as stdout, patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(auth.main(), 0)
            self.assertEqual(stdout.getvalue(), 'only-refresh-token\n')

    def test_error_never_prints_token_or_response_body(self):
        with patch.dict(os.environ, {'SPOTIFY_CLIENT_ID': 'id', 'SPOTIFY_CLIENT_SECRET': 'secret'}), patch.object(auth, 'HTTPServer', side_effect=HTTPError('secret-url', 401, 'secret-body', None, None)), patch('sys.stdout', new_callable=io.StringIO) as stdout, patch('sys.stderr', new_callable=io.StringIO) as stderr:
            self.assertEqual(auth.main(), 1)
            self.assertEqual(stdout.getvalue(), '')
            self.assertIn('HTTP 401', stderr.getvalue())
            self.assertNotIn('secret', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
