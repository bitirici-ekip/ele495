#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
  PNP Makine Web Kontrol Arayüzü — app.py
  ────────────────────────────────────────
  Bu dosya Flask tabanlı bir web sunucu üzerinden PNP (Pick and Place)
  makinesini kontrol etmeyi sağlar.

  Özellikler:
    • Canlı kamera görüntüsü (MJPEG stream)
    • OCR ile yazı algılama (tesserocr)
    • Algılanan yazının merkezini çapraz çizgilerle işaretleme
    • Motorları (X/Y) kontrol ederek yazıyı ekran merkezine taşıma
    • Web arayüzünden manuel motor kontrolü, pompa kontrolü, home
    • SocketIO ile gerçek zamanlı durum güncellemesi

  Kullanım:
    python app.py

  Erişim:
    http://<bu-cihazın-IP-adresi>:5000

═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import glob
import threading
import logging
import functools
from io import BytesIO
from datetime import datetime

import cv2
import numpy as np
from PIL import Image
import difflib

# Flask ve SocketIO
from flask import (Flask, render_template, Response, jsonify, request,
                   session, redirect, url_for)
from flask_socketio import SocketIO

# ─── Ortam değişkenleri ──────────────────────────────────────────────────────
os.environ["OMP_THREAD_LIMIT"] = "1"        # Tesseract tek thread (ARM'da hızlı)
os.environ["PYTHONUNBUFFERED"] = "1"         # Çıktıları anında göster

# ─── Loglama ayarları ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("PNP")

# ═════════════════════════════════════════════════════════════════════════════
#  YAPILANDIRMA (Konfigürasyon)
# ═════════════════════════════════════════════════════════════════════════════

class Config:
    """
    Sistem konfigürasyonu. Web arayüzünden de güncellenebilir.
    PIXEL_TO_MM kalibrasyon değerleri, kameranızın çözünürlüğüne ve
    kameranın PCB'ye uzaklığına göre ayarlanmalıdır.
    """
    # Kamera çözünürlüğü (OCR için Yüksek Çözünürlük)
    CAMERA_WIDTH = 800
    CAMERA_HEIGHT = 1080

    # Yayın (Stream) için maksimum genişlik (Optimizasyon)
    STREAM_MAX_WIDTH = 800

    # Piksel → Milimetre dönüşüm katsayıları (kalibrasyon ile ayarlanır)
    PIXEL_TO_MM_X = 0.1
    PIXEL_TO_MM_Y = 0.1

    # Hedef nokta (ekran koordinatlarında, piksel cinsinden)
    TARGET_X = CAMERA_HEIGHT // 2
    TARGET_Y = CAMERA_WIDTH // 2

    # OCR parametreleri
    OCR_CONFIDENCE_THRESHOLD = 50
    STABILITY_DURATION = 0.1
    IOU_MATCH_THRESHOLD = 0.4

    # Motor hareket ayarları
    MOVE_STEP = 1.0
    FEED_RATE = 1000
    AUTO_CENTER_MAX_ITER = 10
    AUTO_CENTER_TOLERANCE = 5

    # Aranacak hedef yazılar (çoklu kelime desteği)
    TARGET_TEXT = "TEST"
    TARGET_WORDS = ["TEST"]
    
    # OCR Grupları ve Hedef Grup
    OCR_GROUPS = {
        "Varsayilan": ["TEST", "AYD", "CRB", "MUS", "SHN"],
        "Bilesenler": ["R1", "R2", "C1", "C2", "U1", "IC1"],
        "Etiketler": ["START", "STOP", "ERR", "OK"]
    }
    TARGET_GROUP = "Varsayilan"  # Aktif arama grubu
    
    # 2-Aşamalı Merkezleme
    FINE_TUNE_STEP_MM = 0.05     # İkinci aşama hassas adım
    FINE_TUNE_ENABLED = True

    # Seçilen hedef kelime (Eğer boş değilse, auto-center sadece bunu arar)
    SELECTED_TARGET_WORD = ""

    # Motor hareket yönü ters çevirme (eski, geriye uyumluluk)
    INVERT_X = True
    INVERT_Y = False

    # ── KALİBRASYON: Eksen Eşleme ─────────────────
    # Kamera montaj açısına göre ekran↔motor ekseni dönüşümü
    SWAP_AXES = True            # Ekran X↔Y yer değiştir (90° dönük kamera)
    NEGATE_SCREEN_X = False     # Ekran X yönünü ters çevir
    NEGATE_SCREEN_Y = True      # Ekran Y yönünü ters çevir

    # Konfigürasyon dosya yolu
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

    def to_dict(self):
        """JSON olarak döndür."""
        return {
            "pixel_to_mm_x": self.PIXEL_TO_MM_X,
            "pixel_to_mm_y": self.PIXEL_TO_MM_Y,
            "target_x": self.TARGET_X,
            "target_y": self.TARGET_Y,
            "move_step": self.MOVE_STEP,
            "target_text": self.TARGET_TEXT,
            "target_words": self.TARGET_WORDS,
            "auto_center_tolerance": self.AUTO_CENTER_TOLERANCE,
            "auto_center_max_iter": self.AUTO_CENTER_MAX_ITER,
            "invert_x": self.INVERT_X,
            "invert_y": self.INVERT_Y,
            "feed_rate": self.FEED_RATE,
            "camera_width": self.CAMERA_WIDTH,
            "camera_height": self.CAMERA_HEIGHT,
            "swap_axes": self.SWAP_AXES,
            "negate_screen_x": self.NEGATE_SCREEN_X,
            "negate_screen_y": self.NEGATE_SCREEN_Y,
            "negate_screen_x": self.NEGATE_SCREEN_X,
            "negate_screen_y": self.NEGATE_SCREEN_Y,
            "ocr_groups": self.OCR_GROUPS,
            "target_group": self.TARGET_GROUP,
            "fine_tune_step_mm": self.FINE_TUNE_STEP_MM,
            "fine_tune_enabled": self.FINE_TUNE_ENABLED,
            "stream_max_width": self.STREAM_MAX_WIDTH,
            "selected_target_word": self.SELECTED_TARGET_WORD,
        }

    def update_from_dict(self, data):
        """Web arayüzünden gelen verilerle güncelle."""
        if "pixel_to_mm_x" in data: self.PIXEL_TO_MM_X = float(data["pixel_to_mm_x"])
        if "pixel_to_mm_y" in data: self.PIXEL_TO_MM_Y = float(data["pixel_to_mm_y"])
        if "target_x" in data: self.TARGET_X = int(data["target_x"])
        if "target_y" in data: self.TARGET_Y = int(data["target_y"])
        if "move_step" in data: self.MOVE_STEP = float(data["move_step"])
        if "target_text" in data: self.TARGET_TEXT = str(data["target_text"])
        if "target_words" in data: self.TARGET_WORDS = list(data["target_words"])
        if "auto_center_tolerance" in data: self.AUTO_CENTER_TOLERANCE = int(data["auto_center_tolerance"])
        if "auto_center_max_iter" in data: self.AUTO_CENTER_MAX_ITER = int(data["auto_center_max_iter"])
        if "invert_x" in data: self.INVERT_X = bool(data["invert_x"])
        if "invert_y" in data: self.INVERT_Y = bool(data["invert_y"])
        if "feed_rate" in data: self.FEED_RATE = int(data["feed_rate"])
        if "swap_axes" in data: self.SWAP_AXES = bool(data["swap_axes"])
        if "negate_screen_x" in data: self.NEGATE_SCREEN_X = bool(data["negate_screen_x"])
        if "negate_screen_x" in data: self.NEGATE_SCREEN_X = bool(data["negate_screen_x"])
        if "negate_screen_y" in data: self.NEGATE_SCREEN_Y = bool(data["negate_screen_y"])
        if "ocr_groups" in data: self.OCR_GROUPS = data["ocr_groups"]
        if "target_group" in data: self.TARGET_GROUP = str(data["target_group"])
        if "fine_tune_step_mm" in data: self.FINE_TUNE_STEP_MM = float(data["fine_tune_step_mm"])
        if "fine_tune_enabled" in data: self.FINE_TUNE_enabled = bool(data["fine_tune_enabled"])
        if "stream_max_width" in data: self.STREAM_MAX_WIDTH = int(data["stream_max_width"])
        if "selected_target_word" in data: self.SELECTED_TARGET_WORD = str(data["selected_target_word"])
        
        # Target words'ü seçili gruba göre güncelle
        if self.TARGET_GROUP in self.OCR_GROUPS:
            self.TARGET_WORDS = self.OCR_GROUPS[self.TARGET_GROUP]
            
        self.save_config()

    def save_config(self):
        """Konfigürasyonu dosyaya kaydet."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            log.error(f"Config kayıt hatası: {e}")

    def load_config(self):
        """Konfigürasyonu dosyadan yükle."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.update_from_dict(data)
                    log.info("Konfigürasyon yüklendi.")
        except Exception as e:
            log.error(f"Config yükleme hatası: {e}")


