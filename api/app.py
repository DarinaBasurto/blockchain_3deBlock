from flask import Flask


def create_app():
    app = Flask(__name__)

    # Necesario para usar mensajes flash
    app.secret_key = "3deblock-dev-key"

    from .routes import register_routes
    register_routes(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False,
        threaded=True
    )