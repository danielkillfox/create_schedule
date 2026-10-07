# style.py
"""Стили оформления. Вынесено из main.py для чистоты."""

DARK_STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #e6e6e6;
    font-size: 13px;
}
QLabel { background: transparent; }
QPushButton {
    background-color: #3d3d3d;
    color: #e6e6e6;
    border: 1px solid #5a5a5a;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover { background-color: #4c4c4c; }
QPushButton:pressed { background-color: #5e5e5e; }
QSpinBox, QTableWidget, QTextEdit, QComboBox, QLineEdit {
    background-color: #1e1e1e;
    color: #e6e6e6;
    border: 1px solid #5a5a5a;
    padding: 4px;
}
QTableWidget { gridline-color: #4a4a4a; }
QTableWidget::item:selected { background-color: #3a5a8a; }
QHeaderView::section {
    background-color: #3d3d3d;
    color: #e6e6e6;
    border: 1px solid #5a5a5a;
}
QTextEdit { font-family: Consolas, monospace; }
QProgressBar { border: none; text-align: center; background: #333; color: white; }
QProgressBar::chunk { background: #4caf50; }
QTabWidget::pane { border: 1px solid #5a5a5a; }
QTabBar::tab {
    background: #3d3d3d; color: #e6e6e6; padding: 6px 12px;
    border: 1px solid #5a5a5a; border-bottom: none;
}
QTabBar::tab:selected { background: #4c4c4c; }
QGroupBox {
    border: 1px solid #5a5a5a;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QComboBox QAbstractItemView {
    background: #1e1e1e;
    selection-background-color: #3a5a8a;
}
"""