import asyncio
import struct
from datetime import datetime, timezone
from bleak import BleakClient
import httpx
from picamera2 import Picamera2
import os

# --- Config ---
SENSOR_MAC = "XX:XX:XX:XX:XX:XX"   # replace with your sensor's MAC
SENSOR_CODE = "SENSOR_001"          # must match a code in your DB
API_URL = "http://YOUR_BACKEND_IP:8001/sensor-readings/"

PHOTO_TIMES = {"07:00", "19:00"}    # times to take a photo (24-hour HH:MM)
PHOTO_DIR = "/home/pi/photos"       # folder where photos are saved

# SensorPush GATT characteristic UUIDs
SERVICE_UUID      = "EF090000-11D6-42BA-93B8-9DD7EC090AB0"
CHAR_TEMPERATURE  = "EF090080-11D6-42BA-93B8-9DD7EC090AA9"
CHAR_HUMIDITY     = "EF090081-11D6-42BA-93B8-9DD7EC090AA9"
CHAR_PRESSURE     = "EF090082-11D6-42BA-93B8-9DD7EC090AA9"

TRIGGER = bytes([0x01, 0x00, 0x00, 0x00])


def capture_photo():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(PHOTO_DIR, f"photo_{timestamp}.jpg")

    cam = Picamera2()
    cam.configure(cam.create_still_configuration())
    cam.start()
    cam.capture_file(filename)
    cam.stop()
    cam.close()
    print(f"Photo saved: {filename}")


async def read_sensor():
    print(f"Connecting to {SENSOR_MAC}...")
    async with BleakClient(SENSOR_MAC) as client:
        await client.write_gatt_char(CHAR_TEMPERATURE, TRIGGER)
        await asyncio.sleep(0.2)

        temp_raw = await client.read_gatt_char(CHAR_TEMPERATURE)
        hum_raw  = await client.read_gatt_char(CHAR_HUMIDITY)
        await client.write_gatt_char(CHAR_PRESSURE, TRIGGER)
        await asyncio.sleep(0.2)
        pres_raw = await client.read_gatt_char(CHAR_PRESSURE)

        temp_c   = struct.unpack_from('<i', temp_raw)[0] / 100.0
        humidity = struct.unpack_from('<i', hum_raw)[0] / 100.0
        pressure = struct.unpack_from('<i', pres_raw)[0] / 100.0

        print(f"Temp: {temp_c}°C | Humidity: {humidity}% | Pressure: {pressure} Pa")

        payload = {
            "sensor_code": SENSOR_CODE,
            "temperature": temp_c,
            "humidity": humidity,
            "pressure": pressure,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        async with httpx.AsyncClient() as http:
            response = await http.post(API_URL, json=payload)
            print(f"API response: {response.status_code}")


if datetime.now().strftime("%H:%M") in PHOTO_TIMES:
    capture_photo()

asyncio.run(read_sensor())
