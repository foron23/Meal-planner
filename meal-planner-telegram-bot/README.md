# 🍽️ Meal Planner Telegram Bot

Un bot de Telegram inteligente para planificación de menús, construido con Python, LangGraph y SQLite.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📋 Descripción

El Meal Planner Bot es un asistente conversacional que ayuda a los usuarios a planificar sus comidas de manera personalizada. Utiliza un agente de IA basado en LangGraph para generar propuestas de menús adaptadas a las preferencias, restricciones dietéticas y necesidades específicas de cada usuario.

### ✨ Características Principales

- 🤖 **Conversación Natural**: Interactúa en lenguaje natural para solicitar menús
- 🧠 **Memoria a Largo Plazo**: Recuerda tus preferencias entre sesiones
- 🥗 **Personalización**: Adapta menús según restricciones dietéticas, alergias y gustos
- 💾 **Persistencia SQLite**: Almacena conversaciones y preferencias de forma persistente
- 🐳 **Docker Ready**: Fácil despliegue con Docker y Docker Compose

## 🏗️ Arquitectura

```
┌─────────────────────┐
│   Telegram User     │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│              Telegram Bot API                │
└──────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│         python-telegram-bot (async)          │
│  ┌────────────────────────────────────────┐  │
│  │             Handlers Layer             │  │
│  │  /start  /menu  /preferences  /help    │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │         LangGraph Agent                │  │
│  │  ┌──────────┐    ┌──────────────────┐ │  │
│  │  │ Chatbot  │───▶│ Extract Prefs   │ │  │
│  │  │  (LLM)   │    │ (conditional)   │ │  │
│  │  └──────────┘    └──────────────────┘ │  │
│  │         │                              │  │
│  │    SqliteSaver (checkpoints)           │  │
│  └────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────┐  │
│  │           SQLite Database              │  │
│  │  users | user_preferences | checkpoints│  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────┐
│              OpenAI API (LLM)                │
└──────────────────────────────────────────────┘
```

## 📁 Estructura del Proyecto

```
meal-planner-telegram-bot/
├── src/
│   ├── bot.py                    # Punto de entrada principal
│   ├── config.py                 # Configuración con pydantic-settings
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py              # Handler /start
│   │   ├── menu.py               # Handler /menu y mensajes
│   │   └── memory.py             # Handler /preferences, /clear
│   ├── services/
│   │   ├── langgraph_agent.py    # Agente LangGraph con checkpoint
│   │   ├── sqlite_store.py       # Store para usuarios/preferencias
│   │   └── telegram_client.py    # Cliente Telegram (opcional)
│   ├── models/
│   │   ├── user.py               # Modelos User, UserPreferences
│   │   └── conversation.py       # Modelos de conversación
│   └── utils/
│       └── logger.py             # Configuración de logging
├── scripts/
│   └── init_db.py                # Script de inicialización de BD
├── tests/
│   ├── test_handlers.py
│   └── test_services.py
├── docs/
│   ├── spec.md                   # Especificación con DCRs
│   └── architecture.md           # Documentación de arquitectura
├── data/                         # Directorio para SQLite (creado automáticamente)
├── .env.example                  # Variables de entorno de ejemplo
├── requirements.txt              # Dependencias Python
├── pyproject.toml               # Configuración del proyecto
├── Dockerfile                    # Imagen Docker
├── docker-compose.yml           # Orquestación Docker
└── README.md                     # Este archivo
```

## 🚀 Guía de Instalación

### Prerrequisitos

