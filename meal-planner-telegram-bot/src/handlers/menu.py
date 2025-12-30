"""
Menu handler for the Meal Planner Bot.

Handles menu requests via /menu command and natural language messages.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def menu_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /menu command.
    
    Generates a menu based on user preferences and any additional arguments.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    user = update.effective_user
    if not user or not update.message:
        return
    
    # Build the request message from command arguments
    args = context.args
    if args:
        request = " ".join(args)
    else:
        request = "Por favor, sugiere un menú para hoy basándote en mis preferencias."
    
    # Send typing indicator
    await update.message.chat.send_action("typing")
    
    # Get the agent from context
    agent = context.application.bot_data.get("agent")
    
    if not agent:
        await update.message.reply_text(
            "⚠️ Lo siento, el servicio no está disponible en este momento. "
            "Por favor, intenta más tarde."
        )
        return
    
    try:
        # Invoke the agent
        response = await agent.invoke(
            message=request,
            user_id=user.id,
        )
        
        # Send the response
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
        )
        
        logger.info(f"Generated menu for user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to generate menu for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Lo siento, ha ocurrido un error al generar el menú. "
            "Por favor, intenta de nuevo."
        )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle natural language messages for menu generation.
    
    This handler processes all text messages that are not commands.
    In group chats, it only responds when the bot is mentioned or replied to.
    
    Args:
        update: Telegram update containing the message
        context: Bot context with application data
    """
    # Log every call to this handler
    logger.info(f"message_handler called - chat_type: {update.effective_chat.type if update.effective_chat else 'None'}")
    
    user = update.effective_user
    message = update.message
    
    if not user or not message or not message.text:
        return
    
    user_message = message.text.strip()
    
    if not user_message:
        return
    
    # Check if this is a group chat
    chat_type = message.chat.type
    is_group = chat_type in ("group", "supergroup")
    
    if is_group:
        # In groups, only respond if:
        # 1. Bot is mentioned (@botname)
        # 2. Message is a reply to the bot's message
        # 3. Bot username is in the message
        
        bot_username = context.bot.username
        bot_mentioned = bot_username and f"@{bot_username}" in message.text
        
        # Check if this is a reply to the bot
        is_reply_to_bot = False
        if message.reply_to_message and message.reply_to_message.from_user:
            is_reply_to_bot = message.reply_to_message.from_user.id == context.bot.id
        
        if not bot_mentioned and not is_reply_to_bot:
            # Don't respond to messages not directed at the bot in groups
            return
        
        # Remove bot mention from message if present
        if bot_mentioned:
            user_message = user_message.replace(f"@{bot_username}", "").strip()
        
        logger.info(f"Group message for bot from user {user.id} in chat {message.chat.id}")
    else:
        logger.info(f"Private message from user {user.id}: '{user_message[:50]}...'")
    
    # Send typing indicator
    await message.chat.send_action("typing")
    
    # Get the agent from context
    agent = context.application.bot_data.get("agent")
    
    if not agent:
        logger.error("Agent not found in bot_data")
        await message.reply_text(
            "⚠️ Lo siento, el servicio no está disponible en este momento. "
            "Por favor, intenta más tarde."
        )
        return
    
    try:
        logger.info(f"Invoking agent for user {user.id}")
        # Invoke the agent
        response = await agent.invoke(
            message=user_message,
            user_id=user.id,
        )
        
        logger.info(f"Agent response received for user {user.id}, length: {len(response)}")
        
        # Send the response, handling long messages
        if len(response) > 4000:
            # Split into chunks if too long
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await message.reply_text(chunk, parse_mode="Markdown")
        else:
            await message.reply_text(response, parse_mode="Markdown")
        
        logger.debug(f"Processed message for user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to process message for user {user.id}: {e}")
        await message.reply_text(
            "❌ Lo siento, ha ocurrido un error. Por favor, intenta de nuevo."
        )