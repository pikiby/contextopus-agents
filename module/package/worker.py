"""Core's persistent child entrypoint; no private server or database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agents.service import Service


def create_service(core):
    return Service(core)
