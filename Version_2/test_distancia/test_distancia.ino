// Test unitario de los dos sensores de distancia HC-SR04 (Grupo 6 - V2)
// Mide con los dos cada 0,5 s y avisa si alguno parece desconectado
// (5 lecturas seguidas sin eco). Resultado en el Monitor Serie a 9600.

const int trig1 = 4;   // sensor 1
const int echo1 = 5;
const int trig2 = 6;   // sensor 2
const int echo2 = 7;
int sinEco1 = 0;       // lecturas seguidas sin eco de cada sensor
int sinEco2 = 0;

void setup() {
   Serial.begin(9600);
   pinMode(trig1, OUTPUT);
   pinMode(echo1, INPUT);
   pinMode(trig2, OUTPUT);
   pinMode(echo2, INPUT);
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
   return duracion * 0.0343 / 2;          // ida y vuelta -> dividir entre 2
}

void loop() {
   float d1 = medirDistancia(trig1, echo1);
   float d2 = medirDistancia(trig2, echo2);

   Serial.print("Sensor 1: ");
   if (d1 == 0) { sinEco1 = sinEco1 + 1; Serial.print("sin eco"); }
   else         { sinEco1 = 0;           Serial.print(d1); Serial.print(" cm"); }

   Serial.print("   Sensor 2: ");
   if (d2 == 0) { sinEco2 = sinEco2 + 1; Serial.println("sin eco"); }
   else         { sinEco2 = 0;           Serial.print(d2); Serial.println(" cm"); }

   if (sinEco1 >= 5) Serial.println("ERROR: posible fallo del sensor 1");
   if (sinEco2 >= 5) Serial.println("ERROR: posible fallo del sensor 2");
   delay(500);
}
