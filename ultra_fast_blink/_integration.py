from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QMessageBox
from ._window import UltraFastBlinkComparator
from ._models import VERSION

def run(ctx):
    """Open a parent-owned tool window without blocking SASpro's event loop."""
    app = ctx.main_window()
    doc_manager = getattr(app, "docman", None)
    if doc_manager is None:
        doc_manager = getattr(app, "doc_manager", None)
    window = UltraFastBlinkComparator(doc_manager=doc_manager, parent=app)
    window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
    window.setWindowFlags(Qt.WindowType.Window)
    credit = QLabel(f'v{VERSION} | Made with love by <a href="https://emerald.show">Emerald</a>', window)
    credit.setOpenExternalLinks(True)
    credit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    layout = window.layout()
    layout.removeWidget(window.run_status)
    status_row = QHBoxLayout()
    status_row.addWidget(window.run_status, 1)
    status_row.addWidget(credit)
    layout.addLayout(status_row)
    send = getattr(app, "_on_blink_send_to_stacking", None)
    if callable(send):
        window.sendToStacking.connect(
            lambda paths, target, w=window: send(paths, target, w)
        )
    else:
        window.sendToStacking.connect(
            lambda *_: QMessageBox.information(
                window, "Stacking unavailable",
                "This SASpro version does not expose the Blink stacking integration."
            )
        )
    window.show()
    ctx.log("Ultra Fast Blink opened. Add FITS/XISF files or a folder, then Score All.")
