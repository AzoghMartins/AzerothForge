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
            
        if _type == 1:
            # Compressed (DXT)
            # Logic:
            # AlphaDepth 0 -> DXT1
            # AlphaDepth 1 or 8 (usually with AlphaType 1/7) -> DXT3/5
            
            dxt_format = "DXT1" # Default
            
            if alpha_depth > 0:
                if alpha_type == 7: # Interpolated Alpha
                    dxt_format = "DXT5"
                else:
                    dxt_format = "DXT3" # Explicit Alpha or AlphaDepth=1
            else:
                 dxt_format = "DXT1"

            # Check alpha bit depth vs compression
            # DXT1 = 0 alpha
            # DXT3 = 4 bit explicit alpha (AlphaDepth 1 or 4?)
            # DXT5 = interpolated alpha (AlphaDepth 8)
            
            # If we detect mismatch, we might need to trust AlphaType more?
            # but let's stick to this logic for now.
            
            raw_data = blp_data[mip0_offset : mip0_offset + mip0_size]
            return (width, height, raw_data, dxt_format)

        elif _type == 2:
            # Paletted (Uncompressed 8-bit indices + Palette)
            # Palette is at 148 (immediately after header blocks)
            # Palette size = 256 * 4 bytes = 1024 bytes
            palette_offset = 148
            palette_bytes = blp_data[palette_offset : palette_offset + 1024]
            
            # Parse Palette -> List of (r, g, b, a) or similar
            # BLP palette is usually BGRA (Blue, Green, Red, Alpha)
            palette = []
            for i in range(256):
                 b = palette_bytes[i*4 + 0]
                 g = palette_bytes[i*4 + 1]
                 r = palette_bytes[i*4 + 2]
                 a = palette_bytes[i*4 + 3]
                 palette.append((r, g, b, a))
                 
            # Pixel indices are at mip0_offset
            indices = blp_data[mip0_offset : mip0_offset + mip0_size]
            
            # Construct RGBA
            rgba_data = bytearray()
            for index in indices:
                r, g, b, a = palette[index]
                rgba_data.append(r)
                rgba_data.append(g)
                rgba_data.append(b)
                rgba_data.append(a)
                
            return (width, height, bytes(rgba_data), "RGBA")
            
        else:
            print(f"Unsupported BLP Type: {_type}")
            return None
