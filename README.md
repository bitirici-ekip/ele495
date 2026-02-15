# PNP Control Center v2.0
> **Pick & Place Control Interface for Raspberry Pi**

![Status](https://img.shields.io/badge/Status-Active-success)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi-red)
![Python](https://img.shields.io/badge/Python-3.9+-blue)

PNP Control Center is a comprehensive web-based interface for controlling Pick & Place machines powered by GRBL controllers and Raspberry Pi. It features real-time camera streaming with OCR capabilities, precise motor control, and an intuitive modern UI.

## 🌟 Key Features

### 🎮 Machine Control
- **Full Axis Control:** Precise X, Y, Z movement with adjustable step sizes (0.1mm - 50mm)
- **GRBL Integration:** Direct G-code sending, alarm handling, and real-time status monitoring
- **Smart Homing:** Auto-home capability on startup or demand
- **Pump Control:** Integrated vacuum pump switching

### 👁️ Computer Vision & OCR
- **Live Stream:** High-performance MJPEG streaming with low latency
- **OCR Engine:** Tesseract-based optical character recognition for component identification
- **Smart Filtering:** 
  - Minimum word length filtering
  - Bounding box stability checks
  - Ignore list configuration
- **PIP Zoom:** Picture-in-Picture zoom window with live annotations
- **Auto-Centering:** Automatically aligns the machine head with recognized text/components using visual feedback

### ⚙️ Configuration & Customization
- **Web-based Settings:** Configure camera resolution, motor steps, and OCR parameters directly from the UI
- **Calibration Wizard:** Step-by-step visual calibration for camera-to-motor coordinate mapping
- **Theme Support:** Dark/Light mode toggle
- **Position Memory:** Save and recall specific machine coordinates (Bases)

## 🛠️ Installation

### Prerequisites
- Raspberry Pi (4 or 5 recommended)
- Python 3.9+
- Tesseract OCR (`sudo apt install tesseract-ocr libtesseract-dev`)
- GRBL-based CNC Controller connected via USB

### Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/bitirici-ekip/ele495.git
   cd ele495
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

1. **Start the application:**
   ```bash
   sudo ./venv/bin/python app.py
   ```
   *Note: `sudo` might be required for accessing serial ports and hardware interfaces.*

2. **Access the interface:**
   Open your browser and navigate to: `http://<raspberry-pi-ip>:5000`

## 📂 Project Structure

- `app.py` - Main Flask application and backend logic
- `static/` - Frontend assets (CSS, JS)
- `templates/` - HTML templates
- `config.json` - Machine and application configuration
- `bases.json` - Saved coordinate database

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is proprietary software developed by **Bitirici Ekip**. All rights reserved.
