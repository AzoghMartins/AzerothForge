from construct import Struct, Int32ul, Const, Bytes, Array, this, Adapter
import os

class DBCParser:
    """
    Parser for World of Warcraft (3.3.5a) DBC files.
    """
    
    # Generic Header
    Header = Struct(
        "magic" / Const(b"WDBC"),
        "record_count" / Int32ul,
        "field_count" / Int32ul,
        "record_size" / Int32ul,
        "string_block_size" / Int32ul
    )

    def _parse_file(self, file_path):
        if not os.path.exists(file_path):
            print(f"DBC file not found: {file_path}")
            return None, None, None

        with open(file_path, "rb") as f:
            data = f.read()

        header = self.Header.parse(data)
        
        # Calculate offsets
        header_size = self.Header.sizeof()
        records_data_size = header.record_count * header.record_size
        
        records_raw = data[header_size : header_size + records_data_size]
        string_block = data[header_size + records_data_size :]
        
        return header, records_raw, string_block

    def _get_string(self, offset, string_block):
        if offset < 0 or offset >= len(string_block):
            return ""
        
        # Find null terminator
        end = string_block.find(b'\x00', offset)
        if end == -1:
            return string_block[offset:].decode('utf-8', errors='replace')
        return string_block[offset:end].decode('utf-8', errors='replace')

    def _clean_geoset_value(self, value):
        # Some DBC rows carry 0xCCCCCCCC placeholders; treat them as disabled.
        v = int(value or 0)
        if v > 1000:
            return 0
        return v

    def read_faction_dbc(self, file_path) -> dict:
        """
        Reads Faction.dbc and returns {id: name}.
        Assumes Field 0 = ID, Field 23 = Name Offset.
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        # Define Record Structure dynamically based on expectations
        # Or just use the generic strategy of parsing integers manually if structure varies?
        # User constraint: "Map the fields for 3.3.5a Faction.dbc (ID is index 0, Name is index 23 [string ref])."
        # Since we know record_size and field_count, we can parse strictly.
        # But wait, 3.3.5a Faction.dbc usually has ~64 fields.
        # Construct is powerful but defining a struct with 64 Int32ul is tedious if we only need 2.
        # Better approach: Read as Array of Int32ul (since most DBC fields are 4-byte ints/floats/refs).
        
        # Let's verify field_count matches what we expect or just rely on offsets.
        # Standard DBC is all 4-byte fields usually.
        
        # Safe strategy: Array(header.field_count, Int32ul)
        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)
        
        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing records in {file_path}: {e}")
            return {}

        results = {}
        for row in parsed_records:
            if len(row) > 23:
                f_id = row[0]
                name_offset = row[23]
                name = self._get_string(name_offset, string_block)
                results[f_id] = name
                
        return results

        return results

    def read_creature_model_data_dbc(self, file_path) -> dict:
        """
        Reads CreatureModelData.dbc.
        Returns {model_id: model_path_string}.
        ModelID = Field 0.
        ModelPath = Field 2 (string ref).
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}
            
        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)
        
        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}
            
        results = {}
        for row in parsed_records:
            if len(row) > 2:
                m_id = row[0]
                path_offset = row[2]
                path = self._get_string(path_offset, string_block)
                if path:
                    results[m_id] = path
        return results

    def read_display_info_dbc(self, file_path) -> dict:
        """
        Reads CreatureDisplayInfo.dbc.
        Returns {id: {'model_id': int, 'skin1': str, 'extra_id': int}}.
        WotLK (3.3.5a) relevant fields:
        - ID = 0
        - ModelID = 1
        - ExtendedDisplayInfoID = 3 (character models)
        - TextureVariation1/2/3 = 6/7/8 (string refs)
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)
        
        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing records in {file_path}: {e}")
            return {}

        results = {}
        for row in parsed_records:
            if len(row) > 8:
                c_id = row[0]
                model_id = row[1]
                # Prefer first non-empty texture variation.
                skin1 = ""
                for idx in (6, 7, 8):
                    off = row[idx]
                    val = self._get_string(off, string_block)
                    if val:
                        skin1 = val
                        break
                
                results[c_id] = {
                    'model_id': model_id,
                    'skin1': skin1,
                    'extra_id': row[3]
                }
                
        return results

    def read_display_info_extra_dbc(self, file_path) -> dict:
        """
        Reads CreatureDisplayInfoExtra.dbc.
        Returns {id: {...}} with appearance + equipment + bake name.
        Field mapping is for 3.3.5a.
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)

        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

        results = {}
        for row in parsed_records:
            if len(row) < 8:
                continue
            extra_id = row[0]
            results[extra_id] = {
                'race': row[1],
                'gender': row[2],
                'skin': row[3],
                'face': row[4],
                'hair_style': row[5],
                'hair_color': row[6],
                'facial_hair': row[7],
                'npc_item_displays': [
                    row[8], row[9], row[10], row[11], row[12], row[13],
                    row[14], row[15], row[16], row[17], row[18]
                ],
                'flags': row[19],
                'bake_name': self._get_string(row[20], string_block)
            }
        return results

    def read_item_display_info_dbc(self, file_path) -> dict:
        """
        Reads ItemDisplayInfo.dbc.
        Returns {id: {...}} with model names, texture names, geoset groups and visuals.
        Field mapping follows 3.3.5a layout used by itemdisplayinfo_dbc table.
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)

        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

        results = {}
        for row in parsed_records:
            if len(row) < 25:
                continue
            did = row[0]
            results[did] = {
                "model_1": self._get_string(row[1], string_block),
                "model_2": self._get_string(row[2], string_block),
                "model_texture_1": self._get_string(row[3], string_block),
                "model_texture_2": self._get_string(row[4], string_block),
                "geoset_group_1": row[7],
                "geoset_group_2": row[8],
                "geoset_group_3": row[9],
                "flags": row[10],
                "item_visual": row[23],
                "textures": [
                    self._get_string(row[15], string_block),
                    self._get_string(row[16], string_block),
                    self._get_string(row[17], string_block),
                    self._get_string(row[18], string_block),
                    self._get_string(row[19], string_block),
                    self._get_string(row[20], string_block),
                    self._get_string(row[21], string_block),
                    self._get_string(row[22], string_block),
                ],
            }
        return results

    def read_char_hair_geosets_dbc(self, file_path) -> dict:
        """
        Reads CharHairGeosets.dbc.
        Returns {(race, gender): {"ordered": [...], "by_variation": {...}}}.
        """
        header, records_raw, _string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)

        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

        out = {}
        for row in parsed_records:
            if len(row) < 5:
                continue
            race = int(row[1])
            gender = int(row[2])
            variation = int(row[3])
            geoset = self._clean_geoset_value(row[4])
            key = (race, gender)
            bucket = out.setdefault(key, {"ordered": [], "by_variation": {}})
            entry = {
                "id": int(row[0]),
                "variation": variation,
                "geoset": geoset,
            }
            bucket["ordered"].append(entry)
            if variation not in bucket["by_variation"]:
                bucket["by_variation"][variation] = geoset
        return out

    def read_character_facial_hair_styles_dbc(self, file_path) -> dict:
        """
        Reads CharacterFacialHairStyles.dbc.
        Returns {(race, gender): [row_in_file_order, ...]}.
        """
        header, records_raw, _string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)

        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

        out = {}
        for row in parsed_records:
            if len(row) < 8:
                continue
            # Field order in 3.3.5a: ID, SexID, RaceID, VariationID, Geoset100..400
            gender = int(row[1])
            race = int(row[2])
            key = (race, gender)
            out.setdefault(key, []).append({
                "id": int(row[0]),
                "variation": int(row[3]),
                "geoset100": self._clean_geoset_value(row[4]),
                "geoset200": self._clean_geoset_value(row[5]),
                "geoset300": self._clean_geoset_value(row[6]),
                "geoset700": self._clean_geoset_value(row[7]),
            })
        return out

    def read_char_sections_dbc(self, file_path) -> dict:
        """
        Reads CharSections.dbc.
        Returns {(race, gender, section_type, variation, color): {...}}.
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)

        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

        out = {}
        for row in parsed_records:
            if len(row) < 10:
                continue

            race = int(row[1])
            gender = int(row[2])
            section_type = int(row[3])
            variation = int(row[8])
            color = int(row[9])
            key = (race, gender, section_type, variation, color)

            textures = []
            for col in (4, 5, 6):
                tex = self._get_string(int(row[col]), string_block)
                if tex:
                    textures.append(tex)

            out[key] = {
                "id": int(row[0]),
                "flags": int(row[7]),
                "textures": textures,
            }
        return out

    def read_map_dbc(self, file_path) -> dict:
        """
        Reads Map.dbc and returns {id: name}.
        Assumes Field 0 = ID, Field 5 = MapName_Lang Offset (enUS).
        Fallback to Field 1 (Directory) if needed.
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)
        
        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing records in {file_path}: {e}")
            return {}

        results = {}
        for row in parsed_records:
            if len(row) > 5:
                m_id = row[0]
                name_offset = row[5] # MapName_Lang
                name = self._get_string(name_offset, string_block)
                if not name and len(row) > 1:
                    # Fallback to Directory
                    dir_offset = row[1]
                    name = self._get_string(dir_offset, string_block)
                
                results[m_id] = name
                
        return results

    def read_quest_sort_dbc(self, file_path) -> dict:
        """
        Reads QuestSort.dbc.
        Returns {id: name}.
        Field 0 = ID, Field 1 = Name_Lang (Offset).
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}
            
        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)
        
        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}
            
        results = {}
        for row in parsed_records:
            if len(row) > 1:
                qs_id = row[0]
                name_offset = row[1]
                name = self._get_string(name_offset, string_block)
                if name:
                    results[qs_id] = name
        return results

    def read_area_table_dbc(self, file_path) -> dict:
        """
        Reads AreaTable.dbc.
        Returns {id: name}.
        Field 0 = ID.
        Field 11 = AreaName_Lang (Offset) (for 3.3.5a).
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}
            
        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)
        
        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}
            
        results = {}
        for row in parsed_records:
            if len(row) > 11:
                area_id = row[0]
                name_offset = row[11]
                name = self._get_string(name_offset, string_block)
                if name:
                    results[area_id] = name
        return results

    def read_skillline_dbc(self, file_path) -> dict:
        """
        Reads SkillLine.dbc.
        Returns {id: name}.
        Field 0 = ID.
        Field 3 = DisplayName_Lang (Offset) for 3.3.5a.
        """
        header, records_raw, string_block = self._parse_file(file_path)
        if not header:
            return {}

        Record = Array(header.field_count, Int32ul)
        Records = Array(header.record_count, Record)

        try:
            parsed_records = Records.parse(records_raw)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {}

        results = {}
        for row in parsed_records:
            if len(row) > 3:
                skill_id = row[0]
                name_offset = row[3]
                name = self._get_string(name_offset, string_block)
                if name:
                    results[skill_id] = name
        return results
