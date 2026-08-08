"""Run the JalNiti Flask app from the repository root.

Alternative, production-friendly invocations:
    flask run
    gunicorn jalniti.app:app
"""
from jalniti.app import app

if __name__ == "__main__":
    app.run(port=5000)