- Python 3.10 o superior
- Token de Bot de Telegram (obtener de [@BotFather](https://t.me/BotFather))
- API Key de OpenAI (obtener de [OpenAI Platform](https://platform.openai.com/api-keys))

### Opción 1: Instalación Local

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd meal-planner-telegram-bot
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   .\venv\Scripts\activate   # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

5. **Inicializar la base de datos**
   ```bash
   python scripts/init_db.py
   ```

6. **Ejecutar el bot**
   ```bash
   python -m src.bot
   ```

### Opción 2: Despliegue con Docker

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd meal-planner-telegram-bot
   ```

2. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

3. **Construir y ejecutar con Docker Compose**
   ```bash
   docker-compose up -d --build
   ```

4. **Ver logs**
   ```bash
   docker-compose logs -f meal-planner-bot
   ```

5. **Detener el bot**
   ```bash
   docker-compose down
   ```

## ⚙️ Configuración

### Variables de Entorno

| Variable | Descripción | Requerida | Default |
|----------|-------------|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | ✅ | - |
| `OPENAI_API_KEY` | API key de OpenAI | ✅ | - |
| `LLM_MODEL` | Modelo de LLM | ❌ | `gpt-4o-mini` |
| `LLM_TEMPERATURE` | Temperatura del LLM | ❌ | `0.7` |
| `DATABASE_PATH` | Ruta a la BD SQLite | ❌ | `./data/meal_planner.db` |
| `LOG_LEVEL` | Nivel de logging | ❌ | `INFO` |

### Modelos de LLM Soportados

- `gpt-4o` - Mejor calidad, mayor costo
- `gpt-4o-mini` - Buen balance calidad/costo (recomendado)
- `gpt-4-turbo` - Alta calidad
- `gpt-3.5-turbo` - Económico

## 📱 Uso del Bot

### Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `/start` | Iniciar el bot y ver bienvenida |
| `/menu [descripción]` | Generar un menú |
| `/preferences` | Ver preferencias guardadas |
| `/help` | Ver ayuda detallada |
| `/clear` | Limpiar historial de conversación |
| `/clear_preferences` | Borrar todas las preferencias |

### Ejemplos de Uso

```
Usuario: /start
Bot: ¡Hola! Bienvenido al Bot de Planificación de Menús...

Usuario: Necesito ideas para una cena vegetariana para 4 personas
Bot: ¡Perfecto! Aquí tienes algunas opciones para tu cena vegetariana...

Usuario: Tengo alergia a los frutos secos
Bot: Entendido, he guardado esta información. Evitaré los frutos secos...

Usuario: /menu
Bot: Basándome en tus preferencias (vegetariano, 4 personas, sin frutos secos)...
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Ejecutar con cobertura
pytest --cov=src --cov-report=html

# Ejecutar tests específicos
pytest tests/test_handlers.py -v
```

## 🔧 Desarrollo

### Estructura del Agente LangGraph

El agente utiliza un grafo de estados con los siguientes nodos:

1. **load_preferences**: Carga preferencias del usuario desde la BD
2. **chatbot**: Genera respuesta usando el LLM
3. **extract_preferences**: Extrae nuevas preferencias del mensaje
4. **save_preferences**: Guarda preferencias en la BD

### Checkpointing

Los checkpoints de conversación se manejan automáticamente con `langgraph-checkpoint-sqlite`, permitiendo:
- Persistencia de conversaciones entre reinicios
- Historial de mensajes por usuario
- Recuperación de estado del agente

## 📊 Base de Datos

### Esquema

```sql
-- Usuarios
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    username TEXT,
    first_name TEXT,
    ...
);

-- Preferencias de usuario
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    dietary_restrictions TEXT,  -- JSON array
    allergies TEXT,             -- JSON array
    ...
);

-- Checkpoints (manejado por LangGraph)
-- Tabla creada automáticamente por langgraph-checkpoint-sqlite
```

## 🐳 Docker

### Comandos Útiles

```bash
# Construir imagen
docker build -t meal-planner-bot .

# Ejecutar contenedor
docker run -d --name meal-planner-bot --env-file .env meal-planner-bot

# Ver logs
docker logs -f meal-planner-bot

# Acceder al contenedor
docker exec -it meal-planner-bot /bin/bash

# Backup de la base de datos
docker cp meal-planner-bot:/app/data/meal_planner.db ./backup/
```

## 📝 Documentación Adicional

- [Especificación Técnica (DCRs)](docs/spec.md)
- [Arquitectura del Sistema](docs/architecture.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io/)

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [LangGraph](https://github.com/langchain-ai/langgraph) - Framework para agentes conversacionales
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Wrapper de la API de Telegram
- [OpenAI](https://openai.com/) - Modelos de lenguaje

---

**¿Preguntas?** Abre un issue en el repositorio.