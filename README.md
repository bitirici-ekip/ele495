# 🤖 ELE495 - Akıllı Pick & Place Kontrol Sistemi (v2.0)

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-green?style=for-the-badge&logo=flask)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2F5-C51A4A?style=for-the-badge&logo=raspberry-pi)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-red?style=for-the-badge&logo=opencv)

**ELE495 Bitirme Projesi** kapsamında tasarlanmış yüksek hassasiyetli, görüntü işleme destekli ve endüstri standartlarında bir **Akıllı Pick & Place (Dizgi) Makinesi** kontrol arayüzüdür. (Sürüm 2.0)
Makinenin bütün operasyonları, OCR destekli akıllı merkezleme sistemi ve modüler senaryo mimarisi ile baştan uca tek bir web platformundan yönetilmektedir.

---

## 🌟 Öne Çıkan Özellikler

### 🖥️ Profesyonel ve Modern Web Arayüzü
*   **Tam Kontrol (Cross-Platform):** Bilgisayar, tablet veya mobil cihazlardan eşzamanlı ve sorunsuz erişilebilen kullanıcı dostu modern kontrol paneli.
*   **Gerçek Zamanlı Kamera Akışı:** Raspberry Pi Camera Module 3 ve GStreamer destekli **düşük gecikmeli MJPEG video akışı**.
*   **Karanlık Mod Tasarımı (Dark Mode):** Endüstriyel kullanıma uygun, göz yormayan, kontrast düzeyi ayarlanmış profesyonel arayüz (UI).

### 👁️ Akıllı Görüntü İşleme (OCR & Vision)
*   **Gelişmiş Metin Tanıma (Tesseract OCR):** Komponentler, elektronik kartlar veya yüzeyler üzerindeki referans kodlarını anlık ve çoklu olarak yüksek doğrulukla okuyabilme kapasitesi.
*   **PIP (Picture-in-Picture) ve Max Zoom:** 10x'e kadar dijital yakınlaştırma özelliği ile kamera görüntüsünü detaylı inceleme, manuel merkezleme için "Crosshair" özellikli mini PIP ekranı.
*   **Otomatik Hizalama (Auto-Center):** Kameradaki hedef kelimeyi veya referans numarasını tespit edip **milimetrik hassasiyetle** makine eksenini o noktanın tam merkezine otomatik taşıyan akıllı PID / hizalama algoritması.
*   **Dinamik Overlay (Bounding Box):** OCR tarafından tespit edilen tüm nesnelerin ve metinlerin canlı video haritası üzerinde gerçek zamanlı interaktif kutularla (Bounding Box) işaretlenmesi.

### 🎬 Gelişmiş Senaryo ve Üretim Yönetimi
*   **Adım Adım Senaryo (Flow) Yönetimi:** Kod yazmadan karmaşık hareket (X, Y, Z ekseni), Motor Homing, bekleme, vakum açma/kapatma gibi senaryoları tasarlama ve sırasını interaktif olarak düzenleme imkanı.
*   **Master Senaryolar (Sıralı İşletim):** Birbirine bağlı birden fazla alt senaryoyu tek tıklamayla zincirleme olarak işletme desteği (Ör: "Hazırlık -> Bant 1 Dizgi -> Kalite Kontrol").
*   **Z-Only (Sadece Z Axis) Modu:** Mevcut X/Y koordinatını asla bozmadan yalnızca Z ekseninde hızlı yükseklik ayarı ve parça alma / bırakma komutu.
*   **Doğrulama (Verification) Adımları:** Görüntü analizleri sonucu "Okunan değer referansla uyuşuyor mu?" kontrolü ekleme ve duruma göre makineyi devam ettirme veya durdurma mekanizması.

### ⚙️ Güçlü Altyapı ve Güvenlik Mekanizması
*   **GRBL Uyumu:** Arduino / Kontrolcü kartları üzerinden standart CNC ve GRBL v1.1 protokolü ile tam G-Code entegrasyonu.
*   **Hareket Güvenliği:** Sisteme güç verildiğinde veya menüden "Homing" (Sıfırlama), "Soft-Reset", "Shutdown Server", ve anlık "Stop" komutu gibi kritik kontrol yetenekleri.
*   **Hız ve Performans:** Flask arka planında Socket.IO kullanarak web arayüzü ile CNC donanımı arasında **milisaniyeler** mertebesinde çift yönlü asenkron komut iletişim ağı.
*   **Esnek Konfigürasyonlar (Ayarlar Sekmesi):** Uygulama arayüzü üzerinden hiç kod değiştirmeden Motor Kalibrasyonu, OCR Tesseract Optimizasyonu (Adaptive Threshold vs.), Kamera Tolerans ve Çözünürlük ayarlarının anlık revizyonu.

