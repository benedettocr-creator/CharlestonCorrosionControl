import asyncio
import struct
from datetime import datetime, timezone
from bleak import BleakClient
import httpx

# --- Config ---
SENSOR_MAC = "XX:XX:XX:XX:XX:XX"   # replace with your sensor's MAC
SENSOR_CODE = "SENSOR_001"          # must match a code in your DB
API_URL = "http://YOUR_BACKEND_IP:8001/sensor-readings/"

# SensorPush GATT characteristic UUIDs
SERVICE_UUID      = "EF090000-11D6-42BA-93B8-9DD7EC090AB0"
CHAR_TEMPERATURE  = "EF090080-11D6-42BA-93B8-9DD7EC090AA9"
CHAR_HUMIDITY     = "EF090081-11D6-42BA-93B8-9DD7EC090AA9"
CHAR_PRESSURE     = "EF090082-11D6-42BA-93B8-9DD7EC090AA9"

TRIGGER = bytes([0x01, 0x00, 0x00, 0x00])  # write this to trigger a read

async def read_sensor():
    print(f"Connecting to {SENSOR_MAC}...")
    async with BleakClient(SENSOR_MAC) as client:
        # Trigger + read temperature (also populates humidity)
        await client.write_gatt_char(CHAR_TEMPERATURE, TRIGGER)
        await asyncio.sleep(0.2)  # wait for sensor to update

        temp_raw = await client.read_gatt_char(CHAR_TEMPERATURE)
        hum_raw  = await client.read_gatt_char(CHAR_HUMIDITY)
        pres_raw = await client.write_gatt_char(CHAR_PRESSURE, TRIGGER)
        await asyncio.sleep(0.2)
        pres_raw = await client.read_gatt_char(CHAR_PRESSURE)

        # Decode little-endian int32, values are in hundredths
        temp_c    = struct.unpack_from('<i', temp_raw)[0] / 100.0
        humidity  = struct.unpack_from('<i', hum_raw)[0] / 100.0
        pressure  = struct.unpack_from('<i', pres_raw)[0] / 100.0  # Pascals

        print(f"Temp: {temp_c}°C | Humidity: {humidity}% | Pressure: {pressure} Pa")

        # POST to your backend
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

asyncio.run(read_sensor())
