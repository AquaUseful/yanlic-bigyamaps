from PyQt5 import QtWidgets, uic, QtGui, QtCore
import sys
import requests
import typing
import operator
import math


def lonlat_distance(a: tuple, b: tuple):
    degree_to_meters_factor = 111 * 1000
    a_lon, a_lat = a
    b_lon, b_lat = b
    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)
    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor
    distance = math.sqrt(dx * dx + dy * dy)
    return distance


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


class YaMapOrg(object):
    def __init__(self):
        self.server_addr = "https://search-maps.yandex.ru/v1/"
        self.apikey = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"

    def search_ll(self, ll: tuple, text: str):
        self.ll = ll
        self.ll_str = ",".join(map(str, ll))
        self.text = text
        self._request()

    def get_ll(self, radius: float):
        self._filter(radius)
        return self.feature_ll

    def get_name(self, radius: float):
        self._filter(radius)
        return self.feature_name

    def get_address(self, radius: float):
        self._filter(radius)
        return self.feature_address

    def get_point(self, radius: float, style: str, color: str = "", size: int = "", content: int = ""):
        self._filter(radius)
        if self.feature_ll is None:
            return
        point = YaMapPoint(self.feature_ll, style, color, size, content)
        return point

    def _filter(self, radius: float):
        self.feature_ll = None
        self.feature_name = None
        self.feature_address = None
        features = self.json_resp["features"]
        for feature in features:
            feature_ll = feature["geometry"]["coordinates"]
            distance = lonlat_distance(self.ll, feature_ll)
            if distance <= radius:
                self.feature_ll = feature_ll
                self.feature_name = feature["properties"]["name"]
                self.feature_address = feature["properties"]["CompanyMetaData"]["address"]

    def _request(self):
        self.filtered = False
        req_params = {
            "apikey": self.apikey,
            "ll": self.ll_str,
            "text": self.text,
            "lang": "ru_RU",
            "type": "biz"
        }
        response = requests.get(self.server_addr, req_params)
        if not response:
            print(f"Error: {response.status_code} ({response.reason})")
        self.json_resp = response.json()


class YaMapSearch(object):
    def __init__(self):
        self.server_addr = "https://geocode-maps.yandex.ru/1.x/"
        self.apikey = "40d1649f-0493-4b70-98ba-98533de7710b"

    def search_address(self, address: str):
        self.geocode = address
        self._request()

    def search_ll(self, ll: tuple):
        self.geocode = ",".join(map(str, ll))
        self._request()

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
    def __init__(self, ll: tuple, scale: int, layer_comb: int, points: tuple = (), img_size: tuple = (600, 450)):
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
        if 1 <= img_size[0] <= 600 and 1 <= img_size[1] <= 450:
            self.img_size = img_size
        else:
            raise ValueError()

    def save_image(self, filename: str, autopos=False):
        ll_str = ",".join(map(str, self.ll))
        l_str = ",".join(self.aval_layers[self.layer_comb])
        pt_str = "~".join(map(lambda point: point.get_string(), self.points))
        size_str = ",".join(map(str, self.img_size))
        req_params = {}
        req_params["l"] = l_str
        req_params["z"] = self.scale
        req_params["size"] = size_str
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

    def get_size(self, point):
        return self.img_size

    def coords_to_ll(self, coords: tuple):  # КРИВАЯ ФИГНЯ, КТО НАПИШЕТ НОРМАЛЬНУЮ - МОЛОДЕЦ
        spn = scale_to_spn(self.scale, self.img_size)
        coords = (coords[0], self.img_size[1] - coords[1])
        ll_corner_delta = tuple(map(
            lambda spn, coords, img_size: spn * (coords / img_size), spn, coords, self.img_size))
        ll_decart_delta = tuple(
            map(lambda corner_delta, spn: corner_delta - spn / 2, ll_corner_delta, spn))
        ll = map(lambda ll, decart_delta: ll +
                 decart_delta, self.ll, ll_decart_delta)
        print(coords, spn, ll_corner_delta, ll_decart_delta)
        return tuple(ll)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        ll = (37.530887, 55.703118)
        scale = 17
        layer_comb = 0
        self.map_autopos = False
        self.map = YaMapMap(ll, scale, layer_comb)
        self.search = YaMapSearch()
        self.org_search = YaMapOrg()
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
        self.label_map.lclicked.connect(self.search_point)
        self.label_map.rclicked.connect(self.search_org)

    def search_point(self, coords):
        ll = self.map.coords_to_ll(coords)
        self.search.search_ll(ll)
        point = YaMapPoint(ll, "comma")
        self.map.set_points((point,))
        self.update_address()
        self.update_image()

    def search_org(self, coords):
        self.reset_search()
        request = self.lineEdit_org_request.text()
        if not request:
            return
        ll = self.map.coords_to_ll(coords)
        self.org_search.search_ll(ll, request)
        point = self.org_search.get_point(50, "comma")
        if not point:
            return
        self.map.set_points((point,))
        self.update_org()
        self.update_image()

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
        self.lineEdit_org.clear()
        self.update_image()

    def update_org(self):
        name = self.org_search.get_name(50)
        if not name:
            return
        address = self.org_search.get_address(50)
        self.lineEdit_address.setText(address)
        self.lineEdit_org.setText(name)

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
