# config.py
import os
from datetime import timedelta

class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_PERMANENT = False
    REMEMBER_COOKIE_DURATION = timedelta(seconds=0)
    REMEMBER_COOKIE_REFRESH_EACH_REQUEST = False

def _build_default_db_uri():
    """
    Build a local Postgres URI from individual env vars (useful for development).
    Defaults:
      user: postgres
      password: postgres
      host: localhost
      port: 5432
      db: aviation_db
    """
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "postgres")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    db = os.environ.get("DB_NAME", "aviation_db")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

def _normalize_database_url(url: str) -> str:
    """
    Convert possible 'postgres://' URLs (e.g. from Heroku) to SQLAlchemy format
    'postgresql+psycopg2://'.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url

class DevConfig(BaseConfig):
    # Prefer explicit DATABASE_URL; otherwise build from DB_* env vars; fallback to local postgres.
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if raw:
        SQLALCHEMY_DATABASE_URI = _normalize_database_url(raw)
    else:
        SQLALCHEMY_DATABASE_URI = _build_default_db_uri()

    DEBUG = True

class ProdConfig(BaseConfig):
    # In production, expect DATABASE_URL env var (e.g. from hosting provider)
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
    if raw:
        SQLALCHEMY_DATABASE_URI = _normalize_database_url(raw)
    else:
        # As a safe fallback (not recommended for real prod), build from DB_* vars
        SQLALCHEMY_DATABASE_URI = _build_default_db_uri()

    DEBUG = False
