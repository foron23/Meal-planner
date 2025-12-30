#!/usr/bin/env python3
"""
Meal Planner Telegram Bot - Main Entry Point

This module initializes and runs the Telegram bot with LangGraph integration
for intelligent menu planning conversations.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_settings
from src.handlers.menu import menu_command_handler, message_handler
from src.handlers.memory import (
    clear_handler,
    clear_preferences_handler,
    help_handler,
    preferences_handler,
)
from src.handlers.start import start_handler
from src.services.langgraph_agent import MealPlannerAgent
from src.services.sqlite_store import SQLiteStore
from src.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """
    Post-initialization hook for the application.
    
    Sets up bot commands menu and initializes services.
    
    Args:
        application: The Telegram application instance
    """
    # Set bot commands for the menu
    commands = [
        ("start", "Iniciar el bot"),
        ("menu", "Generar un menú"),
        ("preferences", "Ver tus preferencias"),
        ("help", "Ver ayuda"),
        ("clear", "Limpiar historial"),
        ("clear_preferences", "Borrar preferencias"),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands menu set up successfully")


async def post_shutdown(application: Application) -> None:
    """
    Post-shutdown hook for cleanup.
    
    Args:
        application: The Telegram application instance
    """
    # Clean up agent
    agent = application.bot_data.get("agent")
    if agent:
        agent.close()
    
    # Clean up store
    db_store = application.bot_data.get("db_store")
    if db_store:
        db_store.close()
    
    logger.info("Bot shutdown complete")


def create_application() -> Application:
    """
    Create and configure the Telegram Application.
    
    Returns:
        Configured Application instance
    """
    settings = get_settings()
    
    # Initialize SQLite store
    db_store = SQLiteStore(settings.database_path)
    
    # Initialize LangGraph agent
    agent = MealPlannerAgent(db_store)
    
    # Create application builder
    builder = Application.builder()
    builder.token(settings.telegram_bot_token)
    builder.post_init(post_init)
    builder.post_shutdown(post_shutdown)
    
    # Build application
    application = builder.build()
    
    # Store services in bot_data for access in handlers
    application.bot_data["db_store"] = db_store
    application.bot_data["agent"] = agent
    application.bot_data["settings"] = settings
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("menu", menu_command_handler))
    application.add_handler(CommandHandler("preferences", preferences_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("clear", clear_handler))
    application.add_handler(CommandHandler("clear_preferences", clear_preferences_handler))
    
    # Register message handler for natural language (must be last)
    text_message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    application.add_handler(text_message_handler)
    
    logger.info("Registered MessageHandler for TEXT & ~COMMAND")
    logger.info("Telegram application configured successfully")
    
    return application


def main() -> None:
    """
    Main entry point for the bot.
    
    Sets up logging, creates the application, and starts polling.
    """
    # Setup logging
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    
    logger.info("Starting Meal Planner Telegram Bot...")
    logger.info(f"Database path: {settings.database_path}")
    logger.info(f"LLM Model: {settings.llm_model}")
    
    # Create application
    application = create_application()
    
    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping...")
        asyncio.get_event_loop().stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the bot
    logger.info("Bot is starting polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()