
import time #ADDESSES OF TOF NOT VOTTRVT FIXED FIRST NEED TO CONNECT 2ND FIRST TO FIX ADDRESS

# Import the ADS1x15 module.
import Adafruit_ADS1x15
import VL53L0X
import RPi.GPIO as GPIO

#INCREASE I2C CLOCK SPEED TO 400K SOMEHOW

#Have 3 tasks: network, ML, and data collection. Network threading is automatic so make data collection tasks to interrupts and put ML + some network operations as main loop (or thread network and ML at main loop)




#SETUP()
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
print("Totoal timing %d ms" % (times_max/1000))



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



f = open("dataGet.txt", "a")
f.write("\n===start===")

print('Reading ADS1x15 and VL53L0X values, press Ctrl-C to quit...')
# Print nice channel column headers.
print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*range(4)))
print('-' * 37)




adc_values = [0]*4
distance=[0]*3


#Have another loop where device waits for a GO signal from server to start sending data. Can be turned on or off by user
#Also include something where when user logs into the website server will ask for information about past session?


#OPTIMIZE ADC DATA RATES AND TOF DATA COLLECTION MODES BASED ON TOMORROW'S TESTS

counter = 0
#LOOP(). Make this an interrupt or put with ML in series
while True: #CHANGE TO HAVE DEVICE START COLLECTING DATA WHEN SUCCESSFUL LOGIN IS DONE ON THE WEBSITE AND THE DEVICE IS ACTIVATED
    # Read all the ADC channel values in a list.
    
    if (counter%50==0):
        print("Data " + str(counter) + " input:")
        spec = input()
        counter = counter + 1
    else:
        counter = counter + 1

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

    '''


    DO POTENTIAL DATA PROCESSING AND FILTERING HERE!!!!! (average samples, convert raw data, etc
    
    IF MAKE MORE SAMPLES THAN ML CAN PROCESS THEN COMPRESS DATA POINTS THROUGH AVERAGING

    '''

    # PRINT DATA FOR DEBUG PURPOSES BUT IN APPLICATION WE SAVE THEM TO BUFFER
    print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*adc_values))
    print('Distance 0: ' + str(distance[0]) + ' Distance 1: ' + str(distance[1]) + ' Distance 2: ' + str(distance[2]))
    if(spec != "p"):
        f.write("\n"+"|"+str(distance[0])+"|"+str(distance[1])+"|"+str(distance[2])+"|"+str(spec)+"|")
    if len(sampler_buffer)/(FLEX_AMOUNT + IR_AMOUNT +1) < SAMPLER_BUFFER_LENGTH:
        sampler_buffer=sampler_buffer + adc_values + distance + [-1] #-1 here to tell the end of packet



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
tof.stop_ranging()
GPIO.output(sensor2_shutdown, GPIO.LOW)
tof1.stop_ranging()
GPIO.output(sensor1_shutdown, GPIO.LOW)
tof2.stop_ranging()
GPIO.output(sensor1_shutdown, GPIO.LOW)

tof.close()
tof1.close()
tof2.close()
