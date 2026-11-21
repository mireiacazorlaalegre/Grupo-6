// Test unitario del radar (Grupo 6 - V2): dos HC-SR04 espalda con espalda
// sobre el servo. El sensor 1 cubre 0-180º y el sensor 2 (mira al revés)
// cubre 180-360º. Escribe "angulo:distancia" en el Monitor Serie a 9600.

#include <Servo.h>

const int trig1 = 4;   // sensor 1
const int echo1 = 5;
const int trig2 = 6;   // sensor 2 (montado al revés)
const int echo2 = 7;
const int pinServo = 9;        // el mismo pin que en el satélite
Servo miServo;

void setup() {
   Serial.begin(9600);
   pinMode(trig1, OUTPUT);
   pinMode(echo1, INPUT);
   pinMode(trig2, OUTPUT);
   pinMode(echo2, INPUT);
   miServo.attach(pinServo);
}

// medirDistancia: hace una medida con un sensor HC-SR04
//   Parámetros: trig, echo -> pines del sensor
//   Devuelve:   distancia en cm, o 0 si no llega eco
float medirDistancia(int trig, int echo) {
   digitalWrite(trig, LOW);
   delayMicroseconds(2);
   digitalWrite(trig, HIGH);
   delayMicroseconds(10);
   digitalWrite(trig, LOW);
   long duracion = pulseIn(echo, HIGH, 30000);
   return duracion * 0.0343 / 2;
}

void loop() {
   for (int angulo = 0; angulo <= 180; angulo = angulo + 10) {
      miServo.write(angulo);
      delay(300);                                // espera a que el servo llegue

      Serial.print(angulo);                      // sensor 1: su ángulo es el del servo
      Serial.print(":");
      Serial.println(medirDistancia(trig1, echo1));

      Serial.print(angulo + 180);                // sensor 2: mira al revés -> +180
      Serial.print(":");
      Serial.println(medirDistancia(trig2, echo2));
   }
}
