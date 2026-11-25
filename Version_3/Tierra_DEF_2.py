# =====================================================================
#  PROTOCOLO DE APLICACIÓN
#
#  Satélite -> Tierra
#    1:temp:hum     datos de temperatura (ºC) y humedad (%)
#    2:angulo:dist  distancia (cm) medida en un ángulo (0-360º); 0 = sin eco
#    3:             fallo del sensor de temperatura/humedad
#    4:media        media de las 10 últimas temperaturas (solo si se calcula en el satélite)
#    5:sensor       fallo del sensor de distancia 1 o 2 (no responde)
#    6:             coordenadas de la simulación (6:x:y:z)
#    8:             mensaje corrupto (el checksum no coincide)
#    9:             latido (cada 2 s, siempre): la conexión sigue viva
#
#  Tierra -> Satélite
#    1:segundos     nuevo periodo de envío de T/H (1-60 s)
#    2:grados       orientación fija del radar (0-350º, múltiplo de 10)
#    3:             parar envío de T/H
#    4:             reanudar envío de T/H
#    6:             parar radar
#    7:             reanudar radar
#    8:milisegundos nuevo periodo del radar (15-200 ms por grado)
#    9:             modo rastreo: el radar vuelve a barrer (no confundir con el latido, que va al revés)
#    5:1 / 5:0      la media la calcula el satélite (1) o tierra (0)
#    10:            parar envío de la posición
#    11:            reanudar envío de la posición
#    12:segundos    nuevo periodo de envío de la posición (1-60 s)
# =====================================================================

from tkinter import *      
import serial              # comunicación
from matplotlib.figure import Figure    # gráficas
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg     # incrustar gráficas
import threading           # hilos
import random
import time                # para medir el tiempo desde el último mensaje
import math                # pasar grados a radianes
from matplotlib.patches import Circle   # círculo de la Tierra en la gráfica de la órbita

# ---------- Colores ----------
FONDO = "#0B1A2E"      # Azul marino
BORDE = "#2A4468"      # Líneas separadoras
TEXTO2 = "#A9B3C4"     # Texto secundario
C_TEMP = "#FE4E4E"     # Temperatura
C_HUM = "#9CC8F0"      # Humedad
C_CERCA = "#E9D7A5"    # Objeto más cercano
C_RADAR = "#9FE2BF"      # Radar y estados correctos
C_INICIAR = "#FFFFFF"  # Botón INICIAR
C_PARAR = "#F28B82"    # Botones de parar
C_REANUDAR = "#7FD6E8" # Botones de reanudar
C_APLICAR = "#E9D7A5"  # Botón de aplicar
C_ALARMA = "#FF5C5C"   # Alarmas (fallo de sensor, de conexión y de temperatura media)
C_MEDIA = "#ECF65C"    # Línea de la media de temperatura

# ---------- Comunicación y datos ----------
device = 'COM5'
ser = serial.Serial(device, baudrate=9600, timeout=1)  # 9600 baudios, espera máx. 1 s al leer
hilo_iniciado = False       # True cuando se ha pulsado INICIAR (y el hilo ya existe)
alarma_sensor = False       # True cuando el satélite avisa de fallo (código 3)
ultimo_mensaje = 0          # momento (en segundos) del último mensaje válido
TIMEOUT_CONEXION = 6        # segundos sin mensajes para declarar fallo de conexión
ultimo_corrupto = 0         # momento del último mensaje corrupto 
temperaturas = []
humedades = []
eje_x = []
i = 0
distancias_radar = [0] * 36   # última distancia medida en cada ángulo (0º, 10º, ..., 350º)
angulo_actual = 0             # último ángulo del sensor 1 recibido (para la línea de barrido)
ultimo_fallo_dist = [0, 0, 0] # momento del último "5:n" de cada sensor de distancia (se usan [1] y [2])
TIEMPO_FALLO_DIST = 2         # si en 2 s no llega otro "5:n", el sensor vuelve a funcionar
pos_x = []                    # coordenadas X de la órbita (m)
pos_y = []                    # coordenadas Y de la órbita (m)

# --- Cola circular con las 10 últimas temperaturas ---
TAM_COLA = 10           # cuántas temperaturas entran en la media
cola = [0.0] * TAM_COLA # vector de tamaño fijo: aquí se guardan las temperaturas
pos_cola = 0            # posición donde se escribirá la siguiente temperatura
cuantos_cola = 0        # cuántas temperaturas hay de verdad en la cola (máximo TAM_COLA)

# --- Variables para la media y la alarma ---
medias = []             # valores medios calculados
eje_x_media = []        # posición X de cada media
limite = 28.0           # límite de temperatura (lo fija el usuario)
consecutivos = 0        # cuántas medias seguidas superan el límite
alarma_activa = False   # True si 3 medias seguidas superan el límite
media_en_satelite = False   # False = la media la calcula tierra; True = la calcula el satélite


