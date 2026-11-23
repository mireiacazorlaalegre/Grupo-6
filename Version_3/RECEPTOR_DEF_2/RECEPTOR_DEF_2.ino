// =====================================================================
//  PROTOCOLO DE APLICACIÓN  (formato "codigo:dato:dato|checksum", una línea por mensaje)
//  checksum: suma de los caracteres que hay antes del '|', truncada a un byte (0-255)
//
//  Satélite -> Tierra
//    1:temp:hum         datos de temperatura (ºC) y humedad (%)
//    2:angulo:dist      distancia (cm) medida en un ángulo (0-360º); 0 = sin eco
//    3:                 fallo del sensor de temperatura/humedad
//    4:media            media de las 10 últimas temperaturas (solo si se calcula en el satélite)
//    5:sensor           fallo del sensor de distancia 1 o 2 (no responde)
//    8:                 mensaje corrupto (el checksum no coincide)
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

#include <SoftwareSerial.h>                // comunicación con el satélite
#include <LiquidCrystal.h>                 // pantalla LCD

LiquidCrystal lcd(7, 6, 5, 4, 3, 2);   // RS, E, D4, D5, D6, D7
SoftwareSerial mySerial(10, 11);       // RX, TX

// ---------- LED ----------
const int led1 = 12;                   // parpadea al recibir T/H o fallo de sensor
bool stateLed1 = LOW;
const long interval2 = 200;            // LED encendido 0,2 s
unsigned long nextMillis2;             // momento de apagar el LED

// ---------- Fallo de conexión ---------- (gracias al latido siempre llega algo)
unsigned long ultimoMensaje = 0;       // momento del último mensaje válido
const long timeoutConexion = 6000;     // 6 s sin mensajes = 3 latidos perdidos
bool mostrandoFalloConexion = false;   // true = el LCD ya muestra el error

// ---------- Fallo de los sensores de distancia ----------
// mientras un sensor falla, el satélite manda "5:n" en cada medida; si en 2 s no llega ninguno, ya funciona
bool falloDist1 = false;
bool falloDist2 = false;
unsigned long ultimoFalloDist1 = 0;    // momento del último "5:1"
unsigned long ultimoFalloDist2 = 0;    // momento del último "5:2"
const long tiempoFalloDist = 2000;
String textoFila1 = "(^_^)";           // lo que hay ahora en la fila de abajo del LCD

void setup() {
   Serial.begin(9600);                 // con el PC
   mySerial.begin(9600);               // con el satélite
   enviarMensaje("3:");             // al arrancar tierra, el satélite deja de enviar T/H
   enviarMensaje("6:");             // y para el radar, hasta que se pulse INICIAR
   enviarMensaje("9:");             // y vuelve al modo rastreo, por si estaba en orientación fija
   enviarMensaje("5:0");            // y la media la vuelve a calcular tierra (como empieza Python)
   pinMode(led1, OUTPUT);
   Serial.setTimeout(50);              // readStringUntil espera como mucho 50 ms
   mySerial.setTimeout(50);

   delay(500);                         // espera a que el LCD tenga la alimentación estable
   lcd.begin(16, 2);                   // LCD de 16 columnas y 2 filas
   lcd.print("Pulse INICIAR:");
   lcd.setCursor(0, 1);                // segunda fila
   lcd.print("(^_^)");                 // solo caracteres que el LCD sabe mostrar
   ultimoMensaje = millis();           // empieza a contar desde ahora
}

