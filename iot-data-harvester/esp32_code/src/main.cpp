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

// --- Cryptographic Libraries (MbedTLS) ---
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/ecdsa.h"
#include "mbedtls/pk.h"
#include "mbedtls/error.h"
#include "RingBuffer.h"

// --------------------------------------------------------------------------
// HARDWARE & SERVER CONFIGURATION
// --------------------------------------------------------------------------
constexpr int I2C_SDA_PIN = 7;
constexpr int I2C_SCL_PIN = 8;
constexpr int I2C_CLOCK_SPEED = 100000;

#ifndef SERVER_HOST
  #define SERVER_HOST "10.228.201.82"
#endif
#ifndef SERVER_PORT
  #define SERVER_PORT 8000
#endif
#ifndef SERVER_PATH
  #define SERVER_PATH "/misurations/"
#endif
#ifndef SERVER_REGISTER_PATH
  #define SERVER_REGISTER_PATH "/devices/register"
#endif

#ifndef ENROLLMENT_TOKEN
  #ifndef __INTELLISENSE__ 
    // 1. If the REAL compiler doesn't see the token, crash the build to protect us!
    #error "🚨 CRITICAL BUILD ERROR: ENROLLMENT_TOKEN is missing! Add it to esp32_config.env"
  #else 
    // 2. If VSCode's UI is looking at the file, give it a fake token so it stops crying on line 168!
    #define ENROLLMENT_TOKEN "vscode_dummy_token"
  #endif
#endif

// Global Dynamic Sensor ID
int globalSensorID = 0;
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);

// --------------------------------------------------------------------------
// RTOS & DSP DEFINITIONS
// --------------------------------------------------------------------------
QueueHandle_t eventQueue;

struct SeismicEvent {
    float magnitude;
    unsigned long event_millis;
};

constexpr float ALPHA_LTA = 0.05f;
constexpr float ALPHA_STA = 0.40f;
constexpr float TRIGGER_RATIO = 1.8f;
constexpr float NOISE_FLOOR = 0.04f;
constexpr float HPF_ALPHA = 0.9f;

// --------------------------------------------------------------------------
// CRYPTO SUBSYSTEM
// --------------------------------------------------------------------------
Preferences preferences;
mbedtls_entropy_context entropy;
mbedtls_ctr_drbg_context ctr_drbg;
mbedtls_pk_context pk_context;

void initCrypto() {
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    mbedtls_pk_init(&pk_context);

    const char *pers = "quake_guard_signer";
    mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy, (const unsigned char *)pers, strlen(pers));

    preferences.begin("quake-keys", false);

    if (!preferences.isKey("priv_key")) {
        Serial.println("[SEC] Generating New ECDSA Key Pair...");
        mbedtls_pk_setup(&pk_context, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY));
        mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(pk_context), mbedtls_ctr_drbg_random, &ctr_drbg);
        unsigned char priv_buf[128];
        int ret = mbedtls_pk_write_key_der(&pk_context, priv_buf, sizeof(priv_buf));
        preferences.putBytes("priv_key", priv_buf + sizeof(priv_buf) - ret, ret);
        Serial.println("[SEC] Keys Generated.");
    } else {
        Serial.println("[SEC] Loading Existing Keys...");
        size_t len = preferences.getBytesLength("priv_key");
        uint8_t buf[len];
        preferences.getBytes("priv_key", buf, len);
        mbedtls_pk_parse_key(&pk_context, buf, len, NULL, 0);
    }
}

String getPublicKeyHex() {
    unsigned char pub_buf[128];
    int ret = mbedtls_pk_write_pubkey_der(&pk_context, pub_buf, sizeof(pub_buf));
    int len = ret;
    int start_index = sizeof(pub_buf) - len;

    String hexKey = "";
    for(int i = start_index; i < sizeof(pub_buf); i++) {
        char buf[3];
        sprintf(buf, "%02x", pub_buf[i]);
        hexKey += buf;
    }
    return hexKey;
}

