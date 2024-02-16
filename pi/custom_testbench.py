import Custom_ADC_Library
import time


adc=Custom_ADC_Library.flex_adc()


adc.request_sample(channel=0)

time.sleep(110e-6) #after that time sample should be ready

print(adc.get_sample(channel=0))

adc.request_sample(channel=1)

time.sleep(0.1)
           

while True: 
    print(adc.get_sample(channel=1))