void loop() {
   // ----- RECEPCIÓN DE MENSAJES DEL SATÉLITE -----
   if (mySerial.available()) {
      String data = mySerial.readStringUntil('\n');   // lee un mensaje entero
      data.trim();                                    // quita '\r' y '\n'

      if (data.length() > 0 && esMensajeValido(data)) {   // descarta mensajes estropeados
         // buscar el '|' del checksum
         int barra = -1;                                  // posición del '|' (-1 = no hay)
         for (int k = 0; k < data.length(); k++) {
            if (data.charAt(k) == '|') {
               barra = k;
            }
         }
         // comprobar checksum: si no coincide, el mensaje se ha estropeado
         bool mensajeOk = false;
         if (barra > 0) {
            String cuerpo = data.substring(0, barra);       // lo de antes del '|': "3:"
            int chk = data.substring(barra + 1).toInt();    // el número de después: 109
            if (calcularChecksum(cuerpo) == chk) {
               data = cuerpo;                               // a partir de aquí, el mensaje sin el checksum
               mensajeOk = true;
            }
         } 
         if (!mensajeOk) {
            data = "8:";
         }

         Serial.println(data);                        // reenvía TODO al PC (Python)
         ultimoMensaje = millis();                    // la conexión funciona

         if (mostrandoFalloConexion) {                // la conexión ha vuelto
            lcd.clear();
            lcd.print("Conexion OK");
            mostrandoFalloConexion = false;
            textoFila1 = "";                          // la fila de abajo ha quedado vacía
         }

         if (data == "5:1") {                         // fallo del sensor de distancia 1
            falloDist1 = true;
            ultimoFalloDist1 = millis();
         }
         if (data == "5:2") {                         // fallo del sensor de distancia 2
            falloDist2 = true;
            ultimoFalloDist2 = millis();
         }

         // solo T/H (1) y fallo de sensor (3) van al LCD y encienden el LED:
         // el radar (2) llega muy seguido y el latido (9) no aporta nada al usuario
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
         enviarMensaje(orden);                     // reenvia con checksum
      }
   }

   // ----- APAGADO DEL LED -----
   if (stateLed1 && millis() >= nextMillis2) {
      stateLed1 = LOW;
      digitalWrite(led1, stateLed1);
   }
}

// --- MOSTRAR EN LCD: escribe en la fila de arriba los datos de T/H o el fallo del sensor ---
void mostrarEnLCD(String data) {
   int sep = data.indexOf(':', 2);          // posición del segundo ':'

   if (data.startsWith("1:") && sep != -1) {     // datos T/H en la fila de arriba
      escribirFila(0, "T" + data.substring(2, sep) + "C H" + data.substring(sep + 1) + "%");   // "T24.50C H50.00%"
   }
   else if (data.startsWith("3:")) {             // fallo del sensor de T/H
      escribirFila(0, "Fallo sensor T/H");
   }
}

// --- ESCRIBIR FILA: escribe el texto y borra con espacios lo que sobraba de antes ---
void escribirFila(int fila, String texto) {
   lcd.setCursor(0, fila);                  // fila 0 = arriba, 1 = abajo
   lcd.print(texto);
   for (int k = texto.length(); k < 16; k++) {   // rellena hasta las 16 columnas
      lcd.print(' ');
   }
}

// --- FILA DEL RADAR: estado de los sensores de distancia; solo se reescribe si cambia (así no parpadea) ---
void actualizarFilaRadar() {
   if (mostrandoFalloConexion) {
      return;                                   // el error de conexión ocupa toda la pantalla
   }
   if (falloDist1 && millis() - ultimoFalloDist1 > tiempoFalloDist) {
      falloDist1 = false;                       // 2 s sin "5:1": el sensor 1 ya funciona
   }
   if (falloDist2 && millis() - ultimoFalloDist2 > tiempoFalloDist) {
      falloDist2 = false;                       // 2 s sin "5:2": el sensor 2 ya funciona
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

   if (texto != textoFila1) {                   // solo si ha cambiado
      escribirFila(1, texto);
      textoFila1 = texto;
   }
}

// --- MENSAJE VÁLIDO: solo puede tener dígitos, ':', '.', '-' o '|' ---
bool esMensajeValido(String data) {
   for (int k = 0; k < data.length(); k++) {
      char c = data.charAt(k);
      bool esDigito = (c >= '0' && c <= '9');
      if (!esDigito && c != ':' && c != '.' && c != '-' && c != '|') {
         return false;                       // carácter raro: mensaje estropeado
      }
   }
   return true;                              // todos los caracteres son válidos
}

// --- CHECKSUM: cuenta los carácteres del mensaje y devuelve la suma de sus códigos ---
int calcularChecksum(String mensaje) {
   int suma = 0;
   for (int k = 0; k < mensaje.length(); k++) {    // recorre todo el mensaje y suma
      suma = suma + mensaje.charAt(k);
   }
   suma = suma % 256;                              // truncar a byte
   return suma;
}

// --- ENVIAR MENSAJE: envia todo en un solo mensaje---
void enviarMensaje(String mensaje) {
   int checksum = calcularChecksum (mensaje);
   mySerial.print(mensaje);
   mySerial.print("|");
   mySerial.println(checksum);
}
