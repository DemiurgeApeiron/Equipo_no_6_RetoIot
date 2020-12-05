#include <LiquidCrystal.h>
#include <Wire.h>
#include <SoftwareSerial.h>//wifi
#include "MAX30105.h"
#include <hd44780.h>                       
#include <hd44780ioClass/hd44780_I2Cexp.h>

SoftwareSerial ESPserial(2, 3); //Wifi RX | TX
MAX30105 particleSensor;
hd44780_I2Cexp lcd;

const int LCD_COLS = 16;
const int LCD_ROWS = 2;

String dataToSend;
int HR;
long milis;
char data[100];
String command;
String response;
String mesage;
int contador = 0;
int usuario = 0;
int numUsuario = 5;
bool pass = true;
int userPort = A0;
int val = 0;

void setup() {
  int status;
  status = lcd.begin(LCD_COLS, LCD_ROWS);
  if(status) // non zero status means it was unsuccesful
  {
    // hd44780 has a fatalError() routine that blinks an led if possible
    // begin() failed so blink error code using the onboard LED if possible
    hd44780::fatalError(status); // does not return
  }
  Serial.begin(115200);
  dataToSend.reserve(100);
  mesage.reserve(50);
  
  HR=0;
  lcd.print("Inicializando");
  if (particleSensor.begin(Wire, I2C_SPEED_FAST) == false) //Use default I2C port, 400kHz speed
  {
    Serial.println("MAX30105 was not found. Please check wiring/power. ");
    while (1);
  }

    //iniciar wifi
  command.reserve(300);
  response.reserve(200);
  ESPserial.begin(115200);
  Serial.println("Setting up client mode");
  sendCommand("AT+CWMODE=1\r\n", 1000);
  delay(1000);
  /*sendCommand2("AT+CWDHCP_CUR=2,0\r\n", 2000, 1);
  delay(1000);*/
  sendCommand2("AT+CIPSTA_CUR=\"192.168.1.119\",\"192.168.1.254\",\"255.255.255.0\"\r\n", 4000, 1);
  delay(1000); 
  sendCommand2("AT+CWJAP=\"INFINITUM2175_2.4\",\"6182529399\"\r\n", 4000,1);
  delay(1500);
  sendCommand2("AT+CIPSTA_CUR=\"192.168.1.119\",\"192.168.1.254\",\"255.255.255.0\"\r\n", 4000, 2);
  delay(1000);
  sendCommand2("AT+CIPSTART=\"UDP\",\"192.168.1.110\",1337\r\n", 2000, 1);
  

  
  //iniciar SPO2
  
  byte ledBrightness = 70; //Options: 0=Off to 255=50mA
  byte sampleAverage = 4; //Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 2; //Options: 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
  int sampleRate = 400; //Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
  int pulseWidth = 69; //Options: 69, 118, 215, 411
  int adcRange = 16384; //Options: 2048, 4096, 8192, 16384

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange); //Configure sensor with these settings
  lcd.clear();
  delay(100);
  lcd.print("usuario: " + String(usuario));
  ESPserial.listen();
}

void loop() {
  val = analogRead(userPort);
  if(val > 1000){
    usuario++;
    usuario = usuario % numUsuario;
    delay(500);
    contador=0;
    delay(100);
    lcd.clear();
    delay(100);
    lcd.print("Usuario: " + String(usuario));
    delay(100);
    pass = true;
  }
  if(contador < 300 && pass){
    contador++;
    getSamples();
  }
  else{
    if(pass == true){
      udpServerBegin();
      Serial.println("udpB");
    }
    Serial.println(ESPserial.readString());
    while (ESPserial.available()){
      mesage =ESPserial.readString();
      Serial.println(mesage);
    }
    if(mesage != ""){
      lcd.clear();
      delay(100);
      lcd.print(mesage);
      delay(300);
      lcd.clear();
      contador = 0;
      delay(500);
    }
    contador = 0;
    pass = false;
  }
  
      
  }


void udpServerBegin(){
  //ESPserial.listen();
}
void getSamples(){
  //Check the sensor
  particleSensor.check();
  while (particleSensor.available()) {
      particleSensor.check(); 
      milis = millis();
      dataToSend = "IR: ";
      // read stored IR
      dataToSend += particleSensor.getFIFOIR();
      
      // read stored red
      dataToSend += ";red: ";
      dataToSend += particleSensor.getFIFORed();
      // read time
      dataToSend += ";ML: "; 
      dataToSend += milis;
      //user
      dataToSend += ";user: "; 
      dataToSend += usuario;
      //sincronisador
      dataToSend += ";count: "; 
      dataToSend += contador;
      
      //enviar por serial 
      //Serial.println(dataToSend);
      Serial.println(dataToSend);
      //enviar por wifi
      dataToSend+=";\r\n";
      command="AT+CIPSEND=";
      command+=dataToSend.length();
      command+="\r\n";
      sendCommand(command, 1);
      sendData(1);
      // read next set of samples
      particleSensor.nextSample();

    }
}
void sendData(const int timeout)
{
  while ( ESPserial.available() ) {
    Serial.write( ESPserial.read());
    //delay(10);
  }
  response = "";
  int dataSize = dataToSend.length();
  dataToSend.toCharArray(data,dataSize);
  ESPserial.write(data,dataSize); // 
  long int time = millis();
  while( (time+timeout) > millis())
  {
  while(ESPserial.available())
  {
  // The esp has data so display its output to the serial window
  char c = ESPserial.read(); // read the next character.
  response+=c;
  }
  }
  Serial.print(response);
  //return response;
}

void sendCommand(String command, const int timeout)
{
  while ( ESPserial.available() ) {
    Serial.write( ESPserial.read());
    //delay(0);
  }
  response="";
  ESPserial.print(command); // send the read character to the wifi
  long int time = millis();
  while( (time+timeout) > millis())
  {
  while(ESPserial.available())
  {
  // The esp has data so display its output to the serial window
  char c = ESPserial.read(); // read the next character.
  response+=c;
  }
  }
  Serial.print(response);
  //return response;
} 
void sendCommand2(String command, const int timeout, int times)
{
  response="";
  ESPserial.print(command); // send the read character to the wifi
  int i=0;
  while(i<times){
    long int time = millis();
    while( (time+timeout) > millis())
    {
    while(ESPserial.available())
    {
    // The esp has data so display its output to the serial window
    char c = ESPserial.read(); // read the next character.
    response+=c;
    }
    }
    Serial.print(response);
    i+=1;
  }

  //return response;
} 
