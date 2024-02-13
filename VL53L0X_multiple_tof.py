#!/usr/bin/python

# MIT License
# 
# Copyright (c) 2017 John Bryan Moore
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import VL53L0X
import RPi.GPIO as GPIO

import os
import subprocess
import time






# GPIO for Sensor 1 shutdown pin 20 original
sensor1_shutdown = 4 
sensor2_shutdown = 18
sensor3_shutdown = 17

#RASBERRY PI GPIO HAS MEMORY!!!!!! EVEN IF UNUSED REMAIN HIGH!!!!!

GPIO.setwarnings(False)

# Setup GPIO for shutdown pins on each VL53L0X
GPIO.setmode(GPIO.BCM)  #SET LEFT GPIO SIDE ALL HIGH.  NEXT INITIATED ONLY RIGHT SIDE, LEFT SIDE STILL THERE!!!!!. 
GPIO.setup(sensor1_shutdown, GPIO.OUT)
GPIO.output(sensor1_shutdown, GPIO.HIGH) #called to get rid of previous run's state!

GPIO.setup(sensor2_shutdown, GPIO.OUT)
GPIO.output(sensor2_shutdown, GPIO.HIGH) 

GPIO.setup(sensor3_shutdown, GPIO.OUT)
GPIO.output(sensor3_shutdown, GPIO.HIGH) 

time.sleep(0.50)

#Resets Pins by rising edge. ALLOWS THE RESET OF ADDRESSES TO BE CHANGED AGAIN
GPIO.output(sensor1_shutdown, GPIO.LOW)
GPIO.output(sensor2_shutdown, GPIO.LOW)
GPIO.output(sensor3_shutdown, GPIO.LOW)
time.sleep(0.50)
'''
# Set all shutdown pins low to turn off each VL53L0X
GPIO.output(sensor1_shutdown, GPIO.LOW)

# Keep all low for 500 ms or so to make sure they reset
time.sleep(0.50)


print("start operation")
'''

'''

Working method:

Start comm with original address then change address but need to remember the changed address until power goes down!!!!

Problems faced: RASBERRY PI REMEMBERS ALL GPIO SET EVEN AFTER FUNCTION CALL!!! 4 AND 17 SEEMED CONNECTED
TOF NEEDS 5V ON SHUTDOWN TO OPERATE
ADDRESS CHANGE!!!!!

'''


# Create a VL53L0X object. ADDRESS REMAINS CHANGED AS LONG AS POWER IS STILL THERE. At power on is 29, change_address





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


time.sleep(0.50)
tof.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER) 
tof1.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)
tof2.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)


times=[tof.get_timing(), tof1.get_timing(), tof2.get_timing()]

times_max=max(times)

print("Timing %d ms" % (times_max/1000))

for count in range(1, 101):
    distance = tof.get_distance()
    if distance > 0:
        print("sensor %d - %d mm, %d cm, iteration %d" % (1, distance, (distance/10), count))
    else:
        print("%d - Error" % 1)


    distance = tof1.get_distance()
    if distance > 0:
        print("sensor %d - %d mm, %d cm, iteration %d" % (2, distance, (distance/10), count))
    else:
        print("%d - Error" % 2)


    distance = tof2.get_distance()
    if distance > 0:
        print("sensor %d - %d mm, %d cm, iteration %d" % (3, distance, (distance/10), count))
    else:
        print("%d - Error" % 2)

    time.sleep(times_max/1000000.00)


tof.stop_ranging()
tof1.stop_ranging()
tof2.stop_ranging()
tof.close()
tof1.close()
tof2.close()
