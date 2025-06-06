# coding:utf-8
import sys
import shutil
from tqdm import tqdm
import os
import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QAction, QShortcut, QKeySequence
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QApplication, QWidget, QFileDialog

from qfluentwidgets import (MSFluentTitleBar, MSFluentWindow,
                            SubtitleLabel, setFont,
                            TransparentToolButton,
                            isDarkTheme, TransparentDropDownPushButton, RoundMenu, Action,
                            InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF
from ui.AnnotationIndicator import IndicatorPanel
from ui.VideoPlayer import VideoFramePlayer
from ui.VideoGroupManager import VideoGroupManager
from ui.AnnotationIndicator import Status as LightStatus
from ui.PromptEditor import PromptEditor
from ui.VideoGroupManager import DatasetLoader
from ui.VideoPlayer import VideoManager
from ui.SettingPage import SettingPage


direction_list = ['left']


class Exporter:
    def __init__(self, data_path_list):
        data_loader = None
        for data_path in data_path_list:
            if data_loader is None:
                data_loader = DatasetLoader(data_path)
            else:
                data_loader = data_loader + DatasetLoader(data_path)
        self.data_loader = data_loader

    def export(self, output_path):
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.mkdir(output_path)
        with tqdm(total=len(self.data_loader)) as pbar:
            for sample in self.data_loader:
                # Get the original file path
                video_path = sample['sample_path']
                log_path = video_path.replace('.mp4', '.json')
                log_path = log_path.replace('classification', 'log')
                calib_file_path = './ui/calib.json'
                # Classpath construction
                output_class_path = os.path.join(output_path, str(sample['class_index']))
                if not os.path.exists(output_class_path):
                    os.mkdir(output_class_path)
                output_calib_file_path = os.path.join(output_class_path, 'calib.json')
                shutil.copyfile(calib_file_path, output_calib_file_path)
                # Direction path construction
                for direction in direction_list:
                    direction_path = os.path.join(output_class_path, direction)
                    seq_index = sample['sample_index']
                    seq_path = os.path.join(direction_path, 'seq{:0>3d}'.format(seq_index))
                    if not os.path.exists(seq_path):
                        os.makedirs(seq_path)
                    frames_path = os.path.join(seq_path, 'frames')
                    if not os.path.exists(frames_path):
                        os.mkdir(frames_path)
                    segmentation_path = os.path.join(seq_path, 'segmentation')
                    if not os.path.exists(segmentation_path):
                        os.mkdir(segmentation_path)
                    # Get video information and save the video
                    video = VideoManager(video_path, log_path)
                    video_len = len(video)
                    fps = video.fps
                    duration = int(video_len * 1000.0 / fps)
                    video_output_name = '{:0>8d}ms-{:0>8d}ms-visible.mp4'.format(0, duration)
                    video_output_path = os.path.join(frames_path, video_output_name)
                    shutil.copyfile(video_path, video_output_path)
                    # Get the label and save it
                    point_annotation = video.get_annotation_list()
                    prompt_annotation = video.get_annotation_prompt()
                    point_annotation_output_path = os.path.join(segmentation_path, 'labels.json')
                    prompt_annotation_output_path = os.path.join(segmentation_path, 'texts.json')
                    with open(point_annotation_output_path, 'w') as f:
                        data = json.dumps(point_annotation)
                        f.write(data)
                    with open(prompt_annotation_output_path, 'w') as f:
                        data = json.dumps(prompt_annotation)
                        f.write(data)
                    # Save visualization file
                    # video.set_highlighted(False)
                    # video.set_show_context(False)
                    # keyframe_list = video.get_keyframe_list()
                    # for keyframe in keyframe_list:
                    #     visible_output_name = 'visible_{:0>3d}.png'.format(keyframe)
                    #     visible_output_path = os.path.join(segmentation_path, visible_output_name)
                    #     cv2.imwrite(visible_output_path, video[keyframe, 0])
                pbar.update()


class CustomTitleBar(MSFluentTitleBar):
    """ Title bar with icon and title """
    LoadFile = pyqtSignal()
    AddFile = pyqtSignal()
    SaveLog = pyqtSignal()
    Clear = pyqtSignal()
    Export = pyqtSignal()
    PromptEditor = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)

        # add buttons
        self.toolButtonLayout = QHBoxLayout()
        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)
        self.dropDownButton = self.createDropDownButton(color)

        self.toolButtonLayout.setContentsMargins(20, 0, 20, 0)
        self.toolButtonLayout.setSpacing(15)
        self.toolButtonLayout.addWidget(self.dropDownButton)
        self.hBoxLayout.insertLayout(4, self.toolButtonLayout)

        # add setting button
        self.setting_button = TransparentToolButton(FIF.SETTING.icon(color=color), self)
        self.hBoxLayout.insertWidget(6, self.setting_button, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.insertSpacing(8, 20)

    def createDropDownButton(self, color):
        button = TransparentDropDownPushButton('Menu', self, FIF.MENU.icon(color=color))
        button.setFixedHeight(34)
        setFont(button, 12)

        menu = RoundMenu(parent=self)

        menu.addActions([
            Action(FIF.FOLDER.icon(color=color), 'Load...', triggered=self.LoadFile, shortcut=QKeySequence(QKeySequence.StandardKey.Open)),
            Action(FIF.FOLDER_ADD.icon(color=color), 'Add...', triggered=self.AddFile, shortcut='Ctrl+U'),
            Action(FIF.SAVE.icon(color=color), 'Save...', triggered=self.SaveLog, shortcut=QKeySequence(QKeySequence.StandardKey.Save)),
            Action(FIF.SHARE.icon(color=color), 'Export...', triggered=self.Export, shortcut='Ctrl+E'),
        ])
        menu.addSeparator()
        menu.addActions([
            Action(FIF.CANCEL.icon(color=color), 'Clear', triggered=self.Clear, shortcut='Delete'),
        ])
        menu.addSeparator()
        menu.addActions([
            QAction('Prompt Editor', triggered=self.PromptEditor, shortcut='Ctrl+P')
        ])
        button.setMenu(menu)
        return button


class MainWindow(MSFluentWindow):

    def __init__(self):
        self.isMicaEnabled = False
        self.onplay = False
        super().__init__()

        # Initialize the main frame of the form
        self.titleColumn = CustomTitleBar(self)
        self.setTitleBar(self.titleColumn)
        self.hBoxLayout.removeWidget(self.navigationInterface)
        # self.hBoxLayout.removeWidget(self.stackedWidget)
        self.main_framework = QWidget(self)
        self.main_framework.setContentsMargins(20, 10, 20, 20)
        self.stackedWidget.addWidget(self.main_framework)
        self.setWindowIcon(FIF.TILES.icon())
        # self.setWindowIcon(QIcon(':/qfluentwidgets/images/logo.png'))
        self.setWindowTitle('EVA')
        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(40, 40)
        # self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        # Constructing a text annotation form
        self.promptEditor = PromptEditor()

        # Build settings form
        self.settingPage = SettingPage()

        # Video Group Manager
        self.vBoxLayout = QVBoxLayout(self.main_framework)
        self.videoGroupManager = VideoGroupManager(self)
        self.vBoxLayout.addWidget(self.videoGroupManager)

        # Video Group Manager
        self.videoFramePlayer = VideoFramePlayer(self)
        self.vBoxLayout.addWidget(self.videoFramePlayer, stretch=0)

        # Annotation Manager
        self.viceLayout = QHBoxLayout()
        self.annotationIndicator = IndicatorPanel(self)
        self.licence = SubtitleLabel('Powered by: Polysulfone')
        self.licence.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.viceLayout.addWidget(self.annotationIndicator, stretch=3)
        self.viceLayout.addWidget(self.licence, stretch=1)
        self.vBoxLayout.addLayout(self.viceLayout)

        # Configuring signals and slots
        self.titleColumn.LoadFile.connect(self._load_video)
        self.titleColumn.AddFile.connect(self._add_video)
        self.titleColumn.SaveLog.connect(self._save_annotation)
        self.titleColumn.Clear.connect(self._annotation_canceled)
        self.titleColumn.Export.connect(self._export)
        self.titleColumn.PromptEditor.connect(self._open_prompt_widget)
        self.titleColumn.closeBtn.clicked.connect(self.promptEditor.close)
        self.titleColumn.setting_button.clicked.connect(self._open_setting_widget)

        self.videoGroupManager.VideoChanging.connect(self._save_annotation)
        self.videoGroupManager.VideoChanged.connect(self._video_changed)

        self.videoFramePlayer.FrameChanged.connect(self._frame_changed)
        self.videoFramePlayer.PlayBtnClicked.connect(self._toggle_play)
        self.videoFramePlayer.AnnotationLabeled.connect(self._annotation_labeled)
        self.videoFramePlayer.AnnotationCanceled.connect(self._annotation_canceled)
        self.videoFramePlayer.AnnotationSwitch.connect(self.annotationIndicator.switch_by_wheel)
        self.videoFramePlayer.AnnotationAutoFilled.connect(self._annotation_auto_filled)
        self.videoFramePlayer.VideoSwitch.connect(self.videoGroupManager.switch_by_wheel)

        self.annotationIndicator.AnnotationSelectiveChanged.connect(self._annotation_selective_changed)
        self.annotationIndicator.AnnotationSelectiveChanged.connect(self._load_annotation_for_prompt)
        self.annotationIndicator.AnnotationInserted.connect(self._annotation_inserted)
        self.annotationIndicator.AnnotationAppended.connect(self._annotation_appended)
        self.annotationIndicator.AnnotationDeleted.connect(self._annotation_deleted)

        self.promptEditor.VideoSwitch.connect(self.videoGroupManager.switch_by_wheel)
        self.promptEditor.KeyFrameSwitch.connect(self.videoFramePlayer.switch_by_mouse)
        self.promptEditor.AnnotationSwitch.connect(self.annotationIndicator.switch_by_wheel)
        # self.promptEditor.EditorSwitch.connect(self._save_annotation_for_prompt)
        # self.promptEditor.KeyFrameSwitch.connect(self._save_annotation_for_prompt)
        # self.promptEditor.AnnotationSwitch.connect(self._save_annotation_for_prompt)

        self.settingPage.SettingChanged.connect(self._save_setting)

        # Configure shortcut keys
        self.load_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Open), self)
        self.add_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        self.save_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Save), self)
        self.prompt_editor_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        self.export_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.clear_shortcut = QShortcut("Delete", self)

        self.up_shortcut = QShortcut(QKeySequence("UP"), self)
        self.down_shortcut = QShortcut(QKeySequence("DOWN"), self)
        self.left_shortcut = QShortcut(QKeySequence("LEFT"), self)
        self.right_shortcut = QShortcut(QKeySequence("RIGHT"), self)

        # Configure shortcut slot function
        self.load_shortcut.activated.connect(self._load_video)
        self.add_shortcut.activated.connect(self._add_video)
        self.save_shortcut.activated.connect(self._save_annotation)
        self.clear_shortcut.activated.connect(self._annotation_canceled)
        self.export_shortcut.activated.connect(self._export)
        self.prompt_editor_shortcut.activated.connect(self.promptEditor.show)

        self.up_shortcut.activated.connect(self._annotation_fix_up)
        self.down_shortcut.activated.connect(self._annotation_fix_down)
        self.left_shortcut.activated.connect(self._annotation_fix_left)
        self.right_shortcut.activated.connect(self._annotation_fix_right)

        self.prompt_delete_flag = False
        self.folder_path_list = []

        self.simplify_annotation_setting = 'Off'

    # Create a pop-up message
    def createWarningInfoBar(self, title, content):
        InfoBar.warning(
            title=title,
            content=content,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,  # disable close button
            position=InfoBarPosition.TOP_RIGHT,
            duration=10000,
            parent=self
        )

    def createSuccessInfoBar(self):
        # convenient class mothod
        InfoBar.success(
            title='Excellent',
            content="There is no error detected in the current frame!",
            orient=Qt.Orientation.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP_RIGHT,
            # position='Custom',   # NOTE: use custom info bar manager
            duration=2000,
            parent=self
        )

    # Load data
    def _load_video(self, folder_path=None):
        if folder_path is None:
            folder_path = QFileDialog.getExistingDirectory(None, "Select dataset folder")
        if folder_path:
            self.folder_path_list = [folder_path]
            self.videoGroupManager.load_dataset(folder_path)

    # Add data
    def _add_video(self, folder_path=None):
        if folder_path is None:
            folder_path = QFileDialog.getExistingDirectory(None, "Select dataset folder")
        if folder_path and (folder_path not in self.folder_path_list):
            self.folder_path_list.append(folder_path)
            self.videoGroupManager.add_dataset(folder_path)

    # Save annotation
    def _save_annotation(self):
        if self.videoGroupManager.dataset is None:
            return
        self._save_annotation_for_prompt()
        annotation_list = self.videoFramePlayer.get_all_annotation()
        annotation_prompt = self.videoFramePlayer.get_all_prompt_annotation()
        self.videoGroupManager.save_annotation_log(annotation_list, annotation_prompt)

    def _load_annotation_for_prompt(self):
        if not self.promptEditor.isEnabled():
            return
        if self.prompt_delete_flag:
            self.prompt_delete_flag = False
        else:
            self._save_annotation_for_prompt()
        frame_index = self.videoFramePlayer.current_frame
        annotation_index = self.videoFramePlayer.current_annotation
        video_name = self.videoGroupManager.get_current_video_name()
        annotation = self.videoFramePlayer.get_prompt_annotation(frame_index=frame_index, annotation_index=annotation_index)

        self.promptEditor.set_video_name(video_name)
        self.promptEditor.set_index(frame_index=frame_index, annotation_index=annotation_index)
        self.promptEditor.load_annotation(annotation=annotation)

    def _save_annotation_for_prompt(self):
        video_name = self.videoGroupManager.get_current_video_name()
        if video_name != self.promptEditor.get_video_name():
            return
        frame_index, annotation_index = self.promptEditor.get_index()
        annotation = self.promptEditor.get_annotation()
        if annotation is None:
            return
        self.videoFramePlayer.set_prompt_annotation(frame_index=frame_index, annotation_index=annotation_index, annotation=annotation)

    # Export
    def _export(self, output_path=None):
        if not len(self.folder_path_list):
            return
        exporter = Exporter(self.folder_path_list)
        if output_path is None:
            output_path = QFileDialog.getExistingDirectory(None, "Select output folder")
        if output_path:
            exporter.export(output_path)

    # Open Prompt Editor
    def _open_prompt_widget(self):
        self.promptEditor.show()

    # Open setting page
    def _open_setting_widget(self):
        auto_fill_setting = self.videoFramePlayer.get_auto_fill_setting()
        self.settingPage.show()
        self.settingPage.set_setting({'Auto Fill:': auto_fill_setting, 'Simplify Annotation:': self.simplify_annotation_setting})

    # Save setting
    def _save_setting(self, setting_dict):
        auto_fill_setting = setting_dict['Auto Fill:']
        self.videoFramePlayer.set_auto_fill_setting(auto_fill_setting)
        self.simplify_annotation_setting = setting_dict['Simplify Annotation:']
        if self.simplify_annotation_setting == 'On' and self.videoFramePlayer.current_frame:
            self.promptEditor.lock_for_save(True)
            self.annotationIndicator.lock_for_safe(True)
        else:
            self.promptEditor.lock_for_save(False)
            self.annotationIndicator.lock_for_safe(False)

    # Video change slot function
    def _video_changed(self, index):
        video_path, log_path = self.videoGroupManager[index]
        self.videoFramePlayer.load_video(video_path=video_path, log_path=log_path)
        # annotation = self.videoFramePlayer.get_annotation(0)
        # self.annotationIndicator.remake(react=False)
        # self.annotationIndicator.load_annotation_list(annotation)
        self.onplay = False

    # Frame change slot
    def _frame_changed(self, index):
        if self.videoFramePlayer.is_keyframe() and not self.onplay:
            if self.simplify_annotation_setting == 'On':
                self.promptEditor.lock_for_save(False)
                changed_list = self.videoFramePlayer.annotation_auto_fix(index)
                # print(changed_list)
                if len(changed_list):
                    for info in changed_list:
                        self.createWarningInfoBar(title=info['title'], content=info['content'])
                else:
                    self.createSuccessInfoBar()
            annotation = self.videoFramePlayer.get_annotation(index)
            self.annotationIndicator.load_annotation_list(annotation)
            self.promptEditor.set_able_or_not(True)
            if self.simplify_annotation_setting == 'On':
                if index:
                    self.promptEditor.lock_for_save(True)
                    self.annotationIndicator.lock_for_safe(True)
                else:
                    self.promptEditor.lock_for_save(False)
                    self.annotationIndicator.lock_for_safe(False)
        else:
            self.annotationIndicator.remake(react=False)
            self.promptEditor.set_able_or_not(False)

    # Play/Pause slot function
    def _toggle_play(self, flags):
        if self.videoGroupManager.dataset is None:
            return
        self.onplay = flags

    # Change the annotation point slot function
    def _annotation_selective_changed(self, index):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.set_current_annotation(index)

    # Add annotation point slot function
    def _annotation_appended(self):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.append_annotation()

    # Insert annotation point slot function
    def _annotation_inserted(self, index):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.insert_annotation(index)

    # Delete the marker slot function
    def _annotation_deleted(self, index):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.delete_annotation(index)
        self.prompt_delete_flag = True

    # Label slot function
    def _annotation_labeled(self, point):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.set_annotation(point=point)
        self.annotationIndicator.setLightStatus(status=LightStatus.LABELED)

    # Auto-fill slot function
    def _annotation_auto_filled(self, index):
        if self.videoGroupManager.dataset is None:
            return
        self.prompt_delete_flag = True
        self._frame_changed(index)

    # Annotation removal slot function
    def _annotation_canceled(self):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.cancel_annotation()
        self.annotationIndicator.setLightStatus(status=LightStatus.VACANT)

    # Fine-tuning slot function
    def _annotation_fix_up(self):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.fix_annotation(direction=1, step=1)

    def _annotation_fix_down(self):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.fix_annotation(direction=3, step=1)

    def _annotation_fix_left(self):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.fix_annotation(direction=0, step=1)

    def _annotation_fix_right(self):
        if self.videoGroupManager.dataset is None:
            return
        self.videoFramePlayer.fix_annotation(direction=2, step=1)


if __name__ == '__main__':
    # setTheme(Theme.DARK)

    app = QApplication(sys.argv)
    w = MainWindow()
    # w._load_video(folder_path='./data')
    w.show()
    sys.exit(app.exec())
