"""Allow running ingestion as a module: python -m src.ingestion.ingest"""

from .ingest import main

if __name__ == "__main__":
    main()
