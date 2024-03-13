#include <Arduino.h>

#include <U8g2lib.h>

#include <bitset>

#include <HardwareTimer.h>

#include <STM32FreeRTOS.h>

#include <ES_CAN.h>





/*

 

IMPLEMENT KNOB CLASS (MUST) (mutex rotary positions rest is only used by class itself) (all synchronization must be done internally) PRIORITY TASK

 

Update the rotation value using the latest state of the quadrature inputs

Set upper and lower limits

Read the current rotation value

 

Make the class thread safe, meaning that all public methods behave as reenterant functions and they can be called from concurrent tasks without need needing additional synchronisation locks outside the member functions.

 

PUT ALL GLOBALS TO ONE FILE AND IMPLEMENT METHODS THAT INCLUDES THE SYNCHRONIZATION INSIDE THEM

 

USE C++ RAII

 

VERIFY QUALITY OF KNOB TRANSFER

 

-MAKE IFNDEF BASED RECEIVER AND TRANSMITTER SELECTION

-ADD KNOB CONTROL TO OCTAVE (1-10) AND KNOB LIBRARY TO HIDE THREADING STUFF

-HIDE THREADING STUFF

-EXECUTION TIME ANALYSIS

-READ ME

-INTEGRATE WITH PATRICK CODE

 

DO TIMING ANALYSIS




Advanced: move the central octave of system. Use joystick to setup octaves. Setup to different waveforms. Echo effect. SMT32 UPGRADE

 

*/









//Constants

  const uint32_t interval = 100; //Display update interval

 

//Pin definitions

  //Row select and enable

  const int RA0_PIN = D3;

  const int RA1_PIN = D6;

  const int RA2_PIN = D12;

  const int REN_PIN = A5;

 

  //Matrix input and output

  const int C0_PIN = A2;

  const int C1_PIN = D9;

  const int C2_PIN = A6;

  const int C3_PIN = D1;

  const int OUT_PIN = D11;

 

  //Audio analogue out

  const int OUTL_PIN = A4;

  const int OUTR_PIN = A3;

 

  //Joystick analogue in

  const int JOYY_PIN = A0;

  const int JOYX_PIN = A1;

 

  //Output multiplexer bits

  const int DEN_BIT = 3;

  const int DRST_BIT = 4;

  const int HKOW_BIT = 5;

  const int HKOE_BIT = 6;

 

//Display driver object

U8G2_SSD1305_128X32_NONAME_F_HW_I2C u8g2(U8G2_R0);






//Handhshaking variables

 

//Saves information about the id of the keyboard and its current position in keyboard matrix

struct Device{

 

  uint8_t ID;

 

  uint8_t position;

 

};

 

//contains list of all devices in the keyboard matrix

std::vector<Device> device_list;

Device currentDevice = {HAL_GetUIDw0() & 255, 99};

 

//intended that to be the ID used for handshake communication

uint32_t handshakeID = 0x124; //0x123




//octave=4

const uint32_t stepSizes [] = {51076056, 54113197, 57330935, 60740010, 64351798, 68178356, 72232452, 76527617, 81078186, 85899346, 91007186, 96418756, 0};

 

char*  notes [] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B", "N/A"};

 

//Struct to save key presses.

struct KeyInfo{

 

  uint32_t currentStepSize;

 

  char* note;

 

};

 

//Statics use by scan thread only

static uint32_t phaseAcc = 0;

static uint32_t phaseAcc_CAN = 0;

static std::bitset<2> prevKnobState3 = 0;

static std::bitset<2> prevKnobState2 = 0;

static uint8_t direction3= 0;

static uint8_t direction2= 0;

//bitstream to save if buttons are being Pressed or Unpressed. REPLACE WITH INPUTS???

static std::bitset<32> pressState;      //IF GET ERROR PROBABLY GET IT FROM HERE

 

//globals used by multiple tasks

 

const uint8_t ID = HAL_GetUIDw0() & 255; //only need to get id once

 

volatile KeyInfo currentKey = {stepSizes[12], notes[12]};   //in polyphony, update to Patrick's design, probably a list of keys pressed and can sounds made

