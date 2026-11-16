#include <SoftwareSerial.h>
#include <LiquidCrystal.h> //

//  Definición de pines para la pantalla
LiquidCrystal lcd(7, 6, 5, 4, 3, 2); 

SoftwareSerial mySerial(10, 11);
const int led1 = 12;
bool stateLed1 = LOW;
const long interval2 = 200;
unsigned long nextMillis2;
// Detección de fallo de conexión 
unsigned long ultimoMensaje = 0;
const long timeoutConexion = 6000; // Si en 6s no recibe nada, salta error

void setup() { 
   Serial.begin(9600); 
   Serial.println("Empezamos la recepción"); 
   mySerial.begin(9600); 
   pinMode(led1, OUTPUT); 
   Serial.setTimeout(50); 
   mySerial.setTimeout(50); 

   lcd.begin(16, 2); //inicia  pantalla
   ultimoMensaje = millis(); // Inicializa el contador
}

void loop() { 
   if (mySerial.available()) { 
      String data = mySerial.readString(); 
      Serial.print(data); 
      mySerial.println("Gracias, recibido! "); 
      ultimoMensaje = millis(); // Reset de tiempo: la conexión funciona

      stateLed1 = HIGH; 
      digitalWrite(led1, stateLed1); 
      nextMillis2 = millis() + interval2; 

      //  Si el texto recibido contiene "fallo", lo muestra en el LCD
      if (data.indexOf("fallo sensor") != -1) {
         lcd.clear();
         lcd.print("ERROR:");
         lcd.setCursor(0, 1); // Pasa a la segunda línea
         lcd.print("Fallo sensor");
      }
      else if (data.indexOf("fallo conexion") != -1) {
         lcd.clear();
         lcd.print("ERROR:");
         lcd.setCursor(0, 1); // Pasa a la segunda línea
         lcd.print("Fallo conexion");
      }
      else {
         // **Se ejecuta cuando los datos llegan con normalidad
         lcd.clear();
         lcd.setCursor(0, 0);
         lcd.print("Recibiendo datos");
         lcd.setCursor(0, 1);
         lcd.print(data.substring(0, 16)); // Muestra el texto recibido
      }
  
   }
    if (millis() - ultimoMensaje >= timeoutConexion) {  //Fallo de conexion
      lcd.clear();
      lcd.print("ERROR:");
      lcd.setCursor(0, 1);
      lcd.print("Fallo conexion");
   }

   if (Serial.available()) { 
      String orden = Serial.readString(); 
      mySerial.print(orden); 
   }

   if (stateLed1 && millis() >= nextMillis2) { 
      stateLed1 = LOW; 
      digitalWrite(led1, stateLed1); 
   }
}