# Global config nesnesi
config = Config()
config.load_config()


# ═══════════════════════════════════════════════════════════════════════════
#  HATA TAKİP SİSTEMİ
# ═══════════════════════════════════════════════════════════════════════════

error_log = []          # [{message, timestamp, level}]
MAX_ERRORS = 50         # Maksimum hata sayısı

def add_error(message, level="ERROR"):
    """Hata listesine yeni hata ekle — web arayüzüne toast olarak gönderilir."""
    entry = {
        "message": message,
        "timestamp": time.strftime('%H:%M:%S'),
        "level": level,
        "id": len(error_log)
    }
    error_log.append(entry)
    if len(error_log) > MAX_ERRORS:
        error_log.pop(0)

    # SocketIO ile web arayüzüne anında gönder
    try:
        from flask_socketio import SocketIO as _S
        socketio.emit('error_toast', entry)
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════════════════════
#  PNP MOTOR SÜRÜCÜSÜ (GRBL Serial)
# ═════════════════════════════════════════════════════════════════════════════

class PNPDriver:
    """
    GRBL tabanlı PNP makine sürücüsü.
    USB seri port üzerinden motor komutları gönderir.
    Otomatik port bulucu içerir.
    """

    def __init__(self, port=None):
        self.port = port
        self.ser = None
        self.connected = False
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
        self.grbl_state = "Unknown"    # Idle, Run, Hold, Alarm, etc.
        self.alarm_active = False
        self._lock = threading.Lock()

    def find_port(self):
        """Otomatik olarak GRBL cihazının bağlı olduğu portu bulur."""
        import serial
        import serial.tools.list_ports

        ports = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
        if not ports:
            return None

        log.info(f"Taranıyor: {', '.join(ports)}")

        for p in ports:
            try:
                s = serial.Serial(p, 115200, timeout=2)
                s.dtr = False
                time.sleep(0.5)
                s.flushInput()
                s.dtr = True
                time.sleep(3)

                # GRBL yanıtını kontrol et
                resp = ""
                t_start = time.time()
                while time.time() - t_start < 2:
                    if s.in_waiting:
                        resp += s.read(s.in_waiting).decode('utf-8', errors='ignore')
                    time.sleep(0.1)

                s.close()
                if 'grbl' in resp.lower():
                    return p
            except Exception:
                continue

        # GRBL bulunamadıysa ilk portu dene
        return ports[0] if ports else None

    def connect(self):
        """Seri porta bağlan ve GRBL'i başlat."""
        import serial

        if not self.port:
            self.port = self.find_port()

        if not self.port:
            log.warning("PNP portu bulunamadı — simülasyon modunda çalışılacak.")
            return False

        try:
            self.ser = serial.Serial(self.port, 115200, timeout=2)
            log.info(f"PNP bağlanıldı: {self.port}")

            # GRBL reset ve başlatma
            self.ser.dtr = False
            time.sleep(1)
            self.ser.flushInput()
            self.ser.dtr = True
            time.sleep(2)
            self.ser.flushInput()

            # Başlangıç komutları
            self.send("$X")    # Alarm kilidini aç
            self.send("G21")   # Milimetre modu
            self.send("G90")   # Mutlak koordinat
            self.send("G94")   # Feed rate modu

            self.connected = True
            return True

        except Exception as e:
            log.error(f"PNP bağlantı hatası: {e}")
            return False

    def send(self, cmd, timeout=5):
        """
        GRBL'e komut gönder ve 'ok' yanıtını bekle.
        Thread-safe: _lock ile korunur.
        Timeout 5 saniye — UI kilitlenmesini önler.
        """
        with self._lock:
            if not self.ser:
                log.debug(f"[SIM] {cmd}")
                return True

            try:
                full_cmd = cmd.strip() + '\r\n'
                self.ser.write(full_cmd.encode())

                start = time.time()
                while True:
                    if self.ser.in_waiting:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line == 'ok':
                            return True
                        if 'error' in line.lower():
                            error_msg = f"GRBL Hatası: {cmd} → {line}"
                            log.error(error_msg)
                            add_error(error_msg)
                            return False
                        if 'alarm' in line.lower():
                            self.alarm_active = True
                            self.grbl_state = 'Alarm'
                            error_msg = f"ALARM: {line}"
                            log.warning(error_msg)
                            add_error(error_msg)

                    if time.time() - start > timeout:
                        error_msg = f"Timeout ({timeout}s): {cmd}"
                        log.error(error_msg)
                        add_error(error_msg)
                        return False
                    time.sleep(0.01)

            except Exception as e:
                error_msg = f"Gönderme hatası ({cmd}): {e}"
                log.error(error_msg)
                add_error(error_msg)
                return False

    def move_relative(self, dx=0, dy=0, dz=0, feed=None):
        """
        Göreceli hareket (G91 ile).
        PNP kamerasının fiziksel montajına göre yön invertlenebilir.
        """
        if config.INVERT_X:
            dx = -dx
        if config.INVERT_Y:
            dy = -dy

        feed = feed or config.FEED_RATE

        # Göreceli modda hareket et, sonra mutlak moda dön
        self.send("G91")  # Relative
        cmd = f"G1 F{feed}"
        if dx != 0:
            cmd += f" X{dx:.3f}"
        if dy != 0:
            cmd += f" Y{dy:.3f}"
        if dz != 0:
            cmd += f" Z{dz:.3f}"

        log.info(f"Motor hareketi: dx={dx:.3f}mm, dy={dy:.3f}mm, dz={dz:.3f}mm")
        self.send(cmd)
        self.send("G4 P0")   # Senkronizasyon — hareketin tamamlanmasını bekle
        self.send("G90")     # Tekrar mutlak moda dön

        # Simüle pozisyon güncelleme
        self.current_x += dx
        self.current_y += dy
        self.current_z += dz

        return True

    def move_absolute(self, x=None, y=None, z=None, feed=None):
        """Mutlak koordinata hareket."""
        feed = feed or config.FEED_RATE
        cmd = f"G1 F{feed}"
        if x is not None:
            cmd += f" X{x:.2f}"
            self.current_x = x
        if y is not None:
            cmd += f" Y{y:.2f}"
            self.current_y = y
        if z is not None:
            cmd += f" Z{z:.2f}"
            self.current_z = z

        log.info(f"Mutlak hareket: {cmd}")
        self.send(cmd)
        self.send("G4 P0")
        return True

    def home(self):
        """Home komutu ($H) — tüm eksenleri referans noktasına taşır."""
        log.info("Home başlatılıyor ($H)...")
        if self.send("$H", timeout=60):
            log.info("Home tamamlandı.")
            self.send("G92 X0 Y0 Z0")
            self.current_x = 0.0
            self.current_y = 0.0
            self.current_z = 0.0
            time.sleep(1)
            return True
        else:
            log.error("Home hatası!")
            return False

    def pump(self, state):
        """Vakum pompasını aç (True) veya kapat (False)."""
        cmd = "M8" if state else "M9"
        log.info(f"Pompa: {'AÇIK' if state else 'KAPALI'}")
        self.send(cmd)
        self.send("G4 P0")

        # Kapatma güvenliği — tekrar gönder
        if not state:
            time.sleep(0.3)
            self.send("M9")
            self.send("G4 P0")
        return True

    def get_status(self):
        """Motor durumunu döndür."""
        return {
            "connected": self.connected,
            "port": self.port or "Yok",
            "x": round(self.current_x, 2),
            "y": round(self.current_y, 2),
            "z": round(self.current_z, 2),
            "state": self.grbl_state,
            "alarm": self.alarm_active,
        }

    def query_grbl_status(self):
        """
        GRBL'e '?' komutu göndererek gerçek zamanlı durum sorgular.
        Yanıt formatı: <Idle|MPos:0.000,0.000,0.000|...>
        State ve pozisyonu parse eder.
        """
        with self._lock:
            if not self.ser:
                return self.get_status()

            try:
                # Giriş buffer'ını temizle
                self.ser.flushInput()
                # '?' komutu \n gerektirmez
                self.ser.write(b'?')

                start = time.time()
                response = ""
                while time.time() - start < 1.0:
                    if self.ser.in_waiting:
                        chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                        response += chunk
                        if '>' in response:
                            break
                    time.sleep(0.01)

                # Parse: <Idle|MPos:0.000,0.000,0.000|FS:0,0>
                if '<' in response and '>' in response:
                    inner = response[response.index('<')+1:response.index('>')]
                    parts = inner.split('|')

                    if parts:
                        self.grbl_state = parts[0].strip()
                        self.alarm_active = 'alarm' in self.grbl_state.lower()

                    for part in parts:
                        if part.startswith('MPos:') or part.startswith('WPos:'):
                            coords = part.split(':')[1].split(',')
                            if len(coords) >= 3:
                                self.current_x = float(coords[0])
                                self.current_y = float(coords[1])
                                self.current_z = float(coords[2])

            except Exception as e:
                log.error(f"GRBL durum sorgulama hatası: {e}")

        return self.get_status()

    def soft_reset(self):
        """GRBL Soft Reset (Ctrl+X / 0x18) — tüm hareketi iptal eder."""
        with self._lock:
            if not self.ser:
                log.debug("[SIM] Soft Reset")
                return True
            try:
                self.ser.write(b'\x18')  # Ctrl+X
                time.sleep(1)
                self.ser.flushInput()
                log.info("Soft Reset gönderildi.")
                self.alarm_active = False
                self.grbl_state = "Reset"
                return True
            except Exception as e:
                log.error(f"Soft Reset hatası: {e}")
                return False

    def unlock(self):
        """GRBL Kilit Açma ($X) — alarm durumunu temizler."""
        log.info("Kilit açılıyor ($X)...")
        result = self.send("$X")
        if result:
            self.alarm_active = False
            self.grbl_state = "Idle"
            log.info("Kilit açıldı.")
        return result

    def close(self):
        """Bağlantıyı kapat."""
        if self.ser:
            try:
                self.send("M9")  # Pompayı güvenli kapat
            except Exception:
                pass
            self.ser.close()
            log.info("PNP bağlantısı kapatıldı.")
        self.connected = False


