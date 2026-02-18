# 🤖 ELE495 - Akıllı Pick & Place Kontrol Sistemi

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-green?style=for-the-badge&logo=flask)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%2F5-C51A4A?style=for-the-badge&logo=raspberry-pi)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-red?style=for-the-badge&logo=opencv)

**ELE495 Bitirme Projesi** kapsamında geliştirilen, endüstriyel standartlarda, yüksek hassasiyetli ve görüntü işleme destekli bir **Pick & Place (Dizgi) Makinesi** kontrol arayüzüdür.

---

## 🌟 Öne Çıkan Özellikler

### 🖥️ Profesyonel Web Arayüzü
*   **Tam Kontrol:** Herhangi bir cihazdan (PC, Tablet, Telefon) erişilebilir modern kontrol paneli.
*   **Canlı İzleme:** Raspberry Pi Camera Module 3 ile **düşük gecikmeli MJPEG video akışı**.
*   **Karanlık Mod:** Göz yormayan, endüstriyel kullanıma uygun arayüz tasarımı.

### 👁️ Akıllı Görüntü İşleme (OCR & Vision)
*   **Metin Tanıma:** Entegre **Tesseract OCR** motoru ile bileşen üzerindeki kodları anlık okuma.
*   **Otomatik Hizalama (Auto-Center):** Kameradaki hedefi tespit edip **milimetrik hassasiyetle** merkeze getiren akıllı algoritma.
*   **Dinamik Overlay:** Tespit edilen nesneler ve metinler video üzerinde gerçek zamanlı işaretlenir.

### 🎬 Gelişmiş Senaryo Yönetimi
*   **Sürükle-Bırak Mantığı:** Kod yazmadan karmaşık hareket senaryoları oluşturun.
*   **Adım Düzenleme:** Senaryo adımlarını (Git, Bekle, Vakumla, Bırak) sonradan düzenleyin ve güncelleyin.
*   **Hızlı Aksiyonlar:** Sık kullanılan senaryolara tek tıkla erişim.

### ⚙️ Güçlü Altyapı
*   **GRBL Uyumu:** Endüstri standardı G-Code komutları ile tam entegrasyon.
*   **Güvenlik:** Acil Durdurma (E-Stop), Soft-Reset ve Alarm yönetimi.
*   **Hız ve Performans:** Socket.IO ile gerçek zamanlı veri iletişimi.

---

## 🛠️ Kurulum ve Başlangıç

Bu proje **Raspberry Pi** üzerinde çalışmak üzere optimize edilmiştir.

### 1. Hazırlık
Repoyu klonlayın ve proje dizinine gidin:
```bash
git clone https://github.com/bitirici-ekip/ele495.git
cd ele495
```

### 2. Kurulum
Sanal ortam oluşturun ve bağımlılıkları yükleyin:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Çalıştırma
Uygulamayı başlatın:
```bash
sudo ./venv/bin/python app.py
```
Tarayıcınızda: `http://<RASPBERRY_IP>:5000`

---

## 🎮 Kullanım Kılavuzu

| Modül | Açıklama |
| :--- | :--- |
| **Manuel Kontrol** | X, Y, Z eksenlerini butonlarla veya klavye ile hassas kontrol edin. |
| **Senaryolar** | Karmaşık montaj/dizgi işlemlerini otomatikleştirin. |
| **Auto-Center** | "Hızlı Merkezle" paneline bir kelime girin ve makinenin o kelimeyi bulup üzerine gitmesini izleyin. |
| **Z-Only** | "Sadece Z Git" komutu ile X/Y konumunu bozmadan yükseklik ayarı yapın. |

---

## 📂 Proje Mimarisi

*   **Backend:** Python, Flask, Socket.IO
*   **Görüntü İşleme:** OpenCV, Tesseract OCR, Picamera2
*   **Frontend:** HTML5, CSS3 (JetBrains Mono & Inter fonts), Vanilla JS
*   **Donanım:** Raspberry Pi, GRBL Controller, Step Motor Sürücüler

---
© 2026 **ELE495 Bitirme Projesi**
