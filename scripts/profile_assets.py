#!/usr/bin/env python3
"""Generate public profile cards using only the Python standard library."""

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER = 'lukasnunesj'
THEMES = {
    'dark': ('#0b1020', '#cfd9ed', '#97a8c7', '#7dd3fc', '#24324f'),
    'light': ('#f2f5fc', '#172442', '#526482', '#335ca8', '#d6e0f2'),
}


def api(url, headers=None, data=None):
    request = Request(url, headers={'User-Agent': 'lukasnunesj-profile', **(headers or {})}, data=data)
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read()) if response.status != 204 else None


def stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def text(value, limit=60):
    value = str(value)
    return escape(value if len(value) <= limit else value[:limit - 1] + '…', quote=True)


def card(title, content, theme, height=230):
    bg, fg, muted, accent, border = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" role="img" aria-labelledby="title">
<title id="title">{text(title, 200)}</title>
<rect x="1" y="1" width="898" height="{height - 2}" rx="16" fill="{bg}" stroke="{border}"/>
<g font-family="ui-monospace, SFMono-Regular, Consolas, monospace" fill="{fg}">
<text x="32" y="38" fill="{accent}" font-size="13" letter-spacing="2">{text(title.upper(), 100)}</text>
{content(bg, fg, muted, accent, border)}
</g></svg>\n'''


def write_pair(output, name, title, content, height=230):
    output.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        (output / f'{name}-{theme}.svg').write_text(card(title, content, theme, height), encoding='utf-8')


def activity_card(repos, checked):
    # Only original PUBLIC repositories, including archived experiments; no private data.
    original = [r for r in repos if not r.get('fork') and not r.get('private')]
    languages = Counter(r['language'] for r in original if r.get('language')).most_common(5)

    def content(bg, fg, muted, accent, border):
        parts = [f'<text x="32" y="89" font-size="34">{len(original)} public originals</text>',
                 f'<text x="32" y="119" fill="{muted}" font-size="13">Projects + experiments. Forks excluded.</text>',
                 f'<text x="32" y="194" fill="{muted}" font-size="12">Checked {text(checked)}</text>']
        for index, (language, count) in enumerate(languages):
            y = 73 + index * 25
            width = round(180 * count / languages[0][1])
            parts.append(f'<text x="490" y="{y}" font-size="13">{text(language, 18)}</text>'
                         f'<rect x="615" y="{y - 11}" width="{width}" height="12" rx="3" fill="{accent}" opacity="{1 - index * .12}"/>'
                         f'<text x="840" y="{y}" fill="{muted}" font-size="13">{count}</text>')
        parts.append(f'<text x="490" y="214" fill="{muted}" font-size="11">Primary languages by repo, not skill ratings.</text>')
        return '\n'.join(parts)
    return content


def github_activity(output):
    token = os.environ.get('GITHUB_TOKEN')
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    repos = []
    page = 1
    while True:
        batch = api(f'https://api.github.com/users/{USER}/repos?per_page=100&type=owner&page={page}', headers)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    write_pair(output, 'activity', 'Public code / field notes', activity_card(repos, stamp()))


def select_track(current, recent):
    item = (current or {}).get('item')
    if item and item.get('type') == 'track' and current.get('is_playing'):
        return item, 'Playing at last check'
    for entry in (recent or {}).get('items', []):
        if entry.get('track'):
            return entry['track'], 'Last played'
    return None, 'No recent tracks'


def spotify_card(track, status, checked):
    def content(bg, fg, muted, accent, border):
        name = track.get('name', 'Unknown track') if track else 'No listening data yet'
        artists = ', '.join(a.get('name', '') for a in track.get('artists', [])) if track else ('Spotify connection pending' if status == 'Awaiting authorization' else 'No recent listening history')
        return f'''<text x="32" y="78" fill="{accent}" font-size="13">{text(status)}</text>
<text x="32" y="117" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="600">{text(name, 48)}</text>
<text x="32" y="148" font-size="15" fill="{muted}">{text(artists, 65)}</text>
<text x="32" y="194" font-size="12" fill="{muted}">{text(checked, 100)}</text>
<g stroke="{accent}" stroke-width="4" stroke-linecap="round">
<path d="M778 104v12 M790 92v36 M802 78v64 M814 94v32 M826 86v48 M838 102v16"/>
</g>'''
    return content


def spotify(output):
    credentials = [os.environ.get(key) for key in ('SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_REFRESH_TOKEN')]
    if not any(credentials):
        write_pair(output, 'spotify', 'Soundtrack / Spotify', spotify_card(None, 'Awaiting authorization', 'Listening data will appear here once connected.'))
        print('Spotify not configured; generated an honest connection-pending card.')
        return
    if not all(credentials):
        raise ValueError('Spotify configuration incomplete: all three secrets are required.')
    client, secret, refresh = credentials
    basic = base64.b64encode(f'{client}:{secret}'.encode()).decode()
    token = api('https://accounts.spotify.com/api/token',
                {'Authorization': f'Basic {basic}', 'Content-Type': 'application/x-www-form-urlencoded'},
                urlencode({'grant_type': 'refresh_token', 'refresh_token': refresh}).encode())['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    current = api('https://api.spotify.com/v1/me/player/currently-playing', headers)
    track, status = select_track(current, None)
    if not track:
        recent = api('https://api.spotify.com/v1/me/player/recently-played?limit=1', headers)
        track, status = select_track(None, recent)
    write_pair(output, 'spotify', 'Soundtrack / Spotify', spotify_card(track, status, f'Snapshot {stamp()} · refreshed every 30 min'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('feature', choices=['activity', 'spotify'])
    parser.add_argument('--output', type=Path, default=Path('assets'))
    args = parser.parse_args()
    try:
        {'activity': github_activity, 'spotify': spotify}[args.feature](args.output)
    except HTTPError as error:
        # Never log response bodies: an OAuth response may contain sensitive data.
        print(f'{args.feature}: HTTP {error.code}; check service access and configuration. Existing cards preserved.', file=sys.stderr)
        return 1
    except (URLError, TimeoutError, ValueError, KeyError) as error:
        # Do not echo exception text, URLs, tokens, or response payloads.
        print(f'{args.feature}: {type(error).__name__}; existing cards preserved.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
