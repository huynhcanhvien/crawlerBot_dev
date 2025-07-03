"""
Flyway-like migration system for MongoDB
Migrations are versioned and run automatically on startup
"""

import os
import importlib.util
from datetime import datetime
from pathlib import Path
from ..logger import setup_logger

logger = setup_logger(__name__)


class MigrationManager:
    """Manages database migrations similar to Flyway"""
    
    def __init__(self, db):
        self.db = db
        self.migrations_collection = db["schema_version"]
        self.migrations_dir = Path(__file__).parent
        
    def get_migration_files(self):
        """Get all migration files sorted by version"""
        migration_files = []
        
        for file in self.migrations_dir.glob("V*.py"):
            # Parse version from filename (e.g., V001__description.py)
            filename = file.stem
            if filename.startswith("V") and "__" in filename:
                version = filename.split("__")[0]
                migration_files.append({
                    "version": version,
                    "filename": file.name,
                    "filepath": file,
                    "description": filename.split("__", 1)[1] if "__" in filename else ""
                })
        
        # Sort by version
        migration_files.sort(key=lambda x: x["version"])
        return migration_files
    
    def is_migration_applied(self, version):
        """Check if a migration version has been applied"""
        return self.migrations_collection.find_one({"version": version}) is not None
    
    def record_migration(self, version, filename, description, success=True):
        """Record migration execution in database"""
        self.migrations_collection.insert_one({
            "version": version,
            "filename": filename,
            "description": description,
            "executed_at": datetime.utcnow(),
            "success": success
        })
    
    def run_migration_file(self, migration_info):
        """Execute a single migration file"""
        version = migration_info["version"]
        filepath = migration_info["filepath"]
        
        # Load the migration module dynamically
        spec = importlib.util.spec_from_file_location(f"migration_{version}", filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Execute the up() function
        if hasattr(module, 'up'):
            module.up(self.db)
        else:
            raise Exception(f"Migration {version} missing 'up' function")
    
    def run_pending_migrations(self):
        """Run all pending migrations in order"""
        migrations = self.get_migration_files()
        pending_count = 0
        
        for migration in migrations:
            version = migration["version"]
            
            if not self.is_migration_applied(version):
                pending_count += 1
                logger.info(f"Running migration {version}: {migration['description']}")
                
                try:
                    self.run_migration_file(migration)
                    self.record_migration(
                        version=version,
                        filename=migration["filename"],
                        description=migration["description"],
                        success=True
                    )
                    logger.info(f"Migration {version} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Migration {version} failed: {str(e)}")
                    self.record_migration(
                        version=version,
                        filename=migration["filename"],
                        description=migration["description"],
                        success=False
                    )
                    raise
        
        if pending_count == 0:
            logger.info("No pending migrations")
        else:
            logger.info(f"Executed {pending_count} migrations")
    
    def get_migration_history(self):
        """Get history of all applied migrations"""
        return list(self.migrations_collection.find().sort("executed_at", -1))