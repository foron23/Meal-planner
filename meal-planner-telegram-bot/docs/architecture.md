# Architecture of the Meal Planner Telegram Bot

## Overview
The Meal Planner Telegram Bot is a conversational AI application that helps users plan their meals. Built with Python, it leverages LangGraph for intelligent conversation management, SQLite for persistence, and integrates with Telegram's Bot API.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM CLOUD                                  │
│                         (Bot API / Webhook/Polling)                         │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TELEGRAM BOT APPLICATION                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         bot.py (Entry Point)                         │   │
│  │                    python-telegram-bot v20+ async                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │                            HANDLERS LAYER                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   start.py  │  │   menu.py   │  │  memory.py  │  │   help.py   │  │  │
│  │  │  /start cmd │  │ /menu, text │  │/preferences │  │  /help cmd  │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────┼───────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │                           SERVICES LAYER                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    langgraph_agent.py                            │ │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐    │ │  │
│  │  │  │                   LangGraph StateGraph                   │    │ │  │
│  │  │  │  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │    │ │  │
│  │  │  │  │ retrieve │───▶│ chatbot  │───▶│ extract_prefs    │  │    │ │  │
│  │  │  │  │ memory   │    │  (LLM)   │    │ (conditional)    │  │    │ │  │
│  │  │  │  └──────────┘    └──────────┘    └──────────────────┘  │    │ │  │
│  │  │  │       │                                    │            │    │ │  │
│  │  │  │       └────────────────────────────────────┘            │    │ │  │
│  │  │  │                    SqliteSaver                          │    │ │  │
│  │  │  │              (checkpoint persistence)                   │    │ │  │
│  │  │  └─────────────────────────────────────────────────────────┘    │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐ │  │
│  │  │   sqlite_store.py    │  │        telegram_client.py            │ │  │
│  │  │  User/Prefs CRUD     │  │     Message formatting/sending       │ │  │
│  │  └──────────────────────┘  └──────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│  ┌───────────────────────────────────┼───────────────────────────────────┐  │
│  │                           DATA LAYER                                  │  │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐  │  │
│  │  │     models/*.py      │  │              SQLite DB               │  │  │
│  │  │  User, Preferences,  │  │  ┌────────────────────────────────┐ │  │  │
│  │  │    Conversation      │  │  │ users | user_preferences      │ │  │  │
│  │  │   (Pydantic models)  │  │  │ checkpoints (LangGraph)       │ │  │  │
│  │  └──────────────────────┘  │  └────────────────────────────────┘ │  │  │
│  │                            └──────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SERVICES                               │
│                     ┌───────────────────────────────┐                       │
│                     │     OpenAI API / LLM API      │                       │
│                     │   (GPT-4, GPT-3.5, Claude)    │                       │
│                     └───────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Entry Point (`src/bot.py`)
- **Responsibility**: Application bootstrap and lifecycle management
- **Technology**: python-telegram-bot v20+ (async)
- **Key Functions**:
  - Initialize Application with bot token
  - Register command handlers
  - Register message handlers
  - Start polling/webhook
  - Graceful shutdown handling

### 2. Handlers Layer (`src/handlers/`)

#### `start.py`
- Handles `/start` command
- Creates user record if not exists
- Sends welcome message with instructions

#### `menu.py`
- Handles `/menu` command and free-text messages
- Invokes LangGraph agent for menu generation
- Formats and sends response

#### `memory.py`
- Handles `/preferences` command
- Displays current user preferences
- Allows preference modification

#### `help.py`
- Handles `/help` command
- Displays available commands and usage examples

### 3. Services Layer (`src/services/`)

#### `langgraph_agent.py` - Core AI Logic
```python
# LangGraph State Definition
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_preferences: dict
    user_id: int
    should_update_preferences: bool

# Graph Structure
graph = StateGraph(AgentState)
graph.add_node("retrieve_memory", retrieve_memory_node)
graph.add_node("chatbot", chatbot_node)
graph.add_node("extract_preferences", extract_preferences_node)
graph.add_node("save_preferences", save_preferences_node)

# Edges
graph.add_edge(START, "retrieve_memory")
graph.add_edge("retrieve_memory", "chatbot")
graph.add_conditional_edges(
    "chatbot",
    should_extract_preferences,
    {"extract": "extract_preferences", "end": END}
)
graph.add_edge("extract_preferences", "save_preferences")
graph.add_edge("save_preferences", END)
```

**Key Features**:
- **Checkpointing**: Uses `SqliteSaver` from `langgraph-checkpoint-sqlite`
- **Thread Management**: Each Telegram chat is a unique thread_id
- **Memory Integration**: Retrieves user preferences before each response
- **Preference Extraction**: Automatically detects and saves new preferences

#### `sqlite_store.py` - Data Persistence
- Manages SQLite database connections
- CRUD operations for users and preferences
- Does NOT manage checkpoints (LangGraph handles that)

#### `guardrails.py` - Security & Input Validation
- **Input Validation**: Verifica que las solicitudes sean sobre planificación de menús
- **Output Validation**: Asegura que las respuestas permanezcan en el tema
- **Off-topic Detection**: Detecta y rechaza solicitudes de programación, matemáticas, tareas, etc.
- **Keywords & Patterns**: Usa análisis de palabras clave y patrones regex
- **LLM-as-a-Judge**: Clasificación inteligente para casos ambiguos usando el propio LLM
- **Statistics Tracking**: Registra rechazos para análisis de seguridad

**Tipos de Validación**:
- Detección de palabras clave prohibidas (código, matemáticas, tareas escolares)
- Análisis de patrones de código mediante regex
- Identificación de frases específicas fuera de tema
- **LLM-as-a-Judge para mensajes ambiguos**: Usa gpt-4o-mini para clasificar solicitudes sin palabras clave claras
- Verificación de que respuestas no contengan código o fórmulas matemáticas

**Flujo LLM-as-a-Judge**:
1. Validación basada en reglas (rápida, sin costo)
2. Si es ambiguo (mensaje largo sin keywords), consulta al LLM judge
3. LLM clasifica con confianza alta/media/baja
4. Solo rechaza si confianza es alta/media y NO es sobre comida
5. Estrategia "fail-open" en caso de error

#### `telegram_client.py` - Telegram Integration
- Message formatting (Markdown V2)
- Response chunking for long messages
- Error handling for API failures

### 4. Data Layer

#### Models (`src/models/`)

**User Model**:
```python
class User(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    language_code: str = "es"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**UserPreferences Model**:
```python
class UserPreferences(BaseModel):
    id: Optional[int] = None
    user_id: int
    dietary_restrictions: List[str] = Field(default_factory=list)
    cuisine_preferences: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    disliked_ingredients: List[str] = Field(default_factory=list)
    household_size: int = 1
    budget_level: Literal["low", "medium", "high"] = "medium"
    cooking_time_preference: Literal["quick", "medium", "elaborate"] = "medium"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

#### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT,
    language_code TEXT DEFAULT 'es',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    dietary_restrictions TEXT DEFAULT '[]',  -- JSON array
    cuisine_preferences TEXT DEFAULT '[]',   -- JSON array
    allergies TEXT DEFAULT '[]',             -- JSON array
    disliked_ingredients TEXT DEFAULT '[]',  -- JSON array
    household_size INTEGER DEFAULT 1,
    budget_level TEXT DEFAULT 'medium',
    cooking_time_preference TEXT DEFAULT 'medium',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_preferences_user_id ON user_preferences(user_id);
```

---

## Data Flow

### 1. New User Flow
```
User sends /start
       │
       ▼
start_handler receives Update
       │
       ▼
Check if user exists in DB
       │
       ├─── No ──▶ Create user record
       │              │
       ▼              ▼
Send welcome message with instructions
```

### 2. Menu Request Flow
```
User sends "Quiero un menú vegetariano para 4 personas"
       │
       ▼
menu_handler receives message
       │
       ▼
LangGraphAgent.invoke(message, user_id)
       │
       ├──▶ Input Validation (Guardrails)
       │         │
       │         ├── Check for off-topic keywords
       │         ├── Check for code patterns
       │         └── Validate meal-planning relevance
       │
       │    [If INVALID: Return rejection message]
       │    [If VALID: Continue processing]
       │
       ├──▶ retrieve_memory: Load user preferences from DB
       │
       ├──▶ chatbot: Generate response with LLM
       │         │
       │         ├── System prompt with context and strict boundaries
       │         ├── User preferences injected
       │         └── Conversation history from checkpoint
       │
       ├──▶ Output Validation (Guardrails)
       │         │
       │         └── Verify response stays on-topic
       │
       ├──▶ extract_preferences (if new prefs detected)
       │         │
       │         └── Parse "vegetariano, 4 personas"
       │
       └──▶ save_preferences (if extracted)
                 │
                 └── Update DB with new preferences
       │
       ▼
Format response as Telegram message
       │
       ▼
Send response to user
```

### 3. Memory Persistence Flow
```
Conversation Messages          User Preferences
       │                              │
       ▼                              ▼
   LangGraph                     SQLite DB
   Checkpoint                  (user_preferences)
       │                              │
       ▼                              ▼
langgraph-checkpoint-sqlite    sqlite_store.py
       │                              │
       └──────────────┬───────────────┘
                      │
                      ▼
              SQLite Database
           (meal_planner.db)
```

---

## Configuration (`src/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    
    # OpenAI
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    
    # Database
    database_path: str = "./data/meal_planner.db"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
```

---

## Error Handling

### Layers of Error Handling

1. **Handler Level**: Catches exceptions, logs, sends user-friendly messages
2. **Service Level**: Raises specific exceptions with context
3. **Database Level**: Handles connection errors, retries

### Error Types
- `TelegramError`: API communication failures
- `LLMError`: OpenAI/LLM API failures
- `DatabaseError`: SQLite operation failures
- `ValidationError`: Invalid user input

---

## Scalability Considerations

### Current Design (Single Instance)
- SQLite is suitable for single-bot deployment
- Polling mode for simplicity
- Async handlers for concurrent message processing

### Future Scaling Options
1. **Database**: Migrate to PostgreSQL with `langgraph-checkpoint-postgres`
2. **Deployment**: Multiple bot instances with shared DB
3. **Caching**: Redis for session caching
4. **Queue**: Message queue for high-volume processing

---

## Security

1. **Token Security**: Bot token in environment variables only
2. **Database Security**: SQLite file with restricted permissions (600)
3. **Input Sanitization**: All user input validated before processing
4. **Rate Limiting**: Telegram's built-in + optional custom limits
5. **Error Messages**: No sensitive information exposed to users
6. **Model Guardrails**: Sistema de validación multi-capa para prevenir uso indebido del LLM
   - **Pre-LLM Validation**: Rechaza solicitudes fuera de tema antes de invocar el modelo (ahorra costos)
   - **Post-LLM Validation**: Verifica que las respuestas permanezcan en el ámbito de planificación de menús
   - **Detection Mechanisms**:
     - Análisis de palabras clave (listas de permitidos/prohibidos)
     - Patrones regex para detectar código fuente
     - Identificación de frases específicas fuera de tema
     - Validación de bloques de código y notación matemática en salidas
   - **Logging & Monitoring**: Registra todos los rechazos para auditoría de seguridad
   - **User Experience**: Mensajes de rechazo amigables que redirigen a temas apropiados

---

## Testing Architecture

```
tests/
├── conftest.py                    # Pytest fixtures
├── test_handlers.py               # Handler unit tests
├── test_services.py               # Service unit tests
├── test_models_and_client.py      # Model validation tests
├── test_langgraph_agent.py        # LangGraph agent tests
├── test_guardrails.py             # Guardrails unit tests
├── test_guardrails_integration.py # Guardrails integration tests
├── test_sqlite_store.py           # SQLite store tests
└── test_telegram_client.py        # Telegram client tests
```

---

## Deployment Architecture

### Docker Deployment
```yaml
services:
  meal-planner-bot:
    build: .
    volumes:
      - ./data:/app/data  # SQLite persistence
    environment:
      - TELEGRAM_BOT_TOKEN
      - OPENAI_API_KEY
    restart: unless-stopped
```

### File Structure in Container
```
/app/
├── src/
│   ├── bot.py
│   ├── config.py
│   ├── handlers/
│   ├── services/
│   ├── models/
│   └── utils/
├── data/
│   └── meal_planner.db
└── requirements.txt
```