from machine import Pin, I2C
from micropython import const
import time
import ustruct
import network
import socket
import json

# --- Pin Configuration ---
LED_EN = Pin(19)
IRQ_IN = Pin(20)
SDA_PIN = Pin(8)
SCL_PIN = Pin(9)
PICO_LED = Pin("LED", Pin.OUT)

# --- Wi-Fi config ---
#SSID = "TP-Link_F700"
#PASSWORD = "70660180"
SSID = "Emerald"
PASSWORD = "Lassod_er!22d"

# --- Color Sensor Driver ---
_COMMAND_BIT = const(0x80)

_REGISTER_ENABLE = const(0x00)
_REGISTER_ATIME = const(0x01)

_REGISTER_AILT = const(0x04)
_REGISTER_AIHT = const(0x06)

_REGISTER_ID = const(0x12)

_REGISTER_APERS = const(0x0c)

_REGISTER_CONTROL = const(0x0f)

_REGISTER_SENSORID = const(0x12)

_REGISTER_STATUS = const(0x13)
_REGISTER_CDATA = const(0x14)
_REGISTER_RDATA = const(0x16)
_REGISTER_GDATA = const(0x18)
_REGISTER_BDATA = const(0x1a)

_ENABLE_AIEN = const(0x10)
_ENABLE_WEN = const(0x08)
_ENABLE_AEN = const(0x02)
_ENABLE_PON = const(0x01)

_GAINS = (1, 4, 16, 60)
_CYCLES = (0, 1, 2, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60)


class TCS34725:
    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address
        self._active = False
        self.integration_time(2.4)
        sensor_id = self.sensor_id()
        if sensor_id not in (0x44, 0x4D):
            raise RuntimeError("wrong sensor id 0x{:x}".format(sensor_id))

    def _register8(self, register, value=None):
        register |= _COMMAND_BIT
        if value is None:
            return self.i2c.readfrom_mem(self.address, register, 1)[0]
        data = ustruct.pack('<B', value)
        self.i2c.writeto_mem(self.address, register, data)

    def _register16(self, register, value=None):
        register |= _COMMAND_BIT
        if value is None:
            data = self.i2c.readfrom_mem(self.address, register, 2)
            return ustruct.unpack('<H', data)[0]
        data = ustruct.pack('<H', value)
        self.i2c.writeto_mem(self.address, register, data)

    def active(self, value=None):
        if value is None:
            return self._active
        value = bool(value)
        if self._active == value:
            return
        self._active = value
        enable = self._register8(_REGISTER_ENABLE)
        if value:
            self._register8(_REGISTER_ENABLE, enable | _ENABLE_PON)
            time.sleep_ms(3)
            self._register8(_REGISTER_ENABLE,
                enable | _ENABLE_PON | _ENABLE_AEN)
        else:
            self._register8(_REGISTER_ENABLE,
                enable & ~(_ENABLE_PON | _ENABLE_AEN))

    def sensor_id(self):
        return self._register8(_REGISTER_SENSORID)

    def integration_time(self, value=None):
        if value is None:
            return self._integration_time
        value = min(614.4, max(2.4, value))
        cycles = int(value / 2.4)
        self._integration_time = cycles * 2.4
        return self._register8(_REGISTER_ATIME, 256 - cycles)

    def gain(self, value):
        if value is None:
            return _GAINS[self._register8(_REGISTER_CONTROL)]
        if value not in _GAINS:
            raise ValueError("gain must be 1, 4, 16 or 60")
        return self._register8(_REGISTER_CONTROL, _GAINS.index(value))

    def _valid(self):
        return bool(self._register8(_REGISTER_STATUS) & 0x01)

    def read(self, raw=False):
        was_active = self.active()
        self.active(True)
        while not self._valid():
            time.sleep_ms(int(self._integration_time + 0.9))
        data = tuple(self._register16(register) for register in (
            _REGISTER_RDATA,
            _REGISTER_GDATA,
            _REGISTER_BDATA,
            _REGISTER_CDATA,
        ))
        self.active(was_active)
        if raw:
            return data
        return self._temperature_and_lux(data)

    def _temperature_and_lux(self, data):
        r, g, b, c = data
        x = -0.14282 * r + 1.54924 * g + -0.95641 * b
        y = -0.32466 * r + 1.57837 * g + -0.73191 * b
        z = -0.68202 * r + 0.77073 * g +  0.56332 * b
        d = x + y + z
        n = (x / d - 0.3320) / (0.1858 - y / d)
        cct = 449.0 * n**3 + 3525.0 * n**2 + 6823.3 * n + 5520.33
        return cct, y

    def threshold(self, cycles=None, min_value=None, max_value=None):
        if cycles is None and min_value is None and max_value is None:
            min_value = self._register16(_REGISTER_AILT)
            max_value = self._register16(_REGISTER_AILT)
            if self._register8(_REGISTER_ENABLE) & _ENABLE_AIEN:
                cycles = _CYCLES[self._register8(_REGISTER_APERS) & 0x0f]
            else:
                cycles = -1
            return cycles, min_value, max_value
        if min_value is not None:
            self._register16(_REGISTER_AILT, min_value)
        if max_value is not None:
            self._register16(_REGISTER_AIHT, max_value)
        if cycles is not None:
            enable = self._register8(_REGISTER_ENABLE)
            if cycles == -1:
                self._register8(_REGISTER_ENABLE, enable & ~(_ENABLE_AIEN))
            else:
                self._register8(_REGISTER_ENABLE, enable | _ENABLE_AIEN)
                if cycles not in _CYCLES:
                    raise ValueError("invalid persistence cycles")
                self._register8(_REGISTER_APERS, _CYCLES.index(cycles))

    def interrupt(self, value=None):
        if value is None:
            return bool(self._register8(_REGISTER_STATUS) & _ENABLE_AIEN)
        if value:
            raise ValueError("interrupt can only be cleared")
        self.i2c.writeto(self.address, b'\xe6')


