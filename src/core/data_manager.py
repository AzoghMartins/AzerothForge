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
        self.factions = {}
        self.display_infos = {} # Merged ID -> {'model': path, 'texture': skin}
        self.maps = {}
        self.model_data = {} # Raw ModelID -> Path
        
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

        # CreatureModelData.dbc (Dependencies first)
        cmd_path = os.path.join(client_path, "CreatureModelData.dbc")
        if os.path.exists(cmd_path):
            try:
                self.model_data = self.parser.read_creature_model_data_dbc(cmd_path)
                print(f"SUCCESS: Loaded {len(self.model_data)} Model Data entries.")
            except Exception as e:
                print(f"ERROR: Failed to parse CreatureModelData.dbc: {e}")
        else:
             print(f"DEBUG: CreatureModelData.dbc not found at {cmd_path}")

        # CreatureDisplayInfo.dbc
        cdi_path = os.path.join(client_path, "CreatureDisplayInfo.dbc")
        if os.path.exists(cdi_path):
            try:
                raw_display_infos = self.parser.read_display_info_dbc(cdi_path)
                # Merge Logic: DisplayID -> {ModelPath, TexturePath}
                count = 0
                for did, info in raw_display_infos.items():
                    mid = info.get('model_id', 0)
                    skin = info.get('skin1', '')
                    
                    # Lookup model path
                    model_path = self.model_data.get(mid, "")
                    
                    if model_path:
                        # Fix extension: .mdx -> .m2
                        if model_path.lower().endswith('.mdx'):
                            model_path = model_path[:-4] + '.m2'
                        elif model_path.lower().endswith('.mdl'):
                            model_path = model_path[:-4] + '.m2'
                            
                        self.display_infos[did] = {
                            'model': model_path,
                            'texture': skin
                        }
                        count += 1
                        
                print(f"SUCCESS: Loaded and Merged {count} Display Info entries.")
            except Exception as e:
                print(f"ERROR: Failed to parse CreatureDisplayInfo.dbc: {e}")
        else:
            print(f"DEBUG: CreatureDisplayInfo.dbc not found at {cdi_path}")

        # Map.dbc
        map_path = os.path.join(client_path, "Map.dbc")
        if os.path.exists(map_path):
            try:
                self.maps = self.parser.read_map_dbc(map_path)
                print(f"SUCCESS: Loaded {len(self.maps)} Maps.")
            except Exception as e:
                print(f"ERROR: Failed to parse Map.dbc: {e}")
        else:
            print(f"DEBUG: Map.dbc not found at {map_path}")

    def get_map_name(self, map_id):
        return self.maps.get(map_id, f"Unknown Map ({map_id})")

    def search_models(self, query: str, limit=100) -> list:
        """
        Search models by path or ID.
        Returns list of (DisplayID, ModelPath, TexturePath).
        """
        query = query.lower()
        results = []
        for did, info in self.display_infos.items():
            path = info['model']
            tex = info['texture']
            
            if query in path.lower() or query == str(did):
                results.append((did, path, tex))
                if len(results) >= limit:
                    break
        return results
