/**
 * Project: QuakeGuard - Professional Seismic Node
 * Version: 3.3.0-PROV-REFACTORED
 * Target Hardware: ESP32-C3 SuperMini + ADXL345
 * Author: GiZano
 *
 * CHANGELOG:
 * - Merged v3.2.0 Automated Device Handshake (Provisioning) with v3.0.0 FreeRTOS Refactoring.
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

// --------------------------------------------------------------------------
// HARDWARE & SERVER CONFIGURATION
// --------------------------------------------------------------------------
constexpr int I2C_SDA_PIN = 7;
constexpr int I2C_SCL_PIN = 8;
constexpr int I2C_CLOCK_SPEED = 100000;

#ifndef SERVER_HOST
  #define SERVER_HOST "your-tunnel-id.ngrok-free.app"
#endif
#ifndef SERVER_PORT
  #define SERVER_PORT 80
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

#ifdef SENSOR_ID
    if (SENSOR_ID > 0) {
        Serial.printf("[PROV] Using compile-time SENSOR_ID: %d\n", SENSOR_ID);
        preferences.begin("quake-config", false);
        preferences.putInt("sensor_id", SENSOR_ID);
        preferences.end();
        globalSensorID = SENSOR_ID;
        Serial.printf("[PROV] SUCCESS! Assigned Sensor ID: %d\n", globalSensorID);
        Serial.printf("[PROV] Public key: %s\n", crypto().getPublicKeyHex().c_str());
        return true;
    }
#endif

    HTTPClient http;
    String url = String("https://") + SERVER_HOST + SERVER_REGISTER_PATH;

    Serial.printf("[PROV] Connecting to: %s\n", url.c_str());
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("ngrok-skip-browser-warning", "true");
    http.setTimeout(15000);

    JsonDocument doc;
    doc["public_key_hex"] = crypto().getPublicKeyHex();
    doc["mac_address"] = WiFi.macAddress();
    doc["enrollment_token"] = ENROLLMENT_TOKEN;
    
    doc["latitude"] = 41.9028;
    doc["longitude"] = 12.4964;
    
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
// TASK 2: NETWORK DISPATCH (MQTT REFACTOR)
// --------------------------------------------------------------------------
void networkTask(void *pvParameters) { // NOSONAR
    WiFiClientSecure espClient;
    espClient.setInsecure();
    PubSubClient mqttClient(espClient);
    
    mqttClient.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);

    while (WiFi.status() != WL_CONNECTED) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

    SeismicEvent receivedEvt;
    for(;;) {
        // Keep MQTT connection alive
        if (!mqttClient.connected()) {
            Serial.print("[NET] Reconnecting to MQTT Broker...");
            // Use MAC address as unique client ID
            String clientId = "QuakeGuard-" + WiFi.macAddress();
            if (mqttClient.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)) {
                Serial.println(" Connected!");
            } else {
                vTaskDelay(pdMS_TO_TICKS(2000));
                continue;
            }
        }
        /* 
         * NOTE: xQueueReceive below blocks for up to 100ms if empty.
         * This drops the effective mqttClient.loop() frequency to ~10Hz.
         * For our low-volume anomaly queue and standard 15s keep-alives, 
         * this is completely safe and saves CPU cycles.
         */
        mqttClient.loop(); // Process incoming keepalives

        // Wait for a seismic event from the queue
        if (xQueueReceive(eventQueue, &receivedEvt, pdMS_TO_TICKS(100)) == pdTRUE) {
            
            if (globalSensorID == 0) continue; // Unregistered

            auto now_chrono = std::chrono::system_clock::now();
            unsigned long age_ms = millis() - receivedEvt.event_millis;
            time_t evt_time = std::chrono::system_clock::to_time_t(now_chrono - std::chrono::milliseconds(age_ms));
            
            auto val = static_cast<int>(receivedEvt.magnitude * 100);
            String payload = String(val) + ":" + String(evt_time);
            String sig = crypto().signMessage(payload);

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
        }
    }
}

// --------------------------------------------------------------------------
// MAIN ENTRY POINTS
// --------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    delay(2000); 

    Serial.println("\n\n[BOOT] QuakeGuard v3.3 PROV-REFACTORED");
    
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

    if(!accel.begin(0x53) && !accel.begin(0x1D)) {
        Serial.println("[FATAL] Sensor Hardware Error.");
        while(true) vTaskDelay(100);
    }
    
    accel.setDataRate(ADXL345_DATARATE_100_HZ);
    accel.setRange(ADXL345_RANGE_16_G);

    eventQueue = xQueueCreate(20, sizeof(SeismicEvent));
    xTaskCreate(sensorTask, "SensorTask", 8192, NULL, 5, NULL);
    xTaskCreate(networkTask, "NetworkTask", 8192, NULL, 1, NULL);

    Serial.println("[SYS] System Running.");
}

void loop() {
    vTaskDelete(NULL); 
}