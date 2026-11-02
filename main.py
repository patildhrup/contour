"""Vercel entrypoint; deploy from the repository root to preserve package imports."""

from backend.main import app

__all__ = ['app']
