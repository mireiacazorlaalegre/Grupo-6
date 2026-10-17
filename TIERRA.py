from tkmacosx import Button
import numpy as np
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import *
import serial
import matplotlib.pyplot as plt
import threading
from matplotlib.figure import Figure
device = 'COM5' # Puerto serie del PC donde está el Arduino
ser = serial.Serial(device, baudrate=9600, timeout=1) # Abre el puerto a 9600 baudios; espera máx. 1 s al leer
leyendo = False # Indica si se deben mostrar los datos recibidos
temperaturas = []
eje_x = []
i = 0 
def recepcion (): # Función que se ejecutará en un hilo aparte
    global i
    while True:
        if leyendo and ser.in_waiting > 0: # Si está activada la lectura y hay datos esperando
            linea = ser.readline().decode('utf-8').rstrip() # Lee una línea, la pasa a texto y quita saltos finales
            print(linea) # La muestra por la consola
            trozos = linea.split(':')
            eje_x.append(i)
            temperatura = float(trozos[1])
            temperaturas.append(temperatura)
            plt.plot(eje_x, temperaturas)
            plt.title(str(i))
            i = i + 1
            plt.draw()
def IClick ():
    print ('Iniciando') # Se ejecuta al pulsar INICIAR
    global leyendo
    leyendo = True # Activa la lectura
    plt.ion()
    plt.axis([0,100,20,30])
    threadRecepcion = threading.Thread (target = recepcion) # Crea el hilo que ejecuta recepcion()
    threadRecepcion.start() # Lo arranca (así la ventana no se bloquea)
def PClick (): # Se ejecuta al pulsar PARAR
    print ('Parar')
    global leyendo 
    leyendo = False # Desactiva la lectura 
    mensaje = "Parar"
    ser.write(mensaje.encode('utf-8')) # Envía "Parar" al Arduino (convertido a bytes)
def RClick (): # Se ejecuta al pulsar REANUDAR
    global leyendo 
    leyendo = True # Vuelve a activar la lectura
    print ('Reanudar')
    mensaje = "Reanudar"
    ser.write(mensaje.encode('utf-8')) # Envía "Reanudar" al Arduino
#CONFIGURACIÓN DE VENTANA PRINCIPAL
window = Tk()
window.configure(bg="#0B1A2E")
window.geometry("1200x800")
window.rowconfigure(0, weight=2)
window.rowconfigure(1, weight=2)
window.rowconfigure(2, weight=1)
window.columnconfigure(0, weight=3)
window.columnconfigure(1, weight=3)
window.columnconfigure(2, weight=3)
#FONDO
fondo = Canvas(window, bg="#0B1A2E", highlightthickness=0)
fondo.place(x=0, y=0, relwidth=1, relheight=1)
for _ in range(150): #Bucle con el que simulamos las estrellas
    x = random.randint(0, 1200)
    y = random.randint(0, 800)
    fondo.create_oval(x, y, x + 2, y + 2, fill="white", outline="")
fondo.create_text(600, 80, text="TEMPERATURA", fill="white", font=("Helvetica", 20, "italic", "bold")) #El texto "TEMPERATURA" está escrito en el fondo, no como fila de independiente
IniciarButton = Button(window, text="INICIAR", bg="white", fg="#0B1A2E", width=300, height=200, font=("Helvetica", 20, "italic", "bold"), command=IClick)
IniciarButton.grid(row=2, column=0)
PararButton = Button(window, text="PARAR", bg="white", fg="#0B1A2E", width=300, height=200, font=("Helvetica", 20, "italic", "bold"), command=PClick)
PararButton.grid(row=2, column=1)
ReanudarButton = Button(window, text="REANUDAR", bg="white", fg="#0B1A2E", width=300, height=200, font=("Helvetica", 20, "italic", "bold"), command=RClick)
ReanudarButton.grid(row=2, column=2)
window.mainloop()