// === ARDUINO GENERIC SLAVE FIRMWARE (v2 - Emergency Stop) ===
// Bu kod Arduino'ya bir kez yüklenir ve bir daha değiştirilmez.
// Tüm konfigürasyon ve mantık Python (Master) tarafında yönetilir.

/*
  ============================================================================
  MİMARİ AÇIKLAMASI (LLM'ler ve Geliştiriciler İçin):
  ============================================================================

  Bu firmware bir "Generic Slave" (Genel Amaçlı Köle) mimarisindedir.
  Arduino, kendi başına hiçbir karar almaz. Sadece Python Master'dan gelen
  düşük seviyeli (low-level) komutları birebir çalıştırır ve sonuçları döner.

  KOMUT PROTOKOLÜ (Seri Port, '\n' ile sonlanır):
  ──────────────────────────────────────────────────────────────────
  Komut                                        Yanıt
  ──────────────────────────────────────────────────────────────────
  PING                                         OK:PONG
  STEP <count> <dir> <spd> <acc_s> <acc_st>    OK:STEP_DONE veya OK:ESTOP
  STEPG <count> <dir> <spd> <acc_s> <acc_st> <guard_pin>  OK:STEP_DONE veya OK:ESTOP
  EN <0|1>                                     OK
  AREAD <pin>                                  OK:<değer>
  DREAD <pin>                                  OK:<değer>
  DWRITE <pin> <val>                           OK
  AWRITE <pin> <val>                           OK
  PMODE <pin> <mode>                           OK
  MULTI_AREAD <pin> <count>                    OK:<değer>
  ──────────────────────────────────────────────────────────────────

  STEPG Komutu (Guarded Step - Korumalı Adım) [YENİ]:
  - STEP ile aynı, ancak ek olarak bir "koruma pini" (guard_pin) alır.
  - Her adımda guard_pin okunur. Eğer LOW ise (buton basılı) motor
    anında durur ve OK:ESTOP yanıtı döner.
  - Bu, limit switch'in acil durdurma (emergency stop) butonu olarak
    çalışmasını sağlar.
  ============================================================================
*/

const int STEP_PIN = 2;
const int DIR_PIN  = 5;
const int EN_PIN   = 8;

String inputBuffer = "";

void setup() {
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH);
  Serial.begin(115200);
  Serial.println("OK:SLAVE_READY");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
      }
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}

// ===================== KOMUT PARSER & ROUTER =====================
void processCommand(String cmd) {
  int firstSpace = cmd.indexOf(' ');
  String command;
  String args;

  if (firstSpace == -1) {
    command = cmd;
    args = "";
  } else {
    command = cmd.substring(0, firstSpace);
    args = cmd.substring(firstSpace + 1);
  }

  command.toUpperCase();

  if (command == "PING") {
    Serial.println("OK:PONG");
    return;
  }

  // STEPG: Korumalı adım (guard pin ile acil durdurma)
  if (command == "STEPG") {
    handleStepGuarded(args);
    return;
  }

  // STEP: Normal adım
  if (command == "STEP") {
    handleStep(args, -1); // -1 = koruma yok
    return;
  }

  if (command == "EN") {
    int val = args.toInt();
    digitalWrite(EN_PIN, val ? HIGH : LOW);
    Serial.println("OK");
    return;
  }

  if (command == "AREAD") {
    int pin = args.toInt();
    int value = analogRead(pin);
    Serial.print("OK:");
    Serial.println(value);
    return;
  }

  if (command == "MULTI_AREAD") {
    handleMultiARead(args);
    return;
  }

  if (command == "DREAD") {
    int pin = args.toInt();
    int value = digitalRead(pin);
    Serial.print("OK:");
    Serial.println(value);
    return;
  }

  if (command == "DWRITE") {
    int spaceIdx = args.indexOf(' ');
    if (spaceIdx == -1) { Serial.println("ERR:DWRITE pin val gerekli"); return; }
    int pin = args.substring(0, spaceIdx).toInt();
    int val = args.substring(spaceIdx + 1).toInt();
    digitalWrite(pin, val ? HIGH : LOW);
    Serial.println("OK");
    return;
  }

  if (command == "AWRITE") {
    int spaceIdx = args.indexOf(' ');
    if (spaceIdx == -1) { Serial.println("ERR:AWRITE pin val gerekli"); return; }
    int pin = args.substring(0, spaceIdx).toInt();
    int val = args.substring(spaceIdx + 1).toInt();
    analogWrite(pin, constrain(val, 0, 255));
    Serial.println("OK");
    return;
  }

  if (command == "PMODE") {
    int spaceIdx = args.indexOf(' ');
    if (spaceIdx == -1) { Serial.println("ERR:PMODE pin mode gerekli"); return; }
    int pin = args.substring(0, spaceIdx).toInt();
    int mode = args.substring(spaceIdx + 1).toInt();
    if (mode == 0) pinMode(pin, INPUT);
    else if (mode == 1) pinMode(pin, OUTPUT);
    else if (mode == 2) pinMode(pin, INPUT_PULLUP);
    else { Serial.println("ERR:Mode 0/1/2 olmali"); return; }
    Serial.println("OK");
    return;
  }

  Serial.print("ERR:Bilinmeyen komut: ");
  Serial.println(command);
}

