from datetime import datetime
from extensions import db, bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str):
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat(),
        }


# New Translation model
class Translation(db.Model):
    __tablename__ = "translations"

    id = db.Column(db.Integer, primary_key=True)
    isizulu_text = db.Column(db.Text, nullable=False)
    english_text = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "isizulu": self.isizulu_text,
            "english": self.english_text,
        }

class RevokedToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(120), unique=True, nullable=False)  # JWT ID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, jti):
        self.jti = jti


class ZuluEnglishPair(db.Model):
    __tablename__ = 'zulu_english_pairs'
    
    id = db.Column(db.Integer, primary_key=True)
    isiZulu = db.Column(db.Text, nullable=False)
    English = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'isiZulu': self.isiZulu,
            'English': self.English,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<ZuluEnglishPair {self.id}>'


    @classmethod
    def is_jti_blacklisted(cls, jti):
        return db.session.query(cls.id).filter_by(jti=jti).scalar() 