# --- COLA CIRCULAR: cuando está llena se sustituye la más antigua ---
def anadir_cola(valor):
    global pos_cola, cuantos_cola
    cola[pos_cola] = valor              # escribe en la posición actual (si ya había algo, lo sustituye)
    pos_cola = pos_cola + 1
    if pos_cola == TAM_COLA:            # ha llegado al final del vector: vuelve al principio
        pos_cola = 0
    if cuantos_cola < TAM_COLA:         # mientras no esté llena, hay una temperatura más
        cuantos_cola = cuantos_cola + 1


# --- MEDIA ---
def calcular_media():
    if cuantos_cola == 0:
        return 0
    suma = 0
    for k in range(cuantos_cola):       # solo las posiciones que tienen datos de verdad
        suma = suma + cola[k]
    return suma / cuantos_cola


# --- REGISTRAR MEDIA Y COMPROBAR ALARMA ---
def registrar_media(media):
    if len(eje_x) > 0:                  # la media va en la X de la última temperatura
        eje_x_media.append(eje_x[-1])
        medias.append(media)
        comprobar_alarma(media)


# --- COMPROBAR ALARMA: 3 medias superando el límite ---
def comprobar_alarma(media):
    global consecutivos, alarma_activa
    if media > limite:
        consecutivos = consecutivos + 1     # se suma a la racha
    else:
        consecutivos = 0                    # se rompe la racha
    alarma_activa = consecutivos >= 3


# --- RECEPCIÓN: lee el mensaje y actúa en consecuencia ---
def recepcion():
    global i, alarma_sensor, ultimo_mensaje, angulo_actual, ultimo_corrupto
    while True:
        try:
            linea = ser.readline().decode('utf-8').rstrip()   # espera como mucho 1 s
            if linea == "":                                   # no ha llegado nada en 1 s
                continue
            print(linea)
            partes = linea.split(':')                         
            codigo = int(partes[0])                           # el primer trozo es el código
            ultimo_mensaje = time.time()                      # mensaje válido: la conexión funciona
            if codigo == 1:                                   # datos T/H
                temperatura = float(partes[1])
                humedad = float(partes[2])
                eje_x.append(i)
                temperaturas.append(temperatura)
                humedades.append(humedad)
                i = i + 1
                alarma_sensor = False                         # vuelven a llegar datos buenos

                # --- media de los 10 últimos valores (cola circular) ---
                anadir_cola(temperatura)                      # la cola se rellena siempre
                if not media_en_satelite and cuantos_cola == TAM_COLA:
                    registrar_media(calcular_media())         # la calcula tierra
            elif codigo == 4:                                 # la calcula en el satélite
                media = float(partes[1])
                if media_en_satelite:                         # solo se usa si la ha pedido el usuario
                    registrar_media(media)
            elif codigo == 3:                                 # fallo del sensor
                alarma_sensor = True
            elif codigo == 2:                                 # dato del radar
                angulo = int(partes[1])
                distancia = float(partes[2])
                posicion = (angulo % 360) // 10               
                distancias_radar[posicion] = distancia        # sustituye la medida anterior de ese ángulo
                if angulo <= 180:                             # sensor 1: es el ángulo real del servo
                    angulo_actual = angulo
            elif codigo == 5:                                 # fallo de un sensor de distancia
                sensor = int(partes[1])
                if sensor == 1 or sensor == 2:
                    ultimo_fallo_dist[sensor] = time.time()
                    if sensor == 1:                           # borra sus puntos viejos del radar
                        for k in range(0, 18):                # 0º a 170º
                            distancias_radar[k] = 0
                    else:
                        for k in range(19, 36):               # 190º a 350º
                            distancias_radar[k] = 0
            elif codigo == 6:                                 # posición del satélite
                pos_x.append(float(partes[1]))
                pos_y.append(float(partes[2]))
            elif codigo == 8:                                 # mensaje corrupto (lo avisa el Arduino de tierra)
                ultimo_corrupto = time.time()
            # código 9 (latido): solo sirve para actualizar ultimo_mensaje
        except (UnicodeDecodeError, IndexError, ValueError):  # línea defectuosa: se ignora
            pass


