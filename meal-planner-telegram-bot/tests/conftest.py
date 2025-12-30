"""
Pytest configuration and fixtures for the Meal Planner Bot tests.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def temp_db_path():
    """Create a temporary database path for the test session."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("OPENAI_API_KEY", "test_api_key")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "es",
    }


@pytest.fixture
def sample_preferences():
    """Sample preferences data for testing."""
    return {
        "dietary_restrictions": ["vegetariano", "sin gluten"],
        "cuisine_preferences": ["mediterránea", "mexicana"],
        "allergies": ["frutos secos", "mariscos"],
        "disliked_ingredients": ["cilantro", "aceitunas"],
        "household_size": 4,
        "budget_level": "medium",
        "cooking_time_preference": "quick",
    }
