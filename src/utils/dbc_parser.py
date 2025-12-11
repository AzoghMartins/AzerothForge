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
        Returns {id: {'model_id': int, 'skin1': str}}.
        ID = 0, ModelID = 1, Skin1 = 2 (string ref).
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
            if len(row) > 2:
                c_id = row[0]
                model_id = row[1]
                skin_offset = row[2]
                skin1 = self._get_string(skin_offset, string_block)
                
                results[c_id] = {
                    'model_id': model_id,
                    'skin1': skin1
                }
                
        return results

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
