"""
youtube_focus_app.py (v9) - Apple-inspired Design
• Premium UI with smooth animations
• Modern card layouts and hover effects
• Optimized structure and performance
"""

import io, os, re, urllib.parse, shutil, subprocess, time
from typing import List, Dict
from flask import Flask, request, render_template_string, send_file, abort
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from yt_dlp import YoutubeDL

# ---------- Chrome Setup ----------
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

# ---------- Utilities ----------
def duration_to_seconds(duration: str) -> int:
    """Convert duration string to seconds"""
    parts = list(map(int, duration.strip().split(":")))
    h, m, s = (parts + [0, 0, 0])[-3:]
    return h * 3600 + m * 60 + s

def format_subscriber_count(subs: str) -> str:
    """Format subscriber count for display"""
    if not subs:
        return ""
    return subs.replace("subscribers", "").replace("subscriber", "").strip()

# ---------- Video Search ----------
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
                except:
                    duration = ""
                    seconds = None

                # Apply filters
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
                    "dur": duration
                })

                if len(results) >= 8:
                    break

            except Exception:
                continue

        return results

    finally:
        driver.quit()

# ---------- Channel Search ----------
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
                except:
                    subscribers = ""

                try:
                    img_element = channel.find_element(By.CSS_SELECTOR, "img")
                    thumbnail = img_element.get_attribute("src") or ""

                    if thumbnail.startswith("data:") or not thumbnail:
                        thumbnail = img_element.get_attribute("data-thumb") or ""
                except:
                    thumbnail = ""

                channels.append({
                    "title": title,
                    "url": url,
                    "thumb": thumbnail,
                    "subs": subscribers
                })

            except Exception:
                continue

        return channels

    finally:
        driver.quit()

# ---------- Channel Videos ----------
def fetch_channel_videos(channel_url: str, max_videos: int = 36) -> List[Dict[str, str]]:
    """Fetch channel videos using yt-dlp"""
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
                "dur": duration
            })

        return videos

    except Exception as e:
        print(f"Error fetching channel videos: {e}")
        return []

# ---------- Flask App ----------
app = Flask(__name__)

