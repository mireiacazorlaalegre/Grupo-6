// =====================================================================
//  SATÉLITE - Versión 2 (Grupo 6)
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
#include <DHT.h>
#include <PWMServo.h>               // CAMBIO: sustituye a Servo.h (no le afecta SoftwareSerial)

#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ----- Radar: dos HC-SR04 espalda con espalda sobre el servo -----
const int trig1 = 4;                // sensor 1: mira hacia 0-180º
const int echo1 = 5;
const int trig2 = 6;                // sensor 2: montado al revés, mira hacia 180-360º
const int echo2 = 7;
const int pinServo = 9;             // CAMBIO: PWMServo solo funciona en los pines 9 y 10 (el 10 es del SoftwareSerial)
PWMServo miServo;                   // CAMBIO: objeto de la nueva librería

const long timeoutEco = 12000;      // CAMBIO: espera máxima del eco (µs) -> unos 2 m, lo que muestra la gráfica

const int led1 = 12;
bool stateLed1 = LOW;
bool enviarDatos = false;           // empieza parado: arranca con la orden 4: (INICIAR)
bool enviarRadar = false;           // empieza parado: arranca con la orden 7:

SoftwareSerial mySerial(10, 11);

int angulo = 0;                     // ángulo actual del servo (0-180)
int paso = 1;                       // +1 = hacia 180, -1 = hacia 0 (grados por paso)
bool modoFijo = false;              // false = rastreo (barrido), true = orientación fija (orden 2:)

unsigned long nextMillis1;          // próximo envío de T/H
unsigned long nextMillis2;          // momento de apagar el LED
unsigned long nextTimeoutSensor;    // próximo aviso de fallo de sensor
unsigned long nextMillisLatido;     // próximo latido
unsigned long nextMillisRadar;      // próximo paso del radar

long interval1 = 3000;              // periodo T/H (ms), se puede cambiar desde tierra
const long interval2 = 200;         // LED encendido 0,2 s
const long interval3 = 5000;        // espera para declarar fallo de sensor: 5 s
const long intervalLatido = 2000;   // periodo del latido: 2 s
long intervalRadar = 30;            // ms entre grados (se cambia con la orden 8:)

bool esperandoTimeoutSensor = false;

// Media de temperatura en el satélite (5.2): cola circular con las 10 últimas
bool mediaEnSatelite = false;       // false = la calcula tierra; true = la calcula el satélite (orden 5:)
const int TAM_COLA = 10;
float cola[TAM_COLA];               // vector de tamaño fijo con las últimas temperaturas
int posCola = 0;                    // posición donde se escribirá la siguiente temperatura
int cuantosCola = 0;                // cuántas temperaturas hay de verdad (máximo TAM_COLA)

int fallosDist[3] = {0, 0, 0};      // lecturas seguidas sin respuesta de cada sensor (se usan [1] y [2])
const int maxFallosDist = 3;        // a partir de 3 seguidas se avisa a tierra

void setup() {
   mySerial.begin(9600);
   Serial.begin(9600);
   pinMode(led1, OUTPUT);
   mySerial.setTimeout(50);

   pinMode(trig1, OUTPUT);
   pinMode(echo1, INPUT);
   pinMode(trig2, OUTPUT);
   pinMode(echo2, INPUT);
   miServo.attach(pinServo);
   miServo.write(angulo);           // el servo empieza en 0º
   delay(500);                      // le da tiempo a llegar (solo una vez, en setup)
   miServo.detach();                // radar parado: el servo sin señal no tiembla

   nextMillis1 = millis() + interval1;
   nextMillisLatido = millis() + intervalLatido;
   nextMillisRadar = millis();
   dht.begin();
}

