# coding:utf-8
import sys

import cv2
import numpy as np
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout
from qfluentwidgets import ComboBox, PrimaryPushButton
from PyQt6.QtCore import QThread, pyqtSignal

from MFT.MFT import MFT
from MFT.point_tracking import convert_to_point_tracking


class PointTracker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    canceled = pyqtSignal()

    def __init__(self, video, queries, checkpoint_path, device):
        super().__init__()
        self.video = video
        self.queries = queries
        self.checkpoint_path = checkpoint_path
        self.device = device

        self.stop_flag = False

    def run(self):
        initialized = False
        tracker = MFT(checkpoint_path=self.checkpoint_path, device=self.device)
        result = []

        frame = self.video.get_origin_frame(0)
        h, w, _ = frame.shape
        max_width = 1000
        max_height = 1000
        # screen_width = win32api.GetSystemMetrics(0)
        # screen_height = win32api.GetSystemMetrics(1)
        scaling = min(max_width * 1.0 / w, max_height * 1.0 / h)
        height = int(h * scaling)
        width = int(w * scaling)
        scaling_size = [height, width]
        scaling = height * 1.0 / h

        for index in range(len(self.video)):
            ori_frame = self.video.get_origin_frame(index)
            frame = cv2.resize(ori_frame, (scaling_size[1], scaling_size[0]), interpolation=cv2.INTER_LINEAR)
            # cv2.imshow('image', frame)
            # cv2.waitKey(0)
            if not initialized:
                meta = tracker.init(frame)
                initialized = True
            else:
                meta = tracker.track(frame)

            coords, occlusions = convert_to_point_tracking(meta.result, queries=(np.array(self.queries)*scaling).tolist())

            coordinates = []

            num = coords.shape[0]
            for i in range(num):
                if occlusions[i] > 0.5:
                    coordinates.append(None)
                else:
                    coordinates.append((coords[i, :]/scaling).tolist())

            result.append(coordinates)

            self.progress.emit(index)

            if self.stop_flag:
                break
            # print(str(index) + '/' + str(len(self)))
        if not self.stop_flag:
            self.finished.emit(result)
        else:
            self.canceled.emit()

    def __len__(self):
        return len(self.video)

    def stop(self):
        self.stop_flag = True

class PointTrackingWidget(QWidget):
    def __init__(self, devices=None, parent=None):
        super().__init__(parent=parent)

        if devices is None:
            devices = ['cpu']

        self.MainLayout = QHBoxLayout(self)

        self.device_select_box = ComboBox(self)
        self.device_select_box.setPlaceholderText("Select your device")
        self.device_select_box.addItems(devices)
        self.device_select_box.setCurrentIndex(-1)

        self.button = PrimaryPushButton("Track by model", self)

        self.MainLayout.addWidget(self.device_select_box)
        self.MainLayout.addWidget(self.button)

        self.device_select_box.currentText()

    def set_enable(self, enable):
        self.button.setEnabled(enable)

    def get_device(self):
        if self.is_selective():
            return self.device_select_box.currentText()
        else:
            return 'cpu'

    def is_selective(self):
        if self.device_select_box.currentIndex() == -1:
            return False
        else:
            return True

def print_text(device):
    print(device)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = PointTrackingWidget()
    w.show()
    w.button.clicked.connect(lambda: print_text(w.get_device()))
    sys.exit(app.exec())