volatile KeyInfo CANKey = {stepSizes[12], notes[12]};

 

volatile uint8_t TX_Message[8] = {0};

 

//TX and RX Queues

QueueHandle_t msgInQ;

QueueHandle_t msgOutQ;

 

//Semaphore handle used to signal TX that queue is ready to be filled

SemaphoreHandle_t CAN_TX_Semaphore;

 

//everything that is mutexed. Put RX and TX to seperate mutexes?

struct {

 

  std::bitset<32> inputs; 

  std::uint8_t knobPos3;

  std::uint8_t knobPos2;

  uint8_t RX_Message[8];

  SemaphoreHandle_t mutex;

 

} sysState;




//ISRs

 

//ISR of transmitter that gives semaphore to transmit thread when tx queue is empty

void CAN_TX_ISR (void) {

  xSemaphoreGiveFromISR(CAN_TX_Semaphore, NULL);

}

 

//ISR of receiver than only activates when RX BUFFER GAINS AN ELEMENT

void CAN_RX_ISR (void) {

  uint8_t RX_Message_ISR[8];

  uint32_t ID;

  CAN_RX(ID, RX_Message_ISR);

  xQueueSendFromISR(msgInQ, RX_Message_ISR, NULL);

}

 

//get the current keypress, compute necessary waveform phase, write to speaker

//FUTURE: Add check to make it send data to CAN transmit buffer instead to speaker for transmitter key

 

void sampleISR() { //higher priority than CAN, will overwrite it's messages unless polyphony implemented!!!!

// (octave-4) >=0 ? __atomic_load_n(&currentKey.currentStepSize, __ATOMIC_RELAXED) << (octave-4) : __atomic_load_n(&currentKey.currentStepSize, __ATOMIC_RELAXED) >> (4-octave)

 

  uint8_t octave = __atomic_load_n(&sysState.knobPos2, __ATOMIC_RELAXED);  //will use octave stored in knob2 to scale the note to set octave

  phaseAcc += (octave-4) >=0 ? __atomic_load_n(&currentKey.currentStepSize, __ATOMIC_RELAXED) << (octave-4) : __atomic_load_n(&currentKey.currentStepSize, __ATOMIC_RELAXED) >> (4-octave); //allow to overflow???

  //__atomic_load_n(&currentKey.currentStepSize, __ATOMIC_RELAXED) << (octave - 4); //allow to overflow???

  phaseAcc_CAN += __atomic_load_n(&CANKey.currentStepSize, __ATOMIC_RELAXED);

  int32_t Vout = (phaseAcc >> 24) - 128;

  int32_t Vout_CAN = (phaseAcc_CAN >> 24) - 128;

 

  Vout += Vout_CAN;

 

  Vout = Vout >> (8 - __atomic_load_n(&sysState.knobPos3, __ATOMIC_RELAXED));

 

  analogWrite(OUTR_PIN, Vout + 128); //Possibility of Stereo?




}




//Row Reader

std::bitset<4> readCols(){

 

  std::bitset<4> result;

 

  result[0] = digitalRead(C0_PIN);

  result[1] = digitalRead(C1_PIN);

  result[2] = digitalRead(C2_PIN);

  result[3] = digitalRead(C3_PIN);

 

  return result;

 

}




//The bitstream where element i is given to be clocked by certain DFF when ith row is accessed during keyscan. i=5 and 6 are for west and east side handshakes specifically

//All outbits outputs are driven to the single output OUT_PIN, what Ri row changes determine where it's demuxed to

 

//For reception of handshake signal, the input is seen as another key input and mapped to the key matrix elements 5 3 and 6 3 (LOW WHEN INPUT PRESENT)

 

std::bitset<7> outBits = 120;  //1 1 1 1 0 0 0   ;   THE WEST HANDSHALKE DFF IS UPDATED TO outBits[i] R5 ROW IS SELECTED BY THE ROW ADDRESS UPDATE

 