# ---- DIBUJAR: números, gráficas y alarmas ---
def dibujar():
    # --- Gráfica de temperatura y humedad ---
    n = len(humedades)                                # humedades se rellena la última
    lineaTemp.set_data(eje_x[:n], temperaturas[:n])
    lineaHum.set_data(eje_x[:n], humedades[:n])

    # --- media, límite y alarma ---
    m = len(medias)
    lineaMedia.set_data(eje_x_media[:m], medias[:m])                        # dibuja la línea de la media
    lineaLimite.set_data([max(0, i - 100), max(100, i)], [limite, limite])  # línea horizontal del límite
    if media_en_satelite:                                                   # quién calcula la media
        donde = " (satélite)"
    else:
        donde = " (tierra)"
    if alarma_activa:                                                        # 3 medias seguidas por encima del límite
        estadoMedia.config(text="●  ALARMA: temperatura media alta" + donde, fg=C_ALARMA)
    elif hilo_iniciado:
        estadoMedia.config(text="●  Temp. media: OK" + donde, fg=C_RADAR)

    ax.set_xlim(max(0, i - 100), max(100, i))                               # se ven solo las últimas 100 muestras
    canvas.draw_idle()                                                      # vuelve a dibujar la gráfica

    # --- Números de temperatura y humedad + ALARMA DEL SENSOR ---
    if alarma_sensor:                                                   # el satélite ha mandado un 3: (fallo del DHT11)
        valorTemp.config(text="FALLO", fg=C_ALARMA)
        valorHum.config(text="FALLO", fg=C_ALARMA)
        estadoSensor.config(text="●  Sensor T/H: FALLO", fg=C_ALARMA)
    else:
        if n > 0:
            valorTemp.config(text=str(temperaturas[n - 1]) + " °C", fg=C_TEMP)   # último valor
            valorHum.config(text=str(humedades[n - 1]) + " %", fg=C_HUM)
        if hilo_iniciado:
            estadoSensor.config(text="●  Sensor T/H: OK", fg=C_RADAR)

    # --- Radar, línea de barrido y objeto más cercano ---
    radianes = []
    distancias = []
    mas_cerca = 0                                     # 0 = todavía no hay ningún objeto
    angulo_cerca = 0
    for k in range(36):
        d = distancias_radar[k]
        if d > 0:                                     # solo los ángulos con eco
            radianes.append(math.radians(k * 10))     # de radianes a grados
            distancias.append(d)
            if mas_cerca == 0 or d < mas_cerca:       # busca el mínimo
                mas_cerca = d
                angulo_cerca = k * 10
    puntosRadar.set_data(radianes, distancias)
    a = math.radians(angulo_actual)                   # línea que pasa por el centro: sensor 1 y sensor 2
    barrido.set_data([a, a, a + math.pi, a + math.pi], [200, 0, 0, 200])
    canvasRadar.draw_idle()
    if mas_cerca > 0:
        valorCerca.config(text=str(round(mas_cerca)) + " cm")
        valorCercaAngulo.config(text="a " + str(angulo_cerca) + "°")

    # --- ALARMA DE LOS SENSORES DE DISTANCIA ---
    fallo1 = time.time() - ultimo_fallo_dist[1] < TIEMPO_FALLO_DIST
    fallo2 = time.time() - ultimo_fallo_dist[2] < TIEMPO_FALLO_DIST
    if fallo1 and fallo2:                                                       # Fallan los dos
        estadoRadar.config(text="●  FALLO SENSORES DIST. 1 Y 2", fg=C_ALARMA)
    elif fallo1:                                                                # Falla el primero solo
        estadoRadar.config(text="●  FALLO SENSOR DIST. 1", fg=C_ALARMA)
    elif fallo2:                                                                # Falla el segundo solo
        estadoRadar.config(text="●  FALLO SENSOR DIST. 2", fg=C_ALARMA)
    elif hilo_iniciado:                                                         # No fallan
        estadoRadar.config(text="●  Radar: OK", fg=C_RADAR)

    # --- Órbita del satélite ---
    p = len(pos_y)                                    # pos_y se rellena la última
    if p > 0:
        lineaOrbita.set_data(pos_x[:p], pos_y[:p])                 # toda la trayectoria
        puntoSatelite.set_data([pos_x[p - 1]], [pos_y[p - 1]])     # último punto
        canvasOrbita.draw_idle()                                   # vuelve a dibujar la órbita

    # --- ALARMA DE CONEXIÓN Y MENSAJES CORRUPTOS ---
    if hilo_iniciado:                                 # solo se vigila tras pulsar INICIAR
        if time.time() - ultimo_mensaje > TIMEOUT_CONEXION:
            estado.config(text="●  FALLO DE CONEXIÓN", fg=C_ALARMA)
        elif time.time() - ultimo_corrupto < 2:       # ha llegado un mensaje corrupto hace menos de 2 s
            estado.config(text="●  MENSAJE CORRUPTO", fg=C_ALARMA)
        else:
            estado.config(text="●  Recibiendo datos", fg=C_RADAR)

    window.after(500, dibujar)


# ---ENVIA ORDEN AL SATÉLITE ---
def enviar(mensaje):
    for k in range(2):
        ser.write((mensaje + '\n').encode('utf-8'))
        time.sleep(0.05)                               # 50 ms entre las dos copias


# ---LEERENTERO: comprueba si el número introducido es válido ---
def leerEntero(casilla, nombre, minimo, maximo):
    texto = casilla.get()
    try:
        valor = int(texto)
    except ValueError:                                  # no es un número entero
        mensaje.config(text="⚠ " + nombre + ": '" + texto + "' no es un número entero", fg=C_ALARMA)
        return None
    if valor < minimo or valor > maximo:                # fuera de rango
        mensaje.config(text="⚠ " + nombre + ": debe estar entre " + str(minimo) + " y " + str(maximo), fg=C_ALARMA)
        return None
    return valor


