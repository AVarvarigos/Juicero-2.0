"""
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

publish.single(topic="VirtualTopic.test", payload="boo", hostname="b-cbf779c1-9347-4967-9357-ccd4074f3fb0-1.mq.eu-west-2.amazonaws.com", client_id="spongo", port=8883, protocol=mqtt.MQTTv5)

"""
import paho.mqtt.client as mqtt
import random
import json
import uuid


def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))


def on_message(mqttc, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))


def on_publish(mqttc, obj, mid):
    print("mid: " + str(mid))
    pass


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mqttc, obj, level, string):
    print(string)

hwaddr = uuid.getnode()


# If you want to use a specific client id, use
# mqttc = mqtt.Client("client-id")
# but note that the client id must be unique on the broker. Leaving the client
# id parameter empty will generate a random id for you.
mqttc = mqtt.Client(client_id="blahorh-"+str(hwaddr))
mqttc.username_pw_set("lowuser", password="lowuser_lowpassword")
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe
# Uncomment to enable debug messages
mqttc.on_log = on_log
mqttc.tls_set()
mqttc.tls_insecure_set(True)
mqttc.connect("b-cbf779c1-9347-4967-9357-ccd4074f3fb0-1.mq.eu-west-2.amazonaws.com", 8883, 60)

mqttc.loop_start()

sensor_data = {
    "posture_quality": 0.12,
    "device_id": "chair-"+str(hwaddr)
    }

infot = mqttc.publish("VirtualTopic/test", json.dumps(sensor_data), qos=2)

infot.wait_for_publish()
