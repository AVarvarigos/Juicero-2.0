import paramiko
import paho.mqtt.client as mqtt
import ssl
import paho.mqtt.publish as publish


def ssh_command(ip_address, username, private_key_path, command):
    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        private_key = paramiko.RSAKey.from_private_key_file(private_key_path)

        ssh.connect(ip_address, username=username, pkey=private_key)

        stdin, stdout, stderr = ssh.exec_command(command)

        output = stdout.read().decode()

        print(output)

        mqtt_publish(output)

    except paramiko.AuthenticationException:
        print("Authentication failed. Please check your username and private key.")
    except paramiko.SSHException as e:
        print(f"SSH connection failed: {e}")
    finally:
        ssh.close()

def mqtt_publish(message):
    broker_address = "35.176.230.101"
    port = 1883
    private_key_path = "HELPME.ppk"
    client_id = "mqtt_client_id-1"

    client = mqtt.Client(client_id=client_id)

    client.tls_set(keyfile=private_key_path,  certfile=None, cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS)

    try:
        client.connect(broker_address, port)
        message = "Hello, world!"
        publish.single("ssh_output", message, hostname="35.176.230.101")
        print(f"Failed to publish message to MQTT broker: {e}")
    finally:
        client.disconnect()

ip_address = '35.176.230.101'
username = 'ubuntu'
private_key_path = 'HELPME.ppk'
command = 'ls -l'  

ssh_command(ip_address, username, private_key_path, command)
