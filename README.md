# 🏭 PNP Control Center v2.0

<div align="center">

**Endüstriyel Pick & Place Makinesi için Web Tabanlı Akıllı Kontrol Merkezi**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask)](https://flask.palletsprojects.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-4.x-010101?logo=socket.io)](https://socket.io/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv)](https://opencv.org/)
[![Arduino](https://img.shields.io/badge/Arduino-Compatible-00979D?logo=arduino)](https://www.arduino.cc/)
[![License](https://img.shields.io/badge/License-ELE495-orange)](#lisans)

</div>

> Raspberry Pi üzerinde çalışan, Flask + Socket.IO altyapısıyla **gerçek zamanlı makine kontrolü**, **kamera izleme**, **OCR tabanlı otomasyon**, **koşullu test senaryoları** ve **nozzle yönetimi** sunan kapsamlı bir endüstriyel kontrol sistemi.

---

## 📋 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Sayfa ve Sekmeler](#-sayfa-ve-sekmeler)
- [Senaryo Sistemi Detayları](#-senaryo-sistemi-detayları)
- [API Referansı](#-api-referansı)
- [Donanım Gereksinimleri](#-donanım-gereksinimleri)
- [Yapılandırma](#-yapılandırma)
- [Proje Yapısı](#-proje-yapısı)
- [Lisans](#-lisans)

---

## 🔍 Genel Bakış

PNP Control Center, bir **Pick and Place** makinesinin tüm bileşenlerini — CNC motorları, vakum pompası, kamera, OCR, nozzle step motor, direnç/diyot ölçümü — tek bir web arayüzünden yönetmeyi sağlayan **entegre bir kontrol sistemidir**.

### Temel Yetenekler

| Alan | Açıklama |
|------|----------|
| 🎮 **Motor Kontrol** | GRBL tabanlı 3 eksen (X, Y, Z) CNC motor kontrolü |
| 📷 **Kamera & OCR** | Gerçek zamanlı görüntü akışı, Tesseract OCR ile metin tanıma |
| 🔧 **Nozzle Sistemi** | Step motor ile hassas açı kontrolü, direnç ve diyot ölçümü |
| 🎬 **Senaryo Motoru** | Koşullu IF blokları ve çoklu adım senaryoları ile tam otomasyon |
| 👁️ **Doğrulama** | Bileşen yerleşim doğrulaması (OCR tabanlı) |
| 📍 **Konum Yönetimi** | Sınırsız kayıtlı konum, akıllı Z sıralamalı güvenli hareket |
| ⚡ **Otomatik Port** | USB cihazlarını otomatik algılama ve bağlama |

---

## ✨ Özellikler

### 🎮 Motor Kontrol
- **3 Eksen Hareket**: X, Y, Z eksenlerinde hassas konumlandırma
- **Jog Kontrolleri**: Ayarlanabilir adım boyutlarıyla (0.1mm – 50mm) manuel hareket
- **Homing Döngüsü**: Otomatik referans alma, bağlantı kurulduğunda otomatik home
- **Konum Kayıt**: Sınırsız kayıtlı konum (Base Position) tanımlama ve düzenleme
- **Akıllı Z Sıralaması**: Çarpışma riski analizli güvenli hareket (Z önce/sonra otomatik karar)
- **G-code Konsolu**: Doğrudan G-code komutu gönderebilme
- **Klavye Kısayolları**: Ok tuşları, H (Home), C (Center), Space (Pompa)

### 📷 Kamera Sistemi
- **Canlı Yayın**: MJPEG formatında gerçek zamanlı kamera görüntüsü
- **Çift Çözünürlük**: Yakalama (OCR) ve yayın (ekran) çözünürlükleri bağımsız ayarlanabilir
- **PIP Zoom**: Çapraz imlecin olduğu noktada 1x–10x büyütme özelliği
- **FPS Monitörü**: Kamera ve OCR FPS değerleri anlık gösterim
- **Overlay Sistem**: Senaryo durumu, ölçüm sonuçları ve test banner'ları kamera üstünde

### 🔤 OCR (Optik Karakter Tanıma)
- **Tesseract Entegrasyonu**: Gerçek zamanlı metin tanıma (tesserocr)
- **Bounding Box Görselleştirme**: Algılanan metnin etrafında dinamik çerçeveler
- **Stabilizasyon**: Çerçeve boyut sınırlaması ile titreşim önleme
- **Otomatik Merkezleme**: Hedef kelimeyi tespit edip makineyi o konuma otomatik hareket ettirme
- **Beyaz Liste & PSM Modu**: Özelleştirilebilir karakter seti ve Tesseract modu

### 🔄 Nozzle Kontrol Sistemi
- **Step Motor Kontrolü**: Hassas açı kontrolü (0–360°), ivmeli hareket profili
- **Homing**: Limit switch ile otomatik referans alma
- **Hızlı Döndürme**: ±15°, ±45°, ±90°, ±180° preset butonları
- **Direnç Ölçümü**:
  - Anlık ve tekrarlı direnç testi
  - ADC değeri, voltaj, direnç hesaplama
  - Min, Max, Standart Sapma istatistikleri
  - Ölçüm bazında detaylı tablo
- **Diyot Testi**:
  - Anlık ve tekrarlı akım geçiş testi
  - Çoğunluk kararı (pass/fail)
  - Otomatik düzeltme (180° döndürme)
  - ADC istatistikleri ve ölçüm tablosu
- **Hızlı Ölçüm**: Ana kontrol ekranında tek tuşla direnç/diyot okuma + sonuç HUD'u

### 📋 Senaryo Sistemi
- **15+ Adım Tipi**: Konum, OCR, pompa, nozzle, delay, ölçüm, koşullu test ve daha fazlası
- **IF Blokları**: Koşullu direnç ve diyot testleri (PASS/FAIL branching)
- **Pick & Test**: Otomatik al-test-yerleştir döngüsü
- **Master Senaryo**: Birden fazla senaryoyu sıralı çalıştırma
- **Gerçek Zamanlı Sonuç**: Büyük PASS ✅ / FAIL ❌ banner'ı ile belirgin test sonucu gösterimi
- **Senaryo Kopyalama**: Mevcut senaryoyu tek tuşla çoğaltma
- **Alt Adım Düzenleme**: PASS/FAIL branch'leri için yukarı/aşağı sıralama

### ✅ Doğrulama Sistemi
- **OCR Tabanlı Doğrulama**: Bileşen etiketlerini kamera ile okuyup doğrulama
- **Eşik Değeri Ayarı**: Tesseract güven eşiği özelleştirme ve canlı önizleme
- **HUD Entegrasyonu**: Sonuçlar ana ekranda kamera üstünde gerçek zamanlı gösterim
- **Kutu Bazlı İlerleme**: Her bileşen analiz edilirken canlı sonuç kartları

### 🔌 Otomatik Port Algılama
- **GRBL Algılama**: Bağlanınca "Grbl" banner'ı ile doğrulama
- **Nozzle Algılama**: PING/PONG protokolü ile doğrulama
- **Udev Kuralları**: Kalıcı port ataması desteği

---

## 🏗 Sistem Mimarisi

```
┌──────────────────────────────────────────────────┐
│                  Web Tarayıcı                     │
│          (HTML + CSS + JavaScript)                │
│              Socket.IO Client                    │
└──────────────────────┬───────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────┴───────────────────────────┐
│              Flask + Socket.IO                    │
│                  (app.py)                         │
│  ┌─────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  GRBL   │ │  Camera  │ │  Nozzle (Slave   │  │
│  │ Driver  │ │ Manager  │ │  Arduino)        │  │
│  └────┬────┘ └────┬─────┘ └────────┬─────────┘  │
│       │           │                │             │
└───────┼───────────┼────────────────┼─────────────┘
        │           │                │
   ┌────┴────┐ ┌────┴─────┐  ┌──────┴──────┐
   │  GRBL   │ │ RPi Cam  │  │  Arduino    │
   │ Arduino │ │ Module 3 │  │  (Slave)    │
   │ (CNC)   │ │          │  │  Step Motor │
   └─────────┘ └──────────┘  │  ADC Read   │
                              │  Limit SW   │
                              └─────────────┘
```

### Veri Akışı

```
Kullanıcı → Tarayıcı → Socket.IO → Flask Backend → Seri Port → Arduino/GRBL
                ↑                         ↓
                ← Socket.IO Events ← Gerçek Zamanlı Durum Bildirimleri
```

---

## 🛠 Kurulum

### Ön Gereksinimler

- **Raspberry Pi 4/5** (4GB+ RAM önerilen)
- **Python 3.11+**
- **Raspberry Pi Camera Module 3**
- **GRBL uyumlu CNC kontrol kartı** (Arduino Uno/Mega)
- **Arduino** (Nozzle slave kontrolcü)

### Kurulum Adımları

```bash
# 1. Repoyu klonla
git clone https://github.com/bitirici-ekip/ele495.git
cd ele495

# 2. Sanal ortam oluştur ve aktifleştir
python3 -m venv venv
source venv/bin/activate

# 3. Python bağımlılıklarını yükle
pip install -r requirements.txt

# 4. Tesseract OCR ve sistem bağımlılıklarını yükle
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-eng libleptonica-dev libtesseract-dev

# 5. Arduino firmware'ını yükle
# arduino_stepper.ino dosyasını Arduino IDE ile Slave Arduino'ya yükleyin

# 6. Uygulama portlarını ayarla (isteğe bağlı — otomatik algılama mevcuttur)
# Udev kuralları ile kalıcı port ataması:
# /etc/udev/rules.d/99-usb-serial.rules

# 7. Uygulamayı başlat
python app.py
```

Uygulama varsayılan olarak `http://0.0.0.0:5000` adresinde çalışır.

### Hızlı Başlatma

```bash
# Direkt çalıştırma
source venv/bin/activate && python app.py
```

---

## 🖥 Kullanım

Tarayıcınızdan `http://<raspberry-pi-ip>:5000` adresine gidin.

### İlk Kullanım
1. **Otomatik Bağlantı**: Uygulama açılırken GRBL ve Nozzle Arduino'ları otomatik algılar
2. **Home Döngüsü**: Bağlantı kurulduğunda otomatik home yapılır
3. **Konum Kaydetme**: İstenen konumlara gidin ve **Konumlar** sekmesinden kaydedin
4. **Senaryo Oluşturma**: Senaryolar sekmesinden otomasyon adımlarınızı tanımlayın

### Klavye Kısayolları

| Tuş | İşlev |
|-----|-------|
| `↑` `↓` `←` `→` | Motor XY hareketi |
| `W` / `S` | Z yukarı / aşağı |
| `Q` / `E` | Adım boyutu azalt / artır |
| `H` | Home |
| `C` | Auto Center |
| `Space` | Pompa aç/kapat |
| `PageUp` / `PageDown` | Z yukarı / aşağı |

---

## 📑 Sayfa ve Sekmeler

### 🎮 Kontrol Sekmesi (Ana Sayfa)

Ana kontrol merkezi — 3 sütunlu düzen:

**Sol Panel:**
- 🎬 **Hızlı Senaryo Başlatıcı** — Dropdown ile senaryo/master senaryo seçip tek tuşla çalıştırma
- 🎯 **Hızlı Merkezleme** — Kelime gir ve merkeze taşı, preset butonlar (TEST, CRB, SHN, AYD, MUS)
- 📍 **Hızlı Konuma Git** — Kayıtlı konumlara dropdown ile tek tuşla git
- 🔬 **Hızlı Ölçüm** — Direnç ve Diyot butonları
- 📋 **Konsol** — G-code gönderme ve sistem log'ları

**Orta Panel (Kamera):**
- 📹 Canlı kamera görüntüsü (MJPEG stream)
- 🔍 OCR bounding box overlay
- 🔎 PIP Zoom slider (1x–10x)
- ⚙️ Çözünürlük ayarları popup'ı
- 📊 FPS monitörü (Kamera + OCR)
- ✅ Doğrulama sonuçları HUD (kamera üstü)
- 📦 **Ölçüm Sonuç Kutuları** — Kamera altında direnç/diyot sonuçları (senaryo sırasında da görünür)
- 🎯 **Test Sonuç Banner'ı** — Büyük, animasyonlu PASS ✅ / FAIL ❌ gösterimi

**Sağ Panel:**
- 📍 Gerçek zamanlı X/Y/Z koordinatları
- ⚡ Aksiyon butonları (Pompa, Unlock, Reset, Sunucu Kapat)
- 🎮 Motor kontrol yön tuşları (8 yön + Z)
- 📏 Adım boyutu seçici (0.1 – 50mm)
- ↕️ Mutlak Z hedef hareketi

---

### 🔧 Kalibrasyon Sekmesi

Motor yön ve piksel/mm kalibrasyonu:

- **Motor Yön Testi**: X+ ve Y+ yönlerinde hareket → kamerada hangi yöne gittiğini seç
- **Otomatik Hesaplama**: Eksen swap, X ters, Y ters otomatik belirleme
- **Piksel/mm Oranı**: X ve Y çarpanlarını görüntüleme ve kaydetme
- **Manuel Override**: İleri düzey kullanıcılar için eksen ayarları

---

### 📋 Senaryolar Sekmesi

İki bölümlü düzen — **Standart Senaryolar** ve **Master Senaryolar**:

- **Senaryo Oluşturucu**: Ad verin, adımları ekleyin, kaydedin
- **15+ Adım Tipi**: Konum, OCR, pompa, nozzle, ölçüm, koşullu test
- **IF Blokları**: Direnç ve diyot koşullu testler ile dallanma (PASS/FAIL alt adımları)
- **Adım Düzenleme**: Ekleme, düzenleme, silme, yukarı/aşağı taşıma, aralara ekleme
- **Senaryo Kopyalama**: Mevcut senaryoyu tek tuşla çoğalt
- **Master Senaryo**: Birden fazla senaryoyu sıralı çalıştırma
- **Canlı İlerleme**: Çalışan senaryonun her adımı gerçek zamanlı izleme

---

### 🔄 Nozzle Sekmesi

3 sütunlu profesyonel dashboard:

**Sol Sütun — Bağlantı & Motor:**
- Seri port bağlantısı (bağlan/kopar)
- Büyük açı göstergesi (animasyonlu gradient arkaplan)
- Home butonu + hedef açı girişi
- Hızlı döndürme butonları (±15°, ±45°, ±90°, ±180°)

**Orta Sütun — Ölçümler:**
- 🔬 **Direnç Ölçümü**: Anlık + tekrarlı test, detaylı tablo, istatistikler
- 💡 **Diyot Testi**: Anlık + tekrarlı test, otomatik düzeltme (180° döndür)

**Sağ Sütun — Ayarlar:**
- Motor parametreleri (adım/devir, mikro adımlama, min/max açı)
- Hız ayarları (normal, homing, ivme)
- Pin yapılandırması ve ölçüm parametreleri

---

### 👁️ Doğrulama Sekmesi

Bileşen yerleşim doğrulaması:

- Bileşen listesi tanımlama (isim + beklenen eşleşme oranı)
- Base konum seçimi (doğrulama yapılacak konum)
- Threshold canlı önizleme (kamera üstünde)
- Kutu bazlı gerçek zamanlı ilerleme gösterimi
- Her bileşen için PASS ✅ / FAIL ❌ sonuç kartları

---

### ⚙️ Ayarlar Sekmesi

Sistem yapılandırması — 4 kart düzeni:

- **🎛️ Motor & Kalibrasyon**: Piksel/mm oranları, hedef nokta, feed rate, tolerans, yön ters çevirme
- **🔍 OCR Ayarları**: Güven eşiği, PSM modu, whitelist, min kelime uzunluğu, kutu büyüme
- **📊 OCR İzleme**: Algılanan kelime sayısı, hedef durumu, hata listesi
- **ℹ️ Sistem**: Motor port, GRBL state, kamera durumu, çalışma süresi, kısayollar

---

### 📍 Konumlar Sekmesi

Kayıtlı konum (base) yönetimi:

- Yeni konum ekleme (isim + X, Y, Z koordinatları)
- Mevcut konumu çek butonu (anlık pozisyonu al)
- Konum düzenleme (inline edit)
- Konum silme (onay ile)
- Konuma git butonu (akıllı Z sıralaması)

---

## 🎬 Senaryo Sistemi Detayları

### Desteklenen Adım Tipleri

| Tip | Açıklama | Parametreler |
|-----|----------|-------------|
| `goto_base` | Kayıtlı konuma git | Konum adı |
| `auto_center` | Kelimeye otomatik merkezle (OCR) | Hedef kelime |
| `pump_on` | Vakum pompası aç | — |
| `pump_off` | Vakum pompası kapat | — |
| `delay` | Bekleme süresi | Saniye |
| `move_z` | Z ekseni mutlak hareketi | Z (mm) |
| `home` | GRBL Home pozisyonuna git | — |
| `nozzle_goto` | Nozzle'ı belirli açıya döndür | Açı (0–180°) |
| `nozzle_home` | Nozzle homing | — |
| `resistance_read` | Tek seferlik anlık direnç ölçümü | — |
| `diode_read` | Tek seferlik anlık diyot testi | — |
| `resistance_test` | Direnç testi (tekrarlı) | — |
| `diode_test` | Diyot testi (tekrarlı) | — |
| `verify` | Doğrulama kontrolü | — |
| `if_resistance` | Koşullu direnç testi (IF bloku) | Hedef Ω, tolerans %, PASS/FAIL alt adımları |
| `if_diode` | Koşullu diyot testi (IF bloku) | Beklenen durum, PASS/FAIL alt adımları |

### IF Blokları (Koşullu Test)

IF blokları, test sonucuna göre farklı adım dizilerinin çalıştırılmasını sağlar:

```
IF Direnç(hedef=10kΩ, tolerans=±10%)
  ├── ✅ PASS (9kΩ – 11kΩ arası):
  │   ├── Konuma Git: "PASS KUTUSU"
  │   ├── Pompa Kapat
  │   └── ...
  └── ❌ FAIL (aralık dışı):
      ├── Konuma Git: "FAIL KUTUSU"
      ├── Nozzle 180° Döndür
      └── ...
```

### Test Sonuç Gösterimi

Senaryo sırasında yapılan her ölçümde:
1. **Ölçüm Kutuları**: Kamera altında direnç/diyot değerleri (küçük kutular)
2. **PASS/FAIL Banner**: Ekranın ortasında büyük, animasyonlu sonuç gösterimi
   - ✅ **PASS** — Yeşil gradient arka plan
   - ❌ **FAIL** — Kırmızı gradient arka plan
   - 📊 **Ölçüm** — Mavi gradient (koşulsuz düz ölçüm)

---

## 🔌 API Referansı

### Motor Kontrol
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/move` | POST | Göreceli motor hareketi `{x, y, z}` |
| `/api/move_z_absolute` | POST | Mutlak Z hareketi `{z}` |
| `/api/home` | POST | Homing döngüsü |
| `/api/pump` | POST | Pompa kontrolü `{state: true/false}` |
| `/api/grbl_status` | GET | GRBL durum sorgula |

### Kamera & OCR
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/video_feed` | GET | MJPEG video akışı (annotasyonlu) |
| `/video_feed_raw` | GET | MJPEG video akışı (temiz) |
| `/api/camera/resolution` | POST | Çözünürlük ayarla `{width, height}` |
| `/api/auto_center` | POST | Otomatik merkezleme `{target_word}` |
| `/api/status` | GET | Tüm sistem durumu |

### Konumlar
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/bases` | GET/POST | Konumları listele/kaydet |
| `/api/bases/<name>` | DELETE | Konum sil |
| `/api/goto_base` | POST | Konuma git `{name}` |

### Nozzle
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/nozzle/connect` | POST | Nozzle Arduino bağlantısı |
| `/api/nozzle/disconnect` | POST | Bağlantıyı kes |
| `/api/nozzle/home` | POST | Nozzle homing |
| `/api/nozzle/goto` | POST | Belirli açıya git `{angle}` |
| `/api/nozzle/read_resistance` | GET | Anlık direnç oku |
| `/api/nozzle/read_diode` | GET | Anlık diyot testi |
| `/api/nozzle/resistance_test` | POST | Tekrarlı direnç testi |
| `/api/nozzle/diode_test` | POST | Tekrarlı diyot testi |
| `/api/nozzle/status` | GET | Nozzle durumu |
| `/api/nozzle/config` | GET/POST | Nozzle ayarları |

### Senaryo
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/scenarios` | GET/POST | Senaryo listele/kaydet |
| `/api/scenarios/<name>` | DELETE | Senaryo sil |
| `/api/scenarios/run` | POST | Senaryo çalıştır |
| `/api/scenarios/stop` | POST | Senaryoyu durdur |
| `/api/master_scenarios` | GET/POST | Master senaryo listele/kaydet |
| `/api/master_scenarios/run` | POST | Master senaryo çalıştır |

### Doğrulama
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/verification/config` | GET/POST | Doğrulama ayarları |
| `/api/verification/run` | POST | Doğrulama çalıştır |

### Yapılandırma
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/config` | GET/POST | Sistem konfigürasyonu |
| `/api/calibration` | POST | Kalibrasyon kaydet |

### Socket.IO Event'leri

| Event | Yön | Açıklama |
|-------|-----|----------|
| `status_update` | Server→Client | Motor, kamera, OCR durumu |
| `motor_update` | Server→Client | Motor pozisyon güncellemesi |
| `scenario_update` | Server→Client | Senaryo ilerleme durumu |
| `scenario_test_result` | Server→Client | Ölçüm sonucu (direnç/diyot) |
| `auto_center_update` | Server→Client | Merkezleme durumu |
| `verification_update` | Server→Client | Doğrulama sonuçları |
| `nozzle_status` | Server→Client | Nozzle durum güncellemesi |
| `log_message` | Server→Client | Konsol log mesajları |
| `error_toast` | Server→Client | Hata bildirimleri |

---

## 🔧 Donanım Gereksinimleri

| Bileşen | Model/Özellik |
|---------|---------------|
| 🖥️ **Bilgisayar** | Raspberry Pi 4/5 (4GB+ RAM önerilen) |
| 📷 **Kamera** | Raspberry Pi Camera Module 3 |
| ⚙️ **CNC Kontrolcü** | GRBL uyumlu kart (Arduino Uno/Mega) |
| 🔧 **Nozzle Kontrolcü** | Arduino (Slave) — Step motor sürücü |
| 🔌 **Step Motor** | NEMA 17 veya benzeri (nozzle için) |
| 💨 **Vakum Pompası** | 12V/24V vakum pompası + röle |
| 🔘 **Limit Switch** | Nozzle homing için mekanik switch |
| 📏 **ADC** | Arduino analog giriş (direnç/diyot ölçümü) |

### Bağlantı Şeması

```
Raspberry Pi
  ├── USB → Arduino (GRBL CNC) — Motor X, Y, Z + Pompa
  ├── USB → Arduino (Slave)    — Nozzle Step Motor + ADC + Limit Switch
  └── CSI → RPi Camera Module 3
```

---

## ⚙️ Yapılandırma

Uygulama tüm ayarlarını JSON dosyalarında saklar. Web arayüzünden yapılan tüm değişiklikler **otomatik olarak kaydedilir**.

### Yapılandırma Dosyaları

| Dosya | Açıklama |
|-------|----------|
| `config.json` | Motor, kamera, OCR, kalibrasyon ayarları |
| `bases.json` | Kayıtlı konumlar (Base Positions) |
| `scenarios.json` | Standart senaryo tanımları |
| `master_scenarios.json` | Master senaryo tanımları |
| `verification.json` | Doğrulama bileşen listesi ve ayarları |

---

## 📁 Proje Yapısı

```
ele495/
├── app.py                  # Ana Flask sunucu — GRBL sürücü, Nozzle kontrolcü,
│                           # Kamera yöneticisi, OCR, Senaryo motoru, REST API
├── pi_controller.py        # Raspberry Pi kontrolcü (yardımcı modül)
├── arduino_stepper.ino     # Arduino Slave firmware (step motor, ADC, limit switch)
├── templates/
│   ├── index.html          # Ana web arayüzü (tek sayfa uygulama — 7 sekme)
│   └── login.html          # Giriş sayfası
├── static/
│   ├── app.js              # Frontend JavaScript (Socket.IO, UI mantığı)
│   └── style.css           # CSS stil dosyası (dark/light tema)
├── config.json             # Sistem yapılandırması
├── bases.json              # Kayıtlı konumlar
├── scenarios.json          # Senaryo tanımları
├── master_scenarios.json   # Master senaryo tanımları
├── verification.json       # Doğrulama ayarları
├── requirements.txt        # Python bağımlılıkları
├── .gitignore              # Git ignore kuralları
└── README.md               # Bu dosya
```

---

## 🤝 Katkıda Bulunma

1. Bu repoyu fork edin
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Branch'e push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request açın

---

## 👨‍💻 Ekip Üyeleri

- Şahin Yalgun
- Egemen Çorbacı
- Mustafa Anıl Işık
- Aydın Eralp Sırmalı

**ELE495 Bitirme Projesi — Bitirici Ekip**

---

## 📄 Lisans

Bu proje **ELE495 Elektronik Mühendisliği Bitirme Projesi** kapsamında geliştirilmiştir.

© 2026 Bitirici Ekip — Tüm hakları saklıdır.
