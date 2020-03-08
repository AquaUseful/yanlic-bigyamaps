from PyQt5 import QtWidgets
from PyQt5 import QtCore


class QLabel_clickable(QtWidgets.QLabel):
    rclicked = QtCore.pyqtSignal(tuple)
    lclicked = QtCore.pyqtSignal(tuple)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lclicked.emit((event.x(), event.y()))
        elif event.button() == QtCore.Qt.RightButton:
            self.rclicked.emit((event.x(), event.y()))