# ---------- Funciones de los botones ----------
def IniciarClick(evento):           # INICIAR: arranca la recepción, T/H y el radar
    global hilo_iniciado, ultimo_mensaje
    if not hilo_iniciado:                              # solo la primera vez
        ser.reset_input_buffer()                       # descarta lo recibido antes de INICIAR
        ultimo_mensaje = time.time()                   # empieza a contar desde ahora
        threadRecepcion = threading.Thread(target=recepcion, daemon=True)
        threadRecepcion.start()
        hilo_iniciado = True
    enviar("4:")                                       # reanudar T/H
    enviar("7:")                                       # reanudar radar
    enviar("11:")                                      # reanudar posición
    mensaje.config(text="Sistema en marcha", fg="white")

def PararTHClick(evento):
    enviar("3:")
    mensaje.config(text="Envío de T/H parado", fg="white")

def ReanudarTHClick(evento):
    enviar("4:")
    mensaje.config(text="Envío de T/H en marcha", fg="white")

def PararRadarClick(evento):
    enviar("6:")
    mensaje.config(text="Radar parado", fg="white")

def ReanudarRadarClick(evento):
    enviar("7:")
    mensaje.config(text="Radar en marcha", fg="white")

def AplicarClick(evento):                               # comprueba los tres periodos y, si están bien, los envía
    periodo_th = leerEntero(entradaTemp, "Periodo T/H", 1, 60)
    if periodo_th is None:                              # el aviso ya está en mensaje
        return
    periodo_radar = leerEntero(entradaDist, "Periodo radar", 15, 200)
    if periodo_radar is None:
        return
    periodo_pos = leerEntero(entradaPos, "Periodo posición", 1, 60)
    if periodo_pos is None:
        return
    enviar("1:" + str(periodo_th))
    enviar("8:" + str(periodo_radar))
    enviar("12:" + str(periodo_pos))
    mensaje.config(text="Periodos aplicados: T/H " + str(periodo_th) + " s, radar "
                   + str(periodo_radar) + " ms/grado, posición " + str(periodo_pos) + " s", fg="white")

def OrientarClick(evento):                              # orientación fija del radar
    valor = leerEntero(entradaOrientacion, "Orientación", 0, 350)
    if valor is None:                                   # el aviso ya está en mensaje
        return
    if valor % 10 != 0:                                 # el radar mide de 10 en 10 grados
        mensaje.config(text="⚠ Orientación: tiene que ser múltiplo de 10 (0, 10, 20... 350)", fg=C_ALARMA)
        return
    enviar("2:" + str(valor))
    mensaje.config(text="Radar fijo hacia " + str(valor) + "°", fg="white")

def RastreoClick(evento):                                # modo rastreo 
    enviar("9:")
    mensaje.config(text="Radar en modo rastreo (barrido)", fg="white")

def PararPosicionClick(evento):
    enviar("10:")
    mensaje.config(text="Envío de la posición parado", fg="white")

def ReanudarPosicionClick(evento):
    enviar("11:")
    mensaje.config(text="Envío de la posición en marcha", fg="white")

def marcarModoMedia():
    if media_en_satelite:                                       # resalta el boton de satélite
        botonMediaSatelite.config(bg=C_APLICAR, fg=FONDO)
        botonMediaTierra.config(bg=FONDO, fg=C_APLICAR)
    else:                                                       # resalta el boton de tierra
        botonMediaTierra.config(bg=C_APLICAR, fg=FONDO)
        botonMediaSatelite.config(bg=FONDO, fg=C_APLICAR)

def MediaTierraClick(evento):        # la media la calcula tierra
    global media_en_satelite
    media_en_satelite = False
    enviar("5:0")
    marcarModoMedia()
    mensaje.config(text="La media la calcula tierra", fg="white")

def MediaSateliteClick(evento):     # la media la calcula el satélite
    global media_en_satelite
    media_en_satelite = True
    enviar("5:1")
    marcarModoMedia()
    mensaje.config(text="La media la calcula el satélite", fg="white")

def FijarLimiteClick(evento):       # fija el límite de la temperatura media
    global limite
    try:
        valor = float(entradaLimite.get().replace(",", "."))
    except ValueError:
        mensaje.config(text="⚠ Límite: '" + entradaLimite.get() + "' no es un número", fg=C_ALARMA)
        return
    if valor < 0 or valor > 50:                               # rango que mide el DHT11
        mensaje.config(text="⚠ Límite: debe estar entre 0 y 50 °C", fg=C_ALARMA)
        return
    limite = valor
    mensaje.config(text="Límite de temperatura media: " + str(limite) + " °C", fg="white")

def cerrar():
    ser.close()
    window.destroy()


# ---------- Ventana ----------
window = Tk()
window.title("Estación de Tierra")
window.geometry("1400x900")
window.configure(bg=FONDO)

# Columnas y filas
window.columnconfigure(0, weight=1, uniform="col")
window.columnconfigure(1, weight=1, uniform="col")
window.columnconfigure(2, weight=1, uniform="col")
window.rowconfigure(5, weight=1)

