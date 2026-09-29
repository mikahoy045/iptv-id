#!/usr/bin/env python3
"""Refresh hometv.biz.id tokens from a freshly exported INDONESIA-TV m3u.

The hometv panel rotates its /play/<token> URLs every ~48h; when channels show
"too much connection" / 404, grab a new copy of the panel playlist and run:

    python3 refresh_hometv.py path/to/INDONESIA-TV.m3u

Matches by uppercased display name, swaps tokens in data/verified2.json,
re-probes each refreshed row, and reports which channels came back alive.
"""
import json, re, sys, time
from verify import check

def main():
    fresh = sys.argv[1]
    txt = open(fresh, errors='replace').read()
    entries = re.findall(r'#EXTINF[^\n]*,[ ]*(.+)[\n](http://hometv\.biz\.id[^\n]+)', txt)
    fresh_map = {}
    for n, u in entries:
        fresh_map.setdefault(n.strip().upper(), u)
    d = json.load(open('data/verified2.json'))
    swapped, dead = [], []
    for e in d:
        if e.get('source') != 'hometv.ts':
            continue
        nu = fresh_map.get(e['name'].upper())
        if not nu:
            dead.append(e['name']); continue
        if nu != e['url']:
            e['url'] = nu; swapped.append(e['name'])
    print(f'swapped tokens for {len(swapped)} rows; {len(dead)} rows not in fresh file')
    for e in d:
        if e.get('source') == 'hometv.ts':
            r = check(dict(e)); time.sleep(0.3)
            e['ok'], e['err'] = r.get('ok'), r.get('err')
    alive = sum(1 for e in d if e.get('source') == 'hometv.ts' and e.get('ok'))
    total = sum(1 for e in d if e.get('source') == 'hometv.ts')
    print(f'alive after refresh: {alive}/{total}')
    still = [e['name'] for e in d if e.get('source') == 'hometv.ts' and not e.get('ok')]
    if still: print('still dead:', ', '.join(still[:20]), '...' if len(still) > 20 else '')
    json.dump(d, open('data/verified2.json', 'w'), indent=1)

if __name__ == '__main__':
    main()
