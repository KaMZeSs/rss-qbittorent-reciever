
import datetime

from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///./rss_downloader.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RSSFeed(Base):
    __tablename__ = "rss_feeds"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    keyword_filter = Column(String)
    qbit_category = Column(String)
    history = relationship("RSSHistory", back_populates="feed")

class RSSHistory(Base):
    __tablename__ = "rss_history"

    id = Column(Integer, primary_key=True, index=True)
    feed_id = Column(Integer, ForeignKey("rss_feeds.id"))
    feed = relationship("RSSFeed", back_populates="history")
    guid = Column(String, unique=True, index=True)
    title = Column(String)
    downloaded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    qbit_url = Column(String)
    qbit_username = Column(String)
    qbit_password = Column(String)
    rss_refresh_interval = Column(Integer, default=30)
    user_agent = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_and_migrate_db():
    from sqlalchemy import text
    with engine.connect() as connection:
        with connection.begin() as transaction:
            result = connection.execute(text("PRAGMA table_info(rss_history)"))
            columns = [row[1] for row in result]
            if 'created_at' not in columns:
                print("Database migration: 'created_at' column not found in 'rss_history'. Adding and backfilling.")
                connection.execute(text("ALTER TABLE rss_history ADD COLUMN created_at DATETIME"))
                connection.execute(text("UPDATE rss_history SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                print("Database migration complete.")
