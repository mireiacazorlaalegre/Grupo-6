// Test unitario del servo SG90 (Grupo 6 - V2)
// Hace un barrido de 0 a 180 grados y vuelta, de 10 en 10,
// y escribe el ángulo en el Monitor Serie a 9600.
// En el test se usa la librería Servo normal: aquí no hay SoftwareSerial
// que interfiera (en el programa del satélite se usa PWMServo).

#include <Servo.h>

const int pinServo = 9;        // el mismo pin que en el satélite
Servo miServo;

void setup() {
   Serial.begin(9600);
   miServo.attach(pinServo);
}

void loop() {
   for (int angulo = 0; angulo <= 180; angulo = angulo + 10) {     // ida
      miServo.write(angulo);
      Serial.print("Angulo: ");
      Serial.println(angulo);
      delay(300);
   }
   for (int angulo = 180; angulo >= 0; angulo = angulo - 10) {     // vuelta
      miServo.write(angulo);
      Serial.print("Angulo: ");
      Serial.println(angulo);
      delay(300);
   }
}
