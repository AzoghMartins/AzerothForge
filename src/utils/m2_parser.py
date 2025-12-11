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
                
                vertices.append((pos, normal))
                
                current_offset += stride

        if vertices:
             print(f"DEBUG: Parsed {len(vertices)} vertices.")
             print(f"DEBUG: First vertex: {vertices[0]}")
             # Check for NaNs manually?
             import math
             # vertices[0] is now ((x,y,z), (nx,ny,nz))
             pos_check = vertices[0][0]
             if any(math.isnan(c) for c in pos_check):
                 print("DEBUG: First vertex contains NaNs!")
        else:
             print("DEBUG: No vertices extracted.")

        return vertices
