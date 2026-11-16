from tkinter import *                 
import serial                   
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  
import threading      
import random                
device = 'COM5'                       
ser = serial.Serial(device, baudrate=9600, timeout=1)  # Abre el puerto a 9600 baudios y espera máximo 1 segundo al leer.
leyendo = False                      
temperaturas = []                  
humedades = []                   
eje_x = []                           
i = 0                                 

def recepcion ():                     
     global i
     while True:                     
      if leyendo and ser.in_waiting > 0:            
       linea = ser.readline().decode('utf-8').rstrip()    # Si está activada la lectura y hay datos esperando, lee una línea, la pasa a texto y quita saltos finales
       print(linea)                                
       try:                                        
           partes = linea.split(':')              
           temperatura = float(partes[1])
           humedad = float(partes[3]) 
       except (IndexError, ValueError): # Si la línea llega defectuosa, se ignora.
           continue
       eje_x.append(i)                               
       temperaturas.append(temperatura)      #Añade al listado de temperaturas y humedades los últimos valores leídos.         
       humedades.append(humedad)                  
       i = i + 1                                     

def dibujar ():                      
    n = len(humedades)                           # Mismo número de datos en X y en Y
    linea_temp.set_data(eje_x[:n], temperaturas[:n]) # Actualiza la línea con todos los datos
    linea_hum.set_data(eje_x[:n], humedades[:n]) 
    ax.set_xlim(max(0, i - 100), max(100, i))        
    ax.set_title(str(i))                            
    canvas.draw_idle()  # Redibuja la gráfica incrustada
    window.after(500, dibujar)                     

def IClick ():                        
    print ('Iniciando')
    global leyendo                   
    leyendo = True                   
    threadRecepcion = threading.Thread (target = recepcion, daemon = True)  # daemon=True para que el programa termine al cerrar la ventana
    threadRecepcion.start()          
    mensaje = "Reanudar"
    ser.write(mensaje.encode('utf-8')) 
    

def PClick ():                       
    print ('Parar')
    global leyendo
    leyendo = False  # Desactiva la lectura (no imprime datos)
    mensaje = "Parar"
    ser.write(mensaje.encode('utf-8'))   #Envia el mensaje de detener la comunicación al transmisor

def RClick ():                       
    global leyendo
    leyendo = True  # Vuelve a activar la lectura
    print ('Reanudar')
    mensaje = "Reanudar"
    ser.write(mensaje.encode('utf-8'))  

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

fondo = Canvas(window, bg="#0B1A2E", highlightthickness=0)
fondo.place(x=0, y=0, relwidth=1, relheight=1)
for _ in range(150): #Bucle con el que simulamos las estrellas
    x = random.randint(0, 1200)
    y = random.randint(0, 800)
    fondo.create_oval(x, y, x + 2, y + 2, fill="white", outline="")
fondo.create_text(600, 40, text="TEMPERATURA", fill="white", font=("Helvetica", 20, "italic", "bold")) #El texto "TEMPERATURA" está escrito en el fondo, no como fila de independiente



# La gráfica dentro de la ventana
fig = Figure(figsize=(6, 3))          
ax = fig.add_subplot(111)            
ax.set_xlim(0, 100)                
ax.set_ylim(20, 40)  
ax.set_ylabel("Temperatura (°C)", color="red")   
linea_temp, = ax.plot([], [], color="red")      
ax2 = ax.twinx()                                 
ax2.set_ylim(0, 100)                             
ax2.set_ylabel("Humedad (%)", color="blue")      
linea_hum, = ax2.plot([], [], color="blue")      
                           

canvas = FigureCanvasTkAgg(fig, master=window)  # Conecta la figura con la ventana de Tkinter
canvas.get_tk_widget().grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky=N + S + E + W)  


IniciarButton = Button(window, text="INICIAR", bg="white", fg="#0B1A2E", width=15, height=2, font=("Helvetica", 20, "italic", "bold"), command=IClick)
IniciarButton.grid(row=2, column=0)
PararButton = Button(window, text="PARAR", bg="white", fg="#0B1A2E", width=15, height=2, font=("Helvetica", 20, "italic", "bold"), command=PClick)
PararButton.grid(row=2, column=1)
ReanudarButton = Button(window, text="REANUDAR", bg="white", fg="#0B1A2E", width=15, height=2, font=("Helvetica", 20, "italic", "bold"), command=RClick)
ReanudarButton.grid(row=2, column=2)


window.protocol("WM_DELETE_WINDOW", cerrar)  
dibujar()      # Inicia el dibujo periódico
window.mainloop()     # Mantiene la ventana abierta