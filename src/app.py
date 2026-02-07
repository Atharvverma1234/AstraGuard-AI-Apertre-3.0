"""
AstraGuard AI - Main FastAPI Application Entry Point.

This module serves as the primary entry point for production deployments using
Uvicorn. It imports the initialized `app` from `api.service` and configures
the server settings (host, port) for standalone execution.
"""

from api.service import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