# ═════════════════════════════════════════════════════════════════════════════
#  KAMERA YÖNETİCİSİ (Picamera2 + MJPEG Stream)
# ═════════════════════════════════════════════════════════════════════════════

class CameraManager:
    """
    Kamera yöneticisi.
    Picamera2 ile görüntü yakalar, OCR için ayrı thread çalıştırır,
    MJPEG stream için annotasyonlu frame sağlar.
    """

    def __init__(self):
        self.picam2 = None
        self.active = False
        self.simulation = False

        # Frame verileri
        self.current_gray = None          # Gri tonlamalı (display için)
        self.current_thresh = None        # Threshold (OCR için)
        self.annotated_frame = None       # Kutu + çizgi çizilmiş frame (stream için)
        self.frame_lock = threading.Lock()

        # OCR sonuçları
        self.ocr_results = []             # [{text, rect, center}]
        self.ocr_lock = threading.Lock()
        self.ocr_fps = 0.0
        self.display_fps = 0.0
        self.stable_boxes = {}
        self.box_id_counter = 0

        # Auto-center durumu
        self.auto_centering = False
        self.auto_center_status = ""

    def start(self):
        """Kamerayı başlat."""
        try:
            from picamera2 import Picamera2

            self.picam2 = Picamera2()
            cam_config = self.picam2.create_preview_configuration(
                main={
                    "size": (config.CAMERA_WIDTH, config.CAMERA_HEIGHT),
                    "format": "RGB888"
                }
            )
            self.picam2.configure(cam_config)
            self.picam2.start()

            # Oto-fokus ve beyaz ayarı
            try:
                self.picam2.set_controls({"AfMode": 2, "AwbMode": 0})
            except Exception as e:
                log.warning(f"Kamera kontrol ayarı uygulanamadı: {e}")

            self.active = True
            log.info(f"Kamera aktif ({config.CAMERA_WIDTH}x{config.CAMERA_HEIGHT})")

        except ImportError:
            log.warning("Picamera2 bulunamadı — simülasyon modu aktif")
            self.simulation = True
            self.active = True

        except Exception as e:
            log.error(f"Kamera başlatma hatası: {e}")
            self.simulation = True
            self.active = True

    def capture_frame(self):
        """
        Tek frame yakala, gri tonlamaya çevir, threshold uygula.
        Simülasyon modunda siyah ekran döndürür.
        """
        if self.simulation:
            # Simülasyon — test için siyah ekran + metin
            h = config.CAMERA_HEIGHT
            w = config.CAMERA_WIDTH
            frame = np.zeros((w, h, 3), dtype=np.uint8)  # rotate sonrası boyut
            cv2.putText(frame, "SIMULASYON", (20, w // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return gray, gray, frame

        try:
            frame_rgb = self.picam2.capture_array()

            # RGB → Grayscale ve 90° saat yönünde döndür
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            gray_rotated = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)

            # OCR için threshold
            blurred = cv2.GaussianBlur(gray_rotated, (3, 3), 0)
            _, thresh = cv2.threshold(
                blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            kernel = np.ones((2, 2), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            # Gösterim için BGR'ye çevir (renkli annotasyonlar için)
            display = cv2.cvtColor(gray_rotated, cv2.COLOR_GRAY2BGR)

            return gray_rotated, thresh, display

        except Exception as e:
            log.error(f"Frame yakalama hatası: {e}")
            return None, None, None

    def iou(self, box1, box2):
        """İki dikdörtgen arasındaki Intersection over Union hesabı."""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)

        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0

        inter = (xi2 - xi1) * (yi2 - yi1)
        union = w1 * h1 + w2 * h2 - inter
        return inter / union if union > 0 else 0.0

    def update_stable_boxes(self, new_detections):
        """
        Algılama kararlılığı: IoU ile eşleştir, kısa süreli kayıpları tolere et.
        OCR sonuçlarının titremesini (flickering) önler.
        """
        now = time.time()

        for det in new_detections:
            best_id = None
            best_score = config.IOU_MATCH_THRESHOLD
            for bid, sbox in self.stable_boxes.items():
                score = self.iou(det['rect'], sbox['rect'])
                if score > best_score:
                    best_score = score
                    best_id = bid

            if best_id is not None:
                self.stable_boxes[best_id]['rect'] = det['rect']
                self.stable_boxes[best_id]['text'] = det['text']
                self.stable_boxes[best_id]['last_seen'] = now
            else:
                self.box_id_counter += 1
                self.stable_boxes[self.box_id_counter] = {
                    'rect': det['rect'],
                    'text': det['text'],
                    'last_seen': now,
                }

        # Süresi dolmuş kutuları temizle
        expired = [
            bid for bid, sbox in self.stable_boxes.items()
            if now - sbox['last_seen'] > config.STABILITY_DURATION
        ]
        for bid in expired:
            del self.stable_boxes[bid]

    def ocr_worker(self):
        """
        OCR arka plan thread'i.
        Threshold görüntüsü üzerinde tesserocr ile yazı algılama yapar.
        """
        try:
            import tesserocr
        except ImportError:
            log.warning("tesserocr bulunamadı — OCR devre dışı.")
            return
        except Exception as e:
            log.error(f"tesserocr yüklenirken hata: {e}")
            return

        try:
            api = tesserocr.PyTessBaseAPI(
                path='/usr/share/tesseract-ocr/5/tessdata/',
                lang='eng',
                psm=tesserocr.PSM.SPARSE_TEXT,
                oem=tesserocr.OEM.LSTM_ONLY
            )
            api.SetVariable("tessedit_do_invert", "0")
        except Exception as e:
            log.error(f"Tesseract başlatılamadı: {e}")
            return

        log.info("OCR worker başlatıldı.")

        while self.active:
            if self.current_thresh is not None:
                t_start = time.time()

                with self.frame_lock:
                    frame_ocr = self.current_thresh.copy()

                img_h, img_w = frame_ocr.shape[:2]

                try:
                    pil_image = Image.fromarray(frame_ocr)
                    api.SetImage(pil_image)

                    # WORD seviyesinde algılama
                    boxes = api.GetComponentImages(tesserocr.RIL.WORD, True)

                    new_detections = []
                    for i, (im, box, _, _) in enumerate(boxes):
                        x = box['x']
                        y = box['y']
                        w_box = box['w']
                        h_box = box['h']

                        # Sınır kontrolü
                        if x < 0 or y < 0 or x + w_box > img_w or y + h_box > img_h:
                            continue
                        if w_box <= 0 or h_box <= 0:
                            continue

                        api.SetRectangle(x, y, w_box, h_box)
                        text = api.GetUTF8Text().strip()
                        conf = api.MeanTextConf()

                        if conf > config.OCR_CONFIDENCE_THRESHOLD and text:
                            # ── Fuzzy Matching (Bulanık Eşleşme) ──
                            # Algılanan metni, tanımlı gruplardaki kelimelerle karşılaştır
                            # Eğer benzerlik %80 üzerindeyse, doğrusuyla değiştir
                            best_match = None
                            highest_ratio = 0.0
                            
                            # Tüm gruplardaki kelimeleri kontrol et
                            all_known_words = []
                            for words in config.OCR_GROUPS.values():
                                all_known_words.extend(words)
                                
                            matches = difflib.get_close_matches(text, all_known_words, n=1, cutoff=0.7)
                            if matches:
                                # Eğer eşleşme varsa, metni düzelt
                                corrected_text = matches[0]
                                if corrected_text != text:
                                    log.debug(f"OCR Düzeltme: '{text}' -> '{corrected_text}'")
                                    text = corrected_text

                            new_detections.append({
                                'rect': (x, y, w_box, h_box),
                                'text': text
                            })

                    # Kararlı kutuları güncelle
                    with self.ocr_lock:
                        self.update_stable_boxes(new_detections)
                        self.ocr_results = []
                        for sb in self.stable_boxes.values():
                            x, y, w, h = sb['rect']
                            # Merkez noktası hesapla
                            cx = x + w // 2
                            cy = y + h // 2
                            self.ocr_results.append({
                                'rect': (x, y, w, h),
                                'text': sb['text'],
                                'center': (cx, cy)
                            })

                except Exception as e:
                    log.error(f"OCR hatası: {e}")

                elapsed = time.time() - t_start
                if elapsed > 0:
                    self.ocr_fps = 1.0 / elapsed

            time.sleep(0.001)

        api.End()
        log.info("OCR worker durduruldu.")

    def camera_worker(self):
        """
        Kamera arka plan thread'i.
        Sürekli frame yakalar, OCR için threshold verir,
        annotasyonlu display frame oluşturur.
        """
        frame_count = 0
        fps_start = time.time()

        log.info("Kamera worker başlatıldı.")

        while self.active:
            gray, thresh, display_full = self.capture_frame()

            if display_full is None:
                time.sleep(0.01)
                continue

            # OCR thread'ine threshold ver (TAM ÇÖZÜNÜRLÜK)
            with self.frame_lock:
                self.current_thresh = thresh.copy()
                self.current_gray = gray

            # ─── Display Frame Optimizasyonu (Resize) ─────────────
            h_full, w_full = display_full.shape[:2]
            target_w = config.STREAM_MAX_WIDTH
            
            if w_full > target_w:
                scale = target_w / w_full
                new_h = int(h_full * scale)
                display = cv2.resize(display_full, (target_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                scale = 1.0
                display = display_full

            img_h, img_w = display.shape[:2]

            # ─── Annotasyonlar (kutu, çapraz çizgi, merkez) ─────────────
            with self.ocr_lock:
                results_copy = list(self.ocr_results)

            for item in results_copy:
                # Orijinal (Tam Çözünürlük) koordinatlar
                ox, oy, ow, oh = item['rect']
                otext = item['text']
                ocx, ocy = item['center']

                # Display için ölçeklenmiş koordinatlar
                x = int(ox * scale)
                y = int(oy * scale)
                w = int(ow * scale)
                h = int(oh * scale)
                cx = int(ocx * scale)
                cy = int(ocy * scale)

                # ── Bounding box (yeşil dikdörtgen)
                cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # ── Çapraz çizgiler (köşelerden merkeze — turuncu)
                cv2.line(display, (x, y), (x + w, y + h), (0, 165, 255), 1)
                cv2.line(display, (x + w, y), (x, y + h), (0, 165, 255), 1)

                # ── Merkez noktası (kırmızı daire)
                cv2.circle(display, (cx, cy), 5, (0, 0, 255), -1)

                # ── Yazı etiketi (KIRMIZI ve BÜYÜK font)
                label = f"{otext} ({ocx},{ocy})"
                # Arkaplan kutusu (okunabilirlik için)
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(display, (x, y - th - 6), (x + tw, y), (255, 255, 255), -1)
                
                cv2.putText(display, label, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # ─── Hedef nokta crosshair (ekranın ortası — mavi) ──────────
            # Hedef nokta da ölçeklenmeli
            tx = int(config.TARGET_X * scale)
            ty = int(config.TARGET_Y * scale)
            
            # Yatay çizgi
            cv2.line(display, (tx - 20, ty), (tx + 20, ty), (255, 100, 0), 1)
            # Dikey çizgi
            cv2.line(display, (tx, ty - 20), (tx, ty + 20), (255, 100, 0), 1)
            # Dış daire
            cv2.circle(display, (tx, ty), 15, (255, 100, 0), 1)

            # ─── FPS bilgisi (Artık Client-side overlay'e taşındı, buraya yazmıyoruz) ────
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                self.display_fps = frame_count / elapsed
                frame_count = 0
                fps_start = time.time()

            # Auto-center durumu
            if self.auto_centering:
                cv2.putText(display, "AUTO-CENTER AKTIF", (5, img_h - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Annotasyonlu frame'i kaydet (stream için)
            with self.frame_lock:
                self.annotated_frame = display.copy()

            time.sleep(0.001)

        log.info("Kamera worker durduruldu.")

    def get_mjpeg_frame(self):
        """Annotasyonlu frame'i JPEG olarak döndür (MJPEG stream için)."""
        with self.frame_lock:
            if self.annotated_frame is None:
                return None
            _, jpeg = cv2.imencode('.jpg', self.annotated_frame, [
                cv2.IMWRITE_JPEG_QUALITY, 80
            ])
            return jpeg.tobytes()

    def find_target_text(self):
        """
        Hedef yazıları OCR sonuçlarından bul.
        Eğer config.SELECTED_TARGET_WORD ayarlıysa, SADECE onu arar.
        Değilse, config.TARGET_WORDS listesindeki herhangi birini arar.
        """
        target_exact = config.SELECTED_TARGET_WORD.strip()
        
        with self.ocr_lock:
            for item in self.ocr_results:
                txt = item['text']
                txt_lower = txt.lower()
                
                # 1. Öncelik: Seçili kelime (Tam veya kapsayan eşleşme)
                if target_exact:
                    # Fuzzy match zaten ocr_worker'da yapıldı, burada direkt kontrol edebiliriz
                    # Ancak kullanıcı "R1" seçtiyse ve OCR "R1" döndürdüyse eşleşmeli
                    if target_exact == txt or target_exact in txt:
                        return item
                    continue # Seçili kelime varsa diğerlerine bakma

                # 2. Öncelik: Liste tarama (Genel mod)
                for word in config.TARGET_WORDS:
                    if word.lower() in txt_lower:
                        return item
                
                # Geriye dönük uyumluluk
                if config.TARGET_TEXT.lower() in txt_lower:
                    return item
        return None

    def stop(self):
        """Kamerayı ve thread'leri durdur."""
        self.active = False
        if self.picam2:
            try:
                self.picam2.stop()
            except Exception:
                pass
        log.info("Kamera durduruldu.")


# ═════════════════════════════════════════════════════════════════════════════
#  AUTO-CENTER ALGORİTMASI
# ═════════════════════════════════════════════════════════════════════════════

def auto_center(camera: CameraManager, pnp: PNPDriver, socketio: SocketIO, target_word=None):
    """
    Tespit edilen hedef yazıyı ekranın merkezine taşır.
    İki aşamalı hassas merkezleme yapılır:
      1. Kaba Merkezleme (Normal hız/adım)
      2. Hassas Merkezleme (Düşük hız/küçük adım)
    """
    camera.auto_centering = True
    camera.auto_center_status = "Başlatılıyor..."
    socketio.emit('auto_center_update', {'status': 'started', 'message': 'Auto-center başlatıldı'})

    try:
        # ─── 1. AŞAMA: KABA MERKEZLEME ───
        log.info("--- AŞAMA 1: KABA MERKEZLEME ---")
        
        # Başlangıç parametreleri
        coarse_tolerance = config.AUTO_CENTER_TOLERANCE
        
        success_first_pass = False
        
        for iteration in range(config.AUTO_CENTER_MAX_ITER):
            time.sleep(0.5) # Stabilizasyon

            target = camera.find_target_text()
            if target is None:
                what_to_search = target_word if target_word else (config.SELECTED_TARGET_WORD if config.SELECTED_TARGET_WORD else config.TARGET_GROUP)
                msg = f"Hedef bulunamadı! ({what_to_search})"
                camera.auto_center_status = msg
                socketio.emit('auto_center_update', {'status': 'error', 'message': msg})
                log.warning(msg)
                return

            cx, cy = target['center']
            tx, ty = config.TARGET_X, config.TARGET_Y
            dx_px = cx - tx
            dy_px = cy - ty

            # Yeterince yakın mı?
            if abs(dx_px) <= coarse_tolerance and abs(dy_px) <= coarse_tolerance:
                msg = f"Kaba merkezleme tamamlandı. ({cx},{cy})"
                camera.auto_center_status = msg
                socketio.emit('auto_center_update', {'status': 'moving', 'message': msg})
                log.info(msg)
                success_first_pass = True
                break

            # Hareket (Kaba)
            screen_dx_mm = dx_px * config.PIXEL_TO_MM_X
            screen_dy_mm = dy_px * config.PIXEL_TO_MM_Y
            motor_dx, motor_dy = screen_to_motor(screen_dx_mm, screen_dy_mm)

            pnp.move_relative(dx=motor_dx, dy=motor_dy)
            time.sleep(0.8)

        if not success_first_pass:
            msg = "Kaba merkezleme başarısız (iterasyon aşıldı)."
            camera.auto_center_status = msg
            socketio.emit('auto_center_update', {'status': 'error', 'message': msg})
            return

        # ─── 2. AŞAMA: HASSAS MERKEZLEME (Opsiyonel) ───
        if config.FINE_TUNE_ENABLED:
            time.sleep(1.0) # Ekstra stabilizasyon
            log.info("--- AŞAMA 2: HASSAS MERKEZLEME ---")
            
            fine_tolerance = max(1, coarse_tolerance // 2) # Daha sıkı tolerans
            
            # Tek bir hassas düzeltme hamlesi yapıyoruz veya tekrar döngüye sokuyoruz
            # Burada 3 iterasyonluk hassas döngü kuralım
            for i in range(3):
                time.sleep(0.5)
                target = camera.find_target_text()
                if not target: break
                
                cx, cy = target['center']
                tx, ty = config.TARGET_X, config.TARGET_Y
                dx_px = cx - tx
                dy_px = cy - ty
                
                # Çok çok yakınsa bitir
                if abs(dx_px) <= fine_tolerance and abs(dy_px) <= fine_tolerance:
                    break
                    
                # Hassas hareket hesabı
                screen_dx_mm = dx_px * config.PIXEL_TO_MM_X
                screen_dy_mm = dy_px * config.PIXEL_TO_MM_Y
                
                # Hareket miktarını FINE_TUNE_STEP_MM ile sınırla (aşırı salınımı önlemek için)
                # Ancak burada amaç tam gitmek, sadece son bir dokunuş.
                # Kullanıcı isteği: "ikinci seferinde düşük step size olsun"
                # Bu yüzden hesaplanan değer yerine sabit küçük adım atmak yerine,
                # hesaplanan değeri kullanıp G-code tarafında yavaş gitmek daha doğru olabilir.
                # Fakat kullanıcının isteği "step size" olduğu için, 
                # eğer fark büyükse bile maksimum config.FINE_TUNE_STEP_MM kadar git diyelim.
                
                # X ekseni için clamp
                if abs(screen_dx_mm) > config.FINE_TUNE_STEP_MM:
                    screen_dx_mm = config.FINE_TUNE_STEP_MM * (1 if screen_dx_mm > 0 else -1)
                
                # Y ekseni için clamp
                if abs(screen_dy_mm) > config.FINE_TUNE_STEP_MM:
                    screen_dy_mm = config.FINE_TUNE_STEP_MM * (1 if screen_dy_mm > 0 else -1)
                    
                motor_dx, motor_dy = screen_to_motor(screen_dx_mm, screen_dy_mm)
                
                # Düşük hızda hareket (Feed rate'i düşürebiliriz ama şimdilik normal kalsın, mesafe kısa)
                pnp.move_relative(dx=motor_dx, dy=motor_dy)
                time.sleep(1.0) # Tam durmayı bekle

        # ─── SON KONTROL ───
        time.sleep(0.5)
        target = camera.find_target_text()
        final_pos = target['center'] if target else (0,0)

        msg = f"MERKEZLENDİ! ✓ ({final_pos[0]},{final_pos[1]})"
        camera.auto_center_status = msg
        socketio.emit('auto_center_update', {
            'status': 'done',
            'message': msg,
            'center': {'x': final_pos[0], 'y': final_pos[1]}
        })
        log.info(msg)

    except Exception as e:
        msg = f"Auto-center hatası: {e}"
        camera.auto_center_status = msg
        socketio.emit('auto_center_update', {'status': 'error', 'message': msg})
        log.error(msg)

    finally:
        camera.auto_centering = False


# ═════════════════════════════════════════════════════════════════════════════
#  FLASK WEB SUNUCUSU
# ═════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pnp-control-secret-key-2026'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 saat session ömrü
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global nesneler
camera = CameraManager()
pnp = PNPDriver()

# ─── Kullanıcı kimlik bilgileri ──────────────────────────────────────────────
USERNAME = "admin"
PASSWORD = "admin"

# Sistem başlangıç zamanı (uptime hesabı için)
SYSTEM_START_TIME = time.time()

# ─── Log mesajlarını web arayüzüne iletmek için özel handler ────────────────
class SocketIOHandler(logging.Handler):
    """Log mesajlarını SocketIO üzerinden web arayüzüne gönderir."""
    def emit(self, record):
        try:
            msg = self.format(record)
            socketio.emit('log_message', {
                'message': msg,
                'level': record.levelname,
                'timestamp': time.strftime('%H:%M:%S')
            })
        except Exception:
            pass

# SocketIO log handler ekle
sio_handler = SocketIOHandler()
sio_handler.setFormatter(logging.Formatter("%(levelname)s — %(message)s"))
log.addHandler(sio_handler)


# ─── Kimlik doğrulama dekoratörü ─────────────────────────────────────────────
def login_required(f):
    """Oturum doğrulama dekoratörü — giriş yapmamış kullanıcıyı login'e yönlendirir."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            # API istekleri için JSON hata dön
            if request.path.startswith('/api/') or request.path == '/video_feed':
                return jsonify({'error': 'Unauthorized', 'message': 'Giriş yapın'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Sayfalar ────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Giriş sayfası."""
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = time.strftime('%H:%M:%S')
            session.permanent = True
            log.info(f"Kullanıcı giriş yaptı: {username}")
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Hatalı kullanıcı adı veya şifre!')

    return render_template('login.html', error=None)


@app.route('/logout')
def logout():
    """Çıkış yap."""
    user = session.get('username', 'unknown')
    session.clear()
    log.info(f"Kullanıcı çıkış yaptı: {user}")
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Ana web sayfası."""
    return render_template('index.html')


# ─── Video stream ────────────────────────────────────────────────────────────

def generate_mjpeg():
    """MJPEG stream generator — her frame'i multipart response olarak verir."""
    while True:
        frame = camera.get_mjpeg_frame()
        if frame is not None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )
        else:
            time.sleep(0.05)


@app.route('/video_feed')
@login_required
def video_feed():
    """Canlı kamera görüntüsü MJPEG stream endpoint'i."""
    return Response(
        generate_mjpeg(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ─── REST API Endpoint'leri ──────────────────────────────────────────────────

@app.route('/api/status')
@login_required
def api_status():
    """Sistem durumunu JSON olarak döndür."""
    with camera.ocr_lock:
        ocr_data = []
        for item in camera.ocr_results:
            ocr_data.append({
                'text': item['text'],
                'rect': item['rect'],
                'center': item['center']
            })

    return jsonify({
        'camera': {
            'active': camera.active,
            'simulation': camera.simulation,
            'fps': round(camera.display_fps, 1),
            'ocr_fps': round(camera.ocr_fps, 1),
        },
        'motor': pnp.get_status(),
        'ocr': ocr_data,
        'auto_centering': camera.auto_centering,
        'auto_center_status': camera.auto_center_status,
        'config': config.to_dict(),
    })


def screen_to_motor(screen_dx, screen_dy):
    """
    Ekran piksel/mm farkını motor eksenlerine dönüştür.
    Kalibrasyon ayarlarına göre swap ve negate uygular.
    """
    sx = screen_dx
    sy = screen_dy

    # Yön ters çevirme
    if config.NEGATE_SCREEN_X:
        sx = -sx
    if config.NEGATE_SCREEN_Y:
        sy = -sy

    # Eksen değiştirme
    if config.SWAP_AXES:
        motor_dx = sy
        motor_dy = sx
    else:
        motor_dx = sx
        motor_dy = sy

    return motor_dx, motor_dy


@app.route('/api/move', methods=['POST'])
@login_required
def api_move():
    """
    Manuel motor hareketi.
    JSON body: {"x": float, "y": float}  (mm cinsinden göreceli hareket)
    Kalibrasyon ayarlarına göre eksen dönüşümü uygulanır.
    """
    data = request.get_json()
    screen_dx = float(data.get('x', 0))
    screen_dy = float(data.get('y', 0))
    dz = float(data.get('z', 0))

    motor_dx, motor_dy = screen_to_motor(screen_dx, screen_dy)
    success = pnp.move_relative(dx=motor_dx, dy=motor_dy, dz=dz)
    socketio.emit('motor_update', pnp.get_status())
    return jsonify({'success': success, 'motor': pnp.get_status()})


@app.route('/api/home', methods=['POST'])
@login_required
def api_home():
    """Home komutu — tüm eksenleri sıfırla."""
    def _home():
        success = pnp.home()
        socketio.emit('motor_update', pnp.get_status())
        socketio.emit('log_message', {
            'message': 'Home ' + ('tamamlandı' if success else 'hatası!'),
            'level': 'INFO' if success else 'ERROR',
            'timestamp': time.strftime('%H:%M:%S')
        })
    threading.Thread(target=_home, daemon=True).start()
    return jsonify({'success': True, 'message': 'Home başlatıldı...'})


@app.route('/api/auto_center', methods=['POST'])
@login_required
def api_auto_center():
    """Auto-center başlat — hedef yazıyı ekran merkezine taşı. JSON: {"target_word": "TEST"}"""
    if camera.auto_centering:
        return jsonify({'success': False, 'message': 'Auto-center zaten çalışıyor!'})

    data = request.get_json() or {}
    target_word = data.get('target_word', '').strip()

    # Kullanıcı özel bir kelime girdiyse, Config'e kaydet (seçili olarak)
    if target_word:
        config.SELECTED_TARGET_WORD = target_word
        config.save_config()

    threading.Thread(
        target=auto_center,
        args=(camera, pnp, socketio, target_word),
        daemon=True
    ).start()

    return jsonify({'success': True, 'message': 'Auto-center başlatıldı'})


@app.route('/api/pump', methods=['POST'])
@login_required
def api_pump():
    """Pompa aç/kapat. JSON body: {"state": true/false}"""
    data = request.get_json()
    state = bool(data.get('state', False))
    success = pnp.pump(state)
    return jsonify({
        'success': success,
        'state': state,
        'message': f"Pompa {'açıldı' if state else 'kapatıldı'}"
    })


@app.route('/api/config', methods=['GET'])
@login_required
def api_get_config():
    """Konfigürasyonu döndür."""
    return jsonify(config.to_dict())


@app.route('/api/config', methods=['POST'])
@login_required
def api_set_config():
    """Konfigürasyonu güncelle. JSON body: {key: value, ...}"""
    data = request.get_json()
    config.update_from_dict(data)
    log.info(f"Konfigürasyon güncellendi: {data}")
    return jsonify({'success': True, 'config': config.to_dict()})


@app.route('/api/camera/resolution', methods=['GET'])
@login_required
def api_get_camera_resolution():
    """Kamera çözünürlüğünü döndür."""
    return jsonify({
        'width': config.CAMERA_WIDTH,
        'height': config.CAMERA_HEIGHT
    })


@app.route('/api/camera/resolution', methods=['POST'])
@login_required
def api_set_camera_resolution():
    """Kamera çözünürlüğünü değiştir. JSON: {width: int, height: int}"""
    data = request.get_json()
    new_w = int(data.get('width', config.CAMERA_WIDTH))
    new_h = int(data.get('height', config.CAMERA_HEIGHT))

    config.CAMERA_WIDTH = new_w
    config.CAMERA_HEIGHT = new_h

    # Hedef noktayı yeni çözünürlüğün merkezine güncelle
    config.TARGET_X = new_h // 2
    config.TARGET_Y = new_w // 2

    config.save_config()

    # Kamerayı yeniden başlat
    log.info(f"Kamera çözünürlüğü değiştirildi: {new_w}x{new_h}, Yeni Merkez: ({config.TARGET_X}, {config.TARGET_Y})")
    try:
        if hasattr(camera, 'picam2') and camera.picam2:
            camera.picam2.stop()
            cam_config = camera.picam2.create_preview_configuration(
                main={"size": (new_w, new_h), "format": "RGB888"}
            )
            camera.picam2.configure(cam_config)
            camera.picam2.start()
            log.info("Kamera yeniden başlatıldı")
    except Exception as e:
        log.error(f"Kamera yeniden başlatma hatası: {e}")
        add_error(f"Kamera yeniden başlatma hatası: {e}")

    return jsonify({
        'success': True,
        'width': config.CAMERA_WIDTH,
        'height': config.CAMERA_HEIGHT
    })


@app.route('/api/target_words', methods=['GET'])
@login_required
def api_get_target_words():
    """Hedef kelime listesini döndür."""
    return jsonify({'words': config.TARGET_WORDS})


@app.route('/api/target_words', methods=['POST'])
@login_required
def api_set_target_words():
    """Hedef kelime ekle veya listeyi güncelle. JSON: {"action":"add|remove|set", "word":"...", "words":[...]}"""
    data = request.get_json()
    action = data.get('action', 'set')

    if action == 'add':
        word = data.get('word', '').strip()
        if word and word not in config.TARGET_WORDS:
            config.TARGET_WORDS.append(word)
            log.info(f"Hedef kelime eklendi: {word}")
    elif action == 'remove':
        word = data.get('word', '').strip()
        if word in config.TARGET_WORDS:
            config.TARGET_WORDS.remove(word)
            log.info(f"Hedef kelime silindi: {word}")
    elif action == 'set':
        words = data.get('words', [])
        config.TARGET_WORDS = [w.strip() for w in words if w.strip()]
        log.info(f"Hedef kelimeler güncellendi: {config.TARGET_WORDS}")

    config.save_config()
    return jsonify({'success': True, 'words': config.TARGET_WORDS})


@app.route('/api/calibration/test', methods=['POST'])
@login_required
def api_calibration_test():
    """
    Kalibrasyon testi: Ham motor hareketi (dönüşüm yok).
    JSON body: {"axis": "x"|"y", "direction": 1|-1, "step": float}
    Bu endpoint screen_to_motor dönüşümünü atlar — doğrudan motor eksenine gider.
    """
    data = request.get_json()
    axis = data.get('axis', 'x')
    direction = int(data.get('direction', 1))
    step = float(data.get('step', 2.0))

    dx = step * direction if axis == 'x' else 0
    dy = step * direction if axis == 'y' else 0

    log.info(f"Kalibrasyon testi: axis={axis}, dir={direction}, step={step}")
    success = pnp.move_relative(dx=dx, dy=dy)
    socketio.emit('motor_update', pnp.get_status())
    return jsonify({
        'success': success,
        'axis': axis,
        'direction': direction,
        'motor': pnp.get_status()
    })


@app.route('/api/calibration', methods=['POST'])
@login_required
def api_save_calibration():
    """
    Kalibrasyon ayarlarını kaydet.
    JSON body: {"swap_axes": bool, "negate_screen_x": bool, "negate_screen_y": bool}
    """
    data = request.get_json()
    if 'swap_axes' in data:
        config.SWAP_AXES = bool(data['swap_axes'])
    if 'negate_screen_x' in data:
        config.NEGATE_SCREEN_X = bool(data['negate_screen_x'])
    if 'negate_screen_y' in data:
        config.NEGATE_SCREEN_Y = bool(data['negate_screen_y'])
    config.save_config()
    log.info(f"Kalibrasyon güncellendi: swap={config.SWAP_AXES}, negX={config.NEGATE_SCREEN_X}, negY={config.NEGATE_SCREEN_Y}")
    return jsonify({
        'success': True,
        'swap_axes': config.SWAP_AXES,
        'negate_screen_x': config.NEGATE_SCREEN_X,
        'negate_screen_y': config.NEGATE_SCREEN_Y,
    })


@app.route('/api/errors')
@login_required
def api_get_errors():
    """Son hataları döndür."""
    return jsonify({'errors': error_log[-20:]})


@app.route('/api/errors/clear', methods=['POST'])
@login_required
def api_clear_errors():
    """Hata logunu temizle."""
    error_log.clear()
    return jsonify({'success': True})


@app.route('/api/send_gcode', methods=['POST'])
@login_required
def api_send_gcode():
    """Manuel G-code komutu gönder. JSON body: {"command": "G0 X10 Y10"}"""
    data = request.get_json()
    cmd = data.get('command', '').strip()
    if not cmd:
        return jsonify({'success': False, 'message': 'Komut boş!'})

    log.info(f"Manuel G-code: {cmd}")
    success = pnp.send(cmd)
    return jsonify({
        'success': success,
        'command': cmd,
        'message': f"'{cmd}' {'başarılı' if success else 'HATA!'}"
    })


@app.route('/api/emergency_stop', methods=['POST'])
@login_required
def api_emergency_stop():
    """Acil durum durdurma — tüm hareketi durdur, pompayı kapat."""
    log.warning("⚠️ ACİL DURUM DURDURMA AKTİF!")
    pnp.send("!")
    time.sleep(0.1)
    pnp.send("M9")
    pnp.send("$X")
    socketio.emit('log_message', {
        'message': '⚠️ ACİL DURDURMA — Tüm hareket durduruldu!',
        'level': 'ERROR',
        'timestamp': time.strftime('%H:%M:%S')
    })
    return jsonify({'success': True, 'message': 'Acil durdurma uygulandı!'})


@app.route('/api/soft_reset', methods=['POST'])
@login_required
def api_soft_reset():
    """GRBL Soft Reset (Ctrl+X)."""
    success = pnp.soft_reset()
    socketio.emit('motor_update', pnp.get_status())
    return jsonify({'success': success, 'message': 'Soft Reset ' + ('başarılı' if success else 'HATA!')})


@app.route('/api/unlock', methods=['POST'])
@login_required
def api_unlock():
    """GRBL Kilit Açma ($X) — alarm durumunu temizle."""
    success = pnp.unlock()
    socketio.emit('motor_update', pnp.get_status())
    return jsonify({'success': success, 'message': 'Kilit ' + ('açıldı' if success else 'açılamadı!')})


@app.route('/api/grbl_status')
@login_required
def api_grbl_status():
    """GRBL gerçek zamanlı durum sorgulama (? komutu)."""
    status = pnp.query_grbl_status()
    return jsonify(status)


@app.route('/api/uptime')
@login_required
def api_uptime():
    """Sistem çalışma süresini döndür."""
    uptime_sec = int(time.time() - SYSTEM_START_TIME)
    hours = uptime_sec // 3600
    minutes = (uptime_sec % 3600) // 60
    seconds = uptime_sec % 60
    return jsonify({
        'uptime_seconds': uptime_sec,
        'uptime_formatted': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
        'start_time': time.strftime('%H:%M:%S', time.localtime(SYSTEM_START_TIME))
    })


# ─── SocketIO Olayları ──────────────────────────────────────────────────────

@socketio.on('connect')
def handle_connect():
    """Yeni websocket bağlantısı — tüm başlangıç verileri gönderilir."""
    log.info("Web istemci bağlandı.")
    with camera.ocr_lock:
        ocr_data = []
        for item in camera.ocr_results:
            ocr_data.append({
                'text': item['text'],
                'rect': list(item['rect']),
                'center': list(item['center'])
            })

    socketio.emit('status_update', {
        'motor': pnp.get_status(),
        'config': config.to_dict(),
        'camera_fps': round(camera.display_fps, 1),
        'ocr_fps': round(camera.ocr_fps, 1),
        'ocr': ocr_data,
        'auto_centering': camera.auto_centering,
    })


@socketio.on('request_status')
def handle_status_request():
    """Manuel durum isteği."""
    with camera.ocr_lock:
        ocr_data = []
        for item in camera.ocr_results:
            ocr_data.append({
                'text': item['text'],
                'rect': list(item['rect']),
                'center': list(item['center'])
            })

    socketio.emit('status_update', {
        'motor': pnp.get_status(),
        'camera_fps': round(camera.display_fps, 1),
        'ocr_fps': round(camera.ocr_fps, 1),
        'ocr': ocr_data,
        'auto_centering': camera.auto_centering,
    })


def periodic_status_emitter():
    """Her saniye durum güncellemesi yayınla."""
    while True:
        try:
            with camera.ocr_lock:
                ocr_data = []
                for item in camera.ocr_results:
                    ocr_data.append({
                        'text': item['text'],
                        'rect': list(item['rect']),
                        'center': list(item['center'])
                    })

            socketio.emit('status_update', {
                'motor': pnp.get_status(),
                'camera_fps': round(camera.display_fps, 1),
                'ocr_fps': round(camera.ocr_fps, 1),
                'ocr': ocr_data,
                'auto_centering': camera.auto_centering,
            })
        except Exception:
            pass
        time.sleep(1)


# ═════════════════════════════════════════════════════════════════════════════
#  ANA PROGRAM
# ═════════════════════════════════════════════════════════════════════════════

def main():
    """
    Ana giriş noktası.
    1. Kamerayı başlat
    2. PNP motoruna bağlan
    3. OCR ve kamera thread'lerini başlat
    4. Flask web sunucusunu başlat
    """
    log.info("=" * 60)
    log.info("  PNP Web Kontrol Arayüzü Başlatılıyor")
    log.info("=" * 60)

    # 1. Kamerayı başlat
    camera.start()

    # 2. PNP motoruna bağlan
    try:
        pnp.connect()
    except Exception as e:
        log.warning(f"PNP bağlantısı kurulamadı: {e} — simülasyon modunda devam")

    # 3. Kamera thread'ini başlat
    cam_thread = threading.Thread(target=camera.camera_worker, daemon=True)
    cam_thread.start()

    # 4. OCR thread'ini başlat
    ocr_thread = threading.Thread(target=camera.ocr_worker, daemon=True)
    ocr_thread.start()

    # 5. Periyodik durum yayıncısı
    status_thread = threading.Thread(target=periodic_status_emitter, daemon=True)
    status_thread.start()

    # 6. Ağdaki IP adresini bul ve göster
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "0.0.0.0"

    # Daha güvenilir IP bulma
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    log.info("")
    log.info(f"  🌐  Web Arayüzü: http://{local_ip}:5000")
    log.info(f"  📱  Aynı ağdaki herhangi bir cihazdan erişebilirsiniz")
    log.info("")

    # 7. Flask sunucusunu başlat
    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        log.info("Kapatılıyor...")
    finally:
        camera.stop()
        pnp.close()
        log.info("Sistem kapatıldı.")


if __name__ == '__main__':
    main()
