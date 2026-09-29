# Indonesia IPTV Playlist

`tv_indonesia.m3u` — ONE file with everything: 221 channels (216 direct
CDN feeds plus 5 official YouTube 24/7 streams), every URL
live-verified at build time (2026-09-27). Indonesian-registry channels only,
plus the user-requested premium exceptions below. Every shipped URL is
DRM-free (no Widevine/PlayReady) — encrypted pay-TV DASH feeds are rejected
by the verifier because OTT Navigator/VLC cannot decrypt them.

## Christian-first Religious (per user request, 2026-09-27)

All Muslim/dakwah channels were removed at the user's request (MQTV, MTA TV,
Madani TV, Salam TV, TVMU/Muhammadiyah, Izzah TV, Al-Iman TV, Ahsan TV,
Al Wafa Tarim, DMI TV/Tawaf, I Am Channel). The Religious group now carries:
**EWTN** (Asia-Pacific + Africa-Asia, Catholic), **CGNTV Asia** (Christian),
**Angel TV Indonesia** (Christian), **DAAI TV** (Tzu Chi Buddhist),
**Dhamma TV** (Buddhist), **Puja TV Aceh**. Vatican Media / Solusi TV /
Life TV Asia / Hope Channel Indonesia had no verifiable live DRM-free feed
(probed 2026-09-27); Reformed 21 is YouTube-only.

## Groups (in playlist order)

| Group | Ch. | Contents |
|---|---|---|
| MNC | 5 | RCTI, MNCTV, GTV, iNews, Magna Channel |
| Emtek | 5 | SCTV, Indosiar, Moji, Mentari TV, Nusantara TV |
| Trans | 4 | Trans TV, Trans7, CNN Indonesia, CNBC Indonesia |
| National | 5 | ANTV, Kompas TV, RTV, Jak TV, JTV |
| News | 24 | Metro TV, tvOne, BTV, IDX Channel, Sindo News TV + BBC/CNN Int/Sky News/Al Jazeera/France 24/DW/CNBC Asia/Bloomberg/CNA/RT/GB/CBC/NBC News Now/CGTN/EuroNews/TV5 Monde Info |
| Sports | 19 | MAX Sports, Thrill, Ficom Channel + MotoGP (HD/FHD), F1 (TV/DAZN/Sky IT/TSN/Sky UK), Tennis (Channel/T2/Super/Ziggo), Golf (Channel/Sky UK/Ziggo/VSport/M) |
| Movies | 29 | HBO (x4), Cinemax, Star Movies (x2), KIX, AXN, AXN Asia, Warner TV, Celestial Movies, MN+, Zee Bioskop + Movies Now, MNX, Sony Pix, Hits (x2), Studio Universal, Flik, IMC, Rock Action/Entertainment, Cinema World, Thrill, Boo, Showchase, Galaxy (x2) |
| Kids | 12 | Cartoon Network, Nickelodeon/Nick Jr, DreamWorks, Animax, Aniplus, Cartoonito, Moonbug, Zoomoo, Duck TV, Planet Fun, My Kidz |
| Documentary | 14 | Discovery Channel, National Geographic (+Wild), Animal Planet, History, BBC Earth, Love Nature, Crime Investigation, Discovery Asia, CGTN Documentary, InWild/Wild Planet/Wild Earth/Adventure Earth |
| Entertainment additions | 10 | Lifetime, HGTV, TLC, E!, NHK World Premium, KBS World, Drama Hebat, Film Mantap, ABC Australia, Arirang (in General) |
| Movies | 13 | HBO (x4), Cinemax, Star Movies (x2), KIX, AXN, AXN Asia, Warner TV, Celestial Movies, MN+, Zee Bioskop |
| Kids | 1 | My Kidz |
| Lifestyle | 4 | Dens Food/ShowBiz/Life & Style/Learning & Knowledge |
| Documentary | 2 | National Geographic, National Geographic Wild |
| Religious | 7 | EWTN (x2), CGNTV Asia, Angel TV Indonesia, DAAI TV, Dhamma TV, Puja TV Aceh |
| Local | 32 | Bali TV, Jogja TV, Stara TV (x7), Jawa Pos TV, Garuda TV, PONTV, ... |
| Government | 1 | MBG TV |
| General | 27 | RCTV, MDTV, PKTV, TATV, VTV, dTVi, Persija TV, ... + Lifetime, HGTV, TLC, E!, NHK World Premium, KBS World, Drama Hebat, Film Mantap, ABC Australia, Arirang, Citra Drama, K Plus, TV5 Monde (x2) |
| YouTube | 5 | tvOne, Kompas TV, IDX Channel, Metro TV, TVRI Nasional - official 24/7 streams |
| TVRI | 33 | TVRI Nasional + all 31 provinces, Sport, World (isolated group, last) |

