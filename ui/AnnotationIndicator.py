import sys
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QFrame, QApplication, QGraphicsDropShadowEffect
)

from qfluentwidgets import (ToolButton)
from qfluentwidgets import FluentIcon as FIF

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class Status(Enum):
    VACANT = "Vacant"
    ERROR = "Error"
    LABELED = "Labeled"
    COMPLETE = "Complete"


class Position(Enum):
    NORMAL = "Normal"
    BOTH = "Both"
    LEFT = "Left"
    RIGHT = "Right"


# Lights
class Light(QFrame):

    clicked = pyqtSignal(object)

    def __init__(self, parent, status=Status.VACANT, transparency=255, position=Position.NORMAL):
        super().__init__(parent=parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(60)
        self.highlighted = False
        self.status = status
        self.transparency = transparency
        self.position = position
        self.left_radius = 0
        self.right_radius = 0
        if position == Position.LEFT:
            self.setLeftRaius()
        elif position == Position.RIGHT:
            self.setRightRaius()
        elif position == Position.BOTH:
            self.setLeftRaius()
            self.setRightRaius()
        self.setLightStyle()
        self.applyShadow()
        self.shadow.setEnabled(False)

    def setLightStyle(self):
        if self.highlighted:
            self.setFixedHeight(25)
        else:
            self.setFixedHeight(20)

        self.setStyleSheet(f"""
            background-color: rgba({self.getColorRgb()}, {self.transparency}); 
            border-top-left-radius: {self.left_radius};
            border-bottom-left-radius: {self.left_radius}px;
            border-top-right-radius: {self.right_radius}px;
            border-bottom-right-radius: {self.right_radius};
            border: 3px solid rgba(0, 0, 0, 50)
        """)

    def setLeftRaius(self, set_left_radius=True):
        if set_left_radius:
            self.left_radius = 10
        else:
            self.left_radius = 0

    def setRightRaius(self, set_right_radius=True):
        if set_right_radius:
            self.right_radius = 10
        else:
            self.right_radius = 0

    def setPosition(self, position=Position.NORMAL):
        if position == Position.LEFT:
            self.setLeftRaius()
            self.setRightRaius(False)
        elif position == Position.RIGHT:
            self.setRightRaius()
            self.setLeftRaius(False)
        elif position == Position.BOTH:
            self.setLeftRaius()
            self.setRightRaius()
        else:
            self.setLeftRaius(False)
            self.setRightRaius(False)
        self.setLightStyle()

    def getColorRgb(self):

        if self.status == Status.VACANT:
            return "165, 165, 165"
        elif self.status == Status.ERROR:
            return "223, 33, 59"
        elif self.status == Status.LABELED:
            return "255, 235, 156"
        elif self.status == Status.COMPLETE:
            return "198, 239, 206"
        return "169, 169, 169"

    def setStatus(self, status: Status):
        self.status = status
        self.setLightStyle()

    def setHighlighted(self, highlight: bool):
        self.highlighted = highlight
        self.setLightStyle()

    def applyShadow(self):

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        self.shadow.setEnabled(True)

    def leaveEvent(self, event):
        self.shadow.setEnabled(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self)


# LightStrip class
class LightStrip(QWidget):
    AnnotationSelectiveChanged = pyqtSignal(int)
    AnnotationInserted = pyqtSignal(int)
    AnnotationAppended = pyqtSignal()
    AnnotationDeleted = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.lights = [Light(self, status=Status.VACANT, position=Position.BOTH)]
        self.lights[0].setHighlighted(True)
        self.lights[0].clicked.connect(self.leftClickEvent)
        self.dividers = []  # 用来存储竖线
        self.currentIndex = 0

        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.lights[0], stretch=1)

    def __len__(self):
        return len(self.lights)

    def checkPosition(self, index=None):
        if index is None:
            index = self.currentIndex

        if index == 0 and len(self) > 1:
            position = Position.LEFT
        elif index == 0 and len(self) == 1:
            position = Position.BOTH
        elif index == len(self) - 1:
            position = Position.RIGHT
        else:
            position = Position.NORMAL
        return position

    def switch_by_wheel(self, direction: bool):
        if direction and self.currentIndex > 0:
            self.switch2Index(self.currentIndex - 1)
        elif direction and self.currentIndex == 0:
            self.switch2Index(len(self) - 1)
        elif not direction and self.currentIndex < len(self) - 1:
            self.switch2Index(self.currentIndex + 1)
        elif not direction and self.currentIndex == len(self) - 1:
            self.switch2Index(0)

    def switch2Index(self, index, react=True):
        assert index < len(self)
        if self.currentIndex == index:
            return

        self.lights[self.currentIndex].setHighlighted(False)

        self.currentIndex = index
        self.lights[self.currentIndex].setHighlighted(True)
        if react:
            self.AnnotationSelectiveChanged.emit(self.currentIndex)

    def insertLight(self, index=None, status=Status.VACANT, react=True):
        if index is None:
            index = self.currentIndex

        if index == 0:
            light = Light(self, status=status, position=Position.LEFT)
        else:
            light = Light(self, status=status, position=Position.NORMAL)
        light.clicked.connect(self.leftClickEvent)

        divider = self._makeDivider()
        # Insert new light and its dividing line
        self.lights.insert(index, light)
        if self.currentIndex == len(self) - 1:
            self.dividers.append(divider)
        else:
            self.dividers.insert(index, divider)
        if status == Status.VACANT:
            stretch = 1
        else:
            stretch = 1
        self.layout.insertWidget(index * 2, divider)
        self.layout.insertWidget(index * 2, light, stretch=stretch)
        if react:
            self.AnnotationInserted.emit(index)
        # Switch to new light
        if index == 0:
            position = self.checkPosition(1)
            self.lights[1].setPosition(position)
        if self.currentIndex >= index:
            self.currentIndex += 1
        self.switch2Index(index)

    def appendLight(self, status=Status.VACANT, react=True):
        # Instantiate dividing line and light
        light = Light(self, status=status, position=Position.RIGHT)
        light.clicked.connect(self.leftClickEvent)
        divider = self._makeDivider()
        # Insert a new lamp and its dividing line
        if status == Status.VACANT:
            stretch = 1
        else:
            stretch = 1
        self.lights.append(light)
        self.dividers.append(divider)
        self.layout.addWidget(divider)
        self.layout.addWidget(light, stretch=stretch)
        if react:
            self.AnnotationAppended.emit()
        # Switch to new light
        position = self.checkPosition(len(self) - 2)
        self.lights[-2].setPosition(position)
        self.switch2Index(len(self) - 1, react=react)

    def removeLight(self, index=None, react=True):
        if len(self) == 1:
            return
        if index is None:
            index = self.currentIndex
        assert index < len(self)
        if index == 0:
            # Remove first frame
            light = self.lights.pop(0)
            divider = self.dividers.pop(0)
            self.layout.removeWidget(light)
            self.layout.removeWidget(divider)
        else:
            # Remove other frames
            light = self.lights.pop(index)
            divider = self.dividers.pop(index - 1)
            self.layout.removeWidget(light)
            self.layout.removeWidget(divider)
        if index == 0:
            position = self.checkPosition(0)
            self.lights[0].setPosition(position)
        if index == len(self):
            position = self.checkPosition(len(self) - 1)
            self.lights[-1].setPosition(position)
        if index == self.currentIndex:
            if self.currentIndex >= len(self):
                self.currentIndex = len(self) - 1
            self.lights[self.currentIndex].setHighlighted(True)
        if react:
            self.AnnotationDeleted.emit(index)
            self.AnnotationSelectiveChanged.emit(self.currentIndex)

    # Reset indicator bar
    def remake(self, react=True):
        while len(self) > 1:
            self.removeLight(0, react=react)
        self.setLightStatus(status=Status.VACANT, index=0)
        self.currentIndex = 0
        self.lights[0].setHighlighted(True)


    def _makeDivider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setLineWidth(1)
        line.setFixedHeight(30)
        return line

    def nextLight(self):
        if self.currentIndex < len(self) - 1:
            self.switch2Index(self.currentIndex + 1)
        elif self.lights[-1].status:
            self.appendLight()

    def prevLight(self):
        if self.currentIndex > 0:
            self.switch2Index(self.currentIndex - 1)

    def setLightStatus(self, status: Status, index=None):
        if index is None:
            index = self.currentIndex
        self.lights[index].setStatus(status=status)
        if status == Status.VACANT:
            stretch = 1
        else:
            stretch = 1
        self.layout.setStretch(index * 2, stretch)

    def leftClickEvent(self, clicked_light: QWidget):
        index = self.lights.index(clicked_light)
        self.switch2Index(index)


