#!/usr/bin/env python3
"""Parse any M3U/M3U8 playlist text into normalized stream entries."""
import re

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

def parse_playlist(text, source):
    entries = []
    cur = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith('#EXTM3U'):
            continue
        if line.upper().startswith('#EXTINF'):
            cur = {'source': source}
            head, _, name = line.partition(',')
            for k, v in ATTR_RE.findall(head):
                cur[k] = v
            cur['name'] = name.strip()
            # duration may appear as #EXTINF:123
            m = re.match(r'#EXTINF:\s*([\d.]+-?[\d.]*)', head, re.I)
            if m:
                cur['duration'] = m.group(1)
        elif line.upper().startswith('#EXTVLCOPT:') or line.upper().startswith('#EXTHTTP:'):
            k, _, v = line.split(':', 1)[1].partition('=')
            k = k.strip().lower()
            if k == 'http-referrer' or k == 'referer':
                cur['http-referrer'] = v.strip()
            elif k == 'http-user-agent':
                cur['http-user-agent'] = v.strip()
            else:
                cur.setdefault('headers', {})[k] = v.strip()
        elif line.startswith('#'):
            continue
        else:  # URL line
            e = dict(cur)
            e['url'] = line
            e.setdefault('name', re.split(r'[/_]', line.rstrip('/'))[-1] or line[:40])
            entries.append(e)
            cur = {}
    return entries

def norm_name(name):
    """Strip quality/resolution/geo tags for dedupe: 'RCTI HD (720p) [Geo-blocked]' -> 'RCTI'."""
    n = re.sub(r'\[[^\]]*\]', ' ', name or '')
    n = re.sub(r'\(\s*\d{3,4}\s*[piPI]\s*\)', ' ', n)
    n = re.sub(r'\b\d{3,4}\s*[piPI]\b', ' ', n)
    n = re.sub(r'\b(HD|FHD|SD|HQ|LQ|LIVE|Live|24/7|OFF|Geo[- ]?block(?:ed)?)\b', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip(' -·|.')
    return n

if __name__ == '__main__':
    import sys, json, glob
    all_entries = []
    for f in sys.argv[1:]:
        for path in ([f] if not f.endswith('*') else glob.glob(f)):
            try:
                txt = open(path, encoding='utf-8', errors='replace').read()
                src = path.split('/')[-1]
                got = parse_playlist(txt, src)
                all_entries.extend(got)
                print(f'{src}: {len(got)} entries')
            except Exception as e:
                print('FAIL', path, e)
    json.dump(all_entries, open('data/gh_candidates.json', 'w'), indent=1)
    print('TOTAL', len(all_entries))
