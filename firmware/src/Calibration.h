#ifndef QUAKEGUARD_CALIBRATION_H
#define QUAKEGUARD_CALIBRATION_H

#include <Adafruit_ADXL345_U.h>
#include <Arduino.h>

/**
 * Perform a static calibration of the ADXL345 accelerometer.
 * Assumes the sensor is resting flat on a level surface (Z = 1G, X = 0G, Y = 0G).
 * Reads multiple samples, calculates the average error, and updates the hardware 
 * offset registers (OFSX, OFSY, OFSZ).
 */
inline void calibrateADXL345(Adafruit_ADXL345_Unified& accel) {
    Serial.println("[CAL] Starting ADXL345 hardware calibration...");
    Serial.println("[CAL] Please ensure the sensor is resting flat and motionless.");
    
    // Allow sensor to stabilize
    delay(1000);

    float sumX = 0;
    float sumY = 0;
    float sumZ = 0;
    const int numSamples = 100;
    
    for (int i = 0; i < numSamples; i++) {
        sensors_event_t event;
        accel.getEvent(&event);
        sumX += event.acceleration.x;
        sumY += event.acceleration.y;
        sumZ += event.acceleration.z;
        delay(10); // 100 Hz sampling rate
    }

    float avgX = sumX / numSamples;
    float avgY = sumY / numSamples;
    float avgZ = sumZ / numSamples;

    // Convert from m/s^2 to G (1 G = 9.80665 m/s^2)
    const float GRAVITY = 9.80665f;
    float errX_g = avgX / GRAVITY;
    float errY_g = avgY / GRAVITY;
    float errZ_g = (avgZ / GRAVITY) - 1.0f; // Z should be 1G

    Serial.printf("[CAL] Measured average (G) -> X: %.3f, Y: %.3f, Z: %.3f\n", avgX/GRAVITY, avgY/GRAVITY, avgZ/GRAVITY);
    Serial.printf("[CAL] Error (G) -> X: %.3f, Y: %.3f, Z: %.3f\n", errX_g, errY_g, errZ_g);

    // The ADXL345 offset registers are 8-bit, 2's complement, with a scale factor of 15.6 mg/LSB.
    // Offset value = - (Error in G) / 0.0156
    int8_t ofsX = -round(errX_g / 0.0156f);
    int8_t ofsY = -round(errY_g / 0.0156f);
    int8_t ofsZ = -round(errZ_g / 0.0156f);

    Serial.printf("[CAL] Computed OFS registers -> OFSX: %d, OFSY: %d, OFSZ: %d\n", ofsX, ofsY, ofsZ);

    // Write to hardware registers (Adafruit ADXL345 Unified library wrapper)
    // 0x1E = OFSX, 0x1F = OFSY, 0x20 = OFSZ
    // We use the underlying Adafruit_Sensor/Adafruit_ADXL345 getDevice API to write
    // Since getDevice is not exposed with writeRegister directly in all versions, 
    // we use I2C Wire directly or Adafruit's writeRegister.
    // For safety with Adafruit's library we use Adafruit_I2CDevice or standard Wire.
    
    Wire.beginTransmission(0x53); // Default I2C address, might be 0x1D
    Wire.write(0x1E); // OFSX
    Wire.write(ofsX);
    Wire.write(ofsY); // Auto-increments to OFSY
    Wire.write(ofsZ); // Auto-increments to OFSZ
    if (Wire.endTransmission() != 0) {
        // Try alternate address
        Wire.beginTransmission(0x1D);
        Wire.write(0x1E);
        Wire.write(ofsX);
        Wire.write(ofsY);
        Wire.write(ofsZ);
        Wire.endTransmission();
    }

    Serial.println("[CAL] Calibration applied to hardware registers.");
}

#endif // QUAKEGUARD_CALIBRATION_H
