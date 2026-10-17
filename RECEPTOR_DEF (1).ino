#include <SoftwareSerial.h>              // Librería 
SoftwareSerial mySerial(10, 11);         // Puerto serie extra: RX en pin 10, TX en pin 11
const int led1 = 12;                     // Pin donde está conectado el LED
bool stateLed1 = LOW;                    // Estado del LED (apagado al inicio)
const long interval2 = 200;              // Tiempo que el LED permanece encendido: 0,2 s
unsigned long nextMillis2;               // Momento en que toca apagar el LED

void setup() {                         
   Serial.begin(9600);                   
   Serial.println("Empezamos la recepción"); // Mensaje de inicio en el monitor serie
   mySerial.begin(9600);                 
   pinMode(led1, OUTPUT);                // Configura el pin del LED como salida
   Serial.setTimeout(50);               // readString() espera solo 50 ms (en vez de 1 s)
   mySerial.setTimeout(50);   
}

void loop() {                            
   if (mySerial.available()) {           // ¿Ha llegado algún dato del otro Arduino?
      String data = mySerial.readString(); // Lo lee completo como texto
      Serial.print(data);                // Lo muestra en el monitor serie del PC
      mySerial.print("Gracias, recibido! "); // Responde al emisor confirmando la recepción
      stateLed1 = HIGH;                  // Marca el LED como encendido
      digitalWrite(led1, stateLed1);     // Enciende el LED físicamente
      nextMillis2 = millis() + interval2; // Programa apagarlo dentro de 0,2 s
   }
     if (Serial.available()) {            // ¿ha llegado algo de la interfaz gráfica (PC)?
      String orden = Serial.readString(); // lo lee como texto 
      mySerial.print(orden);            //lo reenvía tal cual al satélite

   if (stateLed1 && millis() >= nextMillis2) { // Si el LED está encendido y ya pasaron 0,2 s
      stateLed1 = LOW;                   // Marca el LED como apagado
      digitalWrite(led1, stateLed1);     // Apaga el LED físicamente
   }
}