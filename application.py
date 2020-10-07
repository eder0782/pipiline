from app import application
from app import db
from app.controlers import funcoes_uteis as func


if __name__ == "__main__":
    db.create_all()
    # func.conta_thread()
    application.run(debug=True)
    # func.conta_thread()
    