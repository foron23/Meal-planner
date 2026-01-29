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
    
    # ===== LLM-as-a-Judge tests =====
    
    def test_llm_judge_disabled_by_default(self):
        """Test that guardrails work without LLM judge."""
        guardrails = MealPlannerGuardrails()
        # Should work normally without LLM judge
        is_valid, reason = self.guardrails.validate_input("Hola, quiero un menú")
        assert is_valid
    
    def test_llm_judge_with_mock_structured_output(self):
        """Test LLM-as-a-Judge with structured output using mock."""
        from src.services.guardrails import JudgeResponse
        
        # Mock LLM that returns a structured JudgeResponse
        class MockLLMStructured:
            def with_structured_output(self, schema):
                # Return self to chain the call
                return self
            
            def invoke(self, messages):
                # Return a JudgeResponse object
                return JudgeResponse(
                    is_meal_related=False,
                    confidence="high",
                    reason="test rejection - not about food"
                )
        
        guardrails = MealPlannerGuardrails(llm_judge=MockLLMStructured())
        
        # Long message without keywords should trigger LLM judge
        long_message = "Me gustaría que me ayudes con algo muy interesante que necesito para un proyecto importante"
        is_valid, reason = guardrails.validate_input(long_message)
        
        # Should be rejected by the mock LLM judge
        assert not is_valid
        assert "llm_judge_rejected" in reason
        assert "high confidence" in reason
    
    def test_llm_judge_approves_ambiguous_meal_request(self):
        """Test that LLM judge can approve ambiguous meal-related requests."""
        from src.services.guardrails import JudgeResponse
        
        # Mock LLM that approves the request
        class MockLLMStructured:
            def with_structured_output(self, schema):
                return self
            
            def invoke(self, messages):
                return JudgeResponse(
                    is_meal_related=True,
                    confidence="high",
                    reason="discusses meal planning for family"
                )
        
        guardrails = MealPlannerGuardrails(llm_judge=MockLLMStructured())
        
        # Ambiguous message that might be meal-related
        message = "Necesito organizar algo para la semana que viene para toda la familia"
        is_valid, reason = guardrails.validate_input(message)
        
        # Should be approved
        assert is_valid
    
    def test_llm_judge_with_longer_texts(self):
        """Test LLM judge with longer, more complex texts."""
        from src.services.guardrails import JudgeResponse
        
        # Mock LLM for testing longer texts
        class MockLLMForLongText:
            def __init__(self, meal_related):
                self.meal_related = meal_related
            
            def with_structured_output(self, schema):
                return self
            
            def invoke(self, messages):
                if self.meal_related:
                    return JudgeResponse(
                        is_meal_related=True,
                        confidence="medium",
                        reason="appears to be about meal planning despite length"
                    )
                else:
                    return JudgeResponse(
                        is_meal_related=False,
                        confidence="high",
                        reason="clearly about non-food topics despite being a long message"
                    )
        
        # Test 1: Long text that IS about meal planning (without obvious keywords)
        long_meal_text = (
            "Estoy buscando ayuda para organizar todas las comidas de la próxima semana "
            "para mi familia completa que incluye cuatro adultos y dos niños pequeños. "
            "Necesitaría ideas que sean nutritivas pero también económicas y que no requieran "
            "demasiado tiempo de preparación porque trabajo todo el día y llego tarde a casa."
        )
        
        guardrails_meal = MealPlannerGuardrails(llm_judge=MockLLMForLongText(meal_related=True))
        is_valid, reason = guardrails_meal.validate_input(long_meal_text)
        assert is_valid, "Long meal-related text should be accepted"
        
        # Test 2: Long ambiguous text without obvious keywords that LLM judge will evaluate
        # This text is long but doesn't contain obvious off-topic keywords
        long_ambiguous_text = (
            "Tengo una situación bastante compleja que resolver en los próximos días "
            "relacionada con la organización de actividades para un grupo grande de amigos "
            "que vienen de visita y necesito estructurar todo de manera eficiente considerando "
            "varios factores como el tiempo disponible y las preferencias de cada uno."
        )
        
        guardrails_non_meal = MealPlannerGuardrails(llm_judge=MockLLMForLongText(meal_related=False))
        is_valid, reason = guardrails_non_meal.validate_input(long_ambiguous_text)
        assert not is_valid, "Long non-meal text should be rejected by LLM judge"
        assert "high confidence" in reason
        
        # Test 3: Very long meal-related text (50+ words)
        very_long_meal_text = (
            "Buenos días, estoy planeando un evento familiar grande para el próximo mes "
            "donde estaremos celebrando varios cumpleaños juntos y necesito coordinar todo "
            "lo relacionado con la alimentación de aproximadamente veinte personas que asistirán. "
            "Entre los invitados hay personas con diferentes necesidades y preferencias: algunos "
            "son vegetarianos, otros tienen intolerancia al gluten, y hay niños pequeños que son "
            "bastante selectivos. Me gustaría recibir orientación sobre cómo estructurar los "
            "diferentes platos y asegurarme de que todos puedan disfrutar de opciones adecuadas "
            "sin que resulte demasiado complicado o costoso para nosotros como anfitriones."
        )
        
        guardrails_very_long = MealPlannerGuardrails(llm_judge=MockLLMForLongText(meal_related=True))
        is_valid, reason = guardrails_very_long.validate_input(very_long_meal_text)
        # This should pass validation (either by keywords or LLM judge)
        assert is_valid, "Very long meal text should be accepted"
    
    def test_llm_judge_medium_confidence_rejection(self):
        """Test that medium confidence also triggers rejection."""
        from src.services.guardrails import JudgeResponse
        
        class MockLLM:
            def with_structured_output(self, schema):
                return self
            
            def invoke(self, messages):
                return JudgeResponse(
                    is_meal_related=False,
                    confidence="medium",
                    reason="somewhat unclear but leans towards non-food topic"
                )
        
        guardrails = MealPlannerGuardrails(llm_judge=MockLLM())
        long_message = "Ayúdame con mi situación complicada que necesito resolver pronto para completar"
        is_valid, reason = guardrails.validate_input(long_message)
        
        # Should be rejected even with medium confidence
        assert not is_valid
        assert "medium confidence" in reason
    
    def test_llm_judge_low_confidence_allows(self):
        """Test that low confidence does NOT trigger rejection."""
        from src.services.guardrails import JudgeResponse
        
        class MockLLM:
            def with_structured_output(self, schema):
                return self
            
            def invoke(self, messages):
                return JudgeResponse(
                    is_meal_related=False,
                    confidence="low",
                    reason="very ambiguous, hard to determine"
                )
        
        guardrails = MealPlannerGuardrails(llm_judge=MockLLM())
        long_message = "Necesito ayuda para organizar mis cosas de la próxima semana"
        is_valid, reason = guardrails.validate_input(long_message)
        
        # Should be allowed despite is_meal_related=False because confidence is low
        assert is_valid
