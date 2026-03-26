import serial
import time
import sys

# === RASPBERRY PI MASTER CONTROLLER ===
# Tüm konfigürasyon ve iş mantığı bu dosyadadır.
# Arduino (Slave) sadece düşük seviyeli komutları çalıştırır.

"""
============================================================================
MİMARİ AÇIKLAMASI (LLM'ler ve Geliştiriciler İçin):
============================================================================

MASTER-SLAVE YAPISI:
- MASTER (Bu dosya - Python / Raspberry Pi):
  Tüm konfigürasyon sabitleri, iş mantığı (homing, sınır kontrolü,
  direnç ölçümü, diyot testi, açı-adım dönüşümü) burada tanımlanır.
  Arduino'ya sadece düşük seviyeli komutlar gönderir:
  "şu kadar adım at", "şu pini oku" gibi.

- SLAVE (Arduino):
  Hiçbir karar almaz. Gelen komutları birebir çalıştırır ve sonucu döner.
  Kendi firmware'i bir kez yüklenir, bir daha değiştirilmez.

AVANTAJLARI:
- Parametre değişikliğinde Arduino'ya tekrar kod yüklemeye gerek yok.
- Python tarafında değişiklik yapıp anında test edilebilir.
- Farklı projeler aynı Arduino firmware'i kullanabilir.

DİRENÇ ÖLÇÜMÜ (Voltage Divider):
Devre şeması:
  5V ──[R_bilinmeyen]──┬──[R_bilinen]── GND
                       │
                      A1 (Analog Pin)

Formül: R_bilinmeyen = R_bilinen × ((1023 / ADC) - 1)
  Bu şu şekilde sadeleşir: R_bilinen × (1023 - ADC) / ADC
- ADC: Arduino'nun A1 pininden okuduğu 0-1023 arası değer
- R_bilinen: Voltage divider'a takılan bilinen direnç (Ohm)
- Sonuç: Bilinmeyen direncin Ohm cinsinden değeri

DİYOT TESTİ (D1/D2):
- D1 (İleri Yön - Geçirmeli): Diyotun doğru yönde akım geçirmesi beklenir.
  ADC >= ESIK_DEGERI ise BAŞARILI (akım geçiyor), değilse HATA.
- D2 (Ters Yön - Geçirmesiz): Diyotun ters yönde akım KESmesi beklenir.
  ADC < ESIK_DEGERI ise BAŞARILI (akım kesik), değilse HATA.
- Hata durumunda otomatik düzeltme: 180° dön → 20 sn bekle → geri dön.

KOMUT AKIŞI:
1. Python → Arduino: "MULTI_AREAD 1 20\n"   (A1'den 20 okuma yap, ortala)
2. Arduino → Python: "OK:512"               (Ortalama ADC değeri)
3. Python hesaplar: R = 10000 * ((1023/512) - 1.0) = 9980 Ohm
============================================================================
"""

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     KONFİGÜRASYON SABİTLERİ                           ║
# ║          (Tüm ayarlar burada! Arduino koduna dokunmaya gerek yok)      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# --- Seri Port Ayarları ---
SERIAL_PORT = '/dev/arduino_slave'  # Kalıcı udev symlink (USB port değişse bile aynı kalır)
SERIAL_BAUD = 115200           # Haberleşme hızı (Arduino ile aynı olmalı)
SERIAL_TIMEOUT = 15            # Seri port okuma zaman aşımı (saniye)

# --- CNC Shield Pin Tanımları (Donanımsal sabitler) ---
# Bu değerler CNC Shield V3 tarafından sabitlenmiştir.
STEP_PIN  = 2    # X ekseni Step pini
DIR_PIN   = 5    # X ekseni Direction pini
EN_PIN    = 8    # Motor Enable pini (LOW = Aktif, HIGH = Pasif)
LIMIT_PIN = 9    # X ekseni Limit Switch pini (CNC Shield X-)

# --- Motor Parametreleri ---
STEPS_PER_REV_BASE = 200         # NEMA 17 tam adım/devir (1.8°/adım)
MICROSTEPPING = 16               # CNC Shield jumper ayarı (1, 2, 4, 8 veya 16)
STEPS_PER_REV = STEPS_PER_REV_BASE * MICROSTEPPING  # Toplam adım/devir (ör: 3200)
STEPS_PER_DEGREE = STEPS_PER_REV / 360.0            # Adım/derece (ör: ~8.89)

