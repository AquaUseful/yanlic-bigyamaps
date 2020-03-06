from PyQt5 import QtWidgets, uic, QtGui, QtCore
import sys
import requests
import typing
import operator


class YaMapPoint(object):
    def __init__(self, ll: tuple, style: str, color: str, size: int, content: int):
        self.ll = ll
        self.style = style
        self.color = color
        self.size = size
        self.content = content

    def get_string(self):
        return f"{self.ll[0]},{self.ll[1]},{self.style}{self.color}{self.color}{self.content}"


class YaMapSearch(object):
    pass


class YaMapMap(object):
    def __init__(self, ll: tuple, scale: int, layer_comb: int, points: tuple = ()):
        self.server_addr = "http://static-maps.yandex.ru/1.x/"
        self.aval_layers = (("map",), ("sat",), ("sat", "skl"),
                            ("sat", "trf", "skl"), ("map", "trf", "skl"))
        if -90 <= ll[0] <= 90 and -180 <= ll[1] <= 180:
            self.ll = ll
        else:
            raise ValueError()
        if 0 <= scale <= 17:
            self.scale = scale
        else:
            raise ValueError()
        if 0 <= layer_comb < 5:
            self.layer_comb = layer_comb
        else:
            raise ValueError()
        if all(map(lambda point: point is YaMapPoint, points)):
            self.points = points
        else:
            raise TypeError()

    def save_image(self, filename: str, autopos=False):
        ll_str = ",".join(map(str, self.ll))
        l_str = ",".join(self.aval_layers[self.layer_comb])
        pt_str = "~".join(map(lambda point: point.get_string(), self.points))
        req_params = {}
        req_params["l"] = l_str
        if not autopos or not pt_str:
            req_params["ll"] = ll_str
            req_params["z"] = self.scale
        if pt_str:
            req_params["pt"] = pt_str
        response = requests.get(self.server_addr, req_params)
        if not response:
            print(f"Error: {response.status_code} ({response.reason})")
        self.map_file = filename + ".png"
        with open(self.map_file, "wb") as f:
            f.write(response.content)
        return self.map_file

    def get_map_filename(self):
        return self.map_file

    def move_map(self, ll_delta: tuple):
        new_ll = tuple(map(operator.add, self.ll, ll_delta))
        if -90 <= new_ll[0] <= 90 and -180 <= new_ll[1] <= 180:
            self.ll = new_ll

    def zoom_in(self):
        if self.scale < 17:
            self.scale += 1

    def zoom_out(self):
        if self.scale > 0:
            self.scale -= 1

    def cycle_layers(self):
        self.layer_comb = (self.layer_comb + 1) % len(self.aval_layers)

    def get_scale(self):
        return self.scale


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        ll = (37.530887, 55.703118)
        scale = 17
        layer_comb = 0
        self.map = YaMapMap(ll, scale, layer_comb)
        self.initUi()
        self.update_image()

    def initUi(self):
        uic.loadUi("MainWindow.ui", self)
        self.action_exit.triggered.connect(sys.exit)

    def keyPressEvent(self, event):
        upd = False
        key = event.key()
        if key == QtCore.Qt.Key_PageDown:
            self.map.zoom_out()
            upd = True
        elif key == QtCore.Qt.Key_PageUp:
            self.map.zoom_in()
            upd = True
        elif key == QtCore.Qt.Key_Space:
            self.map.cycle_layers()
            upd = True
        elif key == QtCore.Qt.Key_Right:
            delta = (0.01, 0)
            self.map.move_map(delta)
            upd = True
        elif key == QtCore.Qt.Key_Left:
            delta = (-0.01, 0)
            self.map.move_map(delta)
            upd = True
        elif key == QtCore.Qt.Key_Up:
            delta = (0, 0.01)
            self.map.move_map(delta)
            upd = True
        elif key == QtCore.Qt.Key_Down:
            delta = (0, -0.01)
            self.map.move_map(delta)
            upd = True
        if upd:
            self.update_image()

    def update_image(self):
        filename = self.map.save_image("map")
        pixmap = QtGui.QPixmap(filename)
        self.label_map.setPixmap(pixmap)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
