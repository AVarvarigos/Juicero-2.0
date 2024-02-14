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
















# Copyright (c) 2016 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import time
from .ADS1x15 import ADS1115, ADS1015 #Choose best one


# Register and other configuration values:
ADS1x15_DEFAULT_ADDRESS        = 0x48
ADS1x15_POINTER_CONVERSION     = 0x00
ADS1x15_POINTER_CONFIG         = 0x01
ADS1x15_POINTER_LOW_THRESHOLD  = 0x02
ADS1x15_POINTER_HIGH_THRESHOLD = 0x03
ADS1x15_CONFIG_OS_SINGLE       = 0x8000
ADS1x15_CONFIG_MUX_OFFSET      = 12

# Maping of gain values to config register values. System designed around 16 bits and we need high resolution for bottom so use ADS1115
ADS1x15_CONFIG_GAIN = {
    2/3: 0x0000,
    1:   0x0200,
    2:   0x0400,
    4:   0x0600,
    8:   0x0800,
    16:  0x0A00
}
ADS1x15_CONFIG_MODE_CONTINUOUS  = 0x0000
ADS1x15_CONFIG_MODE_SINGLE      = 0x0100
# Mapping of data/sample rate to config register values for ADS1015 (faster).
ADS1015_CONFIG_DR = {
    128:   0x0000,
    250:   0x0020,
    490:   0x0040,
    920:   0x0060,
    1600:  0x0080,
    2400:  0x00A0,
    3300:  0x00C0
}


# Mapping of data/sample rate to config register values for ADS1115 (slower).
ADS1115_CONFIG_DR = {
    8:    0x0000,
    16:   0x0020,
    32:   0x0040,
    64:   0x0060,
    128:  0x0080,
    250:  0x00A0,
    475:  0x00C0,
    860:  0x00E0
}

#delete the comparator operations
ADS1x15_CONFIG_COMP_WINDOW      = 0x0010
ADS1x15_CONFIG_COMP_ACTIVE_HIGH = 0x0008
ADS1x15_CONFIG_COMP_LATCHING    = 0x0004
ADS1x15_CONFIG_COMP_QUE = {
    1: 0x0000,
    2: 0x0001,
    4: 0x0002
}
ADS1x15_CONFIG_COMP_QUE_DISABLE = 0x0003


'''
Unique implementation:

-Make continuous readings 
-get rid of objective programming
-change I2C to smbus I2C
-Delete comparator operations
-INTEGRATE THE ALERT PIN TO SYSTEM TO SAVE TIME!!!, ATTEMPT READ IF DATA THERE ELSE SKIP SAMPLE
-ADD AUTOMATIC CONFIGURATOR WHERE WE USE SINGLE SHOTS TO READ GAIN AND MODIFY IT UNTIL STOP OVERSHOOTING THE CHANNEL.
-ALSO CALIBRATE DATA RATE AUTOMATICALLY SOMEHOW???
-Do 2 bytes to single sample conversion in one method
-Put method to collect data from all channels at once AND OPTIMIZED?
-software I2C channel???
-DELETE ALL INSTANCES OF ADAFRUIT FROM JUICERO TO HIDE COPY PASTE!!!!!

-ADD USE OF ALERT SIGNALS TO TELL PROGRAM IF DATA READER IS READY. LINK THAT TO THE GPIO INTERRUPT!!!!
-Change I2C to send less data and MAKE CONTINUOUS READS TO GET DATA FROM ALL CHANNELS


-IMRPOVE TIMING OF TOF LIBRARY?
-IMPLEMENT MAGNETOMETER?
-Integrate high speed mode conditions and commands??
-How to program what channel to read?
-IMPLEMENT CONTINUOUS READ TO READ ALL ADC AT ONCE
-ACTIVATE HIGH SPEED MODE IN STARTUP WITH COMMAND

*set address to read first, then keep reading the conversion register
*If read the config 16 bit bitsreatm: MSB 0 mean device is doing conversion and reading 1 mean conversion is done
*CONFIG sets the input channel, SO MEAN CAN'T DO CONTINUOUS FOR ALL CHANNELS??? BİTS 14-12
000 : AINP = AIN0 and AINN = AIN1 (default) 001 : AINP = AIN0 and AINN = AIN3
010 : AINP = AIN1 and AINN = AIN3
011 : AINP = AIN2 and AINN = AIN3
100 : AINP = AIN0 and AINN = GND 101 : AINP = AIN1 and AINN = GND 110 : AINP = AIN2 and AINN = GND 111 : AINP = AIN3 and AINN = GND
*bits 4-0 set comparator settings. don't touch . USE COMPARATOR TO IMMEDIATELY SEE WHEN THERE'S NO USED???
*Set Hi-thres and Lo-thres to 8xxx and 8xxx respectively. Set to RDY mode to get OS bit in single conversion or get pulse train in continuous ate alert!!!!




Set the most-significant bit of the Hi_thresh register to 1 and the most-significant bit of Lo_thresh register to 0 to enable the pin as a conversion ready pin. 
The COMP_POL bit continues to function as expected. Set the COMP_QUE[1:0] bits to any 2-bit value other than 11 to keep the ALERT/RDY pin enabled, and allow the conversion ready signal to appear at the ALERT/RDY pin output. 
The COMP_MODE and COMP_LAT bits no longer control any function. When configured as a conversion ready pin, ALERT/RDY continues to require a pullup resistor. 
The ADS111x provide an approximately 8-μs conversion ready pulse on the ALERT/RDY pin at the end of each conversion in continuous-conversion mode, as shown in Figure 29. In single-shot mode

If not faster than 8us program should poll for the alert pin. BUT BEST IF USE ALERT SIGNAL TO CALL UPON READS


HAVE TO CHANGE CONFIG TO CHANGE THE CHANNEL READ, THERE'S ONLY ONE INPUT CAPACITOR AND CHANNELS GET MUXED TO THAT. 
SO NOT POSSIBLE TO CONTINIOUSLY READ ALL 4 CHANNELS. HAVE TO CHANGE CONFIG TO CHANGE CHANNEL

1001000 is address when set ADDR pin to GND

'''


