#!/usr/bin/env python3
"""Probe YouTube channels for an active 24/7 livestream.

For each handle, `yt-dlp https://www.youtube.com/@<handle>/live` resolves to the
channel's current livestream (real or pseudo-live). We keep it only if
is_live=true and the title is TV-ish (not a news report / music vid).
Writes data/yt_live.json.
"""
import json, re, subprocess, sys, concurrent.futures as cf

# handle -> suggested name (from knowledge; corrected after probe if mismatch)
CANDIDATES = {
    # national FTA
    'trans7': 'Trans7', 'TransTVOfficial': 'Trans TV',
    'officialvidio': 'SCTV', 'officialindosiar': 'Indosiar',
    'metroofficialvideo': 'Metro TV', 'tvOneNews': 'tvOne',
    'Liputan6': 'Liputan6 (NET.)', 'KOMPASTV': 'Kompas TV',
    'tvMu': 'TVMU', 'DAIICTV': 'DAAI TV',
    'RAKYATTVRI': 'TVRI', 'sindonewstv': 'Sindo News TV',
    'BeritaSatuTV': 'BTV (Berita Satu)', 'IDXChannel': 'IDX Channel',
    'BerkilasLokal': 'Jaktv', 'momaliunited': 'MOMALI / ANTV',
    'ANTVtv': 'ANTV', 'RTVChiInfo': 'RTV',
    'inewsdotid': 'iNews', 'rctiofficial': 'RCTI',
    'JawaPosTV': 'Jawa Pos TV', 'NET.': 'NET.',
    'jtvbandung': 'JTV', 'Balivideo': 'Bali TV',
    'DhammaTV': 'Dhamma TV', 'JAK-ONE': 'JAK TV',
    # news/gov
    'CNBCIndonesiaTV': 'CNBC Indonesia', 'CNNIndonesiaTV': 'CNN Indonesia',
    'KPU': 'KPU RI Channel', 'TVParlemenRIdot': 'TV Parlemen DPR RI',
    'KemkomdigiRI': 'Kemenko PMK / Komdigi', 'KemendikbudRI': 'Kemendikbud RI',
    'BNPB_Indonesia': 'BNPB', 'DPRRI': 'DPR RI', 'Setpres': 'Setpres',
    # local/other
    'JogjaTV': 'Jogja TV', 'padangtv': 'Padang TV', 'Malangtv': 'Malang TV',
    'BandungTV': 'Bandung TV', 'Faktanews': 'Fakta News',
    'CitrangTV': 'Citrang TV', 'KLXtv': 'KLX TV',
    'suarasurabayamedia': 'Radio Suara Surabaya',
}

TITLE_BLOCK = re.compile(
    r'\b(lirik|karaoke|clip video|video clip|full album|podcast|talkshow|talk show|'
    r'sinetron|film|series|teaser|trailer|highlights|gol|seleksi|qualification|'
    r'laporan|breaking|berita (?!terkini)|full match|live (?:report|drawing))\b', re.I)

def probe(item):
    handle, name = item
    url = f'https://www.youtube.com/@{handle}/live'
    try:
        out = subprocess.run(
            ['yt-dlp', '--dump-single-json', '--no-warnings', '--skip-download',
             '--no-playlist', url],
            capture_output=True, text=True, timeout=90)
        if out.returncode != 0:
            return {'handle': handle, 'name': name, 'ok': False, 'err': out.stderr.strip()[:200]}
        d = json.loads(out.stdout)
        title = d.get('title', '')
        is_live = bool(d.get('is_live'))
        entry = {
            'handle': handle, 'name': name, 'video_id': d.get('id'),
            'title': title, 'channel': d.get('channel'), 'is_live': is_live,
            'duration': d.get('duration'), 'url': url,
            'ok': is_live and not TITLE_BLOCK.search(title),
        }
        if not entry['ok'] and not is_live:
            entry['err'] = 'not live'
        elif not entry['ok']:
            entry['err'] = 'title blocked: ' + title[:80]
        return entry
    except Exception as e:
        return {'handle': handle, 'name': name, 'ok': False, 'err': str(e)[:200]}

def main():
    items = list(CANDIDATES.items())
    res = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(probe, items):
            mark = 'OK ' if r.get('ok') else '-- '
            print(mark, r['handle'], '|', r.get('video_id'), '|',
                  (r.get('title') or r.get('err', ''))[:80], flush=True)
            res.append(r)
    json.dump(res, open('data/yt_live.json', 'w'), indent=1)
    print('live:', sum(1 for r in res if r['ok']), '/', len(res))

if __name__ == '__main__':
    main()
