"""
Configuration module for the Meal Planner Telegram Bot.

Uses pydantic-settings for type-safe configuration management with environment variables.
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or a .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ==================== Telegram Configuration ====================
    telegram_bot_token: str = Field(
        ...,
        description="Telegram Bot API token from @BotFather",
    )
    
    # ==================== OpenAI Configuration ====================
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for LLM access",
    )
    
    llm_model: str = Field(
        default="gpt-4o-mini",
        description="LLM model to use for menu generation",
    )
    
    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response creativity",
    )
    
    llm_max_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Maximum tokens in LLM response",
    )
    
    # ==================== Database Configuration ====================
    database_path: str = Field(
        default="./data/meal_planner.db",
        description="Path to SQLite database file",
    )
    
    @field_validator("database_path")
    @classmethod
    def ensure_database_directory(cls, v: str) -> str:
        """Ensure the database directory exists."""
        db_path = Path(v)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return str(db_path)
    
    # ==================== Logging Configuration ====================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format",
    )
    
    # ==================== Application Configuration ====================
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    
    default_language: str = Field(
        default="es",
        description="Default language for responses",
    )
    
    max_conversation_history: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Maximum messages to keep in conversation history",
    )


# Global settings instance - lazy loaded
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get the application settings.
    
    Returns:
        Settings: The application settings instance.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# System prompt for the meal planning assistant
SYSTEM_PROMPT = """Eres un asistente experto en planificación de menús y nutrición llamado "Chef Bot". 
Tu objetivo es ayudar a los usuarios a crear menús personalizados según sus preferencias, 
restricciones dietéticas y necesidades específicas.

## Tus capacidades:
1. Generar propuestas de menús completos (desayuno, almuerzo, cena, snacks)
2. Adaptar recetas según restricciones dietéticas (vegetariano, vegano, sin gluten, etc.)
3. Considerar el presupuesto y tiempo de preparación disponible
4. Sugerir alternativas y sustituciones de ingredientes
5. Proporcionar información nutricional básica

## Reglas de comportamiento:
1. Siempre responde en español de manera amable y profesional
2. Si el usuario menciona nuevas preferencias o restricciones, confírmalas y recuérdalas
3. Cuando generes menús, incluye:
   - Nombre del plato
   - Ingredientes principales
   - Tiempo estimado de preparación
   - Nivel de dificultad (fácil, medio, difícil)
4. Si no tienes suficiente información, haz preguntas clarificadoras
5. Sé creativo pero práctico en tus sugerencias
6. Considera las preferencias guardadas del usuario al hacer recomendaciones

## Preferencias del usuario:
{user_preferences}

Recuerda: Tu objetivo es hacer que la planificación de comidas sea fácil, divertida y personalizada."""


# Prompt for extracting user preferences from conversation
PREFERENCE_EXTRACTION_PROMPT = """Analiza el siguiente mensaje del usuario y extrae cualquier preferencia 
alimentaria mencionada. Devuelve un JSON con las preferencias detectadas.

Categorías a detectar:
- dietary_restrictions: restricciones dietéticas (vegetariano, vegano, sin gluten, kosher, halal, etc.)
- cuisine_preferences: preferencias de cocina (mediterránea, asiática, mexicana, italiana, etc.)
- allergies: alergias alimentarias (frutos secos, mariscos, lácteos, huevos, etc.)
- disliked_ingredients: ingredientes que no le gustan
- household_size: número de personas en el hogar
- budget_level: nivel de presupuesto (low, medium, high)
- cooking_time_preference: preferencia de tiempo de cocina (quick, medium, elaborate)
- caloric_needs: necesidades calóricas diarias (número o descripción)
- fitness_goals: objetivos de fitness o deportivos
- protein_preference: preferencia de proteínas (alta, media, baja)

Mensaje del usuario: {message}

Responde SOLO con un JSON válido. Si no se detectan preferencias, responde con un objeto JSON vacío.
Ejemplo de respuesta:
{{"dietary_restrictions": ["vegetariano"], "household_size": 4, "caloric_needs": 2500}}"""