class ADS1x15(object):
    """Base functionality for ADS1x15 analog to digital converters."""

    def __init__(self, address=ADS1x15_DEFAULT_ADDRESS, i2c=None, **kwargs):

        #REPLACE WITH SMBUS2 I2C OPERATIONS

        if i2c is None:
            import Adafruit_GPIO.I2C as I2C
            i2c = I2C
        self._device = i2c.get_i2c_device(address, **kwargs)

    def _data_rate_default(self):
        """Retrieve the default data rate for this ADC (in samples per second).
        Should be implemented by subclasses.
        """
        raise NotImplementedError('Subclasses must implement _data_rate_default!')

    def _data_rate_config(self, data_rate):
        """Subclasses should override this function and return a 16-bit value
        that can be OR'ed with the config register to set the specified
        data rate.  If a value of None is specified then a default data_rate
        setting should be returned.  If an invalid or unsupported data_rate is
        provided then an exception should be thrown.
        """
        raise NotImplementedError('Subclass must implement _data_rate_config function!')

    def _conversion_value(self, low, high):
        """Subclasses should override this function that takes the low and high
        byte of a conversion result and returns a signed integer value.
        """
        raise NotImplementedError('Subclass must implement _conversion_value function!')


    #DO CONFIGURATION AT THE STARTUP, REMOVE SLEEP, PUT CONVERSION RESULT TO SAME METHOD, REPLACE READLIST WITH SMBUS METHOD!!!

    def _read(self, mux, gain, data_rate, mode):
        """Perform an ADC read with the provided mux, gain, data_rate, and mode
        values.  Returns the signed integer result of the read.
        """

        config = ADS1x15_CONFIG_OS_SINGLE  # Go out of power-down mode for conversion.
        # Specify mux value.
        config |= (mux & 0x07) << ADS1x15_CONFIG_MUX_OFFSET
        # Validate the passed in gain and then set it in the config.
        if gain not in ADS1x15_CONFIG_GAIN:
            raise ValueError('Gain must be one of: 2/3, 1, 2, 4, 8, 16')
        config |= ADS1x15_CONFIG_GAIN[gain]
        # Set the mode (continuous or single shot).
        config |= mode
        # Get the default data rate if none is specified (default differs between
        # ADS1015 and ADS1115).
        if data_rate is None:
            data_rate = self._data_rate_default()
        # Set the data rate (this is controlled by the subclass as it differs
        # between ADS1015 and ADS1115).
        config |= self._data_rate_config(data_rate)
        config |= ADS1x15_CONFIG_COMP_QUE_DISABLE  # Disble comparator mode.
        # Send the config value to start the ADC conversion.
        # Explicitly break the 16-bit value down to a big endian pair of bytes.
        self._device.writeList(ADS1x15_POINTER_CONFIG, [(config >> 8) & 0xFF, config & 0xFF])
        # Wait for the ADC sample to finish based on the sample rate plus a
        # small offset to be sure (0.1 millisecond).
        time.sleep(1.0/data_rate+0.0001)
        # Retrieve the result.
        result = self._device.readList(ADS1x15_POINTER_CONVERSION, 2)
        return self._conversion_value(result[1], result[0])
    

    def read_adc(self, channel, gain=1, data_rate=None):
        """Read a single ADC channel and return the ADC value as a signed integer
        result.  Channel must be a value within 0-3.
        """
        assert 0 <= channel <= 3, 'Channel must be a value within 0-3!'
        # Perform a single shot read and set the mux value to the channel plus
        # the highest bit (bit 3) set.
        return self._read(channel + 0x04, gain, data_rate, ADS1x15_CONFIG_MODE_SINGLE)

    def read_adc_difference(self, differential, gain=1, data_rate=None): 
        """Read the difference between two ADC channels and return the ADC value
        as a signed integer result.  Differential must be one of:
          - 0 = Channel 0 minus channel 1
          - 1 = Channel 0 minus channel 3
          - 2 = Channel 1 minus channel 3
          - 3 = Channel 2 minus channel 3
        """
        assert 0 <= differential <= 3, 'Differential must be a value within 0-3!'
        # Perform a single shot read using the provided differential value
        # as the mux value (which will enable differential mode).
        return self._read(differential, gain, data_rate, ADS1x15_CONFIG_MODE_SINGLE)

    def start_adc(self, channel, gain=1, data_rate=None): #do this to bypass read times and keep value ready at hand
        """Start continuous ADC conversions on the specified channel (0-3). Will
        return an initial conversion result, then call the get_last_result()
        function to read the most recent conversion result. Call stop_adc() to
        stop conversions.
        """
        assert 0 <= channel <= 3, 'Channel must be a value within 0-3!'
        # Start continuous reads and set the mux value to the channel plus
        # the highest bit (bit 3) set.
        return self._read(channel + 0x04, gain, data_rate, ADS1x15_CONFIG_MODE_CONTINUOUS)

    def start_adc_difference(self, differential, gain=1, data_rate=None): 
        #KEEP THIS
        """Start continuous ADC conversions between two ADC channels. Differential
        must be one of:
          - 0 = Channel 0 minus channel 1
          - 1 = Channel 0 minus channel 3
          - 2 = Channel 1 minus channel 3
          - 3 = Channel 2 minus channel 3
        Will return an initial conversion result, then call the get_last_result()
        function continuously to read the most recent conversion result.  Call
        stop_adc() to stop conversions.
        """
        assert 0 <= differential <= 3, 'Differential must be a value within 0-3!'
        # Perform a single shot read using the provided differential value
        # as the mux value (which will enable differential mode).
        return self._read(differential, gain, data_rate, ADS1x15_CONFIG_MODE_CONTINUOUS)


    def stop_adc(self):
        """Stop all continuous ADC conversions (either normal or difference mode).
        """
        # Set the config register to its default value of 0x8583 to stop
        # continuous conversions.
        config = 0x8583
        self._device.writeList(ADS1x15_POINTER_CONFIG, [(config >> 8) & 0xFF, config & 0xFF])

    def get_last_result(self):   #PUT THIS
        """Read the last conversion result when in continuous conversion mode.
        Will return a signed integer value.
        """
        # Retrieve the conversion register value, convert to a signed int, and
        # return it.

        result = self._device.readList(ADS1x15_POINTER_CONVERSION, 2)
        return self._conversion_value(result[1], result[0])


