from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()


def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    migrate = Migrate(app, db)
    return db
