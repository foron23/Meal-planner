import asyncio
from types import SimpleNamespace
import pytest


class FakeMessage:
    def __init__(self, text, chat, reply_to_message=None, from_user=None):
        self.text = text
        self.chat = chat
        self.reply_to_message = reply_to_message
        self.from_user = from_user

    async def reply_text(self, text, **kwargs):
        # store last reply for assertions
        self._last_reply = text
        return text


class FakeChat:
    def __init__(self, chat_id, chat_type="private"):
        self.id = chat_id
        self.type = chat_type

    async def send_action(self, action):
        self._action = action


class FakeAgent:
    def __init__(self):
        self.invoked = False

    async def invoke(self, message, user_id):
        self.invoked = True
        return f"generated: {message}"


@pytest.mark.asyncio
async def test_menu_command_handler_calls_agent_and_sends_message(monkeypatch):
    from src.handlers.menu import menu_command_handler

    chat = FakeChat(chat_id=10, chat_type="private")
    msg = FakeMessage(text="/menu", chat=chat, from_user=SimpleNamespace(id=1))
    update = SimpleNamespace(effective_user=SimpleNamespace(id=1), effective_chat=chat, message=msg)

    fake_agent = FakeAgent()
    context = SimpleNamespace(args=[], application=SimpleNamespace(bot_data={"agent": fake_agent}))

    await menu_command_handler(update, context)

    assert fake_agent.invoked is True
    assert hasattr(msg, "_last_reply")
    assert "generated:" in msg._last_reply


@pytest.mark.asyncio
async def test_message_handler_group_requires_mention(monkeypatch):
    from src.handlers.menu import message_handler

    # No mention -> agent should not be invoked
    chat = FakeChat(chat_id=-1001, chat_type="supergroup")
    user = SimpleNamespace(id=42)
    msg = FakeMessage(text="hello everyone", chat=chat, from_user=user)
    update = SimpleNamespace(effective_user=user, effective_chat=chat, message=msg)

    fake_agent = FakeAgent()
    bot = SimpleNamespace(username="mybot", id=999)
    context = SimpleNamespace(application=SimpleNamespace(bot_data={"agent": fake_agent}), bot=bot)

    await message_handler(update, context)
    assert fake_agent.invoked is False

    # With mention -> should invoke
    msg2 = FakeMessage(text="@mybot ¿me recomiendas un menú?", chat=chat, from_user=user)
    update2 = SimpleNamespace(effective_user=user, effective_chat=chat, message=msg2)
    await message_handler(update2, context)
    assert fake_agent.invoked is True
    assert hasattr(msg2, "_last_reply")


@pytest.mark.asyncio
async def test_message_handler_private_invokes_agent(monkeypatch):
    from src.handlers.menu import message_handler

    chat = FakeChat(chat_id=200, chat_type="private")
    user = SimpleNamespace(id=7)
    msg = FakeMessage(text="Quiero un menú vegano", chat=chat, from_user=user)
    update = SimpleNamespace(effective_user=user, effective_chat=chat, message=msg)

    fake_agent = FakeAgent()
    context = SimpleNamespace(application=SimpleNamespace(bot_data={"agent": fake_agent}), bot=SimpleNamespace(username="any", id=1))

    await message_handler(update, context)
    assert fake_agent.invoked is True
    assert hasattr(msg, "_last_reply")
