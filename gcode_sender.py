import serial
import time

class CNCDriver:
    # Hız ayarları (mm/dakika)
    DEFAULT_SPEED_XY = 500
    DEFAULT_SPEED_Z = 300

    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.connect()

    def connect(self):
        try:
            # Linux için resetlemeyi önleyen parametreler (dsrdtr)
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"[BAĞLANTI] {self.port} portuna bağlanıldı.")
            
            # GRBL Uyandırma Prosedürü
            self.ser.dtr = False
            time.sleep(1)
            self.ser.flushInput()
            self.ser.dtr = True
            
            print("[SİSTEM] GRBL uyanıyor (2 sn)...")
            time.sleep(2)
            self.ser.flushInput() # Buffer temizliği
            
            # Başlangıç Ayarları
            self.send_command("$X")             # Alarm Unlock
            self.send_command("G21")            # Millimeters
            self.send_command("G90")            # Absolute Positioning
            self.send_command("G92 X0 Y0 Z0")   # Mevcut konumu 'Ev' (0,0,0) kabul et
            print("[HAZIR] Makine komut bekliyor.")
            
        except Exception as e:
            print(f"[HATA] Bağlantı sorunu: {e}")
            exit()

    def send_command(self, gcode):
        """
        Komutu gönderir ve 'ok' cevabını bekler (Bloklayıcı).
        Busy-wait yerine blocking read kullanılarak CPU kullanımı düşürüldü.
        """
        if not self.ser: return

        # GRBL standartlarına uygun format (Satır sonu \r\n)
        cmd_str = gcode.strip() + '\r\n'
        
        self.ser.write(cmd_str.encode('utf-8'))

        start_time = time.time()
        while True:
            # timeout=1 olduğu için readline 1 saniye bekler, CPU yormaz
            response = self.ser.readline().decode('utf-8', errors='ignore').strip()
            
            if response == 'ok':
                return True
            elif 'error' in response:
                print(f"[GRBL HATA] Komut: {gcode} -> Yanıt: {response}")
                return False
            
            # 30 saniye güvenlik zaman aşımı (uzun hareketler için)
            if time.time() - start_time > 30:
                print("[TIMEOUT] GRBL cevap vermedi.")
                return False

    def move(self, x=None, y=None, z=None, speed=None):
        """
        X, Y, Z eksenlerini hareket ettirir.
        Hız belirtilmezse, Z hareketi için 300, normal hareket için 1000 varsayılır.
        """
        parts = ["G1"]
        
        # Hangi eksenler hareket edecek?
        moving_z = z is not None
        moving_xy = (x is not None) or (y is not None)
        
        if x is not None: parts.append(f"X{x:.2f}")
        if y is not None: parts.append(f"Y{y:.2f}")
        if z is not None: parts.append(f"Z{z:.2f}")
        
        # Hız belirleme mantığı
        if speed is None:
            if moving_xy:
                speed = self.DEFAULT_SPEED_XY
            elif moving_z:
                speed = self.DEFAULT_SPEED_Z
            else:
                speed = self.DEFAULT_SPEED_XY # Varsayılan
        
        parts.append(f"F{speed}")
        
        cmd = " ".join(parts)
        
        # Log mesajı oluştur
        log_parts = []
        if x is not None: log_parts.append(f"X{x}")
        if y is not None: log_parts.append(f"Y{y}")
        if z is not None: log_parts.append(f"Z{z}")
        print(f"[HAREKET] {' '.join(log_parts)} (Hız: {speed})")

        self.send_command(cmd)
        
        # Hareketin bitmesini bekle (G4 P0.1 komutu bufferın boşalmasını bekler)
        self.send_command("G4 P0.1")

    def close(self):
        if self.ser:
            self.ser.close()
        print("[ÇIKIŞ] Bağlantı kapatıldı.")

# --- ANA TEST KISMI ---
if __name__ == "__main__":
    # 1. Makineyi Başlat
    cnc = CNCDriver(port='/dev/ttyUSB0')

    try:
        # Adım 1: Test Hareketleri
        cnc.move(z=10)
        cnc.move(z=0)

        cnc.move(y=10)
        cnc.move(y=0)

        cnc.move(x=10)
        cnc.move(x=0)

        # Eve Dönüş
        cnc.move(x=0, y=0)

    except KeyboardInterrupt:
        print("\nTest iptal edildi.")
    
    finally:
        cnc.close()