#include <SoftwareSerial.h> 
#include <DHT.h> 

#define DHTPIN 2 
#define DHTTYPE DHT11 
DHT dht(DHTPIN, DHTTYPE); 

const int led1 = 12; 
bool stateLed1 = LOW; 
bool enviarDatos = true; 

SoftwareSerial mySerial(10, 11); 

unsigned long nextMillis1; 
unsigned long nextMillis2; 
unsigned long nextTimeoutSensor; 

const long interval1 = 3000; // Envío cada 3 s
const long interval2 = 200;  // LED encendido 0.2 s
const long interval3 = 5000; // Espera para declarar fallo de sensor: 5 s

bool esperandoTimeoutSensor = false; 

void setup() { 
   mySerial.begin(9600); 
   Serial.begin(9600); 
   pinMode(led1, OUTPUT); 
   mySerial.setTimeout(50); 
   
   nextMillis1 = millis() + interval1; 
   dht.begin(); 
}

void loop() { 
   float h = dht.readHumidity(); 
   float t = dht.readTemperature(); 

   //  LECTURA Y ENVÍO 
   if (millis() >= nextMillis1 && enviarDatos) { 
      if (isnan(h) || isnan(t)) {
         if (!esperandoTimeoutSensor) {
            esperandoTimeoutSensor = true;
            nextTimeoutSensor = millis() + interval3;
         }
      } 
      else { 
         esperandoTimeoutSensor = false;

         mySerial.print("T:"); 
         mySerial.print(t); 
         mySerial.print(":H:"); 
         mySerial.println(h); 

         stateLed1 = HIGH; 
         digitalWrite(led1, stateLed1); 
         nextMillis2 = millis() + interval2; 

         nextMillis1 = millis() + interval1; 
      } 
   } 

   //  ENVÍO DE FALLO DE SENSOR 
   if (esperandoTimeoutSensor && millis() >= nextTimeoutSensor) {
      mySerial.println("fallo sensor"); 
      Serial.println("Error: fallo sensor");
      nextTimeoutSensor = millis() + interval3; 
   }

   //  RECEPCIÓN DE ÓRDEN (Parar / Reanudar) 
   if (mySerial.available()) { 
      String data2 = mySerial.readString(); 
      Serial.print(data2); 

      if (data2 == "Parar") { 
         enviarDatos = false;
      } 
      else if (data2 == "Reanudar") { 
         enviarDatos = true;
      } 
   }

   // APAGADO DEL LED
   if (stateLed1 && millis() >= nextMillis2) { 
      stateLed1 = LOW; 
      digitalWrite(led1, stateLed1); 
   }
}