# Priorityly

Aplicación de escritorio para gestión y priorización de tareas basada en la **Matriz de Eisenhower**. Organiza tus tareas según importancia y urgencia, y refina prioridades mediante comparaciones por pares.

---

## Características

- **Matriz de Eisenhower visual** — Cuadrícula 2×2 con código de colores por cuadrante
- **Lista priorizada** — Tareas ordenadas por puntuación (importancia + urgencia + peso de cuadrante)
- **Comparación por pares** — Asistente interactivo para afinar prioridades enfrentando tareas de dos en dos
- **Tareas jerárquicas** — Soporte para tareas padre e hijos (subtareas)
- **Persistencia local** — Almacenamiento automático en JSON en el directorio del usuario
- **Sin dependencias externas** — Usa únicamente la librería estándar de Python

## Cuadrantes de la Matriz de Eisenhower

| Cuadrante | Nombre | Condición | Color |
|-----------|--------|-----------|-------|
| Q1 | Hacer ya | Importancia ≥ 6 y Urgencia ≥ 6 | Rojo |
| Q2 | Planificar | Importancia ≥ 6 y Urgencia < 6 | Azul |
| Q3 | Delegar | Importancia < 6 y Urgencia ≥ 6 | Naranja |
| Q4 | Eliminar | Importancia < 6 y Urgencia < 6 | Gris |

## Requisitos

- Python 3.9 o superior
- Tkinter (incluido en la instalación estándar de CPython)

> En algunas distribuciones de Linux puede ser necesario instalar Tkinter por separado:
> ```bash
> sudo apt install python3-tk   # Debian/Ubuntu
> sudo dnf install python3-tkinter  # Fedora
> ```

## Instalación y uso

```bash
# Clonar el repositorio
git clone <url-del-repositorio>
cd priorityly

# Ejecutar la aplicación
python main.py
```

No se requiere ningún paso de instalación adicional.

## Estructura del proyecto

```
priorityly/
├── main.py          # Punto de entrada
├── requirements.txt # Sin dependencias de terceros
└── src/
    ├── app.py       # Aplicación principal (ventana Tkinter)
    ├── models.py    # Modelo de tarea y lógica de cuadrantes
    ├── priority.py  # Motor de comparación por pares
    └── storage.py   # Capa de persistencia JSON
```

## Datos

Las tareas se guardan automáticamente en:

```
~/.priorityly/tasks.json
```

El archivo se crea en el primer guardado y se actualiza tras cada cambio.

## Cómo funciona la puntuación

Cada tarea tiene valores de **importancia** (1–10) y **urgencia** (1–10). La puntuación final para ordenar las tareas es:

```
puntuación = peso_cuadrante + importancia + urgencia

Pesos: Q1=1000, Q2=100, Q3=10, Q4=0
```

Esto garantiza que las tareas Q1 siempre aparecen primero, seguidas de Q2, Q3 y Q4.

### Comparación por pares

El asistente de comparación genera todos los pares posibles entre tareas y pregunta cuál es más importante y cuál más urgente. Cada victoria ajusta la puntuación ±1.2 puntos (acotado a [1, 10]).

## Licencia

Este proyecto no incluye licencia explícita. Todos los derechos reservados al autor.
