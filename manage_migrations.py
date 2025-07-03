#!/usr/bin/env python3
"""
Migration management CLI tool
Usage:
    python manage_migrations.py status      # Show migration status
    python manage_migrations.py pending     # List pending migrations
    python manage_migrations.py create <description>  # Create new migration
"""

import sys
import os
from datetime import datetime
from app.mongo_client import MongoDBClient
from app.db_migrations.migration_manager import MigrationManager


def get_next_version(migration_dir):
    """Get the next migration version number"""
    import re
    from pathlib import Path
    
    existing_versions = []
    for file in Path(migration_dir).glob("V*.py"):
        match = re.match(r"V(\d+)__", file.stem)
        if match:
            existing_versions.append(int(match.group(1)))
    
    if existing_versions:
        return f"V{max(existing_versions) + 1:03d}"
    else:
        return "V001"


def create_migration(description):
    """Create a new migration file"""
    from pathlib import Path
    
    # Clean description for filename
    clean_desc = description.lower().replace(" ", "_").replace("-", "_")
    clean_desc = ''.join(c for c in clean_desc if c.isalnum() or c == '_')
    
    migration_dir = Path("app/db_migrations")
    version = get_next_version(migration_dir)
    filename = f"{version}__{clean_desc}.py"
    filepath = migration_dir / filename
    
    template = f'''"""
Migration {version}: {description}
Created at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

import logging

logger = logging.getLogger(__name__)


def up(db):
    """
    Apply the migration: {description}
    
    Args:
        db: MongoDB database instance
    """
    # TODO: Implement your migration logic here
    pass


def down(db):
    """
    Rollback the migration (optional)
    
    Args:
        db: MongoDB database instance
    """
    # TODO: Implement rollback logic if needed
    pass
'''
    
    with open(filepath, 'w') as f:
        f.write(template)
    
    print(f"Created migration: {filepath}")
    print(f"Version: {version}")
    print(f"Description: {description}")


def show_status():
    """Show migration status"""
    client = MongoDBClient()
    manager = MigrationManager(client.db)
    
    print("\n=== Migration Status ===")
    
    # Get applied migrations
    history = manager.get_migration_history()
    print(f"\nApplied migrations: {len(history)}")
    for migration in history[:5]:  # Show last 5
        status = "✓" if migration.get("success") else "✗"
        print(f"{status} {migration['version']} - {migration['description']} (executed: {migration['executed_at']})")
    
    if len(history) > 5:
        print(f"... and {len(history) - 5} more")
    
    # Get pending migrations
    all_migrations = manager.get_migration_files()
    pending = [m for m in all_migrations if not manager.is_migration_applied(m["version"])]
    
    print(f"\nPending migrations: {len(pending)}")
    for migration in pending:
        print(f"- {migration['version']} - {migration['description']}")


def show_pending():
    """Show only pending migrations"""
    client = MongoDBClient()
    manager = MigrationManager(client.db)
    
    all_migrations = manager.get_migration_files()
    pending = [m for m in all_migrations if not manager.is_migration_applied(m["version"])]
    
    if pending:
        print(f"\nPending migrations ({len(pending)}):")
        for migration in pending:
            print(f"- {migration['version']} - {migration['description']}")
    else:
        print("\nNo pending migrations")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        show_status()
    elif command == "pending":
        show_pending()
    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Please provide a description for the migration")
            print("Usage: python manage_migrations.py create <description>")
            sys.exit(1)
        description = " ".join(sys.argv[2:])
        create_migration(description)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()