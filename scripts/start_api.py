"""
Start FastAPI server

Quick script to start the API for testing.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
import os
from dotenv import load_dotenv

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    load_dotenv()

    port = int(os.getenv("PORT", "8000"))

    print("=" * 60)
    print("Form 13F AI Agent API")
    print("=" * 60)
    print(f"\n🚀 Starting server on http://localhost:{port}")
    print(f"📚 API Docs: http://localhost:{port}/docs")
    print(f"💚 Health Check: http://localhost:{port}/health")
    print(f"\nPress CTRL+C to stop\n")

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
