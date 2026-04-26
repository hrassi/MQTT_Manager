# mqtt_manager.py — autonomous MQTT manager (ESP32 MicroPython)
# Non-blocking MQTT handler with auto-reconnect
#
# USAGE:
#
#   import mqtt_manager
#
#   def on_msg(topic, msg):
#       print("RX:", topic, msg)
#
#   mqtt_manager.set_callback(on_msg)
#   mqtt_manager.subscribe("esp77/test")
#
#   # Optional: Last Will (offline message)
#   mqtt_manager.set_last_will("esp77/status", "offline", retain=True)
#
#   while True:
#       wifi_loop(ssid, password)
#       mqtt_manager.mqtt_loop()
#       time.sleep_ms(100)
#

from umqtt.simple import MQTTClient
import time


esp_id = "esp77"

# ─────────────────────────────────────────────
# CONFIG (inside module → reusable everywhere)
# ─────────────────────────────────────────────
MQTT_CLIENT_ID = esp_id + "_client"
MQTT_BROKER = "90b46***********************hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "sam02"
MQTT_PASSWORD = "H***********"

SSL = True
SSL_PARAMS = {'server_hostname': MQTT_BROKER}


# ─────────────────────────────────────────────
# INTERNAL STATE
# ─────────────────────────────────────────────
_client = None
_connected = False

_last_attempt = 0
_retry_interval = 5000   # ms between reconnect attempts

_last_ping = 0
_ping_interval = 30000   # ms keepalive ping

_callback = None
_subscriptions = []

_connecting = False

# === ADDED === Last Will storage
_lwt_topic = None
_lwt_message = None
_lwt_retain = False


# ─────────────────────────────────────────────
def set_callback(cb):
    """
    Set function to handle incoming MQTT messages
    """
    global _callback
    _callback = cb


# ─────────────────────────────────────────────
def set_last_will(topic, message, retain=False):
    """
    Configure Last Will (must be called before connection)
    """
    global _lwt_topic, _lwt_message, _lwt_retain

    _lwt_topic = topic
    _lwt_message = message
    _lwt_retain = retain


# ─────────────────────────────────────────────
def subscribe(topic):
    """
    Add topic to subscription list.
    Will auto-subscribe after connect/reconnect.
    """
    global _subscriptions

    if topic not in _subscriptions:
        _subscriptions.append(topic)

    # If already connected → subscribe immediately
    if _connected:
        try:
            _client.subscribe(topic)
            print(f"[MQTT] Subscribed: {topic}")
        except:
            pass


# ─────────────────────────────────────────────
def publish(topic, msg, retain=False):
    """
    Safe publish (non-blocking style)
    """
    global _connected

    if not _connected:
        return False

    try:
        _client.publish(topic, msg, retain=retain)
        return True
    except Exception as e:
        print("[MQTT] Publish error:", e)
        _connected = False
        return False


# ─────────────────────────────────────────────
def is_connected():
    """
    Return MQTT connection state
    """
    return _connected


# ─────────────────────────────────────────────
def mqtt_loop():
    """
    Call this continuously inside main loop.
    Handles:
    - connect
    - reconnect
    - message processing
    - keepalive ping
    """

    global _client, _connected, _connecting
    global _last_attempt, _last_ping

    now = time.ticks_ms()

    # ───── CONNECTED STATE ─────
    if _connected:
        try:
            # Process incoming messages (triggers callback)
            _client.check_msg()

            # Keepalive ping
            if time.ticks_diff(now, _last_ping) > _ping_interval:
                _client.ping()
                _last_ping = now
                # print("[MQTT] Ping")

        except Exception as e:
            print("[MQTT] Connection lost:", e)
            _connected = False

        return True


    # ───── NOT CONNECTED → TRY RECONNECT ─────
    if time.ticks_diff(now, _last_attempt) > _retry_interval:

        print("[MQTT] Connecting...")

        _last_attempt = now
        _connecting = True

        try:
            # Create client
            _client = MQTTClient(
                client_id=MQTT_CLIENT_ID,
                server=MQTT_BROKER,
                port=MQTT_PORT,
                user=MQTT_USER,
                password=MQTT_PASSWORD,
                keepalive=60,
                ssl=SSL,
                ssl_params=SSL_PARAMS
            )

            # === ADDED === Apply Last Will before connect
            if _lwt_topic is not None:
                _client.set_last_will(_lwt_topic, _lwt_message, retain=_lwt_retain)

            # Attach callback
            if _callback:
                _client.set_callback(_callback)

            # Connect to broker
            _client.connect()

            # Subscribe to all stored topics
            for topic in _subscriptions:
                _client.subscribe(topic)

            print("[MQTT] Connected")

            # === ADDED === Publish ONLINE status automatically
            if _lwt_topic is not None:
                try:
                    _client.publish(_lwt_topic, "online", retain=_lwt_retain)
                except:
                    pass

            _connected = True
            _connecting = False
            _last_ping = now

        except Exception as e:
            print("[MQTT] Connect failed:", e)
            _connecting = False

    return False
