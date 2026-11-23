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
| 2 | Radar de 360° con servo + 2 HC-SR04, media de las 10 últimas temperaturas (cola circular) en tierra o en el satélite, alarma de temperatura media, cambio de periodos y orientación del radar desde la interfaz | ([Ver Vídeo 2](https://drive.google.com/file/d/1q4tF_KL9SYcIomtGKmw3714wYmAoL_Bu/view?usp=sharing)) |
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

## Delcaración del uso de la IA
### Versión 1
Para esta primero versión del proyecto de hemos utilizado la inteligencia artificial como apoyo complementario y herramienta de ayuda. En concreto, nos ha ayudado en el diseño de la interfaz:  la elaboración del código de los distintos elementos visuales, como la implementación del bucle para crear estrellas en el fondo, con el objetivo de conseguir un resultado más estético. Además, también ha sido una herramienta útil a la hora de detectar y corregir errores a lo largo del desarrollo, como por ejemplo, cuando nuestra pantalla LCD parpadeaba sin razón, la IA supo identificarlo y corregir el problema. 
Las decisiones, el planteamiento y el contenido del trabajo han sido elaborado por nosotros y hemos revisado críticamente todo lo propuesto por la IA antes de incorporarlo al resultado final

### Versión 2
En la segunda versión de este proyecto hemos vuelto a utilizar herramientas de inteligencia artificial como apoyo complementario durante el proceso. En esta ocasión, nos han ayudado principalmente con el funcionamiento del servo, con el que habíamos tenido problemas, permitiéndonos identificar las causas y encontrar una solución. Además, nos han servido para comprender mejor determinadas partes del código, para recibir sugerencias orientadas a mejorarlo y simplificarlo, y para entender algunos conceptos técnicos relacionados con el montaje y la programación. Por último, también las hemos empleado para detectar y corregir errores durante las pruebas.








