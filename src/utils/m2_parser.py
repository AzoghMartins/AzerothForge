import struct

class M2Parser:
    def __init__(self):
        pass

    def parse_geometry(self, m2_bytes: bytes):
        """
        Parses the binary M2 data to extract geometry (vertices).
        Returns a list of (x, y, z) tuples.
        """
        if not m2_bytes or len(m2_bytes) < 0x50:
            return []

        # 1. Parse Header
        # MD20 signature
        magic = m2_bytes[0:4]
        if magic != b'MD20':
            print(f"Invalid M2 Magic: {magic}")
            return []

        # Version
        version = struct.unpack('<I', m2_bytes[4:8])[0]
        # 264 is WotLK. 
        
        # Offsets for Vertices
        # n_vertices: uint32 at 0x3C
        # ofs_vertices: uint32 at 0x40
        n_vertices = struct.unpack('<I', m2_bytes[0x3C:0x40])[0]
        ofs_vertices = struct.unpack('<I', m2_bytes[0x40:0x44])[0]

        # 2. Parse Vertices
        vertices = []
        if n_vertices > 0 and ofs_vertices > 0:
            # Struct format for a vertex (48 bytes for WotLK)
            # pos (3f), bone_weights (4B), bone_indices (4B), normal (3f), tex_coords (2f), unknown (2f - wait, lets check standard)
            # Standard WotLK M2 Vertex (48 bytes):
            # float x, y, z;
            # uint8 weights[4];
            # uint8 bones[4];
            # float nx, ny, nz;
            # float u, v;
            # float u2, v2; (Sometimes? No, standard is usually just 1 set of UVs + padding or 2 sets)
            # Let's verify size: 3*4 + 4 + 4 + 3*4 + 2*4 = 12 + 8 + 12 + 8 = 40 bytes?
            # Wait, docs say 48 bytes usually?
            # Let's stick to the user's prompt: "Format per vertex (48 bytes): pos_x, pos_y, pos_z (3 floats), weights (4 bytes), indices (4 bytes), normal (3 floats), tex_coords (2 floats)."
            # 12 + 4 + 4 + 12 + 8 = 40 bytes.
            # User said 48 bytes. There must be padding or extra UVs.
            # Assuming user prompt "Format per vertex (48 bytes)" implies the *stride* is 48.
            # I will read the first 3 floats and skip the rest of the 48 bytes.
            
            stride = 48
            current_offset = ofs_vertices
            
            for _ in range(n_vertices):
                if current_offset + 12 > len(m2_bytes):
                    break
                    
                # Read pos (x, y, z)
                # WoW Coordinates: X=North, Y=West, Z=Up.
                # Panda3D: X=Right, Y=Forward, Z=Up. 
                # Usually need conversion: Panda X = -WoW Y, Panda Y = WoW X, Panda Z = WoW Z.
                # But for now let's just read raw.
                
                # Read pos (x, y, z) at offset 0
                pos = struct.unpack('<3f', m2_bytes[current_offset : current_offset + 12])
                
                # Read normal (nx, ny, nz) at offset 20 (12 pos + 4 weights + 4 indices)
                normal = struct.unpack('<3f', m2_bytes[current_offset + 20 : current_offset + 32])
                
                # Read texture coordinates (u, v) at offset 32 (20 normal + 12 ??) -> Normal is 12 bytes. 20+12 = 32.
                # Vertex Structure:
                # 0x00: Pos (12)
                # 0x0C: Weights (4)
                # 0x10: Indices (4)
                # 0x14: Normal (12) -> ends at 0x20 (32)
                # 0x20: TexCoords (8) -> 2 floats
                
                uv = struct.unpack('<2f', m2_bytes[current_offset + 32 : current_offset + 40])
                
                vertices.append((pos, normal, uv))
                
                current_offset += stride

        if vertices:
             print(f"DEBUG: Parsed {len(vertices)} vertices.")
             print(f"DEBUG: First vertex: {vertices[0]}")
             # Check for NaNs manually?
             import math
             # vertices[0] is now ((x,y,z), (nx,ny,nz), (u,v))
             pos_check = vertices[0][0]
             if any(math.isnan(c) for c in pos_check):
                 print("DEBUG: First vertex contains NaNs!")
        else:
             print("DEBUG: No vertices extracted.")

        return vertices

    def parse_textures(self, m2_bytes: bytes):
        """
        Parses texture definitions from M2.
        Returns the first valid Hardcoded (Type 0) Texture filename found.
        """
        if not m2_bytes or len(m2_bytes) < 0x60:
            return None
            
        # Header Offsets (WotLK)
        # n_textures: uint32 at 0x54
        # ofs_textures: uint32 at 0x58
        n_textures = struct.unpack('<I', m2_bytes[0x54:0x58])[0]
        ofs_textures = struct.unpack('<I', m2_bytes[0x58:0x5C])[0]
        
        if n_textures == 0 or ofs_textures == 0:
            return None
            
        current_offset = ofs_textures
        stride = 16 # Texture definition block size
        
        for _ in range(n_textures):
            if current_offset + 16 > len(m2_bytes):
                break
                
            # Read Texture Def
            tex_type = struct.unpack('<I', m2_bytes[current_offset:current_offset+4])[0]
            tex_flags = struct.unpack('<I', m2_bytes[current_offset+4:current_offset+8])[0]
            len_filename = struct.unpack('<I', m2_bytes[current_offset+8:current_offset+12])[0]
            ofs_filename = struct.unpack('<I', m2_bytes[current_offset+12:current_offset+16])[0]
            
            # Type 0 = Hardcoded texture
            if tex_type == 0 and len_filename > 1 and ofs_filename > 0:
                # Read Filename
                try:
                    # Strings in M2 are NOT necessarily null-terminated in the block, 
                    # but 'len_filename' includes null terminator usually? Or just length.
                    # We read len_filename bytes.
                    if raw_name:
                        # Try decoding cleanly, fallback to ascii/replace
                        name = raw_name.decode('utf-8', errors='ignore').split('\x00')[0]
                        if name:
                            return name
                except Exception as e:
                    pass # Silently ignore bad strings to avoid spam
            
            current_offset += stride
            
        return None

    def get_internal_texture_list(self, m2_bytes: bytes) -> list:
        """
        Scans the binary for any string ending in .blp.
        This is a 'dirty' method to find textures when standard parsing fails.
        """
        import re
        results = []
        # Regex for valid filenames ending in .blp
        # Looking for sequence of word chars, slashes, etc.
        pattern = rb'[\w\\/]+\.blp'
        matches = re.findall(pattern, m2_bytes, re.IGNORECASE)
        
        for m in matches:
            try:
                name = m.decode('utf-8')
                results.append(name)
            except:
                pass
                
        # Deduplicate
        return list(set(results))
