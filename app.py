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
import base64
import threading
import logging
import functools
from io import BytesIO
from datetime import datetime

import cv2
import numpy as np
from PIL import Image
import difflib

# tesserocr — ana thread'de import edilmeli (signal handler kısıtı)
try:
    import tesserocr
    TESSEROCR_AVAILABLE = True
except ImportError:
    TESSEROCR_AVAILABLE = False
    logging.getLogger("PNP").warning("tesserocr bulunamadı — OCR devre dışı.")

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
logging.getLogger("werkzeug").setLevel(logging.WARNING)  # HTTP istek spam'ini engelle

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
    CAMERA_WIDTH = 1920
    CAMERA_HEIGHT = 1080

    # Yayın (Stream) için maksimum genişlik (Optimizasyon)
    STREAM_MAX_WIDTH = 800

    # Piksel → Milimetre dönüşüm katsayıları (kalibrasyon ile ayarlanır)
    PIXEL_TO_MM_X = 0.02
    PIXEL_TO_MM_Y = 0.02

    # Hedef nokta (ekran koordinatlarında, piksel cinsinden)
    TARGET_X = CAMERA_WIDTH // 2
    TARGET_Y = CAMERA_HEIGHT // 2

    # OCR parametreleri
    OCR_CONFIDENCE_THRESHOLD = 40
    STABILITY_DURATION = 0.1
    IOU_MATCH_THRESHOLD = 0.4
    OCR_PSM_MODE = 6          # 6=SINGLE_BLOCK, 11=SPARSE_TEXT, 3=AUTO
    OCR_WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # Motor hareket ayarları
    MOVE_STEP = 5.0
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

    # PIP Zoom Faktörü
    ZOOM_FACTOR = 2.0

    # OCR Minimum Kelime Uzunluğu (Bu değerden kısa kelimeler atlanır)
    OCR_MIN_WORD_LENGTH = 3

    # Kutu Büyüme Limiti (Ani sapıtma koruması — bu kattan fazla büyüyen kutular reddedilir)
    BOX_GROWTH_LIMIT = 1.5

    # Açılışta Otomatik Home
    AUTO_HOME = True


    # Motor hareket yönü ters çevirme (eski, geriye uyumluluk)
    INVERT_X = True
    INVERT_Y = False

    # ── KALİBRASYON: Eksen Eşleme ─────────────────
    # Kamera montaj açısına göre ekran↔motor ekseni dönüşümü
    # 180 Derece dönüşte genelde eksenler swap olmaz, sadece yönleri ters olabilir.
    SWAP_AXES = False            # 180 derece için False yapıldı
    NEGATE_SCREEN_X = True       # 180 derece için (Deneme yanılma gerekir)
    NEGATE_SCREEN_Y = True       # 180 derece için

    # Konfigürasyon dosya yolu
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    BASES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bases.json')
    SCENARIOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scenarios.json')
    MASTER_SCENARIOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'master_scenarios.json')
    VERIFICATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verification.json')
    BASES = []
    SCENARIOS = []
    MASTER_SCENARIOS = []
    VERIFICATION = {
        'boxes': [],
        'base_name': '',
        'threshold': 127
    }

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
            "ocr_confidence": self.OCR_CONFIDENCE_THRESHOLD,
            "ocr_psm_mode": self.OCR_PSM_MODE,
            "ocr_whitelist": self.OCR_WHITELIST,
            "zoom_factor": self.ZOOM_FACTOR,
            "ocr_min_word_length": self.OCR_MIN_WORD_LENGTH,
            "box_growth_limit": self.BOX_GROWTH_LIMIT,
            "auto_home": self.AUTO_HOME,
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
        if "ocr_confidence" in data: self.OCR_CONFIDENCE_THRESHOLD = int(data["ocr_confidence"])
        if "ocr_psm_mode" in data: self.OCR_PSM_MODE = int(data["ocr_psm_mode"])
        if "ocr_whitelist" in data: self.OCR_WHITELIST = str(data["ocr_whitelist"])
        if "zoom_factor" in data: self.ZOOM_FACTOR = float(data["zoom_factor"])
        if "ocr_min_word_length" in data: self.OCR_MIN_WORD_LENGTH = int(data["ocr_min_word_length"])
        if "box_growth_limit" in data: self.BOX_GROWTH_LIMIT = float(data["box_growth_limit"])
        if "auto_home" in data: self.AUTO_HOME = bool(data["auto_home"])
        
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

    def load_bases(self):
        """Bases dosyasını yükle (Robust)."""
        log.info(f"Bases yükleniyor: {self.BASES_FILE}")
        try:
            if os.path.exists(self.BASES_FILE):
                with open(self.BASES_FILE, 'r') as f:
                    content = f.read().strip()
                
                if content:
                    try:
                        self.BASES = json.loads(content)
                        log.info(f"{len(self.BASES)} adet konum yüklendi.")
                    except json.JSONDecodeError:
                        log.error("Bases JSON hatası! Yedekleniyor...")
                        try:
                            import shutil
                            shutil.copy(self.BASES_FILE, self.BASES_FILE + ".bak")
                        except: pass
                        self.BASES = []
                else:
                    self.BASES = []
                    log.warning("Bases dosyası boş.")
            else:
                self.BASES = []
                log.info("Bases dosyası bulunamadı, yeni oluşturulacak.")
        except Exception as e:
            log.error(f"Bases yükleme hatası: {e}")
            self.BASES = []

    def save_bases(self):
        """Bases dosyasını güvenli kaydet (Atomic Write)."""
        try:
            temp_file = self.BASES_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.BASES, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.BASES_FILE)
            log.info(f"Bases kaydedildi: {len(self.BASES)} adet")
        except Exception as e:
            log.error(f"Bases kayıt hatası: {e}")

    def load_scenarios(self):
        """Senaryoları dosyadan yükle."""
        try:
            if os.path.exists(self.SCENARIOS_FILE):
                with open(self.SCENARIOS_FILE, 'r') as f:
                    content = f.read().strip()
                if content:
                    try:
                        self.SCENARIOS = json.loads(content)
                        log.info(f"{len(self.SCENARIOS)} adet senaryo yüklendi.")
                    except json.JSONDecodeError:
                        log.error("Scenarios JSON hatası!")
                        self.SCENARIOS = []
                else:
                    self.SCENARIOS = []
            else:
                self.SCENARIOS = []
        except Exception as e:
            log.error(f"Senaryo yükleme hatası: {e}")
            self.SCENARIOS = []

    def save_scenarios(self):
        """Senaryoları güvenli kaydet."""
        try:
            temp_file = self.SCENARIOS_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.SCENARIOS, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.SCENARIOS_FILE)
            log.info(f"Senaryolar kaydedildi: {len(self.SCENARIOS)} adet")
        except Exception as e:
            log.error(f"Senaryo kayıt hatası: {e}")

    def load_master_scenarios(self):
        """Master Senaryoları dosyadan yükle."""
        try:
            if os.path.exists(self.MASTER_SCENARIOS_FILE):
                with open(self.MASTER_SCENARIOS_FILE, 'r') as f:
                    content = f.read().strip()
                if content:
                    try:
                        self.MASTER_SCENARIOS = json.loads(content)
                        log.info(f"{len(self.MASTER_SCENARIOS)} adet master senaryo yüklendi.")
                    except json.JSONDecodeError:
                        log.error("Master Scenarios JSON hatası!")
                        self.MASTER_SCENARIOS = []
                else:
                    self.MASTER_SCENARIOS = []
            else:
                self.MASTER_SCENARIOS = []
        except Exception as e:
            log.error(f"Master Senaryo yükleme hatası: {e}")
            self.MASTER_SCENARIOS = []

    def save_master_scenarios(self):
        """Master Senaryoları güvenli kaydet."""
        try:
            temp_file = self.MASTER_SCENARIOS_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.MASTER_SCENARIOS, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.MASTER_SCENARIOS_FILE)
            log.info(f"Master Senaryolar kaydedildi: {len(self.MASTER_SCENARIOS)} adet")
        except Exception as e:
            log.error(f"Master Senaryo kayıt hatası: {e}")

    def load_verification(self):
        """Doğrulama (Verification) ayarlarını yükle."""
        try:
            if os.path.exists(self.VERIFICATION_FILE):
                with open(self.VERIFICATION_FILE, 'r') as f:
                    content = f.read().strip()
                if content:
                    try:
                        data = json.loads(content)
                        self.VERIFICATION.update(data)
                        log.info(f"Doğrulama ayarları yüklendi. ({len(self.VERIFICATION.get('boxes', []))} kutu)")
                    except json.JSONDecodeError:
                        log.error("Verification JSON hatası!")
        except Exception as e:
            log.error(f"Verification yükleme hatası: {e}")

    def save_verification(self):
        """Doğrulama ayarlarını kaydet."""
        try:
            temp_file = self.VERIFICATION_FILE + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.VERIFICATION, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.VERIFICATION_FILE)
            log.info("Doğrulama ayarları kaydedildi.")
        except Exception as e:
            log.error(f"Verification kayıt hatası: {e}")


