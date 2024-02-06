import paho.mqtt.client as mqtt
from datetime import datetime
import json
import getmac 
import uuid
import threading



broker_address = "sb-cbf779c1-9347-4967-9357-ccd4074f3fb0-1.mq.eu-west-2.amazonaws.com"  
port = 8883 
client_id = getmac.get_mac_address()

#callback function for connection with MQTT broker, 
# flags - connection status, rc - connection code
# at the end we subscribe to all the topics
def on_connect(client, userdata, flags, rc):
    print("connected")
    client.subscribe('#')

# what we do after message is received 
def on_message(client, userdata, msg):
    global chair_settings
    print("Received message: " + msg.topic + " " + str(msg.payload))
    if msg.topic == "poschair/commands":
        command = json.loads(msg.payload)
        if "adjustments" in command:
            chair_settings.update(command["adjustments"])

def measurements_thread():
  print('Hi')

def mqtt_thread():
    client = mqtt.Client(client_id=client_id)
    client.tls_set()
    client.username_pw_set(username="imperialactivemq",password="verySecoorpaswurd!!3")
    client.connect(broker_address, port)
    client.loop_start()
    client.on_connect = on_connect
    client.on_message = on_message
    client.loop_forever()

thread_1 = threading.Thread(target = mqtt_thread)
thread_1.start()

thread_2 = threading.Thread(target = measurements_thread) # needs to be added

while True:    
    timestamp = datetime.now().isoformat()

    metrics = {"metric1": 10.0, "metric2": 20.0, "metric3": 30.0, "metric4": 40.0, "metric5": 50.0,
           "metric6": 60.0, "metric7": 70.0, "metric8": 80.0, "metric9": 90.0, "metric10": 100.0,
           "metric11": 110.0, "metric12": 120.0, "metric13": 130.0, "metric14": 140.0, "metric15": 150.0}
    message = {"timestamp": timestamp, "metrics": metrics}

    message_json = json.dumps(message)

    client.publish("reading", message_json)

    client.disconnect()

