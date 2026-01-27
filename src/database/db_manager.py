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
        
    def get_connection(self, db_name=None, realm_id=None):
        auth_config = self.config_manager.config.get("auth_database", {})
        if not db_name:
            if realm_id:
                # Find specific realm by ID
                realms = self.config_manager.get_realms()
                realm = next((r for r in realms if r["id"] == realm_id), None)
                if realm:
                    db_name = realm.get("db_world_name", "acore_world")
                else:
                    # Fallback to default if ID not found? Or Error?
                    print(f"DbManager Warning: Realm ID {realm_id} not found, using active.")
                    realm = self.config_manager.get_active_realm()
                    db_name = realm.get("db_world_name", "acore_world")
            else:
                # Default to active realm
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

    def save_quest_transaction(self, package, dry_run=True, log_file=None, cleanup_file=None, realm_id=None):
        """
        Saves the quest and its relations in a single transaction using the multi-table package.
        :param dry_run: If True, prints SQL but does NOT execute changes. Default True for safety.
        :param log_file: Optional path to append successful SQL statements to.
        :param cleanup_file: Optional path to append DELETE statements to (for cleanup/reversal).
        :param realm_id: ID of the realm to write to (Target vs Dev).
        """
        conn = None
        try:
            conn = self.get_connection(realm_id=realm_id)
            # conn.start_transaction() # Not needed for dry_run really, but good for structure if we were validating
            cursor = conn.cursor()
            
            q_id = package['id']
            print(f"--- QUEST TRANSACTION START (Dry Run: {dry_run}) ---")
            
            # Initialize/Clear granular files (Overwrite mode)
            if not dry_run:
                if log_file:
                    try:
                        open(log_file, 'w').close()
                    except Exception as e:
                        print(f"Warning: Could not init log file {log_file}: {e}")
                
                if cleanup_file:
                    try:
                        open(cleanup_file, 'w').close()
                    except Exception as e:
                        print(f"Warning: Could not init cleanup file {cleanup_file}: {e}")
            
            def format_sql_value(val):
                if val is None:
                    return "NULL"
                elif isinstance(val, str):
                    clean = val.replace("'", "''").replace("\\", "\\\\") # Basic escape
                    return f"'{clean}'"
                else:
                    return str(val)

            def exec_or_log(sql, params=None):
                # 1. Logic for Cleanup / Deletion Logging
                # If this is a DELETE statement, log it to the cleanup file 
                # (We do this BEFORE execution/forward logging)
                if cleanup_file and sql.strip().upper().startswith("DELETE"):
                    try:
                        if params:
                            formatted_params = [format_sql_value(p) for p in params]
                            reconstructed = sql % tuple(formatted_params)
                        else:
                            reconstructed = sql
                        
                        with open(cleanup_file, "a") as f:
                            f.write(reconstructed + ";\n")
                    except Exception as e:
                        print(f"Failed to log SQL to cleanup file: {e}")

                if dry_run:
                    print(f"[DRY RUN SQL]: {sql} | Params: {params}")
                else:
                    cursor.execute(sql, params)
                    
                    if log_file:
                        # Best effort SQL reconstruction
                        try:
                            # If sql uses %s, replace with formatted params
                            if params:
                                formatted_params = [format_sql_value(p) for p in params]
                                reconstructed = sql % tuple(formatted_params)
                            else:
                                reconstructed = sql
                                
                            with open(log_file, "a") as f:
                                f.write(reconstructed + ";\n")
                        except Exception as e:
                            print(f"Failed to log SQL to file: {e}")
            
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
                # quest_offer_reward
                offer = package.get('offer') # Separate dict for fully detailed offer
                # Fallback to text package for legacy/simple calls
                reward_text = package.get('text', {}).get('RewardText', '') 
                
                if offer:
                    # Detailed Offer Package
                    cols = ["ID", "RewardText"]
                    vals = [q_id, offer.get('RewardText', reward_text)]
                    placeholders = ["%s", "%s"]
                    
                    # Emotes 1-4
                    for i in range(1, 5):
                         cols.append(f"Emote{i}")
                         vals.append(offer.get(f"Emote{i}", 0))
                         placeholders.append("%s")
                         cols.append(f"EmoteDelay{i}")
                         vals.append(offer.get(f"EmoteDelay{i}", 0))
                         placeholders.append("%s")
                    
                    exec_or_log("DELETE FROM quest_offer_reward WHERE ID = %s", (q_id,))
                    sql = f"INSERT INTO quest_offer_reward ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                    exec_or_log(sql, tuple(vals))
                    
                elif reward_text:
                    # Simple (Text Only)
                    exec_or_log("DELETE FROM quest_offer_reward WHERE ID = %s", (q_id,))
                    exec_or_log("INSERT INTO quest_offer_reward (ID, RewardText) VALUES (%s, %s)", (q_id, reward_text))
                    
                # quest_request_items
                request = package.get('request') # Separate dict
                completion_text = package.get('text', {}).get('CompletionText', '')
                
                if request:
                     # Detailed Request Package
                    cols = ["ID", "CompletionText"]
                    vals = [q_id, request.get('CompletionText', completion_text)]
                    placeholders = ["%s", "%s"]
                    
                    # Emotes
                    cols.append("EmoteOnComplete")
                    vals.append(request.get("EmoteOnComplete", 0))
                    placeholders.append("%s")
                    cols.append("EmoteOnIncomplete")
                    vals.append(request.get("EmoteOnIncomplete", 0))
                    placeholders.append("%s")
                    
                    exec_or_log("DELETE FROM quest_request_items WHERE ID = %s", (q_id,))
                    sql = f"INSERT INTO quest_request_items ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                    exec_or_log(sql, tuple(vals))
                    
                elif completion_text:
                    exec_or_log("DELETE FROM quest_request_items WHERE ID = %s", (q_id,))
                    exec_or_log("INSERT INTO quest_request_items (ID, CompletionText) VALUES (%s, %s)", (q_id, completion_text))
            
            # --- 8. Gossip & Scripts (The Brain 2.0) ---
            gossip = package.get('gossip', [])
            for g in gossip:
                npc_id = g['npc_id']
                menu_id = g['menu_id']
                text_id = g['text_id']
                npc_text = g['npc_text_content']
                option_text = g['option_text_content']
                
                # 1. npc_text
                # Note: npc_text schema usually has ID, text0_0, text0_1... we will fill 0_0 and 0_1 with same text for ease
                # We need to delete old one first if we are forcefully overwriting ID
                exec_or_log("DELETE FROM npc_text WHERE ID = %s", (text_id,))
                
                # Assuming standard Trinity/AC npc_text structure. 
                # ID, text0_0, text0_1, lang0, Probability0, em0_0, em0_1, em0_2, em0_3, em0_4, em0_5, ... (simplified for query)
                # We will only insert the necessary columns.
                sql_nt = "INSERT INTO npc_text (ID, text0_0, text0_1, Probability0) VALUES (%s, %s, %s, 1)"
                exec_or_log(sql_nt, (text_id, npc_text, npc_text))
                
                # 2. gossip_menu
                exec_or_log("DELETE FROM gossip_menu WHERE MenuID = %s AND TextID = %s", (menu_id, text_id))
                exec_or_log("INSERT INTO gossip_menu (MenuID, TextID) VALUES (%s, %s)", (menu_id, text_id))
                
                # 3. gossip_menu_option
                # OptionIndex 0, OptionID 1 (Gossip), ActionMenuID 0, ActionPoiID 0, BoxCoded 0, BoxMoney 0, BoxText ''
                # OptionNpcFlag = 1 (GOSSIP) required to show up on Gossip NPCs.
                exec_or_log("DELETE FROM gossip_menu_option WHERE MenuID = %s", (menu_id,))
                sql_gmo = """INSERT INTO gossip_menu_option 
                             (MenuID, OptionID, OptionIcon, OptionText, OptionType, OptionNpcFlag) 
                             VALUES (%s, 0, 0, %s, 1, 1)""" 
                # OptionType 1 = GOSSIP_OPTION_GOSSIP. 
                exec_or_log(sql_gmo, (menu_id, option_text))
                
                # 4. creature_template Update
                # This is the "Overwrite" part.
                exec_or_log("UPDATE creature_template SET gossip_menu_id = %s, npcflag = npcflag | 1 WHERE entry = %s", (menu_id, npc_id))
                
                # 5. Smart Script (SAI)
                # Delete existing script for this source/event if needed? SAI uses (entryOrGuid, source_type, id, link) as composite key usually?
                # Actually commonly (entryorguid, sourcetype, id). ID is the line ID.
                # We will just append a new line or overwrite line 0 if simplistic.
                # Only if dry_run logic allows? SAI tables are complex.
                # We will DELETE based on source first to be clean for this tool's scope.
                
                # SourceType 0 = Creature. EntryOrGuid = npc_id. 
                # Wait, SAI runs on the creature. But is the event triggered by the gossip menu?
                # GOSSIP_SELECT (62) is a standard Event.
                
                exec_or_log("DELETE FROM smart_scripts WHERE entryorguid = %s AND source_type = 0 AND event_type = 62 AND event_param1 = %s", (npc_id, menu_id))
                
                # Added 'comment' field to prevent Error 1364 (Field 'comment' doesn't have a default value)
                sql_sai = """INSERT INTO smart_scripts 
                             (entryorguid, source_type, id, link, event_type, event_param1, event_param2, action_type, action_param1, target_type, comment)
                             VALUES (%s, 0, 0, 0, 62, %s, 0, 15, %s, 7, %s)"""
                # event_param1 = MenuID (matches gossip_menu_option.MenuID)
                # action_param1 = QuestID (Reward Credit)
                # target_type 7 = Invoker
                
                comment_str = f"AzerothForge: Quest {q_id} Credit on Gossip Select"
                exec_or_log(sql_sai, (npc_id, menu_id, q_id, comment_str))
            
            # --- 9. Phasing (spell_area) ---
            spell_area = package.get('spell_area', [])
            if spell_area:
                 # We can't easily delete "all related to this quest" because spell_area is (spell, area, quest_start/end/etc).
                 # Wait, spell_area uses 'quest_start' and 'quest_end' columns.
                 # Usually we insert rows where quest_start = q_id.
                 # Let's focus on quest_start = q_id logic.
                 # Delete existing rows where quest_start = q_id?
                 exec_or_log("DELETE FROM spell_area WHERE quest_start = %s", (q_id,))
                 
                 for sa in spell_area:
                     # {spell, area, autocast}
                     # Schema: spell, area, quest_start, quest_end, aura_spell, racemask, gender, autocast
                     sql_sa = """INSERT INTO spell_area 
                                 (spell, area, quest_start, quest_end, aura_spell, racemask, gender, autocast)
                                 VALUES (%s, %s, %s, 0, 0, 0, 2, %s)"""
                     exec_or_log(sql_sa, (sa['spell'], sa['area'], q_id, sa['autocast']))
                     
            # --- 10. Triggered Phasing (SmartAI) ---
            smart_phasing = package.get('smart_phasing')
            if smart_phasing:
                p_acc = smart_phasing.get('accept', 0)
                p_com = smart_phasing.get('complete', 0)
                
                # Check Starters/Enders
                # We need to apply this to the Quest Givers. 
                # Relation data is in package['relations'] -> starter_id
                relations = package.get('relations', {})
                starter_id = relations.get('starter_id')
                
                if starter_id:
                     # Delete Old Phasing Scripts (Event 19=Accept, 20=Reward; Action 88=PhaseMask)
                     # For THIS starter and THIS quest
                     sql_del_sai = """DELETE FROM smart_scripts 
                                      WHERE entryorguid = %s AND source_type = 0 
                                      AND event_type IN (19, 20)
                                      AND action_type = 88
                                      AND event_param1 = %s"""
                     exec_or_log(sql_del_sai, (starter_id, q_id))
                     
                     if p_acc > 0:
                         # Accepted Quest -> Set Phase Mask
                         sql_acc = """INSERT INTO smart_scripts
                                      (entryorguid, source_type, id, link, event_type, event_param1, action_type, action_param1, target_type, comment)
                                      VALUES (%s, 0, 0, 0, 19, %s, 88, %s, 7, %s)"""
                         exec_or_log(sql_acc, (starter_id, q_id, p_acc, f"Quest {q_id} Accept Phase"))
                         
                     if p_com > 0:
                         # Reward Quest -> Set Phase Mask
                         sql_com = """INSERT INTO smart_scripts
                                      (entryorguid, source_type, id, link, event_type, event_param1, action_type, action_param1, target_type, comment)
                                      VALUES (%s, 0, 0, 0, 20, %s, 88, %s, 7, %s)"""
                         exec_or_log(sql_com, (starter_id, q_id, p_com, f"Quest {q_id} Reward Phase"))
                         
            # --- 11. Custom Loot ---
            loot = package.get('loot')
            if loot:
                 # Creature Loot
                 # Schema: Entry, Item, Reference, Chance, QuestRequired, LootMode, GroupId, MinCount, MaxCount
                 eid = loot['Entry']
                 item = loot['Item']
                 chance = loot['Chance']
                 gid = loot['GroupId']
                 
                 # Force Quest Loot? Usually check 'QuestRequired' = True? 
                 # Or just insert. Loot templates are complex.
                 # Let's assume we append simple loot.
                 # We can't easily "Delete old" unless we know exact item/entry combo.
                 exec_or_log("DELETE FROM creature_loot_template WHERE Entry = %s AND Item = %s", (eid, item))
                 
                 sql_loot = """INSERT INTO creature_loot_template 
                               (Entry, Item, Reference, Chance, QuestRequired, LootMode, GroupId, MinCount, MaxCount)
                               VALUES (%s, %s, 0, %s, 1, 1, %s, 1, 1)"""
                 exec_or_log(sql_loot, (eid, item, chance, gid))
                 
            loot_go = package.get('loot_go')
            if loot_go:
                 eid = loot_go['Entry']
                 item = loot_go['Item']
                 chance = loot_go['Chance']
                 gid = loot_go['GroupId']
                 
                 exec_or_log("DELETE FROM gameobject_loot_template WHERE Entry = %s AND Item = %s", (eid, item))
                 
                 sql_loot_go = """INSERT INTO gameobject_loot_template 
                               (Entry, Item, Reference, Chance, QuestRequired, LootMode, GroupId, MinCount, MaxCount)
                               VALUES (%s, %s, 0, %s, 1, 1, %s, 1, 1)"""
                 exec_or_log(sql_loot_go, (eid, item, chance, gid))

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

    def get_all_quests(self, realm_id=None, min_id=0, max_id=999999):
        """Returns quests within range with ID, Title, Level, MinLevel, and linked Names."""
        print(f"DEBUG: get_all_quests called with realm_id={realm_id}, range={min_id}-{max_id}")
        
        query = f"""
            SELECT qt.ID, qt.LogTitle, qt.QuestLevel, qt.MinLevel, qt.RewardMoney,
                   (SELECT GROUP_CONCAT(c1.name) FROM creature_queststarter qs JOIN creature_template c1 ON qs.id = c1.entry WHERE qs.quest = qt.ID) as StarterNames,
                   (SELECT GROUP_CONCAT(c2.name) FROM creature_questender qe JOIN creature_template c2 ON qe.id = c2.entry WHERE qe.quest = qt.ID) as EnderNames
            FROM quest_template qt
            WHERE qt.ID BETWEEN {min_id} AND {max_id}
            ORDER BY qt.ID DESC
        """
        
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Error (get_all_quests): {e}")
            return []

    def get_all_npcs(self, realm_id=None, min_id=0, max_id=999999):
        """Returns NPCs within range."""
        query = f"""
            SELECT entry, name, subname, minlevel, maxlevel, npcflag
            FROM creature_template
            WHERE entry BETWEEN {min_id} AND {max_id}
            ORDER BY entry DESC
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Error (get_all_npcs): {e}")
            return []

    def get_all_items(self, realm_id=None, min_id=0, max_id=999999):
        """Returns Items within range."""
        query = f"""
            SELECT entry, name, ItemLevel, RequiredLevel, Quality, class, subclass
            FROM item_template
            WHERE entry BETWEEN {min_id} AND {max_id}
            ORDER BY entry DESC
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Error (get_all_items): {e}")
            return []

    def get_campaign_dependencies(self, realm_id, min_quest_id, max_quest_id):
        """
        Fetches all linked NPCs and Items for quests in the given range.
        Returns a dict: {'npcs': [rows], 'items': [rows]}
        """
        range_cond = f"quest BETWEEN {min_quest_id} AND {max_quest_id}"
        q_template_cond = f"ID BETWEEN {min_quest_id} AND {max_quest_id}"
        
        # Optimizing: Group into UNIONs
        # NPC IDs Union
        npc_query_parts = [
             f"SELECT id FROM creature_queststarter WHERE {range_cond}",
             f"SELECT id FROM creature_questender WHERE {range_cond}",
             f"SELECT RequiredNpcOrGo1 as id FROM quest_template WHERE {q_template_cond} AND RequiredNpcOrGo1 > 0",
             f"SELECT RequiredNpcOrGo2 as id FROM quest_template WHERE {q_template_cond} AND RequiredNpcOrGo2 > 0",
             f"SELECT RequiredNpcOrGo3 as id FROM quest_template WHERE {q_template_cond} AND RequiredNpcOrGo3 > 0",
             f"SELECT RequiredNpcOrGo4 as id FROM quest_template WHERE {q_template_cond} AND RequiredNpcOrGo4 > 0"
        ]
        full_npc_query = " UNION ".join(npc_query_parts)
        
        # Item IDs Union
        item_query_parts = [
             f"SELECT RewardItem1 as id FROM quest_template WHERE {q_template_cond} AND RewardItem1 > 0",
             f"SELECT RewardItem2 as id FROM quest_template WHERE {q_template_cond} AND RewardItem2 > 0",
             f"SELECT RewardItem3 as id FROM quest_template WHERE {q_template_cond} AND RewardItem3 > 0",
             f"SELECT RewardItem4 as id FROM quest_template WHERE {q_template_cond} AND RewardItem4 > 0",
             f"SELECT RequiredItemId1 as id FROM quest_template WHERE {q_template_cond} AND RequiredItemId1 > 0",
             f"SELECT RequiredItemId2 as id FROM quest_template WHERE {q_template_cond} AND RequiredItemId2 > 0",
             f"SELECT RequiredItemId3 as id FROM quest_template WHERE {q_template_cond} AND RequiredItemId3 > 0",
             f"SELECT RequiredItemId4 as id FROM quest_template WHERE {q_template_cond} AND RequiredItemId4 > 0",
             f"SELECT RewardChoiceItemID1 as id FROM quest_template WHERE {q_template_cond} AND RewardChoiceItemID1 > 0",
             f"SELECT RewardChoiceItemID2 as id FROM quest_template WHERE {q_template_cond} AND RewardChoiceItemID2 > 0",
             f"SELECT RewardChoiceItemID3 as id FROM quest_template WHERE {q_template_cond} AND RewardChoiceItemID3 > 0",
             f"SELECT RewardChoiceItemID4 as id FROM quest_template WHERE {q_template_cond} AND RewardChoiceItemID4 > 0",
             f"SELECT RewardChoiceItemID5 as id FROM quest_template WHERE {q_template_cond} AND RewardChoiceItemID5 > 0",
             f"SELECT RewardChoiceItemID6 as id FROM quest_template WHERE {q_template_cond} AND RewardChoiceItemID6 > 0"
        ]
        full_item_query = " UNION ".join(item_query_parts)
        
        
        try:
             conn = self.get_connection(realm_id=realm_id)
             cursor = conn.cursor(dictionary=True)
             
             # Run 1: NPCs
             cursor.execute(full_npc_query)
             rows_n = cursor.fetchall()
             npc_ids = {r['id'] for r in rows_n if 'id' in r}
                 
             # Run 2: Items
             cursor.execute(full_item_query)
             rows_i = cursor.fetchall()
             item_ids = {r['id'] for r in rows_i if 'id' in r}
                 
             # Now fetch details
             npc_details = []
             if npc_ids:
                 ids_str = ",".join(map(str, npc_ids))
                 q_n = f"SELECT entry, name, subname, minlevel, maxlevel, npcflag FROM creature_template WHERE entry IN ({ids_str}) ORDER BY entry"
                 cursor.execute(q_n)
                 npc_details = cursor.fetchall()
                 
             item_details = []
             if item_ids:
                 ids_str = ",".join(map(str, item_ids))
                 q_i = f"SELECT entry, name, ItemLevel, RequiredLevel FROM item_template WHERE entry IN ({ids_str}) ORDER BY entry"
                 cursor.execute(q_i)
                 item_details = cursor.fetchall()
                 
             conn.close()
             return {'npcs': npc_details, 'items': item_details}
             
        except mysql.connector.Error as e:
            print(f"Error fetching campaign deps: {e}")
            return {'npcs': [], 'items': []}

    def get_quest_template(self, quest_id, realm_id=None):
        """Fetches full quest dict for a single ID."""
        query = f"SELECT * FROM quest_template WHERE ID = {quest_id}"
        
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            row = cursor.fetchone()
            conn.close()
            return row
            
        except mysql.connector.Error as e:
            print(f"DbManager Error (get_quest_template): {e}")
            return None

    def save_quest_template(self, quest_data, realm_id=None):
        """Updates quest_template for a specific ID."""
        if not quest_data or 'ID' not in quest_data:
            return False, "Invalid Data"
            
        q_id = quest_data['ID']
        
        # Build UPDATE query dynamically
        # Exclude ID from set clause
        fields = []
        values = []
        
        for k, v in quest_data.items():
            if k == 'ID': continue
            fields.append(f"{k} = %s")
            values.append(v)
            
        if not fields:
             return True, "No changes"
             
        sql = f"UPDATE quest_template SET {', '.join(fields)} WHERE ID = %s"
        full_values = values + [q_id]
        
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            cursor.execute(sql, full_values)
            conn.commit()
            conn.close()
            return True, "Saved"
            
        except mysql.connector.Error as e:
            print(f"Update failed: {e}")
            return False, str(e)

    def get_quest_extended(self, quest_id, realm_id=None):
        """
        Fetches full quest data including:
        - quest_template (Base)
        - quest_template_addon (Logic)
        - quest_offer_reward (Emotes/Text)
        - quest_request_items (Emotes/Text)
        - creature_queststarter (List)
        - creature_questender (List)
        """
        data = {}
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            
            # 1. Base Template
            cursor.execute(f"SELECT * FROM quest_template WHERE ID = {quest_id}")
            data['template'] = cursor.fetchone()
            
            # 2. Addon
            cursor.execute(f"SELECT * FROM quest_template_addon WHERE ID = {quest_id}")
            data['addon'] = cursor.fetchone()
            
            # 3. Offer Reward
            cursor.execute(f"SELECT * FROM quest_offer_reward WHERE ID = {quest_id}")
            data['offer_reward'] = cursor.fetchone()
            
            # 4. Request Items
            cursor.execute(f"SELECT * FROM quest_request_items WHERE ID = {quest_id}")
            data['request_items'] = cursor.fetchone()
            
            # 5. Starters
            cursor.execute(f"SELECT id FROM creature_queststarter WHERE quest = {quest_id}")
            data['starters'] = [r['id'] for r in cursor.fetchall()]
            
            # 6. Enders
            cursor.execute(f"SELECT id FROM creature_questender WHERE quest = {quest_id}")
            data['enders'] = [r['id'] for r in cursor.fetchall()]
            
            conn.close()
            return data
            
        except mysql.connector.Error as e:
            print(f"DbManager Error (get_quest_extended): {e}")
            return None

    def save_quest_extended(self, full_data, realm_id=None):
        """
        Transactionally saves full quest data.
        full_data structure:
        {
            'ID': int,
            'template': dict,
            'addon': dict,
            'offer_reward': dict,
            'request_items': dict,
            'starters': [ids],
            'enders': [ids]
        }
        """
        q_id = full_data.get('ID')
        if not q_id: return False, "Missing ID"
        
        conn = None
        try:
            conn = self.get_connection(realm_id=realm_id)
            conn.start_transaction()
            cursor = conn.cursor()
            
            # Helper to execute/update (Upsert Logic)
            def upsert(table, data, pk_col='ID'):
                if not data: return # Nothing to save
                
                # Delete existing to handle complete replace (simplest for 1:1)
                cursor.execute(f"DELETE FROM {table} WHERE {pk_col} = %s", (q_id,))
                
                # Insert
                keys = list(data.keys())
                vals = list(data.values())
                # Ensure ID is in data or added? Usually passed data contains ID.
                # If not, add it.
                if pk_col not in data:
                    keys.append(pk_col)
                    vals.append(q_id)
                elif data[pk_col] != q_id:
                     # Sanity check
                     pass

                cols = ", ".join(keys)
                binds = ", ".join(["%s"] * len(keys))
                sql = f"INSERT INTO {table} ({cols}) VALUES ({binds})"
                cursor.execute(sql, vals)

            # 1. Template
            if 'template' in full_data and full_data['template']:
                upsert("quest_template", full_data['template'])
                
            # 2. Addon
            if 'addon' in full_data and full_data['addon']:
                 upsert("quest_template_addon", full_data['addon'])
            
            # 3. Offer Reward
            if 'offer_reward' in full_data and full_data['offer_reward']:
                 upsert("quest_offer_reward", full_data['offer_reward'])
            
            # 4. Request Items
            if 'request_items' in full_data and full_data['request_items']:
                 upsert("quest_request_items", full_data['request_items'])
                 
            # 5. Starters (M:N)
            if 'starters' in full_data:
                cursor.execute("DELETE FROM creature_queststarter WHERE quest = %s", (q_id,))
                for npc in full_data['starters']:
                    cursor.execute("INSERT INTO creature_queststarter (id, quest) VALUES (%s, %s)", (npc, q_id))
            
            # 6. Enders (M:N)
            if 'enders' in full_data:
                cursor.execute("DELETE FROM creature_questender WHERE quest = %s", (q_id,))
                for npc in full_data['enders']:
                    cursor.execute("INSERT INTO creature_questender (id, quest) VALUES (%s, %s)", (npc, q_id))
            
            conn.commit()
            conn.close()
            return True, "Saved Extended Data"
            
        except mysql.connector.Error as e:
            if conn: conn.rollback()
            print(f"Save Extended Error: {e}")
            return False, str(e)
        finally:
            if conn and conn.is_connected():
                conn.close()

    def search_creatures(self, search_text="", realm_id=None, limit=2000):
        """
        Searches creatures by ID or Name.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            
            if not search_text:
                query = f"SELECT entry, name, subname, minlevel, maxlevel, npcflag FROM creature_template ORDER BY entry DESC LIMIT {limit}"
                args = ()
            else:
                # Check if int for ID search
                is_id = search_text.isdigit()
                if is_id:
                    query = f"""
                        SELECT entry, name, subname, minlevel, maxlevel, npcflag 
                        FROM creature_template 
                        WHERE entry = %s OR name LIKE %s 
                        ORDER BY entry LIMIT {limit}
                    """
                    args = (int(search_text), f"%{search_text}%")
                else:
                    query = f"""
                        SELECT entry, name, subname, minlevel, maxlevel, npcflag 
                        FROM creature_template 
                        WHERE name LIKE %s 
                        ORDER BY entry LIMIT {limit}
                    """
                    args = (f"%{search_text}%",)
            
            cursor.execute(query, args)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Search Error (Creature): {e}")
            return []

    def search_items(self, search_text="", realm_id=None, limit=2000):
        """
        Searches items by ID or Name.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            
            if not search_text:
                query = f"SELECT entry, name, ItemLevel, RequiredLevel, Quality, class, subclass FROM item_template ORDER BY entry DESC LIMIT {limit}"
                args = ()
            else:
                is_id = search_text.isdigit()
                if is_id:
                    query = f"""
                        SELECT entry, name, ItemLevel, RequiredLevel, Quality, class, subclass 
                        FROM item_template 
                        WHERE entry = %s OR name LIKE %s 
                        ORDER BY entry LIMIT {limit}
                    """
                    args = (int(search_text), f"%{search_text}%")
                else:
                    query = f"""
                        SELECT entry, name, ItemLevel, RequiredLevel, Quality, class, subclass 
                        FROM item_template 
                        WHERE name LIKE %s 
                        ORDER BY entry LIMIT {limit}
                    """
                    args = (f"%{search_text}%",)
            
            cursor.execute(query, args)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Search Error (Item): {e}")
            return []

    def search_quests(self, search_text="", realm_id=None, limit=2000):
        """
        Searches quests by ID or Title.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)

            if not search_text:
                query = (
                    f"SELECT ID, LogTitle, QuestLevel, MinLevel, RewardMoney "
                    f"FROM quest_template ORDER BY ID DESC LIMIT {limit}"
                )
                args = ()
            else:
                is_id = search_text.isdigit()
                if is_id:
                    query = f"""
                        SELECT ID, LogTitle, QuestLevel, MinLevel, RewardMoney
                        FROM quest_template
                        WHERE ID = %s OR LogTitle LIKE %s
                        ORDER BY ID LIMIT {limit}
                    """
                    args = (int(search_text), f"%{search_text}%")
                else:
                    query = f"""
                        SELECT ID, LogTitle, QuestLevel, MinLevel, RewardMoney
                        FROM quest_template
                        WHERE LogTitle LIKE %s
                        ORDER BY ID LIMIT {limit}
                    """
                    args = (f"%{search_text}%",)

            cursor.execute(query, args)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Search Error (Quest): {e}")
            return []

    
    # ---------------------------------------------------------
    # Expansion: Phasing & SmartAI
    # ---------------------------------------------------------

    def get_quest_spell_area(self, quest_id, realm_id=None):
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM spell_area WHERE quest_start = %s OR quest_end = %s", (quest_id, quest_id))
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            print(f"DbManager Error (spell_area): {e}")
            return []

    def save_quest_spell_area(self, quest_id, entries, realm_id=None):
        """
        Replaces spell_area entries for this quest.
        entries: list of dicts {'spell': int, 'area': int, 'quest_start': int, 'quest_end': int, 'autocast': int, ...}
        Note: Since a quest might be a start for ONE row and end for ANOTHER, strictly deleting by quest_id might be dangerous 
        if we only edit 'start' ones. 
        However, the UI for 'Permanent Phasing' usually implies this quest is the trigger. 
        We will delete rows where `quest_start` is THIS quest (if we manage start triggers).
        If the user wants to manage 'End' triggers, that's usually on the Previous Quest's editor. 
        For now, we manage rows where `quest_start` == quest_id.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            # Delete existing 'Start' triggers for this quest
            cursor.execute("DELETE FROM spell_area WHERE quest_start = %s", (quest_id,))
            
            # Insert new
            for e in entries:
                # We expect e to handle basic columns
                sql = """INSERT INTO spell_area (spell, area, quest_start, quest_end, autocast, gender, race, class) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                # Defaults
                spell = e.get('spell')
                area = e.get('area')
                q_start = quest_id # Enforce THIS quest as start
                q_end = e.get('quest_end', 0)
                ac = e.get('autocast', 1)
                gender = e.get('gender', -1)
                race = e.get('race', -1)
                cls = e.get('class', -1)
                
                cursor.execute(sql, (spell, area, q_start, q_end, ac, gender, race, cls))
                
            conn.commit()
            conn.close()
            return True, "Saved Spell Area"
        except mysql.connector.Error as e:
            print(f"DbManager Save Error (spell_area): {e}")
            return False, str(e)

    def add_smart_script(self, entry, source_type, event, action, target=0, phase=0, 
                         param1=0, param2=0, param3=0, param4=0, link=0, event_phase_mask=0,
                         realm_id=None):
        """
        Adds a Smart Script.
        Auto-generates ID logic if needed (SmartAI usually allows unique ID per Entry/SourceType).
        Actually SmartAI PK is (entryorguid, source_type, id). ID must be unique.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            # Find next free ID for this entry/source
            cursor.execute("SELECT MAX(id) FROM smart_scripts WHERE entryorguid = %s AND source_type = %s", (entry, source_type))
            res = cursor.fetchone()
            current_max = res[0] if res and res[0] is not None else -1
            new_id = current_max + 1
            
            sql = """INSERT INTO smart_scripts (entryorguid, source_type, id, link, event_type, event_phase_mask, 
                     event_chance, event_flags, event_param1, event_param2, event_param3, event_param4,
                     action_type, action_param1, action_param2, action_param3, action_param4, action_param5, action_param6,
                     target_type, target_param1, target_param2, target_param3, target_x, target_y, target_z, target_o, comment)
                     VALUES (%s, %s, %s, %s, %s, %s, 100, 0, 0, 0, 0, 0, 
                             %s, %s, %s, %s, %s, 0, 0, 
                             %s, 0, 0, 0, 0, 0, 0, 0, %s)"""
            
            comment = f"AF: Auto Generated {event}-{action}"
            
            cursor.execute(sql, (entry, source_type, new_id, link, event, event_phase_mask, 
                                 action, param1, param2, param3, param4, 
                                 target, comment))
            conn.commit()
            conn.close()
            return True, "Added Script"
        except mysql.connector.Error as e:
            print(f"DbManager SmartAI Error: {e}")
            return False, str(e)

    def get_quest_phase_scripts(self, npc_entry, quest_id, realm_id=None):
        """
        Fetches SmartAI scripts on this NPC related to PHASING for this QUEST.
        We look for EVENT_ACCEPTED_QUEST (19) or EVENT_REWARD_QUEST (20) with Action 88 (SET_INGAME_PHASE_MASK).
        Actually, Accept/Reward events take QuestID as param1.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor(dictionary=True)
            
            # Event 19 (Accept) or 20 (Reward) where param1 == quest_id
            # AND action == 88 (Phase)
            sql = """SELECT * FROM smart_scripts 
                     WHERE entryorguid = %s AND source_type = 0 
                     AND (event_type = 19 OR event_type = 20)
                     AND event_param1 = %s
                     AND action_type = 88"""
                     
            cursor.execute(sql, (npc_entry, quest_id))
            rows = cursor.fetchall()
            conn.close()
            return rows
        except mysql.connector.Error as e:
            return []

    def ensure_talk_objective(self, npc_entry, realm_id=None):
        """
        1. Ensures NPC has Gossip Flag (1).
        2. Checks if GOSSIP_HELLO (64) -> KILLED_MONSTER_CREDIT (33) script exists. If not, adds it.
        """
        # 1. Update NPC Flag
        from src.utils.game_constants import NPC_FLAGS, SMART_EVENT, SMART_ACTION, SMART_TARGET
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            # Check current flag
            cursor.execute("SELECT npcflag FROM creature_template WHERE entry = %s", (npc_entry,))
            res = cursor.fetchone()
            if res:
                cur_flags = res[0]
                if not (cur_flags & NPC_FLAGS.GOSSIP):
                    new_flags = cur_flags | NPC_FLAGS.GOSSIP
                    cursor.execute("UPDATE creature_template SET npcflag = %s WHERE entry = %s", (new_flags, npc_entry))
                    conn.commit()
            
            # 2. Check Smart Script
            # Look for Event 64 (Hello) or 62 (Select)
            # We'll use 64 (Hello) for simple "Talk" credit without menu
            # But standard verify: Does it have Action 33 (Kill Credit) targeting Invoker (7)?
            # Note: We need to know WHICH creature credit? Usually the NPC itself.
            # Action Param 1 = Creature Entry (Credit).
            
            sql_check = """SELECT count(*) FROM smart_scripts 
                           WHERE entryorguid = %s AND source_type = 0
                           AND event_type = %s AND action_type = %s AND action_param1 = %s"""
            
            cursor.execute(sql_check, (npc_entry, SMART_EVENT.GOSSIP_HELLO, SMART_ACTION.KILLED_MONSTER_CREDIT, npc_entry))
            count = cursor.fetchone()[0]
            
            script_added = False
            if count == 0:
                # Add it
                # We can't reuse cursor for add_smart_script easily if we want to follow pattern, but let's call self method?
                # Need to close or just use raw insert here? 
                # Better to use helpers but we need to commit first.
                pass
            
            conn.close() 
            
            if count == 0:
                self.add_smart_script(
                    entry=npc_entry,
                    source_type=0, # Creature
                    event=SMART_EVENT.GOSSIP_HELLO,
                    action=SMART_ACTION.KILLED_MONSTER_CREDIT,
                    target=SMART_TARGET.INVOKER, # Player must get credit
                    param1=npc_entry, # Credit for THIS npc
                    realm_id=realm_id
                )
                return True, "Talk Objective Configured"
            
            return True, "Already Configured"
                
        except mysql.connector.Error as e:
            print(f"Ensure Talk Error: {e}")
            return False, str(e)

    def check_talk_objective(self, npc_entry, quest_id, realm_id=None):
        """
        Checks if the NPC is configured to give credit for this quest via Gossip.
        Returns: (True/False, menu_id)
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            # Look for Event 62 (GOSSIP_SELECT) + Action 15 (QUEST_ADD_KILL_CREDIT)
            # Param1 of Action must be quest_id
            sql = """SELECT event_param1, event_param2 FROM smart_scripts
                     WHERE entryorguid = %s AND source_type = 0
                     AND event_type = 62 
                     AND action_type = 15 AND action_param1 = %s"""
            
            cursor.execute(sql, (npc_entry, quest_id))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return True, row[0] # Returns menu_id (event_param1)
            return False, 0
        except:
            return False, 0

    def get_gossip_data(self, menu_id, realm_id=None):
        """
        Fetches the first Option Text and NPC Text for a given menu_id.
        This is heuristic-light: assumes 1 option for the quest.
        """
        gossip_text = ""
        option_text = ""
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            # 1. Get Option Text
            cursor.execute("SELECT OptionText FROM gossip_menu_option WHERE MenuID = %s LIMIT 1", (menu_id,))
            res_opt = cursor.fetchone()
            if res_opt:
                option_text = res_opt[0]
                
            # 2. Get TextID from gossip_menu -> then NPC Text
            cursor.execute("SELECT TextID FROM gossip_menu WHERE MenuID = %s LIMIT 1", (menu_id,))
            res_menu = cursor.fetchone()
            if res_menu:
                text_id = res_menu[0]
                # 3. Get actual text from npc_text
                # Tables usually have text0_0 and text0_1. We prefer 0_1 (English usually) or 0_0.
                cursor.execute("SELECT text0_0, text0_1 FROM npc_text WHERE ID = %s", (text_id,))
                res_text = cursor.fetchone()
                if res_text:
                    gossip_text = res_text[1] if res_text[1] else res_text[0]
            
            conn.close()
            return gossip_text, option_text
        except:
            return "", ""

    def get_quest_rich_texts(self, quest_id, realm_id=None):
        """
        Fetches RewardText (from quest_offer_reward) and CompletionText (from quest_request_items).
        Returns: {'RewardText': str, 'CompletionText': str}
        """
        res = {'RewardText': '', 'CompletionText': ''}
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            # Offer Reward
            cursor.execute("SELECT RewardText FROM quest_offer_reward WHERE ID = %s", (quest_id,))
            row = cursor.fetchone()
            if row: res['RewardText'] = row[0]
            
            # Request Items
            cursor.execute("SELECT CompletionText FROM quest_request_items WHERE ID = %s", (quest_id,))
            row = cursor.fetchone()
            if row: res['CompletionText'] = row[0]
            
            conn.close()
            return res
        except:
            return res

    def clear_quest_phase_scripts(self, npc_entry, quest_id, realm_id=None):
        """
        Removes SmartAI scripts on this NPC related to PHASING for this QUEST.
        """
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            sql = """DELETE FROM smart_scripts 
                     WHERE entryorguid = %s AND source_type = 0 
                     AND (event_type = 19 OR event_type = 20)
                     AND event_param1 = %s
                     AND action_type = 88"""
                     
            cursor.execute(sql, (npc_entry, quest_id))
            conn.commit()
            conn.close()
            return True
        except mysql.connector.Error as e:
            print(f"Clear SmartAI Error: {e}")
            return False

    def delete_quest_full(self, quest_id, realm_id=None):
        """
        Cascade deletes all data related to a quest ID.
        Returns (success, message).
        """
        queries = [
            # Main Tables
            f"DELETE FROM quest_template WHERE ID = {quest_id}",
            f"DELETE FROM quest_template_addon WHERE ID = {quest_id}",
            f"DELETE FROM quest_offer_reward WHERE ID = {quest_id}",
            f"DELETE FROM quest_request_items WHERE ID = {quest_id}",
            
            # Starters/Enders
            f"DELETE FROM creature_queststarter WHERE quest = {quest_id}",
            f"DELETE FROM creature_questender WHERE quest = {quest_id}",
            f"DELETE FROM gameobject_queststarter WHERE quest = {quest_id}",
            f"DELETE FROM gameobject_questender WHERE quest = {quest_id}",
            
            # Phasing (Spell Area)
            f"DELETE FROM spell_area WHERE quest_start = {quest_id} OR quest_end = {quest_id}",
            
            # Smart Scripts (Phasing - Event 19/20 Param1 = QuestID)
            f"DELETE FROM smart_scripts WHERE source_type=0 AND (event_type=19 OR event_type=20) AND event_param1 = {quest_id}",
            
            # Smart Scripts (Gossip Credit - Action 15 Param1 = QuestID)
            f"DELETE FROM smart_scripts WHERE action_type=15 AND action_param1 = {quest_id}"
        ]
        
        try:
            conn = self.get_connection(realm_id=realm_id)
            cursor = conn.cursor()
            
            for sql in queries:
                cursor.execute(sql)
                
            conn.commit()
            conn.close()
            return True, f"Quest {quest_id} deleted successfully."
        except mysql.connector.Error as e:
            print(f"Delete Quest Error: {e}")
            return False, str(e)
