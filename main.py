import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ChatAction

# Importar configuraciones locales
from src.config import TELEGRAM_BOT_TOKEN, ALLOWED_TELEGRAM_USER_IDS
import src.db as db
import src.ai as ai

# Configuración de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejador para el comando /start."""
    user = update.effective_user
    user_id = user.id
    
    # Validar permisos
    if ALLOWED_TELEGRAM_USER_IDS and user_id not in ALLOWED_TELEGRAM_USER_IDS:
        logger.warning(f"Intento de acceso no autorizado por ID: {user_id} (@{user.username})")
        await update.message.reply_text("⛔ Acceso denegado. Este asistente de IA es privado.")
        return

    welcome_text = (
        f"👋 ¡Hola {user.first_name}! Bienvenido a tu **Asistente de IA Privado 24/7** (Versión 3).\n\n"
        "Estoy listo para ayudarte localmente en tus tareas diarias:\n"
        "💵 **Finanzas Personales**: Registra tus gastos e ingresos en lenguaje natural (ej. *'gasté 25 en comida'* o *'recibí 1500 por trabajo'*), "
        "o pídeme reportes financieros (*'dame mi reporte financiero'*).\n"
        "📅 **Agenda Personal**: Agrega eventos bloqueantes (*'reunión mañana a las 10:00'*), consulta tu agenda (*'¿qué tengo hoy?'*) y "
        "recibe notificaciones automáticas minutos antes de que comiencen.\n"
        "🌐 **Búsqueda Web**: Pregúntame sobre cualquier noticia y buscaré en internet.\n\n"
        "📊 **Panel de Control**: Accede a tu dashboard Glassmorphism en `http://localhost:5050`.\n\n"
        "Todos tus datos se guardan estrictamente en tu dispositivo host local."
    )
    
    # Inicializar el chat en la base de datos de memoria si es necesario
    await asyncio.to_thread(db.add_chat_message, user_id, "assistant", "Asistente inicializado.")
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa los mensajes de texto del usuario pasándolos por el agente de IA."""
    user = update.effective_user
    user_id = user.id
    user_message = update.message.text
    
    # Validar permisos
    if ALLOWED_TELEGRAM_USER_IDS and user_id not in ALLOWED_TELEGRAM_USER_IDS:
        logger.warning(f"Mensaje ignorado de usuario no autorizado: {user_id} (@{user.username})")
        await update.message.reply_text("⛔ Acceso denegado. Este asistente de IA es privado.")
        return

    # Mostrar que el bot está escribiendo/procesando
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        # Guardar mensaje del usuario en la base de datos (Ejecutado en hilo para no bloquear el loop)
        await asyncio.to_thread(db.add_chat_message, user_id, "user", user_message)
        
        # Procesar con IA usando OpenRouter (Ejecutado en hilo para llamadas de red bloqueantes)
        final_text, side_effects = await asyncio.to_thread(ai.process_message_with_ai, user_id, user_message)
        
        # Guardar respuesta del asistente en la base de datos
        await asyncio.to_thread(db.add_chat_message, user_id, "assistant", final_text)
        
        # Enviar respuesta textual al usuario
        await update.message.reply_text(final_text, parse_mode="Markdown")
        
        # Procesar efectos secundarios (como enviar reportes en Excel o imágenes de gráficos)
        for effect in side_effects:
            action = effect.get("action")
            file_path = Path(effect.get("file_path", ""))
            
            if not file_path.exists():
                logger.error(f"Error: El archivo para el efecto '{action}' no existe en {file_path}")
                continue
                
            if action == "send_document":
                # Mostrar que el bot está subiendo el archivo
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                with open(file_path, "rb") as doc_file:
                    await update.message.reply_document(
                        document=doc_file,
                        filename=file_path.name,
                        caption="📊 Aquí tienes tu reporte financiero detallado en Excel."
                    )
                logger.info(f"Reporte Excel enviado con éxito al usuario {user_id}: {file_path.name}")
                
            elif action == "send_photo":
                # Mostrar que el bot está subiendo la imagen
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
                with open(file_path, "rb") as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption=effect.get("caption", ""),
                        parse_mode="Markdown"
                    )
                logger.info(f"Imagen visual enviada con éxito al usuario {user_id}: {file_path.name}")
                    
    except Exception as e:
        logger.exception("Error al procesar el mensaje del usuario")
        await update.message.reply_text(
            f"❌ Lo siento, ocurrió un error al procesar tu solicitud.\nDetalle: `{str(e)}`",
            parse_mode="Markdown"
        )

# --- WORKER DE RECORDATORIOS EN SEGUNDO PLANO ---

def check_pending_events_in_db() -> list:
    """
    Busca eventos en la base de datos SQLite que estén programados para comenzar
    en los próximos 15 minutos y que aún no hayan sido notificados.
    """
    now = datetime.now()
    upper_bound = now + timedelta(minutes=15)
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Obtener eventos no notificados
    cursor.execute("SELECT id, title, start_time FROM calendar WHERE notified = 0")
    rows = cursor.fetchall()
    
    events_to_notify = []
    for row in rows:
        try:
            event_time = datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M")
            # Si el evento empieza en los próximos 15 minutos y no es del pasado lejano (> 5 min de retraso)
            if now - timedelta(minutes=5) <= event_time <= upper_bound:
                minutes_left = int((event_time - now).total_seconds() / 60)
                events_to_notify.append({
                    "id": row["id"],
                    "title": row["title"],
                    "start_time": row["start_time"],
                    "minutes_left": minutes_left
                })
            elif event_time < now - timedelta(minutes=5):
                # Descartar eventos lejanos en el pasado sin notificar para evitar spam en el arranque
                cursor.execute("UPDATE calendar SET notified = 1 WHERE id = ?", (row["id"],))
        except Exception as e:
            logger.error(f"Error procesando la fecha del evento {row['id']}: {e}")
            
    conn.commit()
    conn.close()
    return events_to_notify

def mark_event_as_notified(event_id: int):
    """Marca un evento en la base de datos como notificado."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE calendar SET notified = 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

