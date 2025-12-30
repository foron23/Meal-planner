"""
Tests for bot services.

These tests verify the correct behavior of the SQLite store and agent services.
"""

import os
import tempfile
from datetime import datetime, timezone

import pytest

from src.models.user import User, UserPreferences
from src.services.sqlite_store import SQLiteStore


class TestSQLiteStore:
    """Tests for the SQLite store service."""
    
    @pytest.fixture
    def db_store(self):
        """Create a temporary database for testing."""
        # Create temp file for test database
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        store = SQLiteStore(db_path)
        yield store
        
        # Cleanup
        store.close()
        os.unlink(db_path)
    
    def test_create_user(self, db_store):
        """Test creating a new user."""
        user = User(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="es",
        )
        
        created_user = db_store.create_user(user)
        
        assert created_user.id is not None
        assert created_user.telegram_id == 123456
        assert created_user.username == "testuser"
    
    def test_get_user_by_telegram_id(self, db_store):
        """Test retrieving a user by Telegram ID."""
        # Create user first
        user = User(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
        )
        db_store.create_user(user)
        
        # Retrieve user
        retrieved = db_store.get_user_by_telegram_id(123456)
        
        assert retrieved is not None
        assert retrieved.telegram_id == 123456
        assert retrieved.first_name == "Test"
    
    def test_get_nonexistent_user(self, db_store):
        """Test retrieving a user that doesn't exist."""
        retrieved = db_store.get_user_by_telegram_id(999999)
        
        assert retrieved is None
    
    def test_get_or_create_user_creates(self, db_store):
        """Test get_or_create_user creates new user."""
        user = db_store.get_or_create_user(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
        )
        
        assert user.id is not None
        assert user.telegram_id == 123456
    
    def test_get_or_create_user_returns_existing(self, db_store):
        """Test get_or_create_user returns existing user."""
        # Create user first
        db_store.get_or_create_user(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
        )
        
        # Get same user
        user = db_store.get_or_create_user(
            telegram_id=123456,
            username="testuser_updated",
            first_name="Test Updated",
        )
        
        # Should be same user but with updated info
        assert user.telegram_id == 123456
    
    def test_get_user_preferences(self, db_store):
        """Test retrieving user preferences."""
        # Create user first
        db_store.get_or_create_user(
            telegram_id=123456,
            first_name="Test",
        )
        
        # Get preferences
        prefs = db_store.get_user_preferences(123456)
        
        assert prefs is not None
        assert prefs.household_size == 1  # default
        assert prefs.budget_level == "medium"  # default
    
    def test_update_user_preferences(self, db_store):
        """Test updating user preferences."""
        # Create user first
        db_store.get_or_create_user(
            telegram_id=123456,
            first_name="Test",
        )
        
        # Update preferences
        new_prefs = {
            "dietary_restrictions": ["vegetariano", "sin gluten"],
            "allergies": ["frutos secos"],
            "household_size": 4,
            "budget_level": "high",
        }
        
        updated = db_store.update_user_preferences(123456, new_prefs)
        
        assert updated is not None
        assert "vegetariano" in updated.dietary_restrictions
        assert "sin gluten" in updated.dietary_restrictions
        assert "frutos secos" in updated.allergies
        assert updated.household_size == 4
        assert updated.budget_level == "high"
    
    def test_clear_user_preferences(self, db_store):
        """Test clearing user preferences."""
        # Create user and set preferences
        db_store.get_or_create_user(
            telegram_id=123456,
            first_name="Test",
        )
        db_store.update_user_preferences(123456, {
            "dietary_restrictions": ["vegetariano"],
            "household_size": 4,
        })
        
        # Clear preferences
        result = db_store.clear_user_preferences(123456)
        
        assert result is True
        
        # Verify preferences are cleared
        prefs = db_store.get_user_preferences(123456)
        assert prefs.dietary_restrictions == []
        assert prefs.household_size == 1
    
    def test_delete_user(self, db_store):
        """Test deleting a user."""
        # Create user first
        db_store.get_or_create_user(
            telegram_id=123456,
            first_name="Test",
        )
        
        # Delete user
        result = db_store.delete_user(123456)
        
        assert result is True
        
        # Verify user is deleted
        user = db_store.get_user_by_telegram_id(123456)
        assert user is None
    
    def test_get_user_count(self, db_store):
        """Test getting the user count."""
        # Initially empty
        assert db_store.get_user_count() == 0
        
        # Add users
        db_store.get_or_create_user(telegram_id=1, first_name="User1")
        db_store.get_or_create_user(telegram_id=2, first_name="User2")
        db_store.get_or_create_user(telegram_id=3, first_name="User3")
        
        assert db_store.get_user_count() == 3


class TestUserPreferencesModel:
    """Tests for the UserPreferences model."""
    
    def test_has_preferences_empty(self):
        """Test has_preferences returns False for default preferences."""
        prefs = UserPreferences(user_id=1)
        
        assert prefs.has_preferences() is False
    
    def test_has_preferences_with_restrictions(self):
        """Test has_preferences returns True when restrictions are set."""
        prefs = UserPreferences(
            user_id=1,
            dietary_restrictions=["vegetariano"],
        )
        
        assert prefs.has_preferences() is True
    
    def test_has_preferences_with_household_size(self):
        """Test has_preferences returns True when household_size differs."""
        prefs = UserPreferences(
            user_id=1,
            household_size=4,
        )
        
        assert prefs.has_preferences() is True
    
    def test_to_display_text(self):
        """Test converting preferences to display text."""
        prefs = UserPreferences(
            user_id=1,
            dietary_restrictions=["vegetariano", "sin gluten"],
            allergies=["frutos secos"],
            household_size=4,
            budget_level="high",
        )
        
        text = prefs.to_display_text()
        
        assert "vegetariano" in text
        assert "sin gluten" in text
        assert "frutos secos" in text
        assert "4" in text
        assert "Alto" in text


class TestUserModel:
    """Tests for the User model."""
    
    def test_create_user(self):
        """Test creating a User model."""
        user = User(
            telegram_id=123456,
            username="testuser",
            first_name="Test",
            last_name="User",
        )
        
        assert user.telegram_id == 123456
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.language_code == "es"  # default
    
    def test_user_with_timestamps(self):
        """Test User model with timestamps."""
        now = datetime.now(timezone.utc)
        user = User(
            telegram_id=123456,
            first_name="Test",
            created_at=now,
            updated_at=now,
        )
        
        assert user.created_at == now
        assert user.updated_at == now