# Indicator area (light bar + horizontal button group)
class IndicatorPanel(QWidget):
    AnnotationSelectiveChanged = pyqtSignal(int)
    AnnotationInserted = pyqtSignal(int)
    AnnotationAppended = pyqtSignal()
    AnnotationDeleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.lightStrip = LightStrip()

        self.prevBtn = ToolButton(FIF.CARE_LEFT_SOLID, self)
        self.nextBtn = ToolButton(FIF.CARE_RIGHT_SOLID, self)
        self.insertBtn = ToolButton(FIF.ADD, self)
        self.removeBtn = ToolButton(FIF.CLOSE, self)

        self.prevBtn.clicked.connect(self.lightStrip.prevLight)
        self.nextBtn.clicked.connect(self.lightStrip.nextLight)
        self.insertBtn.clicked.connect(lambda: self.lightStrip.insertLight(index=self.lightStrip.currentIndex))
        self.removeBtn.clicked.connect(lambda: self.lightStrip.removeLight(index=self.lightStrip.currentIndex))

        self.lightStrip.AnnotationSelectiveChanged.connect(self.AnnotationSelectiveChanged)
        self.lightStrip.AnnotationInserted.connect(self.AnnotationInserted)
        self.lightStrip.AnnotationAppended.connect(self.AnnotationAppended)
        self.lightStrip.AnnotationDeleted.connect(self.AnnotationDeleted)

        buttonWidge = QWidget()
        buttonLayout = QHBoxLayout(buttonWidge)
        buttonLayout.setSpacing(8)
        buttonLayout.setContentsMargins(0, 0, 0, 0)
        for btn in [self.prevBtn, self.nextBtn, self.insertBtn, self.removeBtn]:
            buttonLayout.addWidget(btn)

        mainLayout = QHBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(20)
        mainLayout.addWidget(self.lightStrip, stretch=1)
        mainLayout.addWidget(buttonWidge)

    def remake(self, react=True):
        self.lightStrip.remake(react=react)

    # Load annotation
    def load_annotation_list(self, annotation_list):
        ori_index = self.lightStrip.currentIndex
        self.lightStrip.remake(react=False)
        if annotation_list is not None:
            for index, annotation in enumerate(annotation_list):
                if index != 0:
                    self.lightStrip.appendLight(react=False)
                if annotation is None:
                    self.lightStrip.setLightStatus(status=Status.VACANT, index=index)
                else:
                    self.lightStrip.setLightStatus(status=Status.LABELED, index=index)
        if ori_index < len(self.lightStrip):
            self.lightStrip.switch2Index(ori_index, react=False)
        else:
            self.lightStrip.switch2Index(0, react=False)
        self.AnnotationSelectiveChanged.emit(self.lightStrip.currentIndex)

    # Set light status
    def setLightStatus(self, status: Status, index=None):
        self.lightStrip.setLightStatus(status=status, index=index)

    def switch_by_wheel(self, direction: bool):
        self.lightStrip.switch_by_wheel(direction=direction)

    # Lock the buttons
    def lock_for_safe(self, able):
        self.prevBtn.setEnabled(not able)
        self.nextBtn.setEnabled(not able)
        self.insertBtn.setEnabled(not able)
        self.removeBtn.setEnabled(not able)

# Test
def changed(index):
    print('Switch to point{}'.format(index))


def inserted(index):
    print('Insert a point at {}'.format(index))


def appended():
    print('Append a point')


def deleted(index):
    print('Remove point{}'.format(index))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = IndicatorPanel()
    window.AnnotationSelectiveChanged.connect(changed)
    window.AnnotationInserted.connect(inserted)
    window.AnnotationAppended.connect(appended)
    window.AnnotationDeleted.connect(deleted)
    window.show()
    sys.exit(app.exec())