void setRow(uint8_t rowIdx){

 

digitalWrite(REN_PIN, LOW);

digitalWrite(RA0_PIN, rowIdx & 1);

digitalWrite(RA1_PIN, (rowIdx & 2)>>1);

digitalWrite(RA2_PIN, (rowIdx & 4)>>2);

 

//put handshake update here. EACH BIT LATCHED AT EACH UPDATE OF R5

digitalWrite(OUT_PIN, outBits[rowIdx]);

 

digitalWrite(REN_PIN, HIGH); //Update selected row address i. When the corresponding Ri row is selected, the outBits[i] is also clocked

 

delayMicroseconds(3); //switching rows take time ensure it happens   RIGHT NOW TOO MUCH KEY PRESS PUTS ONE BOARD DEADLOCK TO SCAN THREAD ONLY

 

}




//Function to set outputs using key matrix

void setOutMuxBit(const uint8_t bitIdx, const bool value) {

      digitalWrite(REN_PIN,LOW);

      digitalWrite(RA0_PIN, bitIdx & 0x01);

      digitalWrite(RA1_PIN, bitIdx & 0x02);

      digitalWrite(RA2_PIN, bitIdx & 0x04);

      digitalWrite(OUT_PIN,value);

      digitalWrite(REN_PIN,HIGH);

      delayMicroseconds(2);

      digitalWrite(REN_PIN,LOW);

}






//Tasks

/*

CAN upgrade:

 

CAN volume set to prev keyboard

PITCH VARIABLE WITH KNOB

Knob Library to hide knob changes




*/

 

//TX task. Wait for item from TX queue then give it to out buffer when there's space

void CAN_TX_Task (void * pvParameters) {

  uint8_t msgOut[8];

  while (1) {

    xQueueReceive(msgOutQ, msgOut, portMAX_DELAY);

    xSemaphoreTake(CAN_TX_Semaphore, portMAX_DELAY);

    CAN_TX(0x123, msgOut);

  }

}





//RX task. Only called when data in RX queue, gets it decodes it and saves it to CANKey struct

void decodeTask(void * pvParameters){

 

  while(1){

 

    uint8_t RX_Message_Got[8] = {0};

 

    //thread waits until getting go from receiver isr

    xQueueReceive(msgInQ, RX_Message_Got, portMAX_DELAY);

 

    //check if release

    uint32_t stepsize_can = 0;

    char* chosenKey_can = "N/A";

 

    bool update_canstep = false;

 

    //if got an update, change CAN's stepsize! Keep CAN and local stepsized isolated to prevent issues. Get whatever sound CAN wants to make and add it to stepsize

 

    if(RX_Message_Got[0] == 'P'){ //decode stepsize, activate stepsize parameter

 

      chosenKey_can = notes[RX_Message_Got[2]];

      stepsize_can = (RX_Message_Got[1]-4) >=0 ? stepSizes[RX_Message_Got[2]] << (RX_Message_Got[1]-4) : stepSizes[RX_Message_Got[2]] >> (4-RX_Message_Got[1]); //first get octave for 4 then use shift to double or half to message's octave

      update_canstep = true;

 

    }

 

    else if (RX_Message_Got[0] == 'U'){ //if the button the CAN is activated for is deactivated, deactivate the switch by not updating the CAN state

 

      update_canstep = true;

 

    }

 

   

 

    if(update_canstep){

 

      __atomic_store_n(&CANKey.currentStepSize, stepsize_can, __ATOMIC_RELAXED);

      CANKey.note=chosenKey_can;

 

      xSemaphoreTake(sysState.mutex, portMAX_DELAY);

 

      sysState.RX_Message[0] = RX_Message_Got[0];

      sysState.RX_Message[1] = RX_Message_Got[1];

      sysState.RX_Message[2] = RX_Message_Got[2];

 

    xSemaphoreGive(sysState.mutex);

 

    }

 

  }

 

}





//Don't detect press at A if C is being pressed. Would implement fix by having a vector of messages and sending them to buffer, but better if system worked with polpphony system

 

//Receiving input, decoding it, and giving to relevant buffers to be processed

