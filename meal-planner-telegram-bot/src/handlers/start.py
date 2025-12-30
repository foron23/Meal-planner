"""
Start command handler for the Meal Planner Bot.

Handles the /start command to welcome new users and provide instructions.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


WELCOME_MESSAGE = """
👋 ¡Hola {name}! Bienvenido al **Bot de Planificación de Menús** 🍽️

Soy tu asistente personal para ayudarte a planificar tus comidas. Puedo:

🥗 **Proponer menús personalizados** según tus preferencias
🍳 **Recordar tus gustos** y restricciones dietéticas
⏱️ **Adaptar recetas** a tu tiempo disponible
💰 **Ajustar sugerencias** a tu presupuesto

**Comandos disponibles:**
• `/menu` - Solicitar un menú nuevo
• `/preferences` - Ver/editar tus preferencias
• `/help` - Ver ayuda detallada
• `/clear` - Limpiar historial de conversación

**¿Cómo empezar?**
Simplemente escríbeme qué tipo de menú necesitas. Por ejemplo:
- "Necesito ideas para una cena vegetariana"
- "Menú semanal para 4 personas con poco tiempo"
- "Recetas sin gluten fáciles de preparar"

¡Cuéntame, ¿qué te gustaría cocinar hoy? 🧑‍🍳
"""


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /start command.
    
    Creates a new user record if necessary and sends a welcome message.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    user = update.effective_user
    if not user:
        logger.warning("Received /start command without effective_user")
        return
    
    # Get the SQLite store from context
    db_store = context.application.bot_data.get("db_store")
    
    if db_store:
        try:
            # Create or update user in database
            db_store.get_or_create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name or "Usuario",
                last_name=user.last_name,
                language_code=user.language_code or "es",
            )
            logger.info(f"User {user.id} ({user.username}) started the bot")
        except Exception as e:
            logger.error(f"Failed to create/update user: {e}")
    
    # Send welcome message
    welcome_text = WELCOME_MESSAGE.format(name=user.first_name or "Usuario")
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
    )