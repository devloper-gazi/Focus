"""
youtube_focus_app.py (v12) - Linux ChromeDriver Fix
• Fixed Linux Chrome binary detection
• Improved ChromeDriver version matching
• Added better error handling for Linux systems
• Fixed download URL patterns for newer Chrome versions
"""

import io, os, re, urllib.parse, shutil, subprocess, time, requests, zipfile, stat, platform
from typing import List, Dict, Optional
from flask import Flask, request, render_template_string, send_file, abort
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from yt_dlp import YoutubeDL

# ---------- Chrome Setup ----------
def find_chrome_binary() -> str:
    """Find Chrome binary with comprehensive search"""
    system = platform.system().lower()

    if system == "windows":
        paths = [
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
    elif system == "darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:  # Linux and others
        # Check common binary locations first
        binary_names = ["google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"]
        paths = []

        # Add which results
        for name in binary_names:
            which_result = shutil.which(name)
            if which_result:
                paths.append(which_result)

        # Add common installation paths
        paths.extend([
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/opt/google/chrome/google-chrome",
            "/opt/google/chrome/chrome",
            # Flatpak
            os.path.expanduser("~/.var/app/com.google.Chrome/current/active/files/bin/google-chrome"),
            os.path.expanduser("~/.var/app/org.chromium.Chromium/current/active/files/bin/chromium"),
            # Snap
            "/snap/bin/chromium",
            "/var/lib/snapd/snap/bin/chromium",
            "/snap/bin/chrome",
            "/snap/bin/google-chrome-stable",
        ])

    for path in paths:
        if path and os.path.exists(path) and os.access(path, os.X_OK):
            print(f"Found Chrome binary: {path}")
            return path

    raise FileNotFoundError(
        f"Chrome/Chromium not found on {system}. Please install:\n"
        f"- Windows: Download from https://www.google.com/chrome/\n"
        f"- Linux: sudo dnf install google-chrome-stable OR sudo apt install google-chrome-stable\n"
        f"- macOS: Download from https://www.google.com/chrome/"
    )

def get_chrome_version(chrome_path: str) -> str:
    """Get Chrome version number with multiple fallback strategies"""
    try:
        # Primary method: --version flag
        version_output = subprocess.check_output(
            [chrome_path, "--version"],
            timeout=15,
            stderr=subprocess.DEVNULL
        ).decode().strip()

        print(f"Chrome version output: {version_output}")

        # Try to extract version number
        version_patterns = [
            r"Google Chrome (\d+\.\d+\.\d+\.\d+)",
            r"Chromium (\d+\.\d+\.\d+\.\d+)",
            r"Chrome (\d+\.\d+\.\d+\.\d+)",
            r"(\d+\.\d+\.\d+\.\d+)",
            r"(\d+\.\d+\.\d+)",
            r"(\d+)",
        ]

        for pattern in version_patterns:
            match = re.search(pattern, version_output)
            if match:
                version = match.group(1)
                # Ensure we have a full version number
                if len(version.split('.')) == 1:
                    version = version + ".0.0.0"
                elif len(version.split('.')) == 2:
                    version = version + ".0.0"
                elif len(version.split('.')) == 3:
                    version = version + ".0"

                print(f"Chrome version detected: {version}")
                return version

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Could not get Chrome version using --version: {e}")

    # Try alternative method for some Linux distributions
    try:
        # Try using --product-version
        version_output = subprocess.check_output(
            [chrome_path, "--product-version"],
            timeout=10,
            stderr=subprocess.DEVNULL
        ).decode().strip()

        if re.match(r"\d+\.\d+\.\d+\.\d+", version_output):
            print(f"Chrome version detected (product-version): {version_output}")
            return version_output

    except:
        pass

    # Final fallback - return a stable recent version
    fallback_version = "120.0.6099.109"
    print(f"Using fallback Chrome version: {fallback_version}")
    return fallback_version

def get_chromedriver_download_info(chrome_version: str) -> tuple:
    """Get ChromeDriver download URL and expected filename based on Chrome version"""
    major_version = chrome_version.split('.')[0]
    system = platform.system().lower()

    # Determine platform suffix
    if system == "windows":
        platform_suffix = "win64"
        filename = "chromedriver.exe"
    elif system == "darwin":
        # Check if it's Apple Silicon or Intel
        try:
            arch = platform.machine().lower()
            if arch in ['arm64', 'aarch64']:
                platform_suffix = "mac-arm64"
            else:
                platform_suffix = "mac-x64"
        except:
            platform_suffix = "mac-x64"
        filename = "chromedriver"
    else:  # Linux
        platform_suffix = "linux64"
        filename = "chromedriver"

    try:
        major_ver = int(major_version)
        print(f"Looking for ChromeDriver for Chrome major version: {major_ver}")

        if major_ver >= 115:
            # New ChromeDriver API for versions 115+
            api_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{major_version}"
            print(f"Trying API URL: {api_url}")

            response = requests.get(api_url, timeout=10)
            print(f"API response status: {response.status_code}")

            if response.status_code == 200:
                exact_version = response.text.strip()
                print(f"Found exact version: {exact_version}")
                download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{exact_version}/{platform_suffix}/chromedriver-{platform_suffix}.zip"
                return download_url, filename, exact_version

        # Fallback to legacy API
        print("Trying legacy API...")
        download_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        response = requests.get(download_url, timeout=10)
        print(f"Legacy API response status: {response.status_code}")

        if response.status_code == 200:
            exact_version = response.text.strip()
            print(f"Legacy API found version: {exact_version}")
            download_url = f"https://chromedriver.storage.googleapis.com/{exact_version}/chromedriver_{platform_suffix}.zip"
            return download_url, filename, exact_version

    except Exception as e:
        print(f"Error getting ChromeDriver info: {e}")

    # Final fallback - use a known stable version
    fallback_version = "120.0.6099.109"
    print(f"Using fallback ChromeDriver version: {fallback_version}")

    if system == "windows":
        download_url = f"https://chromedriver.storage.googleapis.com/{fallback_version}/chromedriver_win32.zip"
    elif system == "darwin":
        download_url = f"https://chromedriver.storage.googleapis.com/{fallback_version}/chromedriver_mac64.zip"
    else:
        download_url = f"https://chromedriver.storage.googleapis.com/{fallback_version}/chromedriver_linux64.zip"

    return download_url, filename, fallback_version

def download_chromedriver_auto(chrome_version: str) -> str:
    """Automatically download ChromeDriver with retry mechanism"""
    download_dir = os.path.expanduser("~/.chromedriver_auto")
    os.makedirs(download_dir, exist_ok=True)

    system = platform.system().lower()
    driver_filename = "chromedriver.exe" if system == "windows" else "chromedriver"
    driver_path = os.path.join(download_dir, driver_filename)

    # Check if already exists and is executable
    if os.path.exists(driver_path) and os.access(driver_path, os.X_OK):
        print(f"Using existing ChromeDriver: {driver_path}")
        return driver_path

    print(f"Downloading ChromeDriver for Chrome version {chrome_version}...")

    # Get download information
    download_url, expected_filename, version = get_chromedriver_download_info(chrome_version)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Download attempt {attempt + 1}/{max_retries}: {download_url}")

            # Download the zip file
            zip_path = os.path.join(download_dir, "chromedriver.zip")

            with requests.get(download_url, stream=True, timeout=30) as response:
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\rDownload progress: {percent:.1f}%", end="", flush=True)

                print("\nDownload completed, extracting...")

            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(download_dir)

            # Find the chromedriver executable
            extracted_driver = None
            for root, dirs, files in os.walk(download_dir):
                for file in files:
                    if file == expected_filename or (file.startswith("chromedriver") and not file.endswith((".zip", ".txt"))):
                        potential_path = os.path.join(root, file)
                        print(f"Found potential chromedriver: {potential_path}")

                        # Check if it's executable or can be made executable
                        if system == "windows" or os.access(potential_path, os.X_OK):
                            extracted_driver = potential_path
                            break
                        else:
                            # Try to make it executable
                            try:
                                os.chmod(potential_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                                if os.access(potential_path, os.X_OK):
                                    extracted_driver = potential_path
                                    break
                            except:
                                pass

                if extracted_driver:
                    break

            if not extracted_driver:
                raise Exception("ChromeDriver executable not found in downloaded archive")

            if extracted_driver != driver_path:
                # Move to final location
                if os.path.exists(driver_path):
                    os.remove(driver_path)
                shutil.move(extracted_driver, driver_path)

            # Make executable on Unix systems
            if system != "windows":
                os.chmod(driver_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

            # Clean up
            if os.path.exists(zip_path):
                os.remove(zip_path)

            # Remove extracted directories
            for item in os.listdir(download_dir):
                item_path = os.path.join(download_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)

            # Verify the download was successful
            if os.path.exists(driver_path) and os.access(driver_path, os.X_OK):
                print(f"\nChromeDriver successfully downloaded: {driver_path}")
                return driver_path
            else:
                raise Exception("Downloaded ChromeDriver is not executable")

        except Exception as e:
            print(f"\nDownload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 3 seconds...")
                time.sleep(3)
            continue

    raise FileNotFoundError("Could not download ChromeDriver after multiple attempts")

def create_webdriver() -> webdriver.Chrome:
    """Create Chrome WebDriver with automatic ChromeDriver management"""
    try:
        chrome_path = find_chrome_binary()
        chrome_version = get_chrome_version(chrome_path)
        major_version = chrome_version.split('.')[0]

        print(f"Chrome path: {chrome_path}")
        print(f"Chrome version: {chrome_version}")
        print(f"Chrome major version: {major_version}")

        # Chrome options
        options = webdriver.ChromeOptions()
        options.binary_location = chrome_path
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument(f"--user-agent=Mozilla/5.0 (Linux; Chrome/{major_version}) YouTube-Focus-App")

        # Strategy 1: Try WebDriver Manager (if available)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            print("Attempting to use WebDriver Manager...")

            try:
                # Try with specific version first
                driver_path = ChromeDriverManager(version=major_version).install()
            except:
                # Fallback to latest version
                driver_path = ChromeDriverManager().install()

            # Verify the driver path is valid
            if os.path.exists(driver_path) and os.access(driver_path, os.X_OK):
                print(f"WebDriver Manager success: {driver_path}")
                return webdriver.Chrome(service=Service(driver_path), options=options)

        except ImportError:
            print("WebDriver Manager not available, using automatic download...")
        except Exception as e:
            print(f"WebDriver Manager failed: {e}")

        # Strategy 2: Try system ChromeDriver first (for Linux)
        system = platform.system().lower()
        if system == "linux":
            system_paths = [
                "/usr/bin/chromedriver",
                "/usr/local/bin/chromedriver",
                shutil.which("chromedriver"),
                "/snap/bin/chromedriver",
            ]

            print("Trying system ChromeDriver locations...")
            for path in system_paths:
                if path and os.path.exists(path) and os.access(path, os.X_OK):
                    try:
                        print(f"Testing system ChromeDriver: {path}")
                        # Test if the ChromeDriver works
                        test_service = Service(path)
                        test_driver = webdriver.Chrome(service=test_service, options=options)
                        test_driver.quit()
                        print(f"System ChromeDriver successful: {path}")
                        return webdriver.Chrome(service=Service(path), options=options)
                    except Exception as e:
                        print(f"System ChromeDriver at {path} failed: {e}")
                        continue

        # Strategy 3: Automatic ChromeDriver download
        try:
            print("Attempting automatic ChromeDriver download...")
            driver_path = download_chromedriver_auto(chrome_version)
            return webdriver.Chrome(service=Service(driver_path), options=options)
        except Exception as e:
            print(f"Automatic ChromeDriver download failed: {e}")

        # Final error message with helpful instructions
        if system == "linux":
            install_cmd = "sudo dnf install chromium-chromedriver OR sudo apt install chromium-chromedriver"
        elif system == "darwin":
            install_cmd = "brew install chromedriver"
        else:
            install_cmd = "Download from https://chromedriver.chromium.org/"

        raise WebDriverException(
            f"Could not create ChromeDriver on {system}. Please try:\n"
            f"1. Install ChromeDriver: {install_cmd}\n"
            f"2. Install WebDriver Manager: pip install webdriver-manager\n"
            f"3. Make sure Chrome/Chromium is installed and up to date\n"
            f"4. Chrome version found: {chrome_version}\n"
            f"5. Chrome binary: {chrome_path}"
        )

    except Exception as e:
        print(f"Critical error in create_webdriver: {e}")
        raise

# ---------- Utilities ----------
def duration_to_seconds(duration: str) -> int:
    """Convert duration string to seconds"""
    if not duration or not duration.strip():
        return 0

    try:
        parts = list(map(int, duration.strip().split(":")))
        if len(parts) == 1:  # Only seconds
            return parts[0]
        elif len(parts) == 2:  # Minutes:Seconds
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:  # Hours:Minutes:Seconds
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        else:
            return 0
    except (ValueError, IndexError):
        return 0

def format_subscriber_count(subs: str) -> str:
    """Format subscriber count for display"""
    if not subs:
        return ""

    # Clean up the subscriber count text
    cleaned = subs.replace("subscribers", "").replace("subscriber", "").strip()

    # Convert to a more readable format if it's a number
    try:
        # Handle formats like "1.2M", "500K", etc.
        if cleaned.endswith(('K', 'M', 'B')):
            return cleaned

        # Convert large numbers to readable format
        num = int(cleaned.replace(',', '').replace('.', ''))
        if num >= 1000000000:
            return f"{num/1000000000:.1f}B"
        elif num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)
    except (ValueError, AttributeError):
        return cleaned

def validate_video_id(video_id: str) -> bool:
    """Validate YouTube video ID format"""
    if not video_id or len(video_id) != 11:
        return False

    # YouTube video IDs are 11 characters long and contain only alphanumeric chars, - and _
    return re.match(r'^[a-zA-Z0-9_-]{11}$', video_id) is not None

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system operations"""
    if not filename:
        return "untitled"

    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized = re.sub(r'[^\w\s.-]', '', sanitized)
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()

    # Limit length and ensure it's not empty
    sanitized = sanitized[:100] if len(sanitized) > 100 else sanitized
    return sanitized if sanitized else "untitled"

def is_valid_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube URL"""
    if not url:
        return False

    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtube\.com/channel/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/user/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/c/[\w-]+',
        r'https?://youtu\.be/[\w-]+',
    ]

    return any(re.match(pattern, url) for pattern in youtube_patterns)

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
