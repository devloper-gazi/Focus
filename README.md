# YouTube Focus

A modern, Apple-inspired web application that helps you find and download YouTube content without distractions. Built with Flask and featuring a clean, responsive design.

## 🌟 Features

- **Distraction-Free Interface**: Clean, modern UI inspired by Apple's design principles
- **Smart Video Search**: Search YouTube videos with duration filters (short, medium, long)
- **Channel Browsing**: Discover and explore YouTube channels
- **Video Playback**: Watch videos in an embedded player
- **Download Support**: Download videos in MP4 format or extract audio as MP3
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Turkish Language Support**: Localized interface in Turkish

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Chrome browser installed
- FFmpeg (for audio extraction)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/devloper-gazi/focus.git
   cd focus
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python youtube.py
   ```

4. **Open your browser**
   Navigate to `http://localhost:5000`

## 📦 Dependencies

```txt
Flask==2.3.3
selenium==4.15.2
webdriver-manager==4.0.1
yt-dlp==2023.9.24
```

## 🎯 Usage

### Search Videos
1. Enter your search query in the search box
2. Select a duration filter (optional):
   - **Short**: Under 4 minutes
   - **Medium**: 4-20 minutes  
   - **Long**: Over 20 minutes
3. Click "Ara" (Search) to find videos

### Browse Channels
- Click on any channel from the search results
- View all videos from that channel
- Navigate through channel content

### Download Content
- **MP4 Download**: Click the blue "MP4 İndir" button
- **MP3 Download**: Click the gray "MP3 İndir" button for audio only

### Watch Videos
- Click on any video thumbnail to open the embedded player
- Download options are available on the player page

## 🏗️ Architecture

### Core Components

- **Flask Web Server**: Handles HTTP requests and routing
- **Selenium WebDriver**: Automates YouTube browsing for search results
- **yt-dlp**: Downloads YouTube content in various formats
- **Chrome Driver**: Headless browser automation

### Key Functions

- `search_videos()`: Searches YouTube and filters results
- `search_channels()`: Finds YouTube channels
- `fetch_channel_videos()`: Retrieves videos from a specific channel
- `create_webdriver()`: Sets up Chrome driver with optimal settings

## 🎨 Design Philosophy

This application follows Apple's Human Interface Guidelines:

- **Clarity**: Clean typography and intuitive navigation
- **Deference**: Content-focused design without unnecessary elements
- **Depth**: Subtle animations and layered interface elements
- **Accessibility**: High contrast ratios and semantic markup

## 🔧 Configuration

### Chrome Setup
The app automatically detects Chrome installation from common paths:
- `/opt/google/chrome/google-chrome`
- `~/.var/app/com.google.Chrome/current/active/files/bin/google-chrome`
- System PATH

### Download Settings
- **Video Quality**: Best quality up to 720p
- **Audio Quality**: 192kbps MP3
- **Storage**: Temporary files in `/tmp/` directory

## 🚀 Deployment

### Local Development
```bash
python youtube_focus_app.py
```

### Production Deployment
For production, consider using:
- **Gunicorn**: `gunicorn -w 4 youtube_focus_app:app`
- **Docker**: Create a Dockerfile for containerization
- **Reverse Proxy**: Use nginx for static files and SSL

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This application is for educational and personal use only. Please respect YouTube's Terms of Service and content creators' rights. The developers are not responsible for any misuse of this software.

## 🔮 Future Enhancements

- [ ] User authentication and playlists
- [ ] Video quality selection
- [ ] Batch download functionality
- [ ] Dark mode toggle
- [ ] Multiple language support
- [ ] Progressive Web App (PWA) features

---

Made with ❤️ using Flask and modern web technologies
