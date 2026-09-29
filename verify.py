#!/usr/bin/env python3
"""Verify IPTV streams: fetch manifest, follow master->variant, report live + peak bitrate."""
import json, re, sys, socket, subprocess, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

socket.setdefaulttimeout(20)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def fetch(url, headers=None, maxlen=65536):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(maxlen), dict(r.headers)

def resolve_youtube(url):
    """Return the best HLS master for a youtube watch/live URL, or None."""
    r = subprocess.run(["yt-dlp", "-f", "bv*+ba/best", "--no-playlist", "-g", url],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return None
    return r.stdout.strip().splitlines()[0] if r.stdout.strip() else None

def check(entry):
    url = entry["url"]
    hdrs = {}
    if entry.get("http-referrer"): hdrs["Referer"] = entry["http-referrer"]
    if entry.get("http-user-agent"): hdrs["User-Agent"] = entry["http-user-agent"]
    out = dict(entry, ok=False, err=None, bitrate=None)
    if "youtube.com/" in url:
        m3u8 = resolve_youtube(url)
        if not m3u8:
            out["err"] = "yt-dlp resolve failed / not live"
            return out
        url = entry["url"] = m3u8   # probe the resolved master below
        hdrs = {"User-Agent": UA}
        entry["http-referrer"] = entry["http-user-agent"] = None
    try:
        body, _ = fetch(url, hdrs)
        text = body.decode("utf-8", "replace")
        if url.endswith(".mpd"):
            out["ok"] = "<MPD" in text
            # DRM-encrypted DASH is unplayable without a license in OTT
            # Navigator / stock VLC, so those rows are dead weight even though
            # the manifest serves fine. Evidence, strongest first:
            #   <cenc:pssh> present, or Widevine/PlayReady system-ID UUID,
            #   or mp4protection scheme carrying a default_KID,
            #   or a 'tenc' box in the init segment with default_IsEncrypted=1.
            if out["ok"] and "ContentProtection" in text:
                low = text.lower()
                drm = ("pssh" in low
                       or "edef8ba9-79d6-4acea-3c8d77d2fbdc" in low      # Widevine
                       or "9a04f079-9840-4286-ab92-e65be0885f95" in low)  # PlayReady
                if not drm:
                    m = re.search(r'urn:mpeg:dash:mp4protection:2011"[^>]*'
                                  r'default_KID="', text)
                    drm = bool(m)
                if not drm:
                    init = re.search(r'initialization="([^"]+)"', text)
                    rep = re.search(r'<Representation[^>]*\bid="([^"]+)"', text)
                    if init:
                        iu = urllib.parse.urljoin(
                            url, init.group(1).replace(
                                "$RepresentationID$", rep.group(1) if rep else ""))
                        try:
                            ib, _ = fetch(iu, hdrs, 16384)
                            j = ib.find(b"tenc")
                            if j >= 0:
                                # fullbox: ver(1)+flags(3), 6 reserved, [v>=1: iv_size(2)],
                                # KID(16), default_IsEncrypted(1)+reserved(1)+IV(8)
                                k = j + 4 + 4 + 6
                                if ib[j + 4] >= 1:
                                    k += 2
                                k += 16
                                if k < len(ib) and ib[k]:
                                    drm = True
                        except Exception:
                            pass   # init unfetchable: cannot confirm, keep live
                if drm:
                    out["ok"] = False
                    out["err"] = "drm-encrypted (license required)"
                    out["bitrate"] = None
        elif "#EXTM3U" in text[:200]:
            out["ok"] = True
            streams = re.findall(r"#EXT-X-STREAM-INF:BANDWIDTH=(\d+)", text)
            if not streams:
                streams = re.findall(r"#EXT-X-STREAM-INF:", text)  # attribute-order agnostic
            if len(streams) > 1:  # master: probe top variant
                m = re.search(r"#EXT-X-STREAM-INF:BANDWIDTH=(\d+)[^\n]*\n([^\n]+)", text)
                if m:
                    out["bitrate"] = int(m.group(1))
                    var = m.group(2).strip()
                    vurl = urllib.parse.urljoin(url, var)
                    vbody, _ = fetch(vurl, hdrs, 32768)
                    vt = vbody.decode("utf-8", "replace")
                    vt_ok = "#EXTM3U" in vt and ("EXTINF" in vt or "EXT-X-ENDLIST" in vt or "EXT-X-TARGETDURATION" in vt)
                    vsegs = re.findall(r"#EXTINF:([\d.]+)", vt) if vt_ok else []
                    out["ok"] = vt_ok and len(vsegs) > 0
                    if not out["ok"]:
                        out["err"] = "variant-broken" 
            else:
                segs = re.findall(r"#EXTINF:([\d.]+)", text)
                media = re.findall(r"#EXT-X-MEDIA-SEQUENCE", text)
                out["ok"] = ("EXT-X-TARGETDURATION" in text or bool(media)) and len(segs) > 0
                # A live playlist can lie: dens.tv serves stale manifests whose
                # segment URLs all 404 (frozen PROGRAM-DATE-TIME). Confirm the
                # LAST segment actually downloads; unfetchable => not live.
                if out["ok"] and media:
                    seg = next((l for l in reversed(text.splitlines())
                                if l and not l.startswith("#")), None)
                    if seg:
                        try:
                            fetch(urllib.parse.urljoin(url, seg.strip()), hdrs, 188)
                        except Exception as e:
                            # signed/live CDNs prune old chunks: the LAST listed
                            # segment can 404 in a race with the encoder. A 404
                            # on the last segment is retryable noise for
                            # youtube-resolved rows; anything else is stale.
                            if not (isinstance(e, urllib.error.HTTPError)
                                    and e.code in (403, 404)
                                    and "googlevideo" in url):
                                out["ok"] = False
                                out["err"] = f"stale-playlist ({type(e).__name__})"
        elif body[:1] == b"\x47" and len(body) >= 376 and body[188:189] == b"\x47":
            # raw MPEG-TS (hometv-style auth redirects serve TS directly):
            # 0x47 sync byte on consecutive 188-byte packets = live transport stream
            out["ok"] = True
        else:
            out["err"] = "no-m3u8-marker"
    except Exception as e:
        out["err"] = f"{type(e).__name__}: {str(e)[:120]}"
    return out

def main():
    src, dst = sys.argv[1], sys.argv[2]
    entries = json.load(open(src))
    results = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(check, e): e for e in entries}
        for f in as_completed(futs):
            results.append(f.result())
    json.dump(results, open(dst, "w"), indent=1)
    ok = sum(1 for r in results if r["ok"])
    print(f"DONE {dst}: {ok}/{len(results)} live")

if __name__ == "__main__":
    main()
