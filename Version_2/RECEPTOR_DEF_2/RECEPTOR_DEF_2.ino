// =====================================================================
//  ESTACIÓN DE TIERRA (Arduino) - Versión 2 (Grupo 6)
//  - Recibe los mensajes del satélite (mySerial), los reenvía al PC
//    (Serial) y muestra el estado en el LCD.
//  - Reenvía al satélite las órdenes que llegan del PC.
// =====================================================================
//  PROTOCOLO DE APLICACIÓN  (formato "codigo:dato:dato", una línea por mensaje)
//
//  Satélite -> Tierra
//    1:temp:hum         datos de temperatura (ºC) y humedad (%)
//    2:angulo:dist      distancia (cm) medida en un ángulo (0-360º); 0 = sin eco
//    3:                 fallo del sensor de temperatura/humedad
//    4:media            media de las 10 últimas temperaturas (solo si se calcula en el satélite)
//    5:sensor           fallo del sensor de distancia 1 o 2 (no responde)
//    9:                 latido (cada 2 s, siempre): la conexión sigue viva
//
//  Tierra -> Satélite
//    1:segundos         nuevo periodo de envío de T/H (1-60 s)
//    2:grados           orientación fija del radar (0-350º, múltiplo de 10)
//    3:                 parar envío de T/H
//    4:                 reanudar envío de T/H
//    6:                 parar radar
//    7:                 reanudar radar
//    8:milisegundos     nuevo periodo del radar (15-200 ms por grado)
//    9:                 modo rastreo: el radar vuelve a barrer (no confundir con el latido, que va al revés)
//    5:1 / 5:0          la media la calcula el satélite (1) o tierra (0)
// =====================================================================

#include <SoftwareSerial.h>
#include <LiquidCrystal.h>

LiquidCrystal lcd(7, 6, 5, 4, 3, 2);   // RS, E, D4, D5, D6, D7
SoftwareSerial mySerial(10, 11);       // RX, TX

const int led1 = 12;
bool stateLed1 = LOW;
const long interval2 = 200;            // LED encendido 0,2 s
unsigned long nextMillis2;

// Detección de fallo de conexión (gracias al latido siempre llega algo)
unsigned long ultimoMensaje = 0;
const long timeoutConexion = 6000;     // 6 s sin mensajes = 3 latidos perdidos
bool mostrandoFalloConexion = false;   // true = el LCD ya muestra el error

// Fallo de los sensores de distancia. Mientras un sensor falla, el satélite
// manda "5:n" en cada medida; si en 2 s no llega ninguno, ya funciona.
bool falloDist1 = false;
bool falloDist2 = false;
unsigned long ultimoFalloDist1 = 0;
unsigned long ultimoFalloDist2 = 0;
const long tiempoFalloDist = 2000;
String textoFila1 = "(^_^)";           // lo que hay ahora en la fila de abajo del LCD

void setup() {
   Serial.begin(9600);
   mySerial.begin(9600);
   mySerial.println("3:");             // al arrancar tierra, el satélite deja de enviar T/H
   mySerial.println("6:");             // y para el radar, hasta que se pulse INICIAR
   mySerial.println("9:");             // y vuelve al modo rastreo, por si estaba en orientación fija
   mySerial.println("5:0");            // y la media la vuelve a calcular tierra (como empieza Python)
   pinMode(led1, OUTPUT);
   Serial.setTimeout(50);
   mySerial.setTimeout(50);

   delay(500);                         // espera a que el LCD tenga la alimentación estable
   lcd.begin(16, 2);
   lcd.print("Pulse INICIAR:");
   lcd.setCursor(0, 1);
   lcd.print("(^_^)");                 // solo caracteres que el LCD sabe mostrar
   ultimoMensaje = millis();
}

