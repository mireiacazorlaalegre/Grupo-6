from tkinter import *                 # Librería para crear la ventana y los botones
import serial                         # Librería para comunicarse por el puerto serie (pySerial)
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Permite meter la gráfica dentro de Tkinter
import threading      
import random                
device = 'COM5'                       # Puerto serie del PC donde está el Arduino
ser = serial.Serial(device, baudrate=9600, timeout=1)  # Abre el puerto a 9600 baudios; espera máx. 1 s al leer
leyendo = False                       # Bandera: indica si se deben mostrar los datos recibidos
temperaturas = []                  # Lista con las temperaturas recibidas
humedades = []                    # Lista con las humedades recibidas
eje_x = []                            # Lista con el número de cada muestra
i = 0                                 # Contador de muestras

def recepcion ():                     # Función que se ejecutará en un hilo aparte (solo lee)
     global i
     while True:                      # Bucle infinito
      if leyendo and ser.in_waiting > 0:             # Si está activada la lectura y hay datos esperando
       linea = ser.readline().decode('utf-8').rstrip()  # Lee una línea, la pasa a texto y quita saltos finales
       print(linea)                                  # La muestra por la consola
       try:                                          # Extrae el número de una línea tipo "Temp:24.5"
           partes = linea.split(':')                 # ["T", "27.90", "H", "50.00"]
           temperatura = float(partes[1])
           humedad = float(partes[3]) 
       except (IndexError, ValueError):              # Si la línea llega rota, se ignora
           continue
       eje_x.append(i)                               # Guarda el número de muestra
       temperaturas.append(temperatura)              # Guarda la temperatura
       humedades.append(humedad)                   # Guarda la humedad
       i = i + 1                                     # Siguiente muestra

def dibujar ():                       # Se ejecuta cada 0,5 s dentro del bucle de Tkinter
    n = len(humedades)                           # Mismo número de datos en X y en Y
    linea_temp.set_data(eje_x[:n], temperaturas[:n]) # Actualiza la línea con todos los datos
    linea_hum.set_data(eje_x[:n], humedades[:n]) 
    ax.set_xlim(max(0, i - 100), max(100, i))        # El eje X se desplaza con los datos
    ax.set_title(str(i))                             # Título de la gráfica
    canvas.draw_idle()                               # Redibuja la gráfica incrustada
    window.after(500, dibujar)                       # Se repite cada 0,5 s

def IClick ():                        # Se ejecuta al pulsar INICIAR
    print ('Iniciando')
    global leyendo                    # Permite modificar la variable global
    leyendo = True                    # Activa la lectura
    threadRecepcion = threading.Thread (target = recepcion, daemon = True)  # daemon=True para que el programa termine al cerrar la ventana
    threadRecepcion.start()           # Lo arranca (así la ventana no se bloquea)
    mensaje = "Reanudar"
    ser.write(mensaje.encode('utf-8'))
    

def PClick ():                        # Se ejecuta al pulsar PARAR
    print ('Parar')
    global leyendo
    leyendo = False                   # Desactiva la lectura (el hilo sigue vivo, pero no imprime)
    mensaje = "Parar"
    ser.write(mensaje.encode('utf-8'))  # Envía "Parar" al Arduino (convertido a bytes)

def RClick ():                        # Se ejecuta al pulsar REANUDAR
    global leyendo
    leyendo = True                    # Vuelve a activar la lectura
    print ('Reanudar')
    mensaje = "Reanudar"
    ser.write(mensaje.encode('utf-8'))  # Envía "Reanudar" al Arduino

def cerrar ():                        
    ser.close()                       
    window.destroy()                  



window = Tk()
window.configure(bg="#0B1A2E")
window.geometry("1200x800")
window.rowconfigure(0, weight=1)
window.rowconfigure(1, weight=4)
window.rowconfigure(2, weight=1)
window.columnconfigure(0, weight=1)
window.columnconfigure(1, weight=1)
window.columnconfigure(2, weight=1)

# CAMBIO: el fondo se crea PRIMERO, para que todo lo demás quede encima
fondo = Canvas(window, bg="#0B1A2E", highlightthickness=0)
fondo.place(x=0, y=0, relwidth=1, relheight=1)
for _ in range(150): #Bucle con el que simulamos las estrellas
    x = random.randint(0, 1200)
    y = random.randint(0, 800)
    fondo.create_oval(x, y, x + 2, y + 2, fill="white", outline="")
fondo.create_text(600, 40, text="TEMPERATURA", fill="white", font=("Helvetica", 20, "italic", "bold")) #El texto "TEMPERATURA" está escrito en el fondo, no como fila de independiente



# La gráfica dentro de la ventana
fig = Figure(figsize=(6, 3))          # Figura de Matplotlib (sustituye a plt)
ax = fig.add_subplot(111)             # Los ejes donde se dibuja
ax.set_xlim(0, 100)                   # Eje X inicial
ax.set_ylim(20, 40)  
ax.set_ylabel("Temperatura (°C)", color="red")   
linea_temp, = ax.plot([], [], color="red")       # antes linea_plot
ax2 = ax.twinx()                                 #segundo eje Y a la derecha
ax2.set_ylim(0, 100)                             
ax2.set_ylabel("Humedad (%)", color="blue")      
linea_hum, = ax2.plot([], [], color="blue")      
                           

canvas = FigureCanvasTkAgg(fig, master=window)  # Conecta la figura con la ventana de Tkinter
canvas.get_tk_widget().grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=N + S + E + W)  # La coloca en la fila 1, ocupando las 3 columnas


IniciarButton = Button(window, text="INICIAR", bg="white", fg="#0B1A2E", width=15, height=2, font=("Helvetica", 20, "italic", "bold"), command=IClick)
IniciarButton.grid(row=2, column=0)
PararButton = Button(window, text="PARAR", bg="white", fg="#0B1A2E", width=15, height=2, font=("Helvetica", 20, "italic", "bold"), command=PClick)
PararButton.grid(row=2, column=1)
ReanudarButton = Button(window, text="REANUDAR", bg="white", fg="#0B1A2E", width=15, height=2, font=("Helvetica", 20, "italic", "bold"), command=RClick)
ReanudarButton.grid(row=2, column=2)


window.protocol("WM_DELETE_WINDOW", cerrar)  
dibujar()                             # Arranca el dibujo periódico
window.mainloop()                     # Mantiene la ventana abierta esperando clics