from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QTextEdit, QPushButton, QGroupBox, QComboBox)
from PySide6.QtCore import Qt, QTimer
from src.core.server_controller import ServerController
from src.core.config_manager import ConfigManager
from src.core.metrics_engine import MetricsEngine
from src.ui.settings_window import SettingsWindow

class DashboardWidget(QWidget):
    def __init__(self, config_manager: ConfigManager = None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager if config_manager else ConfigManager()
        self.controller = ServerController()
        self.metrics = MetricsEngine(self.config_manager)
        
        self.init_ui()
        
        # Load initial realm data
        self.update_controller_config()
        
        # Setup Timer for Service Checks
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_services)
        self.refresh_timer.start(5000) # Check every 5 seconds
        
        # Initial check
        self.check_services()

    def init_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Top Section: Server Status
        status_group = QGroupBox("Server Status")
        status_layout = QHBoxLayout()
        
        self.auth_indicator = self.create_traffic_light("red")
        self.world_indicator = self.create_traffic_light("red")
        
        status_layout.addWidget(QLabel("Auth Server:"))
        status_layout.addWidget(self.auth_indicator)
        status_layout.addSpacing(20)
        status_layout.addWidget(QLabel("World Server:"))
        status_layout.addWidget(self.world_indicator)
        status_layout.addStretch()
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Middle Section: Metrics
        metrics_group = QGroupBox("Live Metrics")
        metrics_layout = QHBoxLayout()
        
        self.uptime_label = QLabel("Uptime: -")
        self.accounts_label = QLabel("Active Accts: 0")
        self.players_label = QLabel("Online Humans: 0")
        self.bots_label = QLabel("Online Bots: 0")
        self.bots_label.setStyleSheet("color: #aaa;") # Grey out initially
        self.bots_label.setVisible(False) # Hide by default
        
        metrics_layout.addWidget(self.uptime_label)
        metrics_layout.addSpacing(20)
        metrics_layout.addWidget(self.accounts_label)
        metrics_layout.addSpacing(20)
        metrics_layout.addWidget(self.players_label)
        metrics_layout.addSpacing(20)
        metrics_layout.addWidget(self.bots_label)
        metrics_layout.addStretch()
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        # Bottom Section: Log Stream
        log_group = QGroupBox("Log Stream")
        log_layout = QVBoxLayout()
        self.log_stream = QTextEdit()
        self.log_stream.setReadOnly(True)
        self.log_stream.setPlaceholderText("Connecting to server.log...")
        # Monospace font for logs
        self.log_stream.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace;")
        log_layout.addWidget(self.log_stream)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Buttons
        button_layout = QHBoxLayout()
        self.restart_btn = QPushButton("Restart World")
        self.restart_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f; 
                color: white; 
                font-weight: bold; 
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.restart_btn.clicked.connect(self.on_restart_clicked)
        self.shutdown_btn = QPushButton("Shutdown")
        
        button_layout.addWidget(self.restart_btn)
        button_layout.addWidget(self.shutdown_btn)
        layout.addLayout(button_layout)

    def create_traffic_light(self, color):
        frame = QFrame()
        frame.setFixedSize(20, 20)
        self.set_traffic_light_color(frame, color)
        return frame

    def set_traffic_light_color(self, frame, color):
        # Green for on, Red for off
        color_code = "#4caf50" if color == "green" else "#f44336"
        frame.setStyleSheet(f"background-color: {color_code}; border-radius: 10px; border: 1px solid #333;")

    # Removed refresh_realm_selector, open_settings. 
    # Settings now handled by MainWindow.

    def on_realm_changed(self):
        # Update controller and check services
        self.update_controller_config()
        self.check_services()

    def update_controller_config(self):
        realm = self.config_manager.get_active_realm()
        # Update controller credentials
        self.controller.set_connection_info(
            realm.get("soap_port", 7878),
            realm.get("soap_user", ""),
            realm.get("soap_pass", "")
        )

    def check_services(self):
        # Get active realm info
        realm = self.config_manager.get_active_realm()
        world_service = realm.get("service_name", "azerothcore-world")

        # Check Auth Server
        auth_service_name = self.config_manager.config.get("auth_service_name", "authserver")
        auth_active = self.controller.check_service(auth_service_name)
        self.set_traffic_light_color(self.auth_indicator, "green" if auth_active else "red")
        
        # Check World Server (Dynamic based on realm)
        world_active = self.controller.check_service(world_service)
        self.set_traffic_light_color(self.world_indicator, "green" if world_active else "red")
        
        # --- Update Metrics ---
        if world_active: # Only fetch metrics if world is running
            uptime = self.metrics.get_uptime()
            self.uptime_label.setText(f"Uptime: {uptime}")
            
            stats = self.metrics.get_population_stats()
            self.accounts_label.setText(f"Active Accts: {stats.get('accounts', 0)}")
            self.players_label.setText(f"Online Humans: {stats.get('humans', 0)}")
            
            if realm.get("playerbots_enabled", False):
                self.bots_label.setVisible(True)
                self.bots_label.setText(f"Online Bots: {stats.get('bots', 0)}")
                
                # Highlight if bots > humans?
                humans = stats.get('humans', 0)
                bots = stats.get('bots', 0)
                if bots > humans and humans > 0:
                     self.bots_label.setStyleSheet("color: #ff9800;") # Orange warning
                else:
                     self.bots_label.setStyleSheet("color: #aaa;")
            else:
                self.bots_label.setVisible(False)
        else:
            self.uptime_label.setText("Uptime: Offline")
            self.accounts_label.setText("Active Accts: -")
            self.players_label.setText("Online Humans: -")
            self.bots_label.setVisible(False)

    # Removed open_settings as it is in MainWindow now

    def on_config_saved(self):
        # MainWindow handles refresh but if we receive this signal directly
        # or if we just want to update without index change
        self.update_controller_config()
        self.check_services()
        self.log_stream.append("[System] Configuration reloaded.")

    def on_restart_clicked(self):
        response = self.controller.send_soap_command(".server info")
        self.log_stream.append(f"[CMD] Restart requested. Response: {response}")
