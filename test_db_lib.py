import sys
try:
    import mysql.connector
    print("mysql.connector is available.")
    from src.core.config_manager import ConfigManager
    cm = ConfigManager()
    auth = cm.config.get("auth_database", {})
    conn = mysql.connector.connect(
        user=auth.get("user", "acore"),
        password=auth.get("password", "acore"),
        host=auth.get("host", "localhost"),
        port=auth.get("port", 3306)
    )
    print("Database connection successful.")
    conn.close()
except ImportError:
    print("mysql.connector is NOT installed.")
except Exception as e:
    print(f"Connection failed: {e}")
