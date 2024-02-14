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

hwaddr = uuid.getnode()
global sampler_buffer2
global sampler_buffer
sampler_buffer = [16000, 14000, 50, 50,-1] 
sampler_buffer2 = [16000,14000,50,50,50,-1]
lock = threading.Lock()
global new_weight
new_weight = 0

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

 
# get data, put in ML, push in network interface, sends to the website, waits for website commands, 
# if website unavailable send flag to change the frequency 
# turn them to pipeline - samples have to be interrupted, so have highest priority,
# min time of TOS = 20us for good accuracy 32us. three of them lead to 100ms. 

# 110 ms per sample. we want to make it periodic. 

# task1: SAMPLE TASK
# task2: ML task
# task3: network task lowest priority - send packets to website, receive the signal and exchange passwords and 
# usernames to make sure the right thing is connected


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

#class MLP(nn.Module):
#    def __init__(self, layer_sizes, activation=nn.ReLU, final_activation=None, lr=0.001):
#        super(MLP, self).__init__()
#        
#        layers = []
#       for i in range(len(layer_sizes) - 1):
#            layers.extend([
#                nn.Linear(layer_sizes[i], layer_sizes[i+1]),
#                activation(),
#            ])
        
        # Pop off the last activation
#        layers.pop()
#        if final_activation:
#            layers.append(final_activation())

#        self.model = nn.Sequential(*layers)
        #self.device = device

#    def forward(self, x):
#        return self.model.forward(x)

#def ml_initialization(model_dir):
#    model = MLP([2, 128, 128, 1], nn.ReLU, nn.Sigmoid)
#    model.load_state_dict(torch.load(model_dir)) #directory "model_save_bin.mdl"
#    return model

#def ml_predict(model,sampler_buffer):
#    left = 0
#    right = 0
#    counter = 0
#    for first,second in zip(sampler_buffer[::8], sampler_buffer[1::8]):
#        counter = counter + 1
#        left = left + first
#        right = right + second
#    left = left / counter
#    right = right / counter
#    logits = model(torch.tensor([left,right]).type(torch.float32))
#    return logits

def ml_model_fake(number):
    print('this thread has started')
    print(new_weight)
    return 1.0

    
