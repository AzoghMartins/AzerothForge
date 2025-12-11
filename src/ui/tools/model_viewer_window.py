from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLineEdit, QPushButton, QHBoxLayout, QListWidget
from src.ui.components.model_viewer import Panda3DWidget

class ModelViewerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WoW Model Viewer (Native)")
        self.resize(800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Controls
        controls = QWidget()
        c_layout = QVBoxLayout(controls)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Enter M2 Path or Search Term")
        self.path_input.setText("Creature\\LichKing\\LichKing.m2")
        
        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Load Model")
        self.load_btn.clicked.connect(self.load_model)
        
        self.search_btn = QPushButton("Search Inside MPQ")
        self.search_btn.clicked.connect(self.search_mpq)
        
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.search_btn)
        
        c_layout.addWidget(self.path_input)
        c_layout.addLayout(btn_layout)
        
        # Search Results
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(150)
        self.result_list.itemDoubleClicked.connect(self.on_result_clicked)
        self.result_list.setVisible(False) # Hide initially
        c_layout.addWidget(self.result_list)
        
        layout.addWidget(controls)
        
        # Viewer
        # Check if Panda is available
        try:
            import panda3d.core
            self.viewer = Panda3DWidget()
            layout.addWidget(self.viewer, 1) # Stretch
        except ImportError:
            self.viewer = None
            layout.addWidget(QPushButton("Panda3D not installed. Cannot view models."))

    def load_model(self):
        if self.viewer:
            path = self.path_input.text()
            self.viewer.load_model(path)

    def search_mpq(self):
        from src.core.mpq_manager import MpqManager
        term = self.path_input.text()
        if not term:
            return
            
        # Ensure MPQ is init (via viewer or manually)
        # Viewer inits MPQ on load... we might need to trigger init if not loaded.
        # But MpqManager is singleton. 
        mpq = MpqManager()
        if not mpq.archives:
             # Try forcing init via viewer logic or getting config
             from src.core.config_manager import ConfigManager
             cm = ConfigManager()
             path = cm.config.get("wow_client_path")
             if path:
                 mpq.initialize(path)
        
        results = mpq.search_files(term)
        self.result_list.clear()
        if results:
            self.result_list.setVisible(True)
            for r in results:
                self.result_list.addItem(r)
        else:
            self.result_list.setVisible(True)
            self.result_list.addItem("No results found.")

    def on_result_clicked(self, item):
        self.path_input.setText(item.text())
        self.load_model()

    def closeEvent(self, event):
        if self.viewer:
            self.viewer.cleanup()
            self.viewer.close() # Ensure widget close event fires too
        super().closeEvent(event)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    
    # Mock Config for MPQ (Quick Hack for testing if run directly)
    # Ideally should run via main app
    win = ModelViewerWindow()
    win.show()
    app.exec()