# ---------- HTML Template ----------
HTML_TEMPLATE = """
<!doctype html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>YouTube Focus</title>
    <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #007AFF;
            --secondary-color: #5856D6;
            --success-color: #34C759;
            --warning-color: #FF9500;
            --error-color: #FF3B30;
            --background-color: #F2F2F7;
            --surface-color: #FFFFFF;
            --text-primary: #1D1D1F;
            --text-secondary: #6E6E73;
            --border-color: #E5E5EA;
            --shadow-light: 0 2px 10px rgba(0, 0, 0, 0.1);
            --shadow-medium: 0 4px 20px rgba(0, 0, 0, 0.15);
            --shadow-heavy: 0 8px 40px rgba(0, 0, 0, 0.2);
            --border-radius: 12px;
            --border-radius-large: 20px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--background-color);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }

        /* Navigation */
        .navbar {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            padding: 1rem 0;
            transition: var(--transition);
        }

        .navbar.scrolled {
            background: rgba(255, 255, 255, 0.95);
            box-shadow: var(--shadow-light);
        }

        .search-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }

        .search-form {
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }

        .search-input {
            flex: 1;
            min-width: 280px;
            padding: 0.75rem 1rem;
            border: 2px solid var(--border-color);
            border-radius: var(--border-radius);
            font-size: 1rem;
            background: var(--surface-color);
            transition: var(--transition);
            outline: none;
        }

        .search-input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
        }

        .filter-select {
            padding: 0.75rem 1rem;
            border: 2px solid var(--border-color);
            border-radius: var(--border-radius);
            background: var(--surface-color);
            font-size: 1rem;
            cursor: pointer;
            transition: var(--transition);
            outline: none;
        }

        .filter-select:focus {
            border-color: var(--primary-color);
        }

        .search-button {
            padding: 0.75rem 2rem;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: var(--border-radius);
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            position: relative;
            overflow: hidden;
        }

        .search-button:hover {
            background: #0056CC;
            transform: translateY(-2px);
            box-shadow: var(--shadow-medium);
        }

        .search-button:active {
            transform: translateY(0);
        }

        /* Main Content */
        .main-content {
            max-width: 1200px;
            margin: 0 auto;
            padding: 8rem 2rem 4rem;
        }

        /* Section Headers */
        .section-header {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 2rem;
            color: var(--text-primary);
            position: relative;
        }

        .section-header::after {
            content: '';
            position: absolute;
            bottom: -0.5rem;
            left: 0;
            width: 60px;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            border-radius: 2px;
        }

        /* Channel Cards */
        .channel-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .channel-card {
            background: var(--surface-color);
            border-radius: var(--border-radius-large);
            padding: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            text-decoration: none;
            color: inherit;
            transition: var(--transition);
            box-shadow: var(--shadow-light);
            border: 1px solid var(--border-color);
        }

        .channel-card:hover {
            transform: translateY(-8px);
            box-shadow: var(--shadow-heavy);
            border-color: var(--primary-color);
        }

        .channel-avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            object-fit: cover;
            border: 3px solid var(--border-color);
            transition: var(--transition);
        }

        .channel-card:hover .channel-avatar {
            border-color: var(--primary-color);
        }

        .channel-info h3 {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
            color: var(--text-primary);
        }

        .channel-info p {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        /* Video Grid */
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 2rem;
        }

        .video-card {
            background: var(--surface-color);
            border-radius: var(--border-radius-large);
            overflow: hidden;
            transition: var(--transition);
            cursor: pointer;
            box-shadow: var(--shadow-light);
            border: 1px solid var(--border-color);
        }

        .video-card:hover {
            transform: translateY(-10px);
            box-shadow: var(--shadow-heavy);
        }

        .video-thumbnail {
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
        }

        .video-thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: var(--transition);
        }

        .video-card:hover .video-thumbnail img {
            transform: scale(1.05);
        }

        .video-duration {
            position: absolute;
            bottom: 0.5rem;
            right: 0.5rem;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .video-content {
            padding: 1.5rem;
        }

        .video-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .video-actions {
            display: flex;
            gap: 0.75rem;
        }

        .action-button {
            flex: 1;
            padding: 0.75rem;
            border: none;
            border-radius: var(--border-radius);
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            text-decoration: none;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .action-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: var(--transition);
        }

        .action-button:hover::before {
            left: 100%;
        }

        .action-button.primary {
            background: var(--primary-color);
            color: white;
        }

        .action-button.primary:hover {
            background: #0056CC;
            transform: translateY(-2px);
            box-shadow: var(--shadow-medium);
        }

        .action-button.secondary {
            background: var(--text-secondary);
            color: white;
        }

        .action-button.secondary:hover {
            background: #4A4A4F;
            transform: translateY(-2px);
            box-shadow: var(--shadow-medium);
        }

        /* Video Player */
        .video-player-container {
            display: flex;
            justify-content: center;
            margin-bottom: 2rem;
        }

        .video-player {
            width: 100%;
            max-width: 900px;
            aspect-ratio: 16/9;
            border-radius: var(--border-radius-large);
            overflow: hidden;
            box-shadow: var(--shadow-heavy);
        }

        .video-player iframe {
            width: 100%;
            height: 100%;
            border: none;
        }

        .player-actions {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-top: 2rem;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-secondary);
        }

        .empty-state h2 {
            font-size: 2rem;
            font-weight: 300;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }

        .empty-state p {
            font-size: 1.1rem;
            max-width: 400px;
            margin: 0 auto;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
            border-top: 1px solid var(--border-color);
            margin-top: 4rem;
        }

        /* Responsive Design */
        @media (max-width: 768px) {
            .search-form {
                flex-direction: column;
                align-items: stretch;
            }

            .search-input {
                min-width: auto;
            }

            .main-content {
                padding: 7rem 1rem 4rem;
            }

            .video-grid {
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }

            .channel-grid {
                grid-template-columns: 1fr;
            }

            .section-header {
                font-size: 1.5rem;
            }

            .video-actions {
                flex-direction: column;
            }
        }

        /* Loading Animation */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid var(--border-color);
            border-radius: 50%;
            border-top-color: var(--primary-color);
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Scroll Animations */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .animate-fade-in-up {
            animation: fadeInUp 0.6s ease-out;
        }

        /* Gradient Background */
        .gradient-bg {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar" id="navbar">
        <div class="search-container">
            <form method="post" action="/" class="search-form">
                <input
                    type="text"
                    name="query"
                    class="search-input"
                    placeholder="YouTube'da ara..."
                    value="{{ q|default('') }}"
                    required>
                <select name="filter" class="filter-select">
                    <option value="all" {% if flt=='all' %}selected{% endif %}>Tümü</option>
                    <option value="short" {% if flt=='short' %}selected{% endif %}>Kısa (&lt;4dk)</option>
                    <option value="medium" {% if flt=='medium' %}selected{% endif %}>Orta (4-20dk)</option>
                    <option value="long" {% if flt=='long' %}selected{% endif %}>Uzun (&gt;20dk)</option>
                </select>
                <button type="submit" class="search-button">
                    <span>Ara</span>
                </button>
            </form>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="main-content">
        {% if chans %}
            <h2 class="section-header">Kanallar</h2>
            <div class="channel-grid">
                {% for channel in chans %}
                    <a href="/channel?url={{ channel.url | urlencode }}&name={{ channel.title | urlencode }}" class="channel-card">
                        <img src="{{ channel.thumb }}" alt="{{ channel.title }}" class="channel-avatar">
                        <div class="channel-info">
                            <h3>{{ channel.title }}</h3>
                            <p>{{ channel.subs }}</p>
                        </div>
                    </a>
                {% endfor %}
            </div>
        {% endif %}

        {% if channel_videos %}
            <h2 class="section-header">{{ channel_name }} - Videolar</h2>
            <div class="video-grid">
                {% for video in channel_videos %}
                    <div class="video-card" onclick="location.href='/play?video_id={{ video.id }}'">
                        <div class="video-thumbnail">
                            <img src="{{ video.thumb }}" alt="{{ video.title }}">
                            {% if video.dur %}
                                <span class="video-duration">{{ video.dur }}</span>
                            {% endif %}
                        </div>
                        <div class="video-content">
                            <h3 class="video-title">{{ video.title }}</h3>
                            <div class="video-actions">
                                <a href="/download/{{ video.id }}?fmt=mp4" class="action-button primary" onclick="event.stopPropagation()">
                                    MP4 İndir
                                </a>
                                <a href="/download/{{ video.id }}?fmt=mp3" class="action-button secondary" onclick="event.stopPropagation()">
                                    MP3 İndir
                                </a>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            </div>

        {% elif vids %}
            <h2 class="section-header">Arama Sonuçları</h2>
            <div class="video-grid">
                {% for video in vids %}
                    <div class="video-card" onclick="location.href='/play?video_id={{ video.id }}'">
                        <div class="video-thumbnail">
                            <img src="{{ video.thumb }}" alt="{{ video.title }}">
                            <span class="video-duration">{{ video.dur }}</span>
                        </div>
                        <div class="video-content">
                            <h3 class="video-title">{{ video.title }}</h3>
                            <div class="video-actions">
                                <a href="/download/{{ video.id }}?fmt=mp4" class="action-button primary" onclick="event.stopPropagation()">
                                    MP4 İndir
                                </a>
                                <a href="/download/{{ video.id }}?fmt=mp3" class="action-button secondary" onclick="event.stopPropagation()">
                                    MP3 İndir
                                </a>
                            </div>
                        </div>
                    </div>
                {% endfor %}
            </div>

        {% elif video_url %}
            <div class="video-player-container">
                <div class="video-player">
                    <iframe src="{{ video_url }}" allowfullscreen></iframe>
                </div>
            </div>
            <div class="player-actions">
                <a href="/download/{{ current_id }}?fmt=mp4" class="action-button primary">
                    MP4 İndir
                </a>
                <a href="/download/{{ current_id }}?fmt=mp3" class="action-button secondary">
                    MP3 İndir
                </a>
            </div>

        {% else %}
            <div class="empty-state">
                <h2>YouTube Focus</h2>
                <p>Favori içeriklerinizi bulmak için arama yapın.</p>
            </div>
        {% endif %}
    </main>

    <!-- Footer -->
    <footer class="footer">
        <p>&copy; 2025 YouTube Focus. Modern tasarım ile güçlendirilmiştir.</p>
    </footer>

    <script>
        // Navbar scroll effect
        window.addEventListener('scroll', function() {
            const navbar = document.getElementById('navbar');
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });

        // Add fade-in animation to cards
        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.video-card, .channel-card');
            cards.forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
                card.classList.add('animate-fade-in-up');
            });
        });

        // Enhanced button interactions
        document.querySelectorAll('.action-button').forEach(button => {
            button.addEventListener('click', function(e) {
                // Create ripple effect
                const rect = this.getBoundingClientRect();
                const ripple = document.createElement('span');
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;

                ripple.style.cssText = `
                    position: absolute;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.3);
                    transform: scale(0);
                    animation: ripple 0.6s linear;
                    left: ${x}px;
                    top: ${y}px;
                    width: ${size}px;
                    height: ${size}px;
                `;

                this.appendChild(ripple);

                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });

        // Add ripple animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(2);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
"""

# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    videos = []
    channels = []
    query = ""
    filter_type = "all"

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        filter_type = request.form.get("filter", "all")

        if query:
            videos = search_videos(query, filter_type)
            channels = search_channels(query)

    return render_template_string(
        HTML_TEMPLATE,
        vids=videos,
        chans=channels,
        channel_videos=None,
        channel_name=None,
        video_url=None,
        current_id=None,
        q=query,
        flt=filter_type
    )

@app.route("/channel")
def channel_page():
    channel_url = request.args.get("url")
    channel_name = request.args.get("name", "Kanal")

    if not channel_url:
        abort(400, "Channel URL is required")

    try:
        decoded_url = urllib.parse.unquote(channel_url)
        videos = fetch_channel_videos(decoded_url)
        decoded_name = urllib.parse.unquote(channel_name)

        return render_template_string(
            HTML_TEMPLATE,
            vids=None,
            chans=None,
            channel_videos=videos,
            channel_name=decoded_name,
            video_url=None,
            current_id=None,
            q="",
            flt="all"
        )
    except Exception as e:
        abort(500, f"Error loading channel: {str(e)}")

@app.route("/play")
def play_video():
    video_id = request.args.get("video_id")

    if not video_id:
        abort(400, "Video ID is required")

    video_url = f"https://www.youtube.com/embed/{video_id}"

    return render_template_string(
        HTML_TEMPLATE,
        vids=None,
        chans=None,
        channel_videos=None,
        channel_name=None,
        video_url=video_url,
        current_id=video_id,
        q="",
        flt="all"
    )

@app.route("/download/<video_id>")
def download_video():
    video_id = request.args.get("video_id") or video_id
    fmt = request.args.get("fmt", "mp4")

    if not video_id:
        abort(400, "Video ID is required")

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        if fmt == "mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': f'/tmp/{video_id}.%(ext)s',
            }
        else:
            ydl_opts = {
                'format': 'best[height<=720]',
                'outtmpl': f'/tmp/{video_id}.%(ext)s',
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', video_id)

            # Find the downloaded file
            if fmt == "mp3":
                filename = f'/tmp/{video_id}.mp3'
            else:
                # Get the actual extension from the downloaded file
                ext = info.get('ext', 'mp4')
                filename = f'/tmp/{video_id}.{ext}'

            if os.path.exists(filename):
                safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                download_name = f"{safe_title}.{fmt}"

                def remove_file():
                    try:
                        os.remove(filename)
                    except:
                        pass

                return send_file(
                    filename,
                    as_attachment=True,
                    download_name=download_name,
                    mimetype='audio/mpeg' if fmt == 'mp3' else 'video/mp4'
                )
            else:
                abort(500, "Download failed - file not found")

    except Exception as e:
        abort(500, f"Download error: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
