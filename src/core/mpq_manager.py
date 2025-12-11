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

    @classmethod
    def get_instance(cls):
        if not cls._instance:
             cls._instance = MpqManager()
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
        ]
        
        # Scan for Locales (enUS, enGB, etc)
        # They should be higher priority than Base but lower than patches? 
        # Usually: patch-enUS-3.MPQ > locale-enUS.MPQ > ...
        # Let's check subfolders.
        locale_archives = []
        possible_locales = ["enUS", "enGB", "deDE", "frFR", "esES", "ruRU"]
        
        for loc in possible_locales:
            loc_path = os.path.join(data_path, loc)
            if os.path.isdir(loc_path):
                print(f"DEBUG: Found Locale Directory: {loc}")
                # Load locale specific MPQs
                # patch-enUS-3.MPQ
                # patch-enUS-2.MPQ
                # locale-enUS.MPQ
                
                # We prepend to priorities? Or load immediately?
                # Let's load them into a list and prepend to self.archives later?
                # Actually, simpler to just add them to the 'priorities' list if we have full paths?
                # But priorities list assumes root Data folder.
                
                # Better: Load them here and add to self.archives
                loc_files = [
                    f"patch-{loc}-3.MPQ",
                    f"patch-{loc}-2.MPQ",
                    f"locale-{loc}.MPQ"
                ]
                
                for lf in loc_files:
                    full_loc_mpq = os.path.join(loc_path, lf)
                    if os.path.exists(full_loc_mpq):
                        try:
                            archive = mpyq.MPQArchive(full_loc_mpq)
                            self.archives.append(archive) # Append? Or Prepend?
                            # If we append, they are lower priority than what we already loaded?
                            # Wait, we haven't loaded priorities yet.
                            print(f"DEBUG: Loading Locale Archive: {lf}")
                            locale_archives.append(archive)
                        except Exception as e:
                            print(f"Failed to load {lf}: {e}")

        # Add Locale archives to main list (High Priority for now)
        self.archives.extend(locale_archives)
        
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

    def read_file(self, internal_path: str) -> Optional[bytes]:
        """
        Reads a file from the loaded archives.
        Normalizes path separators and tries multiple cases to avoid missing files.
        Returns raw bytes or None.
        """
        if not self.archives:
            print("Warning: No MPQ archives loaded.")
            return None
            
        # Generate permutations to beat the Hash Lookup
        candidates = [
            internal_path,                                      # As requested
            internal_path.replace('/', '\\'),                   # Backslashes (WoW Standard)
            internal_path.replace('\\', '/'),                   # Forward Slashes
            internal_path.lower(),                              # Lowercase
            internal_path.upper(),                              # Uppercase
            internal_path.lower().replace('/', '\\'),           # Lower + Backslash
        ]
        
        for archive in self.archives:
            for candidate in candidates:
                try:
                    # Try to read
                    file_data = archive.read_file(candidate)
                    if file_data:
                        print(f"DEBUG: Found {internal_path} as {candidate} in archive.")
                        return file_data
                except:
                    pass
        
        print(f"DEBUG: Failed to find {internal_path} in any archive.")
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

    def debug_list_files(self, filter_str: str):
        """
        Debug method to print all files matching the filter string.
        """
        print(f"DEBUG: searching MPQs for files matching: '{filter_str}'")
        results = self.search_files(filter_str)
        if results:
            for r in results:
                print(f"MATCH: {r}")
        else:
            print("DEBUG: No matches found.")
