import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")

# Validar variables obligatorias
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("ERROR: La variable de entorno TELEGRAM_BOT_TOKEN es obligatoria. Por favor, configúrala en tu archivo .env.")

if not OPENROUTER_API_KEY:
    raise ValueError("ERROR: La variable de entorno OPENROUTER_API_KEY es obligatoria. Por favor, configúrala en tu archivo .env.")

# Cargar IDs de usuario permitidos (opcional, para privacidad)
allowed_ids_raw = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_TELEGRAM_USER_IDS = []
if allowed_ids_raw:
    try:
        ALLOWED_TELEGRAM_USER_IDS = [int(uid.strip()) for uid in allowed_ids_raw.split(",") if uid.strip()]
    except ValueError:
        print("Advertencia: ALLOWED_TELEGRAM_USER_IDS tiene un formato inválido en .env. Debe ser una lista de números separados por comas.")

# Ruta de la base de datos local
DB_PATH = BASE_DIR / "asistente_memoria.db"

# Ruta para reportes temporales
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
