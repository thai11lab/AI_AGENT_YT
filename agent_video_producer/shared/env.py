"""Environment & API Key Resolver for Phase 2 Production Agents."""
import os
from pathlib import Path
from dotenv import load_dotenv

PHASE2_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PHASE2_ROOT.parent
PHASE1_ENV = WORKSPACE_ROOT / "agent_script_writer" / ".env"
PHASE2_ENV = PHASE2_ROOT / ".env"

if PHASE1_ENV.exists():
    load_dotenv(PHASE1_ENV)
if PHASE2_ENV.exists():
    load_dotenv(PHASE2_ENV, override=True)


def get_env_key(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()
