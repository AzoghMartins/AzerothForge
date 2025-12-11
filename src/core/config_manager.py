import json
import os
from typing import Dict, List, Optional
try:
    import mysql.connector
except ImportError:
    mysql = None

class ConfigManager:
    CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "auth_service_name": "authserver",
        "client_data_path": "",
        "wow_client_path": "",
        "auth_database": {
            "host": "localhost",
            "port": 3306,
            "user": "acore",
            "password": "acore",
            "db_name": "acore_auth"
        },
        "playerbots_enabled": False,
        "bot_prefix": "bot",
        "realms": [
            {
                "id": 1,
                "name": "Live Server",
                "service_name": "azerothcore-world",
                "soap_port": 7878,
                "soap_user": "admin",
                "soap_pass": "admin",
                "game_port": 8085,
                "db_world_name": "acore_world",
                "db_chars_name": "acore_characters"
            }
        ],
        "active_realm_index": 0
    }

    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Loads config from file or returns default."""
        if not os.path.exists(self.CONFIG_FILE):
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                # Ensure structure is up to date (simple migration)
                if "auth_database" not in loaded:
                    loaded["auth_database"] = self.DEFAULT_CONFIG["auth_database"].copy()
                if "auth_service_name" not in loaded:
                    loaded["auth_service_name"] = self.DEFAULT_CONFIG["auth_service_name"]
                if "client_data_path" not in loaded:
                    loaded["client_data_path"] = self.DEFAULT_CONFIG["client_data_path"]
                if "wow_client_path" not in loaded:
                    loaded["wow_client_path"] = self.DEFAULT_CONFIG["wow_client_path"]
                if "active_realm_index" not in loaded:
                    loaded["active_realm_index"] = self.DEFAULT_CONFIG["active_realm_index"]
                if "playerbots_enabled" not in loaded:
                    loaded["playerbots_enabled"] = self.DEFAULT_CONFIG["playerbots_enabled"]
                if "bot_prefix" not in loaded:
                    loaded["bot_prefix"] = self.DEFAULT_CONFIG["bot_prefix"]
                return loaded
        except (json.JSONDecodeError, IOError):
            print("Error loading config, using default.")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self, data: Optional[Dict] = None):
        """Saves current config or provided data to file."""
        if data:
            self.config = data
            
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get_active_realm(self) -> Dict:
        """Returns the currently active realm configuration."""
        realms = self.config.get("realms", [])
        index = self.config.get("active_realm_index", 0)
        
        if 0 <= index < len(realms):
            return realms[index]
        elif realms:
            return realms[0]
        else:
            return self.DEFAULT_CONFIG["realms"][0]

    def set_active_realm_index(self, index: int):
        """Sets the active realm index and saves config."""
        if 0 <= index < len(self.config.get("realms", [])):
            self.config["active_realm_index"] = index
            self.save_config()

    def get_realms(self) -> List[Dict]:
        return self.config.get("realms", [])

    def discover_realms(self) -> List[Dict]:
        """
        Connects to Auth DB, fetches realmlist, and merges with local config.
        Returns the updated list of realms.
        """
        if not mysql:
            print("mysql-connector-python not installed.")
            return self.config["realms"]

        auth_config = self.config.get("auth_database", self.DEFAULT_CONFIG["auth_database"])
        
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name, port FROM realmlist")
            db_realms = cursor.fetchall()
            conn.close()
            
            # Merge Logic
            current_realms = self.config.get("realms", [])
            merged_realms = []
            
            for db_realm in db_realms:
                r_id = db_realm['id']
                r_name = db_realm['name']
                r_port = db_realm['port']
                
                # Check if exists in local config (by ID preferred, fallback to Name)
                existing = next((r for r in current_realms if r.get('id') == r_id), None)
                if not existing:
                    existing = next((r for r in current_realms if r.get('name') == r_name), None)
                
                if existing:
                    # Update DB/Read-only fields, keep local overrides
                    existing['id'] = r_id
                    existing['name'] = r_name # Use DB name as truth? Or keep local alias? Let's sync to DB name.
                    existing['game_port'] = r_port
                    merged_realms.append(existing)
                else:
                    # New Realm Found - Apply Smart Defaults
                    new_realm = {
                        "id": r_id,
                        "name": r_name,
                        "game_port": r_port,
                        "service_name": "worldserver" if r_id == 1 else f"worldserver-realm{r_id}",
                        "soap_port": 7878 if r_id == 1 else 7878 + (r_id - 1),
                        "soap_user": "admin",
                        "soap_pass": "admin",
                        "db_world_name": "acore_world",
                        "db_chars_name": "acore_characters"
                    }
                    merged_realms.append(new_realm)
            
            # Optionally keep local realms that weren't in DB? 
            # User might have custom entries? 
            # For now, let's say DB is source of truth for EXISTENCE of realms, 
            # giving a pure sync. 
            
            if merged_realms:
                self.config["realms"] = merged_realms
                self.save_config()
                return merged_realms
            
            return current_realms

        except mysql.connector.Error as err:
            print(f"Error connecting to DB: {err}")
            # Return current list if sync fails
            return self.config["realms"]
