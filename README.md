# ELE495 - Pick & Place Kontrol Arayüzü

Bu proje, ELE495 Bitirme Projesi kapsamında geliştirilmiş, **Raspberry Pi** tabanlı bir **Pick & Place (Dizgi) Makinesi** için kapsamlı bir web kontrol arayüzüdür. Flask, Socket.IO ve OpenCV teknolojileri kullanılarak geliştirilmiştir.

## 🚀 Özellikler

### 1. Web Tabanlı Kontrol Paneli
- **Gerçek Zamanlı Kamera Akışı**: Raspberry Pi Camera Module 3 desteği ile düşük gecikmeli MJPEG yayını.
- **İnteraktif Arayüz**: Modern, duyarlı (responsive) ve kullanıcı dostu tasarım.
- **Motor Kontrolü**: X, Y, Z eksenleri için hassas manuel kontrol ve anlık pozisyon takibi.

### 2. Görüntü İşleme ve OCR (Optik Karakter Tanıma)
- **Tesseract OCR Entegrasyonu**: Kamera görüntüsü üzerindeki metinleri (örneğin parça numaraları) gerçek zamanlı olarak okur.
- **Otomatik Merkezleme (Auto-Center)**: Seçilen bir metni veya bileşeni görüntü işleme algoritmaları kullanarak otomatik olarak kameranın (ve dolayısıyla nozülün) merkezine hizalar.
- **Çok Aşamalı Hizalama**: Kaba ve hassas hizalama algoritmaları ile yüksek doğruluk sağlar.

### 3. Senaryo Yönetimi
- **Senaryo Oluşturucu**: Sürükle-bırak mantığına yakın, adım adım işlem tanımlama (Konuma Git, Merkezle, Pompa Aç/Kapat, Bekle, vb.).
- **Senaryo Düzenleme**: Var olan senaryoları kaydetme, düzenleme ve silme imkanı.
- **Adım Düzenleme**: Eklenmiş adımları sonradan değiştirebilme özelliği.

### 4. Sistem Kontrolü & Güvenlik
- **GRBL Entegrasyonu**: G-Code tabanlı CNC/PnP kontrolcüleriyle tam uyum.
- **Acil Durdurma (E-Stop)**: Yazılımsal acil durdurma ve soft-reset özellikleri.
- **Kilit Açma ($X)**: Alarm durumunda makine kilidini açma fonksiyonu.

## 🛠 Donanım Gereksinimleri

- **Ana Bilgisayar**: Raspberry Pi 4 veya 5 (Tavsiye edilen: 4GB+ RAM)
- **Kamera**: Raspberry Pi Camera Module 3 (Wide veya Standard)
- **Kontrolcü**: GRBL tabanlı CNC Shield veya benzeri kontrol kartı (Arduino Uno/Nano vb.)
- **Mekanik**: CoreXY veya Kartezyen PnP makine şasesi
- **Vakum Pompası**: 5V/12V Röle kontrollü vakum sistemi

## 📦 Kurulum

Proje Python 3 tabanlıdır. Sanal ortam (venv) kullanılması önerilir.

1. **Repoyu Klonlayın:**
   ```bash
   git clone https://github.com/bitirici-ekip/ele495.git
   cd ele495
   ```

2. **Sanal Ortam Oluşturun ve Aktif Edin:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Gerekli Kütüphaneleri Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Not: `tesserocr` ve `picamera2` kurulumları sistem bağımlılıkları gerektirebilir. Detaylar için `requirements.txt` dosyasını inceleyiniz.)*

4. **Tesseract Dil Dosyaları:**
   Sisteminizde `tesseract-ocr` ve `libtesseract-dev` paketlerinin kurulu olduğundan emin olun.

## ▶️ Kullanım

Uygulamayı başlatmak için:

```bash
sudo ./venv/bin/python app.py
```
*(Kamera erişimi ve GPIO kontrolü için `sudo` gerekebilir, ancak modern Linux dağıtımlarında kullanıcı `gpio` ve `video` gruplarına eklenerek çözülebilir.)*

Tarayıcınızdan `http://<RASPBERRY_IP>:5000` adresine giderek arayüze erişebilirsiniz.

### Senaryo Adımları
- **📍 Konuma Git**: Kayıtlı bir (X, Y, Z) noktasına hareket eder.
- **🎯 Kelimeye Merkezle**: Belirtilen metni (OCR ile) bulur ve üzerine merkezlenir.
- **↕️ Z Konumuna Git**: Sadece Z eksenini belirtilen yüksekliğe taşır.
- **💨/🛑 Pompa**: Vakum pompasını açar veya kapatır.
- **⏳ Bekle**: Belirtilen süre kadar bekler.
- **🏠 Home**: Makineyi referans noktasına (Homing) gönderir.

## 📂 Proje Yapısı

```
ele495/
├── app.py              # Ana Flask uygulaması ve Backend mantığı
├── requirements.txt    # Python bağımlılıkları
├── static/             # Frontend kaynakları (CSS, JS, İkonlar)
│   ├── app.js          # İstemci tarafı mantığı
│   └── style.css       # Arayüz stilleri
├── templates/          # HTML şablonları
│   └── index.html      # Ana kontrol sayfası
├── bases.json          # Kayıtlı konumlar veritabanı
├── scenarios.json      # Kayıtlı senaryolar veritabanı
└── config.json         # Sistem ayarları
```

## 👥 Katkıda Bulunanlar

**Bitirici Ekip** - ELE495
- Ali Murat
- [Diğer Ekip Üyeleri İsimleri]

---
© 2026 Tüm Hakları Saklıdır.