# ---------- Estrellas ----------
fondo = Canvas(window, bg=FONDO, highlightthickness=0)
fondo.place(x=0, y=0, relwidth=1, relheight=1)
for _ in range(150):
    x = random.randint(0, 1600)
    y = random.randint(0, 1000)
    fondo.create_oval(x, y, x + 2, y + 2, fill="white", outline="")

# ---------- Fila 0: título ----------
Label(window, text="ESTACIÓN DE TIERRA", bg=FONDO, fg="white",
      font=("Helvetica", 24, "bold")).grid(row=0, column=0, columnspan=3, pady=(20, 0))

# ---------- Fila 1: estado (ALARMAS de conexión y de sensor) ----------
cajaEstado = Frame(window, bg=FONDO)                    
cajaEstado.grid(row=1, column=0, columnspan=3, pady=(0, 10))
estado = Label(cajaEstado, text="●  Sin datos (pulse INICIAR)", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13))
estado.pack(side=LEFT, padx=12)
estadoSensor = Label(cajaEstado, text="●  Sensor T/H: --", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13))
estadoSensor.pack(side=LEFT, padx=12)
estadoMedia = Label(cajaEstado, text="●  Temp. media: --", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13))   # 5.2
estadoMedia.pack(side=LEFT, padx=12)
estadoRadar = Label(cajaEstado, text="●  Radar: --", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13))   # fallo sensores distancia
estadoRadar.pack(side=LEFT, padx=12)

# ---------- Fila 2: línea separadora ----------
Frame(window, bg=BORDE, height=1).grid(row=2, column=0, columnspan=3, sticky="ew", padx=40)

# ---------- Fila 3: números ----------
# Temperatura (columna 0)
cajaTemp = Frame(window, bg=FONDO)
cajaTemp.grid(row=3, column=0, pady=15)
Label(cajaTemp, text="TEMPERATURA", bg=FONDO, fg=TEXTO2, font=("Helvetica", 11, "bold")).pack()
valorTemp = Label(cajaTemp, text="--", bg=FONDO, fg=C_TEMP, font=("Helvetica", 34, "bold"))
valorTemp.pack()

# Humedad (columna 1)
cajaHum = Frame(window, bg=FONDO)
cajaHum.grid(row=3, column=1, pady=15)
Label(cajaHum, text="HUMEDAD", bg=FONDO, fg=TEXTO2, font=("Helvetica", 11, "bold")).pack()
valorHum = Label(cajaHum, text="--", bg=FONDO, fg=C_HUM, font=("Helvetica", 34, "bold"))
valorHum.pack()

# Objeto más cercano (columna 2)
cajaCerca = Frame(window, bg=FONDO)
cajaCerca.grid(row=3, column=2, pady=15)
Label(cajaCerca, text="MÁS CERCANO", bg=FONDO, fg=TEXTO2, font=("Helvetica", 11, "bold")).pack()
valorCerca = Label(cajaCerca, text="--", bg=FONDO, fg=C_CERCA, font=("Helvetica", 34, "bold"))
valorCerca.pack()
valorCercaAngulo = Label(cajaCerca, text="", bg=FONDO, fg=TEXTO2, font=("Helvetica", 11))   
valorCercaAngulo.pack()

# Líneas verticales entre los números
Frame(window, bg=BORDE, width=1).grid(row=3, column=1, sticky="nsw", pady=15)
Frame(window, bg=BORDE, width=1).grid(row=3, column=2, sticky="nsw", pady=15)

# ---------- Fila 4: línea separadora ----------
Frame(window, bg=BORDE, height=1).grid(row=4, column=0, columnspan=3, sticky="ew", padx=40)

# ---------- Fila 5: gráfica y radar ----------
zonaGraficas = Frame(window, bg=FONDO)
zonaGraficas.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=40, pady=10)

# --- Gráfica de temperatura y humedad ---
fig = Figure(figsize=(4, 3), facecolor=FONDO)

estrellas = fig.add_axes([0, 0, 1, 1])        # Estrellas detrás de la gráfica
estrellas.axis("off")
estrellas.scatter([random.random() for _ in range(35)], [random.random() for _ in range(35)], s=2, color="white")

# Eje de la temperatura (izquierda)
ax = fig.add_subplot(111, facecolor="none", frame_on=False, xlim=(0, 100), ylim=(15, 35))   #  más margen para ver el límite
ax.grid(axis="y", color=BORDE)
ax.tick_params(colors=TEXTO2, length=0)
lineaTemp, = ax.plot([], [], color=C_TEMP, linewidth=2)
lineaMedia, = ax.plot([], [], color=C_MEDIA, linewidth=2)                    # media de los 10 últimos
lineaLimite, = ax.plot([], [], color=C_ALARMA, linestyle="--", linewidth=1)  # línea del límite

# Eje de la humedad (derecha)
ax2 = ax.twinx()
ax2.set_frame_on(False)
ax2.set_ylim(0, 100)
ax2.tick_params(colors=TEXTO2, length=0)
lineaHum, = ax2.plot([], [], color=C_HUM, linewidth=2)

