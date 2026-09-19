import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_USERNAME = os.getenv("DB_USERNAME", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "3306")

if DB_HOST and DB_NAME and DB_USERNAME:
    DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
else:
    DATABASE_URL = "sqlite:///./redflag.db"

try:
    if "mysql" in DATABASE_URL:
        engine = create_engine(
            DATABASE_URL,
            pool_recycle=280,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
    else:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
except Exception as e:
    print(f"Warning: Failed to connect with MySQL URL, falling back to SQLite: {e}")
    DATABASE_URL = "sqlite:///./redflag.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(100), unique=True, index=True, nullable=True)
    name = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    is_verified = Column(Integer, default=1)
    picture = Column(Text, nullable=True)
    trial_used = Column(Integer, default=0, nullable=False)
    max_trials = Column(Integer, default=3, nullable=False)
    session_token = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        max_t = self.max_trials if self.max_trials is not None else 3
        used_t = self.trial_used if self.trial_used is not None else 0
        remaining = max(0, max_t - used_t)
        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "trial_used": used_t,
            "max_trials": max_t,
            "remaining_trials": remaining,
            "has_quota": remaining > 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player_name = Column(String(100), nullable=True)
    player_gender = Column(String(50), nullable=True)
    status = Column(String(50), default="in_progress") # in_progress, completed
    redflag_score = Column(Integer, nullable=True)
    category = Column(String(50), nullable=True)
    title_eval = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")

    def to_dict(self):
        return {
            "id": self.id,
            "player_name": self.player_name or "Pengguna",
            "player_gender": self.player_gender or "Laki-laki",
            "status": self.status,
            "redflag_score": self.redflag_score,
            "category": self.category or "Assessment Selesai",
            "title_eval": self.title_eval or "Evaluasi Percakapan",
            "created_at": self.created_at.strftime("%d %b %Y, %H:%M") if self.created_at else None
        }


class Visitor(Base):
    __tablename__ = "visitors"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(100), index=True, nullable=False)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SiteStats(Base):
    __tablename__ = "site_stats"

    stat_key = Column(String(50), primary_key=True)
    stat_value = Column(Integer, default=0, nullable=False)

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        total_views = db.query(SiteStats).filter(SiteStats.stat_key == "total_views").first()
        if not total_views:
            db.add(SiteStats(stat_key="total_views", stat_value=0))
        unique_views = db.query(SiteStats).filter(SiteStats.stat_key == "unique_visitors").first()
        if not unique_views:
            db.add(SiteStats(stat_key="unique_visitors", stat_value=0))
        db.commit()
    except Exception as e:
        print(f"Error initializing stats: {e}")
        db.rollback()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
