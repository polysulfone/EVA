# coding:utf-8
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QMainWindow
from qfluentwidgets import (ProgressRing, InfoBar, InfoBarPosition, BodyLabel, PushButton)
from qfluentwidgets import FluentIcon as FIF


class ProgressWidget(QWidget):
    def __init__(self, total_len, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.progressRing = ProgressRing(self)
        self.progressRing.setValue(0)
        self.progressRing.setTextVisible(True)
        self.progressRing.setFixedSize(50, 50)

        self.current_progress = BodyLabel('0')
        self.current_progress.setStyleSheet("color: deepskyblue")

        self.spliter = BodyLabel('/')

        self.total_progress = BodyLabel(str(total_len))

        text_layout = QHBoxLayout()
        text_layout.addWidget(self.current_progress)
        text_layout.addWidget(self.spliter)
        text_layout.addWidget(self.total_progress)

        layout.addWidget(self.progressRing, stretch=2)
        layout.addLayout(text_layout, stretch=1)

        self.total_len = total_len

    def set_current_progress(self, index):
        self.current_progress.setText(str(index))
        self.progressRing.setValue(int(100.0*index/self.total_len))

    def set_total_progress(self, total_num):
        self.total_progress.setText(str(total_num))


class ProgressBox:
    def __init__(self, total_len, parent=None):
        self.info_box = InfoBar(
            icon=FIF.SYNC,
            title='Tracking...',
            content='',
            orient=Qt.Orientation.Vertical,
            isClosable=False,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=-1,
            parent=InfoBar.desktopView()
        )

        self.progressWidget = ProgressWidget(total_len)
        self.cancel_button = PushButton('Cancel')

        self.info_box.addWidget(self.progressWidget)
        self.info_box.addWidget(self.cancel_button)
        self.info_box.show()

    def set_current_progress(self, index):
        self.progressWidget.set_current_progress(index)

    def set_total_progress(self, total_num):
        self.progressWidget.set_total_progress(total_num)

    def close(self):
        self.info_box.close()

    def set_able(self):
        self.info_box.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QMainWindow()  # 创建主窗口（空窗口）
    window.setWindowTitle("空窗口示例")  # 设置窗口标题
    window.resize(400, 300)  # 设置窗口大小（可选）
    progressRing = ProgressBox(9999, window)
    window.show()
    progressRing.set_current_progress(456)
    app.exec()