# Global config nesnesi
config = Config()
config.load_config()
config.load_bases()
config.load_scenarios()
config.load_master_scenarios()
config.load_verification()


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
        # Hareket tamamlandıktan sonra tekrar mutlak moda dön
        self.send("G90")
        
        # Konum güncelleme (tahmini)
        self.current_x += dx
        self.current_y += dy
        self.current_z += dz
        return True

    def move_absolute_z(self, z_mm, feed=None):
        """
        Mutlak Z hareketi (G90).
        Belirtilen Z koordinatına gider.
        """
        feed = feed or config.FEED_RATE
        self.send("G90")  # Mutlak mod
        cmd = f"G1 Z{z_mm:.3f} F{feed}"
        log.info(f"Z hareketi (mutlak): {cmd}")
        success = self.send(cmd)
        if success:
            self.current_z = z_mm
        return success

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
        self.raw_display_frame = None     # Temiz frame (doğrulama tab için)
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

            # RGB → Grayscale ve 180° döndür (Baş Aşağı)
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            gray_rotated = cv2.rotate(gray, cv2.ROTATE_180)

            # OCR için threshold
            blurred = cv2.GaussianBlur(gray_rotated, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 10
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

            if best_id is None:
                # ── Fallback Matching (Yedek Eşleştirme) ──
                # IoU tutmadı ama belki kutu çok büyüdü/küçüldü veya hafif kaydı.
                # Eğer aynı metin ve merkez noktası çok yakınsa, yine de eşleştir.
                for bid, sbox in self.stable_boxes.items():
                    # Aynı metin mi?
                    if sbox['text'] == det['text']:
                        # Merkezleri yakın mı? (Örn: 50px içinde)
                        ocx = sbox['rect'][0] + sbox['rect'][2]/2
                        ocy = sbox['rect'][1] + sbox['rect'][3]/2
                        ncx = det['rect'][0] + det['rect'][2]/2
                        ncy = det['rect'][1] + det['rect'][3]/2
                        dist = ((ocx-ncx)**2 + (ocy-ncy)**2)**0.5
                        
                        if dist < 50:
                            best_id = bid
                            break

            if best_id is not None:
                # Aniden 1.5x'ten fazla büyüyen kutuları reddet (sapıtma koruması)
                old_rect = self.stable_boxes[best_id]['rect']
                old_area = old_rect[2] * old_rect[3]
                new_area = det['rect'][2] * det['rect'][3]
                
                # Eğer çok büyüdüyse, sadece 'görüldü' bilgisini güncelle, koordinatları güncelleme
                if old_area > 0 and new_area > old_area * config.BOX_GROWTH_LIMIT:
                    self.stable_boxes[best_id]['last_seen'] = now
                else:
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
        if not TESSEROCR_AVAILABLE:
            log.warning("tesserocr bulunamadı — OCR devre dışı.")
            return

        # PSM ve whitelist'i config'den oku — değiştikçe API yeniden oluşturulur
        current_psm = config.OCR_PSM_MODE
        current_whitelist = config.OCR_WHITELIST

        def create_api(psm_mode, whitelist):
            """Tesseract API oluştur."""
            psm_map = {
                3: tesserocr.PSM.AUTO,
                6: tesserocr.PSM.SINGLE_BLOCK,
                11: tesserocr.PSM.SPARSE_TEXT,
            }
            psm = psm_map.get(psm_mode, tesserocr.PSM.SINGLE_BLOCK)
            _api = tesserocr.PyTessBaseAPI(
                path='/usr/share/tesseract-ocr/5/tessdata/',
                lang='eng',
                psm=psm,
                oem=tesserocr.OEM.LSTM_ONLY
            )
            _api.SetVariable("tessedit_do_invert", "0")
            if whitelist:
                _api.SetVariable("tessedit_char_whitelist", whitelist)
            return _api

        try:
            api = create_api(current_psm, current_whitelist)
        except Exception as e:
            log.error(f"Tesseract başlatılamadı: {e}")
            return

        log.info(f"OCR worker başlatıldı (PSM={current_psm}, Whitelist='{current_whitelist}').")

        while self.active:
            # Config değişikliği kontrolü — PSM veya whitelist değiştiyse API'yi yeniden oluştur
            if config.OCR_PSM_MODE != current_psm or config.OCR_WHITELIST != current_whitelist:
                current_psm = config.OCR_PSM_MODE
                current_whitelist = config.OCR_WHITELIST
                try:
                    api.End()
                    api = create_api(current_psm, current_whitelist)
                    log.info(f"OCR API yeniden oluşturuldu (PSM={current_psm}, Whitelist='{current_whitelist}')")
                except Exception as e:
                    log.error(f"OCR API yeniden oluşturma hatası: {e}")

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
                        # Minimum boyut filtresi (çok küçük gürültü)
                        if w_box < 5 or h_box < 5:
                            continue
                        # Maksimum boyut filtresi (frame alanının %25'inden büyükse sapıtma)
                        box_area = w_box * h_box
                        frame_area = img_w * img_h
                        if box_area > frame_area * 0.25:
                            continue

                        api.SetRectangle(x, y, w_box, h_box)
                        text = api.GetUTF8Text().strip()
                        conf = api.MeanTextConf()

                        if conf > config.OCR_CONFIDENCE_THRESHOLD and text and len(text) >= config.OCR_MIN_WORD_LENGTH:
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

            # Temiz frame'i kaydet (doğrulama tabı için — annotasyonsuz)
            with self.frame_lock:
                self.raw_display_frame = display.copy()

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

                # ── Yazı etiketi (sadece okunan yazı, boyut stream kalitesine göre sabit oran)
                font_scale = max(0.4, img_w / 800.0 * 0.6)
                thickness = max(1, int(img_w / 800.0 * 2))
                label = otext
                # Arkaplan kutusu (okunabilirlik için)
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                cv2.rectangle(display, (x, y - th - 6), (x + tw, y), (255, 255, 255), -1)
                
                cv2.putText(display, label, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), thickness)

            # ─── Hedef nokta crosshair (Grid / Profesyonel Görünüm) ──────────
            # Her zaman frame boyutundan dinamik hesapla
            tx = img_w // 2
            ty = img_h // 2
            
            # Renkler: Cyan (Turkuaz)
            color_main = (255, 255, 0)  # BGR
            color_sub = (100, 100, 0)   # Daha sönük
            gap = 25 # Merkez boşluğu
            
            # 1. Tam Ekran Kılavuz Çizgileri (Boşluklu)
            # Yatay Sol
            cv2.line(display, (0, ty), (tx - gap, ty), color_main, 1)
            # Yatay Sağ
            cv2.line(display, (tx + gap, ty), (img_w, ty), color_main, 1)
            # Dikey Üst
            cv2.line(display, (tx, 0), (tx, ty - gap), color_main, 1)
            # Dikey Alt
            cv2.line(display, (tx, ty + gap), (tx, img_h), color_main, 1)

            # 2. Eşmerkezli Daireler (Nişangah)
            for rad in [50, 100, 150, 200]:
                cv2.circle(display, (tx, ty), rad, color_sub, 1)

            # 3. Cetvel Çentikleri (Ticks) - Her 50px
            # Yatay Eksen Çentikleri
            for i in range(0, img_w, 50):
                if abs(i - tx) < gap: continue
                cv2.line(display, (i, ty - 5), (i, ty + 5), color_sub, 1)
            # Dikey Eksen Çentikleri
            for i in range(0, img_h, 50):
                if abs(i - ty) < gap: continue
                cv2.line(display, (tx - 5, i), (tx + 5, i), color_sub, 1)
            
            # 4. Merkez Nokta (Küçük kırmızı nokta, en ortada)
            cv2.circle(display, (tx, ty), 2, (0, 0, 255), -1)

            # ─── FPS bilgisi (Artık Client-side overlay'e taşındı, buraya yazmıyoruz) ────
            frame_count += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                self.display_fps = frame_count / elapsed
                frame_count = 0
                fps_start = time.time()

            # Auto-center durumu
            if self.auto_centering:
                text = "OTOMATIK-MERKEZLEME AKTIF"
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = 1.0
                thick = 3
                (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
                tx_start = (img_w - tw) // 2
                ty_start = 50
                cv2.rectangle(display, (tx_start - 10, ty_start - th - 10), (tx_start + tw + 10, ty_start + 10), (0,0,0), -1)
                cv2.putText(display, text, (tx_start, ty_start), font, scale, (0, 0, 255), thick) # Kırmızı

            # ─── PIP ZOOM (Sol Alt Köşe) ──────────
            if config.ZOOM_FACTOR > 1.0:
                try:
                    # Annotasyonlu frame'den (display) merkezden crop al
                    # Böylece OCR kutuları ve merkez noktaları PIP'te de görünür
                    fh, fw = display.shape[:2]
                    z_w = int(fw / config.ZOOM_FACTOR)
                    z_h = int(fh / config.ZOOM_FACTOR)
                    cx_f, cy_f = fw // 2, fh // 2
                    
                    x1 = max(0, cx_f - z_w // 2)
                    y1 = max(0, cy_f - z_h // 2)
                    x2 = min(fw, x1 + z_w)
                    y2 = min(fh, y1 + z_h)
                    
                    crop = display[y1:y2, x1:x2]
                    
                    # PIP Boyutu (Sabit - Daha Küçük)
                    pip_h_target = 150
                    pip_w_target = int(pip_h_target * (fw / fh))
                    
                    pip_resized = cv2.resize(crop, (pip_w_target, pip_h_target), interpolation=cv2.INTER_LINEAR)
                    
                    # Çerçeve çiz
                    cv2.rectangle(pip_resized, (0,0), (pip_w_target-1, pip_h_target-1), (255,165,0), 4) # Turuncu çerçeve
                    
                    # Merkez işareti (PIP içi - DAHA BELİRGİN)
                    pcx, pcy = pip_w_target//2, pip_h_target//2
                    # Siyah dış hat (kontrast için)
                    cv2.line(pip_resized, (pcx-15, pcy), (pcx+15, pcy), (0,0,0), 4)
                    cv2.line(pip_resized, (pcx, pcy-15), (pcx, pcy+15), (0,0,0), 4)
                    # Yeşil iç hat
                    cv2.line(pip_resized, (pcx-15, pcy), (pcx+15, pcy), (0,255,0), 2)
                    cv2.line(pip_resized, (pcx, pcy-15), (pcx, pcy+15), (0,255,0), 2)
                    
                    # PIP Overlay Konumu: Sol Alt
                    pos_y = img_h - pip_h_target - 10
                    pos_x = 10
                    
                    # Overlay işlemi
                    display[pos_y:pos_y+pip_h_target, pos_x:pos_x+pip_w_target] = pip_resized
                    
                    # Label
                    cv2.putText(display, f"ZOOM x{config.ZOOM_FACTOR:.1f}", (pos_x + 5, pos_y + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                                
                except Exception as e:
                    pass # PIP hatası akışı bozmasın

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

    def get_raw_mjpeg_frame(self):
        """Temiz (annotasyonsuz) frame'i JPEG olarak döndür."""
        with self.frame_lock:
            if self.raw_display_frame is None:
                return None
            _, jpeg = cv2.imencode('.jpg', self.raw_display_frame, [
                cv2.IMWRITE_JPEG_QUALITY, 80
            ])
            return jpeg.tobytes()

    def find_target_text(self, specific_word=None):
        """
        Hedef yazıları OCR sonuçlarından bul.
        Birden fazla eşleşme varsa ekran merkezine en yakın olanı döndürür.
        """
        target_exact = specific_word.strip() if specific_word else config.SELECTED_TARGET_WORD.strip()
        # Ekran merkezi (180 derece olduğu için en/boy değişmez)
        center_x = config.CAMERA_WIDTH // 2
        center_y = config.CAMERA_HEIGHT // 2

        candidates = []

        with self.ocr_lock:
            for item in self.ocr_results:
                txt = item['text']
                txt_lower = txt.lower()
                matched = False

                # 1. Öncelik: Seçili kelime
                if target_exact:
                    if target_exact == txt or target_exact in txt:
                        matched = True
                else:
                    # 2. Öncelik: Liste tarama
                    for word in config.TARGET_WORDS:
                        if word.lower() in txt_lower:
                            matched = True
                            break
                    # Geriye dönük uyumluluk
                    if not matched and config.TARGET_TEXT.lower() in txt_lower:
                        matched = True

                if matched:
                    cx, cy = item['center']
                    dist = ((cx - center_x) ** 2 + (cy - center_y) ** 2) ** 0.5
                    candidates.append((dist, item))

        if not candidates:
            return None

        # Merkeze en yakın olanı seç
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

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
    Profesyonel 4 aşamalı süreç:
      0. Başlangıç — Hedef arama (ekranda yoksa etrafı tarar)
      1. Kaba Merkezleme — Büyük adımlarla hızlı yaklaşma
      2. Hassas Merkezleme — Küçük adımlarla son düzeltme
      3. Son Kontrol — Doğrulama
    """
    camera.auto_centering = True
    camera.auto_center_status = "Başlatılıyor..."
    what_to_search = target_word if target_word else (config.SELECTED_TARGET_WORD if config.SELECTED_TARGET_WORD else config.TARGET_GROUP)

    def emit(status, message, phase=None):
        """Log + SocketIO ile kullanıcıya bildir."""
        prefix = f"[{phase}] " if phase else ""
        full_msg = prefix + message
        camera.auto_center_status = full_msg
        socketio.emit('auto_center_update', {'status': status, 'message': full_msg})
        log.info(f"Auto-Center: {full_msg}")

    try:
        # ─── TARAMA DESENLERİ ───
        scan_step = 0.5  # mm
        scan_pattern_small = [
            (scan_step, 0), (0, scan_step), (-scan_step, 0), (-scan_step, 0),
            (0, -scan_step), (0, -scan_step), (scan_step, 0), (scan_step, 0)
        ]
        scan_step_wide = 1.0
        scan_pattern_wide = [
            (scan_step_wide, 0), (0, scan_step_wide),
            (-scan_step_wide, 0), (-scan_step_wide, 0),
            (0, -scan_step_wide), (0, -scan_step_wide),
            (scan_step_wide, 0), (scan_step_wide, 0),
            (scan_step_wide, 0), (0, scan_step_wide), (0, scan_step_wide),
            (-scan_step_wide, 0), (-scan_step_wide, 0), (-scan_step_wide, 0),
            (0, -scan_step_wide), (0, -scan_step_wide),
        ]

        def search_target(scan_word, max_wait=3, scan_pattern=None):
            """Hedef yazıyı ara: önce bekle, bulamazsa tarama yap."""
            for wait_try in range(max_wait):
                time.sleep(0.8)
                t = camera.find_target_text(scan_word)
                if t is not None:
                    return t
                emit('moving', f"OCR taranıyor... ({wait_try+1}/{max_wait})")

            if scan_pattern is None:
                return None

            emit('moving', f"Hedef görünmüyor — etraf taranıyor ({len(scan_pattern)} adım)...")
            for si, (sdx, sdy) in enumerate(scan_pattern):
                motor_dx, motor_dy = screen_to_motor(sdx, sdy)
                pnp.move_relative(dx=motor_dx, dy=motor_dy)
                time.sleep(0.8)
                t = camera.find_target_text(scan_word)
                if t is not None:
                    emit('moving', f"Hedef bulundu! (tarama adım {si+1}/{len(scan_pattern)})")
                    return t
                if (si + 1) % 4 == 0:
                    emit('moving', f"Tarama devam ediyor... ({si+1}/{len(scan_pattern)})")
            return None

        # Merkez koordinatları (180 derece olduğu için en/boy değişmez)
        tx = config.CAMERA_WIDTH // 2
        ty = config.CAMERA_HEIGHT // 2

        # ══════════════════════════════════════════
        #  AŞAMA 0: BAŞLANGIÇ — HEDEF ARAMA
        # ══════════════════════════════════════════
        emit('started', f"'{what_to_search}' aranıyor...", phase="AŞAMA 0")
        time.sleep(0.5)
        target = camera.find_target_text(what_to_search)

        if target is None:
            emit('moving', f"'{what_to_search}' ekranda yok — geniş tarama başlatılıyor...", phase="AŞAMA 0")
            target = search_target(what_to_search, max_wait=2, scan_pattern=scan_pattern_wide)
            if target is None:
                emit('error', f"'{what_to_search}' hiçbir yerde bulunamadı!", phase="AŞAMA 0")
                return

        cx, cy = target['center']
        emit('moving', f"Hedef bulundu! Konum: ({cx},{cy}) — Merkezleme başlıyor.", phase="AŞAMA 0")
        time.sleep(0.5)

        # ══════════════════════════════════════════
        #  AŞAMA 1: KABA MERKEZLEME
        # ══════════════════════════════════════════
        emit('moving', "Kaba merkezleme başlıyor...", phase="AŞAMA 1")
        coarse_tolerance = config.AUTO_CENTER_TOLERANCE
        success_first_pass = False

        for iteration in range(config.AUTO_CENTER_MAX_ITER):
            time.sleep(0.5)
            target = camera.find_target_text(what_to_search)
            if target is None:
                emit('moving', f"Hedef kayıp — yeniden aranıyor (iterasyon {iteration+1})...", phase="AŞAMA 1")
                target = search_target(what_to_search, max_wait=3, scan_pattern=scan_pattern_small if iteration < 3 else None)
                if target is None:
                    emit('error', f"Hedef kayboldu ve bulunamadı! ({what_to_search})", phase="AŞAMA 1")
                    return

            cx, cy = target['center']
            dx_px = cx - tx
            dy_px = cy - ty
            dist_px = (dx_px**2 + dy_px**2) ** 0.5

            emit('moving', f"İterasyon {iteration+1}: Fark = {dist_px:.0f}px (dx={dx_px}, dy={dy_px})", phase="AŞAMA 1")

            if abs(dx_px) <= coarse_tolerance and abs(dy_px) <= coarse_tolerance:
                emit('moving', f"Kaba merkezleme tamamlandı ✓ (fark: {dist_px:.0f}px)", phase="AŞAMA 1")
                success_first_pass = True
                break

            screen_dx_mm = dx_px * config.PIXEL_TO_MM_X
            screen_dy_mm = dy_px * config.PIXEL_TO_MM_Y
            motor_dx, motor_dy = screen_to_motor(screen_dx_mm, screen_dy_mm)
            pnp.move_relative(dx=motor_dx, dy=motor_dy)
            emit('moving', "Stabilizasyon bekleniyor (1.5s)...", phase="AŞAMA 1")
            time.sleep(1.5)

        if not success_first_pass:
            emit('error', "Kaba merkezleme başarısız — maksimum iterasyon aşıldı.", phase="AŞAMA 1")
            return

        # ══════════════════════════════════════════
        #  GEÇİŞ BEKLEMESİ
        # ══════════════════════════════════════════
        emit('moving', "Hassas merkezlemeye geçiş — stabilizasyon (2s)...", phase="GEÇİŞ")
        time.sleep(2.0)

        # ══════════════════════════════════════════
        #  AŞAMA 2: HASSAS MERKEZLEME
        # ══════════════════════════════════════════
        if config.FINE_TUNE_ENABLED:
            emit('moving', "Hassas merkezleme başlıyor...", phase="AŞAMA 2")
            fine_tolerance = max(1, coarse_tolerance // 2)

            for i in range(5):
                time.sleep(0.5)
                target = camera.find_target_text(what_to_search)
                if not target:
                    emit('moving', "Hassas aşamada hedef kayıp — bekleniyor...", phase="AŞAMA 2")
                    target = search_target(what_to_search, max_wait=2, scan_pattern=None)
                    if not target:
                        emit('moving', "Hedef kaybedildi, mevcut konumla devam.", phase="AŞAMA 2")
                        break

                cx, cy = target['center']
                dx_px = cx - tx
                dy_px = cy - ty
                dist_px = (dx_px**2 + dy_px**2) ** 0.5

                emit('moving', f"Hassas düzeltme {i+1}: Fark = {dist_px:.1f}px", phase="AŞAMA 2")

                if abs(dx_px) <= fine_tolerance and abs(dy_px) <= fine_tolerance:
                    emit('moving', f"Hassas merkezleme tamamlandı ✓ (fark: {dist_px:.1f}px)", phase="AŞAMA 2")
                    break

                screen_dx_mm = dx_px * config.PIXEL_TO_MM_X
                screen_dy_mm = dy_px * config.PIXEL_TO_MM_Y

                if abs(screen_dx_mm) > config.FINE_TUNE_STEP_MM:
                    screen_dx_mm = config.FINE_TUNE_STEP_MM * (1 if screen_dx_mm > 0 else -1)
                if abs(screen_dy_mm) > config.FINE_TUNE_STEP_MM:
                    screen_dy_mm = config.FINE_TUNE_STEP_MM * (1 if screen_dy_mm > 0 else -1)

                motor_dx, motor_dy = screen_to_motor(screen_dx_mm, screen_dy_mm)
                pnp.move_relative(dx=motor_dx, dy=motor_dy)
                time.sleep(1.0)

        # ══════════════════════════════════════════
        #  AŞAMA 3: SON KONTROL
        # ══════════════════════════════════════════
        emit('moving', "Son kontrol yapılıyor...", phase="AŞAMA 3")
        time.sleep(1.0)
        target = camera.find_target_text(what_to_search)

        if target:
            cx, cy = target['center']
            dx_px = cx - tx
            dy_px = cy - ty
            dist_px = (dx_px**2 + dy_px**2) ** 0.5
            emit('done', f"MERKEZLENDİ ✓ — '{what_to_search}' fark: {dist_px:.1f}px", phase="TAMAMLANDI")
        else:
            emit('done', "Merkezleme tamamlandı — son doğrulama yapılamadı.", phase="TAMAMLANDI")

    except Exception as e:
        msg = f"Auto-center hatası: {e}"
        camera.auto_center_status = msg
        socketio.emit('auto_center_update', {'status': 'error', 'message': msg})
        log.error(msg)

    finally:
        camera.auto_centering = False

# ═════════════════════════════════════════════════════════════════════════════
#  GÖRÜNTÜ İŞLEME İLE DOĞRULUK KONTROLÜ (VERIFICATION)
# ═════════════════════════════════════════════════════════════════════════════
verification_running = False

def run_verification(camera_ref, pnp_ref, socketio_ref):
    """
    Belirtilen konuma gidip kamera üzerinden Binary Threshold ile 
    tanımlı ROI kutularındaki siyah piksel doluluk oranını hesaplar.
    Her kutu için threshold görüntüsünü base64 olarak frontend'e gönderir.
    """
    global verification_running
    verification_running = True
    results = []

    def emit(status, message, data=None):
        payload = {'status': status, 'message': message}
        if data is not None:
            payload['data'] = data
        socketio_ref.emit('verification_update', payload)
        log.info(f"Verification: {message}")

    try:
        emit('running', "Doğrulama başlatılıyor...")

        v_config = config.VERIFICATION
        base_name = v_config.get('base_name', '')
        boxes = v_config.get('boxes', [])
        threshold_val = int(v_config.get('threshold', 127))

        if not boxes:
            emit('error', "Doğrulama için tanımlı kutu bulunamadı!")
            return

        # 1. Kayıtlı konuma git
        if base_name:
            target = next((b for b in config.BASES if b['name'] == base_name), None)
            if target:
                emit('running', f"'{base_name}' konumuna gidiliyor...")
                current_z = pnp_ref.current_z
                target_z = target['z']
                if target_z < current_z:
                    pnp_ref.move_absolute(x=target['x'], y=target['y'])
                    pnp_ref.move_absolute(z=target_z)
                else:
                    pnp_ref.move_absolute(z=target_z)
                    pnp_ref.move_absolute(x=target['x'], y=target['y'])
                time.sleep(1.0)
            else:
                emit('warning', f"Doğrulama konumu '{base_name}' bulunamadı. Mevcut konumda devam ediliyor.")
        else:
            emit('info', "Doğrulama konumu seçilmemiş. Mevcut konumda devam ediliyor.")

        emit('running', "Görüntü stabilize ediliyor...")
        time.sleep(1.0)

        for _ in range(5):
            time.sleep(0.1)

        with camera_ref.frame_lock:
            if camera_ref.current_gray is None:
                emit('error', "Kameradan görüntü alınamıyor!")
                return
            frame_gray = camera_ref.current_gray.copy()

        # 2. Binary Threshold uygula
        blurred = cv2.GaussianBlur(frame_gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, threshold_val, 255, cv2.THRESH_BINARY)

        # Tam kare threshold görüntüsünü küçültüp base64 olarak gönder
        h_full, w_full = thresh.shape[:2]
        scale = min(400 / w_full, 300 / h_full)
        small_thresh = cv2.resize(thresh, (int(w_full * scale), int(h_full * scale)))
        _, buf_full = cv2.imencode('.jpg', small_thresh, [cv2.IMWRITE_JPEG_QUALITY, 70])
        full_b64 = base64.b64encode(buf_full).decode('utf-8')
        emit('threshold_frame', "Threshold görüntüsü hazır.", data={'image': full_b64})

        # 3. ROI'leri analiz et
        img_h, img_w = thresh.shape[:2]

        for i, box in enumerate(boxes):
            bx = int(box.get('x', 0) * img_w)
            by = int(box.get('y', 0) * img_h)
            bw = int(box.get('w', 0.1) * img_w)
            bh = int(box.get('h', 0.1) * img_h)
            name = box.get('name', 'Bilinmeyen')
            target_ratio = float(box.get('target_ratio', 10.0))

            x1 = max(0, bx)
            y1 = max(0, by)
            x2 = min(img_w, bx + bw)
            y2 = min(img_h, by + bh)

            if x2 <= x1 or y2 <= y1:
                results.append({'id': box.get('id'), 'name': name, 'ratio': 0.0, 'success': False, 'target': target_ratio, 'roi_image': ''})
                continue

            roi_thresh = thresh[y1:y2, x1:x2]

            # Siyah piksel oranı (threshold sonrası siyah = 0 olan pikseller)
            total_pixels = roi_thresh.size
            black_pixels = total_pixels - cv2.countNonZero(roi_thresh)

            if total_pixels > 0:
                fill_ratio = (black_pixels / total_pixels) * 100.0
            else:
                fill_ratio = 0.0

            success = fill_ratio >= target_ratio

            # ROI threshold görüntüsünü base64 olarak gönder
            roi_resized = cv2.resize(roi_thresh, (120, 90))
            _, buf_roi = cv2.imencode('.jpg', roi_resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
            roi_b64 = base64.b64encode(buf_roi).decode('utf-8')

            emit('box_progress', f"Kutu {i+1}/{len(boxes)}: {name} → %{fill_ratio:.1f}", data={
                'box_index': i, 'name': name, 'ratio': round(fill_ratio, 2),
                'success': success, 'target': target_ratio, 'roi_image': roi_b64
            })
            time.sleep(0.3)  # Her kutu arası kısa bekleme (animasyon efekti)

            results.append({
                'id': box.get('id'),
                'name': name,
                'ratio': round(fill_ratio, 2),
                'success': success,
                'target': target_ratio,
                'roi_image': roi_b64
            })

        emit('done', "Doğrulama tamamlandı.", data=results)

    except Exception as e:
        emit('error', f"Doğrulama hatası: {e}")
        log.error(f"Doğrulama işlemi iptal edildi: {e}")

    finally:
        verification_running = False

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
    """Oturum doğrulama DEVRE DIŞI — herkes erişebilir."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # if not session.get('logged_in'):
        #     ...
        return f(*args, **kwargs)
    return decorated


# ─── Sayfalar ────────────────────────────────────────────────────────────────

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     ... (devre dışı)
#     return redirect(url_for('index'))

@app.route('/login')
def login():
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    return redirect(url_for('index'))


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


def generate_mjpeg_raw():
    """Temiz (annotasyonsuz) MJPEG stream generator."""
    while True:
        frame = camera.get_raw_mjpeg_frame()
        if frame is not None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )
        else:
            time.sleep(0.05)


@app.route('/video_feed_raw')
@login_required
def video_feed_raw():
    """Temiz kamera görüntüsü (crosshair/PIP/OCR yok) — doğrulama tab için."""
    return Response(
        generate_mjpeg_raw(),
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

@app.route('/api/move_z_absolute', methods=['POST'])
@login_required
def api_move_z_absolute():
    """Mutlak Z hareketi."""
    data = request.get_json()
    z = float(data.get('z', -163))
    success = pnp.move_absolute_z(z_mm=z)
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


@app.route('/api/bases', methods=['GET', 'POST'])
def api_bases():
    """Kayıtlı konumları listele veya yeni ekle."""
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': True, 'bases': config.BASES})
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'İsim gerekli'})
        
        # Aynı isimde varsa güncelle, yoksa ekle
        entry = {
            'name': name,
            'x': float(data.get('x', 0)),
            'y': float(data.get('y', 0)),
            'z': float(data.get('z', 0))
        }
        
        # İsim kontrolü
        exists = False
        for i, b in enumerate(config.BASES):
            if b['name'] == name:
                config.BASES[i] = entry
                exists = True
                break
        if not exists:
            config.BASES.append(entry)
            
        config.save_bases()
        return jsonify({'success': True, 'message': 'Konum kaydedildi', 'bases': config.BASES})
        
    return jsonify({'success': True, 'bases': config.BASES})

@app.route('/api/bases/<name>', methods=['DELETE'])
def api_delete_base(name):
    """Kayıtlı konumu sil."""
    original_len = len(config.BASES)
    config.BASES = [b for b in config.BASES if b['name'] != name]
    if len(config.BASES) < original_len:
        config.save_bases()
        return jsonify({'success': True, 'message': 'Konum silindi', 'bases': config.BASES})
    return jsonify({'success': False, 'message': 'Konum bulunamadı'})

@app.route('/api/goto_base', methods=['POST'])
def api_goto_base():
    """Kayıtlı konuma git (Akıllı Z sıralaması)."""
    data = request.get_json()
    name = data.get('name')
    target = next((b for b in config.BASES if b['name'] == name), None)
    
    if target:
        current_z = pnp.current_z  # Mevcut Z pozisyonu
        target_z = target['z']
        
        if target_z < current_z:
            # Z aşağı gidecek → çarpışma riski: önce XY, sonra Z indir
            log.info(f"Goto '{name}': Z aşağı ({current_z:.2f} → {target_z:.2f}), sıra: XY → Z")
            pnp.move_absolute(x=target['x'], y=target['y'])
            success = pnp.move_absolute(z=target_z)
            order_msg = "XY → Z"
        else:
            # Z yukarı gidecek veya aynı → güvenli: önce Z yukarı, sonra XY
            log.info(f"Goto '{name}': Z yukarı ({current_z:.2f} → {target_z:.2f}), sıra: Z → XY")
            pnp.move_absolute(z=target_z)
            success = pnp.move_absolute(x=target['x'], y=target['y'])
            order_msg = "Z → XY"
        
        socketio.emit('motor_update', pnp.get_status())
        return jsonify({'success': success, 'message': f"'{name}' konumuna varıldı ({order_msg})."})
    
    return jsonify({'success': False, 'message': 'Konum bulunamadı'})


# ── Senaryo Çalıştırma Altyapısı ─────────────────────────────────────────────
scenario_running = False
scenario_stop_flag = False

def run_scenario(scenario, pnp_ref, camera_ref, socketio_ref):
    """Senaryoyu arka planda adım adım çalıştır."""
    global scenario_running, scenario_stop_flag
    scenario_running = True
    scenario_stop_flag = False
    name = scenario.get('name', 'İsimsiz')
    steps = scenario.get('steps', [])

    def emit(status, message, step_index=-1):
        socketio_ref.emit('scenario_update', {
            'status': status,
            'message': message,
            'step_index': step_index,
            'total_steps': len(steps),
            'step_type': steps[step_index]['type'] if 0 <= step_index < len(steps) else None,
            'scenario_name': name
        })

    try:
        emit('started', f"Senaryo '{name}' başlatıldı ({len(steps)} adım)")
        log.info(f"Senaryo başlatıldı: {name} ({len(steps)} adım)")

        for i, step in enumerate(steps):
            if scenario_stop_flag:
                emit('stopped', f"Senaryo durduruldu (adım {i+1}/{len(steps)}).")
                log.info(f"Senaryo durduruldu: {name}")
                return

            stype = step.get('type')
            emit('running', f"Adım {i+1}/{len(steps)}: {_step_description(step)}", i)

            if stype == 'goto_base':
                base_name = step.get('base_name', '')
                target = next((b for b in config.BASES if b['name'] == base_name), None)
                if target:
                    current_z = pnp_ref.current_z
                    target_z = target['z']
                    if target_z < current_z:
                        pnp_ref.move_absolute(x=target['x'], y=target['y'])
                        pnp_ref.move_absolute(z=target_z)
                    else:
                        pnp_ref.move_absolute(z=target_z)
                        pnp_ref.move_absolute(x=target['x'], y=target['y'])
                    socketio_ref.emit('motor_update', pnp_ref.get_status())
                else:
                    emit('warning', f"Konum bulunamadı: {base_name}", i)

            elif stype == 'auto_center':
                word = step.get('word', '')
                if word:
                    emit('running', f"'{word}' kelimesine merkezleniyor...", i)
                    auto_center(camera_ref, pnp_ref, socketio_ref, word)
                else:
                    emit('warning', "Merkezleme kelimesi boş!", i)

            elif stype == 'pump_on':
                pnp_ref.pump(True)
                emit('running', "Pompa açıldı.", i)

            elif stype == 'pump_off':
                pnp_ref.pump(False)
                emit('running', "Pompa kapatıldı.", i)

            elif stype == 'delay':
                secs = float(step.get('seconds', 1))
                emit('running', f"{secs}s bekleniyor...", i)
                # Bekleme sırasında durdurma kontrolü
                waited = 0
                while waited < secs:
                    if scenario_stop_flag:
                        emit('stopped', "Senaryo durduruldu (bekleme sırasında).")
                        return
                    time.sleep(min(0.5, secs - waited))
                    waited += 0.5

            elif stype == 'home':
                pnp_ref.home()
                emit('running', "Home'a gidildi.", i)
                time.sleep(0.5)
                socketio_ref.emit('motor_update', pnp_ref.get_status())

            elif stype == 'move_z':
                z_val = float(step.get('z', 0))
                emit('running', f"Z ekseni {z_val}mm konumuna gidiliyor...", i)
                pnp_ref.move_absolute(z=z_val)
                socketio_ref.emit('motor_update', pnp_ref.get_status())

            elif stype == 'verify':
                emit('running', "👁️ Doğruluk Kontrolü yapılıyor...", i)
                if verification_running:
                    emit('warning', "Doğrulama zaten devam ediyor, atlandı.", i)
                else:
                    run_verification(camera_ref, pnp_ref, socketio_ref)
                    # wait for verification to finish
                    while verification_running and not scenario_stop_flag:
                        time.sleep(0.5)
                        
                    if scenario_stop_flag:
                        emit('stopped', "Senaryo durduruldu (doğrulama sırasında).")
                        return

            else:
                emit('warning', f"Bilinmeyen komut tipi: {stype}", i)

            time.sleep(0.3)  # Adımlar arası kısa mola

        emit('done', f"Senaryo '{name}' tamamlandı ✓")
        log.info(f"Senaryo tamamlandı: {name}")

    except Exception as e:
        emit('error', f"Senaryo hatası: {e}")
        log.error(f"Senaryo hatası ({name}): {e}")
    finally:
        scenario_running = False


def _step_description(step):
    """Adım için okunabilir açıklama döndür."""
    t = step.get('type', '?')
    if t == 'goto_base': return f"📍 {step.get('base_name', '?')} konumuna git"
    if t == 'auto_center': return f"🎯 '{step.get('word', '?')}' kelimesine merkezle"
    if t == 'pump_on': return "💨 Pompa AÇ"
    if t == 'pump_off': return "🛑 Pompa KAPAT"
    if t == 'delay': return f"⏳ {step.get('seconds', 1)}s bekle"
    if t == 'move_z': return f"↕️ Z: {step.get('z', 0)}mm konumuna git"
    if t == 'home': return "🏠 Home pozisyonuna git"
    if t == 'verify': return "👁️ Doğruluk Kontrolü yap"
    return f"❓ {t}"


@app.route('/api/scenarios', methods=['GET', 'POST'])
def api_scenarios():
    """Senaryoları listele veya yeni ekle/güncelle."""
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': True, 'scenarios': config.SCENARIOS})
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Senaryo adı gerekli'})
        steps = data.get('steps', [])
        entry = {'name': name, 'steps': steps}

        # Aynı isimde varsa güncelle
        exists = False
        for i, s in enumerate(config.SCENARIOS):
            if s['name'] == name:
                config.SCENARIOS[i] = entry
                exists = True
                break
        if not exists:
            config.SCENARIOS.append(entry)

        config.save_scenarios()
        return jsonify({'success': True, 'message': 'Senaryo kaydedildi', 'scenarios': config.SCENARIOS})

    return jsonify({'success': True, 'scenarios': config.SCENARIOS})


@app.route('/api/scenarios/<name>', methods=['DELETE'])
def api_delete_scenario(name):
    """Senaryoyu sil."""
    original_len = len(config.SCENARIOS)
    config.SCENARIOS = [s for s in config.SCENARIOS if s['name'] != name]
    if len(config.SCENARIOS) < original_len:
        config.save_scenarios()
        return jsonify({'success': True, 'message': 'Senaryo silindi', 'scenarios': config.SCENARIOS})
    return jsonify({'success': False, 'message': 'Senaryo bulunamadı'})


@app.route('/api/scenario/run', methods=['POST'])
def api_run_scenario():
    """Senaryoyu arka planda çalıştır."""
    global scenario_running
    if scenario_running:
        return jsonify({'success': False, 'message': 'Bir senaryo zaten çalışıyor!'})

    data = request.get_json()
    name = data.get('name')
    scenario = next((s for s in config.SCENARIOS if s['name'] == name), None)
    if not scenario:
        return jsonify({'success': False, 'message': 'Senaryo bulunamadı'})

    threading.Thread(
        target=run_scenario,
        args=(scenario, pnp, camera, socketio),
        daemon=True
    ).start()
    return jsonify({'success': True, 'message': f"Senaryo '{name}' başlatıldı"})


@app.route('/api/master_scenarios', methods=['GET', 'POST'])
def api_master_scenarios():
    """Master Senaryoları listele veya yeni ekle/güncelle."""
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': True, 'master_scenarios': config.MASTER_SCENARIOS})
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Master Senaryo adı gerekli'})
        
        # 'sequence' is a list of scenario names
        sequence = data.get('sequence', [])
        entry = {'name': name, 'sequence': sequence}

        exists = False
        for i, ms in enumerate(config.MASTER_SCENARIOS):
            if ms['name'] == name:
                config.MASTER_SCENARIOS[i] = entry
                exists = True
                break
        if not exists:
            config.MASTER_SCENARIOS.append(entry)

        config.save_master_scenarios()
        return jsonify({'success': True, 'message': 'Master Senaryo kaydedildi', 'master_scenarios': config.MASTER_SCENARIOS})

    return jsonify({'success': True, 'master_scenarios': config.MASTER_SCENARIOS})

@app.route('/api/master_scenarios/<name>', methods=['DELETE'])
def api_delete_master_scenario(name):
    """Master Senaryoyu sil."""
    original_len = len(config.MASTER_SCENARIOS)
    config.MASTER_SCENARIOS = [ms for ms in config.MASTER_SCENARIOS if ms['name'] != name]
    if len(config.MASTER_SCENARIOS) < original_len:
        config.save_master_scenarios()
        return jsonify({'success': True, 'message': 'Master Senaryo silindi', 'master_scenarios': config.MASTER_SCENARIOS})
    return jsonify({'success': False, 'message': 'Master Senaryo bulunamadı'})

@app.route('/api/master_scenario/run', methods=['POST'])
def api_run_master_scenario():
    """Master senaryoyu (alt senaryoların birleşimi) çalıştır."""
    global scenario_running
    if scenario_running:
        return jsonify({'success': False, 'message': 'Bir senaryo zaten çalışıyor!'})

    data = request.get_json()
    name = data.get('name')
    
    ms = next((m for m in config.MASTER_SCENARIOS if m['name'] == name), None)
    if not ms:
        return jsonify({'success': False, 'message': 'Master Senaryo bulunamadı'})
        
    # Virtual scenario composed of sub-scenario steps
    virtual_steps = []
    for s_name in ms.get('sequence', []):
        sub = next((s for s in config.SCENARIOS if s['name'] == s_name), None)
        if sub:
            virtual_steps.extend(sub.get('steps', []))
        else:
            log.warning(f"Master Senaryo '{name}' içinde alt senaryo bulunamadı: '{s_name}'")
            
    virtual_scenario = {
        'name': f"[M] {name}",
        'steps': virtual_steps
    }

    threading.Thread(
        target=run_scenario,
        args=(virtual_scenario, pnp, camera, socketio),
        daemon=True
    ).start()
    return jsonify({'success': True, 'message': f"Master Senaryo '{name}' başlatıldı"})


@app.route('/api/scenario/stop', methods=['POST'])
def api_scenario_stop():
    """Çalışan senaryoyu durdur."""
    global scenario_stop_flag
    if not scenario_running:
        return jsonify({'success': False, 'message': 'Çalışan senaryo yok'})
    scenario_stop_flag = True
    return jsonify({'success': True, 'message': 'Durdurma sinyali gönderildi'})


@app.route('/api/verification/settings', methods=['GET', 'POST'])
def api_verification_settings():
    """Doğrulama ayarlarını getir veya güncelle."""
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Boş data'})
            
        config.VERIFICATION.update(data)
        config.save_verification()
        return jsonify({'success': True, 'message': 'Doğrulama ayarları kaydedildi', 'verification': config.VERIFICATION})

    return jsonify({'success': True, 'verification': config.VERIFICATION})


@app.route('/api/verification/run', methods=['POST'])
def api_verification_run():
    """Doğrulama işlemini manuel tetikle."""
    global verification_running
    if verification_running:
        return jsonify({'success': False, 'message': 'Doğrulama zaten çalışıyor!'})

    threading.Thread(
        target=run_verification,
        args=(camera, pnp, socketio),
        daemon=True
    ).start()
    return jsonify({'success': True, 'message': 'Doğrulama başlatıldı'})


@app.route('/api/config', methods=['POST'])
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
    config.TARGET_X = new_w // 2
    config.TARGET_Y = new_h // 2

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


@app.route('/api/shutdown', methods=['POST'])
@login_required
def api_shutdown():
    """Sunucuyu kapat — Python prosesini sonlandır."""
    log.warning("🔌 SUNUCU KAPATILIYOR — Kullanıcı isteği ile...")
    socketio.emit('log_message', {
        'message': '🔌 Sunucu kapatılıyor...',
        'level': 'WARNING',
        'timestamp': time.strftime('%H:%M:%S')
    })

    def shutdown_server():
        """Kamerayı ve PNP'yi kapat, ardından process'i sonlandır."""
        time.sleep(1)  # Client'a yanıt göndermek için kısa bekle
        try:
            camera.stop()
        except Exception:
            pass
        try:
            pnp.close()
        except Exception:
            pass
        log.info("Sistem kapatıldı. Güle güle!")
        os._exit(0)

    threading.Thread(target=shutdown_server, daemon=True).start()
    return jsonify({'success': True, 'message': 'Sunucu kapatılıyor...'})


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
        if pnp.connected and config.AUTO_HOME:
            log.info("Otomatik Home başlatılıyor...")
            try:
                pnp.home()
                log.info("Otomatik Home tamamlandı.")
            except Exception as he:
                log.warning(f"Otomatik Home hatası: {he}")
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
