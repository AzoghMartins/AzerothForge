import os
import mpyq
import re
from typing import Optional, List

class MpqManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MpqManager, cls).__new__(cls)
            cls._instance.archives = []
            cls._instance.archive_indexes = []
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
        self.archive_indexes = []
        
        data_path = os.path.join(client_path, "Data")
        if not os.path.exists(data_path):
            print(f"Error: Data folder not found at {data_path}")
            return

        mpq_paths = []
        for root, _dirs, files in os.walk(data_path):
            for filename in files:
                if filename.lower().endswith(".mpq"):
                    mpq_paths.append(os.path.join(root, filename))

        if not mpq_paths:
            print("No MPQ archives found.")
            return

        def mpq_sort_key(path: str):
            base = os.path.basename(path).lower()
            is_patch = 0 if base.startswith("patch") else 1
            locale_bias = 0 if os.path.dirname(path).lower() != data_path.lower() else 1
            nums = [int(n) for n in re.findall(r"(\d+)", base)]
            patch_num = nums[-1] if nums else 0
            return (is_patch, locale_bias, -patch_num, base)

        mpq_paths = sorted(set(mpq_paths), key=mpq_sort_key)

        for full_path in mpq_paths:
            try:
                archive = mpyq.MPQArchive(full_path)
                self.archives.append(archive)
                self.archive_indexes.append(self._build_archive_index(archive))
                print(f"Loaded MPQ: {os.path.relpath(full_path, data_path)}")
            except Exception as e:
                print(f"Failed to load {full_path}: {e}")

    def _normalize_path(self, p: str) -> str:
        return p.replace('/', '\\').lower()

    def _build_archive_index(self, archive) -> dict:
        idx = {}
        files = getattr(archive, 'files', []) or []
        for filename_bytes in files:
            try:
                filename = filename_bytes.decode('utf-8', errors='ignore')
            except Exception:
                continue
            if not filename:
                continue
            idx[self._normalize_path(filename)] = filename
        return idx

    def _candidate_paths(self, internal_path: str) -> List[str]:
        path = internal_path.strip()
        candidates = []
        base = path.replace('/', '\\')
        variants = {
            base,
            base.lower(),
            base.upper(),
            base.replace('\\', '/'),
            base.lower().replace('\\', '/'),
        }
        for v in variants:
            candidates.append(v)
            # M2/MDX fallback in both directions
            if v.lower().endswith('.m2'):
                candidates.append(v[:-3] + '.mdx')
            elif v.lower().endswith('.mdx'):
                candidates.append(v[:-4] + '.m2')
        # keep order, drop dupes
        out = []
        seen = set()
        for c in candidates:
            n = self._normalize_path(c)
            if n in seen:
                continue
            seen.add(n)
            out.append(c)
        return out

    def resolve_file_path(self, internal_path: str) -> Optional[str]:
        """
        Resolves an internal path to the exact indexed path in loaded MPQs.
        """
        if not self.archives:
            return None
        for candidate in self._candidate_paths(internal_path):
            norm = self._normalize_path(candidate)
            for idx in self.archive_indexes:
                if norm in idx:
                    return idx[norm]
        return None

    def read_file(self, internal_path: str) -> Optional[bytes]:
        """
        Reads a file from the loaded archives.
        Normalizes path separators and tries multiple cases to avoid missing files.
        Returns raw bytes or None.
        """
        if not self.archives:
            print("Warning: No MPQ archives loaded.")
            return None

        candidates = self._candidate_paths(internal_path)

        for archive, idx in zip(self.archives, self.archive_indexes):
            for candidate in candidates:
                try:
                    norm = self._normalize_path(candidate)
                    actual = idx.get(norm, candidate)
                    file_data = archive.read_file(actual)
                    if file_data:
                        print(f"DEBUG: Found {internal_path} as {actual} in archive.")
                        return file_data
                except Exception:
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
