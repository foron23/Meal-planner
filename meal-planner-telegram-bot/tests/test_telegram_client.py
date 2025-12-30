from types import SimpleNamespace


def test_get_updates_and_process(monkeypatch):
    from src.services.telegram_client import TelegramClient

    # Fake requests module behavior
    class FakeResponse:
        def __init__(self, data):
            self._data = data

        def json(self):
            return self._data

    class FakeRequests:
        def __init__(self):
            self._posted = []

        def get(self, url, params=None):
            return FakeResponse({"ok": True, "result": [{"message": {"chat": {"id": 1}, "text": "hi"}}]})

        def post(self, url, json=None):
            return FakeResponse({"ok": True, "result": {"chat_id": json.get("chat_id")}})

    import src.services.telegram_client as tc
    tc.requests = FakeRequests()

    client = TelegramClient(api_token="T")

    updates = client.get_updates()
    assert updates["ok"] is True

    # Patch handle_message to capture calls
    called = {}

    def fake_handle(chat_id, message_text):
        called['chat_id'] = chat_id
        called['text'] = message_text

    client.handle_message = fake_handle

    client.process_updates(updates)
    assert called['chat_id'] == 1
    assert called['text'] == "hi"
