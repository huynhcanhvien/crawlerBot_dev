#!/usr/bin/env python3
"""
Manually run database migrations
"""

from app.mongo_client import MongoDBClient

if __name__ == "__main__":
    print("Running database migrations...")
    
    # Simply creating a MongoDBClient instance will trigger migrations
    client = MongoDBClient()
    
    print("Migrations completed!")
    
    # Optional: Show migration status
    from app.db_migrations.migration_manager import MigrationManager
    manager = MigrationManager(client.db)
    
    history = manager.get_migration_history()
    print(f"\nApplied migrations: {len(history)}")
    for migration in history:
        status = "✓" if migration.get("success") else "✗"
        print(f"{status} {migration['version']} - {migration['description']}")