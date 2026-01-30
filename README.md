# Ssuljaengi - Webtoon Generation Pipeline

A high-quality webtoon/manhwa generation pipeline that converts story text into visual panel sequences using LangGraph and Google Gemini.

## Features

- **Story to Webtoon Conversion**: Automatically split stories into scenes and generate panel layouts
- **Character Extraction**: Extract and normalize character profiles from story text
- **Visual Planning**: Generate detailed visual plans with beat extraction and scene importance detection
- **Panel Generation**: Create panel plans with grammar-based composition rules
- **Image Generation**: Generate webtoon panels using Google Gemini with character reference images
- **Quality Control**: Built-in QC checks for panel distribution, dialogue ratio, and framing variety
- **Blind Testing**: Evaluate if generated panels effectively communicate the original story

## Architecture

The pipeline uses three LangGraph workflows:

1. **StoryBuildGraph**: Story text → Scenes + Characters + Visual Plan
2. **ScenePlanningGraph**: Scene → Panel Plan → Layout → Semantics
3. **SceneRenderGraph**: Semantics → Render Spec → Image

See [docs/task_list_improvements.md](docs/task_list_improvements.md) for detailed architecture documentation.

## Prerequisites

- Python 3.11+
- Google Cloud Project with Gemini API enabled, OR
- Gemini API Key

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/taigi0315/ssuljaengi_v4.git
cd ssuljaengi_v4
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
# Core dependencies
pip install -e .

# Development dependencies (testing, linting)
pip install -e ".[dev]"

# Optional: Telemetry/tracing support
pip install -e ".[telemetry]"
```

### 4. Configure environment variables

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see Environment Variables section below).

### 5. Initialize the database

```bash
# Run migrations
alembic upgrade head
```

### 6. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite+pysqlite:///./dev.db` | Database connection string |
| `GEMINI_API_KEY` | Yes* | - | Gemini API key (or use GCP auth) |
| `GOOGLE_CLOUD_PROJECT` | Yes* | - | GCP project ID (alternative to API key) |
| `GOOGLE_CLOUD_LOCATION` | No | `us-central1` | GCP region |
| `GEMINI_TEXT_MODEL` | No | `gemini-2.5-flash` | Text generation model |
| `GEMINI_IMAGE_MODEL` | No | `gemini-2.5-flash-image` | Image generation model |
| `GEMINI_FALLBACK_TEXT_MODEL` | No | `gemini-2.0-flash` | Fallback text model |
| `GEMINI_MAX_RETRIES` | No | `3` | Max retry attempts |
| `GEMINI_TIMEOUT_SECONDS` | No | `60` | Request timeout |
| `GEMINI_CIRCUIT_BREAKER_THRESHOLD` | No | `5` | Failures before circuit opens |
| `MEDIA_ROOT` | No | `./storage/media` | Local media storage path |
| `LOG_LEVEL` | No | `INFO` | Logging level |

*Either `GEMINI_API_KEY` or `GOOGLE_CLOUD_PROJECT` is required.

## API Usage

For a complete workflow guide and endpoint reference, see `docs/api.md`.

### Create a Project

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Webtoon"}'
```

### Create a Story (in a Project)

```bash
curl -X POST http://localhost:8000/v1/projects/{project_id}/stories \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Story",
    "default_story_style": "default",
    "default_image_style": "default"
  }'
```

### Generate a Story Blueprint (scenes + characters)

```bash
curl -X POST http://localhost:8000/v1/stories/{story_id}/generate/blueprint_async \
  -H "Content-Type: application/json" \
  -d '{
    "source_text": "Your story text here...",
    "max_scenes": 6,
    "panel_count": 3,
    "max_characters": 6
  }'
```

### Generate Full Scene Pipeline (planning + render)

```bash
curl -X POST http://localhost:8000/v1/scenes/{scene_id}/generate/full_async \
  -H "Content-Type: application/json" \
  -d '{"panel_count":3,"style_id":"default"}'
```

For full API documentation, visit `http://localhost:8000/docs` after starting the server.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_json_parsing.py -v

# Run with coverage
pytest --cov=app
```

### Code Style

```bash
# Format code
black app tests

# Lint code
ruff check app tests

# Type checking
mypy app
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Project Structure

```
ssuljaengi_v4/
├── app/
│   ├── api/v1/           # FastAPI endpoints
│   ├── config/           # Configuration files (layouts, grammars, styles)
│   ├── core/             # Core utilities (settings, telemetry)
│   ├── db/               # Database models and migrations
│   ├── graphs/           # LangGraph workflows
│   │   └── nodes/        # Graph node implementations
│   ├── prompts/          # Prompt templates (YAML)
│   ├── services/         # Business logic (Gemini, artifacts, storage)
│   └── main.py           # FastAPI app entry point
├── tests/                # Test suite
├── docs/                 # Documentation
├── storage/              # Local file storage
└── frontend/             # Frontend application (Next.js)
```

## Configuration Files

- `app/config/panel_grammar_library_v1.json` - Panel composition grammar rules
- `app/config/layout_templates_9x16_v1.json` - Vertical webtoon layout templates
- `app/config/layout_selection_rules_v1.json` - Layout selection decision rules
- `app/config/qc_rules_v1.json` - Quality control rules
- `app/config/story_styles.json` - Story genre/mood styles
- `app/config/image_styles.json` - Visual rendering styles
- `app/prompts/prompts.yaml` - LLM prompt templates

## License

MIT License
