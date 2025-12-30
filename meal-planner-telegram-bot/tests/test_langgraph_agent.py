import json
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

    # Replace graph.invoke to return expected structure
    agent.graph = SimpleNamespace(invoke=lambda state, config: {"messages": [AIMessage(content="generated")]})

    out = agent.invoke("hola", user_id=99)
    assert out == "generated"

    agent.close()
