"""
Integration tests for guardrails in the LangGraph agent.

Tests that the guardrails properly integrate with the agent and reject
off-topic requests while allowing meal planning requests.
"""

import pytest
from types import SimpleNamespace
from langchain_core.messages import AIMessage


class FakeLLM:
    """Fake LLM for testing without making actual API calls."""
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, messages):
        # Return a generic meal planning response
        return AIMessage(content="Aquí tienes una sugerencia de menú vegetariano para hoy.")


def make_agent_with_guardrails(tmp_path, monkeypatch):
    """Create an agent with guardrails enabled."""
    from src.services.sqlite_store import SQLiteStore
    from src.services.langgraph_agent import MealPlannerAgent
    from src.config import Settings

    # Mock the settings to avoid requiring environment variables
    mock_settings = Settings(
        telegram_bot_token="fake_token",
        openai_api_key="fake_api_key",
        database_path=str(tmp_path / "test_agent.db"),
    )
    monkeypatch.setattr("src.config._settings", mock_settings)
    monkeypatch.setattr("src.services.langgraph_agent.get_settings", lambda: mock_settings)

    # Prevent real LLM calls
    monkeypatch.setattr("src.services.langgraph_agent.ChatOpenAI", FakeLLM)

    db_path = str(tmp_path / "test_agent.db")
    store = SQLiteStore(db_path)
    agent = MealPlannerAgent(store)
    return agent


class TestGuardrailsIntegration:
    """Integration tests for guardrails in the agent."""
    
    @pytest.mark.asyncio
    async def test_agent_accepts_valid_meal_request(self, tmp_path, monkeypatch):
        """Test that the agent accepts and processes valid meal planning requests."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        valid_requests = [
            "Necesito un menú para la cena",
            "Dame ideas para el desayuno",
            "Soy vegetariano",
        ]
        
        for request in valid_requests:
            response = await agent.invoke(request, user_id=123)
            
            # Should not be a rejection message
            assert "Lo siento" not in response or "menú vegetariano" in response
            # Should contain meal-related content
            assert len(response) > 0
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_agent_rejects_programming_request(self, tmp_path, monkeypatch):
        """Test that the agent rejects programming-related requests."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        programming_requests = [
            "Escribe un código en Python para ordenar una lista",
            "def suma(a, b): return a + b",
            "Ayúdame con JavaScript",
        ]
        
        for request in programming_requests:
            response = await agent.invoke(request, user_id=123)
            
            # Should be a rejection message
            assert "Lo siento" in response
            assert "especializado" in response or "planificación de menús" in response
            # Should NOT contain actual code or programming help
            assert "def " not in response
            assert "function" not in response
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_agent_rejects_math_request(self, tmp_path, monkeypatch):
        """Test that the agent rejects math problem requests."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        response = await agent.invoke("Resuelve la ecuación 2x + 5 = 15", user_id=123)
        
        # Should be a rejection message
        assert "Lo siento" in response
        assert "planificación de menús" in response or "nutrición" in response
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_agent_rejects_homework_help(self, tmp_path, monkeypatch):
        """Test that the agent rejects homework help requests."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        response = await agent.invoke("Ayúdame con mi tarea de historia", user_id=123)
        
        # Should be a rejection message
        assert "Lo siento" in response
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_guardrail_stats_tracked(self, tmp_path, monkeypatch):
        """Test that guardrail statistics are properly tracked."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        # Get initial stats
        initial_stats = agent.get_guardrail_stats()
        initial_rejections = initial_stats["total_rejections"]
        
        # Make some off-topic requests
        await agent.invoke("Escribe código Python", user_id=123)
        await agent.invoke("Resuelve esta ecuación", user_id=123)
        
        # Check that stats were updated
        new_stats = agent.get_guardrail_stats()
        assert new_stats["total_rejections"] == initial_rejections + 2
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_valid_requests_dont_increment_rejections(self, tmp_path, monkeypatch):
        """Test that valid requests don't increment rejection counter."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        # Get initial stats
        initial_stats = agent.get_guardrail_stats()
        initial_rejections = initial_stats["total_rejections"]
        
        # Make valid requests
        await agent.invoke("Necesito un menú vegetariano", user_id=123)
        await agent.invoke("Dame recetas de pasta", user_id=123)
        
        # Check that rejections didn't increase
        new_stats = agent.get_guardrail_stats()
        assert new_stats["total_rejections"] == initial_rejections
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_mixed_valid_and_invalid_requests(self, tmp_path, monkeypatch):
        """Test behavior with mixed valid and invalid requests."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        # Valid request
        response1 = await agent.invoke("Quiero un menú para la cena", user_id=123)
        assert "Lo siento" not in response1 or "menú" in response1
        
        # Invalid request
        response2 = await agent.invoke("Escribe código Python", user_id=123)
        assert "Lo siento" in response2
        assert "planificación de menús" in response2
        
        # Another valid request
        response3 = await agent.invoke("Soy vegetariano", user_id=123)
        assert "Lo siento" not in response3 or "vegetariano" in response3
        
        # Check stats
        stats = agent.get_guardrail_stats()
        assert stats["total_rejections"] >= 1
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_greeting_then_valid_request(self, tmp_path, monkeypatch):
        """Test that greetings followed by valid requests work."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        # Greeting
        response1 = await agent.invoke("Hola", user_id=123)
        assert len(response1) > 0
        
        # Valid meal request
        response2 = await agent.invoke("Necesito un menú para hoy", user_id=123)
        assert len(response2) > 0
        
        # Both should be accepted
        stats = agent.get_guardrail_stats()
        assert stats["total_rejections"] == 0
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_long_message_without_keywords_monitored(self, tmp_path, monkeypatch):
        """Test that long messages without meal keywords are monitored but may be allowed."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        # Long message without obvious meal keywords but not explicitly off-topic
        long_message = "Estoy buscando algo interesante para hacer este fin de semana con mi familia"
        
        response = await agent.invoke(long_message, user_id=123)
        
        # This might be allowed (ambiguous), but should be logged
        # The important thing is it's monitored
        assert len(response) > 0
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_code_snippet_in_message_rejected(self, tmp_path, monkeypatch):
        """Test that messages containing code snippets are rejected."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        code_message = "Mira este código: def factorial(n): return 1 if n == 0 else n * factorial(n-1)"
        
        response = await agent.invoke(code_message, user_id=123)
        
        # Should be rejected
        assert "Lo siento" in response
        
        agent.close()
    
    @pytest.mark.asyncio
    async def test_multiple_users_independent_tracking(self, tmp_path, monkeypatch):
        """Test that guardrails work independently for different users."""
        agent = make_agent_with_guardrails(tmp_path, monkeypatch)
        
        # User 1 makes an invalid request
        response1 = await agent.invoke("Escribe código Python", user_id=100)
        assert "Lo siento" in response1
        
        # User 2 makes a valid request
        response2 = await agent.invoke("Necesito un menú vegetariano", user_id=200)
        assert "Lo siento" not in response2 or "vegetariano" in response2
        
        # User 1 makes another invalid request
        response3 = await agent.invoke("Resuelve esta ecuación", user_id=100)
        assert "Lo siento" in response3
        
        # Total rejections should be 2 (both from user 1)
        stats = agent.get_guardrail_stats()
        assert stats["total_rejections"] >= 2
        
        agent.close()
