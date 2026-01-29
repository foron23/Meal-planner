# Meal Planner Telegram Bot Specification

## Overview
The Meal Planner Telegram Bot is designed to assist users in generating meal proposals based on their preferences and dietary requirements. The bot utilizes a Python backend, integrates with a LangGraph agent for natural language processing, and employs an SQLite3 database to maintain conversation states and long-term memory about users.

---

## Design Change Records (DCRs)

### DCR-001: Migración a LangGraph con Persistencia SQLite
- **Fecha**: 2024-12-28
- **Autor**: Development Team
- **Estado**: Implementado
- **Descripción**: Implementación del agente conversacional usando LangGraph con checkpointing en SQLite para persistencia de estado.
- **Justificación**: LangGraph proporciona un framework robusto para crear agentes conversacionales con estado, permitiendo memoria a largo plazo y gestión de conversaciones complejas.
- **Cambios**:
  - Integración de `langgraph` como framework principal del agente
  - Uso de `langgraph-checkpoint-sqlite` para persistencia de checkpoints
  - Implementación de memoria a largo plazo por usuario
  - Migración a `python-telegram-bot` v20+ (async)

### DCR-002: Arquitectura del Agente LangGraph
- **Fecha**: 2024-12-28
- **Autor**: Development Team
- **Estado**: Implementado
- **Descripción**: Diseño del grafo de estados para el agente de planificación de menús.
- **Componentes del Grafo**:
  - **State**: Estado compartido con mensajes de conversación y preferencias de usuario
  - **Nodes**: 
    - `chatbot`: Nodo principal que procesa mensajes con el LLM
    - `memory_retrieval`: Recupera preferencias del usuario
    - `memory_update`: Actualiza preferencias basadas en la conversación
  - **Edges**: Transiciones condicionales basadas en intención del usuario
- **Checkpointer**: SqliteSaver para persistir estado entre sesiones

### DCR-003: Sistema de Memoria a Largo Plazo
- **Fecha**: 2024-12-28
- **Autor**: Development Team
- **Estado**: Implementado
- **Descripción**: Implementación de memoria persistente para preferencias de usuario.
- **Características**:
  - Almacenamiento de preferencias dietéticas (vegetariano, vegano, alergias, etc.)
  - Historial de menús generados
  - Preferencias de cocina (mediterránea, asiática, etc.)
  - Restricciones alimentarias
- **Tecnología**: SQLite con tablas dedicadas para users y user_preferences

### DCR-004: Migración a python-telegram-bot v20+
- **Fecha**: 2024-12-28
- **Autor**: Development Team
- **Estado**: Implementado
- **Descripción**: Actualización a la versión asíncrona de python-telegram-bot.
- **Justificación**: La v20+ ofrece mejor rendimiento con async/await y es la versión mantenida activamente.
- **Cambios**:
  - Conversión de handlers síncronos a asíncronos
  - Uso de `Application` en lugar de `Updater`
  - Implementación de `ConversationHandler` para flujos complejos

### DCR-005: Sistema de Guardarraíles de Seguridad
- **Fecha**: 2026-01-29
- **Autor**: Development Team
- **Estado**: Implementado
- **Descripción**: Implementación de guardarraíles para prevenir el uso indebido del modelo LLM para propósitos no relacionados con planificación de menús.
- **Justificación**: Garantizar que el modelo solo se use para su propósito específico (planificación de comidas) y no para tareas arbitrarias como programación, matemáticas, tareas escolares, etc. Esto mejora la seguridad, reduce costos de API y mantiene la especialización del bot.
- **Componentes**:
  - **MealPlannerGuardrails**: Clase principal de validación
  - **Validación de Entrada**: Detecta y rechaza solicitudes fuera de tema antes de llamar al LLM
  - **Validación de Salida**: Verifica que las respuestas del LLM permanezcan en el tema
  - **LLM-as-a-Judge**: Clasificación inteligente para casos ambiguos
  - **Monitoreo**: Registra activaciones de guardarraíles para auditoría
