"""
User models for the Meal Planner Bot.

This module defines Pydantic models for user data and preferences.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    """
    Represents a Telegram user.
    
    Attributes:
        id: Database primary key (auto-assigned)
        telegram_id: Unique Telegram user ID
        username: Telegram username (optional, may be None)
        first_name: User's first name
        last_name: User's last name (optional)
        language_code: Preferred language code (default: 'es')
        created_at: Account creation timestamp
        updated_at: Last update timestamp
    """
    id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    language_code: str = "es"
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class UserPreferences(BaseModel):
    """
    User's food and cooking preferences for personalized menu generation.
    
    Attributes:
        id: Database primary key
        user_id: Foreign key to users table
        dietary_restrictions: List of dietary restrictions (vegetarian, vegan, etc.)
        cuisine_preferences: Preferred cuisine types (mediterranean, asian, etc.)
        allergies: Food allergies (nuts, shellfish, etc.)
        disliked_ingredients: Ingredients the user doesn't like
        household_size: Number of people to cook for
        budget_level: Budget preference (low, medium, high)
        cooking_time_preference: Preferred cooking time (quick, medium, elaborate)
        caloric_needs: Daily caloric needs (optional)
        fitness_goals: Fitness or dietary goals
        protein_preference: Protein preference level
        extra_data: Additional flexible preferences as JSON
        updated_at: Last update timestamp
    """
    id: Optional[int] = None
    user_id: Optional[int] = None
    dietary_restrictions: List[str] = Field(default_factory=list)
    cuisine_preferences: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    disliked_ingredients: List[str] = Field(default_factory=list)
    household_size: int = Field(default=1, ge=1, le=20)
    budget_level: Literal["low", "medium", "high"] = "medium"
    cooking_time_preference: Literal["quick", "medium", "elaborate"] = "medium"
    caloric_needs: Optional[int] = None
    fitness_goals: Optional[str] = None
    protein_preference: Optional[str] = None
    extra_data: dict = Field(default_factory=dict)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
    
    def has_preferences(self) -> bool:
        """Check if the user has any preferences set."""
        return bool(
            self.dietary_restrictions or
            self.cuisine_preferences or
            self.allergies or
            self.disliked_ingredients or
            self.household_size != 1 or
            self.budget_level != "medium" or
            self.cooking_time_preference != "medium" or
            self.caloric_needs or
            self.fitness_goals or
            self.protein_preference or
            self.extra_data
        )
    
    def to_display_text(self) -> str:
        """
        Convert preferences to a human-readable format in Spanish.
        
        Returns:
            Formatted string of preferences
        """
        lines = []
        
        if self.dietary_restrictions:
            lines.append(f"🥗 **Restricciones dietéticas:** {', '.join(self.dietary_restrictions)}")
        
        if self.cuisine_preferences:
            lines.append(f"🍳 **Preferencias de cocina:** {', '.join(self.cuisine_preferences)}")
        
        if self.allergies:
            lines.append(f"⚠️ **Alergias:** {', '.join(self.allergies)}")
        
        if self.disliked_ingredients:
            lines.append(f"👎 **No me gusta:** {', '.join(self.disliked_ingredients)}")
        
        lines.append(f"👥 **Personas en casa:** {self.household_size}")
        
        budget_display = {"low": "Bajo", "medium": "Medio", "high": "Alto"}
        lines.append(f"💰 **Presupuesto:** {budget_display[self.budget_level]}")
        
        time_display = {"quick": "Rápido (<30 min)", "medium": "Moderado (30-60 min)", "elaborate": "Elaborado (>60 min)"}
        lines.append(f"⏱️ **Tiempo de cocina:** {time_display[self.cooking_time_preference]}")
        
        if self.caloric_needs:
            lines.append(f"🔥 **Necesidades calóricas:** {self.caloric_needs} kcal")
        
        if self.fitness_goals:
            lines.append(f"💪 **Objetivos fitness:** {self.fitness_goals}")
        
        if self.protein_preference:
            lines.append(f"🥩 **Preferencia de proteína:** {self.protein_preference}")
        
        if self.extra_data:
            for key, value in self.extra_data.items():
                lines.append(f"📝 **{key}:** {value}")
        
        return "\n".join(lines)