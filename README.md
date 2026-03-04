<![CDATA[<div align="center">

# 🏭 PNP Kontrol Merkezi

### Pick & Place CNC Makine Kontrol Sistemi — v2.0

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-SocketIO-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Arduino](https://img.shields.io/badge/Arduino-Firmware-00979D?style=for-the-badge&logo=arduino&logoColor=white)](https://arduino.cc)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Picamera2-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com)
[![GRBL](https://img.shields.io/badge/GRBL-CNC%20Controller-FF6B35?style=for-the-badge)](https://github.com/gnea/grbl)
[![License](https://img.shields.io/badge/ELE495-Bitirme%20Projesi-gold?style=for-the-badge)](https://github.com/bitirici-ekip/ele495)

---

**Raspberry Pi üzerinde çalışan, GRBL tabanlı CNC motor kontrolü, OCR yazı algılama, vakum nozzle sistemi, direnç/diyot ölçümü ve otomatik senaryo çalıştırma özelliklerine sahip profesyonel bir Pick & Place kontrol sistemidir.**

[🚀 Kurulum](#-kurulum) • [📖 Özellikler](#-özellikler) • [🌐 Web Arayüzü](#-web-arayüzü-sayfaları) • [🔌 Donanım](#-donanım-mimarisi) • [📡 API](#-api-referansı) • [⌨️ Kısayollar](#️-klavye-kısayolları)

</div>

---

## 📋 İçindekiler

- [🚀 Kurulum](#-kurulum)
- [📖 Özellikler](#-özellikler)
- [🌐 Web Arayüzü Sayfaları](#-web-arayüzü-sayfaları)
  - [🎮 Kontrol Paneli](#-1-kontrol-paneli)
  - [🔧 Kalibrasyon](#-2-kalibrasyon)
  - [⚙️ Ayarlar](#%EF%B8%8F-3-ayarlar)
  - [📍 Konumlar](#-4-konumlar-bases)
  - [🎬 Senaryolar](#-5-senaryolar)
  - [🔧 Nozzle](#-6-nozzle-kontrolü)
  - [👁️ Doğrulama](#%EF%B8%8F-7-doğrulama-verification)
- [🔌 Donanım Mimarisi](#-donanım-mimarisi)
- [📡 API Referansı](#-api-referansı)
- [⌨️ Klavye Kısayolları](#️-klavye-kısayolları)
- [📂 Proje Yapısı](#-proje-yapısı)
- [🔧 Konfigürasyon](#-konfigürasyon)
- [🤝 Katkıda Bulunma](#-katkıda-bulunma)

---

## 🚀 Kurulum

### Gereksinimler

| Bileşen | Gereksinim |
|---------|-----------|
| **İşletim Sistemi** | Raspberry Pi OS (64-bit önerilir) |
| **Python** | 3.9 veya üstü |
| **Kamera** | Raspberry Pi Camera Module (Picamera2 uyumlu) |
| **CNC Kontrol** | GRBL firmware yüklü Arduino (Uno/Nano) |
| **Nozzle** | Stepper motor kontrollü Arduino (Slave firmware) |
| **OCR** | Tesseract OCR (tesserocr Python binding) |

### Adım Adım Kurulum

```bash
# 1. Repoyu klonlayın
git clone https://github.com/bitirici-ekip/ele495.git
cd ele495

# 2. Virtual environment oluşturun
python3 -m venv venv
source venv/bin/activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Tesseract OCR'ı yükleyin (Raspberry Pi OS)
sudo apt install tesseract-ocr libtesseract-dev libleptonica-dev

# 5. Arduino Slave firmware'ini yükleyin
# arduino_stepper.ino dosyasını Nozzle Arduino'ya yükleyin (Arduino IDE ile)
# ⚠️ DİKKAT: Bu firmware GRBL Arduino'ya DEĞİL, Slave Arduino'ya yüklenmelidir!

# 6. Uygulamayı başlatın
python app.py
```

### Uygulamaya Erişim

Sunucu başlatıldıktan sonra tarayıcınızdan erişin:

```
http://<raspberry-pi-ip>:5000
```

> **Not:** Varsayılan kullanıcı adı/şifre: `admin` / `admin` (Kimlik doğrulama şu anda devre dışıdır)

---

## 📖 Özellikler

### 🎯 Çekirdek Özellikler

| Özellik | Açıklama |
|---------|---------|
| **GRBL Motor Kontrolü** | 3 eksenli (X, Y, Z) CNC motor kontrolü, otomatik port algılama |
| **Canlı Kamera Yayını** | MJPEG üzerinden gerçek zamanlı kamera görüntüsü, PIP zoom desteği |
| **OCR Yazı Algılama** | Tesseract tabanlı gerçek zamanlı yazı tanıma, IoU stabilizasyon |
| **Otomatik Merkezleme** | 4 aşamalı akıllı merkezleme algoritması (kaba → hassas → doğrulama) |
| **Vakum Pompası** | Pick & Place işlemi için kontrol edilebilir vakum sistemi |
| **Nozzle Rotasyon** | Stepper motor ile hassas açı kontrolü, limit switch homing |
| **Direnç Ölçümü** | Voltaj bölücü devresi ile ADC tabanlı direnç ölçümü |
| **Diyot Testi** | Akım akışı yönü tespiti, otomatik 180° düzeltme |
| **Senaryo Sistemi** | Çok adımlı otomasyon senaryoları, koşullu mantık (IF blokları) |
| **Master Senaryolar** | Birden fazla senaryoyu zincirleyerek sıralı çalıştırma |
| **Doğrulama (Verification)** | ROI tabanlı binary threshold analizi ile PCB kontrol |
| **Kalibrasyon Sihirbazı** | Motor-kamera yön eşleştirme ve piksel/mm oranı hesaplama |

### 🔄 Gerçek Zamanlı İletişim

Sistem, **Flask-SocketIO** üzerinden tam çift yönlü WebSocket iletişimi sağlar:

- 📊 Anlık durum güncellemeleri (pozisyon, GRBL durumu, FPS)
- 📋 Konsol log mesajları
- ⚡ OCR algılama sonuçları
- 🎯 Auto-center ilerleme bildirileri
- 🔬 Ölçüm sonuçları
- 🎬 Senaryo durumu ve test sonuçları
- 🔔 Hata bildirimleri (toast mesajlar)

---

## 🌐 Web Arayüzü Sayfaları

Sistem, **7 ana sekme** ile profesyonel bir tek sayfa web arayüzü sunar. Header'da tüm sekmeler arası geçiş yapılabilir. Header ayrıca motor bağlantı durumu, GRBL state göstergesi (Idle/Run/Home/Alarm), sistem çalışma süresi ve tema değiştirici içerir.

---

### 🎮 1. Kontrol Paneli

Ana çalışma ekranıdır. Üç sütunlu bir düzene sahiptir.

#### Sol Sütun — Hızlı Aksiyonlar

| Panel | Açıklama |
|-------|---------|
| **🎬 Hızlı Senaryo** | Dropdown ile senaryo seç ve tek tıkla çalıştır. Master senaryo desteği. Durdur butonu. |
| **🎯 Hızlı Merkez** | Hedef kelimeyi yaz veya listelenmiş kısayollardan (TEST, CRB, SHN, AYD, MUS) seçerek merkezle |
| **📍 Hızlı Konum** | Kayıtlı konumlardan seç ve "GİT" ile makineyi o konuma taşı |
| **🔬 Hızlı Ölçüm** | Tek tıkla direnç ölçümü veya diyot testi yap (sonuç kamera altında gösterilir) |
| **📋 Konsol** | Gerçek zamanlı log mesajları, G-code komut girişi (manuel GRBL kontrol) |

#### Orta Sütun — Canlı Kamera

- **MJPEG canlı yayın** — OCR kutuları ve crosshair ile annotated görüntü
- **PIP Zoom** — Kaydırılabilir zoom (1x – 10x), görüntü merkezinde büyütme penceresi
- **CAM/OCR FPS** — Kamera ve OCR işleme hız göstergesi
- **LIVE badge** — Canlı yayın göstergesi
- **Kamera ayarları** — Yakalama (OCR) ve yayın (ekran) çözünürlüğü presetleri
- **Doğrulama HUD** — Son doğrulama sonuçlarını kamera üstünde gösterir
- **Test Sonuç Banner** — Senaryo testlerinde büyük PASS/FAIL animasyonu

#### Sağ Sütun — Kontrol Panelleri

| Panel | Açıklama |
|-------|---------|
| **📍 Pozisyon** | X, Y, Z koordinatlarını gerçek zamanlı gösterir (mm cinsinden) |
| **⚡ Aksiyonlar** | Pompa AÇ/KAPAT, GRBL Unlock, Reset, Sunucu Kapatma |
| **🎮 Motor Kontrolü** | 8 yönlü XY hareket tuşları (↖↑↗◀HOME▶↙▼↘), Z tuşları (▲▼), adım boyutu seçici (0.1–50mm), mutlak Z hareketi |

---

### 🔧 2. Kalibrasyon

Motor hareket yönü ile kamera eksen yönünü eşleştiren interaktif kalibrasyon sihirbazıdır.

#### Kalibrasyon Adımları

1. **Motor & Yön Testleri** — Motor X+ ve Y+ yönüne hareket ettirilir. Kullanıcı ekrandaki hareket yönünü seçer (yukarı/aşağı/sol/sağ butonları)
2. **Algoritma Sonucu** — Eksen swap, X ters-çevirme ve Y ters-çevirme otomatik hesaplanır
3. **Piksel/mm Oranı** — X ve Y katsayıları otomatik hesaplanır ve gösterilir

#### Gelişmiş Seçenekler

- **Test Adımı Boyutu** — mm veya piksel cinsinden ayarlanabilir
- **Manuel Eksen Ayarı** — Otomatik algoritmaya güvenmeyenler için swap ve negate seçenekleri
- **Kalibrasyon Kaydetme** — Tüm ayarlar `config.json` dosyasına kaydedilebilir

---

### ⚙️ 3. Ayarlar

Sistem konfigürasyonlarının yönetildiği detaylı ayarlar sayfasıdır. Grid düzeninde 4 kart içerir:

#### Motor & Kalibrasyon
- Piksel → mm dönüşüm katsayıları (X, Y)
- Hedef nokta (piksel koordinatları)
- Feed Rate (mm/dk)
- Tolerans (px) ve maksimum iterasyon
- X/Y eksen yön invertleme

#### OCR Ayarları
- **Güven Eşiği** — Algılama filtresi (slider: 10–100)
- **PSM Modu** — SINGLE_BLOCK (6), SPARSE_TEXT (11), AUTO (3)
- **Whitelist** — Algılanacak karakter seti
- **Min. Kelime** — Minimum kelime uzunluğu filtresi
- **Kutu Büyüme** — OCR kutularının büyüme limiti
- **Otomatik Home** — Açılışta home yapılıp yapılmayacağı

#### OCR İzleme
- Algılanan kelime sayısı
- Hedef kelime durumu
- Algılanan kelimeler listesi
- Hata logu

#### Sistem Bilgisi
- Motor port, durum, kamera, GRBL state, çalışma süresi
- Klavye kısayolları referansı (⬆⬇⬅➡ Motor, H Home, C Center, E Kapat)

---

### 📍 4. Konumlar (Bases)

Sık kullanılan makine koordinatlarını kaydetme ve yönetme sayfasıdır.

#### Yeni Konum Ekle
- **Konum Adı** — Tanımlayıcı isim (örn: Home, Pick1, Place1)
- **X, Y, Z koordinatları** — Manuel giriş veya "Mevcut Konumu Çek" butonu ile otomatik doldurma
- **Kaydet** — Konumları `bases.json` dosyasına yazar

#### Kayıtlı Konumlar Listesi
- Tüm konumlar kartlar halinde gösterilir
- **GİT** — Akıllı Z sıralaması ile güvenli konum geçişi (önce Z yukarı → XY hareket → Z aşağı)
- **Sil** — Konumu kaldır
- Senaryolarda ve hızlı konum panelinde referans olarak kullanılır

---

### 🎬 5. Senaryolar

Otomatik iş akışları oluşturma ve yönetme sayfasıdır. İki bölümden oluşur:

#### Standart Senaryolar (Sol Taraf)

Adım adım otomasyon akışları oluşturmanıza olanak tanır:

| Adım Tipi | Açıklama |
|-----------|---------|
| 📍 **Konuma Git** | Kayıtlı bir konuma hareket et |
| 🎯 **Kelimeye Merkezle** | OCR ile hedef kelimeyi bul ve merkezle |
| 👁️ **Doğruluk Kontrolü** | ROI tabanlı doğrulama çalıştır |
| 💨 **Pompa AÇ** | Vakum pompasını aktifleştir |
| 🛑 **Pompa KAPAT** | Vakum pompasını deaktif et |
| ⏳ **Bekle** | Belirtilen süre kadar bekle (saniye) |
| ↕️ **Z Konumuna Git** | Mutlak Z hareketi |
| 🏠 **Home** | Ana makine homing |
| 🔬 **Direnç Ölç (Anlık)** | Tek seferlik direnç ölçümü |
| 💡 **Diyot Test Et (Anlık)** | Tek seferlik diyot testi |
| 🔬 **Direnç Testi** | Tekrarlı direnç testi (istatistik) |
| 💡 **Diyot Testi** | Tekrarlı diyot testi (çoğunluk kararı) |
| 🔄 **Nozzle Açıya Git** | Nozzle'ı belirtilen açıya döndür |
| 🏠 **Nozzle Home** | Nozzle homing |
| 🔬 **IF Direnç Koşulu** | Direnç ölçüm sonucuna göre koşullu dallanma (PASS/FAIL adımları) |
| 💡 **IF Diyot Koşulu** | Diyot test sonucuna göre koşullu dallanma (PASS/FAIL adımları) |

#### IF Blokları (Koşullu Mantık)
- **IF Direnç** — Hedef direnç değeri ve tolerans aralığı belirlenebilir. Ölçüm tolerans içindeyse PASS adımları, değilse FAIL adımları çalışır
- **IF Diyot** — Akım geçip geçmediğine göre dallanma. Otomatik 180° düzeltme seçenegi
- PASS ve FAIL blokları içinde scroll butonları ile adım sıralama desteği

#### Master Senaryolar (Sağ Taraf)

Birden fazla standart senaryoyu sıralı olarak çalıştırır:
- Senaryo sırasını düzenle (yukarı/aşağı)
- Tek tıkla tüm zinciri başlat
- Üretim hattı otomasyonu için ideal

---

### 🔧 6. Nozzle Kontrolü

Slave Arduino üzerinden nozzle step motor ve ölçüm yönetimi. Üç sütunlu dashboard düzeni.

#### Sol Sütun — Bağlantı & Motor

| Panel | Açıklama |
|-------|---------|
| **🔌 Bağlantı** | Port seçimi, bağlan/kopar butonları, bağlantı durumu göstergesi |
| **🔄 Motor Kontrol** | Büyük açı göstergesi (animasyonlu), Home butonu, hedef açıya git, hızlı döndürme butonları (-180° ile +180° arasında preset'ler) |

#### Orta Sütun — Ölçümler

| Panel | Açıklama |
|-------|---------|
| **🔬 Direnç Ölçümü** | Anlık direnç ölçümü (ADC, voltaj, Ω göstergesi), 10 ölçümlük tekrarlı test (istatistiksel sonuç), ilerleme noktaları |
| **💡 Diyot Testi** | Anlık diyot test (akım geçiyor/geçmiyor), 10 ölçümlük tekrarlı test (6/10 çoğunluk kararı), otomatik 180° düzeltme seçeneği |

#### Sağ Sütun — Ayarlar

Tüm nozzle parametreleri yapılandırılabilir:
- **Motor:** Adım/devir, mikro adımlama (1-16x), min/max açı limitleri
- **Hız:** Normal hız, homing hızı, ivme adımı ve başlangıç hızı (µs cinsinden)
- **Pinler:** Limit switch, analog pin, homing yönü, geri yön
- **Ölçüm:** Bilinen R (Ω), ADC örnekleme sayısı, diyot eşik değeri, test sayısı, test aralığı

---

### 👁️ 7. Doğrulama (Verification)

PCB üzerindeki bileşen varlığını binary threshold analizi ile doğrulayan sayfa. Üç sütunlu düzen.

#### Sol Sütun — Ayarlar & ROI Kutuları
- **Konum seçici** — Doğrulama yapılacak kayıtlı konuma git
- **Threshold (Eşik)** — Binary threshold değeri (0–255 slider)
- **Gösterim Eşiği** — Bu yüzdenin altındaki değerler "BOŞ" olarak gösterilir
- **Kutu Editörü** — ROI kutuları ekleme, silme, boyut/konum düzenleme

#### Orta Sütun — Kamera & Kutu Çizim
- Temiz (annotasyonsuz) kamera görüntüsü
- Sürükle-bırak ile ROI kutusu konumlandırma
- Boyutlandırma tutamakları

#### Sağ Sütun — Sonuçlar & Önizleme
- **Sonuçlar paneli** — Her kutunun doluluk yüzdesi
- **Threshold önizleme** — Binary threshold uygulanmış görüntü
- Her kutu için ayrı threshold görüntüsü base64 olarak gönderilir

---

## 🔌 Donanım Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi (Ana Bilgisayar)             │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  Flask Web   │  │  Picamera2   │  │  Tesseract OCR     │  │
│  │  Sunucusu    │  │  Kamera      │  │  Yazı Algılama     │  │
│  │  (SocketIO)  │  │  Modülü      │  │                    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘  │
│         │                 │                    │              │
│         │    USB Seri     │     Frame          │    OCR       │
│    ┌────┴────┐      ┌─────┴──────┐       ┌────┴────┐        │
│    │  GRBL   │      │  MJPEG     │       │  Auto   │        │
│    │ Driver  │      │  Stream    │       │ Center  │        │
│    └────┬────┘      └────────────┘       └─────────┘        │
│         │                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │ USB (/dev/ttyUSB* veya /dev/ttyACM*)
          │
    ┌─────┴──────────────────────────────────────────┐
    │                                                 │
┌───┴───────────┐                          ┌──────────┴──────────┐
│  Arduino #1   │                          │  Arduino #2         │
│  GRBL Firmware│                          │  Slave Firmware     │
│  (CNC Kontrol)│                          │  (arduino_stepper)  │
│               │                          │                     │
│  • X Motoru   │                          │  • Nozzle Stepper   │
│  • Y Motoru   │                          │  • A1: ADC Direnç   │
│  • Z Motoru   │                          │  • D9: Limit Switch │
│  • Pompa Rölesi│                         │                     │
└───────────────┘                          └─────────────────────┘
```

### Port Algılama (Otomatik)

Sistem açılışta tüm USB seri portları tarar:
- **GRBL Arduino** → Bağlanınca `Grbl` banner'ı gönderir
- **Nozzle Arduino** → `SLAVE_READY` veya `PING`→`PONG` yanıtı verir

Port isimleri udev kuralları ile sabitlenebilir (örn: `/dev/arduino_grbl`, `/dev/arduino_slave`).

---

## 📡 API Referansı

### REST Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|---------|
| `GET` | `/` | Ana sayfa (index.html) |
| `GET` | `/video_feed` | MJPEG canlı kamera yayını (annotated) |
| `GET` | `/video_feed_raw` | MJPEG temiz kamera yayını (doğrulama için) |
| `GET` | `/api/status` | Sistem durumu (JSON) |
| `POST` | `/api/move` | Manuel motor hareketi `{"x": float, "y": float}` |
| `POST` | `/api/move_z_absolute` | Mutlak Z hareketi `{"z": float}` |
| `POST` | `/api/home` | Home komutu (tüm eksenleri sıfırla) |
| `POST` | `/api/auto_center` | Otomatik merkezleme `{"target_word": "TEST"}` |
| `POST` | `/api/pump` | Pompa kontrolü `{"state": true/false}` |
| `GET` | `/api/config` | Konfigürasyonu getir |
| `GET/POST` | `/api/bases` | Konumları listele / yeni ekle |
| `DELETE` | `/api/bases/<name>` | Konumu sil |
| `POST` | `/api/goto_base` | Konuma git `{"name": "Pick1"}` |

### SocketIO Olayları

| Olay | Yön | Açıklama |
|------|-----|---------|
| `status_update` | Server → Client | Pozisyon, FPS, OCR verileri |
| `console_log` | Server → Client | Konsol mesajları |
| `connection_status` | Server → Client | Motor/kamera bağlantı durumu |
| `auto_center_status` | Server → Client | Merkezleme ilerleme güncellemesi |
| `scenario_status` | Server → Client | Senaryo çalışma durumu |
| `scenario_test_result` | Server → Client | IF blok test sonucu (PASS/FAIL) |
| `resistance_result` | Server → Client | Anlık direnç ölçüm sonucu |
| `diode_result` | Server → Client | Anlık diyot test sonucu |
| `verification_update` | Server → Client | Doğrulama ilerleme ve sonuçları |
| `grbl_alarm` | Server → Client | GRBL alarm durumu bildirimi |
| `toast` | Server → Client | Hata/uyarı bildirim mesajı |

---

## ⌨️ Klavye Kısayolları

| Tuş | Aksiyon |
|-----|---------|
| `↑` `↓` `←` `→` | Motor XY hareketi |
| `H` | Home (tüm eksenleri sıfırla) |
| `C` | Otomatik merkezleme başlat |
| `E` | Acil durdurma |

---

## 📂 Proje Yapısı

```
ele495/
├── app.py                    # Ana uygulama (Flask + SocketIO sunucu, ~4400 satır)
│                             #   ├── Config — Sistem konfigürasyonu
│                             #   ├── PNPDriver — GRBL motor sürücüsü
│                             #   ├── NozzleController — Nozzle + ölçüm kontrolü
│                             #   ├── CameraManager — Kamera + OCR yönetimi
│                             #   ├── auto_center() — Otomatik merkezleme algoritması
│                             #   ├── run_verification() — Doğrulama motoru
│                             #   ├── run_scenario() — Senaryo çalıştırma motoru
│                             #   └── Flask Routes — REST API & SocketIO handlers
│
├── pi_controller.py          # Raspberry Pi spesifik kontroller (ArduinoSlave, MotorController, vb.)
├── arduino_stepper.ino       # Arduino Slave firmware (Generic Slave mimarisi)
│
├── templates/
│   ├── index.html            # Ana web arayüzü (7 sekmeli SPA, ~1560 satır)
│   └── login.html            # Giriş sayfası
│
├── static/
│   ├── app.js                # Frontend mantığı (SocketIO, UI, senaryolar, ~3000 satır)
│   └── style.css             # Tema, responsive tasarım, animasyonlar
│
├── config.json               # Sistem konfigürasyonu (persisted)
├── bases.json                # Kayıtlı konumlar
├── scenarios.json            # Standart senaryolar
├── master_scenarios.json     # Master senaryolar
├── verification.json         # Doğrulama ayarları ve ROI kutuları
├── requirements.txt          # Python bağımlılıkları
├── .gitignore                # Git ignore kuralları
└── README.md                 # Bu dosya
```

---

## 🔧 Konfigürasyon

Tüm ayarlar `config.json` dosyasında saklanır. Web arayüzünden de düzenlenebilir.

### Önemli Parametreler

```json
{
  "pixel_to_mm_x": 0.02,          // Piksel → mm X katsayısı
  "pixel_to_mm_y": 0.02,          // Piksel → mm Y katsayısı
  "feed_rate": 1000,               // Motor hızı (mm/dk)
  "camera_width": 1920,            // Kamera yakalama genişliği
  "camera_height": 1080,           // Kamera yakalama yüksekliği
  "auto_center_tolerance": 5,      // Merkezleme toleransı (px)
  "auto_center_max_iter": 10,      // Maksimum iterasyon sayısı
  "ocr_confidence": 40,            // OCR güven eşiği
  "ocr_psm_mode": 6,               // Tesseract PSM modu
  "nozzle_known_resistance": 10000, // Voltaj bölücü referans direnci (Ω)
  "nozzle_diode_threshold": 500,    // Diyot ADC eşik değeri
  "nozzle_microstepping": 16        // Mikro adımlama faktörü
}
```

---

## 🔬 Arduino Slave Protokolü

Nozzle Arduino, **Generic Slave** mimarisinde çalışır. Komutlar seri port üzerinden `\n` ile sonlandırılarak gönderilir:

| Komut | Yanıt | Açıklama |
|-------|-------|---------|
| `PING` | `OK:PONG` | Bağlantı testi |
| `STEP <count> <dir> <spd> <acc_s> <acc_st>` | `OK:STEP_DONE` | Adım hareketi |
| `STEPG <count> <dir> <spd> <acc_s> <acc_st> <guard_pin>` | `OK:STEP_DONE` veya `OK:ESTOP` | Korumalı adım (limit switch ile) |
| `AHOME <dir> <back> <spd> <slow> <backoff> <clearance> <pin>` | `OK:HOMED` | Otonom homing |
| `AROTATE <count> <dir> <spd> <acc_s> <acc_st> <pin>` | `OK:DONE` veya `OK:ESTOP` | Otonom dönüş |
| `EN <0\|1>` | `OK` | Motor enable/disable |
| `AREAD <pin>` | `OK:<değer>` | Analog okuma |
| `MULTI_AREAD <pin> <count>` | `OK:<ortalama>` | Çoklu analog okuma (ortalama) |
| `DREAD <pin>` | `OK:<değer>` | Dijital okuma |
| `DWRITE <pin> <val>` | `OK` | Dijital yazma |

---

## 🤝 Katkıda Bulunma

1. Bu repoyu fork edin
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Branch'i push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request açın

---

<div align="center">

### 🎓 ELE495 — Bitirme Projesi

**Bitirici Ekip** tarafından geliştirilmiştir.

---

*Bu proje, Pick & Place CNC makinelerinin web tabanlı kontrolü için açık kaynaklı bir çözüm sunmaktadır.*

</div>
]]>
