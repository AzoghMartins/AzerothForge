import struct

class BlpConverter:
    def process_blp(self, blp_data: bytes):
        """
        Parses BLP2 data and returns (width, height, image_data, format_format).
        Returns None if invalid.
        """
        if not blp_data or len(blp_data) < 20:
            print("Invalid BLP data length.")
            return None

        # Header
        magic = blp_data[0:4]
        if magic != b'BLP2':
            print(f"Invalid BLP Magic: {magic}")
            return None

        _type = struct.unpack('<I', blp_data[4:8])[0]
        # Type 1: Compressed (DXT), Type 2: Uncompressed/Paletted (usually Paletted 8-bit)
        
        compression = struct.unpack('<B', blp_data[8:9])[0] 
        alpha_depth = struct.unpack('<B', blp_data[9:10])[0]
        alpha_type = struct.unpack('<B', blp_data[10:11])[0]
        has_mips = struct.unpack('<B', blp_data[11:12])[0]
        
        width = struct.unpack('<I', blp_data[12:16])[0]
        height = struct.unpack('<I', blp_data[16:20])[0]
        
        # Mipmap offsets (16 * 4 bytes)
        mip_offsets = struct.unpack('<16I', blp_data[20:84])
        # Mipmap sizes (16 * 4 bytes)
        mip_sizes = struct.unpack('<16I', blp_data[84:148])
        
        # We only care about Mip #0
        mip0_offset = mip_offsets[0]
        mip0_size = mip_sizes[0]
        
        if mip0_offset == 0 or mip0_size == 0:
            print("No Mipmap 0 found.")
            return None
            
        # BLP2 decoding depends on `compression` field, not `_type`.
        # compression: 1=palette, 2=DXT, 3=raw BGRA.
        if compression == 2:
            dxt_format = "DXT1"
            if alpha_depth >= 8:
                dxt_format = "DXT5" if alpha_type in (7, 8) else "DXT3"
            elif alpha_depth in (1, 4):
                dxt_format = "DXT3"

            # Correct obviously mismatched headers using block-size math.
            block_count = ((width + 3) // 4) * ((height + 3) // 4)
            expected_dxt1 = block_count * 8
            expected_dxt3_5 = block_count * 16

            if dxt_format == "DXT1" and mip0_size == expected_dxt3_5:
                dxt_format = "DXT5" if alpha_type in (7, 8) else "DXT3"
                print(
                    "BLP header mismatch: promoted DXT1 -> "
                    f"{dxt_format} based on mip size ({mip0_size})."
                )
            elif dxt_format in ("DXT3", "DXT5") and mip0_size == expected_dxt1:
                dxt_format = "DXT1"
                print(
                    "BLP header mismatch: demoted to DXT1 based on mip size "
                    f"({mip0_size})."
                )

            raw_data = blp_data[mip0_offset : mip0_offset + mip0_size]
            return (width, height, raw_data, dxt_format)

        if compression == 1:
            # Paletted 8-bit (indices + optional packed alpha stream).
            palette_offset = 148
            palette_bytes = blp_data[palette_offset : palette_offset + 1024]
            if len(palette_bytes) < 1024:
                print("Invalid BLP palette data.")
                return None

            palette = []
            for i in range(256):
                b = palette_bytes[i * 4 + 0]
                g = palette_bytes[i * 4 + 1]
                r = palette_bytes[i * 4 + 2]
                a = palette_bytes[i * 4 + 3]
                palette.append((r, g, b, a))

            pixel_count = width * height
            mip_blob = blp_data[mip0_offset : mip0_offset + mip0_size]
            indices = mip_blob[:pixel_count]
            if len(indices) < pixel_count:
                print("Invalid paletted mip index data.")
                return None
            alpha_blob = mip_blob[pixel_count:]

            def alpha_at(i, palette_alpha):
                if alpha_depth == 0:
                    # Most 0-bit alpha textures should be fully opaque.
                    return 255
                if alpha_depth == 1:
                    byte_idx = i // 8
                    if byte_idx >= len(alpha_blob):
                        return 255
                    bit = (alpha_blob[byte_idx] >> (i % 8)) & 0x1
                    return 255 if bit else 0
                if alpha_depth == 4:
                    byte_idx = i // 2
                    if byte_idx >= len(alpha_blob):
                        return 255
                    nibble = (alpha_blob[byte_idx] >> (4 * (i % 2))) & 0xF
                    return nibble * 17
                if alpha_depth == 8:
                    if i >= len(alpha_blob):
                        return 255
                    return alpha_blob[i]
                return palette_alpha

            rgba_data = bytearray(pixel_count * 4)
            out = 0
            for i, index in enumerate(indices):
                r, g, b, pa = palette[index]
                a = alpha_at(i, pa)
                rgba_data[out + 0] = r
                rgba_data[out + 1] = g
                rgba_data[out + 2] = b
                rgba_data[out + 3] = a
                out += 4

            return (width, height, bytes(rgba_data), "RGBA")

        if compression == 3:
            # Uncompressed BGRA.
            pixel_count = width * height
            raw = blp_data[mip0_offset : mip0_offset + (pixel_count * 4)]
            if len(raw) < pixel_count * 4:
                print("Invalid BGRA mip data.")
                return None
            rgba_data = bytearray(pixel_count * 4)
            for i in range(pixel_count):
                b = raw[i * 4 + 0]
                g = raw[i * 4 + 1]
                r = raw[i * 4 + 2]
                a = raw[i * 4 + 3]
                rgba_data[i * 4 + 0] = r
                rgba_data[i * 4 + 1] = g
                rgba_data[i * 4 + 2] = b
                rgba_data[i * 4 + 3] = a
            return (width, height, bytes(rgba_data), "RGBA")

        print(
            "Unsupported BLP compression: "
            f"{compression} (type={_type}, alpha_depth={alpha_depth}, alpha_type={alpha_type})"
        )
        return None
