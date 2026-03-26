<h1 align="center">
  🏭 Autonomous Pick & Place Machine Control System
</h1>

<p align="center">
  <b>ELE495 — Senior Design Project in Electronic Engineering</b><br>
  <i>Ankara University · Department of Electrical-Electronics Engineering</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Raspberry%20Pi-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white" />
  <img src="https://img.shields.io/badge/Backend-Flask%20%2B%20SocketIO-000000?style=flat-square&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Vision-OpenCV%20%2B%20Tesseract%20OCR-5C3EE8?style=flat-square&logo=opencv&logoColor=white" />
  <img src="https://img.shields.io/badge/Motion-GRBL%20CNC-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Firmware-Arduino-00979D?style=flat-square&logo=arduino&logoColor=white" />
  <img src="https://img.shields.io/badge/Frontend-HTML5%20%2F%20JS%20%2F%20CSS3-E34F26?style=flat-square&logo=html5&logoColor=white" />
</p>

---

## 📌 Overview

This project delivers a **web-based, autonomous control and testing system** for an industrial **Pick & Place (Surface-Mount) machine**. The system integrates hardware motion control, real-time computer vision, and an intelligent scenario engine on a single platform — enabling fully automated SMD component placement, inline electrical testing, and optical quality verification **without operator intervention**.

### Key Capabilities

| Capability | Description |
|---|---|
| **Autonomous Pick & Place** | 3-axis (X-Y-Z) Cartesian positioning via GRBL-compatible CNC controller with collision-safe interpolation |
| **Inline Electrical Testing** | Resistance measurement & diode forward-voltage testing through ADC on the nozzle slave MCU |
| **Optical Character Recognition** | Real-time Tesseract OCR on the camera feed for component label verification and auto-centering |
| **Scenario Engine** | Block-based, conditional workflow builder (IF-PASS / IF-FAIL branching) for end-to-end production runs |
| **Live Web Dashboard** | Real-time MJPEG video stream, motor telemetry, and full manual/automatic control via WebSocket |
| **Automated Quality Control** | Vision-based PCB inspection with configurable ROI boxes and edge-detection thresholds |

---

## 👥 Team

| Member |
|---|
| Şahin Yalgun |
| Mehmet Egemen Çorbacı |
| Mustafa Anıl Işık |
| Aydın Eralp Sırmalı |

---

## 🏗️ System Architecture

The system is composed of **three principal layers** communicating over serial (UART) and WebSocket channels:

```
┌──────────────────────────────────────────────────────────────────────┐
│                      CLIENT  (Browser)                               │
│  HTML5 Dashboard  ·  MJPEG Video Feed  ·  Scenario Builder UI        │
│  Manual Jog Controls  ·  Test Results Monitor  ·  Config Panel       │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ WebSocket / HTTP
┌──────────────────────▼───────────────────────────────────────────────┐
│               SERVER  (Raspberry Pi · Python / Flask)                │
│                                                                      │
│  app.py ─── Flask + Socket.IO Web Server                             │
│     ├── MJPEG Camera Stream (OpenCV capture + multi-thread)          │
│     ├── Tesseract OCR Engine (real-time text detection & centering)  │
│     ├── GRBL Serial Interface (G-code motion commands)               │
│     ├── Scenario Execution Engine (master & standard scenarios)      │
│     ├── Verification Engine (ROI edge-detection QC)                  │
│     └── Configuration Manager (live-tunable via UI)                  │
│                                                                      │
│  pi_controller.py ─── Nozzle Slave Communication Library             │
│     ├── Stepper Motor Control (homing, rotation, acceleration)       │
│     ├── Resistance Measurement (voltage divider + ADC averaging)     │
│     └── Diode Test (forward-bias detection)                          │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ Serial (UART 115200 baud)
┌──────────────────────▼───────────────────────────────────────────────┐
│             HARDWARE  (GRBL CNC + Arduino Slave)                     │
│                                                                      │
│  GRBL Controller ─── X / Y / Z stepper motor interpolation           │
│  Arduino Slave   ─── Nozzle rotation stepper + analog I/O            │
│     └── arduino_stepper.ino  (Generic Slave Firmware)                │
│         ├── STEP / STEPG commands (guarded emergency-stop)           │
│         ├── AHOME  (autonomous homing with limit switch)             │
│         ├── AROTATE (autonomous angle rotation)                      │
│         ├── AREAD / MULTI_AREAD (analog measurements)               │
│         └── DREAD / DWRITE / PMODE (GPIO control)                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Technical Highlights

- **Multi-threaded Async Pipeline** — Camera capture, OCR computation, and GRBL polling run in isolated threads for jitter-free real-time performance on ARM hardware.
- **Conditional Branching Scenario Engine** — Dynamic tree-structured task decisions based on live test results (e.g., *"If resistance is within 10 % tolerance → place at slot X; otherwise → reject to slot Y"*).
- **Safe Motion Algorithms** — Vector-analysis-based smart interpolation sequences that prevent Z-axis collisions between the nozzle and workpiece.
- **Hot-Reloadable Configuration** — Pixel-to-mm conversion matrices, Tesseract PSM modes, axis inversion, and feed rates are adjustable on-the-fly through the web UI without restarting the server.
- **Master-Slave Firmware Architecture** — The Arduino executes only low-level commands received from the Python master; all decision logic resides server-side for maximum flexibility.

---

## 📂 Repository Structure

```
ele495/
├── README.md                          # Project documentation (this file)
├── .gitignore
│
└── code/                              # All source code
    ├── app.py                         # Main server (Flask, Socket.IO, multi-thread manager)
    ├── pi_controller.py               # Nozzle slave communication library (serial protocol)
    ├── requirements.txt               # Python dependencies
    │
    ├── arduino_stepper/
    │   └── arduino_stepper.ino        # Nozzle slave MCU firmware (Arduino C++)
    ├── arduino_stepper.ino            # Standalone copy of the firmware
    │
    ├── templates/
    │   ├── index.html                 # Main control panel dashboard
    │   └── login.html                 # Authentication page
    │
    ├── static/
    │   ├── app.js                     # Client-side event loop & UI state manager
    │   └── style.css                  # Dashboard styling
    │
    ├── config.json                    # Persistent system configuration
    ├── bases.json                     # Cartesian (XYZ) coordinate database
    ├── scenarios.json                 # Standard (sub-task) scenario definitions
    ├── master_scenarios.json          # End-to-end master production scenarios
    └── verification.json             # Autonomous OCR quality-control parameters
