"""
Base Connector Interface

Abstract base class that all connectors must implement.
Provides standard lifecycle, error handling, freshness scoring, and checkpointing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime


class BaseConnector(ABC):
    """Abstract base for all data connectors."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize connector.
        
        Args:
            name: Connector name (e.g., 'jira', 'confluence')
            config: Configuration dict with credentials and settings
        """
        self.name = name
        self.config = config

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the data source.
        
        Returns:
            True if auth successful, False otherwise
        """
        pass

    @abstractmethod
    def sync_full(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Perform full sync of all records in date range.
        
        Args:
            start_date: Sync start date
            end_date: Sync end date
            
        Returns:
            List of normalized records
        """
        pass

    @abstractmethod
    def sync_incremental(self, checkpoint: Dict) -> List[Dict]:
        """Perform incremental sync since last checkpoint.
        
        Args:
            checkpoint: Last sync checkpoint (timestamp, cursor, etc.)
            
        Returns:
            List of new/updated normalized records
        """
        pass

    @abstractmethod
    def normalize(self, raw_record: Dict) -> Dict:
        """Normalize raw payload to canonical schema.
        
        Args:
            raw_record: Raw data from source
            
        Returns:
            Normalized record with standard fields:
            {
              id, title, body, created_at, updated_at,
              source_type, source_id, metadata
            }
        """
        pass

    @abstractmethod
    def compute_freshness(self, record: Dict) -> float:
        """Compute freshness score for record (0-1).
        
        Args:
            record: Normalized record
            
        Returns:
            Freshness score
        """
        pass

    @abstractmethod
    def store_checkpoint(self, checkpoint: Dict) -> None:
        """Store checkpoint for next incremental sync.
        
        Args:
            checkpoint: Checkpoint data to persist
        """
        pass

    @abstractmethod
    def get_checkpoint(self) -> Dict:
        """Get last stored checkpoint.
        
        Returns:
            Checkpoint dict
        """
        pass

    def retry_with_backoff(self, max_attempts: int = 3) -> Any:
        """Decorator for retry with exponential backoff.
        
        Args:
            max_attempts: Maximum retry attempts
        """
        # TODO: Implement exponential backoff retry logic
        pass

    def emit_error(self, error_type: str, message: str) -> None:
        """Emit typed error.
        
        Args:
            error_type: One of AuthenticationError, RateLimitError, ParseError
            message: Error message
        """
        # TODO: Raise appropriate error type
        pass