String signMessage(const String& message) {
    unsigned char hash[32];
    unsigned char sig[MBEDTLS_ECDSA_MAX_LEN];
    size_t sig_len = 0;
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 0);
    mbedtls_md_starts(&ctx);
    mbedtls_md_update(&ctx, (const unsigned char*)message.c_str(), message.length());
    mbedtls_md_finish(&ctx, hash);
    mbedtls_md_free(&ctx);
    mbedtls_pk_sign(&pk_context, MBEDTLS_MD_SHA256, hash, 0, sig, &sig_len, mbedtls_ctr_drbg_random, &ctr_drbg);
    
    String hexSig = "";
    for(size_t i = 0; i < sig_len; i++) { 
        char buf[3]; 
        sprintf(buf, "%02x", sig[i]); 
        hexSig += buf; 
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
    String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + SERVER_REGISTER_PATH;
    
    Serial.printf("[PROV] Connecting to: %s\n", url.c_str());
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    JsonDocument doc;
    doc["public_key_hex"] = getPublicKeyHex();
    doc["mac_address"] = WiFi.macAddress();
    doc["enrollment_token"] = ENROLLMENT_TOKEN;
    
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
void sensorTask(void *pvParameters) {
    float prev_raw_mag = 9.81f, filtered_mag = 0.0f;
    sensors_event_t event;

    // Instantiate our strict rolling window buffers!
    // At 100Hz: STA = 1 second, LTA = 10 seconds
    RingBuffer<100> staBuffer;
    RingBuffer<1000> ltaBuffer;

    Serial.println("[SENSOR] Task Active. Stabilizing and filling buffers...");
    
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(10); // Exactly 100Hz

    bool inAlarm = false;
    unsigned long alarmStart = 0;

    for(;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        accel.getEvent(&event);
        float raw_mag = sqrt(pow(event.acceleration.x, 2) + pow(event.acceleration.y, 2) + pow(event.acceleration.z, 2));

        // High Pass Filter to remove gravity
        filtered_mag = HPF_ALPHA * (filtered_mag + raw_mag - prev_raw_mag);
        prev_raw_mag = raw_mag;
        float abs_signal = abs(filtered_mag);

        if (abs_signal < NOISE_FLOOR) abs_signal = 0.0f;

        // Push the clean signal into our circular buffers
        staBuffer.push(abs_signal);
        ltaBuffer.push(abs_signal);

        // Wait until the Long-Term window is fully populated before triggering alarms
        if (!ltaBuffer.isFull()) {
            continue; 
        }

        float sta = staBuffer.average();
        float lta = ltaBuffer.average();
        
        // Prevent division by zero if LTA drops too low
        if (lta < 0.01f) lta = 0.01f; 

        float ratio = sta / lta;

        // DEBUG: Uncomment this line to view the rolling windows in the Serial Plotter!
        // Serial.printf("Signal:%.3f,STA:%.3f,LTA:%.3f,Ratio:%.2f\n", abs_signal, sta, lta, ratio);

        if (ratio >= TRIGGER_RATIO && sta > NOISE_FLOOR && !inAlarm) {
            Serial.printf("[SENSOR] EARTHQUAKE! Ratio: %.2f (Mag: %.3f G)\n", ratio, sta);
            SeismicEvent evt = { ratio, millis() };
            xQueueSend(eventQueue, &evt, 0);
            inAlarm = true;
            alarmStart = millis();
        }

        if (inAlarm && (millis() - alarmStart > 5000)) inAlarm = false;
    }
}

// --------------------------------------------------------------------------
// TASK 2: NETWORK DISPATCH
// --------------------------------------------------------------------------
void networkTask(void *pvParameters) {
    WiFiClient client;
    client.setTimeout(2000); 

    while (WiFi.status() != WL_CONNECTED) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
    
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");

    SeismicEvent receivedEvt;
    for(;;) {
        if (xQueueReceive(eventQueue, &receivedEvt, portMAX_DELAY) == pdTRUE) {
            
            if (globalSensorID == 0) {
                Serial.println("[NET] Warning: Event detected but Device is UNREGISTERED!");
                continue;
            }

            if (WiFi.status() != WL_CONNECTED) {
                WiFi.reconnect();
                vTaskDelay(pdMS_TO_TICKS(2000));
                continue;
            }

            time_t now_unix; time(&now_unix);
            unsigned long age_ms = millis() - receivedEvt.event_millis;
            time_t evt_time = now_unix - (age_ms / 1000);
            
            int val = (int)(receivedEvt.magnitude * 100);
            String payload = String(val) + ":" + String(evt_time);
            String sig = signMessage(payload);

            JsonDocument doc;
            doc["value"] = val; 
            doc["misurator_id"] = globalSensorID; 
            doc["device_timestamp"] = evt_time; 
            doc["signature_hex"] = sig;
            String json; serializeJson(doc, json);

            if (client.connect(SERVER_HOST, SERVER_PORT)) {
                client.println(String("POST ") + SERVER_PATH + " HTTP/1.1");
                client.println(String("Host: ") + SERVER_HOST);
                client.println("Content-Type: application/json");
                client.print("Content-Length: "); client.println(json.length());
                client.println("Connection: close"); client.println();
                client.println(json);
                
                while(client.connected() || client.available()) { 
                    if(client.available()) client.readStringUntil('\n'); 
                }
                client.stop();
                Serial.println("[NET] Event Sent OK.");
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
    
    initCrypto();
    
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
        while(1) vTaskDelay(100);
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