import os
import mpyq
from typing import Optional, List

class MpqManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MpqManager, cls).__new__(cls)
            cls._instance.archives = []
            cls._instance.client_path = None
        return cls._instance

    def initialize(self, client_path: str):
        """
        Initializes the MPQ Manager with the WoW client path.
        Loads archives in priority order:
        patch-3.MPQ -> patch-2.MPQ -> patch.MPQ -> lichking.MPQ -> expansion.MPQ -> common.MPQ
        """
        if self.client_path == client_path:
            return # Already initialized
            
        self.client_path = client_path
        self.archives = []
        
        data_path = os.path.join(client_path, "Data")
        if not os.path.exists(data_path):
            print(f"Error: Data folder not found at {data_path}")
            return

        # Priority List (Highest to Lowest)
        # Note: Actual priority in client is determined by alphanumeric sorting of patch-*.MPQ usually, 
        # but hardcoding known WotLK structure is fine for this task.
        priorities = [
            "patch-3.MPQ",
            "patch-2.MPQ",
            "patch.MPQ",
            "lichking.MPQ",
            "expansion.MPQ",
            "common.MPQ"
            # Locales (enUS/enGB) archives would be next, but ignoring for now as M2s are usually in common/exp
        ]
        
        # Load archives
        for filename in priorities:
            chk_path = os.path.join(data_path, filename)
            if os.path.exists(chk_path):
                try:
                    archive = mpyq.MPQArchive(chk_path)
                    self.archives.append(archive)
                    print(f"Loaded MPQ: {filename}")
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")
            else:
                # Also check common/ patches which might be loose? 
                # WotLK structure is usually Data/common.MPQ etc.
                pass
                
        # Also check for alphanumeric patches 'patch-*.MPQ' that we missed?
        # Keeping it simple as per Task 1 reqs.

    def read_file(self, internal_path: str) -> Optional[bytes]:
        """
        Reads a file from the loaded archives.
        Normalizes path separators to backslashes (WoW standard).
        Returns raw bytes or None.
        """
        if not self.archives:
            print("Warning: No MPQ archives loaded.")
            return None
            
        # Try variations of the path (Case sensitivity handling)
        # WoW MPQs usually use backslash.
        base_path = internal_path.replace("/", "\\")
        
        candidates = [
            base_path,              # As provided
            base_path.upper(),      # All caps (COMMON)
            base_path.lower(),      # All lower
            base_path.capitalize()  # First cap
        ]
        
        for archive in self.archives:
            # Check if archive has a list of files we can check against?
            # mpyq 'files' attribute is a list of bytes usually.
            
            for candidate in candidates:
                try:
                    # Try to read
                    file_data = archive.read_file(candidate)
                    if file_data:
                        print(f"Found {candidate} in archive.")
                        return file_data
                except:
                    pass
                    
            # Fallback: Iterate all files in archive to find case-insensitive match?
            # This is slow but might be necessary if listfile has weird casing.
            # Only do this if specific lookups failed? 
            # For performance, maybe skip this for now.
                
        print(f"Failed to find {internal_path} in any archive.")
        return None

    def search_files(self, pattern: str) -> List[str]:
        """
        Searches all loaded archives for files matching the pattern (case-insensitive substring).
        Returns a list of matching filenames.
        """
        results = set()
        pattern = pattern.lower()
        
        for archive in self.archives:
            # mpyq archive.files is a list of bytes
            if not hasattr(archive, 'files') or not archive.files:
                continue
                
            for filename_bytes in archive.files:
                try:
                    filename = filename_bytes.decode('utf-8')
                    if pattern in filename.lower():
                        results.add(filename)
                except UnicodeDecodeError:
                    continue
                    
        return sorted(list(results))
