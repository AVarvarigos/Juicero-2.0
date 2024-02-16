import time
import smbus2

# Register and other configuration values:
DEFAULT_SLAVE_ADDRESS           = 0x48 #Slave address byte. Value when ADDR pin is GND
                                      #One of the following bytes are sent after the slave address byte
CONVERSION_REGISTER_ADDRESS     = 0x00 #Store sampled result in 2 unsigned bytes. Needs conversion to signed. 
CONFIG_REGISTER_ADDRESS         = 0x01 #write all configuration data there
LOW_THRESHOLD_REGISTER_ADDRESS  = 0x02 #set lo to less than 2^15 (MSB is zero) to activate ALERT
HIGH_THRESHOLD_REGISTER_ADDRESS = 0x03 #set to 8xxx hex to activate ALERT
SINGLESHOT_POWERUP_FIELD        = 0x8000  #This contains empty config data except for MSB=1 to power the device up. The config bitstream would be built from left to right.
CHANNEL_FIELD_OFFSET            = 12   #start of mux channel field in 16 bit (2 byte) config data
SINGLESHOT_SET_BYTES            = 0x0100
GAIN                            = 4    #default gain
CONFIG_CURRENT                  = 0x00   #configuration setting of device
RDY_ACTIVE_HIGH                 = 0x0000 #ADAFRUIT DID ACTIVE EDGE, I DID ACTIVE LOAD TO TURN ALERT TO SHOW AVAILABILITY, CHANGE BACK IF NOT WORK!!
SETUP_COMP_RDY                  = 0x0000 #write 00 to COMP_QUE and Thresholds to activate RDY
ADDRESS_CURRENT                 = DEFAULT_SLAVE_ADDRESS


# Maps desired data rate (SPS) to needed configuration register bit setting. 128 is default
DATA_RATE_CONFIG_BYTES = {
    8:    0x0000,
    16:   0x0020,
    32:   0x0040,
    64:   0x0060,
    128:  0x0080,
    250:  0x00A0,
    475:  0x00C0,
}


# Maps desired ADC gain to needed configuration register bit setting. 4 is default and response oversaturate after 8
ADS1x15_CONFIG_GAIN = { 
    2/3: 0x0000, #000 0
    1:   0x0200, #001 0
    2:   0x0400, #010 0
    4:   0x0600, #011 0
    8:   0x0800, #100 0
    16:  0x0A00  #101 0    LSB is Mode pin, written later during operation
}


class flex_adc(object):

    #From right to left make OS, mux channel, gain, mode, data rate, and comp fields
    def __init__(self, gain_set=4, data_rate=128, address=DEFAULT_SLAVE_ADDRESS, i2c=None, **kwargs):

        bus = smbus2.SMBus(1)
        self.address=address

        #this will power on the chip and the config's other fields will be filled by other data
        config = SINGLESHOT_POWERUP_FIELD  
        # Specify mux value.
        config |= (0x04 & 0x07) << CHANNEL_FIELD_OFFSET #MUX field starts after 12. Default samples channel 0

        # Validate the passed in gain and then set it in the config.
        if gain_set not in ADS1x15_CONFIG_GAIN:
            raise ValueError('Gain must be one of: 2/3, 1, 2, 4, 8, 16')
        config |= ADS1x15_CONFIG_GAIN[gain_set]
        # Set the mode to single-shot
        config |= SINGLESHOT_SET_BYTES
        # Set the data rate 
        if data_rate is None:
            data_rate = self._data_rate_default() #data rate set to default. Only continuous mode utilizes data rate so not too critical
        config |= self._data_rate_config(data_rate) 
        config |= SETUP_COMP_RDY  # DON'T DISABLE QUE BUT SET TO 00 01 10 AND THRESHOLDS TO CERTAIN VALUES TI ACTIVATE ALERT/RDY
        # Send the config value to start the ADC conversion.
        # Explicitly break the 16-bit value down to a big endian pair of bytes.

        write_msg=smbus2.i2c_msg.write(address, [CONFIG_REGISTER_ADDRESS, (config >> 8) & 0xFF, config & 0xFF])
        bus.i2c_rdwr(write_msg)
        #smbus2.bus.write_i2c_block_data(address, 0, [ADS1x15_POINTER_CONFIG, (config >> 8) & 0xFF, config & 0xFF])  LOW LEVEL ALTERNATIVE


        #Write hi_thres to 0x8000 and lo thres MSB to 0 to set RDY pin as conversion ready
        write_msg=smbus2.i2c_msg.write(address, [HIGH_THRESHOLD_REGISTER_ADDRESS, 0x80, 0x00])
        bus.i2c_rdwr(write_msg)

        write_msg=smbus2.i2c_msg.write(address, [LOW_THRESHOLD_REGISTER_ADDRESS, 0x07, 0xFF])
        bus.i2c_rdwr(write_msg)


    def get_default_data_rate(self):
        return 128


    def bytes2signed(self, low, high):
         #contacts the received MS byte and LS bytes to 16 bit number then make it signed by removing by subtraction 2*MSB
        # Convert to 16-bit signed value.
        value = ((high & 0xFF) << 8) | (low & 0xFF)
        # Check for sign bit and turn into a negative value if set.
        if value & 0x8000 != 0:
            value -= 1 << 16
        return value

    #Read the sample stored in the conversion register of the ADC. 
    #Need to first write to the address pointer register to set the chip to transmit conversion register's byten upon read call
    def get_sample(self, channel, data_rate=None): 

        bus = smbus2.SMBus(1)
        assert 0 <= channel <= 1, 'Channel must be a value within 0-1! Not using channels 2 and 3'

        register_access = smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONVERSION_REGISTER_ADDRESS])
        read_result = smbus2.i2c_msg.read(ADDRESS_CURRENT, 2)
        bus.i2c_rdwr(register_access, read_result)
        #or one read then one write

        return bytes2signed(read_result[0], read_result[1])



    #Request a single shot sample by writing the config file an OS=1 and MUX=desired channel
    def request_sample(self, channel, data_rate=None):  #write to config to demand data.

        bus = smbus2.SMBus(1)

        assert 0 <= channel <= 1, 'Channel must be a value within 0-1! Not using channels 2 and 3'
        # Perform a single shot read and set the mux value to the channel plus
        # the highest bit (bit 3) set.


        mux=channel + 0x04 #+4 present to get to 1xx where single channel reads are done


        # Erased the MUX field of config then set it to the new MUX
        config = ( config & ( 0x8FFF ) ) | ( (mux & 0x07) << CHANNEL_FIELD_OFFSET ) #MUX field starts after 12
        # Validate the passed in gain and then set it in the config.
        
    
        #after sending the pointer, have immediate access to the desired pointed register and can write it
        
        write_msg=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS, (config >> 8) & 0xFF, config & 0xFF])
        bus.i2c_rdwr(write_msg)
        #smbus2.bus.write_i2c_block_data(address, 0, [ADS1x15_POINTER_CONFIG, (config >> 8) & 0xFF, config & 0xFF])


















































#ADC has programmable digital comparator, AIN used to remove common mode. DOES SIGMA DELTA MODULATION

#single-shot conversion mode: only convert when master demands it, continuous: convert again after conversion is done, rate is programmable


#ADC DOESN'T DRIVE SCL CHIP SO NO CLOCK STRECTHING

#Might or might not need external filter to prevent aliasing.

#Can send conversion ready pulses if set as that. Does it after each conversion. Can use align reads with conversions?

#TIMEOUT AFTER 25MS!!!

'''
SDA is driven while SCL is low. SCL goes high then low. smbus does it automatically


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
