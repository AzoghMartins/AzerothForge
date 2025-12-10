import subprocess
import shutil
import platform
from typing import List

def scan_for_services(keywords: List[str] = ['world', 'auth', 'azeroth', 'acore']) -> List[str]:
    """
    Scans for systemd services matching the given keywords.
    Returns a list of service names.
    """
    # Windows Fallback
    if platform.system() == "Windows" or not shutil.which("systemctl"):
        return ['windows-service-simulation', 'acore-auth-sim', 'acore-world-sim']

    found_services = []
    try:
        # List all services
        cmd = ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return []

        # Parse output line by line
        # Format usually: UNIT LOAD ACTIVE SUB DESCRIPTION
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
                
            parts = line.split()
            if not parts:
                continue
                
            service_name = parts[0]
            
            # Check keywords logic
            # Case insensitive check
            if any(k.lower() in service_name.lower() for k in keywords):
                found_services.append(service_name)
                
    except Exception as e:
        print(f"Error scanning services: {e}")
        return []
        
    return sorted(list(set(found_services)))
