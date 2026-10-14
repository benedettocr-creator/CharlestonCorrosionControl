#!/usr/bin/env python3
"""
Corrosion sensor reader — Charleston Corrosion Control project
Hardware: Raspberry Pi + SensorPush HTP.xw (via SensorPush Cloud API)

Run on EACH Pi. Change SENSOR_CODE and SENSORPUSH_SENSOR_ID below.
"""

import time
import csv
import os
import requests
from datetime import datetime, timezone

# ─── CONFIGURE THESE ON EACH PI ──────────────────────────────────────────────
SENSOR_CODE          = "PI_01"               # Change to "PI_02" on second Pi
SENSORPUSH_EMAIL     = "your@email.com"      # Your SensorPush account email
SENSORPUSH_PASSWORD  = "yourpassword"        # Your SensorPush account password
SENSORPUSH_SENSOR_ID = "XXXXXXXX.YYYYYYYY"  # Run find_sensor_ids.py to get this
BACKEND_URL          = "http://YOUR_SERVER_IP:8001/sensor-readings/"
READ_INTERVAL_SEC    = 300                   # Read every 5 minutes
LOCAL_CSV            = f"readings_{SENSOR_CODE}.csv"
# ─────────────────────────────────────────────────────────────────────────────

SP_BASE = "https://api.sensorpush.com/api/v1"
HPA_TO_IWG = 0.40147   # 1 hPa = 0.40147 inches of water gauge


def sp_get_token() -> str:
    """Authenticate with SensorPush and return an access token."""
    r = requests.post(
        f"{SP_BASE}/oauth/authorize",
        json={"email": SENSORPUSH_EMAIL, "password": SENSORPUSH_PASSWORD},
        timeout=15,
    )
    r.raise_for_status()
    code = r.json()["authorization"]

    r2 = requests.post(
        f"{SP_BASE}/oauth/accesstoken",
        json={"authorization": code},
        timeout=15,
    )
    r2.raise_for_status()
    return r2.json()["accesstoken"]


def sp_latest_sample(token: str) -> dict:
    """Fetch the single most-recent reading from the configured sensor."""
    r = requests.post(
        f"{SP_BASE}/samples",
        headers={"Authorization": token},
        json={"sensors": [SENSORPUSH_SENSOR_ID], "limit": 1},
        timeout=15,
    )
    r.raise_for_status()
    sensor_data = r.json().get("sensors", {})
    samples = sensor_data.get(SENSORPUSH_SENSOR_ID, [])
    if not samples:
        raise RuntimeError(f"No samples returned for sensor ID: {SENSORPUSH_SENSOR_ID}")
    return samples[0]


def fahrenheit_to_celsius(f: float) -> float:
    return round((f - 32.0) * 5.0 / 9.0, 2)


def build_payload(sample: dict) -> dict:
    """Convert a SensorPush sample to the backend SensorReadingRequest format."""
    temp_f = sample["temperature"]
    temp_c = fahrenheit_to_celsius(temp_f)
    rh = round(float(sample["humidity"]), 2)

    pressure_hpa = sample.get("barometric_pressure")
    pressure_iwg = round(pressure_hpa * HPA_TO_IWG, 2) if pressure_hpa else 406.8

    return {
        "sensor_code":  SENSOR_CODE,
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "temp_c":       temp_c,
        "rh_percent":   rh,
        "pressure_iwg": pressure_iwg,
        "sensor_valid": True,
        "event_flag":   0,
    }


def post_to_backend(payload: dict) -> bool:
    try:
        r = requests.post(BACKEND_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"  Backend accepted reading (HTTP {r.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print(f"  Backend unreachable at {BACKEND_URL} — saving to local CSV.")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"  Backend rejected reading: {e} — saving to local CSV.")
        return False


def save_local_csv(payload: dict):
    file_exists = os.path.isfile(LOCAL_CSV)
    with open(LOCAL_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=payload.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(payload)
    print(f"  Saved locally → {LOCAL_CSV}")


def main():
    print(f"[Corrosion Reader] sensor={SENSOR_CODE}  interval={READ_INTERVAL_SEC}s")
    token = None
    token_refresh_at = 0.0

    while True:
        now = time.time()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{ts}] Collecting reading...")

        try:
            # SensorPush tokens expire after ~1 hour; refresh 5 min early
            if now >= token_refresh_at:
                print("  Refreshing SensorPush token...")
                token = sp_get_token()
                token_refresh_at = now + 3300

            sample = sp_latest_sample(token)
            print(
                f"  Temp: {fahrenheit_to_celsius(sample['temperature'])}°C  "
                f"Humidity: {sample['humidity']:.1f}%  "
                f"Pressure: {sample.get('barometric_pressure', 'N/A')} hPa"
            )

            payload = build_payload(sample)
            if not post_to_backend(payload):
                save_local_csv(payload)

        except requests.exceptions.RequestException as e:
            print(f"  Network error: {e}")
            token_refresh_at = 0.0  # Force re-auth on next cycle

        time.sleep(READ_INTERVAL_SEC)


if __name__ == "__main__":
    main()
