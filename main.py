import logging
import asyncio
from pathlib import Path
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
        f"👋 ¡Hola {user.first_name}! Bienvenido a tu **Asistente de IA Privado 24/7**.\n\n"
        "Estoy listo para ayudarte localmente en tres áreas clave:\n"
        "💵 **Finanzas Personales**: Registra tus gastos en lenguaje natural (ej. *'gasté 25 en transporte'*) o "
        "pídeme reportes en Excel (*'genera un reporte de mis gastos'*).\n"
        "📅 **Agenda Personal**: Consulta disponibilidad (*'¿qué tengo programado hoy?'*) o "
        "agenda eventos (*'reunión de trabajo mañana a las 11:00'*).\n"
        "🌐 **Búsqueda Web**: Pregúntame sobre cualquier noticia o hecho actual y buscaré en internet.\n\n"
        "📊 **Panel de Control**: También puedes visualizar tu actividad y estado en tiempo real en tu navegador web ingresando a `http://localhost:5050` (o a la IP de tu dispositivo).\n\n"
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
        
        # Procesar efectos secundarios (como enviar el reporte Excel generado)
        for effect in side_effects:
            if effect.get("action") == "send_document":
                file_path = Path(effect.get("file_path"))
                if file_path.exists():
                    # Mostrar que el bot está subiendo el archivo
                    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT)
                    # Abrir y enviar el documento de manera segura
                    with open(file_path, "rb") as doc_file:
                        await update.message.reply_document(
                            document=doc_file,
                            filename=file_path.name,
                            caption="📊 Aquí tienes tu reporte estructurado de gastos en Excel."
                        )
                    logger.info(f"Reporte enviado con éxito al usuario {user_id}: {file_path.name}")
                else:
                    logger.error(f"Error: El archivo del reporte no existe en la ruta: {file_path}")
                    await update.message.reply_text("⚠️ Ocurrió un problema interno al intentar recuperar el archivo Excel del reporte.")
                    
    except Exception as e:
        logger.exception("Error al procesar el mensaje del usuario")
        await update.message.reply_text(
            f"❌ Lo siento, ocurrió un error al procesar tu solicitud.\nDetalle: `{str(e)}`",
            parse_mode="Markdown"
        )

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
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registrar manejadores
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    logger.info("Bot en ejecución. Presiona Ctrl+C para detener.")
    # Iniciar modo Long Polling
    app.run_polling()

if __name__ == "__main__":
    main()
