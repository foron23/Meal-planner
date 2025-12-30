import json


def test_create_and_get_user(tmp_path):
    """Create a user and retrieve it via telegram_id."""
    from src.services.sqlite_store import SQLiteStore

    db_path = tmp_path / "test_store.db"
    store = SQLiteStore(str(db_path))

    # No users initially
    assert store.get_user_count() == 0

    user = store.get_or_create_user(telegram_id=123456, username="tester", first_name="Test")
    assert user is not None
    assert user.id is not None

    fetched = store.get_user_by_telegram_id(123456)
    assert fetched is not None
    assert fetched.telegram_id == 123456
    assert store.get_user_count() == 1


def test_update_and_get_preferences(tmp_path):
    """Update preferences and verify persisted values are readable."""
    from src.services.sqlite_store import SQLiteStore

    db_path = tmp_path / "test_store.db"
    store = SQLiteStore(str(db_path))

    tid = 555001
    store.get_or_create_user(telegram_id=tid, first_name="PrefsUser")

    prefs = {
        "caloric_needs": 2500,
        "fitness_goals": "muscle",
        "dietary_restrictions": ["gluten"],
        "extra_note": "likes spicy",
    }

    updated = store.update_user_preferences(tid, prefs)
    assert updated is not None
    assert updated.caloric_needs == 2500
    assert updated.fitness_goals == "muscle"
    # dietary_restrictions stored as list
    assert isinstance(updated.dietary_restrictions, list)
    assert "gluten" in updated.dietary_restrictions
    # unknown keys end up in extra_data
    assert updated.extra_data.get("extra_note") == "likes spicy"


def test_clear_preferences(tmp_path):
    """Verify clearing preferences resets values to defaults."""
    from src.services.sqlite_store import SQLiteStore

    db_path = tmp_path / "test_store.db"
    store = SQLiteStore(str(db_path))

    tid = 900900
    store.get_or_create_user(telegram_id=tid, first_name="ClearUser")

    prefs = {"caloric_needs": 1800, "dietary_restrictions": ["vegan"]}
    store.update_user_preferences(tid, prefs)

    # Ensure updated
    before = store.get_user_preferences(tid)
    assert before is not None
    assert before.caloric_needs == 1800

    ok = store.clear_user_preferences(tid)
    assert ok is True

    after = store.get_user_preferences(tid)
    assert after is not None
    assert after.caloric_needs is None
    assert after.dietary_restrictions == []
