# In src/data_explorer/config.py

import json
import os
from pathlib import Path

class Config:
    """Configuration manager for the application."""
    
    def __init__(self):
        # Determine config file location
        self.config_dir = Path.home() / ".pgdataexplorer"
        self.config_file = self.config_dir / "config.json"
        
        # Default configuration
        self.defaults = {
            "recent_connections": [],
            "window": {
                "size": [1000, 700],
                "position": [100, 100],
                "maximized": False
            },
            "splitters": {
                "h_splitter": [250, 750],
                "v_splitter": [300, 400]
            },
            "query_history": [],
            "query_limit": 100  # Default LIMIT value for SELECT queries
        }
        
        # Load configuration
        self.config = self.load()
    
    def load(self):
        """Load configuration from file."""
        # Create config directory if it doesn't exist
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True)
        
        # Create default config if file doesn't exist
        if not self.config_file.exists():
            return self.defaults.copy()
        
        # Load config from file
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Ensure all default keys exist
            for key, value in self.defaults.items():
                if key not in config:
                    config[key] = value
            
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.defaults.copy()
    
    def save(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value."""
        self.config[key] = value
        self.save()
    
    def add_recent_connection(self, connection_details):
        """Add a connection to the recent connections list."""
        # Remove password for security
        connection_copy = connection_details.copy()
        if "password" in connection_copy:
            connection_copy["password"] = ""  # Clear password
        
        # Add to recent connections
        recent = self.config.get("recent_connections", [])
        
        # Remove if already exists
        recent = [c for c in recent if not (
            c.get("host") == connection_copy.get("host") and
            c.get("port") == connection_copy.get("port") and
            c.get("dbname") == connection_copy.get("dbname") and
            c.get("user") == connection_copy.get("user")
        )]
        
        # Add to beginning of list
        recent.insert(0, connection_copy)
        
        # Limit to 10 recent connections
        recent = recent[:10]
        
        # Update config
        self.config["recent_connections"] = recent
        self.save()
    
    def add_query_history(self, query):
        """Add a query to the history."""
        # Get existing history
        history = self.config.get("query_history", [])
        
        # Remove if already exists
        if query in history:
            history.remove(query)
        
        # Add to beginning of list
        history.insert(0, query)
        
        # Limit to 50 queries
        history = history[:50]
        
        # Update config
        self.config["query_history"] = history
        self.save()
    
    def get_query_history(self):
        """Get the query history."""
        return self.config.get("query_history", [])
    
    def get_recent_connections(self):
        """Get the recent connections."""
        return self.config.get("recent_connections", [])