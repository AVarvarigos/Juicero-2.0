import paho.mqtt.client as mqtt
from datetime import datetime
import json
import getmac 
import uuid

broker_address = "sb-cbf779c1-9347-4967-9357-ccd4074f3fb0-1.mq.eu-west-2.amazonaws.com"  
port = 8883 
client_id = "goaway"
mac_address = getmac.get_mac_address()

client = mqtt.Client(client_id=client_id)
client.tls_set()

client.username_pw_set(username="imperialactivemq",password="verySecoorpaswurd!!3")

client.connect(broker_address, port)
client.loop_start()

timestamp = datetime.now().isoformat()  
metrics = {"metric1": 10.0, "metric2": 20.0, "metric3": 30.0, "metric4": 40.0, "metric5": 50.0,
           "metric6": 60.0, "metric7": 70.0, "metric8": 80.0, "metric9": 90.0, "metric10": 100.0,
           "metric11": 110.0, "metric12": 120.0, "metric13": 130.0, "metric14": 140.0, "metric15": 150.0}
message = {"timestamp": timestamp, "metrics": metrics}

message_json = json.dumps(message)

client.publish("reading", message_json)

client.disconnect()