- **Características de Seguridad**:
  - Detección de palabras clave prohibidas (código, matemáticas, tareas, etc.)
  - Análisis de patrones de código mediante expresiones regulares
  - Identificación de frases específicas que indican intenciones fuera del ámbito
  - **LLM-as-a-Judge**: Para mensajes ambiguos (>10 palabras sin keywords claros), usa el LLM para clasificar si es sobre comida
    - Modelo rápido (gpt-4o-mini) con temperatura 0 para consistencia
    - Solo rechaza con confianza alta/media
    - Estrategia "fail-open" para evitar falsos positivos
  - Mensajes de rechazo amigables que redirigen a los usuarios
  - Estadísticas de rechazo para análisis de seguridad
- **Prompt del Sistema Reforzado**: Instrucciones explícitas en el prompt del sistema para rechazar solicitudes no relacionadas con comida/nutrición

---

## Features

### User Interaction
- **Start Command** (`/start`): Inicia la conversación y muestra mensaje de bienvenida con instrucciones.
- **Help Command** (`/help`): Muestra comandos disponibles y ejemplos de uso.
- **Preferences Command** (`/preferences`): Permite ver y modificar preferencias guardadas.
- **Menu Command** (`/menu`): Solicita un menú con las preferencias actuales.
- **Clear Command** (`/clear`): Limpia el historial de conversación actual.
- **Natural Language**: El usuario puede enviar mensajes de texto libre para solicitar menús con características específicas.

### Menu Proposal Features
- Generación de menús personalizados basados en:
  - Número de personas
  - Tipo de comida (desayuno, almuerzo, cena)
  - Restricciones dietéticas (vegetariano, vegano, sin gluten, etc.)
  - Preferencias de cocina (mediterránea, asiática, mexicana, etc.)
  - Ingredientes disponibles
  - Presupuesto aproximado
  - Tiempo de preparación deseado

### Memory Features
- **Memoria de Conversación**: Mantiene contexto durante una sesión usando LangGraph checkpoints
- **Memoria a Largo Plazo**: Almacena preferencias del usuario entre sesiones
- **Aprendizaje de Preferencias**: Extrae preferencias de las conversaciones automáticamente

---

## Technical Architecture

### Backend Components

#### LangGraph Agent (`services/langgraph_agent.py`)
- **StateGraph**: Define el flujo de la conversación
- **State Schema**: 
  ```python
  class AgentState(TypedDict):
      messages: Annotated[list, add_messages]
      user_preferences: dict
      user_id: int
  ```
- **Nodes**:
  - `chatbot`: Procesa mensajes con OpenAI/Anthropic
  - `extract_preferences`: Extrae preferencias del mensaje
  - `save_preferences`: Guarda preferencias en BD
- **Checkpointer**: SqliteSaver para persistencia

#### SQLite Store (`services/sqlite_store.py`)
- Gestión de conexiones SQLite
- CRUD para usuarios y preferencias
- Integración con LangGraph checkpoint

#### Telegram Client (`services/telegram_client.py`)
- Wrapper async para python-telegram-bot
- Gestión de rate limiting
- Formateo de mensajes (Markdown)

### Data Models

#### User Model (`models/user.py`)
```python
class User(BaseModel):
    telegram_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    language_code: str = "es"
    created_at: datetime
    updated_at: datetime
```

#### UserPreferences Model (`models/user.py`)
```python
class UserPreferences(BaseModel):
    user_id: int
    dietary_restrictions: List[str] = []
    cuisine_preferences: List[str] = []
    allergies: List[str] = []
    household_size: int = 1
    budget_level: str = "medium"
    cooking_time_preference: str = "medium"
```

#### Conversation Model (`models/conversation.py`)
```python
class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
```

---

## Database Schema

### Tables