void loop() {
   // ----- RECEPCIÓN DE MENSAJES DEL SATÉLITE -----
   if (mySerial.available()) {
      String data = mySerial.readStringUntil('\n');   // lee un mensaje entero
      data.trim();                                    // quita '\r' y '\n'

      if (data.length() > 0 && esMensajeValido(data)) {   // descarta mensajes estropeados
         Serial.println(data);                        // reenvía TODO al PC (Python)
         ultimoMensaje = millis();                    // la conexión funciona

         if (mostrandoFalloConexion) {                // la conexión ha vuelto
            lcd.clear();
            lcd.print("Conexion OK");
            mostrandoFalloConexion = false;
            textoFila1 = "";                          // la fila de abajo ha quedado vacía
         }

         // Solo T/H (1) y fallo de sensor (3) van al LCD y encienden el LED.
         // El radar (2) llega muy seguido y el latido (9) no aporta nada al usuario.
         if (data == "5:1") {                         // fallo del sensor de distancia 1
            falloDist1 = true;
            ultimoFalloDist1 = millis();
         }
         if (data == "5:2") {                         // fallo del sensor de distancia 2
            falloDist2 = true;
            ultimoFalloDist2 = millis();
         }

         if (data.startsWith("1:") || data.startsWith("3:")) {
            stateLed1 = HIGH;
            digitalWrite(led1, stateLed1);
            nextMillis2 = millis() + interval2;
            mostrarEnLCD(data);
         }
      }
   }

   // ----- FALLO DE CONEXIÓN ----- (solo se escribe una vez)
   if (!mostrandoFalloConexion && millis() - ultimoMensaje >= timeoutConexion) {
      lcd.clear();
      lcd.print("ERROR:");
      lcd.setCursor(0, 1);
      lcd.print("Fallo conexion");
      mostrandoFalloConexion = true;
   }

   // ----- FILA DE ABAJO: ESTADO DE LOS SENSORES DE DISTANCIA -----
   actualizarFilaRadar();

   // ----- ÓRDENES DEL PC HACIA EL SATÉLITE -----
   if (Serial.available()) {
      String orden = Serial.readStringUntil('\n');    // no espera los 50 ms si llega el '\n'
      orden.trim();
      if (orden.length() > 0) {
         mySerial.println(orden);                     // reenvía la orden con su fin de línea
      }
   }

   // ----- APAGADO DEL LED -----
   if (stateLed1 && millis() >= nextMillis2) {
      stateLed1 = LOW;
      digitalWrite(led1, stateLed1);
   }
}

// ---------------------------------------------------------------------
// mostrarEnLCD: muestra en el LCD un mensaje de T/H o de fallo de sensor
//   Parámetro: data -> "1:temp:hum" o "3:" (sin '\r\n')
//   No devuelve nada
// ---------------------------------------------------------------------
void mostrarEnLCD(String data) {
   int sep = data.indexOf(':', 2);          // posición del segundo ':'

   if (data.startsWith("1:") && sep != -1) {     // datos T/H en la fila de arriba
      escribirFila(0, "T" + data.substring(2, sep) + "C H" + data.substring(sep + 1) + "%");   // "T24.50C H50.00%"
   }
   else if (data.startsWith("3:")) {             // fallo del sensor de T/H
      escribirFila(0, "Fallo sensor T/H");
   }
}

// ---------------------------------------------------------------------
// escribirFila: escribe un texto en una fila del LCD y borra lo que
//   sobraba de antes (rellena con espacios hasta las 16 columnas).
//   Parámetros: fila  -> 0 (arriba) o 1 (abajo)
//               texto -> lo que se escribe (máximo 16 caracteres)
//   No devuelve nada
// ---------------------------------------------------------------------
void escribirFila(int fila, String texto) {
   lcd.setCursor(0, fila);
   lcd.print(texto);
   for (int k = texto.length(); k < 16; k++) {
      lcd.print(' ');
   }
}

// ---------------------------------------------------------------------
// actualizarFilaRadar: decide qué poner en la fila de abajo según el
//   estado de los sensores de distancia y solo la reescribe si cambia
//   (así no parpadea).
//   No tiene parámetros ni devuelve nada
// ---------------------------------------------------------------------
void actualizarFilaRadar() {
   if (mostrandoFalloConexion) {
      return;                                   // el error de conexión ocupa toda la pantalla
   }
   if (falloDist1 && millis() - ultimoFalloDist1 > tiempoFalloDist) {
      falloDist1 = false;                       // 2 s sin "5:1": el sensor 1 ya funciona
   }
   if (falloDist2 && millis() - ultimoFalloDist2 > tiempoFalloDist) {
      falloDist2 = false;
   }

   String texto = textoFila1;                   // por defecto, se deja como está
   if (falloDist1 && falloDist2) {
      texto = "Fallo dist 1 y 2";
   }
   else if (falloDist1) {
      texto = "Fallo dist. 1";
   }
   else if (falloDist2) {
      texto = "Fallo dist. 2";
   }
   else if (textoFila1.startsWith("Fallo")) {
      texto = "Radar OK";                       // había un fallo y ya se ha arreglado
   }

   if (texto != textoFila1) {
      escribirFila(1, texto);
      textoFila1 = texto;
   }
}

// ---------------------------------------------------------------------
// esMensajeValido: comprueba que el mensaje solo tiene caracteres del protocolo
//   Parámetro: data -> mensaje recibido (ya sin '\r\n')
//   Devuelve:  true si todos los caracteres son dígitos, ':', '.' o '-'
// ---------------------------------------------------------------------
bool esMensajeValido(String data) {
   for (int k = 0; k < data.length(); k++) {
      char c = data.charAt(k);
      bool esDigito = (c >= '0' && c <= '9');
      if (!esDigito && c != ':' && c != '.' && c != '-') {
         return false;                       // carácter raro: mensaje estropeado
      }
   }
   return true;                              // todos los caracteres son válidos
}