void loop() {
   // ----- LECTURA Y ENVÍO DE T/H -----
   if (enviarDatos && millis() >= nextMillis1) {
      float h = dht.readHumidity();
      float t = dht.readTemperature();

      if (isnan(h) || isnan(t)) {
         if (!esperandoTimeoutSensor) {      // primer fallo: empieza a contar
            esperandoTimeoutSensor = true;
            nextTimeoutSensor = millis() + interval3;
         }
      }
      else {
         esperandoTimeoutSensor = false;

         mySerial.print("1:");               // código 1 = datos T/H
         mySerial.print(t);
         mySerial.print(":");
         mySerial.println(h);                // queda "1:24.50:50.00"

         anadirCola(t);                      // la cola se rellena siempre (cuesta muy poco)
         if (mediaEnSatelite && cuantosCola == TAM_COLA) {
            mySerial.print("4:");            // código 4 = media calculada en el satélite
            mySerial.println(calcularMedia());
         }

         stateLed1 = HIGH;
         digitalWrite(led1, stateLed1);
         nextMillis2 = millis() + interval2;
      }
      nextMillis1 = millis() + interval1;
   }

   // ----- AVISO DE FALLO DE SENSOR -----
   if (enviarDatos && esperandoTimeoutSensor && millis() >= nextTimeoutSensor) {
      mySerial.println("3:");                // código 3 = fallo sensor
      Serial.println("Error: fallo sensor");
      nextTimeoutSensor = millis() + interval3;
   }

   // ----- RADAR -----
   if (enviarRadar && millis() >= nextMillisRadar) {
      if (modoFijo) {
         // Orientación fija: el servo no se mueve; mide siempre en el mismo ángulo,
         // tan a menudo como en el barrido (cada 10 pasos)
         medirYEnviar(1, angulo, trig1, echo1);          // sensor 1
         medirYEnviar(2, angulo + 180, trig2, echo2);    // sensor 2 (al revés)
         nextMillisRadar = millis() + intervalRadar * 10;
      }
      else {
         // Rastreo: avanza 1 grado cada intervalRadar y mide cada 10 grados
         if (angulo % 10 == 0) {                // solo mide en 0, 10, 20, ... 180
            medirYEnviar(1, angulo, trig1, echo1);          // sensor 1
            medirYEnviar(2, angulo + 180, trig2, echo2);    // sensor 2 (al revés)
         }

         angulo = angulo + paso;                // siguiente grado
         if (angulo >= 180) {                   // llega al final: da la vuelta
            angulo = 180;
            paso = -1;
         }
         if (angulo <= 0) {                     // llega al principio: da la vuelta
            angulo = 0;
            paso = 1;
         }
         miServo.write(angulo);                 // se mueve ahora; tiene intervalRadar ms para llegar

         nextMillisRadar = millis() + intervalRadar;
      }
   }

   // ----- LATIDO ----- (se envía siempre, aunque T/H esté parado)
   if (millis() >= nextMillisLatido) {
      mySerial.println("9:");                // código 9 = latido
      nextMillisLatido = millis() + intervalLatido;
   }

   // ----- RECEPCIÓN DE ÓRDENES -----
   if (mySerial.available()) {
      String orden = mySerial.readStringUntil('\n');   // lee un mensaje entero
      orden.trim();                                    // quita espacios, '\r' y '\n'
      Serial.println(orden);                           // para depurar

      int fin = orden.indexOf(':');                    // posición del primer ':'
      if (fin > 0) {                                   // ignora mensajes sin código
         int codigo = orden.substring(0, fin).toInt();

         if (codigo == 1) {                            // nuevo periodo T/H (segundos)
            long valor = orden.substring(fin + 1).toInt();
            if (valor >= 1 && valor <= 60) {           // toInt() da 0 si no es un número
               interval1 = valor * 1000;
               nextMillis1 = millis() + interval1;
            }
            else {
               Serial.println("Periodo no valido");
            }
         }
         else if (codigo == 3) {                       // parar T/H
            enviarDatos = false;
            esperandoTimeoutSensor = false;
         }
         else if (codigo == 4) {                       // reanudar T/H
            if (!enviarDatos) {                        // si ya estaba en marcha, no hace nada
               enviarDatos = true;
               nextMillis1 = millis();                 // envía enseguida
            }
         }
         else if (codigo == 6) {                       // parar radar
            if (enviarRadar) {                         // si ya estaba parado, no hace nada
               enviarRadar = false;
               miServo.detach();                       // sin señal: el servo se queda quieto y no tiembla
            }
         }
         else if (codigo == 7) {                       // reanudar radar
            if (!enviarRadar) {                        // si ya estaba en marcha, no hace nada
               enviarRadar = true;
               miServo.attach(pinServo);               // vuelve a darle señal al servo
               miServo.write(angulo);                  // sigue desde donde se quedó
               nextMillisRadar = millis() + 300;       // primer paso cuando el servo ya está colocado
            }
         }
         else if (codigo == 2) {                       // orientación fija del radar
            String texto = orden.substring(fin + 1);
            long grados = texto.toInt();
            bool esNumero = texto.length() > 0 && texto.charAt(0) >= '0' && texto.charAt(0) <= '9';
            if (esNumero && grados >= 0 && grados <= 350 && grados % 10 == 0) {
               modoFijo = true;
               if (grados <= 180) {
                  angulo = grados;                     // apunta el sensor 1
               }
               else {
                  angulo = grados - 180;               // apunta el sensor 2 (mira al revés)
               }
               if (enviarRadar) {
                  miServo.write(angulo);               // si el radar está parado, se colocará al reanudar
               }
               nextMillisRadar = millis() + 300;       // primera medida cuando el servo ya ha llegado
            }
            else {
               Serial.println("Orientacion no valida");
            }
         }
         else if (codigo == 9) {                       // modo rastreo: vuelve a barrer
            modoFijo = false;
         }
         else if (codigo == 5) {                       // dónde se calcula la media
            String texto = orden.substring(fin + 1);
            if (texto == "1") {
               mediaEnSatelite = true;                 // la calcula el satélite
            }
            else if (texto == "0") {
               mediaEnSatelite = false;                // la calcula tierra
            }
            else {
               Serial.println("Orden de media no valida");
            }
         }
         else if (codigo == 8) {                       // periodo del radar (ms por grado)
            long valor = orden.substring(fin + 1).toInt();
            if (valor >= 15 && valor <= 200) {         // menos de 15 ms: el servo no llega
               intervalRadar = valor;
            }
            else {
               Serial.println("Periodo radar no valido");
            }
         }
      }
   }

   // ----- APAGADO DEL LED -----
   if (stateLed1 && millis() >= nextMillis2) {
      stateLed1 = LOW;
      digitalWrite(led1, stateLed1);
   }
}

