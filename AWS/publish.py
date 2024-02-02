import paho.mqtt.client as mqtt
import time

broker_address = "0.0.0.0"  # Replace with your EC2 instance's public IP
port = 1883
client_id = "mqtt_publisher_id"
client = mqtt.Client(client_id=client_id)
client.connect(broker_address, port)

while True:
    client.publish("ssh_output", "hello")
    time.sleep(1)  # Adjust the delay between messages as needed

# Disconnect from the broker
client.disconnect()