def html_rgb(data):
    r, g, b, c = data
    red = pow((int((r/c) * 256) / 255), 2.5) * 255
    green = pow((int((g/c) * 256) / 255), 2.5) * 255
    blue = pow((int((b/c) * 256) / 255), 2.5) * 255
    return red, green, blue

def html_hex(data):
    r, g, b = html_rgb(data)
    return "{0:02x}{1:02x}{2:02x}".format(int(r),
                             int(g),
                             int(b))



# --- Main Program Logic ---

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        time.sleep(1)
    ip = wlan.ifconfig()[0]
    print("Connected:", ip)
    return ip


def start_server(sensor, ip):


    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    print("Listening on http://{}:80".format(ip))

    while True:
        cl, _ = s.accept()
        try:
            request = cl.recv(1024).decode("utf-8")
            first_line = request.split("\r\n")[0]
            method, path, _ = first_line.split(" ", 2)

            if method == "GET" and path == "/color":
                r, g, b = sensor.read_rgb_normalized()
                raw_r, raw_g, raw_b, raw_c = sensor.read_rgbc()
                body = json.dumps(
                    {
                        "r": r,
                        "g": g,
                        "b": b,
                        "raw": {"r": raw_r, "g": raw_g, "b": raw_b, "c": raw_c},
                    }
                )
                cl.send("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
                cl.send(body)
            else:
                cl.send("HTTP/1.0 404 Not Found\r\n\r\nNot Found")
        except Exception as e:
            print("Error:", e)
            cl.send("HTTP/1.0 500 Internal Server Error\r\n\r\nError")
        finally:
            cl.close()


def main():
    # I2C on default Pico W pins: SDA=GP0, SCL=GP1
    i2c = I2C(0, sda=SDA_PIN, scl=SCL_PIN, freq=400_000)
    sensor = TCS34725(i2c)
    ip = connect_wifi()
    start_server(sensor, ip)


main()
