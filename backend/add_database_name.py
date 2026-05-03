"""Migration: add database_name column to data_types table."""
from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)

# Check if column already exists
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = 'data_types' AND column_name = 'database_name'"
    ))
    if result.scalar() > 0:
        print("database_name column already exists")
    else:
        conn.execute(text("ALTER TABLE data_types ADD COLUMN database_name VARCHAR(255) DEFAULT NULL"))
        conn.commit()
        print("database_name column added")
