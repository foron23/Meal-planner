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
    guardrails = MealPlannerGuardrails()
    
    print("=" * 80)
    print("DEMOSTRACIÓN DEL SISTEMA DE GUARDARRAÍLES")
    print("=" * 80)
    print()
    
    # Valid meal planning requests
    print("✅ SOLICITUDES VÁLIDAS (Relacionadas con planificación de menús):")
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
    print(f"Total de rechazos: {stats['total_rejections']}")
    
    print()
    print("=" * 80)
    print("FIN DE LA DEMOSTRACIÓN")
    print("=" * 80)


if __name__ == "__main__":
    main()
