# coding:utf-8
import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QApplication, QWidget

from qfluentwidgets import (MessageBox, SubtitleLabel, RadioButton, PushButton, PrimaryPushButton)


setting_info = {
    'Auto Fill:': ['From first frame', 'From previous frame'],
    'Simplify Annotation:': ['On', 'Off']
}


class SettingWidget(QWidget):
    def __init__(self, title_name: str, selection_list: list, Vlayout: bool, parent=None):
        super().__init__(parent=parent)
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setSpacing(10)
        if Vlayout:
            self.button_layout = QVBoxLayout()
        else:
            self.button_layout = QHBoxLayout()

        self.section_label = SubtitleLabel(title_name)
        self.section_label.setFixedHeight(40)

        self.button_list = []
        for selection in selection_list:
            self.button_list.append(RadioButton(selection, self))

        self.mainLayout.addWidget(self.section_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        for button in self.button_list:
            self.button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.mainLayout.addLayout(self.button_layout)

        self.button_list[0].setChecked(True)

    # Get title value
    def get_title(self):
        return self.section_label.text()

    # Get selected label value
    def get_checked(self):
        for button in self.button_list:
            if button.isChecked():
                return button.text()

    # Set selected label value
    def set_checked(self, selection_name):
        if selection_name is None:
            return
        for button in self.button_list:
            if button.text() == selection_name:
                button.setChecked(True)
                break


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

        layout_list = [False, False]

        self.setting_widget_list = []

        # Automatic import settings
        for index, dict_item in enumerate(setting_info.items()):
            title_name, setting_list = dict_item
            self.setting_widget_list.append(
                SettingWidget(title_name=title_name, selection_list=setting_info[title_name],
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
        self.close_flag = False

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
            self.SettingChanged.emit(setting_dict)
        self.close_flag = True
        self.close()

    def _cancel_function(self):
        self.close_flag = True
        self.close()

    def closeEvent(self, event):
        if self.close_flag:
            self.close_flag = False
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
