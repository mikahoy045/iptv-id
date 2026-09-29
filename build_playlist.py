#!/usr/bin/env python3
"""Build the final Indonesia IPTV playlist from verified stream data.

Usage: python3 build_playlist.py data/verified2.json tv_indonesia.m3u

Gate (a channel lands in the playlist iff):
  - live: entry.ok from verify.py (manifest actually served segments NOW)
  - Indonesian: tvg-id in the iptv-org ID registry, or host is an .id /
    known Indonesian CDN domain, or name on the curated allow-list
  - not on the foreign-network blocklist
One row per channel (dedup by stream path then canonical name; best source wins).
"""
import json, re, sys, datetime, collections
from urllib.parse import urlparse

REGISTRY = {c['id'].lower(): c for c in json.load(open('data/iptvorg_channels.json'))
            if c['country'] == 'ID'}

ID_HOSTS = re.compile(
    r'(tvri\.go\.id|siar\.us|dens\.tv|vidio\.com|vidiocdn\.com|transvision'
    r'|mncvision|indihome|maxstream|medcom\.id|daaiplus|rodja\.live|jogjatv|staratv|salira'
    r'|carubantv|lingkartv|hgmtv|convergen|asianastream|tvstreamcast|webcache\.maxindo'
    r'|globaldigitalcore|u-channel\.tv|gunadarma|tvku\.tv|rinjanitv'
    r'|suarasurabaya|efarinatv|salamtelevisi|madu\.tv|naajiyatv|abtelevisi|aliman\.id'
    r'|aktvuhfdigital|afbtv|matrixtv|mgstv|youtv\.live|intechmedia|tunnel\.my'
    r'|radartv|dhohotv|smtv\.digital|nusantaratv|i-news\.tv|beetv\.my\.id'
    r'|carubantv\.id|salira\.tv|lingkartv\.my\.id|bpmedialive'
    r'|indonusa\.id|dhammaweb|albahjah|kitv|dhisway|wahyu1ptv'
    r'|pages\.dev|workers\.dev)')
ID_TLD = re.compile(r'\.id$|\.id:')

CURATED_OK = re.compile(
    r'(hanacaraka|jawapos|dex ?tv|jek ?tv|\bk ?tv\b|ficom'
    r'|magna|music information|\bmic\b|indonesiana|tv ?mu\b|rri net|dzakara|tv ?9'
    r'|nabawi|bahjah|rajamitra|elta|\binsert\b|\bmoji\b|sindonews|sin ?po'
    r'|metro globe|\bbn ?channel\b|\bidx ?channel\b|vision prime|channel jowo'
    r'|bioskop indonesia|dunia (anak|lain)|mentari|cartoon tv'
    r'|\bdens\b)\b', re.I)

# foreign networks (restreamed into ID packages) — user asked for Indonesian channels
FOREIGN = re.compile(
    r'(^|[\s\(\[])(ABC Australia|CBeebies|BBC|Fashion ?TV|TV ?[58]|CCTV|CGTN|Phoenix'
    r'|History|H2|Lifetime|Oxygen|Love ?Nature|Muslim TV|MCC|Sheherazade'
    r'|HBO|Cinemax|AXN|Warner|Nickelodeon|Nick ?(Toons|Junior)|Cartoon Network'
    r'|Boomerang|Disney|Baby ?First|Animal Planet|Discovery|Nat ?Geo|NHK|Arirang|KBS|JTBC'
    r'|tvN|Eurosport|DAZN|TSN|FOX ?(SPORTS|MOVIES|NFP)|Sky ?Sports|be ?IN( ?SPORTS)?'
    r'|ESPN|Tennis|Golf|MotoGP|F1|Fubo|Nova ?Sport|Sport ?TV|S ?Sports|SportsOne|TNT'
    r'|ACC|WWE|UFC|Now ?News|Bloomberg|France ?24|DW|Al ?Jazeera|RT|TRT|SPOTV'
    r'|Mezzo|Sting ?brary|Classical|KIX|Zee|Cinema ?Asia'
    r'|Hinaya|Sadan|NBT|TVBI|Leomixer|WBTV|SBS|KCN|Telenovela|Max ?Sports|Cinema ?World)(?![a-z])', re.I)

