# Sistema Satelital — Grupo 6

Somos **Ane, Jan y Mireia** y este es nuestro proyecto de Ciencias de la Computación (EETAC).

El sistema tiene dos partes:
- **Satélite**: Arduino con sensor DHT11 que envía temperatura y humedad.
- **Estación de tierra**: Arduino con pantalla LCD que recibe los datos y los pasa al PC, donde una interfaz en Python (Tkinter + matplotlib) los muestra en una gráfica.

## Estructura del repositorio

```
Version_1/
├── transmisor_def/
│   └── transmisor_def.ino        → Arduino del satélite
├── RECEPTOR_DEF/
│   └── RECEPTOR_DEF.ino          → Arduino de la estación de tierra (LCD)
├── Tierra_DEF.py                 → Interfaz gráfica en el PC
└── tests/                        → Tests unitarios
    ├── test_sensor/              → Prueba del sensor DHT11
    ├── transmisor_test/          → Prueba de envío por SoftwareSerial
    └── Receptor_test_unitario/   → Prueba de recepción por SoftwareSerial
```

> Cada `.ino` está dentro de una carpeta con su mismo nombre porque el IDE de Arduino lo exige para abrirlo.

## Cómo ponerlo en marcha

1. Cargar `transmisor_def.ino` en el Arduino del satélite.
2. Cargar `RECEPTOR_DEF.ino` en el Arduino de tierra.
3. En `Tierra_DEF.py`, cambiar `device = 'COM5'` por el puerto donde esté conectado el Arduino de tierra.
4. Ejecutar `python Tierra_DEF.py` (requiere `pyserial` y `matplotlib`).

## Versión 1

Vídeo explicativo de la versión 1:
https://drive.google.com/file/d/1DW6Z_8IgxookbccRerrv29M3-voX5HDI/view?usp=sharing
