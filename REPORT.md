# REPORT — Disparador

Informe técnico de la fusión de **Alarma** + **Continua terminales** en una sola
aplicación de escritorio.

## 1. Origen

| Herramienta | Stack | Qué hacía |
|-------------|-------|-----------|
| **Alarma** (`proyecto_alarma 1.2`) | Python + tkinter + pygame | Lista de alarmas con hora de inicio/fin; elegía una **hora de disparo aleatoria** dentro del rango; al saltar reproducía un `.wav`, mostraba un aviso y **ejecutaba un programa** o abría un archivo/URL. |
| **Continua terminales** | PowerShell + WPF | A una **hora fija**, enfocaba todas las ventanas que casaban un filtro de título y tecleaba un texto + **Enter** (reanudar Claude al reset de uso). |

## 2. Modelo fusionado

Se unifican en un **programador de tareas** donde cada entrada cruza dos ejes
independientes:

- **Cuándo** — `fixed` (hora `HH:MM`) o `random` (instante al azar en `[desde, hasta]`),
  con `daily` para reprogramarse cada día.
- **Qué** — `terminal` (teclear texto + Enter en ventanas que casen un filtro) o
  `program` (ejecutar programa / abrir archivo o URL).
- **Extras** — `sound` y `popup` (aviso con mensaje).

Resultado: continua-terminales **gana** la hora aleatoria y Alarma **gana** la acción de
escribir en terminales. Cualquier combinación es válida (p. ej. abrir una URL a una hora
aleatoria, o teclear `continua` en las terminales a hora fija).

## 3. Intervalo aleatorio: antitrazabilidad

El disparo a hora aleatoria dentro de un rango es una función de **antitrazabilidad**,
no un mero adorno:

- Una tarea que abre siempre una web o lanza un programa a la **misma hora exacta** crea
  un **patrón horario predecible**. Un observador (del tráfico de red o del sistema) puede
  anticipar *cuándo* ocurrirá la conexión y **correlacionarla** con el usuario.
- Al **aleatorizar** la hora dentro de una ventana amplia, el instante concreto deja de
  ser predecible en cada ejecución: desaparece la **firma horaria** y se rompe la
  correlación "hora conocida → web/programa concreto".
- Con *Repetir cada día*, el azar se **recalcula** en cada jornada, de modo que el patrón
  tampoco se estabiliza entre días.

Implementación: `compute_next()` toma la ventana `[inicio, fin]` del día (soportando
ventanas que cruzan medianoche), descarta la parte ya pasada, y elige
`inicio + random(0, segundos_restantes)`.

## 4. Decisiones técnicas

- **Base Python/tkinter** (la de Alarma) por ser multiplataforma; era un deseo previo del
  proyecto Alarma (portar a Linux, menos dependencias y archivos).
- **Cero dependencias pip.** Se eliminó `pygame`: el sonido usa `winsound` (Windows),
  `afplay` (macOS) o `aplay`/`paplay` (Linux).
- **Tecleo en ventanas sin librerías externas:**
  - *Windows*: `ctypes` sobre `user32`/`kernel32`. Enumeración con `EnumWindows`, enfoque
    real con el truco `AttachThreadInput` + `SetForegroundWindow` (salta el bloqueo de foco
    de Windows), y tecleo con `SendInput` usando `KEYEVENTF_UNICODE` (texto literal, sin
    mapas de teclado) + `VK_RETURN`.
  - *Linux (X11)*: `xdotool search --name` + `windowactivate` + `type` + `key Return`.
- **Disparo en hilo aparte.** La acción (sonido + tecleo/programa) corre en un
  `threading.Thread` para no congelar la interfaz; el aviso emergente se muestra **después**
  del tecleo para no robar el foco a las terminales.
- **Persistencia** en `alarms.json` con el próximo disparo (`next_fire`) ya calculado;
  al arrancar se recalculan los disparos cuya hora ya pasó.

## 5. Limitaciones conocidas

- La ventana debe permanecer **abierta** para disparar (no es un servicio). Para disparo
  persistente, crear una Tarea Programada (Windows) o un `.timer`/cron (Linux) que lance
  el script.
- En **Wayland**, el tecleo en ventanas ajenas puede estar restringido por el compositor.
- El tecleo Unicode omite caracteres fuera del BMP (irrelevante para comandos típicos).

## 6. Estructura

```
disparador.py        aplicación (GUI + scheduler + acciones)
disparador.cmd       lanzador sin consola (Windows)
alarm_sound.wav      sonido de disparo
alarm.ico            icono
alarms.json          tareas guardadas (no versionado)
```