# foreign premium networks the user explicitly asked to keep (the Asia/ID feeds
# carried by Indonesian pay-TV packages). iptv-org registers none of these under
# country=ID, so the FOREIGN gate would otherwise drop them. Keep this list
# minimal: add an id only on a direct user request.
PREMIUM_OK = {'axn.id', 'axnasia.sg', 'hboasia.sg', 'hbohitsasia.sg',
              'hbosignatureasia.sg', 'hbofamilyasia.sg', 'kix.hk',
              'ewtn.us', 'angeltv.id', 'angeltv.in', 'cgntv.id',
              'warner.id', 'starmovies.id', 'celestialmovies.id', 'mnplus.id', 'cinemax.id'}  # user-requested christian + premium
BAD_NAME = re.compile(r'^(auto|plex\.tv|[a-z]+\.tv)\b|^\d{1,4}[pi]$|\.(mpd|m3u8)$|^\[|^\W+$|^\s*$')

REGION_ALIAS = {
    'North Sumatra': 'Sumatera Utara', 'West Sumatra': 'Sumatera Barat',
    'South Sumatra': 'Sumatera Selatan', 'East Java': 'Jawa Timur',
    'Central Java': 'Jawa Tengah', 'West Java': 'Jawa Barat',
    'East Kalimantan': 'Kalimantan Timur', 'West Kalimantan': 'Kalimantan Barat',
    'Central Kalimantan': 'Kalimantan Tengah', 'South Kalimantan': 'Kalimantan Selatan',
    'North Sulawesi': 'Sulawesi Utara', 'Central Sulawesi': 'Sulawesi Tengah',
    'South Sulawesi': 'Sulawesi Selatan', 'Southeast Sulawesi': 'Sulawesi Tenggara',
    'West Sulawesi': 'Sulawesi Barat', 'East Nusa Tenggara': 'Nusa Tenggara Timur',
    'West Nusa Tenggara': 'Nusa Tenggara Barat', 'West Papua': 'Papua Barat',
}

GROUP_OVERRIDE = [
    (re.compile(r'(?i)^tvri'), 'TVRI'),
    (re.compile(r'(?i)\b(rcti|mnctv|gtv|inews|magna)\b'), 'MNC'),
    (re.compile(r'(?i)\b(sctv|indosiar|mentari|moji|nusantara tv|insert)\b'), 'Emtek'),
    (re.compile(r'(?i)\b(trans ?7|trans ?tv|cnbc|cnn indonesia|detik)\b'), 'Trans'),
    (re.compile(r'(?i)\b(beritasatu|berita satu|btv|metro tv|metro globe|tvone|idx|sindo|jawapos)\b'), 'News'),
    (re.compile(r'(?i)\b(antv|kompas|rtv|net\.? tv|jak ?tv|jtv|bdbtv|balikpapan)\b'), 'National'),
    (re.compile(r'(?i)(sport|thri?i?l|champion|ficom)'), 'Sports'),
    (re.compile(r'(?i)(^dens|dens\b|lifestyle|food channel|hanacaraka|life & style|fashion)'), 'Lifestyle'),
    (re.compile(r'(?i)(cartoon|dunia anak|my kid|kids)'), 'Kids'),
    (re.compile(r'(?i)(bioskop|cinema|celestial|vision prime|^life$|\b(axn|hbo|kix|cinemax|warner)\b|star movies|mn\+)'), 'Movies'),
    (re.compile(r'(?i)(daai|wafa|im ?channel|madani|puja|salam|nabawi|bahjah|dzakara|tv ?mu|rree|rodja|tawaf|surau|ahsan|mqtv|mgi|religi|dakwah)'), 'Religious'),
    (re.compile(r'(?i)(ewtn|angel tv|cgntv|reformed|hope channel|vatican|katholic|catholic)'), 'Religious'),
    (re.compile(r'(?i)\b(discovery|national geographic|nat geo|animal planet|history|bbc earth|love nature|crime investigation|cgtn documentary|inwild|wild planet|wild earth|adventure earth)\b'), 'Documentary'),
    (re.compile(r'(?i)\b(bbc news|cnn inter|sky news|al jazeera|dw english|france 24|cnbc asia|bloomberg|\bcna\b|nbc news|rt english|euro news|gb news|cbc news|tv5 monde info|cgtn)\b'), 'News'),
    (re.compile(r'(?i)(cartoon network|nickelodeon|nick jr|dreamworks|aniplus|cartoonito|baby tv|cbeebies|moonbug|zoomoo|duck tv|planet fun|\banimax\b)'), 'Kids'),
    (re.compile(r'(?i)(movies now|\bmnx\b|sony pix|\bhits\b|hits movies|studio universal|\bflik\b|\bimc\b|rock action|rock entertainment|cinema world|\bthrill\b|\bboo\b|showchase|\bgalaxy\b|galaxy premium)'), 'Movies'),
    (re.compile(r'(?i)(motogp|tennis channel|dazn|\bf1\b|f1 tv|golf channel|sky golf|ziggo golf|ziggo tennis|super tennis|tsn f1|sky f1|vsport|m golf|t2 tennis)'), 'Sports'),
    (re.compile(r'(?i)(lifetime|hgtv|\btlc\b|drama hebat|film mantap|nhk world|kbs world|e! entertainment|\bboo\b|arirang|citra drama|\bk plus\b|tv5 monde|abc australia|citra entertainment)'), 'General'),
]

