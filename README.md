# ELE495 - Elektronik Mühendisliği Bitirme Projesi
## Endüstriyel Pick & Place (Yüzey Dizgi) Makinesi İçin Web Tabanlı Otonom Test ve Kontrol Sistemi

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask)](https://flask.palletsprojects.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-4.x-010101?logo=socket.io)](https://socket.io/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv)](https://opencv.org/)
[![Arduino](https://img.shields.io/badge/Arduino-Compatible-00979D?logo=arduino)](https://www.arduino.cc/)

</div>

---

## 👥 Proje Ekibi
* **Şahin Yalgun**
* **Mehmet Egemen Çorbacı**
* **Mustafa Anıl Işık**
* **Aydın Eralp Sırmalı**

---

## 📌 Proje Özeti (Abtract)
Bu proje, elektronik endüstrisinde yaygın olarak kullanılan Pick & Place (Yüzey Dizgi) makinelerinin otomasyon, test ve doğrulama süreçlerini akıllandırmayı hedefleyen kapsamlı bir sistem tasarımıdır. Geliştirilen mimari; donanım kontrolü, görüntü işleme ve karmaşık karar senaryolarını tek bir entegre platformda birleştirir. 

Raspberry Pi tabanlı merkezi işlem birimi üzerinde koşan Flask Sunucusu, bir yandan GRBL uyumlu CNC motor sürücüleriyle hassas Kartezyen (X-Y-Z) konumlandırma yaparken, diğer yandan Tesseract OCR (Optik Karakter Tanıma) destekli bir görüntü işleme hattıyla sistemin kapalı çevrim geri besleme almasını sağlar. Bu sayede dizilen veya dizilecek olan SMD (Yüzeye Monte Edilebilir) komponentlerin doğruluğu anlık olarak denetlenebilmektedir. Ayrıca, sisteme entegre edilen "Slave" donanım birimi (Arduino) üzerinden step motorlu bir nozzle ekseni yönetilmekte ve alınan analog verilerle komponentlere **Direnç ve Diyot testleri** uygulanmaktadır.

---

## 🎯 Temel Hedefler ve İşlevsellikler

1. **Otonom Test ve Doğrulama**: Nozzle ucuna alınan komponentlerin direnç değerlerinin veya diyot iletim durumlarının ADC üzerinden yüksek doğrulukla okunması. Sonuca göre koşullu çalışma (IF-PASS/FAIL dallanmaları).
2. **Optik Karakter Tanıma (OCR) Entegrasyonu**: Kamera üzerinden okunan yazı ve değerlerin Tesseract OCR motoru ile algılanması. Hedef kelimeye otomatik merkezleme (Auto-Center) yeteneği.
3. **Kapsamlı Senaryo Motoru**: Sistemin operatör müdahalesi olmadan dizgi, test ve kalite kontrol süreçlerini başından sonuna kadar işletebilmesini sağlayan, blok tabanlı senaryo yapılandırıcısı (Master ve Standart Senaryolar).
4. **Gerçek Zamanlı Web Arayüzü**: Soket bağlantısı (WebSocket/Socket.IO) ile anlık MJPEG video akışı sağlayan, tüm motor konumlarının ve test sonuçlarının gecikmesiz monitörize edildiği kontrol paneli.
5. **Güvenli Hareket Algoritmaları**: Karmaşık Z ekseni çarpmalarını engelleyen, hedef ve mevcut konum arasındaki vektörel analize dayalı akıllı interpolasyon dizilimleri.

---

## 🏗 Tasarım ve Sistem Mimarisi

Sistem Mimarisi 3 temel katmandan oluşmaktadır:

### 1. Sunucu ve Görüntü İşleme Katmanı (Raspberry Pi & Python/Flask)
Merkezi denetleyici olarak görev yapar. Kamera akışını Open-CV ile işleyerek Tesseract motoruna aktarır, tarayıcı arayüzü ile donanım arasındaki iletişimi WebSocket üzerinden senkronize eder. 

### 2. İstemci Arayüz Katmanı (HTML5, CSS3, Vanilla JS)
Endüstriyel standartlara uygun tasarlanan kontrol paneli. Senaryoların oluşturulması, kamera vizörü, manuel eksen joglama komutları ve sistem metriklerinin görselleştirilmesi bu katmanda gerçekleşir.

### 3. Donanım Katmanı (GRBL CNC Kontrolcü & Nozzle Slave MCU)
Motor hareketlerinin gerçek zamanlı denetiminden (GRBL interpolasyonları) ve analog test prosedürlerinin (Direnç/Diyot okumaları) donanım üzerinden gerçekleştirilip Raspberry Pi'ye raporlanmasından sorumludur.

---

## ⚙ Teknik Özellikler

* **Çok Kanallı Proses Yönetimi**: Kamera verisi, OCR hesaplamaları ve GRBL durum sorguları izole edilmiş çoklu-iş parçacıkları (multi-threading) halinde asenkron çalışır. 
* **Koşullu Dallanma Mimarisi (Scenario Engine)**: Test sonuçlarına dayalı dinamik ağaç yapılı görev kararları (Örn: "Direnç %10 tolerans içindeyse X konumuna, hatalıysa Y konumuna bırak").
* **Esnek Kalibrasyon Altyapısı**: Piksel-Milimetre dönüşüm matrisleri, Tesseract PSM modları ve eksen invert ayarları sistem durdurulmadan dinamik olarak UI üzerinden yönetilebilir.

---

## 📂 Dosya Hiyerarşisi (Repository Structure)

```
ele495/
├── app.py                  # Ana sunucu (Flask, Socket.IO, Multi-thread yöneticisi)
├── pi_controller.py        # Yardımcı donanım iletişim protokolleri (Serial Com)
├── arduino_stepper/        
│   └── arduino_stepper.ino # Nozzle Slave mikrodenetleyici C/C++ kaynak kodları
├── templates/
│   ├── index.html          # Denetim Paneli Arayüzü
│   └── login.html          # Güvenlik ve Kimlik Doğrulama
├── static/
│   ├── app.js              # İstemci tarafı olay döngüsü ve UI durum yöneticisi
│   └── style.css           # Mimari arayüz stilleri
├── config.json             # Sistemin kalıcı yapılandırma bellek kütüğü
├── bases.json              # Kartesian (XYZ) koordinat veritabanı
├── scenarios.json          # Kayıtlı alt görev (standart senaryo) listesi
├── master_scenarios.json   # Modüler uçtan-uca (master) üretim hattı senaryoları
├── verification.json       # Otonom OCR kalite kontrol parametreleri
├── requirements.txt        # Python ortam bağımlılık listesi
└── README.md               # Proje belgelendirmesi
```

---

## 🚀 Çalıştırma ve Test Yönergeleri

**1. Gerekli Ortamın Hazırlanması:**
Sistemin çalıştırılacağı Raspberry Pi (veya Linux tabanlı herhangi bir SBC/PC) üzerinde Tesseract motorunun kurulu olması gereklidir:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng libleptonica-dev libtesseract-dev
```

**2. Python Sanal Ortamının Kurulumu:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Uygulamanın Başlatılması:**
```bash
python app.py
```
*Sistem başlatıldıktan sonra varsayılan olarak `http://0.0.0.0:5000` portu üzerinden ağdaki tüm cihazların erişimine hazır hale gelecektir.*
