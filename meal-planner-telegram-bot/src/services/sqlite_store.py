"""
SQLite Store for the Meal Planner Bot.

This module handles all database operations for users and their preferences.
Note: LangGraph checkpoints are managed separately by langgraph-checkpoint-sqlite.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.user import User, UserPreferences

logger = logging.getLogger(__name__)


class SQLiteStore:
    """
    SQLite database store for user data and preferences.
    
    This class manages:
    - User records (Telegram user information)
    - User preferences (dietary restrictions, allergies, etc.)
    
    LangGraph conversation checkpoints are handled separately by the
    langgraph-checkpoint-sqlite package.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the SQLite store.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        logger.info(f"SQLiteStore initialized with database at {db_path}")
    
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            SQLite connection with row factory configured
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    language_code TEXT DEFAULT 'es',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User preferences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                    dietary_restrictions TEXT DEFAULT '[]',
                    cuisine_preferences TEXT DEFAULT '[]',
                    allergies TEXT DEFAULT '[]',
                    disliked_ingredients TEXT DEFAULT '[]',
                    household_size INTEGER DEFAULT 1,
                    budget_level TEXT DEFAULT 'medium',
                    cooking_time_preference TEXT DEFAULT 'medium',
                    caloric_needs INTEGER,
                    fitness_goals TEXT,
                    protein_preference TEXT,
                    extra_data TEXT DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_telegram_id 
                ON users(telegram_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_preferences_user_id 
                ON user_preferences(user_id)
            """)
            
            conn.commit()
            logger.debug("Database schema initialized")
    
    # ==================== User Operations ====================
    
    def create_user(self, user: User) -> User:
        """
        Create a new user in the database.
        
        Args:
            user: User model to create
            
        Returns:
            Created user with assigned ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, language_code)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user.telegram_id,
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
            ))
            
            user.id = cursor.lastrowid
            conn.commit()
            
            # Create empty preferences for the user
            self._create_default_preferences(user.id)
            
            logger.info(f"Created user: {user.telegram_id}")
            return user
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get a user by their Telegram ID.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            User if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, telegram_id, username, first_name, last_name, 
                       language_code, created_at, updated_at
                FROM users WHERE telegram_id = ?
            """, (telegram_id,))
            
            row = cursor.fetchone()
            
            if row:
                return User(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    username=row["username"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    language_code=row["language_code"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                    updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
                )
            
            return None
    
    def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: str = "Usuario",
        last_name: Optional[str] = None,
        language_code: str = "es"
    ) -> User:
        """
        Get an existing user or create a new one.
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username (optional)
            first_name: User's first name
            last_name: User's last name (optional)
            language_code: Preferred language code
            
        Returns:
            Existing or newly created User
        """
        existing = self.get_user_by_telegram_id(telegram_id)
        
        if existing:
            # Update user info if changed
            if (existing.username != username or 
                existing.first_name != first_name or
                existing.last_name != last_name):
                self._update_user_info(telegram_id, username, first_name, last_name)
                existing.username = username
                existing.first_name = first_name
                existing.last_name = last_name
            return existing
        
        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        
        return self.create_user(new_user)
    
    def _update_user_info(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        last_name: Optional[str]
    ) -> None:
        """Update basic user information."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET username = ?, first_name = ?, last_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (username, first_name, last_name, telegram_id))
            
            conn.commit()
    
    def delete_user(self, telegram_id: int) -> bool:
        """
        Delete a user and their preferences.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            
            if deleted:
                logger.info(f"Deleted user: {telegram_id}")
            
            return deleted
    
    # ==================== Preferences Operations ====================
    
    def _create_default_preferences(self, user_id: int) -> None:
        """Create default preferences for a new user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_preferences (user_id)
                VALUES (?)
            """, (user_id,))
            
            conn.commit()
    
    def get_user_preferences(self, telegram_id: int) -> Optional[UserPreferences]:
        """
        Get preferences for a user by their Telegram ID.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            UserPreferences if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.id, p.user_id, p.dietary_restrictions, p.cuisine_preferences,
                       p.allergies, p.disliked_ingredients, p.household_size,
                       p.budget_level, p.cooking_time_preference, 
                       p.caloric_needs, p.fitness_goals, p.protein_preference,
                       p.extra_data, p.updated_at
                FROM user_preferences p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = ?
            """, (telegram_id,))
            
            row = cursor.fetchone()
            
            if row:
                return UserPreferences(
                    id=row["id"],
                    user_id=row["user_id"],
                    dietary_restrictions=json.loads(row["dietary_restrictions"]),
                    cuisine_preferences=json.loads(row["cuisine_preferences"]),
                    allergies=json.loads(row["allergies"]),
                    disliked_ingredients=json.loads(row["disliked_ingredients"]),
                    household_size=row["household_size"],
                    budget_level=row["budget_level"],
                    cooking_time_preference=row["cooking_time_preference"],
                    caloric_needs=row["caloric_needs"],
                    fitness_goals=row["fitness_goals"],
                    protein_preference=row["protein_preference"],
                    extra_data=json.loads(row["extra_data"]) if row["extra_data"] else {},
                    updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
                )
            
            return None
    
    def update_user_preferences(
        self,
        telegram_id: int,
        preferences: dict
    ) -> Optional[UserPreferences]:
        """
        Update preferences for a user. Creates the user if they don't exist.
        
        Args:
            telegram_id: Telegram user ID
            preferences: Dictionary of preferences to update
            
        Returns:
            Updated UserPreferences if successful, None otherwise
        """
        # Get or create the user
        user = self.get_user_by_telegram_id(telegram_id)
        if not user or user.id is None:
            # Create user automatically
            logger.info(f"Creating user {telegram_id} automatically for preferences update")
            user = self.get_or_create_user(
                telegram_id=telegram_id,
                first_name="Usuario",
            )
        
        if not user or user.id is None:
            logger.error(f"Failed to get or create user {telegram_id}")
            return None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query dynamically
            update_fields = []
            values = []
            extra_data = {}
            
            # Known field mappings
            field_mapping = {
                "dietary_restrictions": ("dietary_restrictions", json.dumps),
                "cuisine_preferences": ("cuisine_preferences", json.dumps),
                "allergies": ("allergies", json.dumps),
                "disliked_ingredients": ("disliked_ingredients", json.dumps),
                "household_size": ("household_size", int),
                "budget_level": ("budget_level", str),
                "cooking_time_preference": ("cooking_time_preference", str),
                "caloric_needs": ("caloric_needs", lambda x: int(x) if x else None),
                "fitness_goals": ("fitness_goals", str),
                "protein_preference": ("protein_preference", str),
            }
            
            for key, value in preferences.items():
                if key in field_mapping:
                    db_field, transform = field_mapping[key]
                    update_fields.append(f"{db_field} = ?")
                    try:
                        values.append(transform(value))
                    except (ValueError, TypeError):
                        values.append(value)
                else:
                    # Store unknown fields in extra_data
                    extra_data[key] = value
            
            # If we have extra data, update it
            if extra_data:
                # Get current extra_data and merge
                cursor.execute(
                    "SELECT extra_data FROM user_preferences WHERE user_id = ?", 
                    (user.id,)
                )
                row = cursor.fetchone()
                current_extra = json.loads(row["extra_data"]) if row and row["extra_data"] else {}
                current_extra.update(extra_data)
                update_fields.append("extra_data = ?")
                values.append(json.dumps(current_extra))
            
            if not update_fields:
                return self.get_user_preferences(telegram_id)
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user.id)
            
            query = f"""
                UPDATE user_preferences 
                SET {', '.join(update_fields)}
                WHERE user_id = ?
            """
            
            cursor.execute(query, values)
            conn.commit()
            
            logger.info(f"Updated preferences for user {telegram_id}: {list(preferences.keys())}")
            return self.get_user_preferences(telegram_id)
    
    def clear_user_preferences(self, telegram_id: int) -> bool:
        """
        Reset user preferences to defaults.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if reset, False if user not found
        """
        user = self.get_user_by_telegram_id(telegram_id)
        if not user or user.id is None:
            return False
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_preferences 
                SET dietary_restrictions = '[]',
                    cuisine_preferences = '[]',
                    allergies = '[]',
                    disliked_ingredients = '[]',
                    household_size = 1,
                    budget_level = 'medium',
                    cooking_time_preference = 'medium',
                    caloric_needs = NULL,
                    fitness_goals = NULL,
                    protein_preference = NULL,
                    extra_data = '{}',
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user.id,))
            
            conn.commit()
            
            logger.info(f"Cleared preferences for user {telegram_id}")
            return True
    
    # ==================== Utility Methods ====================
    
    def get_user_count(self) -> int:
        """Get the total number of users."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
    
    def close(self) -> None:
        """Close any open connections (if using connection pooling)."""
        logger.info("SQLiteStore closed")