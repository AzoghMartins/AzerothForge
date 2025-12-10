import os
from src.core.config_manager import ConfigManager
from src.utils.dbc_parser import DBCParser

class DataManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return
        self.initialized = True
        
        self.config_manager = ConfigManager()
        self.parser = DBCParser()
        
        self.factions = {}
        self.display_infos = {}
        
        # Load immediately or wait?
        # User says "Method load_data()... Check client_data_path... If valid parse..."
        # So we can call load_data explicitly or here.
        # Let's call it here but wrap in try/catch or just be safe.
        self.load_data()

    def load_data(self):
        # Reload config to ensure we have the latest paths from disk
        self.config_manager.config = self.config_manager.load_config()

        client_path = self.config_manager.config.get("client_data_path", "")
        if not client_path or not os.path.isdir(client_path):
            print(f"DEBUG: Client data path not set or invalid ({client_path}). Skipping DBC load.")
            return

        print(f"DEBUG: Attempting to load DBCs from: {client_path}")
        
        # Faction.dbc
        faction_path = os.path.join(client_path, "Faction.dbc")
        if os.path.exists(faction_path):
            try:
                self.factions = self.parser.read_faction_dbc(faction_path)
                print(f"SUCCESS: Loaded {len(self.factions)} Factions.")
            except Exception as e:
                print(f"ERROR: Failed to parse Faction.dbc: {e}")
        else:
            print(f"DEBUG: Faction.dbc not found at {faction_path}")

        # CreatureDisplayInfo.dbc
        cdi_path = os.path.join(client_path, "CreatureDisplayInfo.dbc")
        if os.path.exists(cdi_path):
            try:
                self.display_infos = self.parser.read_display_info_dbc(cdi_path)
                print(f"SUCCESS: Loaded {len(self.display_infos)} Models.")
            except Exception as e:
                print(f"ERROR: Failed to parse CreatureDisplayInfo.dbc: {e}")
        else:
            print(f"DEBUG: CreatureDisplayInfo.dbc not found at {cdi_path}")
