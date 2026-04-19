"""
Feature Flags Runtime Loader

Loads feature flags from YAML and provides simple boolean checks.
Reads from config/feature_flags.yaml at startup, then caches in memory.

Usage:
    from services.shared.config.feature_flags import FeatureFlags
    
    ff = FeatureFlags()  # Loads from config/feature_flags.yaml
    
    if ff.is_enabled('connectors.jira'):
        # Import from Jira
        pass
    
    if ff.is_enabled('evaluation.dry_run_mode'):
        # Run without side effects
        pass
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML required: pip install pyyaml")

logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Loads and manages feature flags from YAML configuration.
    
    Supports dot notation: 'connectors.jira' maps to config['connectors']['jira']['enabled']
    """
    
    def __init__(self, config_file: str = None):
        """
        Initialize feature flags from YAML file.
        
        Args:
            config_file: Path to feature_flags.yaml. Defaults to 'config/feature_flags.yaml'
                        relative to project root.
        """
        if config_file is None:
            # Find project root (directory containing config/)
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "config").exists():
                    config_file = str(current / "config" / "feature_flags.yaml")
                    break
                current = current.parent
            else:
                # Fallback to default path
                config_file = "config/feature_flags.yaml"
        
        self.config_file = config_file
        self._flags: Dict[str, Any] = {}
        self._load_flags()
    
    def _load_flags(self) -> None:
        """Load feature flags from YAML file."""
        if not os.path.exists(self.config_file):
            logger.warning(f"Feature flags file not found: {self.config_file}. Using empty config.")
            self._flags = {}
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
                self._flags = config
                logger.info(f"Loaded {len(self._flatten_flags())} feature flags from {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to load feature flags: {e}")
            self._flags = {}
    
    def _flatten_flags(self) -> Dict[str, bool]:
        """
        Flatten nested flag structure for easier iteration.
        Example: {'connectors': {'jira': {'enabled': True}}} 
                 -> {'connectors.jira': True}
        """
        result = {}
        
        def flatten(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    
                    if isinstance(value, dict):
                        if 'enabled' in value:
                            # This is a flag node
                            result[current_path] = value.get('enabled', False)
                        else:
                            # Keep recursing
                            flatten(value, current_path)
                    elif isinstance(value, bool):
                        # Direct boolean value
                        result[current_path] = value
        
        flatten(self._flags)
        return result
    
    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Dot-notation flag name (e.g., 'connectors.jira')
        
        Returns:
            True if flag is enabled, False otherwise
        
        Examples:
            if ff.is_enabled('connectors.jira'):
                pass
            
            if ff.is_enabled('evaluation.dry_run_mode'):
                pass
        """
        parts = flag_name.split('.')
        current = self._flags
        
        for part in parts:
            if not isinstance(current, dict):
                logger.warning(f"Invalid flag path: {flag_name}")
                return False
            
            if part not in current:
                logger.warning(f"Flag not found: {flag_name}")
                return False
            
            current = current[part]
        
        # Should be at 'enabled' key
        if isinstance(current, dict):
            return current.get('enabled', False)
        elif isinstance(current, bool):
            return current
        else:
            logger.warning(f"Invalid flag format: {flag_name}: {current}")
            return False
    
    def get_description(self, flag_name: str) -> str:
        """
        Get the description of a feature flag.
        
        Args:
            flag_name: Dot-notation flag name (e.g., 'connectors.jira')
        
        Returns:
            Description string, or empty string if not found
        """
        parts = flag_name.split('.')
        current = self._flags
        
        for part in parts:
            if not isinstance(current, dict):
                return ""
            
            if part not in current:
                return ""
            
            current = current[part]
        
        if isinstance(current, dict):
            return current.get('description', '')
        return ""
    
    def list_flags(self, section: str = None) -> Dict[str, Any]:
        """
        List all feature flags, optionally filtered by section.
        
        Args:
            section: Optional section name to filter (e.g., 'connectors', 'evaluation')
        
        Returns:
            Dict of flag_name -> {enabled: bool, description: str}
        
        Examples:
            ff.list_flags()  # All flags
            ff.list_flags('connectors')  # Only connector flags
        """
        if section is None:
            # Return all
            result = {}
            for key, value in self._flatten_flags().items():
                result[key] = {
                    'enabled': value,
                    'description': self.get_description(key)
                }
            return result
        else:
            # Return just this section
            if section not in self._flags:
                logger.warning(f"Section not found: {section}")
                return {}
            
            result = {}
            section_data = self._flags[section]
            
            for key, value in section_data.items():
                if isinstance(value, dict):
                    full_key = f"{section}.{key}"
                    result[full_key] = {
                        'enabled': value.get('enabled', False),
                        'description': value.get('description', '')
                    }
            
            return result
    
    def reload(self) -> None:
        """Reload feature flags from disk (for testing or dynamic updates)."""
        logger.info("Reloading feature flags from disk...")
        self._load_flags()
    
    def __repr__(self) -> str:
        """Pretty-print feature flags status."""
        lines = ["Feature Flags:"]
        for key, value in sorted(self._flatten_flags().items()):
            status = "✅ ENABLED" if value else "❌ DISABLED"
            lines.append(f"  {key}: {status}")
        return "\n".join(lines)


# Singleton instance for convenience
_global_flags = None


def get_feature_flags() -> FeatureFlags:
    """Get or initialize global feature flags instance."""
    global _global_flags
    if _global_flags is None:
        _global_flags = FeatureFlags()
    return _global_flags


# Examples / test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    ff = FeatureFlags()
    
    print("\n" + "="*60)
    print("Feature Flags Status")
    print("="*60 + "\n")
    print(ff)
    
    print("\n" + "="*60)
    print("Connector Flags")
    print("="*60 + "\n")
    for flag, info in ff.list_flags('connectors').items():
        status = "✅" if info['enabled'] else "❌"
        print(f"{status} {flag}: {info['description']}")
    
    print("\n" + "="*60)
    print("Evaluation Flags")
    print("="*60 + "\n")
    for flag, info in ff.list_flags('evaluation').items():
        status = "✅" if info['enabled'] else "❌"
        print(f"{status} {flag}: {info['description']}")