---

## 🛠️ Kurulum ve Başlatma (Quick Start)

Bu proje **Raspberry Pi OS** (Bookworm / Bullseye vb.) Linux ortamında çalışmak için tam optimize edilmiştir.

### 1. Hazırlık ve Klonlama
Git deposunu Raspberry Pi üzerindeki çalışma alanınıza klonlayın ve klasöre girin:
```bash
git clone https://github.com/bitirici-ekip/ele495.git
cd ele495
```

### 2. Gerekli Ortamın ve Paketlerin Kurulumu
Python sanal (virtual) ortamını oluşturun, aktif edin ve `requirements.txt` dosyasındaki PIP bağımlılıklarını kurun:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
*(Not: Bu yazılım Tesseract OCR motoruna, `libcamera` sistem araçlarına ve donanım hızlandırma modüllerine ihtiyaç duyar. Linux paket yöneticisinden (apt-get) sistem bağımlılıklarının kurulduğundan emin olun.)*

### 3. Uygulamanın Başlatılması
Arka plan Flask uygulamasını yetkili kullanıcı (Seri porta erişim) haklarıyla başlatarak CNC/Kamera bağlantısını dinlemeye alın:
```bash
sudo ./venv/bin/python app.py
```
Aynı ağdaki herhangi bir cihazdan (PC, Telefon) web arayüzüne erişmek için tarayıcınızı açıp cihaz IP'sini girin: `http://<RASPBERRY_IP>:5000`

---

## 📂 Web Arayüzü ve Sayfalar (Detaylı Modül Bakışı)

1. **Dashboard (Ana Kontrol Paneli):** Operatörün birincil ekranıdır. Merkezde yüksek yenileme hızlı kamera akışı, köşe modülünde PIP Zoom ekranı bulunur. Sol ve alt panellerde X, Y, Z eksenlerinin posisyon değerleri, jog (adım) ilerletme butonları, Homing / Stop kontrolleri mevcuttur. "Auto-Center" (Görsel hizalama tespit hedefi) arama kutusu buradan tetiklenir.
2. **Senaryolar (Scenarios):** Uygulamanın üretim zinciri yönetimidir. Makinenin yapacağı hareketleri (sıralı adımlar, koordinat kayıtları, pompa yönetimi) "Alt Senaryolar" olarak kaydetmek; ardından bu alt senaryoları "Master Scenarios" havuzu ile bütüncül, çoklu görev zincirlerine dönüştürmek mümkündür.
3. **Ayarlar (Settings):** Sistemin ana sinir ağının kalibre edildiği teknisyen sayfasıdır. Dört ana bölümden oluşur: "Motor Calibration" (hareket limitleri), "OCR Settings" (Görüntü işleme filtre ve gürültü azaltma mekaniği), "OCR Monitoring", ve genel bağlantı parametrelerinin bulunduğu "System" bölümü.
4. **Doğrulama / Log (Verification):** Makinenin gerçekleştirdiği üretim adımlarının canlı test edildiği; kameranın o anki frame'de okuduğu OCR metinlerinin hedeflenen kontrol eşikleri veya tolerans limitleriyle eşleşip eşleşmediğinin onayından sorumlu Kalite-Kontrol sayfasıdır.

---

## 🏗️ Proje Mimarisi Detayları

Proje geliştirilirken temiz, hafif ve tam modüler bir asenkron altyapı hedeflenmiştir:
- **Core Backend (`app.py` & Modüller):** G-Code serializasyonu, Threaded Flask Worker'lar, seri port komut okuma/yazma donanım işlevleri.
- **Vision & OCR Engine:** `Picamera2` entegrasyon kütüphanesi ile frame yakalama, OpenCV ile manipülasyon (Binarization, Dilate/Erode) sonrası PyTesseract aracılığıyla karakterlerin çıkartılması.
- **Depolama Altyapısı:** Veritabanı ağırlığı yaratmamak adına `scenarios.json`, `master_scenarios.json`, `verification.json`, `config.json` şeklindeki seri çalışabilen NoSQL mantığında mini JSON datastore'lar.
- **Frontend Framework:** Vanilla JavaScript ve asenkron Socket.IO listener arabirimi; harici hantal kütüphanelere (React veya ağır CSS kütüphaneleri) ihtiyaç bırakmayan Custom CSS ve Flexbox Grid mimarisi. Terminal fontu olarak "JetBrains Mono" entegrasyonu.

---

## 🤝 Katkıda Bulunanlar

Bu proje, **ELE495** bitirme tasarım projesi standartları bünyesinde **Şahin Yalgun** vizyonuyla, yazılım mühendisliği prensipleri ve endüstriyel mekatronik standartları gözetilerek başarıyla geliştirilmiş ve tamamlanmıştır.
