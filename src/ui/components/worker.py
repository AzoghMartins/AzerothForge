from PySide6.QtCore import QThread, Signal

class SearchWorker(QThread):
    """
    Generic Worker Thread for executing DB search queries asynchronously.
    """
    results_ready = Signal(list)
    
    def __init__(self, search_func, *args, **kwargs):
        super().__init__()
        self.search_func = search_func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            results = self.search_func(*self.args, **self.kwargs)
            self.results_ready.emit(results)
        except Exception as e:
            print(f"SearchWorker Error: {e}")
            self.results_ready.emit([])
