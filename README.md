# 🏭 PNP Control Center v2.0

**Pick and Place (PNP) makinesi için geliştirilmiş profesyonel web tabanlı kontrol merkezi.**

> Raspberry Pi üzerinde çalışan, Flask + Socket.IO altyapısıyla gerçek zamanlı makine kontrolü, kamera izleme, OCR tabanlı otomasyon ve nozzle yönetimi sunan kapsamlı bir endüstriyel kontrol sistemi.

---

## 📋 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Sayfa ve Sekmeler](#-sayfa-ve-sekmeler)
- [API Referansı](#-api-referansı)
- [Donanım Gereksinimleri](#-donanım-gereksinimleri)
- [Yapılandırma](#-yapılandırma)
- [Lisans](#-lisans)

---

## 🔍 Genel Bakış

PNP Control Center, bir Pick and Place makinesinin tüm bileşenlerini (CNC motorları, vakum pompası, kamera, OCR, nozzle step motor, direnç/diyot ölçümü) tek bir web arayüzünden yönetmeyi sağlayan entegre bir kontrol sistemidir.

### Temel Yetenekler

| Alan | Açıklama |
|------|----------|
| **Motor Kontrol** | GRBL tabanlı 3 eksen (X, Y, Z) CNC motor kontrolü |
| **Kamera & OCR** | Gerçek zamanlı görüntü akışı, Tesseract OCR ile metin tanıma |
| **Nozzle Sistemi** | Step motor ile hassas açı kontrolü, direnç ve diyot ölçümü |
| **Senaryo Motoru** | Çoklu adım senaryoları ile tam otomasyon |
| **Doğrulama** | Bileşen yerleşim doğrulaması (OCR tabanlı) |

---

## ✨ Özellikler

### 🎮 Motor Kontrol
- **3 Eksen Hareket**: X, Y, Z eksenlerinde hassas konumlandırma
- **Jog Kontrolleri**: Ayarlanabilir adım boyutlarıyla (0.1mm - 10mm) manuel hareket
- **Homing Döngüsü**: Otomatik referans alma, bağlantı kurulduğunda otomatik home
- **Konum Kayıt**: Sınırsız sayıda kayıtlı konum (Base Position) tanımlama
- **Hızlı Konuma Git**: Tek tuşla kayıtlı konumlara atlama
- **G-code Konsolu**: Doğrudan G-code komutu gönderme

### 📷 Kamera Sistemi
- **Canlı Yayın**: MJPEG formatında gerçek zamanlı kamera görüntüsü
- **Çözünürlük Ayarları**: Yakalama ve yayın çözünürlükleri bağımsız ayarlanabilir (640x480 - 1920x1080)
- **PIP Zoom**: Çapraz imlecin olduğu noktada 1x-10x büyütme özelliği (Picture-in-Picture)
- **FPS Monitörü**: Kamera ve OCR FPS değerleri anlık gösterim

### 🔤 OCR (Optik Karakter Tanıma)
- **Tesseract Entegrasyonu**: Gerçek zamanlı metin tanıma
- **Bounding Box Görselleştirme**: Algılanan metnin etrafında dinamik çerçeveler
- **Stabilizasyon**: Çerçeve boyut sınırlaması (1.5x büyüme limiti) ile titreşim önleme
- **Otomatik Merkezleme**: Hedef kelimeyi tespit edip makineyi o konuma otomatik hareket ettirme
- **Beyaz Liste**: Yalnızca tanımlı büyük harf karakterleri algılama

### 🔄 Nozzle Kontrol Sistemi
- **Step Motor Kontrolü**: Hassas açı kontrolü (0-360°) 
- **Homing**: Limit switch ile otomatik referans alma
- **Hızlı Döndürme**: ±15°, ±45°, ±90°, ±180° preset butonları
- **Direnç Ölçümü**: Anlık ve tekrarlı (10 ölçüm) direnç testi
  - ADC değeri, voltaj, direnç hesaplama
  - Min, Max, Standart Sapma istatistikleri
  - Ölçüm bazında detaylı tablo
- **Diyot Testi**: Anlık ve tekrarlı (10 ölçüm) akım geçiş testi
  - Çoğunluk kararı (pass/fail)
  - Otomatik düzeltme (180° döndürme)
  - ADC istatistikleri ve ölçüm tablosu
- **Hızlı Ölçüm**: Ana kontrol ekranında tek tuşla direnç/diyot okuma
- **Otomatik Durum Takibi**: Sayfa açıldığında nozzle durumu otomatik kontrol

### 📋 Senaryo Sistemi
- **Çoklu Adım Tipleri**:
  - `goto_base` — Kayıtlı konuma git
  - `auto_center` — Kelimeye otomatik merkezle (OCR)
  - `pump_on / pump_off` — Vakum pompası kontrolü
  - `delay` — Bekleme süresi
  - `move_z` — Z ekseni hareketi
  - `home` — Home pozisyonuna git
  - `verify` — Doğrulama kontrolü
  - `resistance_test` — Tekrarlı direnç testi
  - `diode_test` — Tekrarlı diyot testi
  - `nozzle_goto` — Nozzle'ı belirli açıya döndür (0-180°)
  - `nozzle_home` — Nozzle home
- **Senaryo Kopyalama**: Mevcut senaryoları tek tuşla çoğaltma
- **Master Senaryo**: Birden fazla senaryoyu sıralı çalıştırma
- **Gerçek Zamanlı İlerleme**: Her adımın durumu canlı gösterim

### ✅ Doğrulama Sistemi
- **OCR Tabanlı Doğrulama**: Bileşen etiketlerini kamera ile okuyup doğrulama
- **Eşik Değeri Ayarı**: Tesseract güven eşiği özelleştirme
- **Sonuç Gösterimi**: Her bileşen için PASS/FAIL durumu
- **HUD Entegrasyonu**: Sonuçlar ana ekranda kamera üstünde gösterim

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
                              └─────────────┘
```

---

## 🛠 Kurulum

### Ön Gereksinimler

- Raspberry Pi 4/5 (önerilen)
- Python 3.11+
- Raspberry Pi Camera Module 3
- GRBL uyumlu CNC kontrol kartı
- Arduino (Nozzle slave kontrolcü)

### Kurulum Adımları

```bash
# 1. Repoyu klonla
git clone https://github.com/bitirici-ekip/ele495.git
cd ele495

# 2. Sanal ortam oluştur ve aktifleştir
python3 -m venv venv
source venv/bin/activate

# 3. Bağımlılıkları yükle
pip install flask flask-socketio opencv-python-headless numpy

# 4. Tesseract OCR'ı yükle
sudo apt install tesseract-ocr tesseract-ocr-eng

# 5. Uygulamayı başlat
python app.py
```

Uygulama varsayılan olarak `http://0.0.0.0:5000` adresinde çalışır.

---

## 🖥 Kullanım

Tarayıcınızdan `http://<raspberry-pi-ip>:5000` adresine gidin.

### İlk Kullanım
1. **Motor Bağlantısı**: Seri port alanına GRBL cihazın portunu girin ve bağlanın
2. **Home Döngüsü**: Bağlantı kurulduğunda otomatik home yapılır
3. **Nozzle Bağlantısı**: Nozzle sekmesinden slave Arduino'ya bağlanın
4. **Konum Kaydetme**: İstenen konumlara gidin ve kaydedin

---

## 📑 Sayfa ve Sekmeler

### 🎮 Kontrol Sekmesi (Ana Sayfa)

Ana kontrol merkezi. Ekran 3 sütunlu düzende organize edilmiştir:

**Sol Panel:**
- Motor bağlantı durumu ve port ayarı
- GRBL durum göstergesi (Idle, Run, Alarm vb.)
- Jog kontrolleri (X/Y/Z eksenleri, ayarlanabilir adım boyutu)
- Pompa kontrolü (ON/OFF)
- Konum kaydetme/silme
- **Hızlı Konuma Git**: Dropdown ile kayıtlı konuma tek tuşla atlama
- **Hızlı Ölçüm**: Direnç ve Diyot butonları — sonuçlar kamera altında gösterilir
- G-code konsolu

**Orta Panel (Kamera):**
- Canlı kamera görüntüsü (MJPEG stream)
- OCR bounding box overlay
- PIP zoom slider (1x-10x büyütme)
- Çözünürlük ayarları (yakalama + yayın ayrı ayrı)
- FPS monitörü (Kamera + OCR)
- Doğrulama sonuçları HUD (kamera üstü)
- Hızlı ölçüm sonuçları (kamera altı)

**Sağ Panel:**
- Gerçek zamanlı X/Y/Z koordinatları
- Aksiyon butonları (Home, Unlock, Sunucu Kapat)
- Kayıtlı konumlar listesi (düzenle/sil/git)

---

### 📋 Senaryolar Sekmesi

Otomasyon senaryolarını oluşturma, düzenleme ve çalıştırma:

- **Senaryo Oluşturucu**: Ad verin, adımları ekleyin, kaydedin
- **Adım Tipleri**: 12 farklı adım tipi (konum, OCR, pompa, nozzle, delay, vb.)
- **Sürükle-Bırak**: Adımları yeniden sırala
- **Düzenleme**: Mevcut adımları düzenle veya sil
- **Senaryo Kopyalama**: Mevcut senaryoyu çoğalt
- **Master Senaryo**: Birden fazla senaryoyu sıralı çalıştır
- **Canlı İlerleme**: Çalışan senaryonun her adımı gerçek zamanlı izle

---

### 🔄 Nozzle Sekmesi

3 sütunlu profesyonel dashboard tasarımı:

**Sol Sütun — Bağlantı & Motor:**
- Seri port bağlantısı (bağlan/kopar)
- Otomatik durum kontrolü (sayfa açıldığında)
- Büyük açı göstergesi (animasyonlu gradient arkaplan)
- Home butonu
- Hedef açı girişi ve GİT butonu
- Hızlı döndürme butonları (±15°, ±45°, ±90°, ±180°)

**Orta Sütun — Ölçümler:**
- **Direnç Ölçümü**:
  - Anlık ölçüm (ADC, voltaj, direnç, durum)
  - Tekrarlı test (10 ölçüm): Canlı ilerleme dotları
  - Detaylı sonuç tablosu (her ölçüm satır satır)
  - İstatistik paneli (Min, Max, Std Sapma, Geçerli sayısı)
- **Diyot Testi**:
  - Anlık test (ADC, eşik karşılaştırma)
  - Tekrarlı test (10 ölçüm): Çoğunluk kararı
  - Otomatik düzeltme (başarısız → 180° döndür → tekrar test)
  - ADC istatistikleri ve ölçüm tablosu

**Sağ Sütun — Ayarlar (her zaman görünür):**
- Motor parametreleri (adım/devir, mikro adımlama, min/max açı)
- Hız ayarları (normal, homing, ivme)
- Pin yapılandırması (limit switch, analog pin, yön)
- Ölçüm parametreleri (bilinen R, ADC örnekleme, diyot eşiği, test sayısı/aralığı)

---

### ✅ Doğrulama Sekmesi

Bileşen yerleşim doğrulaması:

- Bileşen listesi tanımlama (isim + beklenen değer)
- Eşik değeri ayarlama (Tesseract güven skoru)
- Eşik değeri önizleme (kamera üstünde canlı)
- Doğrulama çalıştırma ve sonuç gösterimi
- Her bileşen için PASS ✅ / FAIL ❌ durumu

---

### ⚙️ Ayarlar Sekmesi

Sistem yapılandırması:

- **Motor Kalibrasyon**: Adım/mm oranları (X, Y, Z), hız, ivme
- **OCR Ayarları**: Güven eşiği, dil, PSM modu, bounding box parametreleri
- **OCR İzleme**: Gerçek zamanlı OCR performans metrikleri
- **Sistem**: Genel sistem ayarları

---

## 🔌 API Referansı

### Motor Kontrol
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/motor/connect` | POST | Motor bağlantısı |
| `/api/motor/disconnect` | POST | Motor bağlantısını kes |
| `/api/motor/move` | POST | Eksen hareketi |
| `/api/motor/home` | POST | Homing döngüsü |
| `/api/motor/unlock` | POST | GRBL kilidi aç |

### Kamera
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/video_feed` | GET | MJPEG video akışı |
| `/api/camera/resolution` | POST | Çözünürlük ayarla |

### Nozzle
| Endpoint | Yöntem | Açıklama |
|----------|--------|----------|
| `/api/nozzle/connect` | POST | Nozzle Arduino bağlantısı |
| `/api/nozzle/disconnect` | POST | Bağlantıyı kes |
| `/api/nozzle/home` | POST | Nozzle homing |
| `/api/nozzle/goto` | POST | Belirli açıya git |
| `/api/nozzle/move_relative` | POST | Bağıl hareket |
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
| `/api/scenarios/run` | POST | Senaryo çalıştır |
| `/api/scenarios/stop` | POST | Senaryoyu durdur |

---

## 🔧 Donanım Gereksinimleri

| Bileşen | Model/Özellik |
|---------|---------------|
| **Bilgisayar** | Raspberry Pi 4/5 (4GB+ RAM önerilen) |
| **Kamera** | Raspberry Pi Camera Module 3 |
| **CNC Kontrolcü** | GRBL uyumlu kart (Arduino Uno/Mega) |
| **Nozzle Kontrolcü** | Arduino (Slave) — Step motor sürücü |
| **Step Motor** | NEMA 17 veya benzeri (nozzle için) |
| **Vakum Pompası** | 12V/24V vakum pompası + röle |
| **Limit Switch** | Nozzle homing için mekanik switch |

---

## ⚙️ Yapılandırma

Uygulama tüm ayarlarını `config.json` ve `nozzle_config.json` dosyalarında saklar. Web arayüzünden yapılan tüm değişiklikler otomatik olarak kaydedilir.

### Önemli Yapılandırma Dosyaları

| Dosya | Açıklama |
|-------|----------|
| `config.json` | Motor, kamera, OCR, senaryo ayarları |
| `nozzle_config.json` | Nozzle motor, pin, ölçüm ayarları |
| `app.py` | Ana uygulama sunucusu |
| `static/app.js` | Frontend JavaScript mantığı |
| `templates/index.html` | Web arayüzü şablonu |

---

## 📁 Proje Yapısı

```
ele495/
├── app.py                  # Flask sunucu, GRBL sürücü, Nozzle kontrolcü, OCR
├── templates/
│   └── index.html          # Web arayüzü (tek sayfa uygulama)
├── static/
│   └── app.js              # Frontend JavaScript
├── config.json             # Sistem yapılandırması
├── nozzle_config.json      # Nozzle yapılandırması
├── requirements.txt        # Python bağımlılıkları
└── README.md               # Bu dosya
```

---

## 👨‍💻 Yazar

**Şahin Yalgun**

---

## 📄 Lisans

Bu proje ELE495 dersi kapsamında geliştirilmiştir.

© 2026 Şahin Yalgun — Tüm hakları saklıdır.