## Premium exceptions (user-requested, clear feeds only)

Premium channels ship as explicit exceptions to the Indonesian-only gate:
`build_playlist.py:PREMIUM_OK` lists the exception tvg-ids (premium +
Christian channels). Sources are license-free: HBO/HBO Family/HBO Hits/
HBO Signature/Cinemax/Star Movies/Star Movies Select/KIX/Warner TV/
Celestial Movies/MN+ stream as unencrypted MPEG-TS via hometv.biz.id
(scramble-flag 0 verified per row 2026-09-27); AXN via Vidio's clear proxy
DASH; AXN Asia via its panel feed (probe-restricted, user-confirmed). The
TransVision/Vision+/IndiHome DASH variants of these channels are
Widevine/PlayReady-encrypted and are rejected — a stream your player cannot
decrypt is a broken stream. Same for SPOTV, Sportstars, Bioskop Indonesia,
Cartoon TV/Cartoonito, Kids TV, Music TV, Muslim TV, HANACARAKA, Galaxy
Premium, Vision Prime, Life, Dunia Anak/Lain and Insert: their only feeds
require a license. "HBO Max" is a streaming app, not a linear channel.

The `.mpd` rows in this playlist are unencrypted DASH: VLC, TiviMate and
OTT Navigator play them directly.

Discovery Channel is also NOT included: no live Indonesian feed exists on
any reachable source right now (IndiHome, Vision+, TransVision, and every
pirate CDN probed dead on 2026-09-27). Its documentary siblings National
Geographic and National Geographic Wild are live and shipped.

## Loading

- **TiviMate / IPTV Smarters / GSE Smart IPTV**: add as playlist from file
  (upload to a web host or use a local-file side-loading option).
- **VLC**: `Media → Open Network Stream` per URL, or open the `.m3u` and
  browse. `#EXTVLCOPT` referrer/user-agent lines are honored by VLC,
  TiviMate and ExoPlayer-based players — required for the MNC (beetv) feeds.
- Some feeds are DASH (`.mpd`): VLC and TiviMate play them; a few plain-HLS-only
  players may not.
- SCTV / ANTV / Moji ship via a Vidio clear-DASH proxy (pages.dev) after the
  dens.tv playlists went stale; Indosiar stays on dens (verified fresh).
- `YouTube` group rows are `youtube.com/watch` links: fine in TiviMate/VLC/
  smart-TV apps (they hand off to their YouTube engine), skipped by dumb
  HLS-only boxes.

## Rebuilding

```
# 1. collect candidate streams (raw M3Us in data/raw/ + data/raw2/ harvests,
#    GitHub search, iptv-org): see parse_m3u.py; new harvests merged into
#    data/verified2.json after batch-probing with verify.py
python3 parse_m3u.py data/raw/*.m3u8 data/raw/*.m3u > /dev/null   # writes data/gh_candidates.json
# 2. verify liveness (manifests must serve segments; DASH is additionally
#    rejected when it declares DRM - pssh, Widevine/PlayReady system-ID
#    UUIDs, or an encrypted tenc box in the init segment; youtube watch
#    URLs resolve via yt-dlp)
python3 verify.py data/candidates2.json data/verified2.json
# 3. refresh official YouTube 24/7 stream IDs (hourly pseudo-live events rotate)
python3 yt_refresh.py                                              # writes data/yt_channels.json
# 4. build grouped playlist (registry-gated Indonesian-only, dedupe, sort;
#    folds data/yt_channels.json into the YouTube group)
python3 build_playlist.py data/verified2.json tv_indonesia.m3u
```

`data/iptvorg_channels.json` is the country=ID registry used to gate names;
`build_playlist.py` also carries `FOREIGN` (hard block), `PREMIUM_OK`
(user-approved foreign exception), `CURATED_OK` (known-good Indonesian
brands) and `CANON` (name-collapsing) tables — edit those to change what
ships. `yt_live.py` is the discovery prober used to find new official
channel handles (`@<handle>/live`, rejects music/podcast titles).

URLs rotate/expire upstream; re-run steps 2-4 before distributing. The
verifier runs 16-wide and free proxies (beetv) can rate-limit it into false
negatives — re-probe failures serially before dropping a row.

## YouTube rows

The five `YouTube`-group entries (tvOne, Kompas TV, IDX Channel, Metro TV,
TVRI Nasional) are `https://www.youtube.com/watch?v=...` links to the
channels' official 24/7 streams — stable, player-resolvable URLs. Players
with YouTube support (smart-TV apps, TiviMate, VLC) open them directly.
Signed HLS master URLs also work but expire within hours and are IP-locked,
so they are NOT shipped. The video IDs themselves change when the channel
restarts its stream; `yt_refresh.py` re-probes and `build_playlist.py`
re-emits.
