"""main.py - Application entry point with splash screen"""
import sys, os
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen, QIcon

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundling"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def make_splash():
    px = QPixmap(640, 360); px.fill(QColor("#0d1117"))
    p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)

    # Background gradient
    g = QLinearGradient(0, 0, 640, 360)
    g.setColorAt(0,   QColor("#0d1117"))
    g.setColorAt(0.5, QColor("#161b22"))
    g.setColorAt(1,   QColor("#0d1117"))
    p.fillRect(0, 0, 640, 360, g)

    # Border glow
    p.setPen(QPen(QColor("#1f6feb"), 2));    p.drawRect(1, 1, 638, 358)
    p.setPen(QPen(QColor("#1f6feb44"), 1));  p.drawRect(4, 4, 632, 352)

    # ── Main title: two big lines ────────────────────────────────
    # Line 1: Digital Electronics (Cyan #58a6ff, font size 28, bold)
    p.setFont(QFont("Consolas", 28, QFont.Bold))
    p.setPen(QColor("#58a6ff"))
    p.drawText(0, 22, 640, 55, Qt.AlignCenter, "Digital Electronics")

    # Line 2: Design & Learning Studio (Green #3fb950, font size 22, bold)
    p.setFont(QFont("Consolas", 22, QFont.Bold))
    p.setPen(QColor("#3fb950"))
    p.drawText(0, 78, 640, 50, Qt.AlignCenter, "Design & Learning Studio")

    # Thin divider under title
    p.setPen(QPen(QColor("#30363d"), 1))
    p.drawLine(60, 142, 580, 142)

    # Gate badges
    gates  = ["AND","OR","NOT","NAND","NOR","XOR","XNOR","MUX","ENC","DEC"]
    colors = ["#42a5f5","#ab47bc","#ef5350","#66bb6a","#ffa726",
              "#f06292","#ce93d8","#1e88e5","#00897b","#e57373"]
    for i, (gt, c) in enumerate(zip(gates, colors)):
        x = 13 + i * 62
        p.setPen(QPen(QColor(c), 1)); p.setBrush(QColor(c + "22"))
        p.drawRoundedRect(x, 158, 56, 26, 4, 4)
        p.setFont(QFont("Consolas", 7, QFont.Bold)); p.setPen(QColor(c))
        p.drawText(x, 158, 56, 26, Qt.AlignCenter, gt)

    # Thin divider above loading
    p.setPen(QPen(QColor("#21262d"), 1))
    p.drawLine(60, 206, 580, 206)

    # Loading text
    p.setFont(QFont("Consolas", 10)); p.setPen(QColor("#8b949e"))
    p.drawText(0, 222, 640, 30, Qt.AlignCenter, "Initializing simulation engine...")

    # Version line
    p.setFont(QFont("Consolas", 8)); p.setPen(QColor("#484f58"))
    p.drawText(0, 258, 640, 22, Qt.AlignCenter, "v2.0  •  Python + PyQt5 + EDA Studio")

    # ── Developer credits — bottom corner with clear contrast and proper spacing ──
    devs = [
        "Developed by :",
        "  Nischal N Bangera",
    ]
    p.setFont(QFont("Consolas", 8))
    line_h = 16
    start_y = 360 - len(devs) * line_h - 14
    metrics = p.fontMetrics()
    max_w = max(metrics.horizontalAdvance(line) for line in devs)
    x = 640 - max_w - 20
    for i, line in enumerate(devs):
        p.setPen(QColor("#8b949e" if i == 0 else "#58a6ff"))
        p.setFont(QFont("Consolas", 8, QFont.Bold if i == 1 else QFont.Normal))
        p.drawText(x, start_y + i * line_h, max_w + 10, line_h, Qt.AlignLeft, line)

    p.end()
    return px

def main():
    try:
        import ctypes
        myappid = 'digital.electronics.eda.studio.v2'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Logic Simulator")
    app.setStyle("Fusion")

    # Set Application & Window Icon
    icon_path = get_resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        app_icon = None

    splash = QSplashScreen(make_splash(), Qt.WindowStaysOnTopHint)
    splash.show(); app.processEvents()

    from main_window import MainWindow
    win = MainWindow()
    if app_icon:
        win.setWindowIcon(app_icon)

    def show():
        splash.finish(win); win.show(); win.raise_()
    QTimer.singleShot(2000, show)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()