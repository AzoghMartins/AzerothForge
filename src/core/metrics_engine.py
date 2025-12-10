import re
import time
try:
    import mysql.connector
except ImportError:
    mysql = None

from src.core.config_manager import ConfigManager
from src.core.server_controller import ServerController

class MetricsEngine:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.controller = ServerController()

    def get_uptime(self) -> str:
        """
        Fetches uptime from Auth DB 'uptime' table.
        """
        # 1. Check Service Status first
        realm = self.config_manager.get_active_realm()
        service_name = realm.get("service_name", "azerothcore-world")
        if not self.controller.check_service(service_name):
            return "Offline"

        # 2. Query DB
        if not mysql:
            return "Unknown (No MySQL)"
            
        auth_config = self.config_manager.config.get("auth_database", {})
        
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor()
            
            # Get latest starttime for this realm
            # 'uptime' table cols: realmid, starttime, uptime, revision
            cursor.execute("SELECT starttime FROM uptime WHERE realmid = %s ORDER BY starttime DESC LIMIT 1", (realm.get('id', 1),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                starttime = row[0]
                current_time = int(time.time())
                delta = current_time - starttime
                
                if delta < 0: delta = 0
                
                # Format: Xd Xh Xm Xs
                days = delta // 86400
                hours = (delta % 86400) // 3600
                minutes = (delta % 3600) // 60
                seconds = delta % 60
                
                parts = []
                if days > 0: parts.append(f"{days}d")
                if hours > 0: parts.append(f"{hours}h")
                if minutes > 0: parts.append(f"{minutes}m")
                parts.append(f"{seconds}s")
                
                return " ".join(parts)
            else:
                return "00:00:00" # No uptime record found
                
        except mysql.connector.Error as e:
            print(f"Uptime DB Error: {e}")
            return "Error"

    def get_population_stats(self) -> dict:
        """
        Connects to DB to count accounts, humans, and bots.
        """
        stats = {
            "accounts": 0,
            "humans": 0,
            "bots": 0
        }
        
        if not mysql:
            return stats
            
        realm = self.config_manager.get_active_realm()
        auth_config = self.config_manager.config.get("auth_database", {})
        
        # Check if Playerbots enabled
        bots_enabled = realm.get("playerbots_enabled", False)
        bot_prefix = realm.get("bot_prefix", "bot").strip()
        
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth")
            )
            cursor = conn.cursor()
            
            # 1. Total Accounts (Filter bots if enabled)
            if bots_enabled and bot_prefix:
                cursor.execute(f"SELECT COUNT(*) FROM account WHERE username NOT LIKE '{bot_prefix}%'")
            else:
                cursor.execute("SELECT COUNT(*) FROM account")
            stats["accounts"] = cursor.fetchone()[0]
            
            # 2. Online Players (Joined with account to filter by username)
            # We need to query the characters DB, but JOIN with Auth DB.
            # Assuming both are on same MySQL instance/connection which is standard for AC.
            # If they are separate instances, this query fails. 
            # But standard AC setup is one MySQL instance with 3 DBs.
            
            chars_db = realm.get("db_chars_name", "acore_characters")
            auth_db = auth_config.get("db_name", "acore_auth")
            
            if bots_enabled and bot_prefix:
                # Count Humans: Online AND username NOT LIKE prefix%
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {chars_db}.characters c 
                    JOIN {auth_db}.account a ON c.account = a.id 
                    WHERE c.online = 1 AND a.username NOT LIKE '{bot_prefix}%'
                """)
                stats["humans"] = cursor.fetchone()[0]
                
                # Count Bots: Online AND username LIKE prefix%
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {chars_db}.characters c 
                    JOIN {auth_db}.account a ON c.account = a.id 
                    WHERE c.online = 1 AND a.username LIKE '{bot_prefix}%'
                """)
                stats["bots"] = cursor.fetchone()[0]
            else:
                # bots_enabled False -> All online are humans
                cursor.execute(f"SELECT COUNT(*) FROM {chars_db}.characters WHERE online = 1")
                stats["humans"] = cursor.fetchone()[0]
                stats["bots"] = 0
                
            conn.close()
            
        except mysql.connector.Error as e:
            print(f"Metrics DB Error: {e}")
            
        return stats

    def _update_controller_creds(self):
        realm = self.config_manager.get_active_realm()
        self.controller.set_connection_info(
            realm.get("soap_port", 7878),
            realm.get("soap_user", ""),
            realm.get("soap_pass", "")
        )
