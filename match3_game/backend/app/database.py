from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./game.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nickname = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True)
    hashed_password = Column(String(200))
    avatar_url = Column(String(200), default="/assets/default_avatar.png")
    email_verified = Column(Integer, default=0)
    verification_code = Column(String(6), nullable=True)
    pts_multiplayer = Column(Integer, default=1000)
    pts_solo_record = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Integer, default=0)


class MatchHistory(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    player1_id = Column(Integer)
    player2_id = Column(Integer)
    winner_id = Column(Integer)
    player1_score = Column(Integer)
    player2_score = Column(Integer)
    pts_change = Column(Integer)
    played_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()