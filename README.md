# PNP Control Center v2.0 🎯

**Professional Pick & Place Machine Control Interface**

![Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/Backend-Flask-green)
![GRBL](https://img.shields.io/badge/CNC-GRBL-orange)

Development of a comprehensive control interface for a Pick and Place (PNP) machine, integrating real-time camera streaming, OCR-based component detection, and precise motor control via GRBL.

## 🚀 Features

- **Real-time Monitoring**: High-quality MJPEG stream from the machine's camera.
- **OCR Component Detection**: Utilizing `tesserocr` to identify components (e.g., chips, labels) on the PCB.
- **Auto-Centering**: 
  - Automatically center the camera on a specific target word.
  - Supports dynamic target word input.
  - Two-stage centering (Coarse & Fine) for high precision.
- **Manual Control**:
  - Full X/Y/Z axis control via UI buttons or keyboard shortcuts.
  - Pump (Vacuum) toggle.
  - Emergency Stop & Soft Reset.
- **Configuration & Calibration**:
  - Easy-to-use calibration wizard for camera-motor alignment.
  - Customize resolution, feed rates, and target words directly from the UI.
- **Professional UI**:
  - Modern, dark-themed interface built with responsive CSS.
  - Central pop-up notifications for improved user feedback.

## 🛠️ Installation

### Prerequisites

- **Python 3.9+**
- **Tesseract OCR** (System dependency)
  ```bash
  sudo apt-get install tesseract-ocr libtesseract-dev libleptonica-dev
  ```

### Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/bitirici-ekip/ele495.git
    cd ele495
    ```

2.  **Create Virtual Environment**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Usage

1.  **Start the Application**
    ```bash
    python app.py
    ```
    *The server will start on port 5000 by default.*

2.  **Access the Web Interface**
    Open your browser and navigate to:
    `http://localhost:5000` (or the Raspberry Pi's IP address)

3.  **Login**
    - **Username**: `admin`
    - **Password**: `admin`

## 🎮 Controls

### Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| **Arrow Keys** | Move X/Y Axis |
| **Page Up/Down** | Move Z Axis |
| **H** | Home Machine ($H) |
| **C** | Start Auto-Center |
| **E** | Emergency Stop |

### OCR & Auto-Center

1.  Go to the **OCR Tab** to view detected words.
2.  Add new target words if needed.
3.  In the **Control Tab**, type the target word into the "HEDEF KELİME" input.
4.  Click **MERKEZLE** to automatically move the machine until the target is centered.

## ⚙️ Configuration

Settings are saved in `config.json`. You can modify these via the **Settings Tab** in the UI:
- **Pixel-to-MM Ratio**: Calibrate for accurate movement.
- **Camera Resolution**: Default 800x1080.
- **Motor Directions**: Invert axes if necessary.

## 📂 Project Structure

```
├── app.py              # Main Application Entry Point (Flask + Logic)
├── config.json         # Persistent Configuration
├── requirements.txt    # Python Dependencies
├── static/
│   ├── app.js          # Frontend Logic (SocketIO, UI interactions)
│   └── style.css       # Professional Dark Theme Styling
└── templates/
    ├── index.html      # Main Dashboard
    └── login.html      # Login Page
```

## 🤝 Contribution

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---
*Developed by Bitirici Ekip for ELE495.*
