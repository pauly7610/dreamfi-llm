"""
Incremental Sync Runner for DreamFi Phase 0

Runs every 30 minutes to perform incremental syncs from all connectors.
Handles pagination, change detection via hashing, and freshness scoring.

CRITICAL CONSTRAINTS:
- Per-connector errors don't block others
- Freshness score: 1.0 if synced <1hr ago, decays to 0.0 at 7 days
- Paginated fetches with limit per page
- Change detection via content hash comparison
- Watermarks updated per connector
"""

import os
import json
import logging
import hashlib
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IncrementalSyncRunner:
    """
    Incremental sync runner that periodically syncs from all connectors.
    
    Detects changes via content hashing and updates freshness scores.
    """

    # Freshness decay parameters
    FRESHNESS_MAX_AGE_HOURS = 168  # 7 days
    FRESHNESS_FULL_SCORE_HOURS = 1  # 1 hour

    def __init__(self, env: Dict[str, str]):
        """
        Initialize incremental sync runner.
        
        Args:
            env: Environment variables with DB connection params
        """
        self.env = env
        self.db_host = env.get('DB_HOST', 'localhost')
        self.db_port = int(env.get('DB_PORT', '5432'))
        self.db_name = env.get('DB_NAME', 'dreamfi')
        self.db_user = env.get('DB_USER', 'postgres')
        self.db_password = env.get('DB_PASSWORD', '')
        
        # Watermarks JSON path
        self.watermarks_path = Path(env.get('WATERMARKS_PATH', 'data/watermarks.json'))
        self.watermarks_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.watermarks: Dict[str, Any] = {}
        self.page_size = int(env.get('SYNC_PAGE_SIZE', '100'))
        
    def _get_db_connection(self) -> psycopg2.extensions.connection:
        """
        Get database connection.
        
        Returns:
            Database connection
            
        Raises:
            psycopg2.Error: If connection fails
        """
        if self.conn is None:
            try:
                self.conn = psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    database=self.db_name,
                    user=self.db_user,
                    password=self.db_password
                )
                logger.info(f"Connected to database: {self.db_name}")
            except psycopg2.Error as e:
                logger.error(f"Database connection failed: {e}")
                raise
        return self.conn
    
    def _load_watermarks(self) -> Dict[str, Any]:
        """
        Load watermarks from JSON file.
        
        Returns:
            Watermarks dict with per-connector sync metadata
        """
        if self.watermarks_path.exists():
            try:
                with open(self.watermarks_path, 'r') as f:
                    self.watermarks = json.load(f)
                logger.info(f"Loaded watermarks: {len(self.watermarks)} connectors")
            except Exception as e:
                logger.error(f"Failed to load watermarks: {e}")
                self.watermarks = {}
        else:
            self.watermarks = {}
            logger.info("No existing watermarks, starting fresh")
        
        return self.watermarks
    
    def _save_watermarks_atomic(self) -> None:
        """
        Save watermarks atomically using tmp + rename.
        
        Ensures no partial writes on failure.
        """
        try:
            # Write to temporary file
            fd, tmp_path = tempfile.mkstemp(
                prefix='watermarks_',
                suffix='.json',
                dir=self.watermarks_path.parent
            )
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(self.watermarks, f, indent=2, default=str)
                
                # Atomic rename
                os.replace(tmp_path, self.watermarks_path)
                logger.info(f"Watermarks saved atomically: {self.watermarks_path}")
            except Exception as e:
                os.close(fd)
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise e
        except Exception as e:
            logger.error(f"Failed to save watermarks atomically: {e}")
            raise
    
    def _compute_object_hash(self, obj: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of object for change detection.
        
        Args:
            obj: Object to hash
            
        Returns:
            SHA256 hex digest
        """
        obj_str = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(obj_str.encode()).hexdigest()
    
    def _compute_freshness_score(self, last_synced_at: datetime) -> float:
        """
        Compute freshness score based on last sync time.
        
        Formula:
        - 1.0 if synced < 1 hour ago
        - 0.0 if synced > 7 days ago
        - Linear decay between
        
        Args:
            last_synced_at: Datetime of last sync
            
        Returns:
            Freshness score (0.0 to 1.0)
        """
        now = datetime.utcnow()
        age_hours = (now - last_synced_at).total_seconds() / 3600
        
        if age_hours <= self.FRESHNESS_FULL_SCORE_HOURS:
            return 1.0
        elif age_hours >= self.FRESHNESS_MAX_AGE_HOURS:
            return 0.0
        else:
            # Linear decay
            decay_range = self.FRESHNESS_MAX_AGE_HOURS - self.FRESHNESS_FULL_SCORE_HOURS
            age_in_decay = age_hours - self.FRESHNESS_FULL_SCORE_HOURS
            score = 1.0 - (age_in_decay / decay_range)
            return max(0.0, min(1.0, score))
    
    def _get_entity_hash(
        self,
        cursor: psycopg2.extensions.cursor,
        source_system: str,
        source_object_id: str
    ) -> Optional[str]:
        """
        Get current content hash of entity from database.
        
        Args:
            cursor: Database cursor
            source_system: Source system name
            source_object_id: ID from source
            
        Returns:
            Content hash or None if not found
        """
        try:
            cursor.execute(
                sql.SQL("""
                    SELECT content_hash FROM core_entities
                    WHERE source_system = %s AND source_object_id = %s
                """),
                (source_system, source_object_id)
            )
            result = cursor.fetchone()
            return result[0] if result else None
        except psycopg2.Error as e:
            logger.error(f"Failed to get entity hash: {e}")
            raise
    
    def _upsert_entity(
        self,
        cursor: psycopg2.extensions.cursor,
        entity: Dict[str, Any],
        is_new: bool
    ) -> None:
        """
        Insert or update entity in core_entities table.
        
        Args:
            cursor: Database cursor
            entity: Normalized entity
            is_new: True if new entity, False if update
        """
        try:
            cursor.execute(
                sql.SQL("""
                    INSERT INTO core_entities (
                        entity_id,
                        source_system,
                        source_object_id,
                        content,
                        content_hash,
                        last_synced_at,
                        freshness_score,
                        confidence_score,
                        eligible_skill_families_json,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_system, source_object_id)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        last_synced_at = EXCLUDED.last_synced_at,
                        freshness_score = EXCLUDED.freshness_score,
                        confidence_score = EXCLUDED.confidence_score,
                        eligible_skill_families_json = EXCLUDED.eligible_skill_families_json,
                        updated_at = EXCLUDED.updated_at
                """),
                (
                    entity.get('entity_id'),
                    entity.get('source_system'),
                    entity.get('source_object_id'),
                    json.dumps(entity.get('content', {})),
                    entity.get('content_hash'),
                    entity.get('last_synced_at', datetime.utcnow()),
                    entity.get('freshness_score', 1.0),
                    entity.get('confidence_score', 1.0),
                    json.dumps(entity.get('eligible_skill_families_json', [])),
                    datetime.utcnow() if is_new else datetime.utcnow(),
                    datetime.utcnow()
                )
            )
        except psycopg2.Error as e:
            logger.error(f"Failed to upsert entity: {e}")
            raise
    
    def _sync_connector(
        self,
        conn: psycopg2.extensions.connection,
        connector: Any,
        connector_name: str
    ) -> Dict[str, Any]:
        """
        Perform incremental sync for single connector.
        
        Workflow:
        1. Get last sync time from watermarks
        2. Paginate through fetch_page() with limit
        3. For each object:
           - Normalize
           - Compute hash
           - Compare with DB hash
           - Update if changed, insert if new
        4. Update freshness scores
        5. Update watermarks
        
        Args:
            conn: Database connection
            connector: Connector instance
            connector_name: Name of connector
            
        Returns:
            Sync result dict
        """
        cursor = conn.cursor()
        result = {
            'connector': connector_name,
            'pages_fetched': 0,
            'objects_processed': 0,
            'objects_new': 0,
            'objects_updated': 0,
            'error': None,
            'status': 'success'
        }
        
        try:
            # Get last sync time
            last_watermark = self.watermarks.get(connector_name, {})
            last_sync_time = last_watermark.get('last_sync_time')
            
            logger.debug(f"Syncing {connector_name}, last_sync={last_sync_time}")
            
            sync_start = datetime.utcnow()
            page_offset = 0
            total_objects = 0
            
            # Paginate through connector data
            if not hasattr(connector, 'fetch_page'):
                raise AttributeError(f"Connector missing fetch_page() method")
            
            while True:
                # Fetch page
                try:
                    page = connector.fetch_page(
                        since=last_sync_time,
                        limit=self.page_size,
                        offset=page_offset
                    )
                except Exception as e:
                    logger.warning(
                        f"fetch_page failed for {connector_name} "
                        f"at offset {page_offset}: {e}"
                    )
                    break
                
                if not page:
                    logger.debug(f"No more pages for {connector_name}")
                    break
                
                result['pages_fetched'] += 1
                logger.debug(f"Fetched page {result['pages_fetched']} "
                           f"({len(page)} objects) from {connector_name}")
                
                # Process each object in page
                for raw_obj in page:
                    result['objects_processed'] += 1
                    
                    try:
                        # Normalize object
                        if not hasattr(connector, 'normalize'):
                            raise AttributeError("Connector missing normalize()")
                        
                        normalized = connector.normalize(raw_obj)
                        
                        # Validate required fields
                        required_fields = {
                            'entity_id', 'source_system', 'source_object_id',
                            'freshness_score', 'confidence_score'
                        }
                        missing = required_fields - set(normalized.keys())
                        if missing:
                            raise ValueError(f"Missing fields: {missing}")
                        
                        # Compute content hash
                        content_hash = self._compute_object_hash(
                            normalized.get('content', {})
                        )
                        normalized['content_hash'] = content_hash
                        
                        # Check if object changed
                        old_hash = self._get_entity_hash(
                            cursor,
                            normalized['source_system'],
                            normalized['source_object_id']
                        )
                        
                        is_new = old_hash is None
                        has_changed = is_new or (old_hash != content_hash)
                        
                        if has_changed:
                            # Update freshness score
                            normalized['freshness_score'] = self._compute_freshness_score(
                                datetime.utcnow()
                            )
                            
                            # Upsert entity
                            self._upsert_entity(cursor, normalized, is_new)
                            
                            if is_new:
                                result['objects_new'] += 1
                                logger.debug(
                                    f"New object: {normalized['source_system']}/"
                                    f"{normalized['source_object_id']}"
                                )
                            else:
                                result['objects_updated'] += 1
                                logger.debug(
                                    f"Updated object: {normalized['source_system']}/"
                                    f"{normalized['source_object_id']}"
                                )
                        else:
                            # Object unchanged, but update freshness if needed
                            old_freshness = self._compute_freshness_score(
                                normalized.get('last_synced_at', datetime.utcnow())
                            )
                            new_freshness = self._compute_freshness_score(
                                datetime.utcnow()
                            )
                            if abs(new_freshness - old_freshness) > 0.01:
                                cursor.execute(
                                    sql.SQL("""
                                        UPDATE core_entities
                                        SET freshness_score = %s, updated_at = %s
                                        WHERE source_system = %s 
                                        AND source_object_id = %s
                                    """),
                                    (
                                        new_freshness,
                                        datetime.utcnow(),
                                        normalized['source_system'],
                                        normalized['source_object_id']
                                    )
                                )
                    
                    except Exception as obj_error:
                        logger.warning(
                            f"Failed to process object in {connector_name}: {obj_error}"
                        )
                        # Continue with next object
                        continue
                
                page_offset += self.page_size
                total_objects += len(page)
            
            # Update watermark
            sync_end = datetime.utcnow()
            self.watermarks[connector_name] = {
                'last_sync_time': sync_end.isoformat(),
                'objects_synced': result['objects_processed'],
                'objects_new': result['objects_new'],
                'objects_updated': result['objects_updated'],
                'sync_duration_seconds': (sync_end - sync_start).total_seconds(),
                'status': 'success'
            }
            
            logger.info(
                f"Synced {connector_name}: "
                f"{result['objects_new']} new, "
                f"{result['objects_updated']} updated "
                f"({result['pages_fetched']} pages)"
            )
            
        except Exception as e:
            logger.error(
                f"Connector {connector_name} sync failed: {e}",
                exc_info=True
            )
            result['error'] = str(e)
            result['status'] = 'failed'
            
            # Update watermark with failure
            self.watermarks[connector_name] = {
                'last_sync_time': self.watermarks.get(
                    connector_name, {}
                ).get('last_sync_time'),
                'status': 'failed',
                'error': str(e)
            }
        
        finally:
            cursor.close()
        
        return result
    
    def incremental_sync(
        self,
        env: Dict[str, str],
        connectors_list: List[Any]
    ) -> Dict[str, Any]:
        """
        Perform incremental sync from all connectors.
        
        Runs every 30 minutes. Per-connector errors don't block others.
        
        Args:
            env: Environment variables
            connectors_list: List of connector instances
            
        Returns:
            Sync summary dict
        """
        logger.info(
            f"Starting incremental sync from {len(connectors_list)} connectors"
        )
        
        self._load_watermarks()
        conn = self._get_db_connection()
        
        summary: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_connectors': len(connectors_list),
            'connectors_synced': 0,
            'connectors_failed': 0,
            'total_objects_processed': 0,
            'total_objects_new': 0,
            'total_objects_updated': 0,
            'connector_results': {}
        }
        
        # Sync each connector independently
        for connector in connectors_list:
            connector_name = getattr(connector, 'name', 'unknown')
            logger.info(f"Syncing connector: {connector_name}")
            
            try:
                result = self._sync_connector(conn, connector, connector_name)
                summary['connector_results'][connector_name] = result
                
                if result['status'] == 'success':
                    summary['connectors_synced'] += 1
                    summary['total_objects_processed'] += result['objects_processed']
                    summary['total_objects_new'] += result['objects_new']
                    summary['total_objects_updated'] += result['objects_updated']
                else:
                    summary['connectors_failed'] += 1
                
            except Exception as e:
                logger.error(
                    f"Unexpected error syncing {connector_name}: {e}",
                    exc_info=True
                )
                summary['connector_results'][connector_name] = {
                    'connector': connector_name,
                    'status': 'failed',
                    'error': str(e)
                }
                summary['connectors_failed'] += 1
        
        # Commit all writes
        try:
            conn.commit()
            logger.info("All database writes committed")
        except psycopg2.Error as e:
            logger.error(f"Commit failed: {e}")
            conn.rollback()
            raise
        
        # Save watermarks atomically
        self._save_watermarks_atomic()
        
        logger.info(
            f"Incremental sync complete: "
            f"{summary['connectors_synced']}/{summary['total_connectors']} "
            f"connectors, {summary['total_objects_new']} new, "
            f"{summary['total_objects_updated']} updated"
        )
        
        return summary
    
    def cleanup(self) -> None:
        """Clean up database connection."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")


# Module-level convenience function
def incremental_sync(
    env: Dict[str, str],
    connectors_list: List[Any]
) -> Dict[str, Any]:
    """
    Convenience function for incremental sync.
    
    Intended to be called every 30 minutes from a scheduler.
    
    Args:
        env: Environment variables
        connectors_list: List of connectors to sync from
        
    Returns:
        Sync summary statistics
    """
    runner = IncrementalSyncRunner(env)
    try:
        return runner.incremental_sync(env, connectors_list)
    finally:
        runner.cleanup()
