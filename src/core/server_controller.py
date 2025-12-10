import subprocess
import shutil
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET

class ServerController:
    """
    Controller for interacting with system services and WorldServer via SOAP.
    """
    
    def __init__(self):
        # Check if systemctl exists, otherwise we're likely on a dev machine/different OS
        self.systemctl_path = shutil.which("systemctl")
        self.soap_config = {}

    def set_connection_info(self, soap_port, soap_user, soap_pass):
        """Sets the connection info for SOAP commands."""
        self.soap_config = {
            "port": soap_port,
            "user": soap_user,
            "pass": soap_pass
        }

    def check_service(self, service_name: str) -> bool:
        """
        Checks if a systemd service is active.
        Returns False if systemd is not available or service is inactive.
        """
        if not self.systemctl_path:
            # Fallback for dev environment without systemd
            # Could implement checking for process name in process list if needed
            return False

        try:
            # systemctl is-active returns 0 if active, non-zero otherwise
            # output is 'active' or 'inactive'/'failed' etc.
            result = subprocess.run(
                [self.systemctl_path, "is-active", service_name],
                capture_output=True,
                text=True,
                check=False 
            )
            is_active = result.stdout.strip() == "active"
            print(f"Checking service: '{service_name}' -> Result: {is_active}")
            return is_active
        except Exception as e:
            print(f"Error checking service {service_name}: {e}")
            return False

    def send_soap_command(self, command: str) -> str:
        """
        Sends a SOAP command to the WorldServer.
        """
        port = self.soap_config.get("port", 7878)
        user = self.soap_config.get("user", "")
        password = self.soap_config.get("pass", "")
        host = "127.0.0.1" # Standard access
        
        url = f"http://{host}:{port}/"
        
        # Construct XML Envelope
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="urn:AC">
  <SOAP-ENV:Body>
    <ns1:executeCommand>
      <command>{command}</command>
    </ns1:executeCommand>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8"
        }

        try:
            response = requests.post(
                url, 
                data=soap_body, 
                auth=HTTPBasicAuth(user, password),
                headers=headers,
                timeout=3 # fast fail
            )
            
            if response.status_code == 200 or response.status_code == 500:
                # Parse XML Response (Success or Fault)
                # Namespace handling for ElementTree
                ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns1': 'urn:AC'}
                try:
                    root = ET.fromstring(response.text)
                    
                    # Check for Fault (Common in 500, but checking in 200 too just in case)
                    fault = root.find(".//soap:Fault", ns)
                    if fault:
                        fault_string = fault.find("faultstring")
                        text = fault_string.text if fault_string is not None else 'Unknown Fault'
                        return f"Error: {text.strip()}"
                    
                    # Success Result (Only expected in 200 OK)
                    if response.status_code == 200:
                        result_node = root.find(".//ns1:executeCommandResponse/result", ns)
                        if result_node is not None:
                            return result_node.text.strip() if result_node.text else "Success (No Output)"
                        return "Command Executed (Empty Response)"
                        
                except ET.ParseError:
                    return f"Error: Could not parse SOAP response (Status {response.status_code})"
                
            if response.status_code == 401:
                return "Error: Unauthorized (Check SOAP User/Pass in Settings)"
            
            # Fallback for other codes
            return f"Error: Server returned {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return "Error: Could not connect to WorldServer (Is it online? Check SOAP port)"
        except requests.exceptions.Timeout:
            return "Error: SOAP Connection Timed Out"
        except Exception as e:
            return f"Error: {str(e)}"
