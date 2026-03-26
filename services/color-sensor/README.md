# Color Sensor Service

MicroPython service that reads RGB values from a TCS34725 color sensor and exposes them over HTTP.

## What it does

- Connects the device to Wi-Fi.
- Starts an HTTP server on port `80`.
- Handles `GET /color` and returns JSON:

```json
{"r": 0, "g": 0, "b": 0}
```

## Configuration

Edit constants in `main.py` before deploying:

- `SSID` / `PASSWORD`: Wi-Fi credentials
- `WLAN_CONFIG`: static IP settings (or set to `False` for DHCP)
- Pin assignments (`LED_EN`, `SDA_PIN`, `SCL_PIN`)

### Default
```text
LED_EN = GP19
SDA_PIN = GP8
SCL_PIN = GP9
SSID = "TP-Link_F700"
PASSWORD = "70660180"
WLAN_CONFIG = ('192.168.0.120', '255.255.255.0', '192.168.0.1', '8.8.8.8')
```

## Deploy
Write `main.py` to the board running MicroPython.

## Fetch data

```bash
curl http://<device-ip>/color
```

