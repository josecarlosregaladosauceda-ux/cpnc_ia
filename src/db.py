import sqlite3
from datetime import datetime
from src.config import DB_PATH

def get_connection():
    """Retorna una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    # Habilitar retorno de filas como diccionarios
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabla para memoria de corto plazo (historial de chat)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla para registro de gastos (módulo financiero)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                concept TEXT NOT NULL,
                amount REAL NOT NULL,
                date_added DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla para agenda y calendario (módulo de agenda)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL, -- Formato: YYYY-MM-DD HH:MM
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# --- MÉTODOS DE MEMORIA DE CHAT ---

def add_chat_message(user_id: int, role: str, content: str):
    """Inserta un mensaje de chat (usuario o asistente) en la base de datos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_memory (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        conn.commit()

def get_chat_history(user_id: int, limit: int = 15) -> list:
    """
    Obtiene los últimos 'limit' mensajes de un usuario en orden cronológico.
    Retorna una lista de diccionarios con las llaves 'role' y 'content'.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # Obtener los últimos mensajes ordenados por ID descendente
        cursor.execute(
            "SELECT role, content FROM chat_memory WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        # Revertir el orden para que sea cronológico (el más antiguo primero)
        history = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        return history

# --- MÉTODOS DE MÓDULO FINANCIERO ---

def add_expense(category: str, concept: str, amount: float) -> str:
    """
    Registra un gasto en la base de datos.
    Normaliza la categoría a minúsculas y elimina espacios extras.
    """
    clean_category = category.strip().lower()
    clean_concept = concept.strip()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (category, concept, amount) VALUES (?, ?, ?)",
            (clean_category, clean_concept, float(amount))
        )
        conn.commit()
        
    return f"Gasto registrado con éxito: {clean_concept} (${amount:.2f}) en la categoría '{clean_category}'."

def search_expenses(keyword: str) -> list:
    """
    Busca gastos utilizando similitud (LIKE) en el concepto o la categoría.
    Retorna una lista de diccionarios con el detalle de las transacciones.
    """
    query_param = f"%{keyword.strip()}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT date_added, category, concept, amount 
            FROM expenses 
            WHERE concept LIKE ? OR category LIKE ? 
            ORDER BY date_added DESC
            """,
            (query_param, query_param)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_all_expenses() -> list:
    """Retorna todos los gastos registrados en la base de datos."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category, concept, amount, date_added FROM expenses ORDER BY date_added ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

# --- MÉTODOS DE MÓDULO DE AGENDA ---

def add_calendar_event(title: str, start_time: str) -> str:
    """
    Inserta un evento bloqueante en el calendario.
    Valida estrictamente que start_time cumpla con el formato YYYY-MM-DD HH:MM.
    """
    start_time_clean = start_time.strip()
    
    # Validación estricta del formato
    try:
        datetime.strptime(start_time_clean, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError("El formato de fecha y hora es inválido. Debe ser estrictamente YYYY-MM-DD HH:MM (ej: 2026-05-22 15:30).")
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calendar (title, start_time) VALUES (?, ?)",
            (title.strip(), start_time_clean)
        )
        conn.commit()
        
    return f"Evento agendado con éxito: '{title}' programado para el {start_time_clean}."

def check_availability(date_str: str) -> list:
    """
    Consulta los eventos de la agenda programados para una fecha específica (YYYY-MM-DD).
    Retorna una lista de diccionarios con los eventos correspondientes.
    """
    date_clean = date_str.strip()
    # Asegurar formato básico YYYY-MM-DD
    try:
        # Validar si el string coincide con YYYY-MM-DD
        datetime.strptime(date_clean, "%Y-%m-%d")
    except ValueError:
        raise ValueError("La fecha debe estar en formato YYYY-MM-DD (ej: 2026-05-22).")
        
    query_param = f"{date_clean}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, start_time FROM calendar WHERE start_time LIKE ? ORDER BY start_time ASC",
            (query_param,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