"""
Tests for Telegram bot handlers.

These tests verify the correct behavior of command and message handlers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestStartHandler:
    """Tests for the /start command handler."""
    
    @pytest.mark.asyncio
    async def test_start_handler_creates_user(self):
        """Test that /start creates a new user if not exists."""
        from src.handlers.start import start_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.effective_user.username = "testuser"
        mock_update.effective_user.first_name = "Test"
        mock_update.effective_user.last_name = "User"
        mock_update.effective_user.language_code = "es"
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock context
        mock_context = MagicMock()
        mock_db_store = MagicMock()
        mock_context.application.bot_data = {"db_store": mock_db_store}
        
        # Call handler
        await start_handler(mock_update, mock_context)
        
        # Verify user was created/updated
        mock_db_store.get_or_create_user.assert_called_once_with(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="es",
        )
        
        # Verify welcome message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Bienvenido" in call_args[0][0] or "Test" in call_args[0][0]


class TestMenuHandler:
    """Tests for the menu command and message handlers."""
    
    @pytest.mark.asyncio
    async def test_menu_handler_invokes_agent(self):
        """Test that menu handler correctly invokes the LangGraph agent."""
        from src.handlers.menu import message_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.text = "Quiero un menú vegetariano"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value="Aquí tienes tu menú vegetariano...")
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"agent": mock_agent}
        
        # Call handler
        await message_handler(mock_update, mock_context)
        
        # Verify agent was invoked
        mock_agent.invoke.assert_called_once_with(
            message="Quiero un menú vegetariano",
            user_id=123456,
        )
        
        # Verify response was sent
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_menu_handler_handles_agent_error(self):
        """Test that menu handler gracefully handles agent errors."""
        from src.handlers.menu import message_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.text = "Test message"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock agent that raises error
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(side_effect=Exception("LLM Error"))
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"agent": mock_agent}
        
        # Call handler
        await message_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "error" in call_args[0][0].lower()


class TestPreferencesHandler:
    """Tests for the /preferences command handler."""
    
    @pytest.mark.asyncio
    async def test_preferences_handler_shows_preferences(self):
        """Test that /preferences shows user's saved preferences."""
        from src.handlers.memory import preferences_handler
        from src.models.user import UserPreferences
        
        # Create mock preferences
        mock_prefs = UserPreferences(
            user_id=1,
            dietary_restrictions=["vegetariano"],
            allergies=["frutos secos"],
            household_size=4,
        )
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock db_store
        mock_db_store = MagicMock()
        mock_db_store.get_user_preferences = MagicMock(return_value=mock_prefs)
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"db_store": mock_db_store}
        
        # Call handler
        await preferences_handler(mock_update, mock_context)
        
        # Verify preferences were retrieved
        mock_db_store.get_user_preferences.assert_called_once_with(123456)
        
        # Verify response was sent
        mock_update.message.reply_text.assert_called_once()


class TestClearHandler:
    """Tests for the /clear command handler."""
    
    @pytest.mark.asyncio
    async def test_clear_handler_clears_conversation(self):
        """Test that /clear clears the conversation history."""
        from src.handlers.memory import clear_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.clear_conversation = MagicMock(return_value=True)
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"agent": mock_agent}
        
        # Call handler
        await clear_handler(mock_update, mock_context)
        
        # Verify conversation was cleared
        mock_agent.clear_conversation.assert_called_once_with(123456)
        
        # Verify success message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "limpiado" in call_args[0][0].lower() or "limpiar" in call_args[0][0].lower()


class TestPreferencesHandlerErrorCases:
    """Tests for error cases in the /preferences command handler."""
    
    @pytest.mark.asyncio
    async def test_preferences_handler_no_user(self):
        """Test that /preferences returns early when user is None."""
        from src.handlers.memory import preferences_handler
        
        # Create mock update with no user
        mock_update = MagicMock()
        mock_update.effective_user = None
        mock_update.message = MagicMock()
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await preferences_handler(mock_update, mock_context)
        
        # Verify no message was sent
        mock_update.message.reply_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_preferences_handler_no_message(self):
        """Test that /preferences returns early when message is None."""
        from src.handlers.memory import preferences_handler
        
        # Create mock update with no message
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = None
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await preferences_handler(mock_update, mock_context)
        
        # Verify no message was sent (since message is None)
    
    @pytest.mark.asyncio
    async def test_preferences_handler_no_db_store(self):
        """Test that /preferences shows error when db_store is not available."""
        from src.handlers.memory import preferences_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock context without db_store
        mock_context = MagicMock()
        mock_context.application.bot_data = {}
        
        # Call handler
        await preferences_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "no está disponible" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_preferences_handler_exception_handling(self):
        """Test that /preferences handles exceptions gracefully."""
        from src.handlers.memory import preferences_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock db_store that raises exception
        mock_db_store = MagicMock()
        mock_db_store.get_user_preferences = MagicMock(side_effect=Exception("Database error"))
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"db_store": mock_db_store}
        
        # Call handler
        await preferences_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "error" in call_args[0][0].lower()


class TestClearHandlerErrorCases:
    """Tests for error cases in the /clear command handler."""
    
    @pytest.mark.asyncio
    async def test_clear_handler_no_user(self):
        """Test that /clear returns early when user is None."""
        from src.handlers.memory import clear_handler
        
        # Create mock update with no user
        mock_update = MagicMock()
        mock_update.effective_user = None
        mock_update.message = MagicMock()
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await clear_handler(mock_update, mock_context)
        
        # Verify no message was sent
        mock_update.message.reply_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_clear_handler_no_message(self):
        """Test that /clear returns early when message is None."""
        from src.handlers.memory import clear_handler
        
        # Create mock update with no message
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = None
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await clear_handler(mock_update, mock_context)
        
        # Verify no message was sent (since message is None)
    
    @pytest.mark.asyncio
    async def test_clear_handler_exception_handling(self):
        """Test that /clear handles exceptions gracefully."""
        from src.handlers.memory import clear_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock agent that raises exception
        mock_agent = MagicMock()
        mock_agent.clear_conversation = MagicMock(side_effect=Exception("Agent error"))
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"agent": mock_agent}
        
        # Call handler
        await clear_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "error" in call_args[0][0].lower()