# acquire name of chair after it has been altered in UI
def fetch_weight():
    url = 'https://e8rieltp49.execute-api.eu-west-2.amazonaws.com/default/DSDAPI/chair?id=chair-'+ str(hwaddr)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            weight = response.json()['weight']
            return weight
        else:
            print(f"Failed to fetch name. Status code: {response.status_code}")
            print(f"Failed to fetch name. Status code: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def output(mlmodel): 
    global lock, sampler_buffer2, sample_buffer, new_weight
    while True:
        lock.acquire() 
        buffer = sampler_buffer.copy()
        lock.release()
        # feed in sample_buffer from the main loop, get it through args
        sensor_data = {
           "posture_quality": ml_model_fake(mlmodel, buffer),
            #"posture_quality": ml_predict(mlmodel, buffer).item(),
            "device_id": "chair-"+str(hwaddr)
        }
        print("buffer and posture quality")
        print(buffer)
        print(sensor_data["posture_quality"])
        time.sleep(1)
        new_weight = fetch_weight()
        if new_weight is None:
            print("Warning: no weight found from server")
            new_weight = 1

        print(new_weight)
        infot = mqttc.publish("VirtualTopic/test", json.dumps(sensor_data), qos=2)  
        infot.wait_for_publish()
        time.sleep(2)

def get_fake_datastream():
    global lock, sampler_buffer2
    while True:
        adcdata = [16000,14000,32767,32767]
        distancedata = [60,50,60]
        lock.acquire()
        sampler_buffer2 = sampler_buffer2 + adcdata + distancedata + [-1] +adcdata + distancedata + [-1] +adcdata + distancedata + [-1]
        print(sampler_buffer2)
        lock.release()
        time.sleep(2)

#WEBSITE STUFF END
#INCREASE I2C CLOCK SPEED TO 400K SOMEHOW
#Have 3 tasks: network, ML, and data collection. Network threading is automatic so make data collection tasks to interrupts and put ML + some network operations as main loop (or thread network and ML at main loop)

#SETUP()

# initialize ML model    
#model_dir = "model_save_bin_cpu.mdl"
#model = ml_initialization(model_dir)
# Create an ADS1115 ADC (16-bit) instance.
adc = Adafruit_ADS1x15.ADS1115()
sensor1_shutdown = 18
sensor2_shutdown = 27
sensor3_shutdown = 17
GPIO.setwarnings(False)

    # Setup GPIO for shutdown pins on each VL53L0X

GPIO.setmode(GPIO.BCM)  #SET LEFT GPIO SIDE ALL HIGH.  NEXT INITIATED ONLY RIGHT SIDE, LEFT SIDE STILL THERE!!!!!.

GPIO.setup(sensor1_shutdown, GPIO.OUT)
GPIO.output(sensor1_shutdown, GPIO.HIGH) #called to get rid of previous run's state!
GPIO.setup(sensor2_shutdown, GPIO.OUT)
GPIO.output(sensor2_shutdown, GPIO.HIGH)
GPIO.setup(sensor3_shutdown, GPIO.OUT)
GPIO.output(sensor3_shutdown, GPIO.HIGH)

    
time.sleep(0.10)
    #Resets Pins by rising edge. ALLOWS THE RESET OF ADDRESSES TO BE CHANGED AGAIN
GPIO.output(sensor1_shutdown, GPIO.LOW)
GPIO.output(sensor2_shutdown, GPIO.LOW)
GPIO.output(sensor3_shutdown, GPIO.LOW)

time.sleep(0.10)

    #I2C ADDRESS BECOMES UNDETECTABLE WHEN SHUTDOWN IS HIGH. Can't change addresses when chip is at shutdown and when it gets off it's at 0x29

    #Took first TOF out of off and reset it
GPIO.output(sensor1_shutdown, GPIO.HIGH) #ORIGINAL METHOD OF CHANGING ADDRESS CAN'T WORK. The address change thing at initializer doesn't work!!! Circumwented with changing address after initialization
tof = VL53L0X.VL53L0X(i2c_bus=1,i2c_address=0x29) #29 is original address. Reset resets the I2C address back to 29 too. If not pull shutdown to low then high address remains same!
tof.change_address(0x0A)
GPIO.output(sensor2_shutdown, GPIO.HIGH)


tof1 = VL53L0X.VL53L0X(i2c_bus=1,i2c_address=0x29)
    
tof1.change_address(0x0B)
    
    #DON'T TOUCH THE PART ABOVE! IT WORKS

GPIO.output(sensor3_shutdown, GPIO.HIGH)
tof2 = VL53L0X.VL53L0X(i2c_bus=1,i2c_address=0x29)
tof2.change_address(0x0C)

    # I2C Address can change before tof.open()
    # tof.change_address(0x29)

tof.open()
tof1.open()
tof2.open()

    # Start ranging

'''
     GOOD = 0        # 33 ms timing budget 1.2m range INCREASE IF HAVE MORE SLACK IN TIMING
     BETTER = 1      # 66 ms timing budget 1.2m range
     BEST = 2        # 200 ms 1.2m range
     LONG_RANGE = 3  # 33 ms timing budget 2m range
     HIGH_SPEED = 4  # 20 ms timing budget 1.2m range

'''

time.sleep(0.30)

tof.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

tof1.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

tof2.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

times=[tof.get_timing(), tof1.get_timing(), tof2.get_timing()]

times_max=max(times)

print("Timing %d ms" % (times_max/1000))


times_max=sum(times)

print("Total timing %d ms" % (times_max/1000))
    #buffers

sampler_buffer=[]
ML_buffer=[]
SAMPLER_BUFFER_LENGTH=500 #Optimize lengths to save space but should be large enough to not be overflown

ML_BUFFER_LENGTH=500 
FLEX_AMOUNT=4

IR_AMOUNT=2

GAIN = [4, 4, 2, 2] #8 gain CAUSE OVERSHOOT. DO 4 OR 2. ASK CHANG ON HIS SENSOR SETTINGS???
    
    #ML SETUP STATEMENTS GO HERE (Chang)

    #NETWORK LIBRARY SETUP STATEMENTS GO THERE (Anastasis)


max_sit_time=-1 #represent time in minutes or hours? A way to ensure timer() won't overflow!

    #ALSO ADD SETUP SERVER COMMUNICATIONS WHERE SERVER SEND PACKETS TO SETUP SYSTEM ACCORDING TO USER INPUTS (SITTING TIME, HEIGHT, WEIGHT, AREA TO FOCUS ON, ETC) AND DEVICE WILL LET

print('Reading ADS1x15 and VL53L0X values, press Ctrl-C to quit...')
    # Print nice channel column headers
print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*range(4)))
print('-' * 37)

