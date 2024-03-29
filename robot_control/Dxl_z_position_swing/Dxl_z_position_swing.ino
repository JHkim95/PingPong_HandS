#include <stdio.h>
#include <math.h>

/* Serial device defines for dxl bus */
#define DXL_BUS_SERIAL1 1  //Dynamixel on Serial1(USART1)  <-OpenCM9.04
#define DXL_BUS_SERIAL2 2  //Dynamixel on Serial2(USART2)  <-LN101,BT210
#define DXL_BUS_SERIAL3 3  //Dynamixel on Serial3(USART3)  <-OpenCM 485EXP


/* Control table defines */
#define GOAL_POSITION 30
#define PRESENT_POSITION 36
#define R1 5
#define R2 4
#define low_pwm 240
#define high_pwm 800
#define middle_pwm 512
#define arm_length 27 //cm

int z=0;
int pwm=0;
int present=0;
char data[3];
int p_data[2];

int get_pwm(int z)
{
  int pwm;
  float theta;
  int distance;
  distance = z-arm_length;
  SerialUSB.println(distance);
  theta = asin(distance/arm_length);
  SerialUSB.println(theta);
  pwm = map(theta, -M_PI/2, M_PI/2, low_pwm, high_pwm); 
  return pwm;
}

Dynamixel Dxl(DXL_BUS_SERIAL3);

void setup()
{  
  // Dynamixel 2.0 Baudrate -> 0: 9600, 1: 57600, 2: 115200, 3: 1Mbps 
  Dxl.begin(3);
  Dxl.jointMode(R1); //jointMode() is to use position mode
  SerialUSB.begin();

}

void loop()
{
  int i;
  if(SerialUSB.available())
  {
    for(i=0; i<2; i++)
    {
      data[i] = SerialUSB.read();
      p_data[i] = data[i] - '0';
    }

    z = p_data[0] * 10 + p_data[1]; //z_position
    SerialUSB.println(z);

    pwm = get_pwm(z);
    Dxl.writeWord(R1, GOAL_POSITION, pwm); 
    
    
    Dxl.writeWord(3, GOAL_POSITION, 512);

    //swing
      
    Dxl.writeWord(R2, GOAL_POSITION, 650);
    delay(500);  
    Dxl.writeWord(R2, GOAL_POSITION, 400);
    delay(500);  
    Dxl.writeWord(4, GOAL_POSITION, 512);
    
   }    
}


 
