import struct

class SkinParser:
    def parse_skin(self, skin_bytes: bytes):
        """
        Parses .skin file to extract Indices and Triangles.
        Returns:
            indices: List[int] (Lookup table: Skin Vertex Index -> M2 Vertex Index)
            triangles: List[int] (List of vertex indices into the 'indices' list defining triangles)
            submeshes: List[dict] (id + triangle range metadata)
        """
        if not skin_bytes or len(skin_bytes) < 0x20:
            return None, None, None

        # Header Parsing
        # 0x00: Magic (SKIN)
        # 0x04: nIndices
        # 0x08: ofsIndices
        # 0x0C: nTriangles
        # 0x10: ofsTriangles
        
        magic = skin_bytes[0:4]
        if magic != b'SKIN':
             print(f"Invalid Skin Magic: {magic}")
             return None, None, None
             
        n_indices = struct.unpack('<I', skin_bytes[0x04:0x08])[0]
        ofs_indices = struct.unpack('<I', skin_bytes[0x08:0x0C])[0]
        
        n_triangles = struct.unpack('<I', skin_bytes[0x0C:0x10])[0]
        ofs_triangles = struct.unpack('<I', skin_bytes[0x10:0x14])[0]
        n_submeshes = struct.unpack('<I', skin_bytes[0x1C:0x20])[0]
        ofs_submeshes = struct.unpack('<I', skin_bytes[0x20:0x24])[0]
        
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

        # Read Submeshes (for geoset-aware rendering of character models)
        submeshes = []
        if n_submeshes > 0:
            stride = 48
            for i in range(n_submeshes):
                start = ofs_submeshes + (i * stride)
                end = start + stride
                if end > len(skin_bytes):
                    break
                # Only first 6 uint16 are needed for ID + triangle range.
                sub_id, _level, _v_start, _v_count, tri_start, tri_count = struct.unpack(
                    '<6H', skin_bytes[start:start + 12]
                )
                submeshes.append({
                    'id': sub_id,
                    'triangle_start': tri_start,
                    'triangle_count': tri_count
                })

        return indices, triangles, submeshes

    def parse_texture_units(self, skin_bytes: bytes):
        """
        Parses skin texture-unit table.
        Returns list of {'submesh_index': int, 'texture_index': int, 'render_flags_index': int}.
        """
        if not skin_bytes or len(skin_bytes) < 0x2C:
            return []
        if skin_bytes[0:4] != b'SKIN':
            return []

        n_tex_units = struct.unpack('<I', skin_bytes[0x24:0x28])[0]
        ofs_tex_units = struct.unpack('<I', skin_bytes[0x28:0x2C])[0]
        if n_tex_units == 0 or ofs_tex_units == 0:
            return []

        units = []
        stride = 24
        for i in range(n_tex_units):
            start = ofs_tex_units + (i * stride)
            end = start + stride
            if end > len(skin_bytes):
                break
            vals = struct.unpack('<12H', skin_bytes[start:end])
            units.append({
                "submesh_index": int(vals[2]),
                "texture_index": int(vals[8]),
                "render_flags_index": int(vals[5]),
            })
        return units
