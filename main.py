import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.core.data_manager import DataManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("AzerothForge")
    
    # Initialize Data Manager (Start loading in bg ideally, but main thread ok for now)
    DataManager()
    
    window = MainWindow()
    window.show()
    
    print("AzerothForge initialized...")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