LOCAL_RE = re.compile(r'(?i)(aceh|bali|bandung|banjar|batam|banten|blitar|bojonegoro|'
    r'cirebon|gorontalo|jambi|jogja|yogyakarta|kediri|kupang|lampung|madiun|madura|malang'
    r'|manado|mataram|medan|padang|palangka|palembang|papua|pontianak|riau|sampit|samarinda'
    r'|semarang|surabaya|sulawesi|sumatra|tasik|ternate|NTT|NTB|Jateng|Jatim|Jabar'
    r'|Kalimantan|Sumsel|Sumbar|Maluku|daerah|radar|stara|puja|duta|madu|smtv|tvku|ugtv'
    r'|salira|dhoho|caruban|matrix|sangaji|tabalong|jawa pos|efarina|mgstv|lingkar'
    r'|garuda|sriwijaya|humabetang|huma betang|atambua|kawanua|kilisuci|selaparang'
    r'|jelita|bms|bengkulu|celebes|sultra|pontv|magelung|banyuwangi|lombok|samosir'
    r'|battang|kalsel|tegartv|banyumas|purnama|slamtv|saka|padjadjaran|nusa\s?tv'
    r'|jptv|sragen|wonosobo|purwokerto|batang|kendal|demak|grobogan|blora|tuban'
    r'|lamongan|gresik|sidoharjo|bondowoso|lumajang|pasuruan|probolinggo|situbondo'
    r'|jember|tulangbawang|pesawaran|pringsewu|pagelaran|pacitan|trenggalek|nganjuk'
    r'|ngawi|magetan|ponorogo|sampang|bangkalan|pamekasan|sumenep|sukabumi|cianjur'
    r'|sumedang|parahyangan|bojone|brebes|tegal|pekalongan)')

CATMAP = {'news': 'News', 'sports': 'Sports', 'kids': 'Kids', 'religious': 'Religious',
          'music': 'Music', 'movies': 'Movies', 'series': 'Movies',
          'documentary': 'Documentary', 'education': 'Documentary',
          'legislative': 'Government', 'lifestyle': 'Lifestyle', 'cooking': 'Lifestyle',
          'business': 'News', 'weather': 'General', 'shop': 'General'}

def group_for(name, reg):
    for rx, g in GROUP_OVERRIDE:
        if rx.search(name):
            return g
    if reg and reg.get('categories'):
        c = reg['categories'][0]
        if c in CATMAP:
            return CATMAP[c]
    return 'Local' if LOCAL_RE.search(name) else 'General'

QUAL = re.compile(r'\((\d{3,4})\s*[piPI]\)|\b(\d{3,4})\s*[piPI]\b')
BRACKET = re.compile(r'\[[^\]]*\]')
STRAY = re.compile(r'(?i)\b(Transcorp|Channel ?Feed|Vidio|DensTV|Dens ?TV|Indihome'
                   r'|First ?Media|Flash ?con|Flashcon|Maxstream|MNC Vision|Alt ?\d*'
                   r'|Backup|Official|LIVE|Geo[- ]?block(?:ed)?|24/7|cdn ?\d+|try ?\d*)\b')

