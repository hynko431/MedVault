# scripts/reindex_prescriptions.py

"""
Elasticsearch Reindexing Script for Prescriptions

This script handles zero-downtime reindexing of prescriptions data from one
Elasticsearch index to another with proper error handling, validation, and rollback.
"""

import argparse
import logging
import sys
import time
from typing import Optional, Tuple

from app.services.search_indexer import (
    create_prescriptions_index,
    reindex_prescriptions,
    switch_alias_to_new_index,
    get_es_client
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReindexError(Exception):
    """Custom exception for reindexing failures"""
    pass


def validate_index_exists(index_name: str) -> bool:
    """
    Validate that the source index exists in Elasticsearch.
    
    Args:
        index_name: Name of the index to validate
        
    Returns:
        True if index exists, False otherwise
    """
    es = get_es_client()
    if es is None:
        logger.error("Elasticsearch client is not available")
        return False
    
    try:
        exists = bool(es.indices.exists(index=index_name))
        if not exists:
            logger.warning(f"Index '{index_name}' does not exist")
        return exists
    except Exception as e:
        logger.error(f"Error checking index existence: {e}")
        return False


def get_index_document_count(index_name: str) -> Optional[int]:
    """
    Get the number of documents in an index.
    
    Args:
        index_name: Name of the index
        
    Returns:
        Number of documents or None if error occurs
    """
    es = get_es_client()
    if es is None:
        return None
    
    try:
        result = es.count(index=index_name)
        count = result.get('count', 0)
        logger.info(f"Index '{index_name}' contains {count} documents")
        return count
    except Exception as e:
        logger.error(f"Error getting document count for '{index_name}': {e}")
        return None


def verify_reindex_success(old_index: str, new_index: str) -> bool:
    """
    Verify that reindexing was successful by comparing document counts.
    
    Args:
        old_index: Source index name
        new_index: Destination index name
        
    Returns:
        True if counts match, False otherwise
    """
    old_count = get_index_document_count(old_index)
    new_count = get_index_document_count(new_index)
    
    if old_count is None or new_count is None:
        logger.error("Cannot verify reindex success - unable to get document counts")
        return False
    
    if old_count == new_count:
        logger.info(f"✅ Verification successful: {old_count} documents in both indices")
        return True
    else:
        logger.error(
            f"❌ Verification failed: Old index has {old_count} documents, "
            f"new index has {new_count} documents"
        )
        return False


def cleanup_old_index(index_name: str, force: bool = False) -> bool:
    """
    Delete an old index after successful reindexing.
    
    Args:
        index_name: Name of the index to delete
        force: If True, delete without confirmation
        
    Returns:
        True if deletion was successful, False otherwise
    """
    es = get_es_client()
    if es is None:
        return False
    
    if not force:
        response = input(f"⚠️  Delete old index '{index_name}'? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Cleanup cancelled by user")
            return False
    
    try:
        es.indices.delete(index=index_name)
        logger.info(f"🗑️  Successfully deleted old index '{index_name}'")
        return True
    except Exception as e:
        logger.error(f"Error deleting index '{index_name}': {e}")
        return False


def rollback_on_failure(new_index: str) -> None:
    """
    Rollback by deleting the new index if reindexing fails.
    
    Args:
        new_index: Name of the new index to delete
    """
    es = get_es_client()
    if es is None:
        return
    
    try:
        if es.indices.exists(index=new_index):
            es.indices.delete(index=new_index)
            logger.info(f"🔄 Rolled back: Deleted new index '{new_index}'")
    except Exception as e:
        logger.error(f"Error during rollback: {e}")


def run_reindex(
    old_index: str,
    new_version: str,
    verify: bool = True,
    cleanup: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Execute the reindexing process with proper error handling and validation.
    
    Args:
        old_index: Name of the source index
        new_version: Version string for the new index (e.g., "v2", "v3")
        verify: Whether to verify document counts after reindexing
        cleanup: Whether to cleanup old index after successful reindexing
        dry_run: If True, validate but don't execute the reindex
        
    Returns:
        True if reindexing was successful, False otherwise
    """
    new_index = None
    
    try:
        # Step 1: Validate Elasticsearch connection
        es = get_es_client()
        if es is None:
            raise ReindexError("Elasticsearch is not enabled or cannot connect")
        
        logger.info("✅ Elasticsearch connection established")
        
        # Step 2: Validate source index exists
        logger.info(f"🔍 Validating source index '{old_index}'...")
        if not validate_index_exists(old_index):
            raise ReindexError(f"Source index '{old_index}' does not exist")
        
        # Step 3: Get source document count
        old_count = get_index_document_count(old_index)
        if old_count == 0:
            logger.warning("⚠️  Source index is empty")
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE - No changes will be made")
            logger.info(f"Would reindex {old_count} documents from '{old_index}' to 'prescriptions_{new_version}'")
            return True
        
        # Step 4: Create new index
        logger.info(f"🚀 Creating new index with version '{new_version}'...")
        new_index = create_prescriptions_index(new_version)
        
        if not new_index:
            raise ReindexError("Failed to create new index")
        
        logger.info(f"✅ Created new index: '{new_index}'")
        
        # Step 5: Reindex data
        logger.info(f"🔄 Reindexing data from '{old_index}' to '{new_index}'...")
        logger.info("⏳ This may take a while for large datasets...")
        
        start_time = time.time()
        reindex_prescriptions(old_index, new_index)
        elapsed_time = time.time() - start_time
        
        logger.info(f"✅ Reindexing completed in {elapsed_time:.2f} seconds")
        
        # Step 6: Verify reindexing
        if verify:
            logger.info("🔍 Verifying reindex success...")
            if not verify_reindex_success(old_index, new_index):
                raise ReindexError("Verification failed - document counts don't match")
        
        # Step 7: Switch alias
        logger.info(f"🔁 Switching alias 'prescriptions_current' to '{new_index}'...")
        switch_alias_to_new_index(new_index)
        logger.info("✅ Alias switched successfully")
        
        # Step 8: Cleanup old index (optional)
        if cleanup:
            logger.info(f"🗑️  Cleaning up old index '{old_index}'...")
            cleanup_old_index(old_index, force=False)
        
        logger.info("🎉 Reindexing completed successfully!")
        logger.info(f"📊 Summary: {old_count} documents migrated from '{old_index}' to '{new_index}'")
        
        return True
        
    except ReindexError as e:
        logger.error(f"❌ Reindexing failed: {e}")
        if new_index:
            logger.info("🔄 Rolling back changes...")
            rollback_on_failure(new_index)
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during reindexing: {e}", exc_info=True)
        if new_index:
            logger.info("🔄 Rolling back changes...")
            rollback_on_failure(new_index)
        return False


def main():
    """Parse command-line arguments and execute reindexing."""
    parser = argparse.ArgumentParser(
        description="Reindex Elasticsearch prescriptions data with zero downtime"
    )
    
    parser.add_argument(
        '--old-index',
        default='prescriptions_v1',
        help='Name of the source index (default: prescriptions_v1)'
    )
    
    parser.add_argument(
        '--new-version',
        default='v2',
        help='Version string for the new index (default: v2)'
    )
    
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip verification of document counts after reindexing'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Delete old index after successful reindexing'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without executing reindex'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Execute reindexing
    success = run_reindex(
        old_index=args.old_index,
        new_version=args.new_version,
        verify=not args.no_verify,
        cleanup=args.cleanup,
        dry_run=args.dry_run
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