void scanKeysTask(void * pvParameters) {

 

  //NEED TO BE FASTER TO CAPTURE MORE FREQUENCT KEY PRESSES. TOO FAST PRESS CAN CAUSE TASKDELAY() TO GO HAYWIRE

 

  const TickType_t xFrequency = 20/portTICK_PERIOD_MS;   //denominator converts ms to clock ticks. setting the initiation period of task in ticks. Set to 50ms

  TickType_t xLastWakeTime = xTaskGetTickCount();

  TickType_t start;

 

  while (1) {

 

    vTaskDelayUntil(&xLastWakeTime, xFrequency); //block until time becomes xFrequency+lastWakeTime (initiation period passed since last call). PUTS THREAD TO WAIT STATE

 

    //Local Variables

    KeyInfo chosenKey= {stepSizes[12], notes[12]};

    std::bitset<32> inputs;

 

    std::bitset<2> knobState3; //volume

    std::bitset<2> knobState2; //octave

 

    uint8_t TX_Message_Made[8] = {0};

   

    bool send_tx = false;

 

    for(int i=0; i<4; i++){

 

      setRow(i);

      std::bitset<4> row = readCols();

 

      for(int j=0; j<4; j++){ //IN CAN, ONLY WANT TO SEND STATE CHANGES IN ORDER TO REDUCE RX INTERRUPT FROM TAKING OPERATION OVER

 

        int key=4*i+j;

 

        inputs[key]   = row[j];

 

        if(i<3){ //looking at keys not knobs atm. write seperate control code for knobs

 

          if(!row[j]){ //if pressed

 

            chosenKey.currentStepSize=stepSizes[key];

            chosenKey.note=notes[key];

 

            //want to send message only when key press state changes

 

            if(pressState[key] == 0){ //if the button wasn't on when press occured, send update to transmitter. The Latest key press would be overwritten to Tx_message_made frame

              TX_Message_Made[0]='P';

              TX_Message_Made[2] = key;

              send_tx=true;

            }

 

            pressState[key] = 1;

 

          }

 

          else{ //if unpressed

 

            //right now, only send update for the chosen button

            if(pressState[key] == 1 && notes[key] == currentKey.note){ //if the button was on before, send update to transmitter. The Latest key press would be overwritten to Tx_message_made frame

              TX_Message_Made[0]='U';

              TX_Message_Made[2] = key;

              send_tx=true;

            }

 

            pressState[key] = 0;

 

          }

 

        }




      }

 

    }

 

    //IN FUTURE WOULD SEND OUT KNOB DATA ONLY WHEN KNOBSTATE UPDATE CAUSES INCREMENT!!!

 

    knobState3[0]=inputs[12]; //A

    knobState3[1]=inputs[13]; //B

    knobState2[0]=inputs[14]; //A

    knobState2[1]=inputs[15]; //B

 

    uint8_t increment3=0;

 

    uint8_t prev3=prevKnobState3.to_ulong();

    uint8_t curr3=knobState3.to_ulong();

 

    if (knobState3[0]!=prevKnobState3[0] && knobState3[1]!=prevKnobState3[1])

      increment3=direction3;

 

    else if((prev3==0 && curr3==1) || (prev3==3 && curr3==2))

      increment3=1;

 

    else if ((prev3==1 && curr3==0) || (prev3==2 && curr3==3))

      increment3=-1;

 

    else

      increment3=0;

   

 

    prevKnobState3[0]=knobState3[0];

    prevKnobState3[1]=knobState3[1];

 

///here

    uint8_t increment2=0;

 

    uint8_t prev2=prevKnobState2.to_ulong();

    uint8_t curr2=knobState2.to_ulong();

 

    if (knobState2[0]!=prevKnobState2[0] && knobState2[1]!=prevKnobState2[1])

      increment2=direction2;

 

    else if((prev2==0 && curr2==1) || (prev2==3 && curr2==2))

      increment2=1;

 

    else if ((prev2==1 && curr2==0) || (prev2==2 && curr2==3))

      increment2=-1;

 

    else

      increment2=0;

   

 

    prevKnobState2[0]=knobState2[0];

    prevKnobState2[1]=knobState2[1];

 

    xSemaphoreTake(sysState.mutex, portMAX_DELAY);

    sysState.inputs=std::move(inputs);

   

    sysState.knobPos3 += increment3;    //Does this block ISR from reading know while it's changing???

    sysState.knobPos3 = sysState.knobPos3 >= 250 ? 0 : sysState.knobPos3;

    sysState.knobPos3 = sysState.knobPos3 >= 8 ? 8 : sysState.knobPos3;

 

    direction3=increment3;

 

    sysState.knobPos2 += increment2;    //Does this block ISR from reading know while it's changing???

    sysState.knobPos2 = sysState.knobPos2 >= 250 ? 0 : sysState.knobPos2;

    sysState.knobPos2 = sysState.knobPos2 >= 10 ? 10 : sysState.knobPos2;

 

    direction2=increment2;

 

    //put octave determinant here: would scale step size accordingly

    TX_Message_Made[1] = sysState.knobPos2;

 

    TX_Message[0]=TX_Message_Made[0];

    TX_Message[1]=TX_Message_Made[1];

    TX_Message[2]=TX_Message_Made[2];

 

    xSemaphoreGive(sysState.mutex);

 

    /*int index = 0;

    while ( index < 13 && stepSizes[index] != currentKey.currentStepSize ) ++index;

    int txKeyValue = ( index == 13 ? -1 : index );

    TX_Message[0] = 'P';

    TX_Message[1] = '4'; //OCTAVE NUMBER IS RANDOM ATM

    TX_Message[2] = txKeyValue;*/

 

    if(send_tx && currentDevice.position != 0){

      //CAN_TX(0x123, TX_Message_Made);

      xQueueSend( msgOutQ, TX_Message_Made, portMAX_DELAY);

    }

 

    __atomic_store_n(&currentKey.currentStepSize, chosenKey.currentStepSize, __ATOMIC_RELAXED);

    currentKey.note=chosenKey.note;

 

  }

 

}

 