class ADS1115(ADS1x15):
    """ADS1115 16-bit analog to digital converter instance."""

    def __init__(self, *args, **kwargs):
        super(ADS1115, self).__init__(*args, **kwargs)

    def _data_rate_default(self):
        # Default from datasheet page 16, config register DR bit default.
        return 128

    def _data_rate_config(self, data_rate): #return the dr config bitstream needed for dr setting
        if data_rate not in ADS1115_CONFIG_DR:
            raise ValueError('Data rate must be one of: 8, 16, 32, 64, 128, 250, 475, 860')
        return ADS1115_CONFIG_DR[data_rate]

    def _conversion_value(self, low, high): 
        #contacts the received MS byte and LS bytes to 16 bit number then make it signed by removing by subtraction 2*MSB
        # Convert to 16-bit signed value.
        value = ((high & 0xFF) << 8) | (low & 0xFF)
        # Check for sign bit and turn into a negative value if set.
        if value & 0x8000 != 0:
            value -= 1 << 16
        return value


class ADS1015(ADS1x15):
    """ADS1015 12-bit analog to digital converter instance."""

    def __init__(self, *args, **kwargs):
        super(ADS1015, self).__init__(*args, **kwargs)

    def _data_rate_default(self):
        # Default from datasheet page 19, config register DR bit default.
        return 1600

    def _data_rate_config(self, data_rate):
        if data_rate not in ADS1015_CONFIG_DR:
            raise ValueError('Data rate must be one of: 128, 250, 490, 920, 1600, 2400, 3300')
        return ADS1015_CONFIG_DR[data_rate]

    def _conversion_value(self, low, high):
        # Convert to 12-bit signed value.
        value = ((high & 0xFF) << 4) | ((low & 0xFF) >> 4)
        # Check for sign bit and turn into a negative value if set.
        if value & 0x800 != 0:
            value -= 1 << 12
        return value










































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