// ===================== STEPG PARSER =====================
// Args: "<count> <dir> <speed> <accel_steps> <accel_start> <guard_pin>"
void handleStepGuarded(String args) {
  // 6 argüman parse et
  int idx1 = args.indexOf(' '); if (idx1 == -1) { Serial.println("ERR:STEPG arguman eksik"); return; }
  long count = args.substring(0, idx1).toInt();
  String r = args.substring(idx1 + 1);

  int idx2 = r.indexOf(' '); if (idx2 == -1) { Serial.println("ERR:STEPG arguman eksik"); return; }
  int dir = r.substring(0, idx2).toInt();
  r = r.substring(idx2 + 1);

  int idx3 = r.indexOf(' '); if (idx3 == -1) { Serial.println("ERR:STEPG arguman eksik"); return; }
  int speed_us = r.substring(0, idx3).toInt();
  r = r.substring(idx3 + 1);

  int idx4 = r.indexOf(' '); if (idx4 == -1) { Serial.println("ERR:STEPG arguman eksik"); return; }
  int accel_steps = r.substring(0, idx4).toInt();
  r = r.substring(idx4 + 1);

  int idx5 = r.indexOf(' '); if (idx5 == -1) { Serial.println("ERR:STEPG arguman eksik"); return; }
  int accel_start_us = r.substring(0, idx5).toInt();
  int guard_pin = r.substring(idx5 + 1).toInt();

  handleStep_internal(count, dir, speed_us, accel_steps, accel_start_us, guard_pin);
}

// ===================== STEP PARSER =====================
// Args: "<count> <dir> <speed> <accel_steps> <accel_start>"
void handleStep(String args, int guard_pin) {
  int idx1 = args.indexOf(' '); if (idx1 == -1) { Serial.println("ERR:STEP arguman eksik"); return; }
  long count = args.substring(0, idx1).toInt();
  String r = args.substring(idx1 + 1);

  int idx2 = r.indexOf(' '); if (idx2 == -1) { Serial.println("ERR:STEP arguman eksik"); return; }
  int dir = r.substring(0, idx2).toInt();
  r = r.substring(idx2 + 1);

  int idx3 = r.indexOf(' '); if (idx3 == -1) { Serial.println("ERR:STEP arguman eksik"); return; }
  int speed_us = r.substring(0, idx3).toInt();
  r = r.substring(idx3 + 1);

  int idx4 = r.indexOf(' '); if (idx4 == -1) { Serial.println("ERR:STEP arguman eksik"); return; }
  int accel_steps = r.substring(0, idx4).toInt();
  int accel_start_us = r.substring(idx4 + 1).toInt();

  handleStep_internal(count, dir, speed_us, accel_steps, accel_start_us, guard_pin);
}

// ===================== STEP EXECUTION (Unified) =====================
void handleStep_internal(long count, int dir, int speed_us, int accel_steps, int accel_start_us, int guard_pin) {
  if (count <= 0 || count > 100000) {
    Serial.println("ERR:Adim sayisi 1-100000 arasi olmali");
    return;
  }
  if (speed_us < 100) {
    Serial.println("ERR:Hiz cok yuksek (min 100us)");
    return;
  }

  digitalWrite(DIR_PIN, dir ? HIGH : LOW);

  long accelZone = min((long)accel_steps, count / 2);
  bool emergency_stopped = false;

  for (long i = 0; i < count; i++) {
    // Acil durdurma: guard_pin tanımlıysa her adımda kontrol et
    if (guard_pin >= 0) {
      if (digitalRead(guard_pin) == LOW) {
        // Buton basıldı! Motoru anında durdur
        emergency_stopped = true;
        break;
      }
    }

    int currentSpeed;
    if (accelZone > 0 && i < accelZone) {
      currentSpeed = map(i, 0, accelZone, accel_start_us, speed_us);
    } else if (accelZone > 0 && i > count - accelZone) {
      currentSpeed = map(i, count - accelZone, count, speed_us, accel_start_us);
    } else {
      currentSpeed = speed_us;
    }

    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(currentSpeed);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(currentSpeed);
  }

  if (emergency_stopped) {
    Serial.println("OK:ESTOP");
  } else {
    Serial.println("OK:STEP_DONE");
  }
}

// ===================== ÇOKLU ANALOG OKUMA =====================
void handleMultiARead(String args) {
  int spaceIdx = args.indexOf(' ');
  if (spaceIdx == -1) { Serial.println("ERR:MULTI_AREAD pin count gerekli"); return; }
  int pin = args.substring(0, spaceIdx).toInt();
  int count = args.substring(spaceIdx + 1).toInt();
  if (count <= 0 || count > 100) { Serial.println("ERR:Okuma 1-100 arasi olmali"); return; }

  long total = 0;
  for (int i = 0; i < count; i++) {
    total += analogRead(pin);
    delay(2);
  }
  Serial.print("OK:");
  Serial.println(total / count);
}