bool start_east;

bool start_west;

 

void displayUpdateTask(void * pvParameters){ //instead of holding program and thread until frame update time arrives, put thread to WAIT until initialization period occurs

 

  const TickType_t xFrequency = 50/portTICK_PERIOD_MS;   //denominator converts ms to clock ticks. setting the initiation period of task in ticks. Set to 50ms

  TickType_t xLastWakeTime = xTaskGetTickCount();

  //uint32_t ID;

  //uint8_t RX_Message[8]={0};

 

  while(1){

 

    vTaskDelayUntil(&xLastWakeTime, xFrequency);

 

    //Update display

    u8g2.clearBuffer();         // clear the internal memory

    u8g2.setFont(u8g2_font_ncenB08_tr); // choose a suitable font

    u8g2.drawStr(2,10,"Hello!");  // write something to the internal memory

   

 

    u8g2.setCursor(60,10);

    u8g2.print("  p");

    u8g2.print(currentDevice.position);

    u8g2.print("  ");

    u8g2.print(start_west);

    u8g2.print("  ");

    u8g2.print(start_east);

    //while (CAN_CheckRXLevel())

      //  CAN_RX(ID, RX_Message);

    u8g2.setCursor(35,30); //66,30

    //u8g2.print((char) TX_Message[0]);

    //u8g2.print(TX_Message[1]);

    //u8g2.print(TX_Message[2]);

    u8g2.print("  ");

 

    xSemaphoreTake(sysState.mutex, portMAX_DELAY);

 

    u8g2.print((char) sysState.RX_Message[0]);

    u8g2.print(sysState.RX_Message[1]);

    u8g2.print(sysState.RX_Message[2]);

    u8g2.print("   ");

    u8g2.print(sysState.inputs.to_ulong(), HEX);

    u8g2.print("   ");

    u8g2.print(sysState.knobPos3);

 

    u8g2.setCursor(3,30);

    u8g2.print(currentKey.note);

    u8g2.print(sysState.knobPos2);

 

    xSemaphoreGive(sysState.mutex);

 

    u8g2.sendBuffer();          // transfer internal memory to the display

 

    //Toggle LED

    digitalToggle(LED_BUILTIN);

 

  }

 

}




//wave phase making and ADC writing are interrupts. Key collection is thread. UI is low priority thread





void write_east(bool state){

 

  outBits[6]=state;  //east write works

  setRow(6);

 

}

 

