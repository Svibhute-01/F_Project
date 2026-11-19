import os
from dotenv import load_dotenv

load_dotenv()

# LLM provider used for code generation and QA planning. Groq is the default for
# lower-latency generation; Gemini remains available as a fallback/provider choice.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MODEL_NAME = GEMINI_MODEL  # backwards-compatible alias used by older integrations
MAX_RETRIES = 3
QA_AUTO_REPAIR_ROUNDS = max(0, min(3, int(os.getenv("QA_AUTO_REPAIR_ROUNDS", "2"))))

if LLM_PROVIDER not in {"groq", "gemini"}:
    raise ValueError("LLM_PROVIDER must be either 'groq' or 'gemini'.")
if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Add it to Developer_Agent/.env or set LLM_PROVIDER=gemini.")
if LLM_PROVIDER == "gemini" and not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing. Add it to Developer_Agent/.env or set LLM_PROVIDER=groq.")

from pathlib import Path

WORKSPACES_DIR = Path(os.getenv("WORKSPACES_DIR") or Path(__file__).resolve().parent.parent / "workspaces")
JOBS_DIR = Path(os.getenv("JOBS_DIR") or Path(__file__).resolve().parent.parent / "jobs")
SERVICE_KEY = os.getenv("DEVELOPER_SERVICE_KEY", "")
VECTORSTORE_DIR = Path(__file__).resolve().parent.parent / "vectorstore"
EMBEDDING_MODEL = "models/gemini-embedding-001"
RETRIEVAL_K = 5
CONTEXT_MODE = os.getenv("CONTEXT_MODE", "all_files")
RUNNER_MODE = os.getenv("RUNNER_MODE", "local").lower()
PYTHON_IMAGE = os.getenv("PYTHON_IMAGE", "python:3.12-slim")
NODE_IMAGE = os.getenv("NODE_IMAGE", "node:20-slim")
DOCKER_MEMORY = os.getenv("DOCKER_MEMORY", "1g")
DOCKER_CPUS = os.getenv("DOCKER_CPUS", "2")
SMOKE_CHECK = os.getenv("SMOKE_CHECK", "true").lower() != "false"
APP_PORT_RANGE = (9100, 9199)
APP_TTL_SECONDS = int(os.getenv("APP_TTL_SECONDS", "900"))
APP_PUBLIC_HOST = os.getenv("APP_PUBLIC_HOST", "127.0.0.1")
APPS_DIR = Path(os.getenv("APPS_DIR") or Path(__file__).resolve().parent.parent / "jobs" / "apps")
PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR") or Path(__file__).resolve().parent.parent / "jobs" / "projects")

def _seconds(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError:
        return default
    return value if value > 0 else default

INSTALL_TIMEOUT_SECONDS = _seconds("INSTALL_TIMEOUT_SECONDS", 600)
IMPORT_TIMEOUT_SECONDS = _seconds("IMPORT_TIMEOUT_SECONDS", 60)
TEST_TIMEOUT_SECONDS = _seconds("TEST_TIMEOUT_SECONDS", 300)
CACHE_DIR = Path(os.getenv("CACHE_DIR") or Path(__file__).resolve().parent.parent / "cache").resolve()
