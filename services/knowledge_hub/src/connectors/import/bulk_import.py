"""
Bulk Import Module for DreamFi Phase 0 Bootstrap

Handles full imports of all connector data with dead-lettering, idempotence,
and watermark-based syncing. Writes all data to canonical schema.

CRITICAL CONSTRAINTS:
- All writes through canonical core_entities table
- Dead-lettered payloads are immutable and auditable
- Watermarks saved atomically (tmp + rename)
- No duplicate writes on retry (UNIQUE constraint)
- One connector error doesn't block others
"""

import os
import json
import logging
import hashlib
import tempfile
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


class BulkImporter:
    """
    Bulk importer that orchestrates full data imports from all connectors.
    
    Manages watermark tracking, dead-lettering, and idempotent writes.
    """

    def __init__(self, env: Dict[str, str]):
        """
        Initialize bulk importer.
        
        Args:
            env: Environment variables dict with DB connection params
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
        
        # Dead-letter directory
        self.deadletter_dir = Path(env.get('DEADLETTER_DIR', 'data/dead-letters'))
        self.deadletter_dir.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.watermarks: Dict[str, Any] = {}
        
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
            Watermarks dict with connector sync metadata
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
    
    def _write_deadletter(
        self,
        connector_name: str,
        payload: Dict[str, Any],
        error: Exception
    ) -> None:
        """
        Write failed payload to dead-letter queue.
        
        Args:
            connector_name: Name of connector that failed
            payload: Raw payload that failed
            error: Error that occurred
        """
        try:
            connector_dir = self.deadletter_dir / connector_name
            connector_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.utcnow().isoformat()
            filename = f"{timestamp.replace(':', '-')}.jsonl"
            filepath = connector_dir / filename
            
            deadletter_record = {
                'timestamp': timestamp,
                'connector': connector_name,
                'error': str(error),
                'error_type': type(error).__name__,
                'payload': payload
            }
            
            with open(filepath, 'a') as f:
                f.write(json.dumps(deadletter_record) + '\n')
            
            logger.debug(f"Dead-lettered payload to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to write dead-letter: {e}")
    
    def _compute_object_hash(self, obj: Dict[str, Any]) -> str:
        """
        Compute hash of object for change detection.
        
        Args:
            obj: Object to hash
            
        Returns:
            SHA256 hex digest
        """
        obj_str = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(obj_str.encode()).hexdigest()
    
    def _object_exists_by_id(
        self,
        cursor: psycopg2.extensions.cursor,
        source_system: str,
        source_object_id: str
    ) -> bool:
        """
        Check if object already exists by (source_system, source_object_id).
        
        Args:
            cursor: Database cursor
            source_system: Source system name
            source_object_id: ID from source
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            cursor.execute(
                sql.SQL("""
                    SELECT 1 FROM core_entities
                    WHERE source_system = %s AND source_object_id = %s
                    LIMIT 1
                """),
                (source_system, source_object_id)
            )
            result = cursor.fetchone()
            return result is not None
        except psycopg2.Error as e:
            logger.error(f"Failed to check object existence: {e}")
            raise
    
    def _write_entity_to_db(
        self,
        cursor: psycopg2.extensions.cursor,
        entity: Dict[str, Any]
    ) -> bool:
        """
        Write normalized entity to core_entities table.
        
        Handles conflicts via UNIQUE constraint on (source_system, source_object_id).
        
        Args:
            cursor: Database cursor
            entity: Normalized entity
            
        Returns:
            True if written, False if already exists
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
                    datetime.utcnow(),
                    datetime.utcnow()
                )
            )
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to write entity: {e}")
            raise
    
    def full_import(
        self,
        env: Dict[str, str],
        connectors_list: List[Any]
    ) -> Dict[str, Any]:
        """
        Execute full import from all connectors.
        
        Workflow:
        1. Load watermarks to track last sync
        2. For each connector:
           - Call connector.fetch_all(since=last_sync_time if incremental else None)
           - For each object:
             * Normalize via connector.normalize()
             * Write to core_entities
             * On error: dead-letter and continue
           - Update watermarks with counts and status
        3. Save watermarks atomically
        
        Args:
            env: Environment variables
            connectors_list: List of connector instances to import from
            
        Returns:
            Summary dict with import statistics
        """
        logger.info(f"Starting full import from {len(connectors_list)} connectors")
        
        self._load_watermarks()
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        summary: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_connectors': len(connectors_list),
            'connectors_imported': 0,
            'connectors_failed': 0,
            'total_objects_processed': 0,
            'total_objects_written': 0,
            'total_deadlettered': 0,
            'connector_results': {}
        }
        
        for connector in connectors_list:
            connector_name = getattr(connector, 'name', 'unknown')
            logger.info(f"Importing from connector: {connector_name}")
            
            connector_result = {
                'connector': connector_name,
                'objects_processed': 0,
                'objects_written': 0,
                'deadlettered': 0,
                'error': None,
                'status': 'success'
            }
            
            try:
                # Get last sync time or None for full import
                last_watermark = self.watermarks.get(connector_name, {})
                last_sync_time = last_watermark.get('last_sync_time')
                is_incremental = last_sync_time is not None
                
                logger.debug(
                    f"Connector {connector_name}: "
                    f"incremental={is_incremental}, "
                    f"last_sync={last_sync_time}"
                )
                
                # Fetch all objects from connector
                if hasattr(connector, 'fetch_all'):
                    objects = connector.fetch_all(
                        since=last_sync_time if is_incremental else None
                    )
                else:
                    logger.warning(f"Connector {connector_name} missing fetch_all()")
                    connector_result['error'] = 'Missing fetch_all() method'
                    connector_result['status'] = 'skipped'
                    summary['connector_results'][connector_name] = connector_result
                    continue
                
                if not isinstance(objects, list):
                    raise TypeError(f"fetch_all() returned {type(objects)}, expected list")
                
                logger.info(f"Fetched {len(objects)} objects from {connector_name}")
                
                # Process each object
                sync_start = datetime.utcnow()
                for raw_obj in objects:
                    connector_result['objects_processed'] += 1
                    summary['total_objects_processed'] += 1
                    
                    try:
                        # Normalize object
                        if not hasattr(connector, 'normalize'):
                            raise AttributeError(f"Connector missing normalize() method")
                        
                        normalized = connector.normalize(raw_obj)
                        
                        # Validate required canonical fields
                        required_fields = {
                            'entity_id', 'source_system', 'source_object_id',
                            'freshness_score', 'confidence_score',
                            'eligible_skill_families_json'
                        }
                        missing = required_fields - set(normalized.keys())
                        if missing:
                            raise ValueError(
                                f"Missing canonical fields: {missing}"
                            )
                        
                        # Compute content hash
                        normalized['content_hash'] = self._compute_object_hash(
                            normalized.get('content', {})
                        )
                        
                        # Write to database
                        self._write_entity_to_db(cursor, normalized)
                        connector_result['objects_written'] += 1
                        summary['total_objects_written'] += 1
                        
                    except Exception as obj_error:
                        logger.error(
                            f"Parse error for {connector_name}: {obj_error}",
                            exc_info=True
                        )
                        self._write_deadletter(connector_name, raw_obj, obj_error)
                        connector_result['deadlettered'] += 1
                        summary['total_deadlettered'] += 1
                        # Continue with next object
                        continue
                
                # Update watermark
                sync_end = datetime.utcnow()
                self.watermarks[connector_name] = {
                    'last_sync_time': sync_end.isoformat(),
                    'objects_synced': connector_result['objects_written'],
                    'objects_deadlettered': connector_result['deadlettered'],
                    'sync_duration_seconds': (sync_end - sync_start).total_seconds(),
                    'status': 'success'
                }
                
                summary['connectors_imported'] += 1
                logger.info(
                    f"Imported {connector_result['objects_written']} objects "
                    f"from {connector_name} "
                    f"({connector_result['deadlettered']} deadlettered)"
                )
                
            except Exception as conn_error:
                logger.error(
                    f"Connector {connector_name} failed: {conn_error}",
                    exc_info=True
                )
                connector_result['error'] = str(conn_error)
                connector_result['status'] = 'failed'
                summary['connectors_failed'] += 1
                
                # Update watermark with failure status
                self.watermarks[connector_name] = {
                    'last_sync_time': self.watermarks.get(
                        connector_name, {}
                    ).get('last_sync_time'),
                    'status': 'failed',
                    'error': str(conn_error)
                }
            
            summary['connector_results'][connector_name] = connector_result
        
        # Commit all writes
        try:
            conn.commit()
            logger.info("All database writes committed")
        except psycopg2.Error as e:
            logger.error(f"Commit failed: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()
        
        # Save watermarks atomically
        self._save_watermarks_atomic()
        
        logger.info(
            f"Full import complete: "
            f"{summary['connectors_imported']}/{summary['total_connectors']} "
            f"connectors, {summary['total_objects_written']} objects written, "
            f"{summary['total_deadlettered']} deadlettered"
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
def full_import(env: Dict[str, str], connectors_list: List[Any]) -> Dict[str, Any]:
    """
    Convenience function for full import.
    
    Args:
        env: Environment variables
        connectors_list: List of connectors to import from
        
    Returns:
        Import summary statistics
    """
    importer = BulkImporter(env)
    try:
        return importer.full_import(env, connectors_list)
    finally:
        importer.cleanup()
