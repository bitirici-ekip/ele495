# ELE495 - Elektronik Mühendisliği Bitirme Projesi
## Endüstriyel Pick & Place Eğitim Modeli için Web Tabanlı Gelişmiş Kontrol ve Test Otonomisi

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
Modern elektronik endüstrisinde, yüksek hız ve yüksek doğruluk gerektiren üretim aşamalarının temel taşı olan **Pick & Place (Yüzey Dizgi) makinaları**, üretim kalitesini belirleyen en önemli unsurlardır. "Endüstriyel Pick & Place Eğitim Modeli için Web Tabanlı Gelişmiş Kontrol ve Test Otonomisi" projesi, bu makinelerin fonksiyonlarını yalnızca bileşen dizimi ile kısıtlamayıp, operasyonel test (Direnç ve Diyot) ile optik doğrulama süreçlerini sisteme organik olarak entegre etmeyi hedeflemektedir.

Tasarlanan sistem; merkezi kontrol ünitesi olarak işlev gören bir Raspberry Pi üzerinde koşan Python/Flask tabanlı bir sunucu ile, motor ve sensör yönetiminden sorumlu GRBL tabanlı çoklu-denetleyici mimarisine sahiptir. İki yönlü, düşük gecikmeli veri haberleşmesi sayesinde sistemin her bir ekseni ve test okuması, Vanilla JS, HTML ve CSS ile sıfırdan oluşturulmuş, endüstriyel kalitedeki bir tarayıcı arayüzü (Dashboard) üzerinden denetlenmektedir. Gelişmiş "Senaryo Motoru" sayesinde, hiçbir yazılım bilgisine ihtiyaç duyulmaksızın, operatörlerin sürükle-bırak mantığı ile test, yönelim, optik merkezleme ve kalite standartlarına dayalı IF-KOŞUL ağaçları yaratabilmesi sağlanmıştır. Bu açıdan proje; mekatronik donanım donatısını yüksek seviye bir karar-destek ve otomasyon diliyle harmanlayan uçtan-uca (end-to-end) bir çözümdür.

---

## 🎯 Entegre Otonomi Hedefleri ve Detaylı İşlevsellikler

Sistemin sunduğu ana katma değerler dört temel boyutta incelenir:

### 1. Karar Verebilen (Conditional) Senaryo Yürütme Motoru
Geleneksel CNC veya P&P yazılımlarındaki doğrusal G-Code işletim mantığı bir adım ileri taşınmıştır. Kurulan otonom senaryo yöneticisi, çalışma zamanında alınan analog ölçümlere (Direnç omik değeri veya Diyot polarizasyonu) dinamik olarak tepki veren koşullu (IF-THEN-ELSE) düğümler içerir.
* **Tolerans Analizi**: Bir SMD kapasitör/direnç hedeflenen (Örn: 10kΩ ± %5) tolerans değerindeyse sistem "PASS" yolunu izleyip komponenti PCB üzerine dizer; tolerans dışındaysa "FAIL" yolunu izleyerek atık / kusurlu komponent kutusuna tahliye işlemini (GOTO: FAIL_KUTUSU, VAKUM: KAPAT) başlatır.
* **Hibrid Görev Zincirleri (Master Scenarios)**: Kullanıcılar spesifik işlemleri (Örn: Sadece ölçüm yap, sadece kamerayla bul) kapsülleyip, "Master Senaryolar" altında birleştirerek devasa üretim reçeteleri (Recipes) üretebilir.

### 2. Görüntü İşleme (Computer Vision) ve Optik Karakter Tanıma (OCR)
Kapalı çevrim (Closed-loop) kalite güvencesi sağlamak için makine üzerinde bulunan kamera vizörü, Python (OpenCV) algoritmaları ile sürekli taranır. Frame'lerden kırpılan ilgi alanları (Region of Interest - ROI), Tesseract OCR motoruna beslenerek saniyelik kare analizi elde edilir. 
* **Oto-Merkezleme (Auto-Tracking):** Sistemin hafızasındaki belli bir bileşene (Örn: "R102", "IC_555" yazısı) hareket emri verildiğinde, görüntü işleme ünitesi makineyi adım adım karakter bloğunun aritmetik merkezine milimetrik olarak oturtur. Titreşim filtresi (Bounding Box Stabilization) ile noise (parazit) değerleri filtrelenir.
* **Uygulama İçi Overlay Mimarisi:** İstemci tarafında video sekansı, MJPEG veri akışı protokolü ile sunulur ve üzerine WebSockets (Socket.IO) ile anlık alınan okuma sonuçları ve dikdörtgen tarama çerçeveleri çizilir (Canvas Overlay).

