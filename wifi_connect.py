# wifi_connect.py — autonomous WiFi manager (ESP32 MicroPython v1.28+)
# will keep trying to connect and check for wifi and internet if not it reconnect
# USAGE:
#        from wifi_connect import wifi_loop
#        MyNetwork = "R********"
#        MyPassword = "H*******t"
#
#        while True:
#           wifi_loop(MyNetwork, MyPassword)
#
#           Your system runs freely here (MQTT, sensors, UI, etc.)
#           
#           time.sleep_ms(100)
#
#
# # ───── 1. WAIT FOR WIFI AT STARTUP ─────
#
# print("[System] Connecting to WiFi...")
#
# while not wifi_loop(MyNetwork, MyPassword):
#    
#     time.sleep_ms(500)
#
# print("[System] WiFi connected!")
#
#
import network
import time
import socket
from machine import Pin

_STA = getattr(network.WLAN, 'IF_STA', network.STA_IF)
wlan = network.WLAN(_STA)

onboard_led=Pin(2,Pin.OUT)
onboard_led.off()


# ─────────────────────────────────────────────
# INTERNAL STATE
# ─────────────────────────────────────────────
_last_attempt = 0
_retry_interval = 5000       # ms between reconnect attempts

_last_health_check = 0
_health_interval = 10000     # ms between health checks

_connecting = False


# ─────────────────────────────────────────────
def wifi_loop(ssid, password, power_save=False):
    """
    Call this continuously in main loop.
    Handles everything automatically:
    - connect
    - reconnect
    - health check
    """

    global _last_attempt, _connecting, _last_health_check

    now = time.ticks_ms()

    # ───── CONNECTED ─────
    if wlan.isconnected():
        if _connecting:
            # Apply power mode after connection
            pm = network.WLAN.PM_PERFORMANCE if power_save else network.WLAN.PM_NONE
            try:
                wlan.config(pm=pm)
            except:
                pass

            ip = wlan.ifconfig()[0]
            rssi = wlan.status('rssi')
            print(f"[WiFi] Connected! IP: {ip}  RSSI: {rssi} dBm  Power Management: {pm}")
            onboard_led.on()
            _connecting = False

        # ───── PERIODIC HEALTH CHECK ─────
        if time.ticks_diff(now, _last_health_check) > _health_interval:
            _last_health_check = now

            if not _internet_ok():
                print("[WiFi] Unhealthy (NO INTERNET) → forcing reconnect")
                onboard_led.off()
                _force_reconnect(ssid, password)
                _connecting = True
                _last_attempt = now

        return True

    # ───── NOT CONNECTED → TRY RECONNECT ─────
    if time.ticks_diff(now, _last_attempt) > _retry_interval:
        print("[WiFi] Wifi disconnected ...Reconnecting...")
        onboard_led.off()
        _force_reconnect(ssid, password)

        _connecting = True
        _last_attempt = now

    return False


# ─────────────────────────────────────────────
def _force_reconnect(ssid, password):
    """
    Safe reconnect sequence (handles all ESP32 states)
    """

    try:
        wlan.disconnect()
    except:
        pass

    try:
        wlan.active(False)
        time.sleep_ms(100)
    except:
        pass

    wlan.active(True)

    try:
        wlan.connect(ssid, password)
    except:
        pass


# ─────────────────────────────────────────────
def _internet_ok(host="8.8.8.8", port=53, timeout=1):
    """
    Connectivity test (fast, non-blocking-ish).
    Change host if using local MQTT (recommended).
    """
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
        s = socket.socket()
        s.settimeout(timeout)
        s.connect(addr)
        s.close()
        onboard_led.on()
        return True
    except:
        onboard_led.off()
        return False
