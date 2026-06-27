from datetime import datetime
import json
import hashlib

from app.extensions import db


class Deployment(db.Model):
    __tablename__ = 'deployments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    pid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    api_key = db.Column(db.String(32), unique=True, nullable=False, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'pid': self.pid
        }

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(16))
    password = db.Column(db.String(32))
    api_key = db.Column(db.String(32), unique=True, index=True)

    def to_dict(self):
        return { 'username': self.username }

# another zatar comment: errrrrrdeeeeeeeeeeer