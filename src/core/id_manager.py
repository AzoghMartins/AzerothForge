import mysql.connector
from typing import List, Optional

class IdManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def find_next_campaign_block(self, start_search_at: int = 50000, block_size: int = 1000, excluded_ranges: List[tuple] = [], target_realms: Optional[List[dict]] = None) -> int:
        """
        Finds the first available gap of size `block_size` starting from `start_search_at`.
        Queries creature, item, and quest templates across specified realms.
        """
        if target_realms is None:
            target_realms = [self.config_manager.get_active_realm()]
            
        auth_config = self.config_manager.config.get("auth_database", {})
        used_ids = set()
        
        try:
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=auth_config.get("db_name", "acore_auth") 
            )
            cursor = conn.cursor()
            
            tables_map = {
                "creature_template": "entry",
                "item_template": "entry",
                "quest_template": "ID"
            }
            
            # Iterate through all target realms
            for realm_config in target_realms:
                world_db = realm_config.get("db_world_name", "acore_world")
                
                for table, id_col in tables_map.items():
                    try:
                        query = f"SELECT {id_col} FROM {world_db}.{table} WHERE {id_col} >= %s ORDER BY {id_col} ASC"
                        cursor.execute(query, (start_search_at,))
                        rows = cursor.fetchall()
                        for row in rows:
                            used_ids.add(row[0])
                    except mysql.connector.Error as e:
                        print(f"Error querying {world_db}.{table}: {e}")
            
            conn.close()
            
            # Check logic
            candidate = start_search_at
             # Align strictly to block_size or 1000? User said "jump candidate += 1000 (Force alignment)".
             # Let's align candidate to nearest 1000 if not already?
             # User example: "Loop: Start candidate at start_search_at (e.g., 50000)."
             # So we assume start_search_at is the starting point.
            
            # Safety limit
            limit = start_search_at + 1000000
            
            while candidate < limit:
                # 1. Check Exclusions (Reserved by apps)
                is_excluded = False
                cand_end = candidate + block_size - 1
                for r_start, r_end in excluded_ranges:
                     if (candidate <= r_end) and (cand_end >= r_start):
                         is_excluded = True
                         break
                
                if is_excluded:
                    candidate += 1000 # Skip dirty block
                    continue

                # 2. Check Database (Existing data)
                # Check if block is free
                # Range is [candidate, candidate + block_size)
                # We check if ANY id in used_ids matches this range
                
                is_free = True
                for i in range(candidate, candidate + block_size):
                    if i in used_ids:
                        is_free = False
                        break
                
                if is_free:
                    return candidate
                
                # Jump by 1000
                candidate += 1000
                
            # Fallback if limit reached, though unlikely with 1M range
            return candidate

        except mysql.connector.Error as e:
            print(f"IdManager Database Error: {e}")
            return start_search_at
        except Exception as e:
            print(f"IdManager Error: {e}")
            return start_search_at

    def is_block_free(self, start_id: int, block_size: int = 1000, target_realms: Optional[List[dict]] = None) -> bool:
        """
        Checks if the ID range [start_id, start_id + block_size) is completely free of data.
        Checks ALL specified realms.
        """
        if target_realms is None:
            target_realms = [self.config_manager.get_active_realm()]
            
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
            
            tables_map = {
                "creature_template": "entry",
                "item_template": "entry",
                "quest_template": "ID"
            }
            
            is_conflict = False
            
            for realm_config in target_realms:
                world_db = realm_config.get("db_world_name", "acore_world")
                
                # We want to know if COUNT > 0 for range
                for table, id_col in tables_map.items():
                    query = f"SELECT COUNT(*) FROM {world_db}.{table} WHERE {id_col} >= %s AND {id_col} < %s"
                    cursor.execute(query, (start_id, start_id + block_size))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        is_conflict = True
                        break
                
                if is_conflict:
                    break
            
            conn.close()
            return not is_conflict

        except mysql.connector.Error as e:
            print(f"IdManager Validation Error: {e}")
            # Fail safe: iterate on caution, assume not free if DB error?
            # Or assume free? Ideally we block if we can't verify.
            return False 
        except Exception as e:
            print(f"IdManager Error: {e}")
            return False
