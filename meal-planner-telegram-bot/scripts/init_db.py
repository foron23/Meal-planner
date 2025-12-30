#!/usr/bin/env python3
"""
Database Initialization Script

This script initializes the SQLite database for the Meal Planner Bot.
It creates all necessary tables and indexes if they don't exist.

Usage:
    python scripts/init_db.py [--db-path PATH]
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def init_database(db_path: str = "./data/meal_planner.db") -> None:
    """
    Initialize the database with required tables.
    
    Args:
        db_path: Path to the SQLite database file
    """
    # Ensure directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Initializing database at: {db_file.absolute()}")
    
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    
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
    print("✓ Created 'users' table")
    
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Created 'user_preferences' table")
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_telegram_id 
        ON users(telegram_id)
    """)
    print("✓ Created index 'idx_users_telegram_id'")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_preferences_user_id 
        ON user_preferences(user_id)
    """)
    print("✓ Created index 'idx_preferences_user_id'")
    
    connection.commit()
    connection.close()
    
    print(f"\n✅ Database initialized successfully!")
    print(f"   Location: {db_file.absolute()}")
    print(f"   Size: {db_file.stat().st_size} bytes")


def verify_database(db_path: str) -> bool:
    """
    Verify the database structure is correct.
    
    Args:
        db_path: Path to the SQLite database file
        
    Returns:
        True if database is valid, False otherwise
    """
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        required_tables = {"users", "user_preferences"}
        missing = required_tables - tables
        
        if missing:
            print(f"❌ Missing tables: {missing}")
            return False
        
        print("✓ All required tables exist")
        
        # Count records
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"   Users: {user_count}")
        
        cursor.execute("SELECT COUNT(*) FROM user_preferences")
        pref_count = cursor.fetchone()[0]
        print(f"   Preferences: {pref_count}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initialize the Meal Planner Bot database"
    )
    parser.add_argument(
        "--db-path",
        default="./data/meal_planner.db",
        help="Path to the SQLite database file (default: ./data/meal_planner.db)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify the database, don't create tables"
    )
    
    args = parser.parse_args()
    
    if args.verify:
        success = verify_database(args.db_path)
        sys.exit(0 if success else 1)
    else:
        init_database(args.db_path)
        verify_database(args.db_path)


if __name__ == "__main__":
    main()