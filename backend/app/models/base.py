from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base — Alembic's env.py autogenerates against
    Base.metadata, so every model must inherit from this class."""
