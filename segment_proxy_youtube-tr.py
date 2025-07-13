import io, os, re, shutil, urllib.parse, requests, textwrap, logging
from typing import List, Dict, Optional
from flask import (Flask, request, Response, stream_with_context,
                   render_template_string, send_file, abort, redirect)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

# ───────────── Chrome helper ─────────────
def chrome_driver() -> webdriver.Chrome:
    chrome_bin = next(p for p in (
        shutil.which("google-chrome"),
        "/opt/google/chrome/google-chrome",
        os.path.expanduser("~/.var/app/com.google.Chrome/current/active/files/bin/google-chrome"))
        if p and os.path.exists(p))
    opts = webdriver.ChromeOptions()
    opts.binary_location = chrome_bin
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

# ───────────── YouTube helpers ─────────────
def dur2sec(t: str) -> int:
    p = list(map(int, t.split(":")))
    h, m, s = (p + [0, 0, 0])[-3:]
    return h * 3600 + m * 60 + s

def yt_search(q: str, flt: str) -> List[Dict]:
    drv = chrome_driver()
    out = []
    try:
        drv.get("https://www.youtube.com")
        drv.implicitly_wait(5)
        drv.find_element(By.NAME, "search_query").send_keys(q + Keys.RETURN)
        drv.implicitly_wait(5)
        for v in drv.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")[:12]:
            try:
                tt = v.find_element(By.ID, "video-title")
                vid = tt.get_attribute("href").split("v=")[1].split("&")[0]
                dur = v.find_element(By.CSS_SELECTOR, "ytd-thumbnail-overlay-time-status-renderer span").text.strip()
                s = dur2sec(dur) if dur else None
                if (flt == "short" and (s is None or s >= 240)) or \
                   (flt == "medium" and (s is None or s < 240 or s > 1200)) or \
                   (flt == "long" and (s is None or s <= 1200)):
                    continue
                out.append({"id": vid, "title": tt.text,
                            "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "dur": dur})
                if len(out) == 8:
                    break
            except:
                pass
    finally:
        drv.quit()
    return out

def yt_channels(q: str) -> List[Dict]:
    drv = chrome_driver()
    res = []
    try:
        drv.get("https://www.youtube.com")
        drv.implicitly_wait(5)
        drv.find_element(By.NAME, "search_query").send_keys(q + Keys.RETURN)
        drv.implicitly_wait(5)
        for c in drv.find_elements(By.CSS_SELECTOR, "ytd-channel-renderer")[:8]:
            try:
                img = c.find_element(By.CSS_SELECTOR, "img")
                res.append({"title": c.find_element(By.ID, "channel-title").text,
                            "url": c.find_element(By.ID, "main-link").get_attribute("href"),
                            "thumb": img.get_attribute("src") or img.get_attribute("data-thumb") or "",
                            "subs": c.find_element(By.ID, "subscribers").text})
            except:
                pass
    finally:
        drv.quit()
    return res

def channel_videos(url: str, limit: int = 36) -> List[Dict]:
    if not url.rstrip("/").endswith("/videos"):
        url = url.rstrip("/") + "/videos"
    with YoutubeDL({"quiet": True, "skip_download": True, "extract_flat": "in_playlist", "playlistend": limit}) as ydl:
        info = ydl.extract_info(url, download=False)
    return [{"id": e["id"], "title": e["title"],
             "thumb": f"https://i.ytimg.com/vi/{e['id']}/hqdefault.jpg",
             "dur": e.get("duration_string") or ""} for e in info.get("entries", [])[:limit]]

def hls_master_url(vid: str) -> Optional[str]:
    try:
        with YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        hls = [f for f in info["formats"] if f.get("ext") == "m3u8"]
        return max(hls, key=lambda f: f.get("height") or 0)["url"] if hls else None
    except Exception as e:
        logging.warning("yt-dlp HLS fetch failed: %s", e)
        return None

def progressive_url(vid: str) -> str:
    with YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
    prog = [f for f in info["formats"] if f["vcodec"] != "none" and f["acodec"] != "none" and f.get("ext") == "mp4"]
    if not prog:
        abort(404, "MP4 bulunamadı")
    return max(prog, key=lambda f: f.get("height") or 0)["url"]

# ───────────── Flask & HTML ─────────────
app = Flask(__name__)

HEAD = textwrap.dedent("""\
<!doctype html><html lang=tr><head>
<meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>YouTube Odak Modu</title>
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel=stylesheet>
<link href="https://vjs.zencdn.net/8.10.0/video-js.min.css" rel=stylesheet>
<link href="https://unpkg.com/@videojs/themes@1/dist/forest/index.css" rel=stylesheet>
<script src="https://vjs.zencdn.net/8.10.0/video.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1" defer></script>
<script src="https://cdn.jsdelivr.net/npm/videojs-hls-quality-selector@1.1.6/dist/videojs-hls-quality-selector.min.js" defer></script>
<style>
    .ratio-16-9{position:relative;padding-top:56.25%}.ratio-16-9>*{position:absolute;inset:0;width:100%;height:100%}
    .vjs-forest .vjs-control-bar { background-color: #2c3e50; }
    .vjs-forest .vjs-button > .vjs-icon-placeholder { color: #ecf0f1; }
    .vjs-forest .vjs-progress-control .vjs-progress-holder { background-color: #16a085; }
    .vjs-forest .vjs-play-progress { background-color: #1abc9c; }
    .vjs-forest .vjs-volume-level { background-color: #1abc9c; }
    .vjs-forest .vjs-slider { background-color: #34495e; }
    .vjs-forest .vjs-big-play-button { background-color: #1abc9c; border-color: #1abc9c; }
    .vjs-forest .vjs-big-play-button:hover { background-color: #16a085; border-color: #16a085; }
</style>
</head><body class="bg-gray-100 flex flex-col min-h-screen">""")
FOOT = "<footer class='text-center text-xs text-gray-500 my-4'>YouTube Odak Modu © 2025</footer></body></html>"

def nav(q="", flt="all"):
    opts = [("all", "Hepsi"), ("short", "Kısa <4dk"), ("medium", "Orta 4-20dk"), ("long", "Uzun >20dk")]
    return "<nav class='bg-indigo-600 fixed w-full z-20 shadow'><form method=post class='flex flex-wrap justify-center gap-2 p-4'>" + \
           f"<input name=query value='{q}' required class='flex-1 min-w-[200px] p-2 rounded' placeholder='YouTube'da ara...'>" + \
           "<select name=filter class='p-2 rounded'>" + \
           "".join(f"<option value={v} {'selected' if v == flt else ''}>{txt}</option>" for v, txt in opts) + \
           "</select><button class='bg-white text-indigo-600 font-semibold px-4 py-2 rounded'>Ara</button></form></nav>"

def page(body: str):
    return HEAD + body + FOOT

# ───────────── Routes ─────────────
@app.route("/", methods=["GET", "POST"])
def home():
    vids = chans = []
    if request.method == "POST":
        q = request.form["query"].strip()
        flt = request.form.get("filter", "all")
        vids = yt_search(q, flt)
        chans = yt_channels(q) if q else []
    else:
        q = ""
        flt = "all"
    chans_html = "".join(f"""
<a href="/channel?url={urllib.parse.quote(c['url'])}&name={urllib.parse.quote(c['title'])}"
 class="flex items-center gap-3 bg-white p-3 rounded shadow hover:shadow-lg transition">
 <img src="{c['thumb']}" class="w-12 h-12 rounded-full object-cover">
 <div><p class="font-semibold text-sm">{c['title']}</p>
      <span class="text-xs text-gray-500">{c['subs']}</span></div></a>""" for c in chans)
    vids_html = "".join(f"""
<div onclick="location='/play?video_id={v['id']}'"
 class="bg-white rounded shadow hover:shadow-lg flex flex-col cursor-pointer group">
  <div class='ratio-16-9'><img src="{v['thumb']}" class='object-cover rounded-t group-hover:opacity-80 transition'>
   <span class='absolute bottom-1 right-1 bg-black/70 text-xs text-white px-1 rounded'>{v['dur']}</span></div>
  <p class='p-3 font-semibold text-sm'>{v['title']}</p></div>""" for v in vids)
    body = nav(q, flt) + f"""
<main class='container mx-auto mt-28 px-4 flex-1'>
 {'<h2 class=text-lg font-semibold mb-2>Kanal Sonuçları</h2><div class="flex flex-wrap gap-4 mb-6">' + chans_html + '</div>' if chans_html else ''}
 {'<div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">' + vids_html + '</div>' if vids_html else '<p class=text-center text-gray-600 mt-20 text-lg>Arama yapın veya bir video seçin.</p>'}
</main>"""
    return page(body)

@app.route("/channel")
def channel():
    url = urllib.parse.unquote(request.args.get("url", ""))
    name = urllib.parse.unquote(request.args.get("name", "Kanal"))
    if not url:
        abort(400)
    vids = channel_videos(url)
    vids_html = "".join(f"""
<div onclick="location='/play?video_id={v['id']}'"
 class="bg-white rounded shadow hover:shadow-lg flex flex-col cursor-pointer group">
  <div class='ratio-16-9'><img src="{v['thumb']}" class='object-cover rounded-t group-hover:opacity-80 transition'>
   <span class='absolute bottom-1 right-1 bg-black/70 text-xs text-white px-1 rounded'>{v['dur']}</span></div>
  <p class='p-3 font-semibold text-sm'>{v['title']}</p></div>""" for v in vids)
    body = nav() + f"""
<main class='container mx-auto mt-28 px-4 flex-1'>
 <h2 class='text-lg font-semibold mb-4'>{name} – Videolar</h2>
 <div class='grid sm:grid-cols-2 lg:grid-cols-3 gap-6'>{vids_html}</div>
</main>"""
    return page(body)

@app.route("/play")
def play():
    vid = request.args.get("video_id")
    if not vid:
        abort(400, "Video ID is required")
    body = nav() + f"""
<main class='container mx-auto mt-28 px-4 flex-1'>
 <div class='flex justify-center'><div class='ratio-16-9 w-full md:w-4/5'>
  <video id="player" class='video-js vjs-theme-forest w-full h-full rounded-xl shadow-lg' controls autoplay></video>
 </div></div>
</main>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    const player = videojs('player');
    const hlsURL = '/hls/{vid}/master.m3u8';
    const mp4URL = '/proxy/{vid}';

    function setupMP4() {{
        player.src({{src: mp4URL, type: 'video/mp4'}});
        player.play();
    }}

    if (Hls.isSupported()) {{
        const hls = new Hls();
        hls.loadSource(hlsURL);
        hls.attachMedia(player.tech().el_);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {{
            player.hlsQualitySelector({{ displayCurrentQuality: true }});
            player.play();
        }});
        hls.on(Hls.Events.ERROR, (event, data) => {{
            if (data.fatal) {{
                setupMP4();
            }}
        }});
    }} else {{
        player.src({{src: hlsURL, type: 'application/x-mpegURL'}});
        player.one('error', setupMP4);
        player.one('loadedmetadata', () => {{
            player.hlsQualitySelector({{ displayCurrentQuality: true }});
        }});
    }}
}});
</script>"""
    return page(body)

# ───────────── Manifest proxy (never 404) ─────────────
@app.route("/hls/<vid>/master.m3u8")
def hls_master(vid):
    src = hls_master_url(vid)
    if not src:
        logging.info("No HLS manifest, redirecting to MP4")
        return redirect(f"/proxy/{vid}", 302)
    try:
        r = requests.get(src, timeout=15)
        if r.status_code >= 400:
            logging.info("HLS manifest %s returns %s, redirecting to MP4", src, r.status_code)
            return redirect(f"/proxy/{vid}", 302)
        txt = r.text
    except Exception as e:
        logging.warning("Manifest fetch error %s, redirect MP4", e)
        return redirect(f"/proxy/{vid}", 302)

    def sub(m):
        absu = urllib.parse.urljoin(src, m.group(0))
        return f"/hlsseg?u={urllib.parse.quote(absu, safe='')}"
    txt = re.sub(r"(https?://[^\s,#]+|[^,\n#]+\.m3u8)", sub, txt)
    return Response(txt, mimetype="application/vnd.apple.mpegurl")

# ───────────── Segment proxy ─────────────
@app.route("/hlsseg")
def hlsseg():
    u = urllib.parse.unquote(request.args.get("u", ""))
    if not u.startswith("http"):
        abort(400)
    hdr = {"Accept-Encoding": "identity"}
    if (rng := request.headers.get("Range")):
        hdr["Range"] = rng
    r = requests.get(u, headers=hdr, stream=True, timeout=15)
    def gen():
        yield from r.iter_content(8192)
    resp = Response(stream_with_context(gen()), status=r.status_code)
    for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
        if h in r.headers:
            resp.headers[h] = r.headers[h]
    resp.headers["Cache-Control"] = "no-store"
    return resp

# ───────────── Progressive MP4 proxy ─────────────
@app.route("/proxy/<vid>")
def proxy_mp4(vid):
    src = progressive_url(vid)
    hdr = {"Accept-Encoding": "identity"}
    if (rng := request.headers.get("Range")):
        hdr["Range"] = rng
    r = requests.get(src, headers=hdr, stream=True, timeout=15)
    def gen():
        yield from r.iter_content(8192)
    resp = Response(stream_with_context(gen()), status=r.status_code)
    for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
        if h in r.headers:
            resp.headers[h] = r.headers[h]
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Content-Disposition"] = "inline"
    return resp

# ───────────── Download ─────────────
@app.route("/download/<vid>")
def download(vid):
    fmt = request.args.get("fmt", "mp4")
    if fmt not in ("mp4", "mp3"):
        abort(400)
    fname = f"{vid}.{fmt}"
    if not os.path.exists(fname):
        opts = {"quiet": True, "outtmpl": fname,
                "format": "bestvideo+bestaudio/best" if fmt == "mp4" else "bestaudio",
                "merge_output_format": "mp4" if fmt == "mp4" else None,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}] if fmt == "mp3" else []}
        YoutubeDL(opts).download([f"https://www.youtube.com/watch?v={vid}"])
    return send_file(open(fname, "rb"), as_attachment=True,
                     download_name=fname, mimetype="video/mp4" if fmt == "mp4" else "audio/mpeg")

# ───────────── main ─────────────
if __name__ == "__main__":
    app.run(debug=True)
