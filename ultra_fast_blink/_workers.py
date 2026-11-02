from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import threading
from PyQt6.QtCore import QThread, pyqtSignal
from ._analysis import measure_file, make_preview

class ScanThread(QThread):
    measured = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, paths, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.cancel = threading.Event()

    def run(self):
        try:
            # At most two jobs in flight, including reads; no unbounded future queue.
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix='ultra-blink') as pool:
                paths = iter(self.paths)
                pending = set()
                for _ in range(2):
                    if (path := next(paths, None)) is not None and not self.cancel.is_set():
                        pending.add(pool.submit(measure_file, path))
                while pending:
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        self.measured.emit(future.result())
                        if not self.cancel.is_set() and (path := next(paths, None)) is not None:
                            pending.add(pool.submit(measure_file, path))
        except Exception as exc:
            self.failed.emit(str(exc))


class PreviewThread(QThread):
    ready = pyqtSignal(str, object, str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.ready.emit(self.path, make_preview(self.path), '')
        except Exception as exc:
            self.ready.emit(self.path, None, str(exc))
