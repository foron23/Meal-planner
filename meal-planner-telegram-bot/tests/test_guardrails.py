"""
Tests for the guardrails module.

Tests input validation, output validation, and rejection behavior
to ensure the model cannot be misused for non-meal-planning purposes.
"""

import pytest
from src.services.guardrails import MealPlannerGuardrails


class TestMealPlannerGuardrails:
    """Test suite for MealPlannerGuardrails"""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.guardrails = MealPlannerGuardrails()
    
    # ===== Valid meal planning requests =====
    
    def test_valid_menu_request(self):
        """Test that valid menu requests are accepted."""
        valid_requests = [
            "Necesito un menú para la cena de hoy",
            "Quiero preparar algo vegetariano",
            "Dame ideas para el desayuno",
            "Ayúdame a planificar la comida de la semana",
            "Necesito recetas sin gluten",
            "Soy alérgico a los frutos secos, qué puedo comer?",
            "Quiero un menú bajo en calorías",
            "Tengo que cocinar para 4 personas",
            "Recetas rápidas para el almuerzo",
            "Platos con pollo y verduras",
        ]
        
        for request in valid_requests:
            is_valid, reason = self.guardrails.validate_input(request)
            assert is_valid, f"Valid request rejected: '{request}' - Reason: {reason}"
            assert reason is None
    
    def test_valid_preference_updates(self):
        """Test that preference updates are accepted."""
        preference_messages = [
            "Soy vegetariano",
            "Tengo alergia a la lactosa",
            "Prefiero comida mediterránea",
            "Somos 3 personas en casa",
            "Me gusta la comida picante",
            "No me gustan las berenjenas",
            "Busco recetas económicas",
            "Necesito 2500 kcal al día porque hago deporte",
        ]
        
        for message in preference_messages:
            is_valid, reason = self.guardrails.validate_input(message)
            assert is_valid, f"Preference update rejected: '{message}'"
            assert reason is None
    
    def test_valid_greetings(self):
        """Test that greetings are accepted."""
        greetings = [
            "Hola",
            "Buenos días",
            "Buenas tardes",
            "Hola, ¿cómo estás?",
            "Hey",
        ]
        
        for greeting in greetings:
            is_valid, reason = self.guardrails.validate_input(greeting)
            assert is_valid, f"Greeting rejected: '{greeting}'"
    
    # ===== Invalid off-topic requests =====
    
    def test_programming_requests_rejected(self):
        """Test that programming requests are rejected."""
        programming_requests = [
            "Escribe un código en Python para ordenar una lista",
            "Ayúdame con mi función de JavaScript",
            "Cómo crear una clase en Java",
            "def factorial(n): escribelo",
            "Muéstrame un ejemplo de API REST",
            "Ayúdame a debugear este código",
            "Explícame qué es un algoritmo de ordenamiento",
        ]
        
        for request in programming_requests:
            is_valid, reason = self.guardrails.validate_input(request)
            assert not is_valid, f"Programming request not rejected: '{request}'"
            assert reason is not None
    
    def test_math_requests_rejected(self):
        """Test that math problems are rejected."""
        math_requests = [
            "Resuelve esta ecuación: 2x + 5 = 15",
            "Calcula la derivada de x^2",
            "Ayúdame con geometría",
            "Explícame el teorema de Pitágoras",
            "Necesito resolver este problema de álgebra",
        ]
        
        for request in math_requests:
            is_valid, reason = self.guardrails.validate_input(request)
            assert not is_valid, f"Math request not rejected: '{request}'"
            assert reason is not None
    
    def test_homework_requests_rejected(self):
        """Test that homework/academic requests are rejected."""
        homework_requests = [
            "Ayúdame con mi tarea de historia",
            "Escribe un ensayo sobre la Segunda Guerra Mundial",
            "Necesito un resumen del libro Don Quijote",
            "Explícame la teoría de la relatividad",
            "Ayúdame con mi proyecto escolar",
        ]
        
        for request in homework_requests:
            is_valid, reason = self.guardrails.validate_input(request)
            assert not is_valid, f"Homework request not rejected: '{request}'"
            assert reason is not None
    
    def test_general_advice_rejected(self):
        """Test that general life advice requests are rejected."""
        advice_requests = [
            "Dame consejo sobre mi vida",
            "Cómo puedo ganar dinero rápido",
            "Ayúdame a invertir en bolsa",
            "Qué opinas sobre la política actual",
            "Háblame de religión",
        ]
        
        for request in advice_requests:
            is_valid, reason = self.guardrails.validate_input(request)
            assert not is_valid, f"General advice request not rejected: '{request}'"
            assert reason is not None
    
    def test_code_patterns_detected(self):
        """Test that code-like patterns are detected and rejected."""
        code_snippets = [
            "def suma(a, b): return a + b",
            "function calculate() { return x + y; }",
            "class MiClase: pass",
            "import numpy as np",
            "from datetime import datetime",
            "<html><body>Hola</body></html>",
        ]
        
        for code in code_snippets:
            is_valid, reason = self.guardrails.validate_input(code)
            assert not is_valid, f"Code pattern not detected: '{code}'"
            # Reason should contain either code_pattern or off_topic (since "clase" is in OFF_TOPIC_KEYWORDS)
            assert "code_pattern" in reason or "off_topic" in reason
    
    def test_off_topic_phrases_detected(self):
        """Test that off-topic phrases are detected."""
        off_topic = [
            "Ayúdame con mi tarea de matemáticas",
            "Resuelve este problema de física",
            "Escribe un código para esto",
            "Crea una función que haga X",
            "Traduce esto al inglés",
        ]
        
        for message in off_topic:
            is_valid, reason = self.guardrails.validate_input(message)
            assert not is_valid, f"Off-topic phrase not detected: '{message}'"
            assert reason is not None
    
    # ===== Output validation =====
    
    def test_output_validation_accepts_meal_content(self):
        """Test that meal planning responses are accepted."""
        valid_outputs = [
            "Aquí tienes un menú vegetariano para hoy:\n- Desayuno: Tostadas con aguacate\n- Almuerzo: Ensalada César",
            "Te sugiero esta receta de pasta con verduras. Necesitarás: tomates, albahaca, ajo...",
            "Para 4 personas, puedes preparar: 1) Pollo al horno 2) Arroz pilaf 3) Ensalada mixta",
        ]
        
        for output in valid_outputs:
            is_valid = self.guardrails.validate_output(output)
            assert is_valid, f"Valid meal output rejected: '{output[:50]}...'"
    
    def test_output_validation_rejects_code(self):
        """Test that code in output is detected."""
        code_outputs = [
            "```python\ndef calculate():\n    return x + y\n```",
            "Aquí está el código en JavaScript:\n```javascript\nfunction test() {}\n```",
            "```sql\nSELECT * FROM users;\n```",
        ]
        
        for output in code_outputs:
            is_valid = self.guardrails.validate_output(output)
            assert not is_valid, f"Code output not rejected: '{output[:50]}...'"
    
    def test_output_validation_rejects_math_notation(self):
        """Test that mathematical notation is detected."""
        math_outputs = [
            "La solución es $x = 5$ según la ecuación",
            "\\[E = mc^2\\] es la fórmula",
            "\\begin{equation}x^2 + y^2 = r^2\\end{equation}",
        ]
        
        for output in math_outputs:
            is_valid = self.guardrails.validate_output(output)
            assert not is_valid, f"Math notation not rejected: '{output[:50]}...'"
    
    # ===== Rejection messages =====
    
    def test_rejection_message_format(self):
        """Test that rejection messages are user-friendly."""
        message = self.guardrails.get_rejection_message("test_reason")
        
        # Check that message is in Spanish
        assert "Lo siento" in message or "siento" in message
        
        # Check that it mentions meal planning
        assert "menú" in message.lower() or "comida" in message.lower()
        
        # Check that it's helpful
        assert "?" in message  # Offers to help
    
    # ===== Statistics =====
    
    def test_rejection_statistics_tracked(self):
        """Test that rejection statistics are tracked."""
        initial_stats = self.guardrails.get_stats()
        initial_count = initial_stats["total_rejections"]
        
        # Trigger a rejection
        self.guardrails.validate_input("Escribe un código en Python")
        
        # Check that count increased
        new_stats = self.guardrails.get_stats()
        assert new_stats["total_rejections"] == initial_count + 1
    
    def test_multiple_rejections_counted(self):
        """Test that multiple rejections are counted correctly."""
        initial_stats = self.guardrails.get_stats()
        initial_count = initial_stats["total_rejections"]
        
        # Trigger multiple rejections
        off_topic_requests = [
            "def test(): pass",
            "Ayúdame con mi tarea",
        ]
        
        for request in off_topic_requests:
            self.guardrails.validate_input(request)
        
        # Check that all were counted
        new_stats = self.guardrails.get_stats()
        assert new_stats["total_rejections"] == initial_count + len(off_topic_requests)
    
    # ===== Edge cases =====
    
    def test_empty_message_allowed(self):
        """Test that empty messages are handled gracefully."""
        is_valid, reason = self.guardrails.validate_input("")
        assert is_valid
        
        is_valid, reason = self.guardrails.validate_input("   ")
        assert is_valid
    
    def test_mixed_content_with_meal_keywords(self):
        """Test that mixed content with meal keywords is allowed if meal-related."""
        mixed_messages = [
            "Quiero preparar pasta, somos 4 personas en casa",
            "Necesito un menú vegetariano para mi familia de 5",
        ]
        
        for message in mixed_messages:
            is_valid, reason = self.guardrails.validate_input(message)
            assert is_valid, f"Mixed meal content rejected: '{message}'"
    
    def test_case_insensitive_detection(self):
        """Test that keyword detection is case-insensitive."""
        # Should be rejected regardless of case
        is_valid, reason = self.guardrails.validate_input("ESCRIBE UN CÓDIGO EN PYTHON")
        assert not is_valid
        
        # Should be accepted regardless of case
        is_valid, reason = self.guardrails.validate_input("NECESITO UN MENÚ VEGETARIANO")
        assert is_valid
