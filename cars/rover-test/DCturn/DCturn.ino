#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "utility/Adafruit_MS_PWMServoDriver.h"

//Creating motor shield object with default I2C address
//Can use different I2C address- say for stacking by putting (0x61) inside ()
Adafruit_MotorShield AFMS = Adafruit_MotorShield(); 

//Select port (M1, M2, M3, M4- (1) means M1)
//Can 3 other motors to control
Adafruit_DCMotor *leftMotor = AFMS.getMotor(1);
Adafruit_DCMotor *rightMotor = AFMS.getMotor(2);
Adafruit_DCMotor *LbackMotor = AFMS.getMotor(3);
Adafruit_DCMotor *RbackMotor = AFMS.getMotor(4);

//Setup code will run once
void setup() {
  
  AFMS.begin(); 
  //sets up frequency, default is 1.6 kHz, to change put (1000)

}

// put your main code here, to run repeatedly:
void loop() {

  //Set speed 0 (off) - 255 (max)
  leftMotor->setSpeed(150);
  rightMotor->setSpeed(150);
  LbackMotor->setSpeed(150);
  RbackMotor->setSpeed(150);

  //Commands are FORWARD, BACKWARD, RELEASE (shuts off motor)
  leftMotor->run(FORWARD);
  rightMotor->run(FORWARD);
  LbackMotor->run(FORWARD);
  RbackMotor->run(FORWARD); 
  delay(2000);

  //Attempting turn to the left 
/* Loop can only make 45 degree turn
    for (int i=0; i<250; i++) {
    rightMotor->setSpeed(i); 
    RbackMotor->setSpeed(i);
    delay(10);}
*/
  
  rightMotor->setSpeed(250); 
  RbackMotor->setSpeed(250);
  rightMotor->run(FORWARD);
  RbackMotor->run(FORWARD);
  delay (3500); //doesn't turn quite as straight, might have to do with time delay

  
  

}
