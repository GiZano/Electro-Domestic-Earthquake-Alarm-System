#include "GnssModule.h"

#ifdef GNSS_ENABLED

namespace quakeguard_gnss {

float scaleLat(double lat) {
  return static_cast<float>(lat);
}

float scaleLon(double lon) {
  return static_cast<float>(lon);
}

}  // namespace quakeguard_gnss

using namespace quakeguard_gnss;

GnssModule& gnss() {
  static GnssModule instance;
  return instance;
}

volatile unsigned long GnssModule::lastPpsMs_ = 0;
void IRAM_ATTR GnssModule::onPpsIsr() { lastPpsMs_ = millis(); }

void GnssModule::begin() {
  loadLastKnownFix();
  serial_.begin(GPS_SERIAL_BAUD, SERIAL_8N1, GPS_SERIAL_RX_PIN, GPS_SERIAL_TX_PIN);
  Serial.printf("[GNSS] Module started (UART RX=%d TX=%d, baud=%d, PPS=%d)\n",
                GPS_SERIAL_RX_PIN, GPS_SERIAL_TX_PIN, GPS_SERIAL_BAUD, GPS_PPS_PIN);
  // PPS on GPIO 2 (J4-5) — JLCPCB wired, v1.3 will discipline NTP+PPS
  pinMode(GPS_PPS_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(GPS_PPS_PIN), onPpsIsr, RISING);
  Serial.printf("[GNSS] PPS listener armed on GPIO %d\n", GPS_PPS_PIN);
  if (last_known_valid_) {
    Serial.printf("[GNSS] Last-known fix loaded: %.5f, %.5f\n", last_known_lat_, last_known_lon_);
  } else {
    Serial.println("[GNSS] No last-known fix in NVS.");
  }
}

void GnssModule::loop() {
  while (serial_.available()) {
    gps_.encode(serial_.read());
  }
  // PPS pulse logging (GPIO 2, J4-5) — v1.3 discipline will use this timestamp
  static unsigned long lastLoggedPps = 0;
  unsigned long pps = lastPpsMs_;
  if (pps != 0 && pps != lastLoggedPps) {
    Serial.printf("[GNSS] PPS pulse @ %lu ms (GPIO %d)\n", pps, GPS_PPS_PIN);
    lastLoggedPps = pps;
  }

  // Persist a newly observed valid fix (throttled for NVS wear levelling).
  if (gps_.location.isValid() && gps_.location.age() < GNSS_FIX_MAX_AGE_MS) {
    unsigned long now = millis();
    if (now - last_save_ms_ >= GNSS_SAVE_INTERVAL_MS) {
      last_known_valid_ = true;
      last_known_lat_ = scaleLat(gps_.location.lat());
      last_known_lon_ = scaleLon(gps_.location.lng());
      last_save_ms_ = now;
      saveLastKnownFix();
      Serial.printf("[GNSS] FIX locked: %.5f, %.5f\n", last_known_lat_, last_known_lon_);
    }
  }
}

bool GnssModule::getFix(GnssFix& out) {
  out = GnssFix{};
  if (gps_.location.isValid() && gps_.location.age() < GNSS_FIX_MAX_AGE_MS) {
    out.latitude = scaleLat(gps_.location.lat());
    out.longitude = scaleLon(gps_.location.lng());
    out.age_ms = gps_.location.age();
    out.from_storage = false;
    out.valid = true;
    return true;
  }
  if (last_known_valid_) {
    out.latitude = last_known_lat_;
    out.longitude = last_known_lon_;
    out.age_ms = 0;
    out.from_storage = true;
    out.valid = true;
    return true;
  }
  return false;
}

void GnssModule::saveLastKnownFix() {
  prefs_.begin(GNSS_NVS_NAMESPACE, false);
  prefs_.putFloat(GNSS_NVS_LAT, last_known_lat_);
  prefs_.putFloat(GNSS_NVS_LON, last_known_lon_);
  prefs_.putBool(GNSS_NVS_VALID, true);
  prefs_.end();
}

void GnssModule::loadLastKnownFix() {
  prefs_.begin(GNSS_NVS_NAMESPACE, true);
  bool valid = prefs_.getBool(GNSS_NVS_VALID, false);
  if (valid) {
    last_known_valid_ = true;
    last_known_lat_ = prefs_.getFloat(GNSS_NVS_LAT, 0.0f);
    last_known_lon_ = prefs_.getFloat(GNSS_NVS_LON, 0.0f);
  }
  prefs_.end();
}

#endif  // GNSS_ENABLED