void write_west(bool state){

 

  outBits[5]=state; //west write works

  setRow(5);

 

}

 

bool read_east(){

 

  setRow(6);

  return !digitalRead(C3_PIN);

 

}

 

bool read_west(){

 

  setRow(5);

  return !digitalRead(C3_PIN);

 

}

 

void handshake(){

 

/***HANDSHAKE***/




  //setup R5 and R6 DFFs high by clocking with row setting, reset row to 0 at the end

  write_west(1);

  write_east(1);

 

//TURN ON DELAY STILL PRESENT SO NO MATTER DELAY ADDED ONE WILL READ WHILE OTHER IS OFF

 

  uint32_t tim = millis();

  //READ FLAG VALUES AT START AND DISPLAY THEM FOR DEBUGGING

  while(millis()-tim <100){ //reed reading for one second   100 too low 500 good

    start_west = read_west();  //east west reading works, they both read 1 after delay

    start_east = read_east();  //changed order of call, did anything? NO IT DID NOT H

  }

 

  uint8_t Handshake_TX_Message[8] = {0};   //(1st byte is ID, second byte is position, 3rd byte tell if handshake is done, rest unused)    8 BIT FRAME SIZE IS FIXED, REDUCE IT TO TAILOR IN FUTURE?

  uint8_t Handshake_RX_Message[8] = {0};

  Handshake_RX_Message[1] = -1;

 

  //true if board got message when west was off, which allowed it to identify itself

  bool know_self = false;

 

  //true if handshake done signal is received from the rightmost board

  bool handshake_done = false;

 

  //saves the east and west flag values respectively

  bool east;

  bool west;

 

  //ISSUE WAS: THE PRESENCE OF CAN FILTER PREVENTED RECEPTION OF MESSAGES WITH DIFFERENT ID. COULDN'T GOT THE KEYMESSAGES AND HANDSHALE MESSAGES TO HAVE DIFFERENT IDS YET

  //CURRENT ISSUE: RX READS WEST AS ZERO BEFORE RX IS SENT BECAUSE RX DOESN'T SEE LEFT AS ONE!




  while(!handshake_done){

 

      //TURN ON DELAY CAN CAUSE TRANSMITTER TO READ RECEIVER AS ZERO AT START AND TURN ON TO BE RECEIVER

      //TO COUNTER PROPOGATION DELAYS OF ANY KIND, READ THE HANDSHAKE FLAGS MULTIPLE OF TIMES

      uint32_t tim = millis();

 

      while(millis()-tim <5){ //reed reading for one second   100 too low 500 good

          west = read_west();  //east west reading works, they both read 1 after delay

          east = read_east();  //changed order of call, did anything? NO IT DID NOT H

      }

 

      uint32_t ID;

      while (CAN_CheckRXLevel())

          CAN_RX(ID, Handshake_RX_Message);

 

      //handshake ID can't be too large or else CAN overflows and can't detect flag.

      //If received message is under handshake flag and isn't received when west is off, then it is a message from right components. Just add them to device list

      //Also if the device already knows itself, it would be set to receive messages always until it receives the handshake done signal. Set to ensure it receives handshake done

      if(ID == handshakeID && (west || know_self)){ //if got correct ID message

 

          //assume polling waits until getting message

 

          Device newDevice;

          newDevice.ID = Handshake_RX_Message[0];

 

          int i=0;

 

          while(i<device_list.size() && device_list[i].position < Handshake_RX_Message[1])

            i++;

 

          newDevice.position = Handshake_RX_Message[1];

          device_list.insert(device_list.begin() + i, newDevice);

 

          handshake_done=Handshake_RX_Message[2];

 

      }

 

      //if west went off and don't know self yet, the message received is from the left side that knows its position now

      if(!west && !know_self){ //First thing left side will see and send out. OTHERS DON'T SEND MESSAGES UNTIL LEFT STARTS.

      //If see west change then position at the most recent message than probably caused that change is the left neighbor. Now add self to list and transmit position to next element

         

              int i=0;

 

              while(i<device_list.size() && device_list[i].position < Handshake_RX_Message[1])

                  i++;

 

              currentDevice.position = Handshake_RX_Message[1]+1; //should save RX message of previous iteration

              device_list.insert(device_list.begin() + i, currentDevice);

             

              Handshake_TX_Message[0]=currentDevice.ID;

              Handshake_TX_Message[1]=currentDevice.position;

              Handshake_TX_Message[2]=!east; //if there's no east detected, send transmission to end communication

 

              handshake_done=!east;

 

              //write east to low so next board will know its neighbor

 

              //broadcast transmit message only once? enough?

              CAN_TX(handshakeID, Handshake_TX_Message);

 

              write_east(0); //Error happened because tx writes to east before rx reads transmitted message

 

              know_self=true;

 

         

 

      }

 

  }

 

 

  write_west(1);

  write_east(1);

 

/*

 

  SHOULD ADD DELAY TO ENSURE ALL RX MESSAGES ARE READ?

  AFTER GETTING MESSAGE, QUICKLY READ WEST INPUT TO SEE IF IT WAS FROM THE LEFT NEIGHBOR

 

  */


 /*

 

Each board will loop through this decision tree until their latest received message has a done flag (given when east=0)


  If west is zero:

    If broadcast not been done before:

      -The previous message must've also caused the west to go to zero so it is most likely the message from the left neighbot

      -Add self to device list with its position set to +1 of that on latest message (left neighbor)

      -Change east to zero to make right neightbor's west zero

      -Broadcast self position and ID to every board. If east input is zero then nothing on right so also send one as done flag on frame

      -enter poll state

 

    If broadcast been done before:

      -Poll for messages from right elements like the west is one case 

 

 If west is one:

    -Position not known yet so don't add self yet

    -Poll for received data then add element to device list (also record the done flag on the received data message buffer)


In the data list, we save structs of id and position. Position is there so that when adding elements, can increment index up to the point where received position is larger than

current position on the array. Then it will add element on right of that point

 

 */

 

}





