import time #ADDESSES OF TOF NOT VOTTRVT FIXED FIRST NEED TO CONNECT 2ND FIRST TO FIX ADDRESS
import requests
import Custom_ADC_Library
import VL53L0X
import RPi.GPIO as GPIO


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

hwaddr = uuid.getnode() #acquire mac address in order to have unique client_id
global sampler_buffer
sampler_buffer = [16000, 14000, 50, 50,-1] 
global lock
lock = threading.Lock()

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

def output(): 
    global lock, sample_buffer
    while True:
        lock.acquire() 
        buffer = sampler_buffer.copy()
        lock.release()
        # feed in sample_buffer from the main loop, get it through args
        sensor_data = {
           "raw_data": buffer,
            "device_id": "chair-"+str(hwaddr)
        }
        print("buffer and posture quality")
        print(buffer)
        time.sleep(1)
        infot = mqttc.publish("raw_data", json.dumps(sensor_data), qos=2)  
        infot.wait_for_publish()
        time.sleep(2)

#WEBSITE END
#INCREASE I2C CLOCK SPEED TO 400K SOMEHOW
#Have 3 tasks: network, ML, and data collection. Network threading is automatic so make data collection tasks to interrupts and put ML + some network operations as main loop (or thread network and ML at main loop)

#Setup
# Create an ADS1115 ADC (16-bit) instance.
adc = Custom_ADC_Library.flex_adc()
sensor1_shutdown = 18
sensor2_shutdown = 17
sensor3_shutdown = 27
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

#Took first TOF out of off and reset it
GPIO.output(sensor1_shutdown, GPIO.HIGH) #ORIGINAL METHOD OF CHANGING ADDRESS CAN'T WORK. The address change thing at initializer doesn't work!!! Circumwented with changing address after initialization
tof = VL53L0X.VL53L0X(i2c_bus=1,i2c_address=0x29) #29 is original address. Reset resets the I2C address back to 29 too. If not pull shutdown to low then high address remains same!
tof.change_address(0x0A)
GPIO.output(sensor2_shutdown, GPIO.HIGH)

tof1 = VL53L0X.VL53L0X(i2c_bus=1,i2c_address=0x29)  
tof1.change_address(0x0B)  
GPIO.output(sensor3_shutdown, GPIO.HIGH)
tof2 = VL53L0X.VL53L0X(i2c_bus=1,i2c_address=0x29)
tof2.change_address(0x0C)

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
FLEX_AMOUNT=2
IR_AMOUNT=2
GAIN = [4, 4] #8 gain CAUSE OVERSHOOT. DO 4 OR 2. ASK CHANG ON HIS SENSOR SETTINGS???
max_sit_time=-1 #represent time in minutes or hours? A way to ensure timer() won't overflow!
print('Reading ADS1x15 and VL53L0X values, press Ctrl-C to quit...')
# Print nice channel column headers
#print('| {0:>6} | {1:>6} |'.format(*range(2)))
print('-' * 37)
adc_values = [0]*2
distance=[0]*3

#LOOP(). Make this an interrupt or put with ML in series
def measurements():
    global sampler_buffer, lock
    while True:        
        #Get adc data as 32k range digital number
        adc.request_sample(channel=0)
	    #SAMPLE TOF DATA IN MM
        distance[0] = tof.get_distance()
        adc_values[0]=adc.get_sample(channel=0)
        adc.request_sample(channel=1)
        distance[1] = tof1.get_distance()
        adc_values[1]=adc.get_sample(channel=1)
        adc.request_sample(channel=0)
        distance[2] = tof2.get_distance()
        adc_values[0]+=adc.get_sample(channel=1)
        adc_values[0]/=2
        adc_values[1]=adc_values[1]-2000
        # PRINT DATA FOR DEBUG PURPOSES BUT IN APPLICATION WE SAVE THEM TO BUFFER
        print('| {0:>6} | {1:>6} |'.format(*adc_values))
        print('Distance 0: ' + str(distance[0]) + ' Distance 1: ' + str(distance[1]) + ' Distance 2: ' + str(distance[2]))
        if len(sampler_buffer)/(FLEX_AMOUNT + IR_AMOUNT +1) < SAMPLER_BUFFER_LENGTH:
            lock.acquire()
            sampler_buffer=adc_values + distance + [-1] #-1 here to tell the end of packet
            lock.release()
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
        time.sleep(220/1000) 

publish_thread = threading.Thread(target = output)
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
