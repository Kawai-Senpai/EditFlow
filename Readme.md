<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FFmpeg-Required-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<h1 align="center">🎬 Video Script</h1>

<p align="center">
  <strong>A powerful tool for processing gameplay recordings with channel branding</strong>
</p>

<p align="center">
  Join multiple videos, split into episodes, add intro/outro overlays, and periodic subscribe graphics - all from a clean web interface.
</p>

---

## ✨ Features

### 🎯 Processing Modes

| Mode | Description |
|------|-------------|
| **Single Video** | Combine multiple gameplay clips into one seamless video |
| **Episodic** | Automatically split long recordings into episodes with configurable overlap |

### 🎨 Channel Branding

Create branding presets for different channels with:

- **Intro Overlay** - Transparent video/image that appears at the start with configurable overlap
- **Outro Overlay** - Transparent video/image that appears before the end
- **Subscribe Graphics** - Periodic popup reminders at configurable intervals

All overlays support:
- Transparent video formats (WebM, MOV with alpha)
- PNG/GIF images
- Audio mixing options
- Customizable overlap duration

### 🔄 Transitions

Choose how clips blend together:
- **Cut** - Instant switch (no transition)
- **Crossfade** - Smooth blend between clips
- **Fade to Black** - Professional fade out/in
- **Dip to White** - Bright flash transition

### 📺 Output Presets

Optimized encoding presets for YouTube:
- YouTube 4K (2160p)
- YouTube 1440p
- YouTube 1080p
- YouTube 1080p Fast
- YouTube 720p
- Original Quality (stream copy)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+**
- **FFmpeg** (must be in PATH)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/video-script.git
cd video-script

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Open your browser and navigate to: **http://127.0.0.1:5000**

---

## 📁 Project Structure

```
video-script/
├── app.py                 # Flask API server
├── config.py              # Configuration and presets
├── profile_manager.py     # Branding profile management
├── video_processor.py     # FFmpeg video processing
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html         # Web interface
│   ├── styles.css         # Styling
│   └── app.js             # Frontend logic
├── data/
│   └── profiles/          # Saved branding profiles
├── temp/                  # Temporary processing files
└── output/                # Processed video output
```

---

## 🎮 Usage Guide

### 1. Create Channel Branding

1. Go to **Branding** tab
2. Click **New Branding**
3. Upload your assets:
   - **Intro** - Transparent video that plays at the start
   - **Outro** - Transparent video that plays at the end
   - **Subscribe** - Popup graphic shown periodically
4. Configure overlap and audio settings
5. Save your branding preset

### 2. Process Videos

1. Go to **Process** tab
2. Select output mode:
   - **Single Video** - Join all clips into one
   - **Episodic** - Split into episodes
3. Drag and drop your video files
4. Reorder clips as needed
5. Select your branding profile
6. Configure transition and quality settings
7. Click **Start Processing**

### 3. View Outputs

- Go to **Outputs** tab to see processed files
- Click **Open Folder** to access the output directory

---

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Server settings
HOST = "127.0.0.1"
PORT = 5000

# Output presets
OUTPUT_PRESETS = {
    "youtube_1080p": {
        "resolution": "1920x1080",
        "bitrate": "8M",
        "preset": "slow",
        "crf": 18
    },
    # Add your own presets...
}
```

---

## 🛠️ API Reference

### Video Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process/single` | POST | Process into single video |
| `/api/process/episodic` | POST | Process into episodes |
| `/api/process/<job_id>/status` | GET | Get processing status |
| `/api/process/<job_id>/cancel` | POST | Cancel processing |

### Branding Profiles

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/profiles` | GET | List all profiles |
| `/api/profiles` | POST | Create new profile |
| `/api/profiles/<id>` | PUT | Update profile |
| `/api/profiles/<id>` | DELETE | Delete profile |
| `/api/profiles/<id>/intro` | POST | Upload intro |
| `/api/profiles/<id>/outro` | POST | Upload outro |
| `/api/profiles/<id>/subscribe` | POST | Upload subscribe graphic |

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Ranit Bhowmick**

- Website: [ranitbhowmick.com](https://ranitbhowmick.com)
- GitHub: [@ranitbhowmick](https://github.com/ranitbhowmick)

---

<p align="center">
  Made with ❤️ for content creators
</p>