# Meter la gráfica en la ventana
canvas = FigureCanvasTkAgg(fig, master=zonaGraficas)
canvas.get_tk_widget().configure(bg=FONDO, highlightthickness=0)
canvas.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=True)

# Línea vertical entre la gráfica y el radar
Frame(zonaGraficas, bg=BORDE, width=1).pack(side=LEFT, fill=Y, padx=10)

# --- Radar (mitad derecha) ---
figRadar = Figure(figsize=(4, 3), facecolor=FONDO)            # Figura con el mismo azul que la ventana

# Capa de estrellas detrás del radar
estrellasR = figRadar.add_axes([0, 0, 1, 1])  # Ocupa toda la figura
estrellasR.axis("off")                        # Sin ejes ni números
estrellasR.scatter([random.random() for _ in range(30)],
                   [random.random() for _ in range(30)], s=2, color="white")   # 30 estrellas al azar

# Gráfica circular (polar)
axRadar = figRadar.add_subplot(111, projection="polar", facecolor="none")   # Círculo sin fondo
axRadar.set_ylim(0, 100)
axRadar.set_yticks([25, 50, 75, 100])
axRadar.grid(color=C_RADAR, alpha=0.3)
axRadar.spines["polar"].set_color(C_RADAR)
axRadar.tick_params(colors=TEXTO2)
barrido, = axRadar.plot([], [], color=C_RADAR, linewidth=2)                 # línea que gira con el servo
puntosRadar, = axRadar.plot([], [], 'o', color=C_CERCA, markersize=6)      

# Meter el radar en la ventana
canvasRadar = FigureCanvasTkAgg(figRadar, master=zonaGraficas)
canvasRadar.get_tk_widget().configure(bg=FONDO, highlightthickness=0)
canvasRadar.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=True)

# Línea vertical entre el radar y la órbita
Frame(zonaGraficas, bg=BORDE, width=1).pack(side=LEFT, fill=Y, padx=10)

# --- Órbita del satélite (vista desde el polo norte) ---
figOrbita = Figure(figsize=(4, 3), facecolor=FONDO)
axOrbita = figOrbita.add_subplot(111, facecolor="none")
axOrbita.set_xlim(-8e6, 8e6)                     # la órbita tiene radio 6771 km: cabe con margen
axOrbita.set_ylim(-8e6, 8e6)
axOrbita.set_aspect("equal")                     # proporción 1:1 para que la órbita salga redonda
axOrbita.set_title("Órbita (vista desde el polo norte)", color=TEXTO2, fontsize=10)
axOrbita.set_xlabel("X (m)", color=TEXTO2)
axOrbita.set_ylabel("Y (m)", color=TEXTO2)
axOrbita.tick_params(colors=TEXTO2)
axOrbita.xaxis.offsetText.set_color(TEXTO2)      # el "1e6" que sale junto a los ejes
axOrbita.yaxis.offsetText.set_color(TEXTO2)
axOrbita.grid(color=BORDE)
for lado in axOrbita.spines.values():            # bordes del recuadro
    lado.set_color(BORDE)
axOrbita.add_patch(Circle((0, 0), 6371000, color="orange", fill=False))       # superficie de la Tierra
lineaOrbita, = axOrbita.plot([], [], color=C_HUM, linewidth=1)                # trayectoria del satélite
puntoSatelite, = axOrbita.plot([], [], 'o', color=C_ALARMA, markersize=7)     # último punto

# Meter la órbita en la ventana
canvasOrbita = FigureCanvasTkAgg(figOrbita, master=zonaGraficas)
canvasOrbita.get_tk_widget().configure(bg=FONDO, highlightthickness=0)
canvasOrbita.get_tk_widget().pack(side=LEFT, fill=BOTH, expand=True)

# ---------- Fila 6: línea separadora ----------
Frame(window, bg=BORDE, height=1).grid(row=6, column=0, columnspan=3, sticky="ew", padx=40)

# ---------- Fila 7: controles ----------
# --- Temperatura / humedad (columna 0) ---
cajaControlTH = Frame(window, bg=FONDO)
cajaControlTH.grid(row=7, column=0, pady=20, sticky="e")
Label(cajaControlTH, text="TEMPERATURA / HUMEDAD", bg=FONDO, fg=TEXTO2,
      font=("Helvetica", 11, "bold")).pack(pady=(0, 10))

# Fila de botones
botonesTH = Frame(cajaControlTH, bg=FONDO)
botonesTH.pack()
bordePararTH = Frame(botonesTH, bg=C_PARAR, padx=2, pady=2)
bordePararTH.pack(side=LEFT, padx=5)
botonPararTH = Label(bordePararTH, text="PARAR T/H", bg=FONDO, fg=C_PARAR, font=("Helvetica", 13, "bold"),
                     padx=15, pady=8, cursor="hand2")
