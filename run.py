"""
Entry point — run from project root:

    python run.py

Or via uvicorn for development:

    uvicorn run:app --reload --host 0.0.0.0 --port 8000
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Re-export the FastAPI app so uvicorn can find it as `run:app`
from src.api.main import app  # noqa: E402, F401

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=False)
