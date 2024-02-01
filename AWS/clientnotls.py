import paho.mqtt.client as mqtt
import ssl
import paho.mqtt.publish as publish

def mqtt_publish(message):
    broker_address = "35.176.230.101"
    port = 8883
    client_id = "mqtt_client_id-1"

    client = mqtt.Client(client_id=client_id)
    try:
        client.connect(broker_address, port)
        message = "Hello, world!"
        publish.single("ssh_output", message, hostname="35.176.230.101")
        print("Message published to MQTT broker.")
    except Exception as e:
        print(f"Failed to publish message to MQTT broker: {e}")
    finally:
        client.disconnect()

mqtt_publish("Example message")