class TestClearPreferencesHandler:
    """Tests for the /clear_preferences command handler."""
    
    @pytest.mark.asyncio
    async def test_clear_preferences_handler_success(self):
        """Test that /clear_preferences successfully clears preferences."""
        from src.handlers.memory import clear_preferences_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock db_store
        mock_db_store = MagicMock()
        mock_db_store.clear_user_preferences = MagicMock(return_value=True)
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"db_store": mock_db_store}
        
        # Call handler
        await clear_preferences_handler(mock_update, mock_context)
        
        # Verify preferences were cleared
        mock_db_store.clear_user_preferences.assert_called_once_with(123456)
        
        # Verify success message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "borradas" in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_clear_preferences_handler_no_preferences(self):
        """Test that /clear_preferences handles case when no preferences exist."""
        from src.handlers.memory import clear_preferences_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock db_store
        mock_db_store = MagicMock()
        mock_db_store.clear_user_preferences = MagicMock(return_value=False)
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"db_store": mock_db_store}
        
        # Call handler
        await clear_preferences_handler(mock_update, mock_context)
        
        # Verify preferences clear was attempted
        mock_db_store.clear_user_preferences.assert_called_once_with(123456)
        
        # Verify info message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "no había" in call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_clear_preferences_handler_no_user(self):
        """Test that /clear_preferences returns early when user is None."""
        from src.handlers.memory import clear_preferences_handler
        
        # Create mock update with no user
        mock_update = MagicMock()
        mock_update.effective_user = None
        mock_update.message = MagicMock()
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await clear_preferences_handler(mock_update, mock_context)
        
        # Verify no message was sent
        mock_update.message.reply_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_clear_preferences_handler_no_message(self):
        """Test that /clear_preferences returns early when message is None."""
        from src.handlers.memory import clear_preferences_handler
        
        # Create mock update with no message
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = None
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await clear_preferences_handler(mock_update, mock_context)
        
        # Verify no message was sent (since message is None)
    
    @pytest.mark.asyncio
    async def test_clear_preferences_handler_no_db_store(self):
        """Test that /clear_preferences shows error when db_store is not available."""
        from src.handlers.memory import clear_preferences_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock context without db_store
        mock_context = MagicMock()
        mock_context.application.bot_data = {}
        
        # Call handler
        await clear_preferences_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "no está disponible" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_clear_preferences_handler_exception_handling(self):
        """Test that /clear_preferences handles exceptions gracefully."""
        from src.handlers.memory import clear_preferences_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123456
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock db_store that raises exception
        mock_db_store = MagicMock()
        mock_db_store.clear_user_preferences = MagicMock(side_effect=Exception("Database error"))
        
        # Create mock context
        mock_context = MagicMock()
        mock_context.application.bot_data = {"db_store": mock_db_store}
        
        # Call handler
        await clear_preferences_handler(mock_update, mock_context)
        
        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "error" in call_args[0][0].lower()


class TestHelpHandler:
    """Tests for the /help command handler."""
    
    @pytest.mark.asyncio
    async def test_help_handler_shows_help(self):
        """Test that /help shows the help information."""
        from src.handlers.memory import help_handler
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler
        await help_handler(mock_update, mock_context)
        
        # Verify help message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        help_text = call_args[0][0]
        assert "ayuda" in help_text.lower()
        assert "/start" in help_text
        assert "/menu" in help_text
        assert "/preferences" in help_text
        assert "/clear" in help_text
        assert "/clear_preferences" in help_text
        assert "/help" in help_text
    
    @pytest.mark.asyncio
    async def test_help_handler_no_message(self):
        """Test that /help returns early when message is None."""
        from src.handlers.memory import help_handler
        
        # Create mock update with no message
        mock_update = MagicMock()
        mock_update.message = None
        
        # Create mock context
        mock_context = MagicMock()
        
        # Call handler - should return early without doing anything
        await help_handler(mock_update, mock_context)
        
        # Verify no message was sent (since message is None)
