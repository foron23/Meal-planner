"""
LangGraph Agent for the Meal Planner Bot.

This module implements the conversational AI agent using LangGraph with SQLite
checkpoint persistence for maintaining conversation state and long-term memory.
"""

import json
import logging
import sqlite3
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from src.config import (
    PREFERENCE_EXTRACTION_PROMPT,
    SYSTEM_PROMPT,
    get_settings,
)
from src.models.user import UserPreferences
from src.services.sqlite_store import SQLiteStore
from src.services.guardrails import MealPlannerGuardrails

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """
    State schema for the LangGraph agent.
    
    Attributes:
        messages: Conversation history with automatic message aggregation
        user_preferences: Current user preferences loaded from database
        user_id: Telegram user ID for database lookups
        extracted_preferences: Newly extracted preferences from current message
        should_save_preferences: Flag indicating if preferences should be saved
    """
    messages: Annotated[list[BaseMessage], add_messages]
    user_preferences: dict[str, Any]
    user_id: int
    extracted_preferences: dict[str, Any]
    should_save_preferences: bool


class MealPlannerAgent:
    """
    LangGraph-based conversational agent for meal planning.
    
    This agent uses a state graph to manage conversations, with nodes for:
    - Loading user preferences from long-term memory
    - Generating responses using an LLM
    - Extracting and saving new preferences
    
    Conversation state is persisted using SQLite checkpoints, allowing
    conversations to resume across bot restarts.
    """
    
    def __init__(self, db_store: SQLiteStore):
        """
        Initialize the Meal Planner Agent.
        
        Args:
            db_store: SQLite store instance for user data persistence
        """
        self.settings = get_settings()
        self.db_store = db_store
        
        # Initialize guardrails
        self.guardrails = MealPlannerGuardrails()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
            api_key=self.settings.openai_api_key,
        )
        
        # Initialize checkpoint saver for conversation persistence
        # Create a persistent connection for the checkpointer
        checkpoint_db_path = self.settings.database_path.replace(".db", "_checkpoints.db")
        self._checkpoint_conn = sqlite3.connect(checkpoint_db_path, check_same_thread=False)
        self.checkpointer = SqliteSaver(self._checkpoint_conn)
        
        # Build the graph
        self.graph = self._build_graph()
        
        logger.info("MealPlannerAgent initialized successfully")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state graph.
        
        Returns:
            Compiled StateGraph with all nodes and edges configured
        """
        # Create the graph with our state schema
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("load_preferences", self._load_preferences_node)
        graph.add_node("chatbot", self._chatbot_node)
        graph.add_node("extract_preferences", self._extract_preferences_node)
        graph.add_node("save_preferences", self._save_preferences_node)
        
        # Define edges
        graph.add_edge(START, "load_preferences")
        graph.add_edge("load_preferences", "chatbot")
        graph.add_conditional_edges(
            "chatbot",
            self._should_extract_preferences,
            {
                "extract": "extract_preferences",
                "end": END,
            }
        )
        graph.add_edge("extract_preferences", "save_preferences")
        graph.add_edge("save_preferences", END)
        
        # Compile with checkpointer for persistence
        return graph.compile(checkpointer=self.checkpointer)
    
    def _load_preferences_node(self, state: AgentState) -> dict[str, Any]:
        """
        Load user preferences from long-term storage.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with user preferences
        """
        user_id = state["user_id"]
        
        try:
            preferences = self.db_store.get_user_preferences(user_id)
            if preferences:
                pref_dict = preferences.model_dump(exclude={"id", "user_id", "updated_at"})
                logger.debug(f"Loaded preferences for user {user_id}: {pref_dict}")
                return {"user_preferences": pref_dict}
        except Exception as e:
            logger.warning(f"Failed to load preferences for user {user_id}: {e}")
        
        return {"user_preferences": {}}
    
    def _chatbot_node(self, state: AgentState) -> dict[str, Any]:
        """
        Generate a response using the LLM.
        
        Args:
            state: Current agent state with messages and preferences
            
        Returns:
            Updated state with new AI message
        """
        # Format preferences for the system prompt
        prefs = state.get("user_preferences", {})
        if prefs:
            pref_text = self._format_preferences(prefs)
        else:
            pref_text = "No hay preferencias guardadas aún."
        
        # Create system message with user context
        system_message = SystemMessage(content=SYSTEM_PROMPT.format(user_preferences=pref_text))
        
        # Combine system message with conversation history
        messages = [system_message] + list(state["messages"])
        
        # Limit conversation history
        max_history = self.settings.max_conversation_history
        if len(messages) > max_history + 1:  # +1 for system message
            messages = [messages[0]] + messages[-(max_history):]
        
        # Generate response
        try:
            response = self.llm.invoke(messages)
            logger.debug(f"Generated response: {response.content[:100]}...")
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            error_message = AIMessage(
                content="Lo siento, ha ocurrido un error al procesar tu mensaje. "
                "Por favor, intenta de nuevo más tarde."
            )
            return {"messages": [error_message]}
    
    def _should_extract_preferences(self, state: AgentState) -> Literal["extract", "end"]:
        """
        Determine if we should try to extract preferences from the conversation.
        
        Args:
            state: Current agent state
            
        Returns:
            "extract" if we should extract preferences, "end" otherwise
        """
        # Get the last user message
        messages = state.get("messages", [])
        user_messages = [m for m in messages if isinstance(m, HumanMessage)]
        
        if not user_messages:
            logger.info("No user messages found, skipping preference extraction")
            return "end"
        
        last_user_message = user_messages[-1].content.lower()
        logger.info(f"Checking message for preferences: '{last_user_message[:100]}...'")
        
        # Keywords that suggest preference information
        preference_keywords = [
            # Dietary restrictions
            "vegetariano", "vegano", "sin gluten", "celiaco", "alergia",
            "kosher", "halal", "lactosa", "intolerancia", "dieta", "keto",
            # Preferences
            "no me gusta", "prefiero", "me gusta", "no como", "evitar",
            "bajo en", "sin", "rico en", "alto en",
            # Household
            "somos", "personas", "familia", "niños", "adultos",
            # Budget/Time
            "presupuesto", "rápido", "fácil", "económico", "barato",
            # Cuisine
            "mediterráneo", "asiático", "mexicano", "italiano", "español",
            # Allergies
            "frutos secos", "mariscos", "huevo", "cacahuete", "soja",
            # Fitness/Health
            "calorías", "kcal", "proteína", "deportista", "gimnasio",
            "musculación", "adelgazar", "engordar", "peso", "fitness",
            "carbohidratos", "grasas", "saludable",
        ]
        
        if any(keyword in last_user_message for keyword in preference_keywords):
            logger.info(f"Preference keyword detected, will extract preferences")
            return "extract"
        
        logger.info("No preference keywords detected")
        return "end"
    
    def _extract_preferences_node(self, state: AgentState) -> dict[str, Any]:
        """
        Extract user preferences from the conversation.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with extracted preferences
        """
        logger.info("Starting preference extraction...")
        
        # Get the last user message
        messages = state.get("messages", [])
        user_messages = [m for m in messages if isinstance(m, HumanMessage)]
        
        if not user_messages:
            logger.warning("No user messages to extract preferences from")
            return {"extracted_preferences": {}, "should_save_preferences": False}
        
        last_message = user_messages[-1].content
        logger.info(f"Extracting preferences from: '{last_message[:100]}...'")
        
        try:
            # Use LLM to extract preferences
            extraction_prompt = PREFERENCE_EXTRACTION_PROMPT.format(message=last_message)
            response = self.llm.invoke([HumanMessage(content=extraction_prompt)])
            
            # Parse JSON response
            content = response.content.strip()
            logger.info(f"LLM extraction response: {content[:200]}...")
            
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            extracted = json.loads(content)
            
            if extracted:
                logger.info(f"Successfully extracted preferences: {extracted}")
                return {
                    "extracted_preferences": extracted,
                    "should_save_preferences": True,
                }
            else:
                logger.info("No preferences extracted (empty result)")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse preference extraction response: {e}, content: {content[:100]}")
        except Exception as e:
            logger.error(f"Preference extraction failed: {e}")
        
        return {"extracted_preferences": {}, "should_save_preferences": False}
    
    def _save_preferences_node(self, state: AgentState) -> dict[str, Any]:
        """
        Save extracted preferences to long-term storage.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with merged preferences
        """
        logger.info(f"Save preferences node called, should_save: {state.get('should_save_preferences')}")
        
        if not state.get("should_save_preferences"):
            logger.info("Skipping save - should_save_preferences is False")
            return {}
        
        user_id = state["user_id"]
        extracted = state.get("extracted_preferences", {})
        current = state.get("user_preferences", {})
        
        logger.info(f"User {user_id} - Current prefs: {current}, Extracted: {extracted}")
        
        if not extracted:
            logger.info("No extracted preferences to save")
            return {}
        
        try:
            # Merge extracted preferences with current
            merged = self._merge_preferences(current, extracted)
            logger.info(f"Merged preferences: {merged}")
            
            # Save to database
            self.db_store.update_user_preferences(user_id, merged)
            
            logger.info(f"Successfully saved preferences for user {user_id}")
            return {"user_preferences": merged}
        except Exception as e:
            logger.error(f"Failed to save preferences for user {user_id}: {e}")
        
        return {}
    
    def _merge_preferences(
        self,
        current: dict[str, Any],
        new: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge new preferences into current preferences.
        
        For list fields, new items are added if not already present.
        For scalar fields, new values replace old ones.
        
        Args:
            current: Current preferences
            new: New preferences to merge
            
        Returns:
            Merged preferences dictionary
        """
        merged = current.copy()
        
        list_fields = [
            "dietary_restrictions",
            "cuisine_preferences",
            "allergies",
            "disliked_ingredients",
        ]
        
        for key, value in new.items():
            if key in list_fields:
                existing = merged.get(key, [])
                if isinstance(value, list):
                    merged[key] = list(set(existing + value))
                else:
                    if value not in existing:
                        merged[key] = existing + [value]
            else:
                merged[key] = value
        
        return merged
    
    def _format_preferences(self, prefs: dict[str, Any]) -> str:
        """
        Format preferences dictionary into readable text.
        
        Args:
            prefs: User preferences dictionary
            
        Returns:
            Formatted string for inclusion in system prompt
        """
        parts = []
        
        if prefs.get("dietary_restrictions"):
            parts.append(f"- Restricciones dietéticas: {', '.join(prefs['dietary_restrictions'])}")
        
        if prefs.get("cuisine_preferences"):
            parts.append(f"- Preferencias de cocina: {', '.join(prefs['cuisine_preferences'])}")
        
        if prefs.get("allergies"):
            parts.append(f"- Alergias: {', '.join(prefs['allergies'])}")
        
        if prefs.get("disliked_ingredients"):
            parts.append(f"- Ingredientes que no le gustan: {', '.join(prefs['disliked_ingredients'])}")
        
        if prefs.get("household_size"):
            parts.append(f"- Tamaño del hogar: {prefs['household_size']} personas")
        
        if prefs.get("budget_level"):
            budget_map = {"low": "bajo", "medium": "medio", "high": "alto"}
            parts.append(f"- Presupuesto: {budget_map.get(prefs['budget_level'], prefs['budget_level'])}")
        
        if prefs.get("cooking_time_preference"):
            time_map = {"quick": "rápido", "medium": "moderado", "elaborate": "elaborado"}
            parts.append(f"- Tiempo de cocina preferido: {time_map.get(prefs['cooking_time_preference'], prefs['cooking_time_preference'])}")
        
        return "\n".join(parts) if parts else "No hay preferencias guardadas."
    
    async def invoke(
        self,
        message: str,
        user_id: int,
        thread_id: str | None = None
    ) -> str:
        """
        Process a user message and generate a response.
        
        Args:
            message: User's message text
            user_id: Telegram user ID
            thread_id: Optional thread ID for conversation tracking (defaults to user_id)
            
        Returns:
            AI-generated response text
        """
        # Validate input with guardrails
        is_valid, rejection_reason = self.guardrails.validate_input(message)
        if not is_valid:
            logger.warning(f"Input rejected by guardrails for user {user_id}: {rejection_reason}")
            return self.guardrails.get_rejection_message(rejection_reason)
        
        if thread_id is None:
            thread_id = str(user_id)
        
        # Configure the thread for checkpoint persistence
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }
        
        # Initial state with the user message
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "user_preferences": {},
            "extracted_preferences": {},
            "should_save_preferences": False,
        }
        
        try:
            # Invoke the graph
            result = self.graph.invoke(initial_state, config)
            
            # Extract the last AI message
            ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
            if ai_messages:
                response = ai_messages[-1].content
                
                # Validate output with guardrails
                if not self.guardrails.validate_output(response):
                    logger.warning(f"Output rejected by guardrails for user {user_id}")
                    return self.guardrails.get_rejection_message("output_validation_failed")
                
                return response
            
            return "Lo siento, no pude generar una respuesta."
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            raise
    
    def clear_conversation(self, user_id: int, thread_id: str | None = None) -> bool:
        """
        Clear the conversation history for a user.
        
        Args:
            user_id: Telegram user ID
            thread_id: Optional thread ID (defaults to user_id)
            
        Returns:
            True if cleared successfully, False otherwise
        """
        if thread_id is None:
            thread_id = str(user_id)
        
        try:
            # Delete checkpoints for this thread from the database
            if hasattr(self, '_checkpoint_conn') and self._checkpoint_conn:
                cursor = self._checkpoint_conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
                self._checkpoint_conn.commit()
            logger.info(f"Cleared conversation for thread {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}")
            return False
    
    def close(self):
        """Close the agent and release resources."""
        try:
            if hasattr(self, '_checkpoint_conn') and self._checkpoint_conn:
                self._checkpoint_conn.close()
            logger.info("MealPlannerAgent closed")
        except Exception as e:
            logger.warning(f"Error closing agent: {e}")
    
    def get_guardrail_stats(self) -> dict:
        """
        Get guardrail statistics.
        
        Returns:
            Dictionary with guardrail activation statistics
        """
        return self.guardrails.get_stats()