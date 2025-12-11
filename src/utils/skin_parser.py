import struct

class SkinParser:
    def parse_skin(self, skin_bytes: bytes):
        """
        Parses .skin file to extract Indices and Triangles.
        Returns:
            indices: List[int] (Lookup table: Skin Vertex Index -> M2 Vertex Index)
            triangles: List[int] (List of vertex indices into the 'indices' list defining triangles)
        """
        if not skin_bytes or len(skin_bytes) < 0x20:
            return None, None

        # Header Parsing
        # 0x00: Magic (SKIN)
        # 0x04: nIndices
        # 0x08: ofsIndices
        # 0x0C: nTriangles
        # 0x10: ofsTriangles
        
        magic = skin_bytes[0:4]
        if magic != b'SKIN':
             print(f"Invalid Skin Magic: {magic}")
             return None, None
             
        n_indices = struct.unpack('<I', skin_bytes[0x04:0x08])[0]
        ofs_indices = struct.unpack('<I', skin_bytes[0x08:0x0C])[0]
        
        n_triangles = struct.unpack('<I', skin_bytes[0x0C:0x10])[0]
        ofs_triangles = struct.unpack('<I', skin_bytes[0x10:0x14])[0]
        
        # Read Indices (Lookup Table)
        # Array of uint16
        indices = []
        if n_indices > 0:
            count = n_indices
            start = ofs_indices
            end = start + (count * 2)
            if end <= len(skin_bytes):
                indices = list(struct.unpack(f'<{count}H', skin_bytes[start:end]))
            else:
                print("Skin Indices truncated.")
                
        # Read Triangles (Indices into the Lookup Table)
        # Array of uint16
        # Usually nTriangles is the number of triangle INDICES (so 3 * actual triangles), or number of triangles?
        # WoWDev says "nTriangles: number of triangle indices". So it's divisible by 3.
        triangles = []
        if n_triangles > 0:
            count = n_triangles
            start = ofs_triangles
            end = start + (count * 2)
            if end <= len(skin_bytes):
                triangles = list(struct.unpack(f'<{count}H', skin_bytes[start:end]))
            else:
                print("Skin Triangles truncated.")
                
        return indices, triangles
