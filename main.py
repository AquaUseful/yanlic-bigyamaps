from PyQt5 import QtWidgets, uic, QtGui, QtCore
import sys
import requests
import typing
import operator


def scale_to_spn(scale: int, image_size: tuple):
    lon = (360 / 2 ** scale) * (image_size[0] / 256)
    lat = (180 / 2 ** scale) * (image_size[1] / 256)
    return (lon, lat)


class YaMapPoint(object):
    def __init__(self, ll: tuple, style: str, color: str = "", size: int = "", content: int = ""):
        self.ll = ll
        self.style = style
        self.color = color
        self.size = size
        self.content = content

    def get_string(self):
        return f"{self.ll[0]},{self.ll[1]},{self.style}{self.color}{self.size}{self.content}"


class YaMapSearch(object):
    def __init__(self):
        self.server_addr = "https://geocode-maps.yandex.ru/1.x/"
        self.apikey = "40d1649f-0493-4b70-98ba-98533de7710b"

    def search_address(self, address: str):
        self.geocode = address
        self._request()

    def search_ll(self, ll: tuple):
        self.geocode = ",".join(map(str, ll))

    def get_ll(self, index: int):
        feature_member = self.json_resp["response"]["GeoObjectCollection"]["featureMember"][index]
        ll_string = feature_member["GeoObject"]["Point"]["pos"]
        return tuple(map(float, ll_string.split()))

    def get_address(self, index: int):
        feature_member = self.json_resp["response"]["GeoObjectCollection"]["featureMember"][index]
        return feature_member["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]["Address"]["formatted"]

    def get_point(self, index: int, style: str, color: str = "", size: int = "", content: int = ""):
        ll = self.get_ll(index)
        return YaMapPoint(ll, style, color, size, content)

    def get_postal_code(self, index: int):
        feature_member = self.json_resp["response"]["GeoObjectCollection"]["featureMember"][index]
        try:
            return feature_member["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]["Address"]["postal_code"]
        except KeyError:
            return ""

    def _request(self):
        req_params = {
            "apikey": self.apikey,
            "geocode": self.geocode,
            "format": "json"
        }
        response = requests.get(self.server_addr, req_params)
        if not response:
            print(f"Error: {response.status_code} ({response.reason})")
        self.json_resp = response.json()


class YaMapMap(object):
    def __init__(self, ll: tuple, scale: int, layer_comb: int, points: tuple = ()):
        self.server_addr = "https://static-maps.yandex.ru/1.x/"
        self.aval_layers = (("map",), ("sat",), ("sat", "skl"),
                            ("sat", "trf", "skl"), ("map", "trf", "skl"))
        if -180 <= ll[0] <= 180 and -90 <= ll[1] <= 90:
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
        if all(map(lambda point: isinstance(point, YaMapPoint), points)):
            self.points = points
        else:
            raise TypeError()

    def save_image(self, filename: str, autopos=False):
        ll_str = ",".join(map(str, self.ll))
        l_str = ",".join(self.aval_layers[self.layer_comb])
        pt_str = "~".join(map(lambda point: point.get_string(), self.points))
        req_params = {}
        req_params["l"] = l_str
        req_params["z"] = self.scale
        # req_params["size"] = "256,256"
        if not autopos or not pt_str:
            req_params["ll"] = ll_str
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
        if -180 <= new_ll[0] <= 180 and -90 <= new_ll[1] <= 90:
            self.ll = new_ll

    def zoom_in(self):
        if self.scale < 17:
            self.scale += 1

    def zoom_out(self):
        if self.scale > 0:
            self.scale -= 1

    def set_scale(self, scale: int):
        if 0 <= scale <= 17:
            self.scale = scale

    def set_ll(self, ll: tuple):
        if -180 <= ll[0] <= 180 and -90 <= ll[1] <= 90:
            self.ll = ll

    def cycle_layers(self):
        self.layer_comb = (self.layer_comb + 1) % len(self.aval_layers)

    def get_scale(self):
        return self.scale

    def set_points(self, points: tuple):
        self.points = points


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        ll = (37.530887, 55.703118)
        scale = 17
        layer_comb = 0
        self.map_autopos = False
        self.map = YaMapMap(ll, scale, layer_comb)
        self.search = YaMapSearch()
        self.initUi()
        self.update_image()

    def initUi(self):
        uic.loadUi("MainWindow.ui", self)
        self.action_exit.triggered.connect(sys.exit)
        self.horizontalSlider.valueChanged.connect(self.update_scale)
        self.pushButton_cycle_view.clicked.connect(self.cycle_layers)
        self.pushButton_search.clicked.connect(self.search_address)
        self.pushButton_reset.clicked.connect(self.reset_search)
        self.checkBox_add_index.clicked.connect(self.update_address)

    def keyPressEvent(self, event):
        upd = False
        key = event.key()
        if key == QtCore.Qt.Key_PageDown:
            self.horizontalSlider.setValue(self.horizontalSlider.value() - 1)
        elif key == QtCore.Qt.Key_PageUp:
            self.horizontalSlider.setValue(self.horizontalSlider.value() + 1)
        elif key == QtCore.Qt.Key_Space:
            self.map.cycle_layers()
            upd = True
        elif key == QtCore.Qt.Key_Right:
            spn = scale_to_spn(self.map.get_scale(), (650, 450))
            delta = (spn[0] / 2, 0)
            self.map.move_map(delta)
            upd = True
        elif key == QtCore.Qt.Key_Left:
            spn = scale_to_spn(self.map.get_scale(), (650, 450))
            delta = (-spn[0] / 2, 0)
            self.map.move_map(delta)
            upd = True
        elif key == QtCore.Qt.Key_Up:
            spn = scale_to_spn(self.map.get_scale(), (650, 450))
            delta = (0, spn[1] / 2)
            self.map.move_map(delta)
            upd = True
        elif key == QtCore.Qt.Key_Down:
            spn = scale_to_spn(self.map.get_scale(), (650, 450))
            delta = (0, -spn[1] / 2)
            self.map.move_map(delta)
            upd = True
        if upd:
            self.update_image()

    def move_map(self, delta):
        self.map.move_map(delta)
        self.update_image()

    def cycle_layers(self):
        self.map.cycle_layers()
        self.update_image()

    def update_scale(self):
        self.map.set_scale(self.sender().value())
        self.update_image()

    def search_address(self):
        req = self.lineEdit_request.text()
        self.search.search_address(req)
        point = self.search.get_point(0, "comma")
        ll = self.search.get_ll(0)
        address = self.search.get_address(0)
        self.map.set_ll(ll)
        self.map.set_points((point,))
        print(ll)
        self.update_image()
        self.update_address()

    def update_address(self):
        address = self.search.get_address(0)
        postal_code = self.search.get_postal_code(0)
        if self.checkBox_add_index.isChecked() and postal_code:
            address += "; " + postal_code
        self.lineEdit_address.setText(address)

    def reset_search(self):
        self.map.set_points(())
        self.lineEdit_address.clear()
        self.update_image()

    def update_image(self):
        filename = self.map.save_image("map", self.map_autopos)
        pixmap = QtGui.QPixmap(filename)
        self.label_map.setPixmap(pixmap)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
