
import sys
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from style import DARK_STYLE


def run_gui():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()