#include <SoftwareSerial.h>
int i;
SoftwareSerial mySerial(10, 11); // RX, TX 
void setup() {
   mySerial.begin(9600);
   mySerial.println("Empezamos");
   i=1;
   Serial.begin(9600);
   Serial.println("Empezamos");
  
}
void loop() {
   delay (3000);
   mySerial.print("Envío: ");
   mySerial.println(i);
   i=i+1;
   Serial.begin(9600);
   Serial.print("Envío: ");
   Serial.println(i);
     if (mySerial.available()) {
      String data2 = mySerial.readString();
      Serial.print(data2);

}
}
