import os
import sys
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not os.getenv("OPENAI_API_KEY"):
    logger.error("OPENAI_API_KEY no está configurada en las variables de entorno")
    sys.exit(1)

if not os.getenv("TELEGRAM_BOT_TOKEN"):
    logger.error("TELEGRAM_BOT_TOKEN no está configurado en las variables de entorno")
    sys.exit(1)

from agent.agent_main import run_agent

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start"""
    user = update.effective_user
    welcome_message = f"""
¡Hola {user.first_name}!

Soy un asistente conversacional impulsado por Gemini.
Puedo ayudarte con:
• Responder preguntas
• Proporcionar información
• Asistir con diversas tareas

Simplemente envíame un mensaje y te responderé.

Comandos disponibles:
/start - Muestra este mensaje
/help - Ayuda y información
"""
    await update.message.reply_text(welcome_message)
    logger.info(f"Usuario {user.id} ({user.first_name}) inició el bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /help"""
    help_message = """
  Ayuda del Bot

Puedes hacerme cualquier pregunta o pedirme ayuda con tareas.

Comandos:
/start - Mensaje de bienvenida
/help - Muestra esta ayuda

Simplemente escribe tu mensaje y te responderé.
"""
    await update.message.reply_text(help_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto del usuario"""
    user = update.effective_user
    user_message = update.message.text
    
    logger.info(f"Usuario {user.id} ({user.first_name}): {user_message}")
    
    try:
        await update.message.chat.send_action(action="typing")
        
        response = await run_agent(user_message)
        
        await update.message.reply_text(response)
        logger.info(f"Respuesta enviada a {user.id}")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        await update.message.reply_text(
            "Lo siento, ocurrió un error al procesar tu mensaje. "
            "Por favor, intenta de nuevo."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores del bot"""
    logger.error(f"Error en update: {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "Ocurrió un error inesperado. Por favor, intenta de nuevo más tarde."
        )

def main():
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error_handler)
    
    logger.info("Bot iniciado - Esperando mensajes...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
