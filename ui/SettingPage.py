# coding:utf-8
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QApplication, QWidget

from qfluentwidgets import (MessageBox, SubtitleLabel, RadioButton, PushButton, PrimaryPushButton, SpinBox)


setting_info = {
    'Annotation Inheritance:': ['From first frame', 'From previous frame'],
    'Consistency Enforcement:': ['On', 'Off'],
    'Annotation Spacing:': [0, 999999]
}

layout_list = [False, False, False]

class SettingWidget(QWidget):
    def __init__(self, title_name: str, setting_list: list, Vlayout: bool, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)
        if Vlayout:
            self.button_layout = QVBoxLayout()
        else:
            self.button_layout = QHBoxLayout()

        self.section_label = SubtitleLabel(title_name)
        self.section_label.setFixedHeight(40)

        if type(setting_list[0]) == str:
            self.button_list = []

            for selection in setting_list:
                self.button_list.append(RadioButton(selection, self))

            self.mainLayout.addWidget(self.section_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            for button in self.button_list:
                self.button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

            self.mainLayout.addLayout(self.button_layout)

            self.button_list[0].setChecked(True)

            self.setting_type = 'button'
        else:
            self.spinBox = SpinBox(self)
            self.spinBox.setAccelerated(True)
            self.spinBox.setMinimum(setting_list[0])
            self.spinBox.setMaximum(setting_list[1])

            self.mainLayout.addWidget(self.section_label,
                                      alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.mainLayout.addWidget(self.spinBox)

            self.setting_type = 'input_box'


    # Get title value
    def get_title(self):
        return self.section_label.text()

    # Get selected label value
    def get_checked(self):
        if self.setting_type == 'button':
            for button in self.button_list:
                if button.isChecked():
                    return button.text()
        else:
            return self.spinBox.value()

    # Set selected label value
    def set_checked(self, setting_info):
        if setting_info is None:
            return
        if self.setting_type == 'button':
            for button in self.button_list:
                if button.text() == setting_info:
                    button.setChecked(True)
                    break
        else:
            if self.spinBox.value() != setting_info:
                self.spinBox.setValue(setting_info)


class SettingPage(QWidget):
    SettingChanged = pyqtSignal(dict)

    def __init__(self, setting_dict=None):
        super().__init__()
        self.setWindowTitle('Setting')
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(40, 10, 40, 10)
        self.setStyleSheet('SettingPage{background:white}')
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        # self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.setting_widget_list = []

        # Automatic import settings
        for index, dict_item in enumerate(setting_info.items()):
            title_name, setting_list = dict_item
            self.setting_widget_list.append(
                SettingWidget(title_name=title_name, setting_list=setting_info[title_name],
                              Vlayout=layout_list[index]))
            if setting_dict is not None and title_name in setting_dict:
                self.setting_widget_list[index].set_checked(setting_dict[title_name])

        # Initialize button
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 20, 0, 0)
        self.save_button = PrimaryPushButton('Save')
        self.cancel_button = PushButton('Cancel')
        self.button_layout.addWidget(self.save_button)
        self.button_layout.addWidget(self.cancel_button)

        for setting_widget in self.setting_widget_list:
            self.mainLayout.addWidget(setting_widget)
        self.mainLayout.addLayout(self.button_layout)

        self.save_button.clicked.connect(self._save_function)
        self.cancel_button.clicked.connect(self._cancel_function)
        self.ori_setting = setting_dict

    # Set setting
    def set_setting(self, setting_dict):
        for title_name, selection in setting_dict.items():
            if title_name in setting_info:
                self.setting_widget_list[list(setting_info.keys()).index(title_name)].set_checked(selection)

    # Save function
    def _save_function(self):
        if self.ori_setting:
            changed_flag = False
        else:
            changed_flag = True
        setting_dict = {}
        for setting_widget in self.setting_widget_list:
            title_name = setting_widget.get_title()
            setting_list = setting_widget.get_checked()
            setting_dict[title_name] = setting_list
            if self.ori_setting:
                if setting_list != self.ori_setting[title_name]:
                    changed_flag = True
        if changed_flag:
            self.ori_setting = setting_dict
            self.SettingChanged.emit(setting_dict)
        self.close()

    def _cancel_function(self):
        self.close()

    def closeEvent(self, event):
        changed_flag = False
        for setting_widget in self.setting_widget_list:
            title_name = setting_widget.get_title()
            setting_list = setting_widget.get_checked()
            if self.ori_setting:
                if setting_list != self.ori_setting[title_name]:
                    changed_flag = True
            else:
                changed_flag = True
        if not changed_flag:
            return

        title = 'Do you want to save the setting?'
        content = """You have modifyed the setting, would you like to save the change?"""

        w = MessageBox(title, content, self)

        w.setClosableOnMaskClicked(True)

        if w.exec():
            self._save_function()


def print_setting(setting_dict):
    print(setting_dict)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = SettingPage()
    w.SettingChanged.connect(print_setting)
    w.show()
    sys.exit(app.exec())
