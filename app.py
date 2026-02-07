"""Flask application entry point."""
from __future__ import annotations

import logging
from flask import Flask

from webhook import webhook_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(webhook_bp)

    @app.route("/")
    def healthcheck():
        return "Water Wallet WhatsApp skeleton is running."

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(port=5000, debug=True)