adc_values = [0]*4

distance=[0]*3

    #Have another loop where device waits for a GO signal from server to start sending data. Can be turned on or off by user
    #Also include something where when user logs into the website server will ask for information about past session?


    #OPTIMIZE ADC DATA RATES AND TOF DATA COLLECTION MODES BASED ON TOMORROW'S TESTS

#LOOP(). Make this an interrupt or put with ML in series
def measurements():
    global sampler_buffer, lock
    while True:
        for i in range(4):
            #SAMPLE ADC DATA
            # Read the specified ADC channel using the previously set gain value.
            adc_values[i] = adc.read_adc(i, gain=GAIN[i], data_rate=128) #ASSUMES IT USES DEFAULT ADDRESS
            # Note you can also pass in an optional data_rate parameter that controls
            # the ADC conversion time (in samples/second). Each chip has a different
            # set of allowed data rate values, see datasheet Table 9 config register
            # DR bit values.
            # Each value will be a 12 or 16 bit signed integer value depending on the
            # ADS1115 = 16-bit).
        #SAMPLE TOF DATA IN MM
        distance[0] = tof.get_distance()
        distance[1] = tof1.get_distance()
        distance[2] = tof2.get_distance()
        #SEND TIME SPENT ON CHAIR TOO
        #FIND A WAY TO INDETIFY THE PERSON SITTING ON CHAIR
        '''
        DO POTENTIAL DATA PROCESSING AND FILTERING HERE!!!!! (average samples, convert raw data, etc
        IF MAKE MORE SAMPLES THAN ML CAN PROCESS THEN COMPRESS DATA POINTS THROUGH AVERAGING
        '''
        # PRINT DATA FOR DEBUG PURPOSES BUT IN APPLICATION WE SAVE THEM TO BUFFER
        print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*adc_values))
        print('Distance 0: ' + str(distance[0]) + ' Distance 1: ' + str(distance[1]) + ' Distance 2: ' + str(distance[2]))
        if len(sampler_buffer)/(FLEX_AMOUNT + IR_AMOUNT +1) < SAMPLER_BUFFER_LENGTH:
            lock.acquire()    
            sampler_buffer=sampler_buffer + adc_values + distance + [-1] #-1 here to tell the end of packet
            lock.release()
        #time.sleep(220/1000.0) 
        '''
        ML DATA PROCESSING
        -In series for now as data collection would be interrupts and website stuff will have their own threads done automatically
        if(size(sampler_buffer)>0):
            -POP FROM SAMPLE BUFFER (if empty do nothing DON'T BLOCK)
            -DO ML CALCULATION (OPTIMIZED)
            -Turn on haptic motor(s) if see bad posture
            -MAKE RESULT PACKET
        if(have_made_packet_at_hand and )
            -ML_buffer=ML_buffer + DATA_PACKET + [-1]
        -NEEDS TO BE NONBLOCKING. CAN JUST LEAVE IT AS IT IS IF ITS RUNTIME IS LESS THAN 1MS
        '''
        time.sleep(220/1000) #MAKE IT NON BLOCKING???
        #-Network in background if can make that: FIND LIBRARY THAT ALLOWS THAT
        #-If have time, sampling is in interrupt that will interfere with ML operation but will ensure fast and continuous data collection. CANNOT PARALLEL I2C COMMUNICATIONS BUT IMPROVE SOMEHOW??? (multiple I2C ports?)
        #-ML stuff will be in the main While(1) loop 
    #What TOF does when program is terminated. How to add some sort of stop condition to ensure this is executed when operation is done. Look more into what these methods do!    


publish_thread = threading.Thread(target = output, args = (5,))
measurements_thread = threading.Thread(target = measurements)

publish_thread.start()
measurements_thread.start()

publish_thread.join()
measurements_thread.join()

tof.stop_ranging()
GPIO.output(sensor2_shutdown, GPIO.LOW)
tof1.stop_ranging()
GPIO.output(sensor1_shutdown, GPIO.LOW)
tof2.stop_ranging()
GPIO.output(sensor1_shutdown, GPIO.LOW)
tof.close()
tof1.close()
tof2.close
