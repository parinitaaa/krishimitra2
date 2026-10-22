# create_tables.py — applies migrations/*.sql in order, tracked in schema_migrations
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from services.db import SessionLocal, engine, Base
from models.price import MandiPrice  # registers MandiPrice with Base

def run_migrations():
    # Ensure Base models are registered
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"⚠️ Base.metadata.create_all note: {e}")

    backend_dir = Path(__file__).resolve().parent
    # Check both backend/migrations and root migrations/
    migrations_dir = backend_dir / "migrations"
    if not migrations_dir.exists():
        migrations_dir = backend_dir.parent / "migrations"

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found at {migrations_dir}")
        return False

    with SessionLocal() as db:
        # Create schema_migrations tracking table if missing
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version text PRIMARY KEY,
                applied_at timestamp with time zone DEFAULT now()
            )
        """))
        db.commit()

        # Find all .sql files sorted
        sql_files = sorted(migrations_dir.glob("*.sql"))
        print(f"Found {len(sql_files)} migration files in {migrations_dir}")

        for sql_file in sql_files:
            version = sql_file.name
            already_applied = db.execute(
                text("SELECT 1 FROM public.schema_migrations WHERE version = :ver"),
                {"ver": version}
            ).fetchone()

            if already_applied:
                print(f"[SKIP] Migration {version} already applied.")
                continue

            print(f"[RUN] Applying migration {version}...")
            content = sql_file.read_text(encoding="utf-8")
            
            # Execute migration content
            try:
                db.execute(text(content))
                db.execute(
                    text("INSERT INTO public.schema_migrations (version) VALUES (:ver)"),
                    {"ver": version}
                )
                db.commit()
                print(f"[OK] Applied migration {version} successfully.")
            except Exception as e:
                db.rollback()
                print(f"[ERROR] Migration {version} failed: {e}")
                raise e

    print("[DONE] All migrations verified and up to date.")
    return True

if __name__ == "__main__":
    run_migrations()