"""Contour API serverless package for Vercel deployment.

The bootstrap logic lives directly in index.py because Vercel's resolver
imports the entrypoint by file path without executing this __init__.
"""
