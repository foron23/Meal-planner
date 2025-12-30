class TelegramClient:
    def __init__(self, api_token):
        self.api_token = api_token
        self.base_url = f"https://api.telegram.org/bot{api_token}/"

    def send_message(self, chat_id, text):
        url = f"{self.base_url}sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(url, json=payload)
        return response.json()

    def get_updates(self, offset=None):
        url = f"{self.base_url}getUpdates"
        params = {"offset": offset}
        response = requests.get(url, params=params)
        return response.json()

    def process_updates(self, updates):
        for update in updates.get("result", []):
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]
            self.handle_message(chat_id, message_text)

    def handle_message(self, chat_id, message_text):
        # Placeholder for message handling logic
        pass