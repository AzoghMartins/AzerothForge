import json
import os
import uuid
from datetime import datetime
from datetime import datetime
from typing import List, Dict, Optional
from src.core.id_manager import IdManager

class CampaignManager:
    DATA_FILE = "campaigns.json"
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.campaigns = self.load_campaigns()
        self.active_campaign_id = None

    def load_campaigns(self) -> List[Dict]:
        if not os.path.exists(self.DATA_FILE):
            return []
        try:
            with open(self.DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save_campaigns(self):
        try:
            with open(self.DATA_FILE, 'w') as f:
                json.dump(self.campaigns, f, indent=4)
        except IOError as e:
            print(f"Error saving campaigns: {e}")

    def create_campaign(self, name: str, start_id: int, gm_char: str, dev_realm_id: int, target_realm_id: int = None) -> Dict:
        """
        Creates a new campaign with a dedicated ID range.
        Range size is defaulted to 1000 for now.
        """
        campaign_id = str(uuid.uuid4())
        
        # Define ranges
        # Current starts at start_id.
        end_id = start_id + 999
        
        new_campaign = {
            "id": campaign_id,
            "name": name,
            "gm_character": gm_char,
            "dev_realm_id": dev_realm_id,
            "target_realm_id": target_realm_id,
            "ranges": {
                "creature": {"start": start_id, "current": start_id, "end": end_id},
                "quest": {"start": start_id, "current": start_id, "end": end_id},
                "item": {"start": start_id, "current": start_id, "end": end_id}
            },
            "content": {
                "npcs": [],
                "items": [],
                "quests": []
            },
            "created_at": datetime.now().isoformat()
        }
        
        self.campaigns.append(new_campaign)
        self.save_campaigns()
        return new_campaign

    def get_active_campaign(self) -> Optional[Dict]:
        if not self.active_campaign_id:
            return None
        return next((c for c in self.campaigns if c["id"] == self.active_campaign_id), None)

    def set_active_campaign(self, campaign_id: str):
        self.active_campaign_id = campaign_id

    def get_campaigns(self) -> List[Dict]:
        return self.campaigns

    def get_reserved_ranges(self) -> List[tuple]:
        """Returns a list of (start, end) tuples for all campaigns."""
        ranges = []
        for c in self.campaigns:
            # We assume creature range is representative of the block
            # Since all types share the same block currently
            cr_range = c["ranges"]["creature"]
            ranges.append((cr_range["start"], cr_range["end"]))
        return ranges

    def delete_campaign(self, campaign_id: str):
        self.campaigns = [c for c in self.campaigns if c["id"] != campaign_id]
        if self.active_campaign_id == campaign_id:
            self.active_campaign_id = None
        self.save_campaigns()

    def suggest_next_id_block(self, check_realm_ids: List[int] = []) -> int:
        if not self.config_manager:
            return 50000
        
        # Gather realms from IDs
        realms = []
        all_realms = self.config_manager.get_realms()
        
        if not check_realm_ids:
            # Fallback to active if nothing provided
            realms.append(self.config_manager.get_active_realm())
        else:
            for rid in check_realm_ids:
                r = next((x for x in all_realms if x["id"] == rid), None)
                if r and r not in realms:
                    realms.append(r)
        
        excluded = self.get_reserved_ranges()
        id_manager = IdManager(self.config_manager)
        return id_manager.find_next_campaign_block(excluded_ranges=excluded, target_realms=realms)

    def validate_id_block(self, start_id: int, block_size: int = 1000, check_realm_ids: List[int] = []) -> bool:
        """
        Validates if a block is safe to use.
        Checks both reserved ranges (other campaigns) and DB data.
        """
        # 1. Check Reservsations
        end_id = start_id + block_size - 1
        for r_start, r_end in self.get_reserved_ranges():
            # Check for overlap
            # Overlap if (StartA <= EndB) and (EndA >= StartB)
            if (start_id <= r_end) and (end_id >= r_start):
                return False

        # 2. Check Database
        if not self.config_manager:
            return True # Cannot validate DB
            
        # Gather realms
        realms = []
        all_realms = self.config_manager.get_realms()
        
        if not check_realm_ids:
            realms.append(self.config_manager.get_active_realm())
        else:
            for rid in check_realm_ids:
                r = next((x for x in all_realms if x["id"] == rid), None)
                if r and r not in realms:
                    realms.append(r)
            
        id_manager = IdManager(self.config_manager)
        return id_manager.is_block_free(start_id, block_size, target_realms=realms)

    def get_first_available_id(self, campaign_id: str, type_key: str) -> Optional[int]:
        """
        Connects to the campaign's Dev Realm DB and finds the first unused ID 
        within the campaign's reserved range.
        table items: creature_template, item_template, quest_template
        """
        import mysql.connector
        
        campaign = next((c for c in self.campaigns if c["id"] == campaign_id), None)
        if not campaign:
            return None
            
        ranges = campaign.get("ranges", {})
        if type_key not in ranges:
            return None
            
        type_range = ranges[type_key]
        start_id = type_range["start"]
        end_id = type_range["end"]
        
        # Determine table name
        table_map = {
            "creature": "creature_template",
            "item": "item_template",
            "quest": "quest_template"
        }
        table_name = table_map.get(type_key)
        if not table_name:
            return None
            
        # Connect to DB
        dev_realm_id = campaign.get("dev_realm_id")
        if not dev_realm_id or not self.config_manager:
            return type_range["current"] # Fallback
            
        realms = self.config_manager.get_realms()
        realm_config = next((r for r in realms if r["id"] == dev_realm_id), None)
        if not realm_config:
            return type_range["current"]
            
        auth = self.config_manager.config.get("auth_database", {})
        
        try:
            conn = mysql.connector.connect(
                host=auth.get("host", "localhost"),
                port=auth.get("port", 3306),
                user=auth.get("user", "acore"),
                password=auth.get("password", "acore"),
                database=realm_config.get("db_world_name", "acore_world")
            )
            cursor = conn.cursor()
            
            # Get all IDs in range
            col_name = "entry" if type_key in ["creature", "item"] else "ID"
            if type_key == "quest": col_name = "ID" 
            # Wait, quests usually use `ID` or `entry`? In ACore `quest_template`.`ID`.
            # Let's verify standard AC schema.
            # creature_template -> entry
            # item_template -> entry
            # quest_template -> ID
            
            query = f"SELECT `{col_name}` FROM `{table_name}` WHERE `{col_name}` BETWEEN %s AND %s ORDER BY `{col_name}` ASC"
            cursor.execute(query, (start_id, end_id))
            rows = cursor.fetchall()
            used_ids = {row[0] for row in rows}
            conn.close()
            
            # Find first gap
            for candidate in range(start_id, end_id + 1):
                if candidate not in used_ids:
                    return candidate
                    
            return None # Full
            
        except ImportError:
            return type_range["current"]
        except mysql.connector.Error as e:
            print(f"DB Error finding ID: {e}")
            return type_range["current"]

    def get_next_id(self, type_key: str) -> Optional[int]:
         # Deprecated/Fallback wrapper if needed, or remove?
         # Keeping simpler logic for internal state if DB fails
         pass

    def register_content(self, campaign_id: str, content_type: str, entry_id: int):
        """
        Registers a created content ID to the campaign.
        content_type: 'npcs', 'items', 'quests'
        """
        campaign = next((c for c in self.campaigns if c["id"] == campaign_id), None)
        if not campaign:
            return
            
        if "content" not in campaign:
            campaign["content"] = {"npcs": [], "items": [], "quests": []}
            
        if content_type in campaign["content"]:
            if entry_id not in campaign["content"][content_type]:
                campaign["content"][content_type].append(entry_id)
                self.save_campaigns()