void setup() {

  // put your setup code here, to run once:

 

//Initialise UART

  Serial.begin(9600);

  Serial.println("Hello World");






  //Set pin directions

  pinMode(RA0_PIN, OUTPUT);

  pinMode(RA1_PIN, OUTPUT);

  pinMode(RA2_PIN, OUTPUT);

  pinMode(REN_PIN, OUTPUT);

  pinMode(OUT_PIN, OUTPUT);

  pinMode(OUTL_PIN, OUTPUT);

  pinMode(OUTR_PIN, OUTPUT);

  pinMode(LED_BUILTIN, OUTPUT);

 

  pinMode(C0_PIN, INPUT);

  pinMode(C1_PIN, INPUT);

  pinMode(C2_PIN, INPUT);

  pinMode(C3_PIN, INPUT);

  pinMode(JOYX_PIN, INPUT);

  pinMode(JOYY_PIN, INPUT);

 

  CAN_Init(false); //set false to stop self loop where messages are for self only

  CAN_RegisterRX_ISR(CAN_RX_ISR); //links the RX ISR to CAN comm initiated. ISR called whenever program gets CAN message to its buffer

  CAN_RegisterTX_ISR(CAN_TX_ISR);

 

  //setCANFilter(0x123,0x7ff);

  setCANFilter();

  CAN_Start();

 

  //Initialise display

  setOutMuxBit(DRST_BIT, LOW);  //Assert display logic reset

  delayMicroseconds(2);

  setOutMuxBit(DRST_BIT, HIGH);  //Release display logic reset

  u8g2.begin();

  setOutMuxBit(DEN_BIT, HIGH);  //Enable display power supply




  handshake();

 

  //create mutex and link it to state field. The mutex is a flag object that turns other mutex.get calls in other call to wait statements when a task locks it

  sysState.mutex = xSemaphoreCreateMutex();

 

  //Create a countinng semaphore flag for TX buffer access. 3 means that the semaphore can be nonblocking for 3 calls then it blocks until ISR gives go. Because STM32 has 3 outboxes

  CAN_TX_Semaphore = xSemaphoreCreateCounting(3,3); //3 is also the maximum amount the semaphore count can increment to (below maximum amount of mailboxes)




  //0=receiver and player  1=transmitter

  if(currentDevice.position == 0){

 

      //create queue to transfer CAN received by ISR to the decoder task (number of items to store, size of item)

      //Increase queue size if decoder task needs larger initiation period. 8 is enough to store 1 CAN message

      msgInQ = xQueueCreate(36,8);

 

      TIM_TypeDef *Instance = TIM1;

      HardwareTimer *sampleTimer = new HardwareTimer(Instance);

      sampleTimer->setOverflow(22000, HERTZ_FORMAT);

      sampleTimer->attachInterrupt(sampleISR);

      sampleTimer->resume();

 

      TaskHandle_t scanKeysHandle = NULL;

      xTaskCreate(

      scanKeysTask,   /* Function that implements the task */

      "scanKeys",   /* Text name for the task */

      64,         /* Stack size in words, not bytes */

      NULL,     /* Parameter passed into the task */

      3,      /* Task priority */

      &scanKeysHandle );  /* Pointer to store the task handle */

 

      TaskHandle_t decodeHandle = NULL;

      xTaskCreate(

      decodeTask,    /* Function that implements the task */

      "decode",    /* Text name for the task */

      256,          /* Stack size in words, not bytes */

      NULL,     /* Parameter passed into the task */

      2,      /* Task priority */

      &decodeHandle ); /* Pointer to store the task handle */

 

      TaskHandle_t displayUpdateHandle = NULL;

      xTaskCreate(

      displayUpdateTask,    /* Function that implements the task */

      "displayUpdate",    /* Text name for the task */

      256,          /* Stack size in words, not bytes */

      NULL,     /* Parameter passed into the task */

      1,      /* Task priority */

      &displayUpdateHandle ); /* Pointer to store the task handle */

 

  }

 

  else{

 

      //create queue to transfer CAN received by ISR to the decoder task (number of items to store, size of item)

      //Increase queue size if decoder task needs larger initiation period. 8 is enough to store 1 CAN message

      msgOutQ = xQueueCreate(36,8);

 

      TaskHandle_t scanKeysHandle = NULL;

      xTaskCreate(

      scanKeysTask,   /* Function that implements the task */

      "scanKeys",   /* Text name for the task */

      64,         /* Stack size in words, not bytes */

      NULL,     /* Parameter passed into the task */

      3,      /* Task priority */

      &scanKeysHandle );  /* Pointer to store the task handle */

 

      TaskHandle_t canTXHandle = NULL;

      xTaskCreate(

      CAN_TX_Task,    /* Function that implements the task */

      "transmit",    /* Text name for the task */

      64,          /* Stack size in words, not bytes */

      NULL,     /* Parameter passed into the task */

      2,      /* Task priority */

      &canTXHandle ); /* Pointer to store the task handle */

 

      TaskHandle_t displayUpdateHandle = NULL;

      xTaskCreate(

      displayUpdateTask,    /* Function that implements the task */

      "displayUpdate",    /* Text name for the task */

      256,          /* Stack size in words, not bytes */

      NULL,     /* Parameter passed into the task */

      1,      /* Task priority */

      &displayUpdateHandle ); /* Pointer to store the task handle */

     

      }

 

      vTaskStartScheduler(); //Start running tasks

 

}





//EMPTY IN RTOS. CPU RUNS TASKS

 

void loop() {

 

  // put your main code here, to run repeatedly:

 

}





/*

 

CAN'T MUTEX IF INTERRUPT ACCESSES IT

 

CAN STATE ATOMIVITY IF TAKE ONLY 1 TICK. ATOMIC MEAN NO SWITCH UNTIL OPERATION IS DONE.

 

Mutex: If thread takes mutex, it locks the protected data mutex belongs to from other threads until released. Inheritance given based on priority

 

Semaphore: Signalling mechanism using integers. Thread wait() for signal()

 

CAN CHANGE MUTEX TO FINITE TIME BUT TO DO THAT WE NEED CHECK TO ENSURE MUTEX TAKING WAS SUCCESSFUL

 

MUTEX AND SEMAPHORE FOR THREAD, ATOMIC FR INTERRUPT

 

*/