NOISE_PAREN = re.compile(r'(?i)^[\s|]*(\d{1,4}\s*[piPI]?|HD|FHD|SD|LQ|HQ|LIVE|Official'
                         r'|Backup|Alt ?\d*|Eng\.? ?\d*|V\+|not 24/7|try ?\d*|geo[- ]?block(?:ed)?'
                         r'|transcorp|channel ?feed|vidio|dens ?tv|indihome|first ?media'
                         r'|flash ?con|maxstream|mnc ?vision|undefined|dash(/ ?mpd)?|mpd|\d+)[\s|]*$')

def strip_noise(n):
    n = BRACKET.sub(' ', n)
    def repl(m):
        inner = m.group(0)[1:-1]
        return ' ' if NOISE_PAREN.fullmatch(inner) or STRAY.search(inner) else m.group(0)
    for _ in range(4):
        nn = re.sub(r'\([^()]*\)', repl, n)
        if nn == n:
            break
        n = nn
    n = UNBALANCED.sub(' ', n)
    n = QUAL.sub(' ', n)
    n = STRAY.sub(' ', n)
    n = re.sub(r'(?i)\s*\bHD\b', ' ', n)
    return re.sub(r'\s+', ' ', n).strip(' -·|,.()')

UNBALANCED = re.compile(r'\([^()]*$')

CANON = {  # nkey-normalized spellings that must collapse into one row
    'showchaseennosub': 'Showchase',
    'beritasatu': 'BTV',
    'rctvindonesia': 'RCTV',
    'dhohotvkediri': 'Dhoho TV',
    'thriil': 'Thrill',
    'suarasurabayavisualradiosurabaya': 'Suara Surabaya Visual Radio',
    'magnatv': 'Magna Channel',
}

def clean_name(e):
    """Canonical display name; keeps region suffixes (@Jakarta) that distinguish feeds."""
    n = strip_noise(e.get('name', '') or '')
    tvg = e.get('tvg-id', '') or ''
    base, _, region = tvg.partition('@')
    reg = REGISTRY.get(base.lower())
    for eng, ind in REGION_ALIAS.items():
        n = n.replace(eng, ind)
    key = re.sub(r'[^a-z0-9]', '', n.lower())
    if key in CANON:
        n = CANON[key]
    if reg:
        rkey = nkey(reg['name'])
        key = nkey(n)
        if region and region not in ('SD', 'HD', 'FHD', ''):
            # TVRI.id@Jakarta -> 'TVRI Jakarta' (URL-dedup keeps one row per feed)
            if key.startswith(rkey) or not n:
                n = f"{reg['name']} {region.capitalize()}"
        else:
            same = key == rkey or (key.startswith(rkey) and len(key) <= len(rkey) + 3) \
                   or (rkey.startswith(key) and len(key) <= len(rkey))
            if not n or same:
                n = reg['name']   # canonical registry spelling (MNCTV, Insert, ...)
    return CANON.get(nkey(n), n)

def url_key(e):
    """Same feed path (+ channel-selecting query) = same feed regardless of name."""
    url = e['url']
    m = re.search(r'ott-balancer\.tvri\.go\.id/live/eds/([^/]+)/', url)
    if m:
        return 'tvri-' + m.group(1).lower()
    p = urlparse(url)
    ch = re.search(r'(?:^|&)(ch|chname|channel|c)=([^&]+)', p.query or '')
    q = '?' + ch.group(2).lower() if ch else ''
    return (p.netloc + p.path + q).lower()

