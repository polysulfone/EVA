import sys
import cv2
from enum import Enum
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QHBoxLayout
)
from PyQt6.QtCore import Qt, QSize

from qfluentwidgets import (TransparentToolButton, ToolTipFilter, Slider)
from qfluentwidgets import FluentIcon as FIF


class Status(Enum):
    Default = 'default'
    Working = 'working'
    Error = 'error'
    Success = 'Success'


# Define the base class for video buttons
class MediaPlayBarButton(TransparentToolButton):
    """ Media play bar button """

    def _postInit(self):
        super()._postInit()
        self.installEventFilter(ToolTipFilter(self, 1000))
        self.setFixedSize(30, 30)
        self.setIconSize(QSize(16, 16))


# Play button class
class PlayButton(MediaPlayBarButton):
    """ Play button """

    def _postInit(self):
        super()._postInit()
        self.setIconSize(QSize(14, 14))
        self.setPlay(False)

    def setPlay(self, isPlay: bool):
        if isPlay:
            self.setIcon(FIF.PAUSE_BOLD)
            self.setToolTip(self.tr('Pause'))
        else:
            self.setIcon(FIF.PLAY_SOLID)
            self.setToolTip(self.tr('Play'))


# Previous button class
class PreviousButton(MediaPlayBarButton):
    def _postInit(self):
        super()._postInit()
        self.setIconSize(QSize(14, 14))
        self.setIcon(FIF.LEFT_ARROW)


# Next button class
class NextButton(MediaPlayBarButton):
    def _postInit(self):
        super()._postInit()
        self.setIconSize(QSize(14, 14))
        self.setIcon(FIF.RIGHT_ARROW)


# Keyframe switch button class
class MarkerButton(QPushButton):
    def __init__(self, index, callback=None):
        super().__init__()
        self.index = index
        self.callback = callback
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status = "default"
        self.setObjectName(self.status)
        self.setStyleSheet(self.build_stylesheet())

        self.clicked.connect(lambda: callback(self.index)) if callback else None

    def setStatus(self, status: Status):
        """设置按钮状态颜色，例如：'default', 'working', 'error', 'success'"""
        self.status = status.value()
        self.setObjectName(status.value())
        self.setStyleSheet(self.build_stylesheet())

    def build_stylesheet(self):
        return """
        QPushButton#default {
            background-color: #0078D4;
            border: none;
            border-radius: 8px;
        }
        QPushButton#default:hover {
            background-color: #005A9E;
        }

        QPushButton#success {
            border: none;
            border-radius: 8px;
            background-color: #107C10;
        }
        QPushButton#success:hover {
            background-color: #0B6A0B;
        }

        QPushButton#working {
            border: none;
            border-radius: 8px;
            background-color: #FFB900;
        }
        QPushButton#working:hover {
            background-color: #EAA300;
        }

        QPushButton#error {
            border: none;
            border-radius: 8px;
            background-color: #D13438;
        }
        QPushButton#error:hover {
            background-color: #A80000;
        }
        """


# Keyframe indicator bar class
class MarkerOverlay(QWidget):

    def __init__(self, parent, keyframe_list=None, jump_callback=None):
        super().__init__(parent)
        self.jump_callback = jump_callback
        if keyframe_list is None:
            self.index_list = [0, 20, 40, 60, 80, 100]
        else:
            self.index_list = keyframe_list
        self.buttons = []
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        # self.setFixedHeight(25)
        self.setContentsMargins(76, 0, 40, 0)
        self.add_marker_buttons()


    def __len__(self):
        return len(self.index_list)

    # Clear
    def clear_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            self.layout.removeWidget(widget)
            # widget = item.widget()
            # if widget is not None:
            #     widget.deleteLater()
            #     widget.setParent(None)
            # elif item.layout() is not None:
            #     self.clear_layout(item.layout())

    # Readd
    def add_marker_buttons(self, progress_bar_len=400):
        for index, frame_num in enumerate(self.index_list):
            mark = MarkerButton(frame_num, self.jump_callback)
            self.layout.addWidget(mark, stretch=0)
            if index != len(self.index_list) - 1:
                gap = self.index_list[index + 1] - self.index_list[index]
                part1 = 1.0 * progress_bar_len * gap / self.index_list[-1]
                part2 = 16
                stretch = int((part1 - part2))
                self.layout.addStretch(stretch)
            self.buttons.append(mark)

    # Rearrange
    def resize(self, progress_bar_len):
        for index, frame_num in enumerate(self.index_list):
            operate_index = 2 * index + 1
            self.layout.removeItem(self.layout.itemAt(operate_index))
            if index != len(self.index_list) - 1:
                gap = self.index_list[index + 1] - self.index_list[index]
                part1 = 1.0 * progress_bar_len * gap / self.index_list[-1]
                part2 = 16
                stretch = int(10*(part1 - part2))
                self.layout.insertStretch(operate_index, stretch)

    # Rebuild
    def remake(self, keyframe_list, progress_bar_len):
        self.index_list = keyframe_list
        self.clear_layout()
        self.add_marker_buttons(progress_bar_len=progress_bar_len)

    # Set status
    def set_status(self, key_frame_index, status):
        self.buttons[key_frame_index].setStatus(status=status)


# Video playback progress bar class
class VideoPlayBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)

        self.hBoxLayout.setContentsMargins(10, 4, 10, 4)
        self.hBoxLayout.setSpacing(6)

        self.playBtn = PlayButton()
        self.preBtn = PreviousButton()
        self.progressSlider = Slider(Qt.Orientation.Horizontal, self)
        self.progressSlider.setMinimum(0)
        self.progressSlider.setMinimumWidth(400)
        self.nextBtn = NextButton()

        self.hBoxLayout.addWidget(self.playBtn)
        self.hBoxLayout.addWidget(self.preBtn)
        self.hBoxLayout.addWidget(self.progressSlider)
        self.hBoxLayout.addWidget(self.nextBtn)

        # self.setFixedHeight(48)

    def set_frames_num(self, total_num):
        self.progressSlider.setMaximum(total_num)

    def set_frames_progress(self, index):
        self.progressSlider.setValue(index)

    def get_slider_value(self):
        return self.progressSlider.value()

    def get_slider_width(self):
        return self.progressSlider.width()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = QWidget()
    layout = QVBoxLayout(widget)
    bar = VideoPlayBar(widget)
    bar.progressSlider.setMinimum(0)
    bar.progressSlider.setMaximum(100)
    bar.progressSlider.setTickInterval(1)
    marker = MarkerOverlay(widget, [0, 15, 36, 77, 100], jump_callback=bar.progressSlider.setValue)
    layout.addWidget(marker)
    layout.addWidget(bar)
    widget.show()
    cv2.waitKey()
    bar.progressSlider.setFixedWidth(800)
    marker.clear_layout()
    marker.add_marker_buttons(progress_bar_len=800)
    sys.exit(app.exec())