# --- Hareket Sınırları ---
MIN_ANGLE = -180.0      # Minimum açı (derece) - Home / Limit switch noktası
MAX_ANGLE = 180.0    # Maksimum açı (derece)

# --- Hız Parametreleri (mikrosaniye/adım) ---
NORMAL_SPEED_US   = 400    # Normal hareket hızı (küçük = hızlı)
HOMING_SPEED_US   = 2000   # Homing hızı (yavaş ve güvenli)
ACCEL_STEPS       = 200    # İvmelenme bölge adım sayısı
ACCEL_START_US    = 2000   # İvmelenme başlangıç hızı (en yavaş)

# --- Direnç Ölçümü (Voltage Divider) ---
ANALOG_PIN = 1           # Ölçüm pini (A1)
KNOWN_RESISTANCE = 10000  # Voltage divider'daki bilinen direnç (Ohm) - 10kΩ
VCC = 5.0                # Arduino besleme voltajı
ADC_MAX = 1023           # Arduino ADC çözünürlüğü (10-bit)
ADC_SAMPLE_COUNT = 20    # Her ölçüm için yapılacak okuma sayısı (gürültü azaltma)

# --- Diyot Testi Parametreleri ---
ESIK_DEGERI = 500        # Diyot geçirgenlik eşik değeri (ADC birimi, 0-1023)
                         # ADC >= bu değer → akım geçiyor (diyot ileri yönde)
                         # ADC <  bu değer → akım kesik (diyot ters yönde veya yok)

# --- Test Parametreleri ---
R_TEST_DURATION = 20     # Sürekli direnç testi süresi (saniye)
R_TEST_INTERVAL = 1.0    # Direnç ölçüm aralığı (saniye)

# --- Homing Parametreleri ---
HOMING_MAX_DEGREES = 400         # Homing sırasında maksimum tarama açısı (güvenlik)
HOMING_BACKOFF_DEGREES = 5.0     # Switch'ten geri çekilme mesafesi (hassas referans için)
HOMING_CLEARANCE_DEGREES = 3.0   # Homing sonrası switch'ten uzaklaşma mesafesi (bu nokta 0° olur)
HOMING_DIR = 1                  # Homing yönü: switch'e doğru (0 veya 1, motorunuza göre ayarlayın)
HOMING_BACK_DIR = 0             # Homing geri çekilme yönü (HOMING_DIR'in tersi)