### 3. Hassas Ölçüm Birimi ve Nozzle-Motor Mekatroniği 
G-Code bazlı yönlendirmelere maruz kalan asıl üç eksenin (X, Y, Z CNC bloğu) yanı sıra sistem tamamen izole bir Arduino köle (Slave) birimi ile özel nozzle operasyonlarını denetler. 
* **360° Oryantasyon ve Açı Hassasiyeti:** Nozzle ucu, minyatür bir step motor ve sürücü katmanı üzerinden kapalı çevrim PING-PONG seri protokol ile denetlenir. PCB üzerindeki Pad'lerin açısına uygun şekilde bileşenin yönelimi değiştirilebilir.
* **Kelvin/Analog Empedans Testi:** Nozzle ucuna entegre iletken problar, bileşenle temas kurduğunda Arduino'nun Analog-to-Digital (ADC) pini üzerinden voltaj düşümü (Voltage divider layout) okunur. Alınan örneklemler (samples) varyasyonları minimuma indirmek amacıyla matematiksel filtrelerden geçirilerek ortalaması alınır.

### 4. Güvenli Konumlandırma ve Vektörel Sınır Kontrolü (Smart Routing)
Otonom bir robotun en tehlikeli hareketi yanlış koordinasyondan doğan Z-Ekseni çarpmalarıdır. (Bileşen veya iğne kırılmaları). "GOTO_BASE" komutlarında Z rotalaması akıllı algoritmik koruma altındadır. Mekanizma her zaman ilk aşamada "Güvenli Z noktasına" çıkma, XY düzleminde interpolasyonlu ilerleme ve nihayetinde güvenli iniş sekansını işletir.  

---

## 🏗 Kapsamlı Sistem Tasarımı ve Bileşen Mimarisi

Sistemin esnek, dayanıklı ve tam zamanlı veri iletişimi sağlayabilmesi için donanım ile sunucu arasında mikro-servis benzeri bir mantıkla çalışan asenkron katmanlar kullanılmıştır:

### ⚙️ Yazılım Yığını (Software Stack)
* **Backend Framework:** Python 3.11 tabanlı Flask.
* **Gerçek Zamanlı Haberleşme Katmanı:** Flask-SocketIO ve python-engineio. Tüm G-Code komutları, donanım geri bildirimleri, ölçüm tamamlanma eventleri ve hata bildirimleri 15ms'den daha düşük gecikmeyle (WebSocket) taşınmaktadır. 
* **Veri Kalıcılığı (Persistence):** `config.json`, `scenarios.json`, `bases.json` gibi yapılandırma dosyaları üzerinden anlık, lokal dosya tabanlı State Management yapısı. Relasyonel DBMS overhead'inden kaçınılarak SSD/SD okuma performansından maksimum verim alınmıştır. 
* **İstemci Arayüzü (Frontend):** Hiçbir büyük framework'e (React, Vue vb.) bağlı kalmadan, yüksek perfromans sağlaması ve RAM ayak izinin asgari tutulması hedeflenerek Vanilla JS ve DOM manüpilasyon rutinleri ile inşa edilmiştir.

### 🔗 Paralel İş Parçacığı Yönetimi (Concurrency Management)
Sunucu üzerinde sistemin "Lock/Halt" (kilitlenme) durumlarına düşmesini engellemek için üç temel `Thread` koşmaktadır: 
1. **Camera Thread:** OpenCV frame yakalama, görüntü formatlama ve MJPEG stream üretimi işlevlerini tekeline alır.
2. **GRBL State Polling Thread:** 500 ms döngüler ile `?` komutları yollayıp Kartezyen denetleyicinin o sıradaki `Run/Idle/Alarm` statüsünü tarar ve arayüze basmak üzere soket kuyruğuna aktarır. 
3. **Scenario Engine Thread (Worker):** Karar dallanmalarının `while` döngüsünü engellemeden asenkron çalışabilmesi için yaratılan yürütme motorudur. Sürekli olarak Queue yapısından beslenip, `sleep()` metodlarından etkilenmeden arka planda adım işletir. 

### 🧰 Donanım ve Sensör Katmanı 
* **Ana İşlem Merkezi:** Raspberry Pi 4/5 (Broadcom System-on-Chip) 
* **Kartezyen (XYZ) Kontrolcü:** NEMA step motorları sürücü kalkanıyla birlikte kontrol eden, üzerine GRBL v1.1.x Firmware flaşlanmış Arduino devresi. Girdileri seri port kanalıyla direkt G-Code direktifi olarak alır. (G0, G1 vb.) 
* **Analog ve Açı Denetimcisi (Slave Arduino):** Uygulamaya özgü yazılmış, ADC ve Limit Switch interrupt (kesme) bayraklarına tepki veren C++ Firmware'i ile beslenir. "Açıya dön", "Direnç Yolla", "Diyot Ölç" gibi String parse tabanlı seri haberleşme döngüsü izler. Düşük gürültülü analog kablolama tasarımına sahiptir. 
* **Kamera:** CSI (Camera Serial Interface) portuna bağlı RPi Gen 3 yüksek çözünürlük özellikli kamera sensörü. Vizyon tabanlı analiz ve operasyon bu bant genişliği üzerinden sağlanır. 