```

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Details |
|---|---|
| **Hardware** | Raspberry Pi 4 (or any Linux SBC / PC), USB camera, GRBL CNC shield, Arduino Nano/Uno |
| **OS** | Raspberry Pi OS / Debian-based Linux |
| **Tesseract OCR** | System package with English language data |

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng libleptonica-dev libtesseract-dev
```

### 2. Set Up the Python Environment

```bash
cd code/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Flash the Arduino Firmware

Open `code/arduino_stepper/arduino_stepper.ino` in the Arduino IDE and upload it to the **Nozzle Slave Arduino** (not the GRBL controller).

### 4. Launch the Server

```bash
python app.py
```

The control panel will be available at:

```
http://<raspberry-pi-ip>:5000
```

---

## 🔧 Configuration

All runtime parameters are stored in `code/config.json` and can be modified live through the web dashboard. Key parameters include:

| Parameter | Description |
|---|---|
| `pixel_to_mm_x/y` | Camera pixel-to-millimeter conversion factor |
| `feed_rate` | CNC movement speed (mm/min) |
| `ocr_confidence` | Minimum OCR confidence threshold (%) |
| `ocr_psm_mode` | Tesseract page segmentation mode |
| `nozzle_*` | Nozzle stepper motor tuning (speed, acceleration, limits) |
| `auto_center_tolerance` | Pixel tolerance for auto-centering on detected text |
| `invert_x/y` | Axis direction inversion flags |
| `fine_tune_step_mm` | Fine-tuning step size for precise positioning |

---

## 📡 Communication Protocol

The Arduino slave firmware uses a newline-terminated serial protocol:

| Command | Response | Description |
|---|---|---|
| `PING` | `OK:PONG` | Connection health check |
| `STEP <n> <dir> <spd> <acc_s> <acc_st>` | `OK:STEP_DONE` | Move stepper N steps |
| `STEPG <n> <dir> <spd> <acc_s> <acc_st> <guard>` | `OK:STEP_DONE` / `OK:ESTOP` | Guarded step with emergency stop |
| `AHOME <dir> <spd> <pin> <back_dir> <back_spd> <back_steps>` | `OK:HOME_DONE` | Autonomous homing to limit switch |
| `AROTATE <steps> <dir> <spd> <acc_s> <acc_st> <guard>` | `OK:STEP_DONE` | Autonomous rotation |
| `AREAD <pin>` | `OK:<value>` | Single analog read |
| `MULTI_AREAD <pin> <count>` | `OK:<avg>` | Averaged analog read |
| `DREAD <pin>` / `DWRITE <pin> <val>` | `OK:<value>` / `OK` | Digital I/O |

---

## 🧪 Inline Testing

The system performs **automated electrical tests** through the nozzle probe:

- **Resistance Measurement** — Voltage divider circuit with a known reference resistor. Multiple ADC samples are averaged to reduce noise, and the unknown resistance is calculated using the divider formula.
- **Diode Test** — Forward-bias voltage detection. The ADC reading is compared against a configurable threshold to determine conduction state (PASS / FAIL).

Test results feed directly into the **scenario engine**, enabling conditional branching: components that fail testing are automatically routed to a reject location.

---

## 📜 License

This project was developed as a senior design project (ELE495) at Ankara University, Department of Electrical-Electronics Engineering.

---

<p align="center">
  <sub>Built with ❤️ by the ELE495 Senior Design Team — Spring 2026</sub>
</p>
