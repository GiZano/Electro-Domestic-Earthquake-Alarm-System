/**
 * Magnitude estimation — mirrors backend `src/worker.py:estimate_magnitude`.
 * M_IoT = log10(PGA_calib) + b, with PGA = raw_value / SENSOR_SCALE.
 */

export const SENSOR_SCALE = 100.0; // raw value -> m/s²
export const K_CALIBRATION = 1.6; // MyShake-style MEMS calibration factor
export const B_OFFSET = 3.0; // anchor: PGA 0.07 m/s² ≈ M3.85

export const ALERT_MAGNITUDE = 4.5; // worker publishes a CRITICAL alert at this
export const CAUTION_MAGNITUDE = 4.0; // amber band below the alert threshold

export function estimateMagnitude(sensorValue: number): number {
  const pga = sensorValue / SENSOR_SCALE;
  const pgaCalib = pga / K_CALIBRATION;
  if (pgaCalib <= 0) return 0;
  const magnitude = Math.log10(pgaCalib) + B_OFFSET;
  return Math.max(0, Math.min(magnitude, 9.9));
}

export type Threshold = "live" | "caution" | "alert";

export function thresholdOf(sensorValue: number): Threshold {
  const magnitude = estimateMagnitude(sensorValue);
  if (magnitude >= ALERT_MAGNITUDE) return "alert";
  if (magnitude >= CAUTION_MAGNITUDE) return "caution";
  return "live";
}
