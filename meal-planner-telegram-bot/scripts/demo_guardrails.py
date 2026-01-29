#!/usr/bin/env python3
"""
Demonstration script for the guardrails system.

This script shows examples of how the guardrails work by testing
various inputs and showing which are accepted and which are rejected.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.guardrails import MealPlannerGuardrails


def main():
    """Demonstrate guardrails functionality."""
    print("=" * 80)
    print("DEMOSTRACIÓN DEL SISTEMA DE GUARDARRAÍLES")
    print("=" * 80)
    print()
    
    # Demonstrate without LLM-as-a-Judge
    print("🔍 MODO 1: Validación basada en reglas (sin LLM-as-a-Judge)")
    print("=" * 80)
    guardrails = MealPlannerGuardrails()
    
    # Valid meal planning requests
    print("\n✅ SOLICITUDES VÁLIDAS (Relacionadas con planificación de menús):")
    print("-" * 80)
    valid_requests = [
        "Necesito un menú para la cena de hoy",
        "Quiero preparar algo vegetariano",
        "Soy alérgico a los frutos secos",
        "Dame recetas rápidas para 4 personas",
        "Tengo que cocinar con un presupuesto bajo",
    ]
    
    for i, request in enumerate(valid_requests, 1):
        is_valid, reason = guardrails.validate_input(request)
        status = "✅ ACEPTADO" if is_valid else "❌ RECHAZADO"
        print(f"{i}. {status}: '{request}'")
        if reason:
            print(f"   Razón: {reason}")
    
    print()
    
    # Invalid off-topic requests
    print("❌ SOLICITUDES INVÁLIDAS (Fuera de tema):")
    print("-" * 80)
    invalid_requests = [
        "Escribe un código en Python para ordenar una lista",
        "Resuelve la ecuación 2x + 5 = 15",
        "Ayúdame con mi tarea de historia",
        "Explícame qué es JavaScript",
        "Cómo puedo invertir mi dinero",
        "def factorial(n): return 1 if n == 0 else n * factorial(n-1)",
    ]
    
    for i, request in enumerate(invalid_requests, 1):
        is_valid, reason = guardrails.validate_input(request)
        status = "✅ ACEPTADO" if is_valid else "❌ RECHAZADO"
        print(f"{i}. {status}: '{request}'")
        if reason:
            print(f"   Razón: {reason}")
    
    print()
    
    # Demonstrate LLM-as-a-Judge with mock
    print("\n🤖 MODO 2: Validación con LLM-as-a-Judge (Structured Output)")
    print("=" * 80)
    print("Para casos ambiguos (mensajes largos sin palabras clave), se usa el LLM")
    print("para clasificar si la solicitud está relacionada con comida.")
    print("Usa Pydantic (JudgeResponse) para garantizar el formato de respuesta.")
    print()
    
    # Mock LLM for demonstration with structured output
    from src.services.guardrails import JudgeResponse
    
    class MockLLMJudge:
        """Mock LLM that simulates the judge behavior with structured output."""
        def with_structured_output(self, schema):
            # Return self to simulate chaining
            return self
        
        def invoke(self, messages):
            # Simple mock: if message contains certain words, classify accordingly
            message_content = str(messages)
            if "familia" in message_content.lower():
                # Ambiguous case - could be meal planning
                return JudgeResponse(
                    is_meal_related=True,
                    confidence="medium",
                    reason="podría ser sobre planificación de comidas familiares"
                )
            else:
                return JudgeResponse(
                    is_meal_related=False,
                    confidence="high",
                    reason="no relacionado con comidas"
                )
    
    guardrails_with_judge = MealPlannerGuardrails(llm_judge=MockLLMJudge())
    
    ambiguous_requests = [
        "Necesito organizar algo importante para la próxima semana con toda la familia",
        "Tengo que preparar una presentación sobre un tema interesante",
    ]
    
    print("🔍 SOLICITUDES AMBIGUAS:")
    print("-" * 80)
    for i, request in enumerate(ambiguous_requests, 1):
        is_valid, reason = guardrails_with_judge.validate_input(request)
        status = "✅ ACEPTADO" if is_valid else "❌ RECHAZADO"
        print(f"{i}. {status}: '{request}'")
        if reason:
            print(f"   Razón: {reason}")
    
    print()
    
    # Show rejection message
    print("📝 MENSAJE DE RECHAZO ENVIADO AL USUARIO:")
    print("-" * 80)
    rejection_msg = guardrails.get_rejection_message()
    print(rejection_msg)
    
    print()
    
    # Show statistics
    print("📊 ESTADÍSTICAS:")
    print("-" * 80)
    stats = guardrails.get_stats()
    print(f"Total de rechazos (sin LLM judge): {stats['total_rejections']}")
    stats_with_judge = guardrails_with_judge.get_stats()
    print(f"Total de rechazos (con LLM judge): {stats_with_judge['total_rejections']}")
    
    print()
    print("=" * 80)
    print("NOTA: El LLM-as-a-Judge mejora la precisión para casos ambiguos")
    print("y reduce falsos positivos al usar inteligencia artificial para clasificar.")
    print("=" * 80)
    print()
    print("FIN DE LA DEMOSTRACIÓN")
    print("=" * 80)


if __name__ == "__main__":
    main()
