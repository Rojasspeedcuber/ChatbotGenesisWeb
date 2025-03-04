from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from services.db import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship with subscriptions
    subscriptions = db.relationship(
        'Subscription', backref='user', lazy='dynamic')

    def __init__(self, username, email, password, is_admin=False):
        self.username = username
        self.email = email
        self.set_password(password)
        self.is_admin = is_admin

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_active_subscription(self):
        """Check if user has an active subscription"""
        from models.subscription import Subscription
        active_sub = Subscription.query.filter_by(
            user_id=self.id,
            status='active'
        ).first()
        return active_sub is not None
