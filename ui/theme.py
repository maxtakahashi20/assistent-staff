"""Color palettes and Qt style sheets."""

DARK_QSS = """
QWidget { background: #0d111b; color: #e8ecf5; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background: #0d111b; }
QFrame#Sidebar { background: #101725; border-right: 1px solid #202b3d; }
QFrame#Topbar { background: #111a29; border-bottom: 1px solid #202b3d; }
QLabel#Brand { color: #f4f7ff; font-size: 15pt; font-weight: 700; }
QLabel#Muted { color: #8b98ad; }
QLabel#PageTitle { color: #f4f7ff; font-size: 19pt; font-weight: 700; }
QLabel#SectionTitle { color: #dfe7f5; font-size: 12pt; font-weight: 650; }
QFrame#Card, QFrame#Panel { background: #151f30; border: 1px solid #26334a; border-radius: 12px; }
QLabel#Metric { color: #f4f7ff; font-size: 24pt; font-weight: 700; }
QLabel#MetricLabel { color: #93a1b8; font-size: 9pt; }
QPushButton { background: #202c40; color: #e8ecf5; border: 1px solid #2d3d57; border-radius: 8px; padding: 8px 13px; }
QPushButton:hover { background: #293953; border-color: #536e9e; }
QPushButton:pressed { background: #182438; }
QPushButton#Primary { background: #5268df; border: 1px solid #6479ed; color: white; font-weight: 600; }
QPushButton#Primary:hover { background: #6378ee; }
QPushButton#Nav { text-align: left; padding: 11px 14px; background: transparent; border: 0; color: #9eabc1; }
QPushButton#Nav:hover { background: #1b2940; color: #f4f7ff; }
QPushButton#Nav:checked { background: #26365b; color: #ffffff; border-left: 3px solid #7185ff; }
QLineEdit, QComboBox, QSpinBox, QTextEdit { background: #0f1725; color: #e8ecf5; border: 1px solid #2d3b51; border-radius: 7px; padding: 8px; selection-background-color: #5268df; }
QComboBox::drop-down { border: 0; width: 25px; }
QCheckBox { spacing: 9px; color: #cbd5e5; }
QCheckBox::indicator { width: 17px; height: 17px; }
QTableWidget { background: #111a29; alternate-background-color: #151f30; border: 1px solid #26334a; border-radius: 9px; gridline-color: #26334a; selection-background-color: #283b66; selection-color: #ffffff; }
QHeaderView::section { background: #172337; color: #98a8c0; border: 0; border-bottom: 1px solid #2a3950; padding: 10px; font-weight: 650; }
QTableWidget::item { padding: 7px; border-bottom: 1px solid #202b3d; }
QScrollBar:vertical { background: #101725; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #34435d; min-height: 25px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QStatusBar { background: #101725; color: #8b98ad; border-top: 1px solid #202b3d; }
QMessageBox, QDialog { background: #111a29; }
"""

LIGHT_QSS = """
QWidget { background: #f3f6fb; color: #202a3a; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background: #f3f6fb; }
QFrame#Sidebar { background: #ffffff; border-right: 1px solid #dfe5ef; }
QFrame#Topbar { background: #ffffff; border-bottom: 1px solid #dfe5ef; }
QLabel#Brand, QLabel#PageTitle { color: #182338; font-weight: 700; }
QLabel#Brand { font-size: 15pt; } QLabel#PageTitle { font-size: 19pt; }
QLabel#Muted, QLabel#MetricLabel { color: #748199; }
QLabel#SectionTitle { color: #26334a; font-size: 12pt; font-weight: 650; }
QFrame#Card, QFrame#Panel { background: #ffffff; border: 1px solid #dfe5ef; border-radius: 12px; }
QLabel#Metric { color: #182338; font-size: 24pt; font-weight: 700; }
QPushButton { background: #edf1f8; color: #26334a; border: 1px solid #d7dfeb; border-radius: 8px; padding: 8px 13px; }
QPushButton:hover { background: #e2e9f5; }
QPushButton#Primary { background: #5268df; border: 1px solid #5268df; color: white; font-weight: 600; }
QPushButton#Nav { text-align: left; padding: 11px 14px; background: transparent; border: 0; color: #66748c; }
QPushButton#Nav:checked { background: #edf0ff; color: #354dbf; border-left: 3px solid #5268df; }
QLineEdit, QComboBox, QSpinBox, QTextEdit { background: #ffffff; color: #202a3a; border: 1px solid #d7dfeb; border-radius: 7px; padding: 8px; }
QTableWidget { background: #ffffff; alternate-background-color: #f6f8fc; border: 1px solid #dfe5ef; border-radius: 9px; gridline-color: #e5eaf2; selection-background-color: #e3eaff; selection-color: #202a3a; }
QHeaderView::section { background: #edf1f8; color: #66748c; border: 0; padding: 10px; font-weight: 650; }
QTableWidget::item { padding: 7px; border-bottom: 1px solid #edf1f8; }
QStatusBar { background: #ffffff; color: #748199; }
"""
