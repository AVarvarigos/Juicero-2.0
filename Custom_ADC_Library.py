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
GAIN       = 4    #default gain
global CONFIG_CURRENT 
CONFIG_CURRENT                  = 0x0000   #configuration setting of device
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
GAIN_CONFIG_BYTES = { 
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

        global CONFIG_CURRENT

        bus = smbus2.SMBus(1)
        ADDRESS_CURRENT=address

        #this will power on the chip and the config's other fields will be filled by other data
        config = 0x0000 
        print(hex(config))  
        # Specify mux value.
        config |= (0x04 & 0x07) << CHANNEL_FIELD_OFFSET #MUX field starts after 12. Default samples channel 0
        print(hex(config))  
        # Validate the passed in gain and then set it in the config.
        if gain_set not in GAIN_CONFIG_BYTES:
            raise ValueError('Gain must be one of: 2/3, 1, 2, 4, 8, 16')
        config |= GAIN_CONFIG_BYTES[gain_set]
        print(hex(config))  
        # Set the mode to single-shot
        config |= SINGLESHOT_SET_BYTES
        print(hex(config))  
        # Set the data rate 
        if data_rate not in DATA_RATE_CONFIG_BYTES:
            data_rate = self.get_default_data_rate() #data rate set to default. Only continuous mode utilizes data rate so not too critical
        config |= DATA_RATE_CONFIG_BYTES[data_rate] 
        print(hex(config))  
        config |= SETUP_COMP_RDY 
        print(hex(config))   
         # DON'T DISABLE QUE BUT SET TO 00 01 10 AND THRESHOLDS TO CERTAIN VALUES TI ACTIVATE ALERT/RDY
        # Send the config value to start the ADC conversion.
        # Explicitly break the 16-bit value down to a big endian pair of bytes.

        #CREATED CONFIG CORRECT

        write_msg=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS, (config >> 8) & 0xFF, config & 0xFF])
        bus.i2c_rdwr(write_msg)
        #smbus2.bus.write_i2c_block_data(address, 0, [ADS1x15_POINTER_CONFIG, (config >> 8) & 0xFF, config & 0xFF])  LOW LEVEL ALTERNATIVE



        set_read=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS])
        read_msg=smbus2.i2c_msg.read(ADDRESS_CURRENT, 2)
        bus.i2c_rdwr(set_read)#CAN'T DO RDWR IMMEDIATELY! NEED 10MS DELAY ELSE START TO MISS BITS
        time.sleep(0.0062)
        bus.i2c_rdwr(read_msg)
        print("what's in chip")
        print(hex(read_msg.buf[0][0]))
        print(hex(read_msg.buf[1][0]))


        #Write hi_thres to 0x8000 and lo thres MSB to 0 to set RDY pin as conversion ready
        write_msg=smbus2.i2c_msg.write(ADDRESS_CURRENT, [HIGH_THRESHOLD_REGISTER_ADDRESS, 0x80, 0x00])
        bus.i2c_rdwr(write_msg)

        write_msg=smbus2.i2c_msg.write(ADDRESS_CURRENT, [LOW_THRESHOLD_REGISTER_ADDRESS, 0x07, 0xFF])
        bus.i2c_rdwr(write_msg)

        CONFIG_CURRENT=config





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
    


        #SUCCESSFULLY START A CONVERSION!!! AFTER SETTING THE WRITE IT TAKES 108us TO FINISH WRITING DATA. IF DELAY TOO LARGE GET ISSUE IN SAMPLES!!!
        #NEED AT LEAST 30U TIME TO GET CONVERSION STA

        #Request a single shot sample by writing the config file an OS=1 and MUX=desired channel
    def request_sample(self, channel=0, data_rate=None):  #write to config to demand data.
        print("request")
        global CONFIG_CURRENT
        
        bus = smbus2.SMBus(1)

        assert 0 <= channel <= 1, 'Channel must be a value within 0-1! Not using channels 2 and 3'
        # Perform a single shot read and set the mux value to the channel plus
        # the highest bit (bit 3) set.


        mux=channel + 0x04 #+4 present to get to 1xx where single channel reads are done


        # Erased the MUX field of config then set it to the new MUX
        config = ( CONFIG_CURRENT & ( 0x8FFF ) ) | ( (mux & 0x07) << CHANNEL_FIELD_OFFSET ) #MUX field starts after 12
        # Validate the passed in gain and then set it in the config.

        set_read=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS])
        read_msg=smbus2.i2c_msg.read(ADDRESS_CURRENT, 2)
        bus.i2c_rdwr(set_read)#CAN'T DO RDWR IMMEDIATELY! NEED 10MS DELAY ELSE START TO MISS BITS
        time.sleep(0.0062)
        bus.i2c_rdwr(read_msg)
        
        print("what's in chip")
        print(hex(read_msg.buf[0][0])) #0 is MS 1 is LS byte
        print(hex(read_msg.buf[1][0]))

        config|=SINGLESHOT_POWERUP_FIELD
        
        #UPDATE MUX CORRECTLY!!!
    
        #after sending the pointer, have immediate access to the desired pointed register and can write it
        print("config to trigger data is")
        print(hex(config))
        write_msg=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS, (config >> 8) & 0xFF, config & 0xFF])
        bus.i2c_rdwr(write_msg)    #dONE AFTER 108 MICROSECONDS. If have 100-30us delay between request and read will see request ongoing.
        #time.sleep(108e-6)
        #smbus2.bus.write_i2c_block_data(address, 0, [ADS1x15_POINTER_CONFIG, (config >> 8) & 0xFF, config & 0xFF])
        #time.sleep(30e-6)  #IF 1 WAS WRITTEN TO OS AT POWER DOWN WRITING 1 AGAIN TAKES IT TO 0 AND STARTS CONVERSION
        #IF DELAY TOO MUCH SYSTEM CAN MESS UP!!!
        #time.sleep(100e-6)
        set_read=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS])
        read_msg=smbus2.i2c_msg.read(ADDRESS_CURRENT, 2)
        bus.i2c_rdwr(set_read)#CAN'T DO RDWR IMMEDIATELY! NEED 10MS DELAY ELSE START TO MISS BITS
        time.sleep(0.0062)
        bus.i2c_rdwr(read_msg)
        print("after write request chip")
        print(hex(read_msg.buf[0][0]))
        print(hex(read_msg.buf[1][0]))


        CONFIG_CURRENT=config

        

    #Read the sample stored in the conversion register of the ADC. 
    #Need to first write to the address pointer register to set the chip to transmit conversion register's byten upon read call
    def get_sample(self, channel=0, data_rate=None): 
        print("receive")
        bus = smbus2.SMBus(1)
        assert 0 <= channel <= 1, 'Channel must be a value within 0-1! Not using channels 2 and 3'
        
        
        set_read=smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONFIG_REGISTER_ADDRESS])
        read_msg=smbus2.i2c_msg.read(ADDRESS_CURRENT, 2)
        bus.i2c_rdwr(set_read)#CAN'T DO RDWR IMMEDIATELY! NEED 10MS DELAY ELSE START TO MISS BITS
        time.sleep(0.0062)
        bus.i2c_rdwr(read_msg)
        
        print("what's the status")
        print(hex(read_msg.buf[0][0])) #0 is MS 1 is LS byte
        print(hex(read_msg.buf[1][0]))

        
        
        
        register_access = smbus2.i2c_msg.write(ADDRESS_CURRENT, [CONVERSION_REGISTER_ADDRESS])
        read_result = smbus2.i2c_msg.read(ADDRESS_CURRENT, 2)
        bus.i2c_rdwr(register_access)
        time.sleep(0.0062)
        bus.i2c_rdwr(read_result)
        #after doing that successfully switched conversion register and read its results

        print("what's in conversion")
        print(hex(read_result.buf[0][0]))
        print(hex(read_result.buf[1][0]))

        #WORK UP TO HERE???

        #or one read then one write
        return flex_adc.bytes2signed(self, read_result.buf[0][0], read_result.buf[1][0])
        #return bytes2signed(flex_adc, read_result[0], read_result[1])
