#include <SoftwareSerial.h>   // Librería 
#include <DHT.h>              // Librería para el sensor de temperatura/humedad DHT
#define DHTPIN 2              // Pin digital donde está conectado el sensor
#define DHTTYPE DHT11         // Modelo de sensor utilizado
DHT dht(DHTPIN, DHTTYPE);     // Crea el objeto del sensor con ese pin y modelo
const int led1 = 12;          // Pin donde está conectado el LED
bool stateLed1 = LOW;         // Estado del LED (apagado al inicio)
bool enviarDatos = true;      // true = enviar datos, false = en pausa
SoftwareSerial mySerial(10, 11); // Puerto serie extra: RX en pin 10, TX en pin 11
unsigned long nextMillis1;       // Momento en que toca el próximo envío de datos
unsigned long nextMillis2;       // Momento en que toca apagar el LED
const long interval1 = 3000; // Tiempo entre envíos: 3 s
const long interval2 = 200;  // Tiempo que el LED permanece encendido: 0,2 s

void setup() {                        
   mySerial.begin(9600);               // Inicia el puerto serie por software a 9600 baudios
   mySerial.println("Empezamos");      // Envía un mensaje de inicio por ese puerto
   pinMode(led1, OUTPUT);              // Configura el pin del LED como salida
   Serial.begin(9600);                 
   Serial.println("Empezamos");        // Mensaje de inicio en el monitor serie
   mySerial.setTimeout(50);           //readString() espera solo 50 ms
   nextMillis1 = millis() + interval1; // Programa el primer envío dentro de 3 s
   
   dht.begin(); // Inicialización del sensor
}

void loop() {                         
     float h = dht.readHumidity();     // Lee la humedad del sensor
   float t = dht.readTemperature();    // Lee la temperatura del sensor (°C)
   if (millis() >= nextMillis1 && enviarDatos) {   //Solo envía si enviarDatos es true
      if (isnan(h) || isnan(t))   // ¿Alguna lectura ha fallado (no es un número)?
         Serial.println("Error al leer el sensor DHT11");    // Print error
    else {                             // Si las lecturas son correctas:Envía los datos
      mySerial.print("T:");            
      mySerial.print(t);               
      mySerial.print(":H:");           
      mySerial.print(h);               
     
      

                

      stateLed1 = HIGH;                // LED encendido
      digitalWrite(led1, stateLed1);   // LED encendido físicamente
      nextMillis2 = millis() + interval2;   // Programa apagarlo dentro de 0,2 s

      nextMillis1 = millis() + interval1;   // Programa el siguiente envío dentro de 3 s
   }                                   
   }                                   

   if (stateLed1 && millis() >= nextMillis2) {  // Si el LED está encendido y ya pasaron 0,2 s
      stateLed1 = LOW;                          // LED apagado
      digitalWrite(led1, stateLed1);            // ED apagado físicamente
   }

   if (mySerial.available()) {         // ¿Ha llegado algún dato por el puerto serie software?
      String data2 = mySerial.readString(); // Lo lee completo como texto
      Serial.print(data2);             // Lo reenvía al monitor serie del PC
      if (data2 == "Parar") {                    // Orden de pausa
         enviarDatos = false;
      }
      else if (data2 == "Reanudar") {            // Orden de reanudar
         enviarDatos = true;
      }
      else {                                     // Cualquier otro mensaje (p. ej. "Gracias, recibido!")
         Serial.print(data2);                    // se muestra en el monitor serie
      }
   }
}