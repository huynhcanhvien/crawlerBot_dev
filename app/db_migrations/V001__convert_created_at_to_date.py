"""
Migration V001: Convert created_at string fields to Date objects
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def up(db):
    """
    Convert all created_at string fields to proper Date objects
    """
    tweets_collection = db["tweets"]
    
    # Count documents that need migration
    count = tweets_collection.count_documents({"created_at": {"$type": "string"}})
    if count == 0:
        logger.info("No documents need date migration")
        return
    
    logger.info(f"Migrating {count} documents with string dates...")
    
    # Find and update documents with string dates
    cursor = tweets_collection.find({"created_at": {"$type": "string"}})
    updated = 0
    errors = 0
    
    for doc in cursor:
        try:
            # Parse Twitter date format: "Wed Oct 10 20:19:24 +0000 2018"
            date_str = doc["created_at"]
            date_obj = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
            
            # Update document
            tweets_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"created_at": date_obj}}
            )
            
            updated += 1
            if updated % 1000 == 0:
                logger.info(f"Progress: {updated}/{count} documents")
                
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to migrate document {doc.get('_id')}: {e}")
    
    logger.info(f"Date migration complete: {updated} updated, {errors} errors")
    
    # Create index on created_at if not exists
    tweets_collection.create_index([("created_at", -1)])


def down(db):
    """
    Rollback: Convert Date objects back to strings (not recommended)
    """
    # Usually we don't rollback data migrations
    pass