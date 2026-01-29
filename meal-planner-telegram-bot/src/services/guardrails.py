"""
Guardrails module for the Meal Planner Bot.

This module implements input validation and safety checks to ensure the LLM
is only used for meal planning purposes and not for unrelated tasks.
"""

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)


class MealPlannerGuardrails:
    """
    Implements guardrails to prevent model misuse.
    
    Ensures the bot only responds to meal planning related requests and
    rejects off-topic queries such as coding help, math problems, general
    conversation, or any non-food-related tasks.
    """
    
    # Keywords that indicate meal planning topics
    MEAL_PLANNING_KEYWORDS = {
        # Food and meals
        "comida", "cena", "desayuno", "almuerzo", "merienda", "snack",
        "receta", "plato", "menú", "menu", "cocina", "cocinar",
        # Food types
        "vegetariano", "vegano", "carne", "pescado", "pollo", "verduras",
        "pasta", "arroz", "ensalada", "sopa", "postre",
        # Dietary
        "dieta", "nutrición", "calorías", "proteína", "carbohidratos",
        "gluten", "lactosa", "alergia", "restricción",
        # Preferences
        "ingredientes", "alimentos", "productos", "frescos",
        # Cooking
        "preparar", "elaborar", "hornear", "freír", "cocer",
        "tiempo de preparación", "dificultad",
        # Household/planning
        "personas", "familia", "plan semanal", "lista de compras",
        "presupuesto para comida", "despensa",
    }
    
    # Keywords that indicate off-topic requests
    OFF_TOPIC_KEYWORDS = {
        # Programming/Technical
        "código", "programar", "javascript", "python", "java", "html",
        "css", "sql", "api", "github", "git", "función", "variable",
        "algoritmo", "clase", "método", "framework", "biblioteca",
        "compile", "debug", "error de código", "script",
        # Math/Science
        "ecuación", "derivada", "integral", "teorema", "fórmula matemática",
        "química", "física cuántica", "geometría", "álgebra",
        "calcular números", "resolver matemáticamente",
        # Writing/Content creation
        "escribir ensayo", "redactar artículo", "crear historia",
        "poema", "novela", "guion", "tesis", "documento legal",
        # General tasks
        "traducir idioma", "resumir libro", "analizar texto",
        "crear presentación", "hacer homework", "tarea escolar",
        # Other topics
        "política", "religión", "finanzas personales", "inversiones",
        "consejo legal", "diagnóstico médico", "tratamiento médico",
    }
    
    # Phrases that indicate clear off-topic intent
    OFF_TOPIC_PHRASES = {
        "ayúdame con mi tarea",
        "ayudame con mi tarea",
        "resuelve este problema",
        "escribe un código",
        "crea una función",
        "traduce esto",
        "qué es tu opinión sobre",
        "háblame de",
        "cuéntame sobre",
        "explícame la teoría",
        "dame consejo sobre mi vida",
        "cómo invertir",
        "invertir en bolsa",
        "ayúdame a invertir",
        "invertir mi dinero",
        "cómo ganar dinero",
        "ganar dinero",
        "escribe un ensayo",
        "escribe una historia",
        "escribe un artículo",
        "resumen del libro",
        "resumir libro",
        "analiza el libro",
        "proyecto escolar",
        "mi proyecto",
    }
    
    def __init__(self):
        """Initialize the guardrails system."""
        self.rejection_count = 0
        logger.info("MealPlannerGuardrails initialized")
    
    def validate_input(self, message: str) -> tuple[bool, str | None]:
        """
        Validate if the user input is appropriate for meal planning.
        
        Args:
            message: User's input message
            
        Returns:
            Tuple of (is_valid, rejection_reason)
            - is_valid: True if the message is meal planning related
            - rejection_reason: None if valid, otherwise a string explaining why it was rejected
        """
        if not message or not message.strip():
            return True, None
        
        message_lower = message.lower()
        
        # Check for explicit off-topic phrases
        for phrase in self.OFF_TOPIC_PHRASES:
            if phrase in message_lower:
                reason = f"off_topic_phrase_detected: {phrase}"
                logger.warning(f"Guardrail triggered: {reason}")
                self.rejection_count += 1
                return False, reason
        
        # Check for code patterns (looking for code-like syntax)
        code_patterns = [
            r'def\s+\w+\s*\(',  # Python function definition
            r'function\s+\w+\s*\(',  # JavaScript function
            r'class\s+\w+\s*[:{]',  # Class definition
            r'import\s+\w+',  # Import statements
            r'from\s+\w+\s+import',  # Python import
            r'<\w+>.*</\w+>',  # HTML tags
            r'\w+\s*=\s*\w+\s*[\+\-\*/]',  # Variable assignments with math
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                reason = f"code_pattern_detected: {pattern}"
                logger.warning(f"Guardrail triggered: {reason}")
                self.rejection_count += 1
                return False, reason
        
        # Check for off-topic keywords
        off_topic_matches = [
            keyword for keyword in self.OFF_TOPIC_KEYWORDS
            if keyword in message_lower
        ]
        
        # Check for meal planning keywords
        on_topic_matches = [
            keyword for keyword in self.MEAL_PLANNING_KEYWORDS
            if keyword in message_lower
        ]
        
        # If we have off-topic keywords but no on-topic ones, likely off-topic
        if off_topic_matches and not on_topic_matches:
            reason = f"off_topic_keywords: {', '.join(off_topic_matches[:3])}"
            logger.warning(f"Guardrail triggered: {reason}")
            self.rejection_count += 1
            return False, reason
        
        # For very short messages (greetings, etc.), allow them
        # The system prompt will handle appropriate responses
        if len(message_lower.split()) <= 3:
            # Common greetings are allowed
            greetings = {"hola", "holi", "buenas", "buenos días", "buenas tardes",
                        "buenas noches", "hey", "hi", "hello", "saludos"}
            if any(greeting in message_lower for greeting in greetings):
                return True, None
        
        # If message is long but has no meal planning indicators, be suspicious
        # but don't reject immediately (let the system prompt guide the LLM)
        if len(message.split()) > 10 and not on_topic_matches:
            logger.info(f"Long message with no meal planning keywords, monitoring: '{message[:50]}...'")
            # Don't reject, but log for monitoring
        
        # Default: allow (system prompt will guide the LLM)
        return True, None
    
    def get_rejection_message(self, rejection_reason: str | None = None) -> str:
        """
        Get a user-friendly rejection message.
        
        Args:
            rejection_reason: Internal reason for rejection (optional)
            
        Returns:
            User-friendly message explaining the rejection
        """
        return (
            "🍽️ Lo siento, soy un asistente especializado únicamente en **planificación de menús** "
            "y **nutrición**. No puedo ayudarte con otros temas.\n\n"
            "Puedo ayudarte con:\n"
            "• Generar menús personalizados\n"
            "• Sugerir recetas según tus preferencias\n"
            "• Adaptar menús a restricciones dietéticas\n"
            "• Planificar comidas semanales\n"
            "• Proporcionar información nutricional\n\n"
            "¿Te gustaría que te ayude con alguno de estos temas relacionados con comidas?"
        )
    
    def validate_output(self, response: str) -> bool:
        """
        Validate that the LLM output stays on topic.
        
        This is a secondary check to ensure the LLM didn't generate
        off-topic content despite the system prompt.
        
        Args:
            response: The LLM's generated response
            
        Returns:
            True if the response appears to be meal planning related
        """
        if not response or not response.strip():
            return True
        
        response_lower = response.lower()
        
        # Check if response contains obvious code blocks
        if "```" in response and any(lang in response_lower for lang in 
                                      ["python", "javascript", "java", "html", "css", "sql"]):
            logger.warning("LLM output contains code blocks - possible off-topic response")
            return False
        
        # Check for mathematical formulas (LaTeX-like patterns)
        if re.search(r'\$.*\$|\\\[.*\\\]|\\begin\{equation\}', response):
            logger.warning("LLM output contains mathematical notation - possible off-topic response")
            return False
        
        # For now, be permissive with output validation
        # The input validation is the primary defense
        return True
    
    def get_stats(self) -> dict:
        """
        Get statistics about guardrail activations.
        
        Returns:
            Dictionary with guardrail statistics
        """
        return {
            "total_rejections": self.rejection_count,
        }
