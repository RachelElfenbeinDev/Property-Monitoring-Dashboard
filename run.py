"""
Application entry point.

Run this script to start the Flask development server:
    python run.py

For production, use a WSGI server like Gunicorn:
    gunicorn -w 4 "app:create_app()" --bind 0.0.0.0:5000
"""

import os

from app import create_app

if __name__ == "__main__":
    app = create_app()
    
    # Get configuration from environment
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    
    app.run(host=host, port=port, debug=debug)
