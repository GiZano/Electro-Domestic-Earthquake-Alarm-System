/**
 * Project: QuakeGuard - Professional Seismic Node
 * Version: 1.3.0-GNSS-PPS
 * Target Hardware: ESP32-C3 SuperMini + ADXL345 + NEO-6M (JLCPCB)
 * Author: GiZano
 *
 * CHANGELOG:
 * - v1.3.0: GNSS on UART1 RX 5 / TX 4 (JLCPCB J4), PPS on GPIO 2, fallback coords via .env,
 *   LED blue (10) PWM dimmed + red (3) 3s quake pulse + boot self-test, NTP+PPS discipline prep.
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <time.h>
#include <PubSubClient.h>

// --- Cryptographic Libraries (MbedTLS) ---
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/pk.h"
#include "mbedtls/error.h"
#include <array>
#include <vector>
#include <chrono>
#include "DetectionCore.h"
#include "GnssModule.h"
#include "SerialFallback.h"

// --------------------------------------------------------------------------
// HARDWARE & SERVER CONFIGURATION
// --------------------------------------------------------------------------
constexpr int I2C_SDA_PIN = 7;
constexpr int I2C_SCL_PIN = 8;
constexpr int I2C_CLOCK_SPEED = 100000;

constexpr int LED_BLUE_PIN = 10; // connection state: double->wifi, single->server, solid->connected
constexpr int LED_RED_PIN = 3;  // quake detected: on 3 s

#ifndef SERVER_HOST
  #define SERVER_HOST "your-tunnel-id.trycloudflare.com"
#endif
#ifndef SERVER_PORT
  #define SERVER_PORT 80
#endif
#ifndef SERVER_PROTOCOL
  #define SERVER_PROTOCOL "https"
#endif
#ifndef SERVER_PATH
  #define SERVER_PATH "/readings/"
#endif
#ifndef SERVER_REGISTER_PATH
  #define SERVER_REGISTER_PATH "/devices/register"
#endif
#ifndef MQTT_BROKER_HOST
  #error "MQTT_BROKER_HOST is missing! Add it to esp32_config.env"
#endif
#ifndef MQTT_BROKER_PORT
  #define MQTT_BROKER_PORT 8883
#endif
#ifndef MQTT_USERNAME
  #error "MQTT_USERNAME is missing! Add it to esp32_config.env"
#endif
#ifndef MQTT_PASSWORD
  #error "MQTT_PASSWORD is missing! Add it to esp32_config.env"
#endif

#ifndef SERIAL_FALLBACK_ENABLED
  #define SERIAL_FALLBACK_ENABLED 1
#endif
#ifndef SERIAL_FALLBACK_MARKER
  #define SERIAL_FALLBACK_MARKER "[QG:FB]"
#endif

#ifndef ENROLLMENT_TOKEN
  #ifndef __INTELLISENSE__ 
    // 1. If the REAL compiler doesn't see the token, crash the build to protect us!
    #error "CRITICAL BUILD ERROR: ENROLLMENT_TOKEN is missing! Add it to esp32_config.env"
  #else 
    // 2. If VSCode's UI is looking at the file, give it a fake token so it stops crying on line 168!
    #define ENROLLMENT_TOKEN "vscode_dummy_token"
  #endif
#endif

// Global Dynamic Sensor ID
static int globalSensorID = 0;
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);

// LED state (v1.3) — blue dimmed via PWM, red 3 s pulse
static volatile unsigned long g_redLedOffAt = 0;
static constexpr int BLUE_BRIGHT = 100; // 0-255, ~40% per dimmare leggermente il blu (era 255)

inline void triggerQuakeLed() {
    digitalWrite(LED_RED_PIN, HIGH);
    Serial.println("[LED] Red ON (quake) for 3 s");
    g_redLedOffAt = millis() + 3000;
}

inline void updateConnectionLed(bool wifiConnected, bool serverConnected) {
    // Red LED auto-off
    if (g_redLedOffAt != 0 && (long)(millis() - g_redLedOffAt) >= 0) {
        digitalWrite(LED_RED_PIN, LOW);
        g_redLedOffAt = 0;
        Serial.println("[LED] Red OFF");
    }
    // Blue LED: PWM dimmed (analogWrite) — double blink WiFi, single blink server, solid connected
    if (!wifiConnected) {
        unsigned long phase = millis() % 1000;
        bool on = (phase < 100) || (phase >= 200 && phase < 300);
        analogWrite(LED_BLUE_PIN, on ? BLUE_BRIGHT : 0);
    } else if (!serverConnected) {
        unsigned long phase = millis() % 1000;
        bool on = (phase < 200);
        analogWrite(LED_BLUE_PIN, on ? BLUE_BRIGHT : 0);
    } else {
        analogWrite(LED_BLUE_PIN, BLUE_BRIGHT);
    }
}

// Boot self-test: blink both LEDs to verify wiring (red active-HIGH: GPIO3->R3->D3->GND)
inline void ledBootTest() {
    Serial.println("[LED] Boot test: blue + red");
    for (int i = 0; i < 2; i++) {
        digitalWrite(LED_BLUE_PIN, HIGH); // full bright for test
        digitalWrite(LED_RED_PIN, HIGH);
        delay(250);
        digitalWrite(LED_BLUE_PIN, LOW);
        digitalWrite(LED_RED_PIN, LOW);
        delay(250);
    }
    // leave both off, updateConnectionLed will drive blue from now on
    analogWrite(LED_BLUE_PIN, 0);
}

// --------------------------------------------------------------------------
// RTOS & DSP DEFINITIONS
// --------------------------------------------------------------------------
QueueHandle_t eventQueue;

struct SeismicEvent {
    float magnitude;
    unsigned long event_millis;
};

constexpr float TRIGGER_RATIO = 1.8f;
constexpr float NOISE_FLOOR = 0.04f;
constexpr float HPF_ALPHA = 0.9f;

// v1.2.2: bounded in-memory retention for events with no delivery path.
constexpr size_t RETENTION_CAPACITY = 100;

// --------------------------------------------------------------------------
// CRYPTO SUBSYSTEM
// --------------------------------------------------------------------------
static Preferences preferences;

class CryptoContext {
    mbedtls_entropy_context entropy_;
    mbedtls_ctr_drbg_context ctr_drbg_;
    mbedtls_pk_context pk_context_;
public:
    void init();
    String getPublicKeyHex();
    String signMessage(const String& message);
};

CryptoContext& crypto() {
    static CryptoContext c;
    return c;
}

void CryptoContext::init() {
    mbedtls_entropy_init(&entropy_);
    mbedtls_ctr_drbg_init(&ctr_drbg_);
    mbedtls_pk_init(&pk_context_);

    constexpr const char pers[] = "quake_guard_signer";
    mbedtls_ctr_drbg_seed(&ctr_drbg_, mbedtls_entropy_func, &entropy_, (const unsigned char*)pers, sizeof(pers) - 1);

    preferences.begin("quake-keys", false);

    if (!preferences.isKey("priv_key")) {
        Serial.println("[SEC] Generating New ECDSA Key Pair...");
        mbedtls_pk_setup(&pk_context_, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
        mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(pk_context_), mbedtls_ctr_drbg_random, &ctr_drbg_);
        std::array<unsigned char, 128> priv_buf;
        int ret = mbedtls_pk_write_key_der(&pk_context_, priv_buf.data(), priv_buf.size());
        preferences.putBytes("priv_key", priv_buf.data() + priv_buf.size() - ret, ret);
        Serial.println("[SEC] Keys Generated.");
    } else {
        Serial.println("[SEC] Loading Existing Keys...");
        size_t len = preferences.getBytesLength("priv_key");
        std::vector<uint8_t> buf(len);
        preferences.getBytes("priv_key", buf.data(), len);
        mbedtls_pk_parse_key(&pk_context_, buf.data(), len, NULL, 0);
    }
}

String CryptoContext::getPublicKeyHex() {
    std::array<unsigned char, 128> pub_buf;
    int ret = mbedtls_pk_write_pubkey_der(&pk_context_, pub_buf.data(), pub_buf.size());
    int len = ret;
    int start_index = pub_buf.size() - len;

    String hexKey = "";
    for(int i = start_index; i < static_cast<int>(pub_buf.size()); i++) {
        std::array<char, 3> buf;
        snprintf(buf.data(), buf.size(), "%02x", pub_buf[i]); // NOSONAR(cpp:S6494) - std::format unavailable on ESP32
        hexKey += buf.data();
    }
    return hexKey;
}

String CryptoContext::signMessage(const String& message) {
    std::array<unsigned char, 32> hash;
    std::array<unsigned char, MBEDTLS_ECDSA_MAX_LEN> sig;
    size_t sig_len = 0;
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 0);
    mbedtls_md_starts(&ctx);
    mbedtls_md_update(&ctx, (const unsigned char*)message.c_str(), message.length());
    mbedtls_md_finish(&ctx, hash.data());
    mbedtls_md_free(&ctx);
    mbedtls_pk_sign(&pk_context_, MBEDTLS_MD_SHA256, hash.data(), 0, sig.data(), &sig_len, mbedtls_ctr_drbg_random, &ctr_drbg_);
    
    String hexSig = "";
    for(size_t i = 0; i < sig_len; i++) { 
        std::array<char, 3> buf; 
        snprintf(buf.data(), buf.size(), "%02x", sig[i]); // NOSONAR(cpp:S6494)
        hexSig += buf.data(); 
    }
    return hexSig;
}

// --------------------------------------------------------------------------
// PROVISIONING LOGIC
// --------------------------------------------------------------------------
bool performProvisioning() {
    Serial.println("\n[PROV] Starting Device Handshake...");
    if(WiFi.status() != WL_CONNECTED) {
        Serial.println("[PROV] Error: No WiFi connection.");
        return false;
    }

    HTTPClient http;
    // SERVER_HOST may be configured with or without a leading scheme; normalize
    // it so a "https://host" value cannot produce "https://https://host". The
    // actual request protocol comes from SERVER_PROTOCOL below.
    auto host = String(SERVER_HOST);
    auto scheme = host.indexOf("://");
    if (scheme != -1) {
        host.remove(0, scheme + 3);
    }

    String url = String(SERVER_PROTOCOL) + "://" + host;
    int serverPort = SERVER_PORT;
    if (serverPort != 80 && serverPort != 443) {
        url += ":" + String(serverPort);
    }
    url += SERVER_REGISTER_PATH;

    Serial.printf("[PROV] Connecting to: %s\n", url.c_str());
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("ngrok-skip-browser-warning", "true");
    http.setTimeout(15000);

    JsonDocument doc;
    doc["public_key_hex"] = crypto().getPublicKeyHex();
    doc["mac_address"] = WiFi.macAddress();
    doc["enrollment_token"] = ENROLLMENT_TOKEN;

#ifdef GNSS_ENABLED
    // GNSS-ready: report the real fix when available, else the last-known fix
    // persisted in NVS. If neither exists, use fallback coords from .env
    // (cantina testing) or omit -> backend assigns "Unknown Region".
    GnssFix fix;
    if (gnss().getFix(fix)) {
        doc["latitude"] = fix.latitude;
        doc["longitude"] = fix.longitude;
        Serial.printf("[PROV] Sending fix: %.5f, %.5f (from %s)\n",
                      fix.latitude, fix.longitude,
                      fix.from_storage ? "NVS" : "GNSS");
    } else {
#ifdef GNSS_FALLBACK_LAT
        doc["latitude"] = GNSS_FALLBACK_LAT;
        doc["longitude"] = GNSS_FALLBACK_LON;
        Serial.printf("[PROV] Using fallback coords: %.5f, %.5f (GNSS no-fix, cantina)\n",
                      (double)GNSS_FALLBACK_LAT, (double)GNSS_FALLBACK_LON);
#else
        Serial.println("[PROV] No GNSS fix available: omitting coordinates");
#endif
    }
#else
    // Hardcoded fallback until a GNSS module is attached (see ROADMAP v1.3).
    doc["latitude"] = 41.9028;
    doc["longitude"] = 12.4964;
#endif
    
    String requestBody;
    serializeJson(doc, requestBody);

    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode == 200 || httpResponseCode == 201) {
        String response = http.getString();
        JsonDocument resDoc;
        deserializeJson(resDoc, response);
        
        int newID = resDoc["sensor_id"];
        if (newID > 0) {
            preferences.begin("quake-config", false);
            preferences.putInt("sensor_id", newID);
            preferences.end();
            globalSensorID = newID;
            Serial.printf("[PROV] SUCCESS! Assigned Sensor ID: %d\n", globalSensorID);
            Serial.printf("[PROV] Public key: %s\n", crypto().getPublicKeyHex().c_str());
            http.end();
            return true;
        }
    } else {
        Serial.printf("[PROV] Registration Failed. HTTP Code: %d\n", httpResponseCode);
    }
    http.end();
    return false;
}

// --------------------------------------------------------------------------
// TASK 1: SENSOR ACQUISITION
// --------------------------------------------------------------------------
void sensorTask(void *pvParameters) { // NOSONAR
    sensors_event_t event;

    // Pure-C++ STA/LTA core, shared with the host SIL validation (same source).
    SeismicDetector detector(HPF_ALPHA, TRIGGER_RATIO, NOISE_FLOOR);

    Serial.println("[SENSOR] Task Active. Stabilizing and filling buffers...");
    
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(10); // Exactly 100Hz

    for(;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        accel.getEvent(&event);
        float raw_mag = SeismicDetector::norm3(event.acceleration.x, event.acceleration.y, event.acceleration.z);

        // Clock-injected: the detector receives the same millis() the firmware would use.
        if (detector.push(raw_mag, millis())) {
            Serial.printf("[SENSOR] EARTHQUAKE! Ratio: %.2f (Mag: %.3f G)\n", detector.lastRatio(), detector.lastSTA());
            SeismicEvent evt = { detector.lastRatio(), millis() };
            xQueueSend(eventQueue, &evt, 0);
        }
    }
}

// --------------------------------------------------------------------------
// TASK 2: NETWORK DISPATCH (MQTT + USB SERIAL FALLBACK)
// --------------------------------------------------------------------------
static void deliverEvent(PubSubClient& mqttClient, DeliveryPath path, int val, time_t evt_time, const String& sig);

#if SERIAL_FALLBACK_ENABLED
static void drainRetention(RetentionRing<RETENTION_CAPACITY>& retention,
                           PubSubClient& mqttClient,
                           bool mqttUp, bool usbHost, bool timeValid,
                           time_t epochAtSync, unsigned long millisAtSync) {
    if (retention.empty() || !timeValid) return;
    DeliveryPath path = decidePath(mqttUp && timeValid, usbHost, timeValid); // NOSONAR(cpp:S5811) - using enum requires C++20
    if (path != DeliveryPath::MQTT && path != DeliveryPath::SERIAL_CDC) return;
    SerialEvent retainedEvt;
    while (retention.pop(retainedEvt)) {
        time_t report_time = epochAtSync + (millis() - millisAtSync) / 1000;
        String payload = String(retainedEvt.value) + ":" + String(report_time);
        String sig = crypto().signMessage(payload);
        deliverEvent(mqttClient, path, retainedEvt.value, report_time, sig);
        triggerQuakeLed();
    }
}
#endif

static void deliverEvent(PubSubClient& mqttClient, DeliveryPath path, int val, time_t evt_time, const String& sig) {
    if (path == DeliveryPath::MQTT) { // NOSONAR(cpp:S5811)
        JsonDocument doc;
        doc["value"] = val;
        doc["sensor_id"] = globalSensorID;
        doc["device_timestamp"] = evt_time;
        doc["signature_hex"] = sig;

        String json;
        serializeJson(doc, json);

        // FIRE AND FORGET! Milliseconds instead of HTTP round-trips!
        if (mqttClient.publish("quakeguard/telemetry", json.c_str())) {
            Serial.println("[NET] MQTT Publish OK.");
        } else {
            Serial.println("[NET] MQTT Publish FAILED.");
        }
    } else {
        // USB serial fallback: machine-readable frame on the CDC port.
        Serial.print(buildSerialFrame(SERIAL_FALLBACK_MARKER, val, globalSensorID,
                                      (long)evt_time, sig.c_str()).c_str());
        Serial.println();
        Serial.println("[NET] Serial Fallback Publish OK.");
    }
}

void networkTask(void *pvParameters) { // NOSONAR
    WiFiClientSecure espClient;
    espClient.setInsecure();
    PubSubClient mqttClient(espClient);

    mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);

    // NTP sync happens opportunistically; event dispatch never blocks on it.
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

#if SERIAL_FALLBACK_ENABLED
    // Software clock anchored at the first successful NTP sync, so retained
    // events keep a valid wall time even after WiFi drops.
    time_t epochAtSync = 0;
    unsigned long millisAtSync = 0;
    bool timeValid = false;

    RetentionRing<RETENTION_CAPACITY> retention;
#endif

    SeismicEvent receivedEvt;
    unsigned long lastMqttAttempt = 0;

    for (;;) {
        mqttClient.loop(); // Process incoming keepalives

        // Opportunistic MQTT (re)connection, throttled to 5 s: never blocks.
        bool mqttUp = mqttClient.connected();
        // Blue LED: double blink WiFi, single blink server, solid connected (also handles red auto-off)
        updateConnectionLed(WiFi.status() == WL_CONNECTED, mqttUp);
        if (!mqttUp && WiFi.status() == WL_CONNECTED && (millis() - lastMqttAttempt > 5000)) {
            lastMqttAttempt = millis();
            String clientId = "QuakeGuard-" + WiFi.macAddress();
            if (mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
                Serial.println("[NET] MQTT Reconnected.");
                mqttUp = true;
            }
        }

#if SERIAL_FALLBACK_ENABLED
        if (!timeValid) {
            auto now = std::chrono::system_clock::now();
            time_t t = std::chrono::system_clock::to_time_t(now);
            if (t > 1600000000) {
                epochAtSync = t;
                millisAtSync = millis();
                timeValid = true;
                Serial.println("[NET] NTP time synchronized.");
            }
        }

        bool usbHost = Serial.isConnected(); // HWCDC: true only with a real USB host

        // Drain retained events to a path that just became available. Events
        // are re-signed with the current wall time (reporting time) so the
        // backend's +/-300 s replay window accepts the retransmission.
        drainRetention(retention, mqttClient, mqttUp, usbHost, timeValid, epochAtSync, millisAtSync);
#endif

        // Wait for a seismic event from the queue (up to 100 ms).
        if (xQueueReceive(eventQueue, &receivedEvt, pdMS_TO_TICKS(100)) == pdTRUE) {
            if (globalSensorID == 0) continue; // Unregistered

            const std::chrono::system_clock::time_point now_chrono = std::chrono::system_clock::now();
            unsigned long age_ms = millis() - receivedEvt.event_millis;
            time_t evt_time = std::chrono::system_clock::to_time_t(now_chrono - std::chrono::milliseconds(age_ms));

            auto val = static_cast<int>(receivedEvt.magnitude * 100);
            String payload = String(val) + ":" + String(evt_time);
            String sig = crypto().signMessage(payload);

#if SERIAL_FALLBACK_ENABLED
            {
                DeliveryPath path = decidePath(mqttUp && timeValid, usbHost, timeValid);
                switch (path) { // NOSONAR(cpp:S5811) - using enum requires C++20, ESP32 gnu++11
                    case DeliveryPath::MQTT:
                    case DeliveryPath::SERIAL_CDC:
                        deliverEvent(mqttClient, path, val, evt_time, sig);
                        triggerQuakeLed();
                        break;
                    case DeliveryPath::RETAIN:
                        retention.push({val, static_cast<long>(evt_time)});
                        Serial.println("[NET] No delivery path: event retained in ring.");
                        break;
                }
            }
#else
            deliverEvent(mqttClient, DeliveryPath::MQTT, val, evt_time, sig); // NOSONAR(cpp:S5811)
            triggerQuakeLed();
#endif
        }
    }
}

// --------------------------------------------------------------------------
// TASK 3 (OPTIONAL): GNSS ACQUISITION
// --------------------------------------------------------------------------
#ifdef GNSS_ENABLED
void gnssTask(void *pvParameters) { // NOSONAR
    gnss().begin();
    for(;;) {
        gnss().loop();
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}
#endif

// --------------------------------------------------------------------------
// MAIN ENTRY POINTS
// --------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(2000); 

    // LEDs: blue (10) connection state, red (3) quake indicator
    pinMode(LED_BLUE_PIN, OUTPUT);
    pinMode(LED_RED_PIN, OUTPUT);
    digitalWrite(LED_BLUE_PIN, LOW);
    digitalWrite(LED_RED_PIN, LOW);
    ledBootTest(); // verify wiring: 2x blink both LEDs

    Serial.println("\n\n[BOOT] QuakeGuard v1.3.0 GNSS+PPS+LED");
    
    crypto().init();
    
    preferences.begin("quake-config", false);
    globalSensorID = preferences.getInt("sensor_id", 0);
    preferences.end();

    if (globalSensorID > 0) {
        Serial.printf("[BOOT] Device Registered. ID: %d\n", globalSensorID);
    } else {
        Serial.println("[BOOT] Device UNREGISTERED. Entering Provisioning Mode...");
    }

    WiFiManager wm;
    wm.setConfigPortalTimeout(180); 
    
    Serial.println("[NET] Initializing WiFiManager...");
    if (!wm.autoConnect("QuakeGuard-Setup")) {
        Serial.println("[NET] WiFi Failed. Offline Mode.");
    } else {
        WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE, IPAddress(8,8,4,4));
        Serial.println("[NET] WiFi Connected.");
        if (globalSensorID == 0) {
            performProvisioning();
        }
    }

    Wire.setPins(I2C_SDA_PIN, I2C_SCL_PIN);
    Wire.begin();
    Wire.setClock(I2C_CLOCK_SPEED); 
    delay(100); 

    // ADXL345 init with retry — JLCPCB J3 on GPIO 7/8, allow cold-boot settling
    bool adxlOk = false;
    for (int attempt = 0; attempt < 3; attempt++) {
        if (accel.begin(0x53) || accel.begin(0x1D)) { adxlOk = true; break; }
        Serial.printf("[SENSOR] ADXL init failed, retry %d/3...\n", attempt + 1);
        // blink red rapidly to signal I2C issue
        for (int i = 0; i < 3; i++) { digitalWrite(LED_RED_PIN, HIGH); delay(80); digitalWrite(LED_RED_PIN, LOW); delay(80); }
        delay(500);
    }
    if (!adxlOk) {
        Serial.println("[FATAL] Sensor Hardware Error — check J3 wiring, 3.3V, SDA 7/SCL 8, or try re-seating ADXL module.");
        // do not halt forever: keep networkTask alive so blue LED and provisioning can be observed
        digitalWrite(LED_RED_PIN, HIGH); // solid red = sensor fault
        // still create tasks, sensorTask will keep reporting error via Serial
    } else {
        accel.setDataRate(ADXL345_DATARATE_100_HZ);
        accel.setRange(ADXL345_RANGE_16_G);
    }

    eventQueue = xQueueCreate(20, sizeof(SeismicEvent));
    xTaskCreate(sensorTask, "SensorTask", 8192, NULL, 5, NULL);
    xTaskCreate(networkTask, "NetworkTask", 8192, NULL, 1, NULL);
#ifdef GNSS_ENABLED
    xTaskCreate(gnssTask, "GnssTask", 8192, NULL, 2, NULL);
#endif

    Serial.println("[SYS] System Running.");
}

void loop() {
    vTaskDelete(NULL); 
}