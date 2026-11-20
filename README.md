# Sistema Satelital — Grupo 6

Proyecto de Ciencias de la Computación

## Equipo

| Miembro | Parte principal |
| --- | --- |
| Ane Badiola García | Interfaz visual, sensor HC-SR04 y servo |
| Jan | Montaje Arduino, protocolo de aplicación |
| Mireia Cazorla Alegre | GitHub, media de temperatura, cola circular |

## Descripción del sistema

El sistema simula un satélite que se comunica con una estación de tierra:

- **Satélite (Arduino):** mide temperatura y humedad con un DHT11 y, desde la versión 2, vigila los objetos cercanos con un radar: dos sensores de ultrasonidos HC-SR04 montados espalda con espalda sobre un servo, de forma que entre los dos cubren 360°.
- **Estación de tierra (Arduino + LCD 16x2):** recibe los mensajes del satélite, muestra el estado en el LCD y los reenvía al PC. También reenvía al satélite las órdenes que llegan del PC.
- **Interfaz gráfica:** muestra los datos en gráficas, gestiona las alarmas y permite al usuario enviar órdenes al satélite.

## Versiones

| Versión | Qué incluye | Vídeo |
| --- | --- | --- |
| 1 | Envío de temperatura y humedad, LCD en tierra, gráfica en tiempo real, órdenes de parar/reanudar y alarmas (fallo de sensor y de conexión) | [Ver vídeo V1](https://drive.google.com/file/d/1DW6Z_8IgxookbccRerrv29M3-voX5HDI/view?usp=sharing) |
| 2 | Radar de 360° con servo + 2 HC-SR04, media de las 10 últimas temperaturas (cola circular) en tierra o en el satélite, alarma de temperatura media, cambio de periodos y orientación del radar desde la interfaz | (pendiente) |
| 3 | (pendiente) | — |
| 4 | (pendiente) | — |

## Cómo ponerlo en marcha

**Librerías de Arduino:** DHT sensor library, PWMServo, LiquidCrystal y SoftwareSerial.

**Librerías de Python:** pyserial y matplotlib (se instalan con: pip install pyserial matplotlib).

1. Cargar transmisor_def_2.ino en el Arduino del satélite.
2. Cargar RECEPTOR_DEF_2.ino en el Arduino de tierra.
3. En Tierra_DEF_2.py, cambiar device = 'COM5' por el puerto del Arduino de tierra.
4. Ejecutar Tierra_DEF_2.py y pulsar **INICIAR**.

### Conexiones del satélite

- **DHT11:** pin 2
- **HC-SR04 sensor 1 (0–180°):** Trig 4, Echo 5
- **HC-SR04 sensor 2 (180–360°):** Trig 6, Echo 7
- **Servo:** pin 9 (PWMServo solo funciona en los pines 9 y 10)
- **Comunicación con tierra:** RX 10, TX 11
- **LED de envío:** pin 12

### Conexiones de la estación de tierra

- **LCD 16x2 (RS, E, D4, D5, D6, D7):** pines 7, 6, 5, 4, 3, 2
- **Comunicación con el satélite:** RX 10, TX 11
- **LED de recepción:** pin 12

## Protocolo de aplicación

Cada mensaje es una línea de texto con el formato **codigo:dato:dato**.

**Satélite → Tierra**

- **1:temp:hum** — temperatura (°C) y humedad (%)
- **2:angulo:dist** — distancia (cm) medida en un ángulo (0–360°); 0 = sin eco
- **3:** — fallo del sensor de temperatura/humedad
- **4:media** — media de las 10 últimas temperaturas (solo si la calcula el satélite)
- **5:sensor** — fallo del sensor de distancia 1 o 2
- **9:** — latido (cada 2 s): la conexión sigue viva

**Tierra → Satélite**

- **1:segundos** — nuevo periodo de envío de T/H (1–60 s)
- **2:grados** — orientación fija del radar (0–350°, múltiplo de 10)
- **3:** / **4:** — parar / reanudar el envío de T/H
- **5:1** / **5:0** — la media la calcula el satélite (1) o tierra (0)
- **6:** / **7:** — parar / reanudar el radar
- **8:milisegundos** — nuevo periodo del radar (15–200 ms por grado)
- **9:** — modo rastreo: el radar vuelve a hacer el barrido
