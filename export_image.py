"""export_image.py - Export circuit canvas to PNG/JPEG"""
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QPainter, QColor

def export_scene(scene, parent=None, fmt="PNG"):
    if not scene.items():
        QMessageBox.information(parent,"Export","Nothing to export."); return
    bounds = scene.itemsBoundingRect().adjusted(-40,-40,40,40)
    w,h = max(int(bounds.width()),100), max(int(bounds.height()),100)
    px = QPixmap(w,h); px.fill(QColor("#0d1117"))
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    scene.render(painter, source=bounds)
    painter.end()
    ext = fmt.lower()
    path, _ = QFileDialog.getSaveFileName(parent, f"Export as {fmt}", f"circuit.{ext}", f"{fmt} (*.{ext})")
    if path:
        if px.save(path, fmt, quality=95):
            QMessageBox.information(parent,"Export",f"Saved: {path}")
        else:
            QMessageBox.warning(parent,"Export Error","Failed to save.")

def export_scene_as_png(scene, parent=None):  export_scene(scene, parent, "PNG")
def export_scene_as_jpeg(scene, parent=None): export_scene(scene, parent, "JPEG")