botonPararTH.pack()
botonPararTH.bind("<Button-1>", PararTHClick)                 
bordeReanudarTH = Frame(botonesTH, bg=C_REANUDAR, padx=2, pady=2)
bordeReanudarTH.pack(side=LEFT, padx=5)
botonReanudarTH = Label(bordeReanudarTH, text="REANUDAR T/H", bg=FONDO, fg=C_REANUDAR, font=("Helvetica", 13, "bold"),
                        padx=15, pady=8, cursor="hand2")
botonReanudarTH.pack()
botonReanudarTH.bind("<Button-1>", ReanudarTHClick)           

# Fila de periodo
periodoTH = Frame(cajaControlTH, bg=FONDO)
periodoTH.pack(pady=(15, 0))
Label(periodoTH, text="Periodo (1-60 s)", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13)).pack(side=LEFT, padx=(0, 10))
entradaTemp = Entry(periodoTH, width=6, justify=CENTER, bg=FONDO, fg="white", font=("Helvetica", 14),
                    highlightthickness=1, highlightbackground=BORDE, insertbackground="white")
entradaTemp.insert(0, "3")                         # valor inicial: el del satélite
entradaTemp.pack(side=LEFT)

# Fila del límite de la temperatura media 
filaLimite = Frame(cajaControlTH, bg=FONDO)
filaLimite.pack(pady=(10, 0))
Label(filaLimite, text="Límite media (°C)", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13)).pack(side=LEFT, padx=(0, 10))
entradaLimite = Entry(filaLimite, width=6, justify=CENTER, bg=FONDO, fg="white", font=("Helvetica", 14),
                      highlightthickness=1, highlightbackground=BORDE, insertbackground="white")
entradaLimite.insert(0, "28")
entradaLimite.pack(side=LEFT)
bordeFijar = Frame(filaLimite, bg=C_APLICAR, padx=2, pady=2)
bordeFijar.pack(side=LEFT, padx=(10, 0))
botonFijar = Label(bordeFijar, text="FIJAR", bg=FONDO, fg=C_APLICAR, font=("Helvetica", 11, "bold"),
                   padx=10, pady=3, cursor="hand2")
botonFijar.pack()
botonFijar.bind("<Button-1>", FijarLimiteClick)

# Fila para elegir dónde se calcula la media 
filaMedia = Frame(cajaControlTH, bg=FONDO)
filaMedia.pack(pady=(10, 0))
Label(filaMedia, text="Media en", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13)).pack(side=LEFT, padx=(0, 10))
bordeMediaTierra = Frame(filaMedia, bg=C_APLICAR, padx=2, pady=2)
bordeMediaTierra.pack(side=LEFT)
botonMediaTierra = Label(bordeMediaTierra, text="TIERRA", font=("Helvetica", 11, "bold"),
                         padx=8, pady=3, cursor="hand2")
botonMediaTierra.pack()
botonMediaTierra.bind("<Button-1>", MediaTierraClick)
bordeMediaSatelite = Frame(filaMedia, bg=C_APLICAR, padx=2, pady=2)
bordeMediaSatelite.pack(side=LEFT, padx=(6, 0))
botonMediaSatelite = Label(bordeMediaSatelite, text="SATÉLITE", font=("Helvetica", 11, "bold"),
                           padx=8, pady=3, cursor="hand2")
botonMediaSatelite.pack()
botonMediaSatelite.bind("<Button-1>", MediaSateliteClick)
marcarModoMedia()                                  # al empezar, resalta TIERRA

# --- INICIAR, APLICAR y mensajes (columna 1) ---
cajaCentro = Frame(window, bg=FONDO)
cajaCentro.grid(row=7, column=1, pady=20)
haloIniciar = Frame(cajaCentro, bg="#3B4E6B", padx=4, pady=4)
haloIniciar.pack(pady=(0, 15))
botonIniciar = Label(haloIniciar, text="▶  INICIAR", bg=C_INICIAR, fg=FONDO, font=("Helvetica", 20, "bold"),
                     padx=35, pady=12, cursor="hand2")
botonIniciar.pack()
botonIniciar.bind("<Button-1>", IniciarClick)                 
bordeAplicar = Frame(cajaCentro, bg=C_APLICAR, padx=2, pady=2)
bordeAplicar.pack()
botonAplicar = Label(bordeAplicar, text="APLICAR PERIODOS", bg=FONDO, fg=C_APLICAR, font=("Helvetica", 13, "bold"),
                     padx=15, pady=8, cursor="hand2")
botonAplicar.pack()
botonAplicar.bind("<Button-1>", AplicarClick)   

# Controles de la posición
Label(cajaCentro, text="POSICIÓN", bg=FONDO, fg=TEXTO2,
      font=("Helvetica", 11, "bold")).pack(pady=(15, 5))
filaPosicion = Frame(cajaCentro, bg=FONDO)
filaPosicion.pack()
bordePararP = Frame(filaPosicion, bg=C_PARAR, padx=2, pady=2)
bordePararP.pack(side=LEFT, padx=5)
botonPararP = Label(bordePararP, text="PARAR", bg=FONDO, fg=C_PARAR, font=("Helvetica", 11, "bold"),
                    padx=8, pady=3, cursor="hand2")
