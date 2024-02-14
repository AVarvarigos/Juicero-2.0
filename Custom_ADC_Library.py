print("hello world")
print("terminal works")

#Raspberry Pi Zero W clock is 1GHz->1ns per instruction->need delays
#I2C COMMUNICATIONS CAN'T OCCUR CONCURRENTLY DUE TO SHARED BUS

#Find better way to give delay to system rather than delay. Thread can be paused and restarted again by Timer???

#HAVE FAST MODE AND HIGH SPEED MODE, HIGH SPEED MODE USES FASTER CLOCK
#Duration of start condition (bus free time between START AND STOP) is 600n or 160n
#Start clock 600 or 160ns after start condition (SDA pulse go up then down) 
#After clock isn't driven anymore, send stop condition again only after 600-160ns
#No hold time (can change clock just after SDA changed value)
#Setup time is 100-10 ns (data not change for 100ns after clock rose)
#min width of low period is 1300-160 ns and min width of high period is 600-60
#clock fall time is 300-160ns and rise time is same min. CLOCK OF MASTER MUST OBEY THAT

































#ADC has programmable digital comparator, AIN used to remove common mode. DOES SIGMA DELTA MODULATION

#single-shot conversion mode: only convert when master demands it, continuous: convert again after conversion is done, rate is programmable


#ADC DOESN'T DRIVE SCL CHIP SO NO CLOCK STRECTHING

#Might or might not need external filter to prevent aliasing.

#Can send conversion ready pulses if set as that. Does it after each conversion. Can use align reads with conversions?

#TIMEOUT AFTER 25MS!!!

'''
SDA is driven while SCL is low. SCL goes high then low


0) Send start condition
1) Address byte and bit to tell adc to listen
2) Register pointer got from register map table (MIGHT NOT BE PRESENT FOR READ?)
3) MS byte of data to write, data read
4) LS byte of data to write, data read. LOOK AT READ AND WRITE TIMING OPERATIONS
5) Send stop condition or repeated start condition

DATA IS 2 BYTES (16 bit) 2S COMPLEMENT (change to unsigned?)


DO FAST MODE FIRST SINCE VERY FAST NEED ADDITIONAL SETTING. IF TOO SLOW CHANGE TO VERY FAST

THERE IS AN ACKNOWLEDGEMENT BETWEEN EACH BYTE

'''

'''

IDLE: SDA AND SCL HIGH
start condition: SCL is high SDA goes high to low
stop condition: SCL returns back to high SDA goes from low to high
address byte i 7 bits, last bit is R or W

write ack: after sending byte master stop driving SDA. SCL is low. Slave send a bit by asserting SDA. 
0: acknowledge 1: not acknowledged (Throw in error exception then)
Master than takes SCL high then low to clock acknowledgement. If 0, next byte is the next byte

read ack: (master clocks the system, slave updates the data), after read byte, master drives
the SDA line low after the LSB and clocks it. If slave sees that aknowledgement it continues sending data. ELSE WHAT???


At the end, may issue STOP (just bring SDA back to high) or do repeated start (bring SDA high then low again)

Send 0 instead of address (72-75) to send commands. 06h resets and powers down

Send 00001xxx then start condition to start communication at very fast mode. This byte not need acknowledge. Switch out after stop. xxx unique to Hs-capable master.

??????Is by high-speed mode capable??????


'''

#FOR SIMPLICITY KEEP SAME DELAY FOR ENTIRE COMMUNICATION THEN OPTIMIZE. I2C DRIVER HANDLES THIS SO WORRY ABOUT DELAY BETWEEN NEW DATA?



'''
To change register read, MUST FIRST CHANGE THE POINTER REGISTER VALUE. 
For read, only write when wanna read other register, for write write to Pointer always before a read

Protocol: start comm, send slave address with R/W=0, send in the Pointer register value 000000xx (xx denotes register to change to) then STOP communication.
Next read communication will read from register at address xx.

RESISTERS:
00: conversion (contain result of last conversion), 2 byte (READ THIS DURING OPERATION)
01:  config: 2 byte with fields that tell operation modes (WRITE TO THAT AT START)
10: lo_thresh: low threshold of hysteresis internal comparator (WRITE AT START)
11: hi_thresh: high threshold of hysteresis internal comparator (WRITE AT START) (comparator can also setup to give high only if in range of these thresholds) (reduce comparison operation to digitalRead)
Can'y use comparator if change ALRT pin to conversion ready pin that goes high when new data is written

Store state of pointer in rasberry. Only send pointer if we need to update

'''


'''

DATA RATE CAN BE PROGRAMMABLE, START LOW INCREASE LATER AT SETUP (8 to 860 samples per second, optimize to i2c read speed and processor latency)
(not time critical can keep system slow)
COMPARATOR PRESENT
DIFFERENTIAL INPUT PRESENT

SAMPLING RATE???: 

'''
