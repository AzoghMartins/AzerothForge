import mysql.connector
from src.core.config_manager import ConfigManager

class DbManager:
    _instance = None

    @classmethod
    def get_instance(cls, config_manager=None):
        if cls._instance is None:
            if config_manager is None:
                # Fallback: Create new config manager if not provided
                config_manager = ConfigManager()
            cls._instance = cls(config_manager)
        return cls._instance

    def __init__(self, config_manager):
        if DbManager._instance is not None:
             raise Exception("This class is a singleton!")
        self.config_manager = config_manager
        
    def get_connection(self, db_name=None):
        auth_config = self.config_manager.config.get("auth_database", {})
        if not db_name:
            # Default to world DB if available, else auth?
            # Actually user flows usually need World DB.
            realm = self.config_manager.get_active_realm()
            db_name = realm.get("db_world_name", "acore_world")

        return mysql.connector.connect(
            host=auth_config.get("host", "localhost"),
            port=auth_config.get("port", 3306),
            user=auth_config.get("user", "acore"),
            password=auth_config.get("password", "acore"),
            database=db_name
        )

    def get_next_entry_id(self, table, column='entry'):
        """
        Returns the next available ID (MAX + 1) for the given table/column.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = f"SELECT MAX({column}) FROM {table}"
            cursor.execute(query)
            result = cursor.fetchone()
            
            conn.close()
            
            if result and result[0] is not None:
                return int(result[0]) + 1
            else:
                return 1
                
        except mysql.connector.Error as e:
            print(f"DbManager Error: {e}")
            return 0

    def get_free_entry_in_range(self, table, min_id, max_id, col_name='entry'):
        """
        Returns the first unused ID in the given range. Returns None if range is full.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Fetch all used IDs in range
            query = f"SELECT {col_name} FROM {table} WHERE {col_name} >= %s AND {col_name} <= %s ORDER BY {col_name} ASC"
            cursor.execute(query, (min_id, max_id))
            results = cursor.fetchall()
            conn.close()
            
            used_ids = set(row[col_name] for row in results)
            
            # 2. Find gap
            for candidate in range(min_id, max_id + 1):
                if candidate not in used_ids:
                    return candidate
            
            return None # Full
            
        except mysql.connector.Error as e:
            print(f"DbManager Error: {e}")
            return None

    def get_character_location(self, character_name, realm_config):
        """
        Fetches character location (map, x, y, z) from the realm specified in realm_config.
        Uses a separate connection based on realm_config credentials if provided, otherwise default.
        """
        try:
            # Determine DB Name
            # ConfigManager.get_realms returns dicts with 'db_chars_name'
            char_db = realm_config.get("db_chars_name", "acore_characters")
            
            # Use 'auth_database' credentials from config (or realm specific if supported)
            # Standard: Realms share Auth/User/Pass but have different DB names
            # But we should respect if retrieving for a remote Dev Realm
            
            # We need to access global Auth config to connect if realm_config doesn't have creds
            # In ConfigManager structure, individual realms don't have user/pass unless custom.
            # We will use the main auth config for connection, but point to the specific char DB.
            
            auth_config = self.config_manager.config.get("auth_database", {})
            
            conn = mysql.connector.connect(
                host=auth_config.get("host", "localhost"),
                port=auth_config.get("port", 3306),
                user=auth_config.get("user", "acore"),
                password=auth_config.get("password", "acore"),
                database=char_db
            )
            
            cursor = conn.cursor(dictionary=True)
            query = "SELECT map, position_x, position_y, position_z FROM characters WHERE name = %s"
            cursor.execute(query, (character_name,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'map': result['map'],
                    'x': result['position_x'],
                    'y': result['position_y'],
                    'z': result['position_z']
                }
            return None
            
        except mysql.connector.Error as e:
            print(f"DbManager Error (get_character_location): {e}")
            return None

    def save_quest_transaction(self, package, dry_run=True):
        """
        Saves the quest and its relations in a single transaction using the multi-table package.
        :param dry_run: If True, prints SQL but does NOT execute changes. Default True for safety.
        """
        conn = None
        try:
            conn = self.get_connection()
            # conn.start_transaction() # Not needed for dry_run really, but good for structure if we were validating
            cursor = conn.cursor()
            
            q_id = package['id']
            print(f"--- QUEST TRANSACTION START (Dry Run: {dry_run}) ---")
            
            def exec_or_log(sql, params=None):
                if dry_run:
                    print(f"[DRY RUN SQL]: {sql} | Params: {params}")
                else:
                    cursor.execute(sql, params)
            
            # --- 1. Quest Template (The Face) ---
            template = package['template']
            if template:
                exec_or_log("DELETE FROM quest_template WHERE ID = %s", (q_id,))
                
                columns = ', '.join(template.keys())
                placeholders = ', '.join(['%s'] * len(template))
                sql = f"INSERT INTO quest_template ({columns}) VALUES ({placeholders})"
                exec_or_log(sql, list(template.values()))
            
            # --- 2. Quest Template Addon (The Brain) ---
            addon = package.get('addon')
            if addon:
                exec_or_log("DELETE FROM quest_template_addon WHERE ID = %s", (q_id,))
                
                columns = ', '.join(addon.keys())
                placeholders = ', '.join(['%s'] * len(addon))
                sql = f"INSERT INTO quest_template_addon ({columns}) VALUES ({placeholders})"
                exec_or_log(sql, list(addon.values()))
                
            # --- 3. POI (The Map) ---
            poi = package.get('poi')
            if poi:
                exec_or_log("DELETE FROM quest_poi WHERE QuestID = %s", (q_id,))
                exec_or_log("DELETE FROM quest_poi_points WHERE QuestID = %s", (q_id,))
                
                poi_id = 1
                map_id = poi['MapID']
                sql_poi = """INSERT INTO quest_poi (QuestID, id, ObjectiveIndex, MapID, WorldMapAreaId, Floor, Priority, Flags)
                    VALUES (%s, %s, -1, %s, 0, 0, 0, 0)"""
                exec_or_log(sql_poi, (q_id, poi_id, map_id))
                
                x = poi['X']
                y = poi['Y']
                sql_pts = """INSERT INTO quest_poi_points (QuestID, Idx1, Idx2, X, Y)
                    VALUES (%s, %s, 0, %s, %s)"""
                exec_or_log(sql_pts, (q_id, poi_id, x, y))
                
            # --- 4. Relations (Starter/Ender) ---
            relations = package.get('relations', {})
            starter_id = relations.get('starter_id')
            ender_id = relations.get('ender_id')
            
            if starter_id:
                exec_or_log("DELETE FROM creature_queststarter WHERE quest = %s", (q_id,))
                exec_or_log("INSERT INTO creature_queststarter (id, quest) VALUES (%s, %s)", (starter_id, q_id))
            
            if ender_id:
                exec_or_log("DELETE FROM creature_questender WHERE quest = %s", (q_id,))
                exec_or_log("INSERT INTO creature_questender (id, quest) VALUES (%s, %s)", (ender_id, q_id))
                
            # --- 5. Loot (Side Effects) ---
            loot = package.get('loot')
            if loot:
                exec_or_log("DELETE FROM creature_loot_template WHERE Entry = %s AND Item = %s", (loot['Entry'], loot['Item']))
                
                cols = ', '.join(loot.keys())
                phs = ', '.join(['%s'] * len(loot))
                sql = f"INSERT INTO creature_loot_template ({cols}) VALUES ({phs})"
                exec_or_log(sql, list(loot.values()))

            # --- 6. Loot GO (Side Effects) ---
            loot_go = package.get('loot_go')
            if loot_go:
                exec_or_log("DELETE FROM gameobject_loot_template WHERE Entry = %s AND Item = %s", (loot_go['Entry'], loot_go['Item']))
                
                cols = ', '.join(loot_go.keys())
                phs = ', '.join(['%s'] * len(loot_go))
                sql = f"INSERT INTO gameobject_loot_template ({cols}) VALUES ({phs})"
                exec_or_log(sql, list(loot_go.values()))

            # --- 7. Quest Text (Offer/Request) ---
            text = package.get('text')
            if text:
                reward_text = text.get('RewardText')
                completion_text = text.get('CompletionText')
                
                # quest_offer_reward
                if reward_text:
                    exec_or_log("DELETE FROM quest_offer_reward WHERE ID = %s", (q_id,))
                    exec_or_log("INSERT INTO quest_offer_reward (ID, RewardText) VALUES (%s, %s)", (q_id, reward_text))
                    
                # quest_request_items
                if completion_text:
                    exec_or_log("DELETE FROM quest_request_items WHERE ID = %s", (q_id,))
                    exec_or_log("INSERT INTO quest_request_items (ID, CompletionText) VALUES (%s, %s)", (q_id, completion_text))
            
            if not dry_run:
                conn.commit()
                print(f"SUCCESS: Quest {q_id} saved locally.")
            else:
                print("--- TRANSACTION COMPLETE (Simulated/Dry Run) ---")
                
            return True
            
        except mysql.connector.Error as e:
            print(f"Transaction Failed: {e}")
            if conn and not dry_run:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
