"""
Flask application factory and configuration.

This module creates and configures the Flask application instance.
"""

import os
from flask import Flask


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = os.environ.get(
        "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
    )

    # Initialize database
    from app.models import init_db

    init_db()

    # Register blueprints
    from app.routes import main_bp

    app.register_blueprint(main_bp)

    return app
