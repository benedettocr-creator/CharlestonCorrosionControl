#!/usr/bin/env python3
"""
Run this ONCE on either Pi to discover your SensorPush sensor IDs.
Copy the IDs into sensor_reader.py on each Pi.
"""

import requests

EMAIL    = "your@email.com"
PASSWORD = "yourpassword"
SP_BASE  = "https://api.sensorpush.com/api/v1"


def main():
    print("Authenticating...")
    r = requests.post(f"{SP_BASE}/oauth/authorize",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    r.raise_for_status()
    code = r.json()["authorization"]

    r2 = requests.post(f"{SP_BASE}/oauth/accesstoken",
                       json={"authorization": code}, timeout=15)
    r2.raise_for_status()
    token = r2.json()["accesstoken"]

    print("Fetching sensor list...\n")
    r3 = requests.post(f"{SP_BASE}/devices/sensors",
                       headers={"Authorization": token},
                       json={}, timeout=15)
    r3.raise_for_status()

    sensors = r3.json()
    if not sensors:
        print("No sensors found. Make sure your HTP.xw devices are connected in the SensorPush app.")
        return

    for sensor_id, info in sensors.items():
        print(f"Sensor ID : {sensor_id}")
        print(f"  Name    : {info.get('name', 'unnamed')}")
        print(f"  Model   : {info.get('deviceId', 'unknown')}")
        print(f"  Battery : {info.get('battery', {}).get('voltage', 'N/A')} V")
        print()

    print("Copy each sensor ID into SENSORPUSH_SENSOR_ID in sensor_reader.py.")


if __name__ == "__main__":
    main()