async def reminder_worker(application):
    """Loop infinito que revisa periódicamente si hay recordatorios pendientes."""
    logger.info("Iniciando trabajador de recordatorios en segundo plano...")
    # Esperar un momento a que el bot termine de arrancar completamente
    await asyncio.sleep(5)
    
    while True:
        try:
            # Consultar eventos pendientes en un hilo de trabajo
            events = await asyncio.to_thread(check_pending_events_in_db)
            
            for event in events:
                title = event["title"]
                start_time_str = event["start_time"]
                minutes_left = event["minutes_left"]
                event_id = event["id"]
                
                # Formatear hora de inicio
                time_only = start_time_str.split(" ")[1]
                
                # Enviar notificación a todos los usuarios autorizados
                for user_id in ALLOWED_TELEGRAM_USER_IDS:
                    try:
                        if minutes_left <= 0:
                            message = f"⏰ *¡EVENTO EMPEZANDO AHORA!*\n\nTu evento *'{title}'* programado para hoy a las {time_only} acaba de comenzar."
                        else:
                            message = f"⏰ *RECORDATORIO DE AGENDA*\n\nTu evento *'{title}'* está por comenzar en {minutes_left} minutos (a las {time_only})."
                        
                        await application.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode="Markdown"
                        )
                        logger.info(f"Notificación de evento {event_id} enviada exitosamente a {user_id}.")
                    except Exception as send_err:
                        logger.error(f"Error al enviar mensaje de recordatorio a {user_id}: {send_err}")
                
                # Marcar evento como notificado en la BD
                await asyncio.to_thread(mark_event_as_notified, event_id)
                
        except Exception as e:
            logger.error(f"Error en el ciclo del reminder_worker: {e}")
            
        # Esperar 60 segundos antes de la siguiente comprobación
        await asyncio.sleep(60)

async def auto_restart_worker():
    """
    Temporizador asíncrono que apaga el bot tras 2 horas (7200 segundos) 
    de ejecución para permitir que el demonio de start.sh actualice el código.
    """
    logger.info("Iniciando temporizador de auto-reinicio de 2 horas...")
    await asyncio.sleep(7200)
    logger.info("Auto-reinicio: Apagando proceso para buscar actualizaciones...")
    import os
    os._exit(0)

async def post_init(application):
    """Inicialización asíncrona tras arrancar el bot de Telegram."""
    asyncio.create_task(reminder_worker(application))
    asyncio.create_task(auto_restart_worker())

def main():
    """Punto de entrada para inicializar y arrancar el bot de Telegram y el servidor web."""
    logger.info("Inicializando base de datos local...")
    db.init_db()
    logger.info("Base de datos lista.")

    logger.info("Iniciando servidor web del Panel de Control en el puerto 5050...")
    import threading
    from src.web import run_server
    web_thread = threading.Thread(target=run_server, kwargs={"host": "0.0.0.0", "port": 5050}, daemon=True)
    web_thread.start()
    logger.info("Servidor web listo en http://0.0.0.0:5050")

    logger.info("Iniciando aplicación de Telegram Bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    # Registrar manejadores
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    logger.info("Bot en ejecución. Presiona Ctrl+C para detener.")
    # Iniciar modo Long Polling
    app.run_polling()

if __name__ == "__main__":
    main()
