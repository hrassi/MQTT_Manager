from wifi_connect import wifi_loop
import mqtt_manager
import time
from machine import Pin
from machine import WDT
import clock

MyNetwork = "R*********"
MyPassword = "H********t"
esp_id = "esp77"
onboard_led=Pin(2,Pin.OUT)


wdt = WDT(timeout=40000)  # 40 seconds

# Topics
TOPIC_TEXT = f"{esp_id}/text"
TOPIC_REFRESH = f"{esp_id}/refresh"
TOPIC_TIME= f"{esp_id}/pottime"
PUB_TOPIC = "esp/notification"

STATUS_TOPIC = f"{esp_id}/status"

# Callback
def on_mqtt(topic, msg):
    t = topic.decode()
    m = msg.decode()

    print("RX:", t, m)

    if t == TOPIC_REFRESH:
        print("Refresh command received")
        if m=="0":
            
            onboard_led.value(not onboard_led.value()) #toggle led
            mqtt_manager.publish(TOPIC_TIME, clock.get_time())
            time.sleep(1)
     
# Setup
mqtt_manager.set_callback(on_mqtt)

mqtt_manager.set_last_will(STATUS_TOPIC, "offline", retain=True)

mqtt_manager.subscribe(TOPIC_TEXT)
mqtt_manager.subscribe(TOPIC_REFRESH)




last_pub = time.time()

# Main loop
while True:
    
    wdt.feed()
    wifi_loop(MyNetwork, MyPassword)
    mqtt_manager.mqtt_loop()

    # Example publish
    if mqtt_manager.is_connected():
        if time.time() - last_pub > 3600:
            print(clock.get_time())
            #mqtt_manager.publish(PUB_TOPIC, "testing mqtt")
            last_pub = time.time()

    time.sleep_ms(100)
