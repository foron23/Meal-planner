"""
Memory and preferences handler for the Meal Planner Bot.

Handles the /preferences and /clear commands for managing user memory.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def preferences_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /preferences command.
    
    Shows current user preferences and allows modification.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    user = update.effective_user
    if not user or not update.message:
        return
    
    # Get the SQLite store from context
    db_store = context.application.bot_data.get("db_store")
    
    if not db_store:
        await update.message.reply_text(
            "⚠️ El servicio no está disponible. Intenta más tarde."
        )
        return
    
    try:
        # Get user preferences
        preferences = db_store.get_user_preferences(user.id)
        
        if preferences and preferences.has_preferences():
            text = "📋 **Tus preferencias actuales:**\n\n"
            text += preferences.to_display_text()
            text += "\n\n💡 _Puedes actualizar tus preferencias simplemente diciéndome tus nuevos gustos en la conversación._"
            text += "\n\nPara **borrar todas las preferencias**, usa `/clear_preferences`."
        else:
            text = """📋 **No tienes preferencias guardadas todavía.**

Puedo aprender tus gustos mientras conversamos. Por ejemplo, dime:
• "Soy vegetariano"
• "Tengo alergia a los frutos secos"
• "Prefiero cocina mediterránea"
• "Somos 4 en casa"
• "Tengo poco tiempo para cocinar"

¡Y lo recordaré para futuras recomendaciones! 🧠"""
        
        await update.message.reply_text(text, parse_mode="Markdown")
        logger.info(f"Showed preferences for user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to get preferences for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Error al obtener tus preferencias. Intenta de nuevo."
        )


async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /clear command.
    
    Clears the conversation history for the user.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    user = update.effective_user
    if not user or not update.message:
        return
    
    # Get the agent from context
    agent = context.application.bot_data.get("agent")
    
    if agent:
        try:
            agent.clear_conversation(user.id)
            await update.message.reply_text(
                "🧹 ¡Historial de conversación limpiado!\n\n"
                "Empezamos de nuevo. ¿En qué puedo ayudarte?"
            )
            logger.info(f"Cleared conversation for user {user.id}")
        except Exception as e:
            logger.error(f"Failed to clear conversation for user {user.id}: {e}")
            await update.message.reply_text(
                "❌ Error al limpiar el historial. Intenta de nuevo."
            )
    else:
        await update.message.reply_text(
            "⚠️ El servicio no está disponible. Intenta más tarde."
        )


async def clear_preferences_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /clear_preferences command.
    
    Resets all user preferences to defaults.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    user = update.effective_user
    if not user or not update.message:
        return
    
    # Get the SQLite store from context
    db_store = context.application.bot_data.get("db_store")
    
    if not db_store:
        await update.message.reply_text(
            "⚠️ El servicio no está disponible. Intenta más tarde."
        )
        return
    
    try:
        success = db_store.clear_user_preferences(user.id)
        
        if success:
            await update.message.reply_text(
                "🗑️ **Preferencias borradas.**\n\n"
                "He olvidado todas tus preferencias anteriores. "
                "Puedes empezar a contarme tus nuevos gustos cuando quieras."
            )
            logger.info(f"Cleared preferences for user {user.id}")
        else:
            await update.message.reply_text(
                "ℹ️ No había preferencias que borrar."
            )
            
    except Exception as e:
        logger.error(f"Failed to clear preferences for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Error al borrar preferencias. Intenta de nuevo."
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /help command.
    
    Shows detailed help information about the bot.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    if not update.message:
        return
    
    help_text = """
🍽️ **Bot de Planificación de Menús - Ayuda**

**Comandos disponibles:**

• `/start` - Iniciar el bot y ver bienvenida
• `/menu [descripción]` - Generar un menú
• `/preferences` - Ver tus preferencias guardadas
• `/clear` - Limpiar historial de conversación
• `/clear_preferences` - Borrar todas tus preferencias
• `/help` - Ver esta ayuda

**¿Cómo usar el bot?**

1️⃣ **Conversa naturalmente**: Simplemente escríbeme lo que necesitas.
   Ejemplo: "Necesito ideas para una cena romántica"

2️⃣ **Cuéntame tus preferencias**: Te las recordaré automáticamente.
   Ejemplo: "Soy vegetariano y tengo alergia al gluten"

3️⃣ **Pide menús específicos**: Puedo adaptar las recetas.
   Ejemplo: "Menú semanal para 4 personas con presupuesto bajo"

**Tipos de menús que puedo crear:**
• Menús diarios o semanales
• Desayunos, almuerzos, cenas y snacks
• Recetas rápidas o elaboradas
• Comida para eventos especiales
• Menús para dietas específicas

**💡 Consejo:** Mientras más me cuentes sobre tus gustos, 
mejores serán mis recomendaciones.

¿En qué puedo ayudarte hoy? 🧑‍🍳
"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")