#### `users`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| telegram_id | INTEGER UNIQUE | Telegram user ID |
| username | TEXT | Telegram username |
| first_name | TEXT NOT NULL | User's first name |
| last_name | TEXT | User's last name |
| language_code | TEXT DEFAULT 'es' | Preferred language |
| created_at | TIMESTAMP | Creation date |
| updated_at | TIMESTAMP | Last update date |

#### `user_preferences`
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| user_id | INTEGER REFERENCES users(id) | FK to users |
| dietary_restrictions | TEXT (JSON) | Diet restrictions |
| cuisine_preferences | TEXT (JSON) | Cuisine types |
| allergies | TEXT (JSON) | Food allergies |
| household_size | INTEGER DEFAULT 1 | Number of people |
| budget_level | TEXT DEFAULT 'medium' | Budget preference |
| cooking_time_preference | TEXT DEFAULT 'medium' | Time preference |
| updated_at | TIMESTAMP | Last update |

#### `checkpoints` (LangGraph managed)
Managed automatically by `langgraph-checkpoint-sqlite`.

---

## API Integration

### LLM Provider
- **Primary**: OpenAI GPT-4 / GPT-3.5-turbo
- **Alternative**: Anthropic Claude
- **Configuration**: Via environment variables

### System Prompt
```
Eres un asistente experto en planificación de menús y nutrición. Tu objetivo es ayudar 
a los usuarios a crear menús personalizados según sus preferencias, restricciones 
dietéticas y necesidades específicas.

Cuando generes un menú:
1. Considera las preferencias del usuario almacenadas
2. Incluye información nutricional básica
3. Sugiere variaciones o sustituciones
4. Proporciona tiempos de preparación estimados
5. Responde siempre en español

Si el usuario menciona nuevas preferencias o restricciones, asegúrate de recordarlas
para futuras conversaciones.
```

---

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | ✅ | - |
| `OPENAI_API_KEY` | API key de OpenAI | ✅ | - |
| `DATABASE_PATH` | Ruta al archivo SQLite | ❌ | `./data/meal_planner.db` |
| `LOG_LEVEL` | Nivel de logging | ❌ | `INFO` |
| `LLM_MODEL` | Modelo de LLM a usar | ❌ | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | Temperatura del LLM | ❌ | `0.7` |

---

## Deployment

### Docker Deployment
```bash
# Build image
docker build -t meal-planner-bot .

# Run with docker-compose
docker-compose up -d
```

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run bot
python src/bot.py
```

---

## Testing Strategy

### Unit Tests
- `tests/test_handlers.py`: Tests para command handlers
- `tests/test_services.py`: Tests para servicios (agent, store)
- `tests/test_models.py`: Tests para modelos de datos

### Integration Tests
- Test de flujo completo de conversación
- Test de persistencia de checkpoints
- Test de memoria a largo plazo

### Mocking
- Mock de API de Telegram
- Mock de LLM para tests determinísticos

---

## Security Considerations

1. **API Keys**: Almacenadas en variables de entorno, nunca en código
2. **Database**: Archivo SQLite con permisos restrictivos
3. **User Data**: Mínima información personal almacenada
4. **Rate Limiting**: Implementado para prevenir abuso
5. **Input Validation**: Sanitización de inputs del usuario
6. **Guardarraíles de Modelo**: Sistema de validación que previene el uso del LLM para propósitos no relacionados con planificación de menús
   - Validación de entrada para detectar solicitudes fuera de tema
   - Validación de salida para asegurar respuestas apropiadas
   - Rechazo de solicitudes de programación, matemáticas, tareas escolares, etc.
   - Logging y monitoreo de intentos de uso indebido
   - Prompt del sistema reforzado con límites estrictos

---

## Future Enhancements

- [ ] Integración con APIs de recetas externas
- [ ] Generación de listas de compras
- [ ] Integración con supermercados online
- [ ] Soporte para múltiples idiomas
- [ ] Exportación de menús a PDF
- [ ] Integración con calendarios
- [ ] Notificaciones programadas de menús