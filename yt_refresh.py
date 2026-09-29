#!/usr/bin/env python3
"""Refresh data/yt_channels.json: re-probe each known handle for its current
24/7 livestream (IDs rotate as YouTube restarts the pseudo-live events),
and harvest logos from the main playlist for shared channels."""
import json, re, subprocess

HANDLES = {  # handle -> (name, group)
    'tvOneNews': ('tvOne', 'News'),
    'KOMPASTV': ('Kompas TV', 'News'),
    'IDXChannel': ('IDX Channel', 'News'),
    'metrotvnews': ('Metro TV', 'News'),
    'TVRINasional': ('TVRI Nasional', 'TVRI'),
}

def main():
    txt = open('tv_indonesia.m3u').read() if __import__('os').path.exists('tv_indonesia.m3u') else ''
    logos = {}
    for m in re.finditer(r'#EXTINF:[^\n]*tvg-logo="([^"]*)"[^\n]*,(\S[^\n]*)$', txt, re.M):
        logos.setdefault(m.group(2).strip(), m.group(1))
    rows = []
    for h, (name, group) in HANDLES.items():
        url = f'https://www.youtube.com/@{h}/live'
        try:
            p = subprocess.run(['yt-dlp', '--dump-single-json', '--no-warnings',
                                '--skip-download', '--no-playlist', url],
                               capture_output=True, text=True, timeout=90)
            d = json.loads(p.stdout)
        except Exception as e:
            print('DROP', name, e)
            continue
        if p.returncode != 0 or not d.get('is_live'):
            print('DROP (not live):', name)
            continue
        rows.append({'tvg-id': h + '.yt', 'name': name, 'group': group,
                     'video_id': d['id'],
                     'watch': 'https://www.youtube.com/watch?v=' + d['id'],
                     'title': d.get('title', ''), 'channel': d.get('channel', ''),
                     'logo': logos.get(name, '')})
        print('KEEP', name, d['id'], d.get('title', '')[:60])
    json.dump(rows, open('data/yt_channels.json', 'w'), indent=1)
    print('total', len(rows))

if __name__ == '__main__':
    main()
