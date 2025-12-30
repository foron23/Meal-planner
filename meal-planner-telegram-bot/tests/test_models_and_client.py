import json
import types


def test_userpreferences_to_display_text():
    from src.models.user import UserPreferences

    prefs = UserPreferences(
        dietary_restrictions=["vegetariano"],
        cuisine_preferences=["mediterránea"],
        allergies=["nueces"],
        disliked_ingredients=["cilantro"],
        household_size=2,
        budget_level="low",
        cooking_time_preference="quick",
        caloric_needs=2200,
        fitness_goals="mantenerse",
        protein_preference="alta",
        extra_data={"nota": "prefiere picante"}
    )

    text = prefs.to_display_text()
    assert "Restricciones dietéticas" in text
    assert "Presupuesto" in text
    assert "Necesidades calóricas" in text
    assert "nota" in text


def test_telegram_client_calls_requests(monkeypatch):
    from src.services import telegram_client

    # Prepare a fake requests module
    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

    class FakeRequests:
        def post(self, url, json=None):
            return FakeResponse({"ok": True, "result": {"chat_id": json.get("chat_id")}})

        def get(self, url, params=None):
            return FakeResponse({"ok": True, "result": []})

    # Inject fake requests into module
    telegram_client.requests = FakeRequests()

    client = telegram_client.TelegramClient(api_token="TOKEN")
    resp = client.send_message(chat_id=123, text="hola")
    assert resp.get("ok") is True
