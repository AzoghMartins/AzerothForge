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
        self.display_infos = {} # Merged ID -> {'model': path, 'texture': skin}
        self.display_extras = {} # Raw ExtraID -> character customization tuple
        self.item_displays = {} # ItemDisplayInfo ID -> visual rows
        self.char_hair_geosets = {} # (race, gender) -> hair geoset mapping
        self.facial_hair_styles = {} # (race, gender) -> facial geoset rows
        self.char_sections = {} # (race, gender, section_type, variation, color) -> texture rows
        self.maps = {}
        self.model_data = {} # Raw ModelID -> Path
        self.quest_sorts = {}
        self.areas = {}
        self.skill_lines = {}
        
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
        cdie_path = os.path.join(client_path, "CreatureDisplayInfoExtra.dbc")

        if os.path.exists(cdie_path):
            try:
                self.display_extras = self.parser.read_display_info_extra_dbc(cdie_path)
                print(f"SUCCESS: Loaded {len(self.display_extras)} Display Info Extra entries.")
            except Exception as e:
                print(f"ERROR: Failed to parse CreatureDisplayInfoExtra.dbc: {e}")
        else:
            print(f"DEBUG: CreatureDisplayInfoExtra.dbc not found at {cdie_path}")

        idi_path = os.path.join(client_path, "ItemDisplayInfo.dbc")
        if os.path.exists(idi_path):
            try:
                self.item_displays = self.parser.read_item_display_info_dbc(idi_path)
                print(f"SUCCESS: Loaded {len(self.item_displays)} Item Display entries.")
            except Exception as e:
                print(f"ERROR: Failed to parse ItemDisplayInfo.dbc: {e}")
        else:
            print(f"DEBUG: ItemDisplayInfo.dbc not found at {idi_path}")

        hair_geo_path = os.path.join(client_path, "CharHairGeosets.dbc")
        if os.path.exists(hair_geo_path):
            try:
                self.char_hair_geosets = self.parser.read_char_hair_geosets_dbc(hair_geo_path)
                print(f"SUCCESS: Loaded CharHairGeosets for {len(self.char_hair_geosets)} race/gender buckets.")
            except Exception as e:
                print(f"ERROR: Failed to parse CharHairGeosets.dbc: {e}")
        else:
            print(f"DEBUG: CharHairGeosets.dbc not found at {hair_geo_path}")

        facial_path = os.path.join(client_path, "CharacterFacialHairStyles.dbc")
        if os.path.exists(facial_path):
            try:
                self.facial_hair_styles = self.parser.read_character_facial_hair_styles_dbc(facial_path)
                print(f"SUCCESS: Loaded CharacterFacialHairStyles for {len(self.facial_hair_styles)} race/gender buckets.")
            except Exception as e:
                print(f"ERROR: Failed to parse CharacterFacialHairStyles.dbc: {e}")
        else:
            print(f"DEBUG: CharacterFacialHairStyles.dbc not found at {facial_path}")

        char_sections_path = os.path.join(client_path, "CharSections.dbc")
        if os.path.exists(char_sections_path):
            try:
                self.char_sections = self.parser.read_char_sections_dbc(char_sections_path)
                print(f"SUCCESS: Loaded {len(self.char_sections)} CharSections entries.")
            except Exception as e:
                print(f"ERROR: Failed to parse CharSections.dbc: {e}")
        else:
            print(f"DEBUG: CharSections.dbc not found at {char_sections_path}")

        if os.path.exists(cdi_path):
            try:
                raw_display_infos = self.parser.read_display_info_dbc(cdi_path)
                # Merge Logic: DisplayID -> {ModelPath, TexturePath}
                count = 0
                for did, info in raw_display_infos.items():
                    mid = info.get('model_id', 0)
                    skin = info.get('skin1', '')
                    extra_id = info.get('extra_id', 0)
                    
                    # Lookup model path
                    model_path = self.model_data.get(mid, "")
                    
                    if model_path:
                        # Fix extension: .mdx -> .m2
                        if model_path.lower().endswith('.mdx'):
                            model_path = model_path[:-4] + '.m2'
                        elif model_path.lower().endswith('.mdl'):
                            model_path = model_path[:-4] + '.m2'

                        # Character models use the bake name from DisplayInfoExtra when available.
                        extra = self.display_extras.get(extra_id, {})
                        if model_path.lower().startswith("character\\"):
                            bake_name = (extra.get("bake_name") or "").strip()
                            if bake_name:
                                skin = f"Textures\\BakedNpcTextures\\{bake_name}"
                            elif not skin and extra_id:
                                skin = f"Textures\\BakedNpcTextures\\CreatureDisplayExtra-{extra_id:05d}"
                            elif not skin:
                                skin = f"Textures\\BakedNpcTextures\\CreatureDisplayExtra-{did:05d}"

                        extra_payload = dict(extra) if extra else {}
                        if extra_payload:
                            race = int(extra_payload.get("race", 0) or 0)
                            gender = int(extra_payload.get("gender", 0) or 0)
                            hair_style = int(extra_payload.get("hair_style", 0) or 0)
                            facial_style = int(extra_payload.get("facial_hair", 0) or 0)
                            race_gender_key = (race, gender)

                            hair_bucket = self.char_hair_geosets.get(race_gender_key) or {}
                            by_variation = hair_bucket.get("by_variation", {})
                            ordered_hair = hair_bucket.get("ordered", [])

                            if hair_style in by_variation:
                                extra_payload["resolved_hair_geoset"] = int(by_variation.get(hair_style, 0) or 0)
                                extra_payload["resolved_hair_source"] = "variation"
                            elif 0 <= hair_style < len(ordered_hair):
                                extra_payload["resolved_hair_geoset"] = int(ordered_hair[hair_style].get("geoset", 0) or 0)
                                extra_payload["resolved_hair_source"] = "row_index"
                            elif ordered_hair:
                                extra_payload["resolved_hair_geoset"] = int(ordered_hair[0].get("geoset", 0) or 0)
                                extra_payload["resolved_hair_source"] = "fallback_first"

                            facial_rows = self.facial_hair_styles.get(race_gender_key) or []
                            if facial_rows:
                                desired_hair_geo = int(extra_payload.get("resolved_hair_geoset", 0) or 0)
                                target_700 = facial_style + 1

                                best = None
                                for idx, candidate in enumerate(facial_rows):
                                    c700 = int(candidate.get("geoset700", 0) or 0)
                                    c300 = int(candidate.get("geoset300", 0) or 0)
                                    c100 = int(candidate.get("geoset100", 0) or 0)
                                    c200 = int(candidate.get("geoset200", 0) or 0)
                                    score = 0

                                    if c700 == target_700:
                                        score += 30
                                    elif c700 == facial_style:
                                        score += 20

                                    if c300 == desired_hair_geo:
                                        score += 10
                                    elif abs(c300 - desired_hair_geo) == 1:
                                        score += 4

                                    if int(candidate.get("variation", -1)) == facial_style:
                                        score += 6

                                    # Prefer baseline face/chin geosets when ties happen.
                                    score -= (c100 + c200)

                                    rank = (score, -idx)
                                    if best is None or rank > best[0]:
                                        best = (rank, candidate, idx)

                                row = best[1] if best else facial_rows[0]
                                source = "score_match"
                                extra_payload["resolved_facial_geosets"] = {
                                    "source": source,
                                    "row_id": int(row.get("id", 0) or 0),
                                    "variation": int(row.get("variation", 0) or 0),
                                    "geoset100": int(row.get("geoset100", 0) or 0),
                                    "geoset200": int(row.get("geoset200", 0) or 0),
                                    "geoset300": int(row.get("geoset300", 0) or 0),
                                    "geoset700": int(row.get("geoset700", 0) or 0),
                                }

                            # SectionType 3 is hairstyle textures.
                            hair_textures = self._resolve_char_section_textures(
                                race=race,
                                gender=gender,
                                section_type=3,
                                variation=hair_style,
                                color=int(extra_payload.get("hair_color", 0) or 0),
                            )
                            if hair_textures:
                                extra_payload["resolved_hair_textures"] = hair_textures

                            # SectionType 2 carries facial hair / brow texture atlases for many races.
                            facial_textures = self._resolve_char_section_textures(
                                race=race,
                                gender=gender,
                                section_type=2,
                                variation=facial_style,
                                color=int(extra_payload.get("hair_color", 0) or 0),
                            )
                            if facial_textures:
                                extra_payload["resolved_facial_textures"] = facial_textures

                        if extra_payload.get("npc_item_displays"):
                            item_details = []
                            for slot, disp_id in enumerate(extra_payload.get("npc_item_displays", []), start=1):
                                d_id = int(disp_id or 0)
                                detail = self.item_displays.get(d_id, {})
                                item_details.append({
                                    "slot": slot,
                                    "display_id": d_id,
                                    "model_1": detail.get("model_1", ""),
                                    "model_2": detail.get("model_2", ""),
                                    "model_texture_1": detail.get("model_texture_1", ""),
                                    "model_texture_2": detail.get("model_texture_2", ""),
                                    "geoset_group_1": detail.get("geoset_group_1", 0),
                                    "geoset_group_2": detail.get("geoset_group_2", 0),
                                    "geoset_group_3": detail.get("geoset_group_3", 0),
                                    "textures": detail.get("textures", []),
                                })
                            extra_payload["npc_item_details"] = item_details
                            
                        self.display_infos[did] = {
                            'model': model_path,
                            'texture': skin,
                            'extra_id': extra_id,
                            'extra': extra_payload
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

        # QuestSort.dbc
        qs_path = os.path.join(client_path, "QuestSort.dbc")
        if os.path.exists(qs_path):
            try:
                self.quest_sorts = self.parser.read_quest_sort_dbc(qs_path)
                print(f"SUCCESS: Loaded {len(self.quest_sorts)} Quest Sorts.")
            except Exception as e:
                print(f"ERROR: Failed to parse QuestSort.dbc: {e}")
        else:
            print(f"DEBUG: QuestSort.dbc not found at {qs_path}")

        # AreaTable.dbc
        area_path = os.path.join(client_path, "AreaTable.dbc")
        if os.path.exists(area_path):
            try:
                self.areas = self.parser.read_area_table_dbc(area_path)
                print(f"SUCCESS: Loaded {len(self.areas)} Areas.")
            except Exception as e:
                print(f"ERROR: Failed to parse AreaTable.dbc: {e}")
        else:
            print(f"DEBUG: AreaTable.dbc not found at {area_path}")

        # SkillLine.dbc
        skill_path = os.path.join(client_path, "SkillLine.dbc")
        if os.path.exists(skill_path):
            try:
                self.skill_lines = self.parser.read_skillline_dbc(skill_path)
                print(f"SUCCESS: Loaded {len(self.skill_lines)} Skill Lines.")
            except Exception as e:
                print(f"ERROR: Failed to parse SkillLine.dbc: {e}")
        else:
            print(f"DEBUG: SkillLine.dbc not found at {skill_path}")

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

    def search_skill_lines(self, query: str, limit=100) -> list:
        """
        Search skill lines by name or ID.
        Returns list of (id, name).
        """
        query = query.lower()
        results = []
        for sid, name in self.skill_lines.items():
            if query in name.lower() or query == str(sid):
                results.append((sid, name))
                if len(results) >= limit:
                    break
        return results

    def _resolve_char_section_textures(self, race, gender, section_type, variation, color):
        candidates = [
            (race, gender, section_type, variation, color),
            (race, gender, section_type, variation + 1, color),
        ]
        for key in candidates:
            row = self.char_sections.get(key)
            if row and row.get("textures"):
                return list(row.get("textures"))
        return []
