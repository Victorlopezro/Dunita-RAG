# Guía de instalación en Windows sin Docker

Esta guía permite ejecutar **rag-rack** completamente en Windows **sin permisos de administrador** y sin Docker.

---

## Resumen de lo que se instala

| Componente | Cómo se instala | ¿Requiere admin? |
|---|---|---|
| **Ollama** (runtime del LLM) | Instalador `.exe` en carpeta de usuario | **No** |
| **Qdrant** (base vectorial) | Binario portable `.zip`, sin instalación | **No** |
| **Python 3.11** | Instalador con opción "solo para este usuario" | **No** |
| **Dependencias Python** | `pip install` en entorno de usuario | **No** |

---

## Requisitos previos

- Windows 10 (versión 22H2 o más reciente) o Windows 11
- Conexión a internet para descargar modelos (~5 GB la primera vez)
- Al menos 16 GB de RAM y 20 GB de espacio libre en disco

---

## Paso 1 — Preparar el proyecto

Descarga y descomprime el archivo `rag-rack.zip` en una carpeta de tu elección, por ejemplo:

```
C:\Users\TuNombre\rag-rack\
```

Abre **PowerShell** (no hace falta "como administrador") y navega a esa carpeta:

```powershell
cd C:\Users\TuNombre\rag-rack
```

---

## Paso 2 — Copiar el .env para Windows

```powershell
copy .env.windows .env
```

Esto configura el sistema para usar `localhost` en lugar de los nombres de contenedor Docker.

---

## Paso 3 — Instalar Python (si no lo tienes)

Descarga el instalador desde:

> **https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe**

Durante la instalación:

1. Marca **"Add Python to PATH"** (casilla en la parte inferior).
2. Haz clic en **"Install Now"** — si pide admin, haz clic en **"Install for current user only"** (no requiere admin).

Verifica que funciona abriendo una nueva PowerShell:

```powershell
python --version
# Debe mostrar: Python 3.11.x
```

---

## Paso 4 — Instalar Ollama

Descarga el instalador desde:

> **https://ollama.com/download/OllamaSetup.exe**

Ejecuta el instalador. **No pide permisos de administrador** — se instala en tu carpeta de usuario (`%LOCALAPPDATA%\Programs\Ollama`).

Una vez instalado, Ollama aparecerá en la **bandeja del sistema** (esquina inferior derecha). Debe estar corriendo antes de usar rag-rack.

---

## Paso 5 — Descargar Qdrant portable

Descarga el archivo ZIP desde:

> **https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-pc-windows-msvc.zip**

Descomprime el contenido dentro de la carpeta `bin\` del proyecto:

```
rag-rack\
└─ bin\
   └─ qdrant.exe   ← debe quedar aquí
```

---

## Paso 6 — Instalar dependencias Python

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\2_instalar_python_deps.ps1
```

Esto instala todas las librerías necesarias (Haystack, Qdrant client, SBERT, FastAPI, Streamlit, etc.).

> La primera vez puede tardar **3-5 minutos**.

---

## Paso 7 — Inicializar el sistema

Este paso arranca Qdrant, verifica Ollama, **descarga el modelo Qwen 2.5:7b** (~4.7 GB) y crea la colección vectorial:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\3_inicializar_sistema.ps1
```

> La descarga del modelo puede tardar **5-15 minutos** según tu conexión. Solo se hace una vez.

---

## Paso 8 — Arrancar el sistema

A partir de aquí, cada vez que quieras usar rag-rack ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\4_arrancar.ps1
```

Este script:
1. Arranca Qdrant (ventana minimizada).
2. Verifica que Ollama está corriendo.
3. Arranca la API FastAPI en una nueva ventana PowerShell.
4. Arranca el frontend Streamlit en otra ventana.
5. Abre el chatbot en el navegador automáticamente.

---

## Acceder al sistema

| Servicio | URL |
|---|---|
| **Chatbot** | http://localhost:8501 |
| **API (documentación)** | http://localhost:8000/docs |
| **Qdrant (panel web)** | http://localhost:6333/dashboard |

---

## Detener el sistema

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\5_detener.ps1
```

Para detener Ollama: clic derecho en su icono en la bandeja del sistema → **Quit**.

---

## Uso básico del chatbot

### Ingestar un repositorio GitHub

En la barra lateral del chatbot, introduce la URL del repositorio y haz clic en **"Ingestar repos"**:

```
https://github.com/usuario/repositorio
```

### Ingestar páginas web

En la barra lateral, introduce las URLs (una por línea) y haz clic en **"Ingestar webs"**.

### Hacer una consulta

Escribe tu pregunta en el campo de chat. La respuesta incluirá las fuentes exactas utilizadas.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `python` no reconocido | Reinstala Python marcando "Add to PATH" y abre una nueva PowerShell |
| `ollama` no reconocido | Cierra y vuelve a abrir PowerShell después de instalar Ollama |
| Qdrant no arranca | Verifica que `bin\qdrant.exe` existe; descárgalo del paso 5 |
| API no responde | Revisa la ventana de PowerShell de la API para ver el error |
| Modelo muy lento | Qwen 2.5:7b requiere ~8 GB RAM. Si tienes menos, usa `qwen2.5:3b` cambiando `OLLAMA_MODEL` en `.env` |
| Error de permisos en PowerShell | Ejecuta siempre con `-ExecutionPolicy Bypass` como se indica |

---

## Cambiar el modelo LLM

Si tu equipo tiene poca RAM, puedes usar un modelo más ligero. Edita el archivo `.env`:

```env
OLLAMA_MODEL=qwen2.5:3b
```

Y descarga el modelo:

```powershell
ollama pull qwen2.5:3b
```

| Modelo | RAM necesaria | Calidad |
|---|---|---|
| `qwen2.5:3b` | ~4 GB | Buena para pruebas |
| `qwen2.5:7b` | ~8 GB | Recomendado |
| `qwen2.5:14b` | ~16 GB | Alta calidad |
