import time #ADDESSES OF TOF NOT VOTTRVT FIXED FIRST NEED TO CONNECT 2ND FIRST TO FIX ADDRESS
import requests
# Import the ADS1x15 module.
import Adafruit_ADS1x15
import VL53L0X
import RPi.GPIO as GPIO
#import torch
#import torch.nn as nn


"""
import paho.mqtt.publish as publish

import paho.mqtt.client as mqtt

publish.single(topic="VirtualTopic.test", payload="boo", hostname="b-cbf779c1-9347-4967-9357-ccd4074f3fb0-1.mq.eu-west-2.amazonaws.com", client_id="spongo", port=8883, protocol=mqtt.MQTTv5)

"""
#WEBSITE SETUP HERE
import paho.mqtt.client as mqtt
import random
import json
import uuid
import threading
import time
import torch
import torch.nn as nn

#==============================ML SetUP============================
# The following is to be put on setup, runs once
class End2EndModel(torch.nn.Module):
	def __init__(self, model1, model2):
		super(End2EndModel, self).__init__()
		self.first_model = model1#x to c
		self.sec_model = model2 #c to y

	def forward_stage2(self, c, x):
		return c,self.sec_model(c)

	def forward(self, x):
		c = self.first_model(x)
		return self.forward_stage2(c,x)

class MLP(nn.Module):
	def __init__(self, layer_sizes, activation=nn.ReLU, final_activation=None, lr=0.001):
		super(MLP, self).__init__()
		
		layers = []
		for i in range(len(layer_sizes) - 1):
			layers.extend([
				nn.Linear(layer_sizes[i], layer_sizes[i+1]),
				activation(),
			])
		
		# Pop off the last activation
		layers.pop()
		if final_activation:
			layers.append(final_activation())

		self.model = nn.Sequential(*layers)
		#self.device = device

	def forward(self, x):
		return self.model.forward(x)

def XtoCtoY(n_features, n_concepts):

	layer_sizes=[n_features, 128, n_concepts] #dummy sidechannels
	x_to_c = MLP(layer_sizes, nn.ReLU, nn.Sigmoid)

	layer_sizes=[n_concepts, 1]
	c_to_y = MLP(layer_sizes, nn.ReLU)

	return End2EndModel(x_to_c, c_to_y)

    #model initialization
def Flex_Model_Initialization(model_dir):
   model = MLP([2, 128, 128, 1], nn.ReLU, nn.Sigmoid)
   model.load_state_dict(torch.load(model_dir)) #directory "model_save_bin.mdl"
   return model
def IR_model_initialization(IR_Model_Dir):
	BACKCipher = XtoCtoY(4,5)
	BACKCipher.load_state_dict(torch.load(IR_Model_Dir))
	return BACKCipher
    
    #model directory might need to change
ASSCipher = Flex_Model_Initialization('model_save_bin_cpu.mdl')
BACKCipher = IR_model_initialization('5_7500_back_model_save_bin_cpu.mdl')

def normalize_IR(ir_raw):
	return ir_raw/8190.0
def normalize_Height(height_raw):
	return height_raw/200.0
def normalize_Flex(flex_reading1, flex_reading2):
	return flex_reading1/16783.0-1.0, flex_reading2/14581.0-1.0
def set_max_to_one(lst):
	if not lst:
		return []

	max_value = max(lst)
	max_index = max(range(len(lst)), key=lst.__getitem__)

	result = [0.0] * len(lst)
	result[max_index] = 1.0

	return result

#ML predict functions, to be called everytime inference needed.

def IR_Model_Predict(model, height, sampler_buffer): 
	### takes in the model, height(float) and sampler buffer,
	### returns a tuple of Posture Score (float) and Identified Type (list of float, either 1 or 0, 1 indicating which type identified)
	### types in order of typelist = ['Good', 'Lean Forward', 'Lying too low', 'Medium', 'Empty']
	IR_raw = sampler_buffer[2:5]
	IR_raw = [float(i) for i in IR_raw]
	data = [height]+IR_raw
	print('=======data')
	print(data)
	print('===========')
	Type, PostureScore = model(torch.tensor([normalize_Height(data[0]),normalize_IR(data[1]),normalize_IR(data[2]),normalize_IR(data[3])]))
	Type = Type.tolist()
	PostureScore = PostureScore.item()
	Type = set_max_to_one(Type)
	return PostureScore,Type

def Flex_Model_Predict(model,sampler_buffer):
	### takes in the model, and sampler buffer. It extracts left and right flex sensor readings
	### returns 0.0 to 1.0 on whether the posture is good (1.0 good, 0.0 bad)

	left = 0
	right = 0
	counter = 0
	first = sampler_buffer[0]
	second = sampler_buffer[1]
	normalized_first, normalized_second = normalize_Flex(first, second)
	logits = model(torch.tensor([normalized_first,normalized_second]).type(torch.float32))
	return logits

#==================ML SetUP Done==================================
hwaddr = uuid.getnode()
global new_height
new_height = 0

def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))

def on_message(mqttc, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    print('qos and payload')
    print(msg.qos)
    print(msg.payload)
    importantlist = json.loads(msg.payload.decode('utf-8'))['raw_data']
    PostureScore, Type = IR_Model_Predict(BACKCipher, fetch_height(), importantlist)
    FlexLogits = Flex_Model_Predict(ASSCipher, importantlist)
    print('model prediction done')
    print('posturescore and type onehot')
    print(PostureScore)
    print(Type)
    print('Flex logits')
    print(FlexLogits)
    sensor_data = {
           "posture_score_IR": PostureScore,
           "posture_type_IR": Type,
           "posture_quality_FLEX": FlexLogits.item(),
            #"posture_quality": ml_predict(mlmodel, buffer).item(),
            "device_id": "chair-"+str(hwaddr)
    }
    infot = mqttc.publish("VirtualTopic/test", json.dumps(sensor_data), qos=2)  
    #infot.wait_for_publish()

def on_publish(mqttc, obj, mid):
    print("mid: " + str(mid))
    pass

def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mqttc, obj, level, string):
    print(string)

### MQTT Client Setup
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="blahorh-"+str(hwaddr))
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

def fetch_height():
    url = 'https://e8rieltp49.execute-api.eu-west-2.amazonaws.com/default/DSDAPI/chair?id=chair-'+ str(hwaddr)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            height = response.json()['height']
            return height
        else:
            print(f"Failed to fetch name. Status code: {response.status_code}")
            print(f"Failed to fetch name. Status code: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

mqttc.subscribe("raw_data")
input("Processing...")
	


