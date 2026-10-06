"""Focused checks for public data selection, Spotify states, and safe SVG rendering."""
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

import profile_assets as assets


class ProfileAssetsTest(unittest.TestCase):
    def test_public_originals_only(self):
        repos = [{'language': 'TypeScript'}, {'language': 'C', 'fork': True}, {'private': True}]
        svg = assets.card('Public code', assets.activity_card(repos, 'checked'), 'dark')
        ET.fromstring(svg)
        self.assertIn('1 public originals', svg)
        self.assertIn('TypeScript', svg)
        self.assertNotIn('>C<', svg)

    def test_playback_states(self):
        track = {'type': 'track', 'name': 'Song'}
        recent = {'items': [{'track': track}]}
        self.assertEqual(assets.select_track({'item': track, 'is_playing': True}, recent), (track, 'Playing at last check'))
        for current in (None, {}, {'item': None}, {'item': track, 'is_playing': False}, {'item': {'type': 'episode'}}):
            self.assertEqual(assets.select_track(current, recent), (track, 'Last played'))
        self.assertEqual(assets.select_track(None, {'items': []}), (None, 'No recent tracks'))

    def test_svg_escaping_and_both_themes(self):
        track = {'name': '<script>&"', 'artists': [{'name': 'A & B'}]}
        for theme in assets.THEMES:
            svg = assets.card('Soundtrack', assets.spotify_card(track, 'Last played', 'checked'), theme)
            root = ET.fromstring(svg)
            self.assertFalse(root.findall('.//{http://www.w3.org/2000/svg}script'))
            self.assertIn('A &amp; B', svg)

    def test_missing_credentials_does_not_call_network(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch.object(assets, 'api') as api:
            assets.spotify(Path(directory))
            api.assert_not_called()
            for theme in assets.THEMES:
                self.assertIn('Awaiting authorization', (Path(directory) / f'spotify-{theme}.svg').read_text())

    def test_partial_credentials_are_rejected(self):
        with patch.dict(os.environ, {'SPOTIFY_CLIENT_ID': 'example'}, clear=True):
            with self.assertRaises(ValueError):
                assets.spotify(Path('/unused'))

    def test_live_fetch_and_recent_fallback(self):
        track = {'name': 'Song', 'artists': [{'name': 'Artist'}], 'type': 'track'}
        credentials = dict(SPOTIFY_CLIENT_ID='id', SPOTIFY_CLIENT_SECRET='secret', SPOTIFY_REFRESH_TOKEN='refresh')
        with TemporaryDirectory() as directory, patch.dict(os.environ, credentials, clear=True), patch.object(assets, 'api', side_effect=[{'access_token': 'token'}, None, {'items': [{'track': track}]}]) as api:
            assets.spotify(Path(directory))
            self.assertEqual(api.call_count, 3)
            self.assertIn('grant_type=refresh_token', api.call_args_list[0].args[2].decode())
            self.assertIn('Last played', (Path(directory) / 'spotify-dark.svg').read_text())

    def test_http_error_preserves_cards_and_hides_response(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'spotify-dark.svg'
            target.write_text('previous card')
            with patch('sys.argv', ['profile_assets.py', 'spotify', '--output', directory]), patch.object(assets, 'spotify', side_effect=HTTPError('hidden-url', 401, 'hidden-secret', None, None)), patch('sys.stderr', new_callable=io.StringIO) as stderr:
                self.assertEqual(assets.main(), 1)
                self.assertIn('HTTP 401', stderr.getvalue())
                self.assertNotIn('hidden', stderr.getvalue())
            self.assertEqual(target.read_text(), 'previous card')


if __name__ == '__main__':
    unittest.main()
