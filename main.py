import time

# Import the ADS1x15 module.
import Adafruit_ADS1x15
import VL53L0X
import RPi.GPIO as GPIO

#INCREASE I2C CLOCK SPEED TO 400K SOMEHOW

#Have 3 tasks: network, ML, and data collection. Network threading is automatic so make data collection tasks to interrupts and put ML + some network operations as main loop (or thread network and ML at main loop)




#SETUP()
# Create an ADS1115 ADC (16-bit) instance.
adc = Adafruit_ADS1x15.ADS1115()  

sensor1_shutdown = 4
sensor2_shutdown = 18

GPIO.setwarnings(False)

# Setup GPIO for shutdown pins on each VL53L0X
GPIO.setmode(GPIO.BCM)
GPIO.setup(sensor1_shutdown, GPIO.OUT)
GPIO.setup(sensor2_shutdown, GPIO.OUT)

# Set all shutdown pins low to turn off each VL53L0X
GPIO.output(sensor1_shutdown, GPIO.LOW)
GPIO.output(sensor2_shutdown, GPIO.LOW)

# Create one object per VL53L0X passing the address to give to
# each. TOF CAN HAVE AS MANY ADDRESSES AS POSSIBLE AND AS MANY TOF DEVICES AS POSSIBLE.
#Set address of each by using shutdown GPIO pins to shutdown all except desired TOF, alter its address, then repeat for other sensors (not effect by comm when at shutdown)
tof = VL53L0X.VL53L0X(i2c_address=0x2B)
tof1 = VL53L0X.VL53L0X(i2c_address=0x2D)
tof.open()
tof1.open()

time.sleep(0.50)


# Set shutdown pin high for the first VL53L0X then  (turning them on one by one)
# call to start ranging 
GPIO.output(sensor1_shutdown, GPIO.HIGH)
time.sleep(0.50) #CHANGE DELAYS TO BE LOWER IF POSSIBLE
tof.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER) #IMPROVE ACCURACY MODE IF WANT MORE ACCURACY

# Set shutdown pin high for the second VL53L0X then 
# call to start ranging 
GPIO.output(sensor2_shutdown, GPIO.HIGH)
time.sleep(0.50)
tof1.start_ranging(VL53L0X.Vl53l0xAccuracyMode.BETTER)

timing = tof.get_timing() #how to alter it?
if timing < 20000:
    timing = 20000
print("Timing %d ms" % (timing/1000))



#buffers
sampler_buffer=[]
ML_buffer=[]
SAMPLER_BUFFER_LENGTH=100 #Optimize lengths to save space but should be large enough to not be overflown
ML_BUFFER_LENGTH=100
FLEX_AMOUNT=4
IR_AMOUNT=2
GAIN = [1, 1, 1, 1] #INCREASE GAIN TO ALTER SENSITIVITY #FINISH CALIBRATION!

#ML SETUP STATEMENTS GO HERE (Chang)
#NETWORK LIBRARY SETUP STATEMENTS GO THERE (Anastasis)

max_sit_time=-1 #represent time in minutes or hours? A way to ensure timer() won't overflow!

#ALSO ADD SETUP SERVER COMMUNICATIONS WHERE SERVER SEND PACKETS TO SETUP SYSTEM ACCORDING TO USER INPUTS (SITTING TIME, HEIGHT, WEIGHT, AREA TO FOCUS ON, ETC) AND DEVICE WILL LET 





print('Reading ADS1x15 and VL53L0X values, press Ctrl-C to quit...')
# Print nice channel column headers.
print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*range(4)))
print('-' * 37)




adc_values = [0]*4
distance=[0]*2


#Have another loop where device waits for a GO signal from server to start sending data. Can be turned on or off by user
#Also include something where when user logs into the website server will ask for information about past session?


#LOOP(). Make this an interrupt or put with ML in series
while True: #CHANGE TO HAVE DEVICE START COLLECTING DATA WHEN SUCCESSFUL LOGIN IS DONE ON THE WEBSITE AND THE DEVICE IS ACTIVATED
    # Read all the ADC channel values in a list.
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
    time.sleep(timing/1000000.00) #IMPROVE THAT? MAKE IT NONBLOCKING SOMEHOW AND LET ML DATA COLLECTOR WORK DURING THAT TIME


    #DO POTENTIAL DATA PROCESSING AND FILTERING HERE!!!!! (average samples, convert raw data, etc


    # PRINT DATA FOR DEBUG PURPOSES BUT IN APPLICATION WE SAVE THEM TO BUFFER
    print('| {0:>6} | {1:>6} | {2:>6} | {3:>6} |'.format(*adc_values))
    print('Distance 0: ' + distance[0] + 'Distance 1: ' + distance[1])

    if len(sampler_buffer)/(FLEX_AMOUNT + IR_AMOUNT +1) < SAMPLER_BUFFER_LENGTH:
        sampler_buffer=sampler_buffer + adc_values + distance + [-1] #-1 here to tell the end of packet

    # Pause for half a second.    
    time.sleep(0.5) #FOR READING OUTPUT DATA ONLY??? REMOVE THAT FOR FINAL DESIGN TO REDUCE LATENCY


    #ML OPERATIONS GO THERE: READ FROM SAMPLE BUFFER (SAMEK BUFFER OR DIFFERENT BUFFER), DO ML CALCULATION (OPTIMIZED), MAKE RESULT PACKET, GIVE RESULT PACKET TO NETWORK
    #BASED ON ML RESULT, ML WILL START A HAPTIC VIBRATION PULSE TRAIN WHICH WILL PERIODICALLY SEND SUCCESSIVE PULSES. NUMBER OF PULSES DEPEND ON WHICH BAD POSTURE DEVICE WANTS TO WARN ABOUT (user can turn on off bad posture outputs or focus on certain ones based on their needs)
    #NEED TO MAKE SURE HAPTIC PULSE IS NONBLOCKING AND ITS TIMING IS ACCURATE. IF RUNTIME OF OTHER STUFF IS BAD, MAKE IT A HIGH PRIORITY INTERRUPT OF SHORT RUNTIME (but a periıd of 2 seconds)

    #ML_BUFFER WRITING GO THERE

    #NETWORK OPERATIONS GO THERE: READ FROM ML BUFFER, BASED ON NETWORK QUALITY SEND SOME DATA PACKETS AT FIXED RATE TO THE SERVER. GOOD IF SENDING PACKET IS NONBLOCKING BUT HAVE TO ENSURE WHEN WE WANT TO SEND NEW PACKET PREVIOUS IS ALREADY SENT

    #TO DO: AFTER GETTING max_sit_time functionality COMPARE SITTING TIME WITH TIME SET BY SERVER. IF LARGER THAN SERVER TIME OVERWRITE HAPTIC TO GIVE OUT CONTINUOUS PULSE


#TO DO: Calibration, testing code, ADC I2C library, model training, haptic implementation


'''
-Network in background if can make that: FIND LIBRARY THAT ALLOWS THAT
-If have time, sampling is in interrupt that will interfere with ML operation but will ensure fast and continuous data collection. CANNOT PARALLEL I2C COMMUNICATIONS BUT IMPROVE SOMEHOW??? (multiple I2C ports?)
-ML stuff will be in the main While(1) loop
'''





    
        
#What TOF does when program is terminated. How to add some sort of stop condition to ensure this is executed when operation is done. Look more into what these methods do!      
tof1.stop_ranging()
GPIO.output(sensor2_shutdown, GPIO.LOW)
tof.stop_ranging()
GPIO.output(sensor1_shutdown, GPIO.LOW)

tof.close()
tof1.close()

    