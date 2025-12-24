#!/usr/bin/env python
"""
migrate.py - Laravel-like migration commands for the Roommate Agreement Generator

Usage:
    python migrate.py migrate      # Run all pending migrations (like php artisan migrate)
    python migrate.py rollback     # Rollback last migration (like php artisan migrate:rollback)
    python migrate.py refresh      # Rollback all and re-run migrations (like php artisan migrate:refresh)
    python migrate.py status       # Show migration status (like php artisan migrate:status)
    python migrate.py make <name>  # Create new migration file (like php artisan make:migration)
    python migrate.py fresh        # Drop all tables and re-run migrations (like php artisan migrate:fresh)
"""
import sys
import os
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_alembic_command(args: list):
    """Run an alembic command."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    
    if args[0] == "upgrade":
        command.upgrade(alembic_cfg, args[1] if len(args) > 1 else "head")
    elif args[0] == "downgrade":
        command.downgrade(alembic_cfg, args[1] if len(args) > 1 else "-1")
    elif args[0] == "current":
        command.current(alembic_cfg, verbose=True)
    elif args[0] == "history":
        command.history(alembic_cfg, verbose=True)
    elif args[0] == "revision":
        message = args[1] if len(args) > 1 else "new migration"
        command.revision(alembic_cfg, message=message, autogenerate=True)


def migrate():
    """Run all pending migrations."""
    print("[MIGRATE] Running migrations...")
    run_alembic_command(["upgrade", "head"])
    print("[SUCCESS] Migrations completed!")


def rollback():
    """Rollback the last migration."""
    print("[ROLLBACK] Rolling back last migration...")
    run_alembic_command(["downgrade", "-1"])
    print("[SUCCESS] Rollback completed!")


def refresh():
    """Rollback all and re-run migrations."""
    print("[REFRESH] Refreshing database...")
    run_alembic_command(["downgrade", "base"])
    run_alembic_command(["upgrade", "head"])
    print("[SUCCESS] Database refreshed!")


def status():
    """Show migration status."""
    print("[STATUS] Migration Status:")
    print("-" * 50)
    run_alembic_command(["current"])
    print("-" * 50)
    print("\n[HISTORY] Migration History:")
    run_alembic_command(["history"])


def make(name: str):
    """Create a new migration file."""
    print(f"[CREATE] Creating new migration: {name}")
    run_alembic_command(["revision", name])
    print("[SUCCESS] Migration file created!")


def fresh():
    """Drop all tables and re-run migrations."""
    print("[FRESH] Dropping all tables and re-running migrations...")
    
    from app.config import get_settings
    from sqlalchemy import create_engine, text
    
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Get all table names
        result = conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        
        if tables:
            # Disable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            
            # Drop all tables
            for table in tables:
                print(f"  Dropping table: {table}")
                conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
            
            # Re-enable foreign key checks
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
    
    print("[SUCCESS] All tables dropped!")
    
    # Run migrations
    migrate()


def create_database():
    """Create the database if it doesn't exist."""
    print("[DATABASE] Creating database if not exists...")
    
    from app.config import get_settings
    import pymysql
    
    settings = get_settings()
    
    # Parse database URL to get connection params
    # Format: mysql+pymysql://user:pass@host:port/dbname
    url = settings.database_url
    parts = url.replace("mysql+pymysql://", "").split("/")
    db_name = parts[-1]
    host_part = parts[0]
    
    if "@" in host_part:
        auth, host_port = host_part.rsplit("@", 1)
        if ":" in auth:
            user, password = auth.split(":", 1)
        else:
            user, password = auth, ""
    else:
        user, password = "root", ""
        host_port = host_part
    
    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host, port = host_port, 3306
    
    try:
        conn = pymysql.connect(host=host, user=user, password=password, port=port)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        conn.close()
        print(f"[SUCCESS] Database '{db_name}' created/verified!")
        return True
    except Exception as e:
        print(f"[ERROR] Error creating database: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    if command == "migrate":
        create_database()
        migrate()
    elif command == "rollback":
        rollback()
    elif command == "refresh":
        refresh()
    elif command == "status":
        status()
    elif command == "make":
        if len(sys.argv) < 3:
            print("[ERROR] Please provide a migration name: python migrate.py make <name>")
            return
        make(sys.argv[2])
    elif command == "fresh":
        fresh()
    elif command == "db:create":
        create_database()
    else:
        print(f"[ERROR] Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
