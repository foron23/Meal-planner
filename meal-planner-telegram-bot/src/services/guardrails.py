"""
Guardrails module for the Meal Planner Bot.

This module implements input validation and safety checks to ensure the LLM
is only used for meal planning purposes and not for unrelated tasks.
"""

import json
import logging
import re
import threading
from typing import Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class JudgeResponse(BaseModel):
    """
    Structured response from the LLM-as-a-Judge.
    
    This model ensures the LLM returns data in the expected format
    using structured output mode.
    """
    is_meal_related: bool = Field(
        description="True if the request is about meal planning, food, recipes, or nutrition. False otherwise."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level: 'high' if very certain, 'medium' if somewhat ambiguous, 'low' if difficult to determine"
    )
    reason: str = Field(
        description="Brief explanation of the classification decision"
    )


# LLM-as-a-Judge prompt for validating ambiguous requests
LLM_JUDGE_PROMPT = """Eres un clasificador de temas. Tu tarea es determinar si una solicitud del usuario está relacionada con planificación de menús, comidas, recetas o nutrición.

Solicitud del usuario: "{message}"

Criterios:
- is_meal_related = true si la solicitud trata sobre: comidas, menús, recetas, ingredientes, nutrición, dietas, cocina, planificación alimentaria
- is_meal_related = false si trata sobre: programación, matemáticas, tareas escolares, consejos no relacionados con comida, temas generales
- confidence = "high" si estás muy seguro, "medium" si hay cierta ambigüedad, "low" si es difícil de determinar

Clasifica la solicitud y proporciona una breve explicación."""


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
        "política", "religión", "finanzas", "inversiones",
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
    
    def __init__(self, llm_judge: Optional[any] = None):
        """
        Initialize the guardrails system.
        
        Args:
            llm_judge: Optional LLM instance to use as a judge for ambiguous cases.
                      If None, LLM-as-a-Judge feature is disabled.
        """
        self._rejection_count = 0
        self._lock = threading.Lock()
        self._llm_judge = llm_judge
        self._llm_judge_enabled = llm_judge is not None
        logger.info(f"MealPlannerGuardrails initialized (LLM-as-a-Judge: {'enabled' if self._llm_judge_enabled else 'disabled'})")
    
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
                with self._lock:
                    self._rejection_count += 1
                return False, reason
        
        # Check for code patterns (looking for code-like syntax)
        # Made more specific to reduce false positives
        code_patterns = [
            r'\bdef\s+[a-zA-Z_]\w*\s*\(',  # Python function definition
            r'\bfunction\s+[a-zA-Z_]\w*\s*\(',  # JavaScript function
            r'\bclass\s+[A-Z][a-zA-Z_]*\s*[:{]',  # Class definition (capitalized)
            r'\bimport\s+[a-zA-Z_]',  # Import statements
            r'\bfrom\s+[a-zA-Z_]+\s+import',  # Python import
            r'<(?:div|span|p|html|body|head|script|style)\b[^>]*>',  # Common HTML tags
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                reason = f"code_pattern_detected: {pattern}"
                logger.warning(f"Guardrail triggered: {reason}")
                with self._lock:
                    self._rejection_count += 1
                return False, reason
        
        # Check for off-topic keywords (whole word matching to avoid substring issues)
        off_topic_matches = [
            keyword for keyword in self.OFF_TOPIC_KEYWORDS
            if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower)
        ]
        
        # Check for meal planning keywords (whole word matching)
        on_topic_matches = [
            keyword for keyword in self.MEAL_PLANNING_KEYWORDS
            if re.search(r'\b' + re.escape(keyword) + r'\b', message_lower)
        ]
        
        # If we have off-topic keywords but no on-topic ones, likely off-topic
        if off_topic_matches and not on_topic_matches:
            reason = f"off_topic_keywords: {', '.join(off_topic_matches[:3])}"
            logger.warning(f"Guardrail triggered: {reason}")
            with self._lock:
                self._rejection_count += 1
            return False, reason
        
        # For very short messages (greetings, etc.), allow them
        # The system prompt will handle appropriate responses
        if len(message_lower.split()) <= 3:
            # Common greetings are allowed
            greetings = {"hola", "holi", "buenas", "buenos días", "buenas tardes",
                        "buenas noches", "hey", "hi", "hello", "saludos"}
            if any(greeting in message_lower for greeting in greetings):
                return True, None
        
        # If message is long but has no meal planning indicators, use LLM-as-a-Judge if available
        if len(message.split()) > 10 and not on_topic_matches:
            logger.info(f"Long message with no meal planning keywords, checking with LLM judge: '{message[:50]}...'")
            
            # Use LLM-as-a-Judge for ambiguous cases
            if self._llm_judge_enabled:
                is_valid, judge_reason = self._validate_with_llm_judge(message)
                if not is_valid:
                    logger.warning(f"LLM judge rejected: {judge_reason}")
                    with self._lock:
                        self._rejection_count += 1
                    return False, f"llm_judge_rejected: {judge_reason}"
        
        # Default: allow (system prompt will guide the LLM)
        return True, None
    
    def _validate_with_llm_judge(self, message: str) -> tuple[bool, str]:
        """
        Use LLM-as-a-Judge to validate ambiguous requests.
        
        This method uses the LLM itself to determine if a request is meal-planning
        related when keyword-based validation is inconclusive. Uses structured
        output to guarantee the response format.
        
        Args:
            message: User's message to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not self._llm_judge_enabled:
            return True, "llm_judge_disabled"
        
        try:
            # Format the judge prompt with the user's message
            judge_prompt = LLM_JUDGE_PROMPT.format(message=message)
            
            # Use structured output with the JudgeResponse model
            # This guarantees the LLM returns data in the expected format
            structured_llm = self._llm_judge.with_structured_output(JudgeResponse)
            
            # Call the LLM judge
            from langchain_core.messages import HumanMessage
            result: JudgeResponse = structured_llm.invoke([HumanMessage(content=judge_prompt)])
            
            # Extract fields from the structured response
            is_meal_related = result.is_meal_related
            confidence = result.confidence
            reason = result.reason
            
            logger.info(f"LLM judge result: meal_related={is_meal_related}, confidence={confidence}, reason={reason}")
            
            # Only reject if LLM is confident it's not meal-related
            if not is_meal_related and confidence in ["high", "medium"]:
                return False, f"{confidence} confidence: {reason}"
            
            return True, "llm_judge_approved"
            
        except Exception as e:
            logger.error(f"LLM judge validation failed: {e}")
            # On error, err on the side of allowing (fail open)
            return True, "llm_judge_error"
    
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
        with self._lock:
            return {
                "total_rejections": self._rejection_count,
            }
