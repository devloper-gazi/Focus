import os
import re
import shutil
import subprocess
import time
import urllib.parse
from typing import Dict, List

from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from yt_dlp import YoutubeDL


def find_chrome_binary() -> str:
    paths = [
        shutil.which("google-chrome"),
        "/opt/google/chrome/google-chrome",
        os.path.expanduser("~/.var/app/com.google.Chrome/current/active/files/bin/google-chrome"),
    ]
    for path in paths:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("Chrome not found. Please check your installation.")


def create_webdriver() -> webdriver.Chrome:
    chrome_path = find_chrome_binary()
    version_output = subprocess.check_output([chrome_path, "--version"]).decode()
    major_version = re.search(r"(\d+)", version_output).group(1)

    options = webdriver.ChromeOptions()
    options.binary_location = chrome_path
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    try:
        driver_path = ChromeDriverManager(version=major_version).install()
    except TypeError:
        driver_path = ChromeDriverManager().install()

    return webdriver.Chrome(service=Service(driver_path), options=options)


def duration_to_seconds(duration: str) -> int:
    parts = list(map(int, duration.strip().split(":")))
    h, m, s = (parts + [0, 0, 0])[-3:]
    return h * 3600 + m * 60 + s


def format_subscriber_count(subs: str) -> str:
    if not subs:
        return ""
    return subs.replace("subscribers", "").replace("subscriber", "").strip()


def search_videos(query: str, filter_type: str) -> List[Dict[str, str]]:
    driver = create_webdriver()
    try:
        driver.get("https://www.youtube.com")
        driver.implicitly_wait(5)

        search_box = driver.find_element(By.NAME, "search_query")
        search_box.send_keys(query + Keys.RETURN)
        time.sleep(3)

        results = []
        video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")[:12]

        for video in video_elements:
            try:
                title_element = video.find_element(By.ID, "video-title")
                href = title_element.get_attribute("href") or ""

                if "v=" not in href:
                    continue

                video_id = href.split("v=")[1].split("&")[0]
                title = title_element.text.strip()

                try:
                    duration_element = video.find_element(By.CSS_SELECTOR, "ytd-thumbnail-overlay-time-status-renderer span")
                    duration = duration_element.text.strip()
                    seconds = duration_to_seconds(duration) if duration else None
                except Exception:
                    duration = ""
                    seconds = None

                if filter_type == "short" and (seconds is None or seconds >= 240):
                    continue
                elif filter_type == "medium" and (seconds is None or seconds < 240 or seconds > 1200):
                    continue
                elif filter_type == "long" and (seconds is None or seconds <= 1200):
                    continue

                thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

                results.append({
                    "id": video_id,
                    "title": title,
                    "thumb": thumbnail,
                    "dur": duration,
                })

                if len(results) >= 8:
                    break
            except Exception:
                continue
        return results
    finally:
        driver.quit()


def search_channels(query: str) -> List[Dict[str, str]]:
    driver = create_webdriver()
    try:
        driver.get("https://www.youtube.com")
        driver.implicitly_wait(5)

        search_box = driver.find_element(By.NAME, "search_query")
        search_box.send_keys(query + Keys.RETURN)
        time.sleep(2)

        channels = []
        channel_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-channel-renderer")[:8]

        for channel in channel_elements:
            try:
                title_element = channel.find_element(By.ID, "channel-title")
                title = title_element.text.strip()

                url_element = channel.find_element(By.ID, "main-link")
                url = url_element.get_attribute("href")

                try:
                    subs_element = channel.find_element(By.ID, "subscribers")
                    subscribers = format_subscriber_count(subs_element.text)
                except Exception:
                    subscribers = ""

                try:
                    img_element = channel.find_element(By.CSS_SELECTOR, "img")
                    thumbnail = img_element.get_attribute("src") or ""
                    if thumbnail.startswith("data:") or not thumbnail:
                        thumbnail = img_element.get_attribute("data-thumb") or ""
                except Exception:
                    thumbnail = ""

                channels.append({
                    "title": title,
                    "url": url,
                    "thumb": thumbnail,
                    "subs": subscribers,
                })
            except Exception:
                continue
        return channels
    finally:
        driver.quit()


def fetch_channel_videos(channel_url: str, max_videos: int = 36) -> List[Dict[str, str]]:
    if not channel_url.rstrip("/").endswith("/videos"):
        channel_url = channel_url.rstrip("/") + "/videos"

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": max_videos,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

        videos = []
        for entry in info.get("entries", [])[:max_videos]:
            video_id = entry.get("id")
            title = entry.get("title", "")
            duration = entry.get("duration_string", "")
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            videos.append({
                "id": video_id,
                "title": title,
                "thumb": thumbnail,
                "dur": duration,
            })
        return videos
    except Exception:
        return []


app = Flask(__name__)
CORS(app)


@app.get("/api/videos")
def api_search_videos():
    query = request.args.get("q", "")
    filter_type = request.args.get("filter", "all")
    if not query:
        return jsonify([])
    results = search_videos(query, filter_type)
    return jsonify(results)


@app.get("/api/channels")
def api_search_channels():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    results = search_channels(query)
    return jsonify(results)


@app.get("/api/channel")
def api_channel_videos():
    channel_url = request.args.get("url")
    if not channel_url:
        abort(400, "Channel URL required")
    decoded = urllib.parse.unquote(channel_url)
    videos = fetch_channel_videos(decoded)
    return jsonify(videos)


@app.get("/api/download/<video_id>")
def api_download(video_id):
    fmt = request.args.get("fmt", "mp4")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        if fmt == "mp3":
            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": f"/tmp/{video_id}.%(ext)s",
            }
        else:
            ydl_opts = {
                "format": "best[height<=720]",
                "outtmpl": f"/tmp/{video_id}.%(ext)s",
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get("title", video_id)

        if fmt == "mp3":
            filename = f"/tmp/{video_id}.mp3"
        else:
            ext = info.get("ext", "mp4")
            filename = f"/tmp/{video_id}.{ext}"

        if os.path.exists(filename):
            safe_title = re.sub(r"[^\w\s-]", "", title).strip()
            download_name = f"{safe_title}.{fmt}"
            return send_file(
                filename,
                as_attachment=True,
                download_name=download_name,
                mimetype="audio/mpeg" if fmt == "mp3" else "video/mp4",
            )
        else:
            abort(500, "Download failed - file not found")
    except Exception as e:
        abort(500, f"Download error: {str(e)}")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
