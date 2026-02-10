#!/usr/bin/env python3
"""
Ana Kontrol Dosyası

Bu dosya:
1. PNP (Pick and Place) makinesini kontrol eder (portu otomatik bulur).
2. Kamera OCR sistemini çalıştırır.
3. Önceden belirlenen senaryoyu uygular.

Kullanım:
    python main.py
"""
import sys
import time
import threading
import serial
import serial.tools.list_ports
import glob
import os

# Çıktıları anında gör
os.environ["PYTHONUNBUFFERED"] = "1"

# Kamera modülü (aynı klasörde olmalı: camera_ocr.py)
try:
    import camera_ocr
except ImportError:
    print("HATA: 'camera_ocr.py' dosyası bulunamadı!", flush=True)
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# 1. PNP SÜRÜCÜSÜ (Basitleştirilmiş)
# ═══════════════════════════════════════════════════════════════

class PNPDriver:
    def __init__(self, port=None):
        self.port = port or self.find_port()
        self.ser = None
        if not self.port:
            raise Exception("PNP Portu bulunamadı!")
        
        self.connect()

    def find_port(self):
        """Otomatik port bulma."""
        ports = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
        if not ports: return None
        print(f"[PNP] Taranıyor: {', '.join(ports)}", flush=True)

        for p in ports:
            try:
                s = serial.Serial(p, 115200, timeout=2)
                s.dtr = False; time.sleep(0.5); s.flushInput(); s.dtr = True; time.sleep(3)
                
                # GRBL yanıtını bekle
                resp = ""
                t_start = time.time()
                while time.time() - t_start < 2:
                    if s.in_waiting:
                        resp += s.read(s.in_waiting).decode('utf-8', errors='ignore')
                    time.sleep(0.1)
                
                s.close()
                if 'grbl' in resp.lower(): return p
            except: continue
            
        # Eğer hiç GRBL bulamazsa ama port varsa ilkini döndür (riskli ama pratik)
        return ports[0]

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=2)
            print(f"[PNP] Bağlanıldı: {self.port}", flush=True)
            
            self.ser.dtr = False; time.sleep(1); self.ser.flushInput(); self.ser.dtr = True
            time.sleep(2) # Uyanma
            self.ser.flushInput()
            
            self.send("$X") # Kilidi aç toparlan
            self.send("G21") # Milimetre
            self.send("G90") # Absolute
            self.send("G94") # Feed rate
            
        except Exception as e:
            print(f"[PNP BAĞLANTI HATASI] {e}", flush=True)
            raise

    def send(self, cmd, timeout=30):
        """Komut gönder ve 'ok' bekle."""
        if not self.ser: return False
        
        full_cmd = cmd.strip() + '\r\n'
        self.ser.write(full_cmd.encode())
        
        start = time.time()
        while True:
            if self.ser.in_waiting:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line == 'ok': return True
                if 'error' in line.lower(): 
                    print(f"[HATA] {cmd} -> {line}", flush=True)
                    return False
            
            if time.time() - start > timeout:
                print(f"[TIMEOUT] {cmd}", flush=True)
                return False
            time.sleep(0.01)

    def move(self, x=None, y=None, z=None, f=None):
        """Hareket (G0 hızıyla)."""
        cmd = "G0"
        if x is not None: cmd += f" X{x:.2f}"
        if y is not None: cmd += f" Y{y:.2f}"
        if z is not None: cmd += f" Z{z:.2f}"
        
        print(f"[HAREKET] {cmd}", flush=True)
        self.send(cmd)
        self.send("G4 P0") # Hareketin bitmesini bekle (Sync)

    def pump(self, state):
        cmd = "M8" if state else "M9"
        print(f"[POMPA] {'AÇIK' if state else 'KAPALI'}", flush=True)
        self.send(cmd)
        self.send("G4 P0")  # Buffer'ı boşalt, komutun uygulanmasını garanti et
        if not state:
            # Kapama durumunda ekstra güvenlik: tekrar gönder
            time.sleep(0.5)
            self.send("M9")
            self.send("G4 P0")

    def wait(self, seconds):
        """GRBL üzerinde bekleme (G4 komutu)."""
        print(f"[BEKLEME] {seconds}sn", flush=True)
        self.send(f"G4 P{seconds}")

    def home(self):
        print("[PNP] Home yapılıyor ($H)...", flush=True)
        if self.send("$H", timeout=60):
            print("[PNP] Home tamam.", flush=True)
            self.send("G92 X0 Y0 Z0") # Home sonrası koordinatları sıfırla
            time.sleep(1)
        else:
            print("[PNP] Home hatası!", flush=True)

    def close(self):
        if self.ser: 
            self.ser.close()
            print("[PNP] Bağlantı kapatıldı.", flush=True)


# ═══════════════════════════════════════════════════════════════
# 2. SENARYO (G-Code Mantığı)
# ═══════════════════════════════════════════════════════════════

def run_scenario_thread():
    """Arka planda çalışacak PNP senaryosu."""
    pnp = None
    try:
        print("[SİSTEM] PNP Başlatılıyor...", flush=True)
        pnp = PNPDriver()
        
        # --- BAŞLANGIÇ ---
        pnp.home()

        # --- BÖLÜM 1: AL ---
        print("\n=== BÖLÜM 1: AL VE GÖTÜR ===", flush=True)

        pnp.move(x=1.7, y=-25)      # Konumlan

        pnp.move(z=-165.7)          # Tam in
        pnp.pump(True)              # TUT
        pnp.wait(1)
        
        pnp.move(z=-150)            # Kaldır
        
        # Test hareketi (istenirse kaldırılabilir)
        pnp.move(x=1.7, y=-10.8)
        pnp.move(z=-171.5)
        pnp.wait(5)
        pnp.move(z=-150)

        # Hedefe git
        pnp.move(x=46.7, y=-46.5)
        pnp.move(z=-171)

        pnp.send("G4 P1")           # 1sn bekle

        pnp.pump(False)             # BIRAK

        pnp.wait(2)

        # Güvenlik Home
        print("[GÜVENLİK] Ara Home...", flush=True)
        pnp.home()

        # Pompa güvenlik kapama
        pnp.pump(False)

        print("[SİSTEM] Senaryo Başarıyla Tamamlandı.", flush=True)

    except Exception as e:
        print(f"[PNP HATA] {e}", flush=True)
    finally:
        if pnp: 
            try:
                print("[SİSTEM] Temizlik yapılıyor...", flush=True)
                pnp.send("M9") # Pompayı zorla kapat
            except: pass
            pnp.close()


# ═══════════════════════════════════════════════════════════════
# 3. ANA PROGRAM
# ═══════════════════════════════════════════════════════════════

def main():
    print("=== SİSTEM BAŞLATILIYOR (PNP + KAMERA) ===", flush=True)
    
    # 1. PNP Thread'i başlat (Daemon = program kapanınca bu da kapansın)
    t = threading.Thread(target=run_scenario_thread, daemon=True)
    t.start()
    
    # 2. Kamerayı ana thread'de çalıştır
    try:
        camera_ocr.main()
    except KeyboardInterrupt:
        print("\n[ÇIKIŞ] Kapatılıyor...", flush=True)
    except Exception as e:
        print(f"\n[HATA] Kamera hatası: {e}", flush=True)

if __name__ == "__main__":
    main()