def nkey(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def score(e):
    url = e['url']
    s = 0
    if e.get('bitrate'): s += 20000 + e['bitrate'] / 100000
    q = QUAL.search(e.get('name', ''))
    if q: s += int(q.group(1) or q.group(2))
    host = urlparse(url).hostname or ''
    if 'tvri.go.id' in url: s += 500
    if ID_TLD.search(host) or 'siar.us' in host: s += 300
    elif ID_HOSTS.search(host): s += 250
    if url.startswith('https'): s += 150
    if 'workers.dev' in url or 'pages.dev' in url: s -= 400
    if re.search(r':8000/play/', url): s -= 350
    if '.mpd' in url: s -= 60
    if 'beetv.my.id' in url: s = -50   # flaky rate-limited proxy: never outranks an official CDN (stored bitrate would)
    if 'youtube.com' in url: s -= 40
    return s

def is_indonesian(e):
    if e.get('source') in ('hometv.ts', 'alt-fashion', 'ftv-official'):
        return True              # user-approved additions (hometv panel + alternates)
    name = (e.get('name', '') or '') + ' ' + (e.get('tvg-id', '') or '')
    base = (e.get('tvg-id', '') or '').split('@')[0].lower()
    if base in REGISTRY: return True          # iptv-org country=ID is authoritative
    if base in PREMIUM_OK: return True        # user-requested premium exception
    host = urlparse(e['url']).hostname or ''
    if ID_TLD.search(host) or 'siar.us' in host or ID_HOSTS.search(host): return True
    if CURATED_OK.search(name): return True
    return False

PRIORITY = {'MNC': 0, 'Emtek': 1, 'Trans': 2, 'National': 3, 'News': 4,
            'Sports': 5, 'Movies': 6, 'Kids': 7, 'Music': 8, 'Lifestyle': 9,
            'Documentary': 10, 'Religious': 11, 'Local': 12, 'Government': 13,
            'General': 14, 'YouTube': 15, 'TVRI': 16}

def main():
    vered = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    live = [e for e in vered if e.get('ok') and is_indonesian(e)]
    by_url = {}
    for e in live:                       # collapse identical feed paths first
        k = url_key(e)
        if k not in by_url or score(e) > score(by_url[k]):
            by_url[k] = e
    best = {}
    for e in by_url.values():
        disp = clean_name(e)
        base = (e.get('tvg-id', '') or '').split('@')[0].lower()
        reg = REGISTRY.get(base)          # registry id is authoritative; skips FOREIGN
        if (not disp or BAD_NAME.match(disp)
                or (e.get('source') not in ('hometv.ts', 'alt-fashion', 'ftv-official')
                    and not reg and base not in PREMIUM_OK and FOREIGN.search(disp))):
            continue
        k = nkey(disp)
        cand = best.get(k)
        if cand is None or score(e) > score(cand[1]):
            best[k] = (disp, e)
    rows = []
    for disp, e in best.values():
        base = (e.get('tvg-id', '') or '').split('@')[0].lower()
        reg = REGISTRY.get(base)
        grp = group_for(disp, reg)
        rows.append((PRIORITY.get(grp, 16), disp.lower(), disp, e, reg, grp))
    try:
        yt = json.load(open('data/yt_channels.json'))
    except (OSError, ValueError):
        yt = []
    for c in yt:
        disp = c['name'] + ' (YouTube)'
        e = {'url': c['watch'], 'tvg-id': c['tvg-id'],
             'tvg-logo': c.get('logo', '')}
        rows.append((PRIORITY['YouTube'], c['name'].lower(), disp, e, None, 'YouTube'))
    rows.sort()
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    lines = [f'#EXTM3U generated-at="{now}"']
    n = 0
    for _, _, disp, e, reg, grp in rows:
        tvg_id = e.get('tvg-id') or (reg['id'] if reg else re.sub(r'[^A-Za-z0-9]', '', disp) + '.id')
        attrs = f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{disp}" tvg-chno="{n+1:03d}"'
        if e.get('tvg-logo'): attrs += f' tvg-logo="{e["tvg-logo"]}"'
        lines.append(attrs + f' group-title="{grp}",{disp}')
        if e.get('http-referrer'): lines.append('#EXTVLCOPT:http-referrer=' + e['http-referrer'])
        if e.get('http-user-agent'): lines.append('#EXTVLCOPT:http-user-agent=' + e['http-user-agent'])
        lines.append(e['url'])
        n += 1
    open(out, 'w').write('\n'.join(lines) + '\n')
    groups = collections.Counter(r[5] for r in rows)
    print(f'{out}: {n} channels')
    for g in sorted(groups, key=lambda g: PRIORITY.get(g, 16)):
        print(f'  {groups[g]:4}  {g}')

if __name__ == '__main__':
    main()
