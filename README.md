# PNP Machine Control & Camera OCR System

Bu proje, GRBL tabanlı bir Pick and Place (PNP) makinesini kontrol etmek ve entegre kamera sistemi ile gerçek zamanlı Optik Karakter Tanıma (OCR) yapmak için geliştirilmiştir.

## Özellikler

### 1. **PNP Kontrolcü (`main.py`)**
- GRBL uyumlu CNC/Robot kollarını otomatik olarak tanır ve bağlanır.
- G-Code komutlarını senkronize bir şekilde gönderir (Okuma/Yazma teyidi ile).
- Önceden tanımlanmış senaryoları (Al-Götür-Bırak) uygular.
- **Güvenlik Özellikleri**:
  - Pompa açma/kapama işlemlerinde buffer temizliği (`G4 P0`).
  - Hata durumunda otomatik temizlik ve kapanış.
  - Z ekseni güvenlik hareketleri.

### 2. **Kamera & OCR Sistemi (`camera_ocr.py`)**
- **Donanım**: Raspberry Pi Camera Module 3 (IMX708) ile uyumlu `Picamera2` kütüphanesi kullanır.
- **OCR Motoru**: Tesseract 5.0 (C++ API wrapper `tesserocr`) kullanarak yüksek performanslı metin tanıma yapar.
- **Görüntü İşleme**:
  - Görüntüyü otomatik döndürme (90 derece).
  - Gri tonlama (Grayscale) ve Adaptive Thresholding ile metin netleştirme.
  - Titremeyi önleyen (anti-flicker) stabilizasyon algoritması (`STABILITY_DURATION`).
  - Nesne takibi ve eşleştirme logic'i (`IOU_MATCH_THRESHOLD`).

## Kurulum

Bu proje Raspberry Pi (Bookworm OS veya üzeri) üzerinde çalışacak şekilde tasarlanmıştır.

### Sistem Gereksinimleri
Aşağıdaki paketleri terminal üzerinden yükleyin:

```bash
sudo apt update
sudo apt install tesseract-ocr libtesseract-dev libleptonica-dev
sudo apt install python3-libcamera python3-kms++ libcamera-apps
```

### Python Kütüphaneleri
Proje dizininde sanal ortam oluşturup kütüphaneleri yükleyin:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

*Not: `tesserocr` kurulumu sırasında derleme hatası alırsanız sistem paketlerinin tam yüklü olduğundan emin olun.*

## Kullanım

### Tüm Sistemi Başlatma
PNP makinesini ve Kamera sistemini aynı anda başlatmak için:

```bash
python main.py
```
Bu komut:
1. PNP portunu bulur ve bağlanır (`/dev/ttyUSB*` veya `/dev/ttyACM*`).
2. Kamerayı açar ve ekranda canlı görüntü verir.
3. PNP senaryosunu arka planda çalıştırmaya başlar.

### Sadece Kamerayı Test Etme
Sadece görüntü işleme ve OCR performansını görmek için:

```bash
python camera_ocr.py
```
Çıkmak için: `q` tuşuna basın veya pencereyi kapatın.

## Konfigürasyon (`camera_ocr.py`)

Kamera performansını ortam ışığına göre optimize etmek için şu parametreleri düzenleyebilirsiniz:

- **`STABILITY_DURATION`** (Varsayılan: 0.1s): Bir metin tespit edildikten sonra ekranda en az ne kadar kalacağını belirler. Titremeyi önler.
- **`IOU_MATCH_THRESHOLD`** (Varsayılan: 0.4): Ardışık karelerdeki kutuların aynı nesne olup olmadığına karar veren eşik değeridir.

## Proje Yapısı

```
.
├── main.py            # Ana kontrol dosyası (PNP + Kamera Thread)
├── camera_ocr.py      # Görüntü işleme ve OCR modülü
├── requirements.txt   # Python bağımlılıkları
└── README.md          # Proje dokümantasyonu
```

## Lisans
Bu proje ELE495 Bitirme Projesi kapsamında geliştirilmiştir.