---

## 💻 API ve İletişim Protokolleri (Developer Reference)

Kullanıcı arayüzü ile donanım işlemlerini birleştiren genişletilebilir bir REST JSON ve Socket.io mimarisi kurulmuştur. Gelecekte bir başka arayüz (Mobil / Masaüstü) tasarlandığında sistem ile sorunsuz konuşması hedeflenmiştir:

| Olay / Yönlendirme Sınıfı | Transfer Türü | Temel İşlevi |
|---|---|---|
| **`/api/move` & `/api/home`** | HTTP POST | GRBL motor sürücüsüne standart G0 / yönelim komutlarını dönüştürerek yollar. G-Code üreticisi katmanıdır. |
| **`/api/nozzle/*`** | HTTP POST / GET | `read_resistance`, `goto`, `home` komutlarıyla Slave MCU'nun hareket profillerini yönetir ve JSON formatında `{"success": true, "voltage": x.x, "resistance": y.y}` response döner. |
| **`/api/scenarios/run`** | HTTP POST | Gönderilen senaryo payload'ını Worker Thread'e push eder ve yürütme döngüsünü ateşler. |
| **`video_feed`** | HTTP GET | Multipart MIME formatında, sürekli frame basan Jpeg jeneratör rutini. Kamera gecikmesini %1'in altına çeker. |
| **`status_update`** | WebSocket | XY pikselleri, GRBL eksen koordinatları ve FPS bilgilerini Frontend ile senkron halinde tutan event emisyonu. |
| **`scenario_test_result`** | WebSocket | IF modüllerindeki karar bloğunun sonucunu pushlar. Arayüzün PASS veya FAIL kutucuğunu anlık aydınlatmasını tetikler. |

---

## 📋 Kurulum ve Devreye Alma Süreci

Endüstriyel otopilot donanım ve yazılımlarının bir prototipi olan sistemi devre dışından kendi makinenizde simüle etmek/çalıştırmak için: 

### 1. Gereksinim Duyulan Sistem Bağımlılıkları (Root)
Uygulamanın Computer Vision ve Metin algılama uzantılarının sağlıklı çalışabilmesi adına Tesseract OSS projesi C++ çekirdeği entegrasyonuna ihtiyaç duyulmaktadır:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng libleptonica-dev libtesseract-dev
```

### 2. Uygulama ve Bağımlılık İzolasyonu
Tüm python paketlerini dış katmanlardan izole ederek sanal bir env içerisinde toplamak ve başlatmak en iyi pratiktir:
```bash
# Versiyon kopyasının alınması (Clone)
git clone https://github.com/bitirici-ekip/ele495.git
cd ele495

# Python sanal ortam (VENV) kurulması ve paket yüklenimi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Çevresel Birim Bağlantıları ve Otonom Başlatma
1. GRBL uyumlu ana kartı ve Nozzle sürücü Slave Arduino'yu USB üzerinden bağlayın. (Cihazların `ttyUSB0` / `ttyACM0` gibi linux sembolik linkleri *PNP Control Center Bağlantı Katmanı* tarafından Boot anında asenkron taranıp otomatik uyuşturulur.)
2. `python app.py` komutuyla sistemi ayağa kaldırın. 
3. Uygulama lokasyon bağımsız biçimde varsayılan olarak `http://0.0.0.0:5000` üzerinden yayına başlayacaktır. Web tarayıcınızdan ağınızdaki yayın adresine bağlanınız.

---

## 📜 Akademik Nitelik ve Sürdürülebilirlik Beyanı

Bu depo ve içerisindeki tüm bileşenler, donanım tasarımıyla, yazılımsal kararlarıyla, ve kontrol protokolleriyle; ELE495 Elektronik Mühendisliği Bitirme Projesi kapsamında mühendislik disiplinine, güncel sistem geliştirme standartlarına ve donanım yazılım entegrasyonu etiğine sıkı sıkıya bağlı kalarak baştan sona ekibimizce kurgulanıp kodlanmış ve mimarisi oluşturulmuştur. 

Otomasyonda standart çözümlere yönelmek yerine kapalı çevrim test entegrasyonlarını modüler yazılım pratikleriyle birleştirerek geleceğin Endüstri 4.0 tabanlı üretim tezgahları için bir yapı bloğu yaratmak öncelenmiştir. Geliştirilen REST API, donanım bağımsızlığı (abstraction) ve dinamik senaryo yürütücüsü, projenin açık kaynak olarak genişletilebilir ve ölçeklenebilir altyapıya sahip olduğunu belgeler. Şematik bağlantılar ve kaynak kodları serbest araştırma ve modifikasyonlar için açıktır.

© 2026 Bitirici Ekip — Tüm telif hakları proje ekibine aittir.