# Hareket Yön Haritasi (Home=0°, pozitif açılar switch'ten uzaklaşır)
POSITIVE_DIR = HOMING_BACK_DIR   # +derece = home'dan uzaklaş (switch'ten uzaklaş)
NEGATIVE_DIR = HOMING_DIR        # -derece = home'a doğru (switch'e doğru)


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     ARDUINO HABERLEŞME SINIFI                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ArduinoSlave:
    """
    Arduino ile seri port üzerinden haberleşme sınıfı.
    Düşük seviyeli komutları Arduino'ya gönderir ve yanıtları okur.
    """

    def __init__(self, port, baud, timeout=15):
        """Arduino'ya bağlan ve hazır olmasını bekle."""
        self.serial = serial.Serial(port=port, baudrate=baud, timeout=timeout)
        time.sleep(2)  # Arduino Auto-Reset stabilizasyonu

        # Bekleme tampon mesajlarını temizle
        while self.serial.in_waiting > 0:
            line = self.serial.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"  Arduino: {line}")

    def send_command(self, cmd, timeout=15):
        """
        Arduino'ya komut gönder ve yanıtı oku.
        Başarılıysa (value, True) döner. value "OK" sonrası veri.
        Başarısızsa (error_msg, False) döner.
        """
        try:
            self.serial.reset_input_buffer()
            self.serial.write(f"{cmd}\n".encode('utf-8'))

            start = time.time()
            while time.time() - start < timeout:
                if self.serial.in_waiting > 0:
                    response = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if response.startswith("OK:"):
                        return response[3:], True
                    elif response == "OK":
                        return "", True
                    elif response.startswith("ERR:"):
                        return response[4:], False
                else:
                    time.sleep(0.01)

            return "Timeout: Arduino'dan yanit alinamadi", False
        except Exception as e:
            return f"Seri port hatasi: {e}", False

    def close(self):
        """Seri port bağlantısını kapat."""
        if self.serial and self.serial.is_open:
            self.serial.close()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     MOTOR KONTROL SINIFI                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class MotorController:
    """
    Step motor kontrolünü yönetir. Tüm mantık (açı-adım dönüşümü,
    sınır kontrolü, homing) bu sınıftadır.
    """

    def __init__(self, slave: ArduinoSlave):
        self.slave = slave
        self.current_angle = 0.0
        self.is_homed = False

        # Limit switch pinini INPUT_PULLUP olarak ayarla
        self.slave.send_command(f"PMODE {LIMIT_PIN} 2")

        # Motoru başlangıçta serbest bırak
        self.motor_enable(False)

    def motor_enable(self, enable: bool):
        """
        Motoru aktif et veya serbest bırak.
        enable=True  → Motor kilitlenir (tork aktif)
        enable=False → Motor serbest kalır (ısınmaz)
        """
        val = 0 if enable else 1  # EN pini aktif düşük (LOW = aktif)
        self.slave.send_command(f"EN {val}")

    def move_relative(self, degrees: float) -> tuple:
        """
        Motoru belirtilen derece kadar GORECE döndür (dahili kullanım).
        Dönen: (gerçek_hareket, yeni_pozisyon, mesaj)
        """
        if degrees == 0:
            return 0, self.current_angle, "Hareket yok."

        # Sınır kontrolü
        new_angle = self.current_angle + degrees
        clamped = False
        if new_angle > MAX_ANGLE:
            degrees = MAX_ANGLE - self.current_angle
            clamped = True
        elif new_angle < MIN_ANGLE:
            degrees = MIN_ANGLE - self.current_angle
            clamped = True

        if abs(degrees) < 0.01:
            return 0, self.current_angle, "Motor zaten sınır noktasında!"

        steps = int(abs(degrees * STEPS_PER_DEGREE))
        direction = POSITIVE_DIR if degrees > 0 else NEGATIVE_DIR

        if steps == 0:
            return 0, self.current_angle, "Çok küçük açı."

        self.motor_enable(True)
        time.sleep(0.01)

        cmd = f"STEPG {steps} {direction} {NORMAL_SPEED_US} {ACCEL_STEPS} {ACCEL_START_US} {LIMIT_PIN}"
        response, success = self.slave.send_command(cmd, timeout=30)

        time.sleep(0.05)
        self.motor_enable(False)

        if success:
            if response == "ESTOP":
                self.is_homed = False
                return 0, self.current_angle, "⚠️ ACİL DURDURMA! Limit switch basıldı. Tekrar 'home' yapın."
            else:
                self.current_angle += degrees
                msg = f"{degrees:+.1f}° hareket"
                if clamped:
                    msg += " (sınıra kırpıldı)"
                return degrees, self.current_angle, msg
        else:
            return 0, self.current_angle, f"Hata: {response}"

    def goto_angle(self, target: float) -> tuple:
        """
        Motoru belirtilen MUTLAK açıya götür.
        Örnek: goto_angle(180) → motor 180°'ye gider (nerede olursa olsun).
        Dönen: (başarılı_mı, yeni_pozisyon, mesaj)
        """
        # Hedef sınır içinde mi?
        if target > MAX_ANGLE:
            target = MAX_ANGLE
        elif target < MIN_ANGLE:
            target = MIN_ANGLE

        delta = target - self.current_angle

        if abs(delta) < 0.01:
            return 0, self.current_angle, f"Zaten {target:.1f}° pozisyonunda."

        moved, new_pos, msg = self.move_relative(delta)
        return moved, new_pos, msg

    def home(self) -> tuple:
        """
        Homing (referans alma) işlemi.
        Motor, limit switch'e ulaşana kadar HOMING_DIR yönünde döner.
        Switch noktası 0° (HOME) olarak kaydedilir ve motor orada kalır.
        Dönen: (başarılı_mı, mesaj)
        """
        print("  ⏳ Homing başlatılıyor...")

        # Motoru aktif et
        self.motor_enable(True)
        time.sleep(0.05)

        # --- AŞAMA 1: Limit switch'e hızlı yaklaşma ---
        print("  ⏳ Limit switch aranıyor...")
        max_steps = int(HOMING_MAX_DEGREES * STEPS_PER_DEGREE)
        batch_size = 50

        found = False
        steps_taken = 0

        while steps_taken < max_steps:
            response, success = self.slave.send_command(f"DREAD {LIMIT_PIN}")
            if success and response == "0":
                found = True
                break

            cmd = f"STEP {batch_size} {HOMING_DIR} {HOMING_SPEED_US} 0 {HOMING_SPEED_US}"
            self.slave.send_command(cmd, timeout=10)
            steps_taken += batch_size
            time.sleep(0.02)

        if not found:
            self.motor_enable(False)
            return False, "Limit switch bulunamadı! Kablo bağlantısını kontrol edin."

        print("  ⏳ Switch bulundu, hassas referans alınıyor (1. geçiş)...")
        time.sleep(0.3)

        # --- AŞAMA 2: Geri çekilme (switch'ten uzaklaş) ---
        backoff_steps = int(HOMING_BACKOFF_DEGREES * STEPS_PER_DEGREE)
        cmd = f"STEP {backoff_steps} {HOMING_BACK_DIR} {HOMING_SPEED_US} 0 {HOMING_SPEED_US}"
        self.slave.send_command(cmd, timeout=10)
        time.sleep(0.3)

        # --- AŞAMA 3: Hassas yaklaşma - 1. geçiş (çok yavaş) ---
        slow_speed = HOMING_SPEED_US * 2
        for _ in range(backoff_steps + 50):
            response, success = self.slave.send_command(f"DREAD {LIMIT_PIN}")
            if success and response == "0":
                break
            cmd = f"STEP 1 {HOMING_DIR} {slow_speed} 0 {slow_speed}"
            self.slave.send_command(cmd, timeout=5)
            time.sleep(0.01)

        print("  ⏳ Hassas referans alınıyor (2. geçiş)...")
        time.sleep(0.3)

        # --- AŞAMA 4: 2. geri çekilme (daha kısa) ---
        small_backoff = int(2.0 * STEPS_PER_DEGREE)  # 2 derece geri
        cmd = f"STEP {small_backoff} {HOMING_BACK_DIR} {slow_speed} 0 {slow_speed}"
        self.slave.send_command(cmd, timeout=10)
        time.sleep(0.3)

        # --- AŞAMA 5: Ultra hassas yaklaşma - 2. geçiş (en yavaş) ---
        ultra_slow = HOMING_SPEED_US * 4
        for _ in range(small_backoff + 30):
            response, success = self.slave.send_command(f"DREAD {LIMIT_PIN}")
            if success and response == "0":
                break
            cmd = f"STEP 1 {HOMING_DIR} {ultra_slow} 0 {ultra_slow}"
            self.slave.send_command(cmd, timeout=5)
            time.sleep(0.01)

        # --- AŞAMA 6: Switch'ten uzaklaş ---
        clearance_steps = int(HOMING_CLEARANCE_DEGREES * STEPS_PER_DEGREE)
        cmd = f"STEP {clearance_steps} {HOMING_BACK_DIR} {HOMING_SPEED_US} 0 {HOMING_SPEED_US}"
        self.slave.send_command(cmd, timeout=10)
        time.sleep(0.1)

        # --- AŞAMA 7: Uzaklaşmış noktayı 0° olarak kaydet ---
        self.current_angle = 0.0
        self.is_homed = True

        self.motor_enable(False)

        return True, "Homing tamamlandı. Motor 0° pozisyonunda."


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     DİRENÇ ÖLÇÜM SINIFI                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ResistanceMeter:
    """
    Voltage divider üzerinden direnç ölçümü yapar.

    Devre:
    5V ──[R_bilinmeyen]──┬──[R_bilinen]── GND
                         │
                        A1

    ADC değeri ters çevrilerek okunur (1023 - ham_ADC).
    Formül: R_bilinmeyen = R_bilinen × (1023 - ADC_ters) / ADC_ters
    - Devre boşken: ADC_ters ≈ 0 → AÇIK DEVRE
    - Kısa devre:   ADC_ters ≈ 1023 → KISA DEVRE
    """

    def __init__(self, slave: ArduinoSlave):
        self.slave = slave

    def read_adc(self) -> tuple:
        """
        A1 pininden ortalama ADC değeri oku ve ters çevir.
        Dönen: (ters_adc_değeri, başarılı_mı)
        """
        response, success = self.slave.send_command(
            f"MULTI_AREAD {ANALOG_PIN} {ADC_SAMPLE_COUNT}"
        )
        if not success:
            return 0, False
        raw = int(response)
        return (ADC_MAX - raw), True  # ADC'yi ters çevir

    def calculate_resistance(self, adc_value: int) -> tuple:
        """
        Ters çevrilmiş ADC değerinden direnç hesapla.
        Dönen: (direnç_ohm, voltaj, durum_mesajı)
        """
        # ADC_ters düşük → devre boş (açık devre)
        if adc_value <= 5:
            return float('inf'), 0, 'ACIK_DEVRE'

        # ADC_ters yüksek → kısa devre
        if adc_value >= ADC_MAX - 5:
            return 0, VCC, 'KISA_DEVRE'

        voltage = (adc_value / ADC_MAX) * VCC
        # Formül: R_bilinmeyen = R_bilinen × (1023 - ADC_ters) / ADC_ters
        resistance = KNOWN_RESISTANCE * (ADC_MAX - adc_value) / adc_value
        return resistance, voltage, 'NORMAL'

    def measure(self) -> tuple:
        """
        Tek seferlik direnç ölçümü yap.
        Dönen: (direnç_ohm, adc_değeri, voltaj, başarılı_mı)
        """
        adc_value, success = self.read_adc()
        if not success:
            return 0, 0, 0, False

        resistance, voltage, status = self.calculate_resistance(adc_value)
        return resistance, adc_value, voltage, True

    def format_resistance(self, resistance: float) -> str:
        """Direnci okunabilir formatta string'e çevir."""
        if resistance == float('inf'):
            return "AÇIK DEVRE"
        elif resistance == 0:
            return "KISA DEVRE"
        elif resistance >= 1_000_000:
            return f"{resistance/1_000_000:.2f} MΩ"
        elif resistance >= 1000:
            return f"{resistance/1000:.2f} kΩ"
        else:
            return f"{resistance:.1f} Ω"


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     KOMPONENT TEST SINIFI                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class ComponentTester:
    """
    Direnç ve diyot testlerini yönetir.

    TEST MODLARİ (LLM'ler İçin Detaylı Açıklama):

    R (Direnç Testi):
      - R_TEST_DURATION saniye boyunca (varsayılan: 20 sn) sürekli direnç ölçümü yapar.
      - Her R_TEST_INTERVAL saniyede (varsayılan: 1 sn) bir ölçüm alır ve terminale basar.
      - Voltage divider formülü: R = R_SABIT × ((1023 / ADC) - 1)
      - Üç olası durum: AÇIK DEVRE (ADC ≤ 5), KISA DEVRE (ADC ≥ 1018), NORMAL

    D (Diyot Testi):
      - Diyotun akım geçirip geçirmediğini kontrol eder.
      - A1 pininden ADC ölçümü alır.
      - ADC >= ESIK_DEGERI (500) → Akım GEÇİYOR
      - ADC <  ESIK_DEGERI (500) → Akım GEÇMİYOR
    """

    def __init__(self, slave: ArduinoSlave, meter: ResistanceMeter):
        self.slave = slave
        self.meter = meter

    def resistance_test(self):
        """
        MOD R: Sürekli direnç ölçümü (R_TEST_DURATION saniye boyunca).
        Her saniye ölçüm alır ve terminale basar.
        """
        print(f"\n  >>> MOD: Direnç Testi ({R_TEST_DURATION} Saniye)")
        print(f"  {'─' * 45}")

        start_time = time.time()
        elapsed = 0

        while elapsed < R_TEST_DURATION:
            # ADC oku
            adc_value, success = self.meter.read_adc()

            if not success:
                print(f"  [Sn:{int(elapsed):2d}] HATA: Okuma başarısız!")
            else:
                resistance, voltage, status = self.meter.calculate_resistance(adc_value)

                if status == 'ACIK_DEVRE':
                    print(f"  [Sn:{int(elapsed):2d}] Durum: AÇIK DEVRE (ADC: {adc_value})")
                elif status == 'KISA_DEVRE':
                    print(f"  [Sn:{int(elapsed):2d}] Durum: KISA DEVRE (ADC: {adc_value})")
                else:
                    r_str = self.meter.format_resistance(resistance)
                    print(f"  [Sn:{int(elapsed):2d}] Direnç: {r_str} | ADC: {adc_value} | V: {voltage:.3f}V")

            # Bir sonraki ölçüme kadar bekle
            time.sleep(R_TEST_INTERVAL)
            elapsed = time.time() - start_time

        print(f"  {'─' * 45}")
        print(f"  >>> Direnç testi tamamlandı.\n")

    def diode_test(self):
        """
        MOD D: Diyot testi.
        A1 pininden ADC ölçümü alır ve akım geçirip geçirmediğini raporlar.
        """
        print(f"\n  >>> MOD: Diyot Testi")
        print(f"  {'─' * 45}")

        # A1 pininden ölçüm al
        adc_value, success = self.meter.read_adc()

        if not success:
            print("  [HATA] ADC okuması başarısız!")
            print(f"  {'─' * 45}\n")
            return

        print(f"  Ölçüm (ADC): {adc_value} | Eşik: {ESIK_DEGERI}")

        if adc_value >= ESIK_DEGERI:
            print("  SONUÇ: ✅ AKIM GEÇİYOR")
        else:
            print("  SONUÇ: ❌ AKIM GEÇMİYOR")

        print(f"  {'─' * 45}\n")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                     ANA PROGRAM (Kullanıcı Arayüzü)                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    print("=" * 55)
    print("  MASTER-SLAVE KONTROL SİSTEMİ v4.0")
    print("  Motor + Direnç Ölçümü + Diyot Testi")
    print("=" * 55)
    print(f"\nBağlanılıyor ({SERIAL_PORT})...")

    try:
        slave = ArduinoSlave(SERIAL_PORT, SERIAL_BAUD, SERIAL_TIMEOUT)
    except Exception as e:
        print(f"[HATA] Bağlantı başarısız: {e}")
        sys.exit(1)

    # Bağlantı testi
    response, success = slave.send_command("PING")
    if success and response == "PONG":
        print("[OK] Arduino bağlantısı doğrulandı.\n")
    else:
        print("[UYARI] PING yanıtı alınamadı, devam ediliyor...\n")

    # Kontrol nesnelerini oluştur
    motor = MotorController(slave)
    meter = ResistanceMeter(slave)
    tester = ComponentTester(slave, meter)

    # Kullanım bilgisi
    print(f"{'─' * 55}")
    print("  KOMUTLAR:")
    print(f"{'─' * 55}")
    print("  [sayı]      Hedef açıya git (ör: 90, 0, 180)")
    print("  home        Limit switch ile referans alma")
    print("  pos         Mevcut pozisyonu göster")
    print("  ohm         Tek seferlik direnç ölçümü (A1)")
    print("  r           Sürekli direnç testi (20 sn)")
    print("  d           Diyot testi (akım geçiriyor mu?)")
    print("  status      Sistem durumu")
    print("  config      Mevcut konfigürasyonu göster")
    print("  q / quit    Çıkış")
    print(f"{'─' * 55}")
    print(f"  Hareket: {MIN_ANGLE}° ↔ {MAX_ANGLE}° | Mikro adım: 1/{MICROSTEPPING}")
    print(f"  Bilinen Direnç: {KNOWN_RESISTANCE} Ω | Eşik: {ESIK_DEGERI} ADC")
    print(f"{'─' * 55}\n")

    while True:
        try:
            user_input = input(">> ").strip()

            if not user_input:
                continue

            cmd = user_input.lower()

            # --- Çıkış ---
            if cmd in ['q', 'quit', 'exit']:
                print("Çıkış yapılıyor...")
                break

            # --- HOME ---
            elif cmd == 'home':
                success, msg = motor.home()
                prefix = "[OK]" if success else "[HATA]"
                print(f"{prefix} {msg}")

            # --- POS ---
            elif cmd == 'pos':
                print(f"[POZ] {motor.current_angle:.1f}° | Homed: {'Evet' if motor.is_homed else 'Hayır'}")

            # --- OHM (Tek seferlik direnç ölçümü) ---
            elif cmd == 'ohm':
                resistance, adc, voltage, success = meter.measure()
                if success:
                    r_str = meter.format_resistance(resistance)
                    if resistance == float('inf') or resistance == 0:
                        print(f"[OHM] {r_str} (ADC: {adc})")
                    else:
                        print(f"[OHM] Direnç: {r_str} | Voltaj: {voltage:.3f}V | ADC: {adc}")
                else:
                    print("[HATA] Direnç ölçümü başarısız.")

            # --- R (Sürekli direnç testi - 20 sn) ---
            elif cmd == 'r':
                tester.resistance_test()

            # --- D (Diyot testi) ---
            elif cmd == 'd':
                tester.diode_test()

            # --- STATUS ---
            elif cmd == 'status':
                print(f"  Motor Pozisyon  : {motor.current_angle:.1f}°")
                print(f"  Homed           : {'Evet' if motor.is_homed else 'Hayır'}")
                print(f"  Hareket Aralığı : {MIN_ANGLE}° ↔ {MAX_ANGLE}°")
                print(f"  Adım/Derece     : {STEPS_PER_DEGREE:.2f}")
                print(f"  Hız             : {NORMAL_SPEED_US} µs/adım")
                print(f"  Eşik Değeri     : {ESIK_DEGERI} ADC")

                # Limit switch durumu
                resp, ok = slave.send_command(f"DREAD {LIMIT_PIN}")
                if ok:
                    sw = "BASILI" if resp == "0" else "AÇIK"
                    print(f"  Limit Switch    : {sw}")

                # Direnç ölçümü
                resistance, adc, voltage, ok = meter.measure()
                if ok:
                    r_str = meter.format_resistance(resistance)
                    print(f"  Direnç (A{ANALOG_PIN})    : {r_str} (ADC: {adc})")

            # --- CONFIG ---
            elif cmd == 'config':
                print(f"\n  {'─' * 45}")
                print(f"  KONFİGÜRASYON")
                print(f"  {'─' * 45}")
                print(f"  Seri Port         : {SERIAL_PORT}")
                print(f"  Baud Rate         : {SERIAL_BAUD}")
                print(f"  Step Pin          : {STEP_PIN}")
                print(f"  Dir Pin           : {DIR_PIN}")
                print(f"  Enable Pin        : {EN_PIN}")
                print(f"  Limit Pin         : {LIMIT_PIN}")
                print(f"  Adım/Devir        : {STEPS_PER_REV} ({STEPS_PER_REV_BASE} × {MICROSTEPPING})")
                print(f"  Adım/Derece       : {STEPS_PER_DEGREE:.2f}")
                print(f"  Min/Max Açı       : {MIN_ANGLE}° / {MAX_ANGLE}°")
                print(f"  Normal Hız        : {NORMAL_SPEED_US} µs/adım")
                print(f"  Homing Hızı       : {HOMING_SPEED_US} µs/adım")
                print(f"  İvme Adım         : {ACCEL_STEPS}")
                print(f"  İvme Başlangıç    : {ACCEL_START_US} µs/adım")
                print(f"  Bilinen Direnç    : {KNOWN_RESISTANCE} Ω")
                print(f"  Analog Pin        : A{ANALOG_PIN}")
                print(f"  ADC Örnekleme     : {ADC_SAMPLE_COUNT} okuma")
                print(f"  Diyot Eşik        : {ESIK_DEGERI} ADC")
                print(f"  R Test Süresi     : {R_TEST_DURATION} sn")
                print(f"  {'─' * 45}\n")

            # --- Sayısal Açı Komutu ---
            else:
                try:
                    angle = float(user_input)
                except ValueError:
                    print("[HATA] Geçersiz komut. Sayı veya komut adı girin.")
                    continue

                moved, new_pos, msg = motor.goto_angle(angle)
                print(f"[OK] {msg} | Pozisyon: {new_pos:.1f}°")

        except KeyboardInterrupt:
            print("\nProgram kapatılıyor...")
            break

    slave.close()
    print("Bağlantı kapatıldı. Hoşçakalın!")


if __name__ == '__main__':
    main()
