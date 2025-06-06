# coding:utf-8
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QApplication, QWidget
from qfluentwidgets import (SubtitleLabel, TitleLabel, RadioButton, CheckBox,
                            SpinBox, PushButton)


class LocationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)

        self.location_label = SubtitleLabel('Location:')
        self.location_label.setFixedHeight(40)

        self.tissue_button = RadioButton('Tissue', self)
        self.instrument_button = RadioButton('Instrument', self)

        self.mainLayout.addWidget(self.location_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.mainLayout.addWidget(self.tissue_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.mainLayout.addWidget(self.instrument_button,
                                  alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.tissue_button.setChecked(True)

    # Get selected label value
    def get_checked(self):
        if self.tissue_button.isChecked():
            return 'Tissue'
        elif self.instrument_button.isChecked():
            return 'Instrument'
        else:
            return None

    # Set selected label value
    def set_checked(self, location):
        if location is None:
            return
        if location == 'Tissue':
            self.tissue_button.setChecked(True)
        elif location == 'Instrument':
            self.instrument_button.setChecked(True)


class StatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)

        self.status_label = SubtitleLabel('Status:')
        self.status_label.setFixedHeight(40)

        # self.option_list = ['Clear view',
        #                     'Pulled',
        #                     'Reflection',
        #                     'Obscured by smoke',
        #                     'Obscured by instrument',
        #                     'Obscured by tissue',
        #                     'Off camera']

        self.option_list = ['Clear View',
                            'Pulled',
                            'Reflection',
                            'Smoke Obscuration',
                            'Instrument Obscuration',
                            'Tissue Obscuration',
                            'Out of view']

        self.check_box_list = []
        for option in self.option_list:
            check_box = CheckBox(option, self)
            check_box.setTristate(False)
            self.check_box_list.append(check_box)

        self.mainLayout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        for check_box in self.check_box_list:
            self.mainLayout.addWidget(check_box, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    # Get label items
    def get_checked(self):
        checked_list = []
        for index, check_box in enumerate(self.check_box_list):
            if check_box.isChecked():
                checked_list.append(self.option_list[index])
        return checked_list

    # Set annotation items
    def set_checked(self, checked_list):
        if checked_list is None:
            checked_list = []
        for index, check_box in enumerate(self.check_box_list):
            if self.option_list[index] in checked_list:
                self.check_box_list[index].setChecked(True)
            else:
                self.check_box_list[index].setChecked(False)


class OrderWidget(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)

        self.status_label = SubtitleLabel(title)
        self.status_label.setFixedHeight(40)

        self.orderEdit = SpinBox(self)
        self.orderEdit.setAccelerated(True)
        self.orderEdit.setMaximum(9999)

        self.mainLayout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.mainLayout.addWidget(self.orderEdit, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    # Get label items
    def get_order(self):
        return self.orderEdit.value()

    # Set label items
    def set_order(self, order):
        self.orderEdit.setValue(order)

    def set_zero(self):
        self.orderEdit.setValue(0)


class InstrumentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)

        self.location_label = SubtitleLabel('Instrument Name:')
        self.location_label.setFixedHeight(40)

        # instruments_list = ['Cadiere Forceps',
        #                     'Bipolar Coagulation Forceps',
        #                     'Needle Holder',
        #                     'Clip Applier',
        #                     'Clip',
        #                     'Curved Grasper',
        #                     'Harmonic Ace']

        instruments_list = ['Cadiere Forceps',
                            'Fenestrated Bipolar Forceps',
                            'Needle Diver',
                            'Clip Applier',
                            'Clip',
                            'Tip-Up Fenestrated Grasper',
                            'Harmonic Ace Curved Shears']

        self.button_list = []
        for instrument_name in instruments_list:
            self.button_list.append(RadioButton(instrument_name, self))

        self.mainLayout.addWidget(self.location_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        for button in self.button_list:
            self.mainLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.button_list[0].setChecked(True)

    # Get label items
    def get_checked(self):
        for button in self.button_list:
            if button.isChecked():
                return button.text()

    # Set label items
    def set_checked(self, instrument_name):
        if instrument_name is None:
            return
        for button in self.button_list:
            if button.text() == instrument_name:
                button.setChecked(True)
                break


class InstrumentStatus(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)

        self.location_label = SubtitleLabel('Status:')
        self.location_label.setFixedHeight(40)

        # instruments_list = ['Clear view',
        #                     'Self-occlusion',
        #                     'Eternal occlusion',
        #                     'Off camera']

        instruments_list = ['Clear View',
                            'Self-occlusion',
                            'Eternal Occlusion',
                            'Out of view']

        self.button_list = []
        for instrument_name in instruments_list:
            self.button_list.append(RadioButton(instrument_name, self))

        self.mainLayout.addWidget(self.location_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        for button in self.button_list:
            self.mainLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.button_list[0].setChecked(True)

    # Get label items
    def get_checked(self):
        for button in self.button_list:
            if button.isChecked():
                return button.text()

    # Set label items
    def set_checked(self, instrument_name):
        if instrument_name is None:
            return
        for button in self.button_list:
            if button.text() == instrument_name:
                button.setChecked(True)
                break


class PromptEditor(QWidget):
    EditorSwitch = pyqtSignal(bool)
    KeyFrameSwitch = pyqtSignal(bool)
    AnnotationSwitch = pyqtSignal(bool)
    VideoSwitch = pyqtSignal(bool)

    def __init__(self, test_function=False):
        super().__init__()
        self.setWindowTitle('Prompt Editor')
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(40, 10, 40, 10)
        self.setStyleSheet('PromptEditor{background:white}')
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.video_name = TitleLabel('Video Name')
        self.video_name.setFixedHeight(60)
        self.index_label = SubtitleLabel('Frame: 0      Index: 0')
        self.index_label.setFixedHeight(30)

        self.locationWidget = LocationWidget(self)
        self.statusWidget = StatusWidget(self)
        self.instrumentOrderWidget = OrderWidget('Instrument Order:', self)
        self.pointOrderWidget = OrderWidget('Point Order:', self)
        self.pointOrderWidget.orderEdit.setMinimum(1)
        self.pointOrderWidget.orderEdit.setMaximum(7)
        self.instrumentWidget = InstrumentWidget(self)
        self.instrumentStatusWidget = InstrumentStatus(self)
        self.instrumentWidget.hide()
        self.instrumentOrderWidget.hide()
        self.pointOrderWidget.hide()
        self.instrumentWidget.hide()
        self.instrumentStatusWidget.hide()

        self.mainLayout.addWidget(self.video_name, alignment=Qt.AlignmentFlag.AlignCenter)
        self.mainLayout.addWidget(self.index_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.mainLayout.addWidget(self.locationWidget)
        self.mainLayout.addWidget(self.statusWidget)
        self.mainLayout.addWidget(self.instrumentOrderWidget)
        self.mainLayout.addWidget(self.pointOrderWidget)
        self.mainLayout.addWidget(self.instrumentWidget)
        self.mainLayout.addWidget(self.instrumentStatusWidget)
        if test_function:
            self.test_button = PushButton('Test Button')
            self.test_button.clicked.connect(self.print_annotation)
            self.mainLayout.addWidget(self.test_button)
            self.video_name.setText('Test')

        self.locationWidget.tissue_button.clicked.connect(self.statusWidget.show)
        self.locationWidget.tissue_button.clicked.connect(self.instrumentOrderWidget.hide)
        self.locationWidget.tissue_button.clicked.connect(self.pointOrderWidget.hide)
        self.locationWidget.tissue_button.clicked.connect(self.instrumentWidget.hide)
        self.locationWidget.tissue_button.clicked.connect(self.instrumentStatusWidget.hide)
        self.locationWidget.instrument_button.clicked.connect(self.statusWidget.hide)
        self.locationWidget.instrument_button.clicked.connect(self.instrumentOrderWidget.show)
        self.locationWidget.instrument_button.clicked.connect(self.pointOrderWidget.show)
        self.locationWidget.instrument_button.clicked.connect(self.instrumentWidget.show)
        self.locationWidget.instrument_button.clicked.connect(self.instrumentStatusWidget.show)
        self.locationWidget.tissue_button.clicked.connect(self.adjustSize)
        self.locationWidget.instrument_button.clicked.connect(self.adjustSize)

        self.instrumentOrderWidget.orderEdit.valueChanged.connect(self.pointOrderWidget.set_zero)

        self.frame_index = 0
        self.annotation_index = 0
        self.lock_if_not_first_frame = True

    def print_annotation(self):
        print(self.get_annotation())

    def set_able_or_not(self, able):
        self.locationWidget.setEnabled(able)
        self.statusWidget.setEnabled(able)
        self.instrumentOrderWidget.setEnabled(able)
        self.pointOrderWidget.setEnabled(able)
        self.instrumentWidget.setEnabled(able)
        self.instrumentStatusWidget.setEnabled(able)

    def lock_for_save(self,able):
        self.locationWidget.setEnabled(not able)
        # self.statusWidget.setEnabled(able)
        self.instrumentOrderWidget.setEnabled(not able)
        self.pointOrderWidget.setEnabled(not able)
        self.instrumentWidget.setEnabled(not able)
        # self.instrumentStatusWidget.setEnabled(able)

    def set_video_name(self, video_name):
        self.video_name.setText(video_name)

    def set_index(self, frame_index, annotation_index):
        self.index_label.setText('Frame: {}      Index: {}'.format(frame_index, annotation_index))
        self.frame_index = frame_index
        self.annotation_index = annotation_index

    def load_annotation(self, annotation):
        try:
            location = annotation['location']
            self.locationWidget.set_checked(location)
        except:
            location = self.locationWidget.get_checked()
        if location == 'Tissue':
            try:
                status = annotation['status']
            except:
                status = []
            self.statusWidget.set_checked(status)
            self.statusWidget.show()
            self.instrumentOrderWidget.hide()
            self.pointOrderWidget.hide()
            self.instrumentWidget.hide()
            self.instrumentStatusWidget.hide()
            self.adjustSize()
        else:
            try:
                instrument_order = annotation['instrument_order']
                self.instrumentOrderWidget.set_order(instrument_order)
            except:
                pass
            try:
                point_order = annotation['point_order']
                self.pointOrderWidget.set_order(point_order)
            except:
                pass
            try:
                instrument_name = annotation['instrument_name']
                self.instrumentWidget.set_checked(instrument_name)
            except:
                pass
            try:
                status = annotation['status']
                self.instrumentStatusWidget.set_checked(status)
            except:
                pass
            self.statusWidget.hide()
            self.instrumentOrderWidget.show()
            self.pointOrderWidget.show()
            self.instrumentWidget.show()
            self.instrumentStatusWidget.show()
            self.adjustSize()

    def get_video_name(self):
        return self.video_name.text()

    def get_index(self):
        return self.frame_index, self.annotation_index

    def get_annotation(self):
        if self.video_name.text() == 'Video Name':
            return None
        location = self.locationWidget.get_checked()
        if location == 'Tissue':
            status = self.statusWidget.get_checked()
            return {'location': location, 'status': status}
        else:
            instrument_order = self.instrumentOrderWidget.get_order()
            point_order = self.pointOrderWidget.get_order()
            instrument_name = self.instrumentWidget.get_checked()
            status = self.instrumentStatusWidget.get_checked()
            return {'location': location, 'instrument_order': instrument_order, 'point_order': point_order,
                    'instrument_name': instrument_name, 'status': status}

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        modifiers = event.modifiers()
        # Roll up
        if delta > 0:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.EditorSwitch.emit(True)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.KeyFrameSwitch.emit(True)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.VideoSwitch.emit(True)
            elif modifiers == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                self.AnnotationSwitch.emit(True)
        # Roll down
        elif delta < 0:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.EditorSwitch.emit(False)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.KeyFrameSwitch.emit(False)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.VideoSwitch.emit(False)
            elif modifiers == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                self.AnnotationSwitch.emit(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = PromptEditor(test_function=False)
    w.load_annotation({'location': 'Instrument', 'instrument_order': 1, 'point_order': 4, 'instrument_name': 'Clip', 'status': 'Self-Occlusion'})
    # w._load_video(folder_path='./data')
    w.show()
    sys.exit(app.exec())
