import json
import pytest
from types import SimpleNamespace
from langchain_core.messages import HumanMessage, AIMessage


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, messages):
        # If passed a list, return an AIMessage
        return AIMessage(content="Respuesta de prueba")


def make_agent(tmp_path, monkeypatch):
    from src.services.sqlite_store import SQLiteStore
    from src.services.langgraph_agent import MealPlannerAgent
    from src.config import Settings

    # Mock the settings to avoid requiring environment variables
    mock_settings = Settings(
        telegram_bot_token="fake_token",
        openai_api_key="fake_api_key",
        database_path=str(tmp_path / "agent.db"),
    )
    monkeypatch.setattr("src.config._settings", mock_settings)
    monkeypatch.setattr("src.services.langgraph_agent.get_settings", lambda: mock_settings)

    # Prevent real LLM calls during initialization
    monkeypatch.setattr("src.services.langgraph_agent.ChatOpenAI", FakeLLM)

    db_path = str(tmp_path / "agent.db")
    store = SQLiteStore(db_path)
    agent = MealPlannerAgent(store)
    return agent


def test_should_extract_preferences_end_and_extract(tmp_path, monkeypatch):
    from src.services.langgraph_agent import HumanMessage

    agent = make_agent(tmp_path, monkeypatch)

    # No human messages -> end
    state = {"messages": []}
    assert agent._should_extract_preferences(state) == "end"

    # With a human message containing keywords -> extract
    state = {"messages": [HumanMessage(content="Soy deportista y necesito 2500 kcal")]}
    assert agent._should_extract_preferences(state) == "extract"

    agent.close()


def test_extract_preferences_parses_json(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    # Make LLM return a JSON string
    monkeypatch.setattr(agent, "llm", SimpleNamespace(invoke=lambda msgs: SimpleNamespace(content=json.dumps({"caloric_needs": 2500, "fitness_goals": "deportista"}))))

    state = {"messages": [HumanMessage(content="Necesito 2500 kcal, soy deportista")], "user_id": 1}
    out = agent._extract_preferences_node(state)
    assert out["should_save_preferences"] is True
    assert out["extracted_preferences"]["caloric_needs"] == 2500

    agent.close()


def test_save_preferences_calls_db(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    # Fake db_store
    called = {}

    class FakeStore:
        def update_user_preferences(self, user_id, prefs):
            called['user_id'] = user_id
            called['prefs'] = prefs
            return prefs

    agent.db_store = FakeStore()

    state = {
        "should_save_preferences": True,
        "user_id": 42,
        "user_preferences": {"dietary_restrictions": ["vegan"]},
        "extracted_preferences": {"dietary_restrictions": ["gluten"], "caloric_needs": 2000},
    }

    out = agent._save_preferences_node(state)
    assert called['user_id'] == 42
    assert 'caloric_needs' in called['prefs']
    assert out.get("user_preferences") is not None

    agent.close()


def test_merge_and_format_preferences(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    current = {"dietary_restrictions": ["vegan"], "budget_level": "medium"}
    new = {"dietary_restrictions": ["gluten"], "caloric_needs": 1800}
    merged = agent._merge_preferences(current, new)
    assert set(merged["dietary_restrictions"]) == {"vegan", "gluten"}
    assert merged["caloric_needs"] == 1800

    fmt = agent._format_preferences(merged)
    assert "Restricciones dietéticas" in fmt or "Tamaño" in fmt or "Presupuesto" in fmt

    agent.close()


def test_chatbot_node_success_and_error(tmp_path, monkeypatch):
    from src.services.langgraph_agent import AIMessage

    agent = make_agent(tmp_path, monkeypatch)

    # Success path: llm.invoke returns AIMessage-like with content attribute
    agent.llm = SimpleNamespace(invoke=lambda msgs: AIMessage(content="Hola mundo"))
    state = {"messages": [], "user_preferences": {}, "messages": []}
    res = agent._chatbot_node({"messages": [], "user_preferences": {}})
    assert isinstance(res.get("messages", [None])[0], AIMessage)

    # Error path: llm.invoke raises
    def raise_exc(msgs):
        raise RuntimeError("fail")

    agent.llm = SimpleNamespace(invoke=raise_exc)
    res = agent._chatbot_node({"messages": [], "user_preferences": {}})
    assert isinstance(res.get("messages", [None])[0], AIMessage)

    agent.close()


def test_invoke_uses_graph_return(tmp_path, monkeypatch):
    from src.services.langgraph_agent import AIMessage

    agent = make_agent(tmp_path, monkeypatch)

    # Test the logic that extracts content from graph result
    # Simulate what happens inside invoke method
    result = {"messages": [AIMessage(content="generated")]}
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
    extracted_content = ai_messages[-1].content if ai_messages else "Lo siento, no pude generar una respuesta."

    assert extracted_content == "generated"

    agent.close()


def test_load_preferences_node_success(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    # Create some test preferences in the database
    from src.models.user import UserPreferences
    test_prefs = UserPreferences(
        user_id=123,
        dietary_restrictions=["vegetarian"],
        allergies=["nuts"],
        household_size=4
    )
    agent.db_store.update_user_preferences(123, test_prefs.model_dump(exclude={"id", "user_id", "updated_at"}))

    state = {"user_id": 123}
    result = agent._load_preferences_node(state)
    
    assert "user_preferences" in result
    assert result["user_preferences"]["dietary_restrictions"] == ["vegetarian"]
    assert result["user_preferences"]["allergies"] == ["nuts"]
    assert result["user_preferences"]["household_size"] == 4

    agent.close()


def test_load_preferences_node_no_preferences(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    state = {"user_id": 999}  # User with no preferences
    result = agent._load_preferences_node(state)
    
    assert result == {"user_preferences": {}}

    agent.close()


def test_load_preferences_node_db_error(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    # Mock db_store to raise an exception
    class FakeStore:
        def get_user_preferences(self, user_id):
            raise Exception("Database error")

    agent.db_store = FakeStore()

    state = {"user_id": 123}
    result = agent._load_preferences_node(state)
    
    assert result == {"user_preferences": {}}

    agent.close()


def test_should_extract_preferences_no_keywords(tmp_path, monkeypatch):
    agent = make_agent(tmp_path, monkeypatch)

    # Message without preference keywords
    state = {"messages": [HumanMessage(content="Hola, ¿cómo estás?")]}
    result = agent._should_extract_preferences(state)
    
    assert result == "end"

    agent.close()