botonPararP.pack()
botonPararP.bind("<Button-1>", PararPosicionClick)
bordeReanudarP = Frame(filaPosicion, bg=C_REANUDAR, padx=2, pady=2)
bordeReanudarP.pack(side=LEFT, padx=5)
botonReanudarP = Label(bordeReanudarP, text="REANUDAR", bg=FONDO, fg=C_REANUDAR, font=("Helvetica", 11, "bold"),
                       padx=8, pady=3, cursor="hand2")
botonReanudarP.pack()
botonReanudarP.bind("<Button-1>", ReanudarPosicionClick)
periodoP = Frame(cajaCentro, bg=FONDO)
periodoP.pack(pady=(8, 0))
Label(periodoP, text="Periodo (1-60 s)", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13)).pack(side=LEFT, padx=(0, 10))
entradaPos = Entry(periodoP, width=4, justify=CENTER, bg=FONDO, fg="white", font=("Helvetica", 14),
                   highlightthickness=1, highlightbackground=BORDE, insertbackground="white")
entradaPos.insert(0, "1")                          # valor inicial: el del satélite
entradaPos.pack(side=LEFT) 

mensaje = Label(cajaCentro, text="", bg=FONDO, fg="white", font=("Helvetica", 11),
                wraplength=360)                               
mensaje.pack(pady=(10, 0))

# --- Radar (columna 2) ---
cajaControlR = Frame(window, bg=FONDO)
cajaControlR.grid(row=7, column=2, pady=20, sticky="w")
Label(cajaControlR, text="RADAR", bg=FONDO, fg=TEXTO2,
      font=("Helvetica", 11, "bold")).pack(pady=(0, 10))

botonesR = Frame(cajaControlR, bg=FONDO)
botonesR.pack()
bordePararR = Frame(botonesR, bg=C_PARAR, padx=2, pady=2)
bordePararR.pack(side=LEFT, padx=5)
botonPararR = Label(bordePararR, text="PARAR RADAR", bg=FONDO, fg=C_PARAR, font=("Helvetica", 13, "bold"),
                    padx=15, pady=8, cursor="hand2")
botonPararR.pack()
botonPararR.bind("<Button-1>", PararRadarClick)               
bordeReanudarR = Frame(botonesR, bg=C_REANUDAR, padx=2, pady=2)
bordeReanudarR.pack(side=LEFT, padx=5)
botonReanudarR = Label(bordeReanudarR, text="REANUDAR RADAR", bg=FONDO, fg=C_REANUDAR, font=("Helvetica", 13, "bold"),
                       padx=15, pady=8, cursor="hand2")
botonReanudarR.pack()
botonReanudarR.bind("<Button-1>", ReanudarRadarClick)         

periodoR = Frame(cajaControlR, bg=FONDO)
periodoR.pack(pady=(15, 0))
Label(periodoR, text="Periodo (15-200 ms/grado)", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13)).pack(side=LEFT, padx=(0, 10))
entradaDist = Entry(periodoR, width=6, justify=CENTER, bg=FONDO, fg="white", font=("Helvetica", 14),
                    highlightthickness=1, highlightbackground=BORDE, insertbackground="white")
entradaDist.insert(0, "30")                        # valor inicial: el del satélite (ms por grado)
entradaDist.pack(side=LEFT)

# Fila de orientación fija / rastreo (punto 10)
filaOrientar = Frame(cajaControlR, bg=FONDO)
filaOrientar.pack(pady=(10, 0))
Label(filaOrientar, text="Orientar a (°)", bg=FONDO, fg=TEXTO2, font=("Helvetica", 13)).pack(side=LEFT, padx=(0, 10))
entradaOrientacion = Entry(filaOrientar, width=5, justify=CENTER, bg=FONDO, fg="white", font=("Helvetica", 14),
                           highlightthickness=1, highlightbackground=BORDE, insertbackground="white")
entradaOrientacion.insert(0, "90")
entradaOrientacion.pack(side=LEFT)
bordeOrientar = Frame(filaOrientar, bg=C_APLICAR, padx=2, pady=2)
bordeOrientar.pack(side=LEFT, padx=(10, 0))
botonOrientar = Label(bordeOrientar, text="ORIENTAR", bg=FONDO, fg=C_APLICAR, font=("Helvetica", 11, "bold"),
                      padx=8, pady=3, cursor="hand2")
botonOrientar.pack()
botonOrientar.bind("<Button-1>", OrientarClick)
bordeRastreo = Frame(filaOrientar, bg=C_REANUDAR, padx=2, pady=2)
bordeRastreo.pack(side=LEFT, padx=(6, 0))
botonRastreo = Label(bordeRastreo, text="RASTREO", bg=FONDO, fg=C_REANUDAR, font=("Helvetica", 11, "bold"),
                     padx=8, pady=3, cursor="hand2")
botonRastreo.pack()
botonRastreo.bind("<Button-1>", RastreoClick)

window.protocol("WM_DELETE_WINDOW", cerrar)
dibujar()
window.mainloop()
