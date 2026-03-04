from connexion import AsyncApp

from . import create_app

if __name__ == "__main__":
    app: AsyncApp = create_app()
    app.run(host="0.0.0.0", port=8080)
