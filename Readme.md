<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FFmpeg-Required-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg">
  <img src="https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

<h1 align="center">⚡ EditFlow</h1>

<p align="center">
  <strong>Professional Video Processing Workflow Tool</strong>
</p>

<p align="center">
  A sleek, modern desktop application for processing videos with custom branding, hardware acceleration, and automated workflow features. Perfect for content creators, streamers, and video editors.
</p>

---

## ✨ Features

### 🎬 Video Processing
- **Concatenate multiple videos** with seamless transitions (cut, crossfade, fade to black, dip to white)
- **Trim videos** - Remove unwanted seconds from start/end of each clip
- **Episode splitting** - Automatically split long recordings into episodes with configurable overlap

### 🎨 Branding System
- **Intro/Outro support** - Prepend or overlay intro/outro clips with your branding
- **Full overlap mode** - Overlay transparent intros/outros on top of video content
- **Append mode** - Add intros/outros sequentially before/after main content
- **Subscribe graphics** - Automated overlay popups at configurable intervals

### ⚡ Performance
- **Hardware acceleration** - Auto-detects NVIDIA NVENC, Intel QuickSync, AMD AMF
- **Multiple quality presets** - YouTube 4K, 1440p, 1080p, 720p optimized
- **Real-time progress tracking** - Live encoding progress and detailed status

### 💾 Workflow
- **Branding profiles** - Save and reuse branding configurations
- **Non-destructive** - References original files, no unnecessary copies
- **Output management** - Browse, preview, and manage rendered outputs

---

## 🖥️ Screenshots

<p align="center">
  <em>Modern dark-themed interface with intuitive controls</em>
</p>

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+**
- **FFmpeg** (with NVENC/QSV support for hardware acceleration)
- **Tkinter** (usually included with Python)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/editflow.git
   cd editflow
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   ```
   http://localhost:5000
   ```

---

## 📖 Usage Guide

### Basic Workflow

1. **Add Videos** - Drop files or click to browse for video files
2. **Configure Settings**
   - Choose transition type (cut, crossfade, fade to black, dip to white)
   - Select quality preset (4K, 1440p, 1080p, 720p)
   - Pick encoder (NVENC for fastest rendering)
   - Set trim values if needed
3. **Select Branding** - Choose a branding profile (optional)
4. **Process** - Click "Process Videos" and watch the progress

### Branding Profiles

1. Go to **Branding** tab
2. Click **+ Add Profile**
3. Configure your branding elements:
   - **Intro** - Video to play before main content
   - **Outro** - Video to play after main content
   - **Subscribe Popup** - Overlay that appears periodically during the video

### Overlap Modes Explained

| Setting | Behavior |
|---------|----------|
| `Full Overlap = ON` | Intro/outro plays **on top** of video (for transparent overlays) |
| `Full Overlap = OFF`, `Overlap > 0` | Intro/outro overlaps into video by specified seconds |
| `Full Overlap = OFF`, `Overlap = 0` | Intro/outro is **appended** sequentially (no overlap) |

---

## ⚙️ Configuration

### Hardware Acceleration

EditFlow automatically detects and uses available hardware encoders for faster processing:

| Encoder | GPU Required | Speed | Quality |
|---------|-------------|-------|---------|
| **NVENC** | NVIDIA GTX 600+ | ⚡⚡⚡ Fastest | Excellent |
| **QuickSync** | Intel CPU with iGPU | ⚡⚡ Fast | Good |
| **AMF** | AMD GPU | ⚡⚡ Fast | Good |
| **Software** | None | ⚡ Standard | Best |

### Quality Presets

| Preset | Resolution | Bitrate | Best For |
|--------|------------|---------|----------|
| YouTube 4K | 3840×2160 | 45 Mbps | Maximum quality uploads |
| YouTube 1440p | 2560×1440 | 24 Mbps | High quality gaming content |
| YouTube 1080p | 1920×1080 | 12 Mbps | Standard content (recommended) |
| YouTube 1080p Fast | 1920×1080 | 12 Mbps | Quick previews |
| YouTube 720p | 1280×720 | 7.5 Mbps | Faster uploads, limited bandwidth |
| Original | Source | Source | Stream copy (fastest, no re-encoding) |

---

## 📁 Project Structure

```
editflow/
├── app.py              # Flask API server
├── video_processor.py  # FFmpeg processing engine
├── profile_manager.py  # Branding profiles handler
├── config.py           # Configuration and presets
├── static/
│   ├── index.html      # Main UI
│   ├── app.js          # Frontend logic
│   └── styles.css      # Dark theme styling
├── data/
│   ├── output/         # Rendered videos
│   ├── profiles/       # Branding profiles JSON
│   └── temp/           # Temporary processing files
└── requirements.txt    # Python dependencies
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, Flask |
| **Processing** | FFmpeg with hardware acceleration |
| **Frontend** | Vanilla JavaScript, CSS3 (Dark theme) |
| **File Dialog** | Tkinter native dialogs |
| **Data Storage** | JSON files |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Ranit Bhowmick**
- 🌐 Website: [ranitbhowmick.com](https://ranitbhowmick.com)
- 💼 GitHub: [@ranitbhowmick](https://github.com/ranitbhowmick)

---

## 🙏 Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - The amazing video processing library
- [Flask](https://flask.palletsprojects.com/) - Lightweight web framework

---

<p align="center">
  <strong>Made with ❤️ for content creators</strong>
</p>

<p align="center">
  <sub>⭐ Star this repo if you find it useful!</sub>
</p>