// ---------------------------------------------------------------------
// medirDistancia: hace una medida con un sensor HC-SR04
//   Parámetros: trig, echo -> pines del sensor
//   Devuelve:   distancia en cm,
//               0 si el sensor responde pero no hay objeto cerca (sin eco),
//              -1 si el sensor no responde (desconectado o roto)
// ---------------------------------------------------------------------
float medirDistancia(int trig, int echo) {
   digitalWrite(trig, LOW);
   delayMicroseconds(2);
   digitalWrite(trig, HIGH);
   delayMicroseconds(10);
   digitalWrite(trig, LOW);

   // 1. Un sensor que funciona pone echo en HIGH menos de 1 ms después del disparo
   unsigned long inicio = micros();
   while (digitalRead(echo) == LOW) {
      if (micros() - inicio > 3000) {
         return -1;                          // no responde: fallo del sensor
      }
   }

   // 2. Echo está en HIGH mientras el sonido va y vuelve
   unsigned long subida = micros();
   while (digitalRead(echo) == HIGH) {
      if (micros() - subida > timeoutEco) {
         return 0;                           // no vuelve el eco: no hay objeto cerca
      }
   }
   return (micros() - subida) * 0.0343 / 2;  // ida y vuelta -> dividir entre 2
}

// ---------------------------------------------------------------------
// anadirCola: guarda una temperatura en la cola circular. Cuando está
//   llena, la nueva sustituye a la más antigua.
//   Parámetro: valor -> la temperatura que se añade
//   No devuelve nada (cambia cola, posCola y cuantosCola)
// ---------------------------------------------------------------------
void anadirCola(float valor) {
   cola[posCola] = valor;
   posCola = posCola + 1;
   if (posCola == TAM_COLA) {               // final del vector: vuelve al principio
      posCola = 0;
   }
   if (cuantosCola < TAM_COLA) {
      cuantosCola = cuantosCola + 1;
   }
}

// ---------------------------------------------------------------------
// calcularMedia: media de las temperaturas que hay en la cola
//   No tiene parámetros
//   Devuelve: la media, o 0 si la cola está vacía
// ---------------------------------------------------------------------
float calcularMedia() {
   if (cuantosCola == 0) {
      return 0;
   }
   float suma = 0;
   for (int k = 0; k < cuantosCola; k++) {
      suma = suma + cola[k];
   }
   return suma / cuantosCola;
}

// ---------------------------------------------------------------------
// medirYEnviar: mide con un sensor y envía el resultado a tierra.
//   Si el sensor no responde 3 veces seguidas, envía "5:sensor".
//   Parámetros: sensor -> 1 o 2
//               ang    -> ángulo hacia el que mira el sensor
//               trig, echo -> pines del sensor
//   No devuelve nada
// ---------------------------------------------------------------------
void medirYEnviar(int sensor, int ang, int trig, int echo) {
   float d = medirDistancia(trig, echo);
   if (d < 0) {                                       // el sensor no ha respondido
      fallosDist[sensor] = fallosDist[sensor] + 1;
      if (fallosDist[sensor] >= maxFallosDist) {
         mySerial.print("5:");                        // código 5 = fallo sensor de distancia
         mySerial.println(sensor);
      }
      else {
         enviarDistancia(ang, 0);                     // fallo suelto: se envía como "sin eco"
      }
   }
   else {
      fallosDist[sensor] = 0;                         // responde: se reinicia la cuenta
      enviarDistancia(ang, d);
   }
}

// ---------------------------------------------------------------------
// enviarDistancia: envía a tierra el mensaje "2:angulo:distancia"
//   Parámetros: ang  -> ángulo en grados (0-360)
//               dist -> distancia en cm (0 = sin eco)
//   No devuelve nada
// ---------------------------------------------------------------------
void enviarDistancia(int ang, float dist) {
   mySerial.print("2:");
   mySerial.print(ang);
   mySerial.print(":");
   mySerial.println(dist);                   // queda "2:90:35.20"
}
