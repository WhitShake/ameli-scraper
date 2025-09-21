#src/database.py
# sqlalchemy provides a way to communicate across many database types (SQLite, MySQL, Oracle, etc)
#create_engine - interface to talk to a database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Provides the details (url) needed to connect to the database
SQLALCHEMY_DATABASE_URL = "sqlite:///./ameli_providers.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Only needed for SQLite
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# This will be the base class for our ORM models
Base = declarative_base()
