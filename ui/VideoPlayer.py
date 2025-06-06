import copy
import json
import sys, os
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QColor, QGuiApplication

from ui.VideoProgressBar import MarkerOverlay, VideoPlayBar

# Color of the visualization points (not important)
point_color = (255, 0, 0)
highlight_color = (0, 255, 0)


# Define annotation window
class LabelingWidget(QLabel):
    AutoFilled = pyqtSignal()
    Labeled = pyqtSignal(tuple)
    Canceled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        ori_frame = np.zeros((400, 800, 3), dtype=np.uint8)
        image = QImage(ori_frame.data, 800, 400, 2400, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            if modifiers == Qt.KeyboardModifier.NoModifier:
                pos = event.position()
                self.Labeled.emit((int(pos.x()), int(pos.y())))
            elif modifiers == Qt.KeyboardModifier.AltModifier:
                self.AutoFilled.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            self.Canceled.emit()


# Video management class
class VideoManager:
    def __init__(self, video_path, log_path):
        # 读取标注信息
        annotation_list = None
        annotation_prompt = None
        old_version = False
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r') as file:
                    log_data = json.load(file)
                if 'history' in [k for k, v in log_data.items()]:
                    annotation_list = log_data['history']
                    old_version = True
                else:
                    if 'Tracking_Annotation' in [k for k, v in log_data.items()]:
                        annotation_list = log_data['Tracking_Annotation']
                    if 'Text_Annotation' in [k for k, v in log_data.items()]:
                        annotation_prompt = log_data['Text_Annotation']
            except:
                pass

        # Get video frames
        video = cv2.VideoCapture(video_path)
        assert video is not None
        video_fps = int(video.get(cv2.CAP_PROP_FPS))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))

        # Get len
        video_len = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        s = False
        while not s:
            video_len -= 1
            video.set(cv2.CAP_PROP_POS_FRAMES, video_len)
            s, _ = video.read()
        video_len += 1

        # Get keyframes list
        keyframes_list = []
        for i in range(video_len):
            if i % 30 == 0 or i == video_len - 1:
                keyframes_list.append(i)

        # Initialize annotation list
        if annotation_list is None:
            annotation_list = {}
            for keyframe_index in keyframes_list:
                annotation_list[str(keyframe_index)] = [None]

        if annotation_prompt is None:
            annotation_prompt = {}
            for keyframe_index in keyframes_list:
                annotation_prompt[str(keyframe_index)] = [None]

        for k, v in annotation_list.items():
            while len(annotation_prompt[k]) < len(annotation_list[k]):
                annotation_prompt[k].append(None)

        # Calculate size scaling
        ori_size = [height, width]
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        # screen_width = win32api.GetSystemMetrics(0)
        # screen_height = win32api.GetSystemMetrics(1)
        scaling = min(screen_width / width / 1.5, screen_height * 1.0 / height) * 0.9
        height = int(height * scaling)
        width = int(width * scaling)
        scaling_size = [height, width]
        scaling = height * 1.0 / ori_size[0]

        scaling_ = 1
        if old_version:
            screen_width = 1707
            screen_height = 1067
            scaling_ = min(screen_width / width / 1.5, screen_height * 1.0 / height) * 0.9
            height_ = int(height * scaling_)
            scaling_ = height_ * 1.0 / ori_size[0]
            annotation_list_fix = {}
            for k, v in annotation_list.items():
                annotation_fix = []
                for pt in v:
                    if pt is None:
                        annotation_fix.append(None)
                    else:
                        annotation_fix.append([int(pt[0] // scaling_), int(pt[1] // scaling_)])
                annotation_list_fix[k] = annotation_fix
            annotation_list = annotation_list_fix

        # Define class attributes
        self.video = video
        self.fps = video_fps
        self.ori_size = ori_size
        self.scaling_size = scaling_size
        self.scaling = scaling
        self.scaling_ = scaling_
        self.scaling_fix = scaling
        self.video_len = video_len
        self.log_path = log_path

        # Annotation information
        self.keyframes_list = keyframes_list
        self.annotation_list = annotation_list
        self.annotation_prompt = annotation_prompt

        # Location information
        self.selective_point = 0
        self.current_frame = 0

        # Setting information
        self.show_label = True
        self.show_context = True
        self.show_frame_index = True
        self.show_annotation_index = True
        self.highlighted = True

    def reset_scaling(self):
        height = self.ori_size[0]
        width = self.ori_size[1]
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        if self.show_context:
            scaling = min(screen_width / width / 1.5, screen_height * 1.0 / height) * 0.9
        else:
            scaling = min(screen_width * 1.0 / width, screen_height * 1.0 / height) * 0.9
        height = int(height * scaling)
        width = int(width * scaling)
        scaling_size = [height, width]
        scaling = height * 1.0 / self.ori_size[0]
        self.scaling = scaling
        self.scaling_size = scaling_size
        self.scaling_fix = scaling

    # Input
    def set_show_label(self, show_label: bool):
        self.show_label = show_label

    def set_show_context(self, show_context: bool):
        ori_flag = self.show_context
        self.show_context = show_context
        if ori_flag != show_context:
            self.reset_scaling()

    def set_show_frame_index(self, show_frame_index: bool):
        self.show_frame_index = show_frame_index

    def set_show_annotation_index(self, show_annotation_index: bool):
        self.show_annotation_index = show_annotation_index

    def set_highlighted(self, highlighted: bool):
        self.highlighted = highlighted

    def annotation_insert(self, frame_index, annotation_index):
        annotation = self.annotation_list[str(frame_index)]
        annotation.insert(annotation_index, None)
        self.annotation_list[str(frame_index)] = annotation
        annotation = self.annotation_prompt[str(frame_index)]
        annotation.insert(annotation_index, None)
        self.annotation_prompt[str(frame_index)] = annotation

    def annotation_append(self, frame_index):
        annotation = self.annotation_list[str(frame_index)]
        annotation.append(None)
        self.annotation_list[str(frame_index)] = annotation
        annotation = self.annotation_prompt[str(frame_index)]
        annotation.append(None)
        self.annotation_prompt[str(frame_index)] = annotation

    def annotation_delete(self, frame_index, annotation_index):
        annotation = self.annotation_list[str(frame_index)]
        annotation.pop(annotation_index)
        self.annotation_list[str(frame_index)] = annotation
        annotation = self.annotation_prompt[str(frame_index)]
        annotation.pop(annotation_index)
        self.annotation_prompt[str(frame_index)] = annotation

    def set_annotation(self, frame_index, annotation_index, point):
        annotation = self.annotation_list[str(frame_index)]
        annotation[annotation_index] = (point[0] // self.scaling, point[1] // self.scaling)
        self.annotation_list[str(frame_index)] = annotation

    def set_prompt_annotation(self, frame_index, annotation_index, annotation):
        annotations = self.annotation_prompt[str(frame_index)]
        while annotation_index > len(annotations) - 1:
            annotations.append(None)
        annotations[annotation_index] = annotation
        self.annotation_prompt[str(frame_index)] = annotations

    def auto_fill(self, frame_index, auto_fill_setting):
        if auto_fill_setting == 'From first frame':
            self.annotation_list[str(frame_index)] = copy.deepcopy(self.annotation_list['0'])
            self.annotation_prompt[str(frame_index)] = copy.deepcopy(self.annotation_prompt['0'])
        elif auto_fill_setting == 'From previous frame':
            keyframe_index = self.keyframes_list[self.keyframes_list.index(frame_index) - 1]
            self.annotation_list[str(frame_index)] = copy.deepcopy(self.annotation_list[str(keyframe_index)])
            self.annotation_prompt[str(frame_index)] = copy.deepcopy(self.annotation_prompt[str(keyframe_index)])

    def annotation_auto_fix(self, frame_index):
        keyframe_list = self.keyframes_list
        if frame_index not in keyframe_list or frame_index == 0:
            return []
        point_annotation_list = self.annotation_list
        prompt_annotation_list = self.annotation_prompt
        changed_list = []

        # Point num fix
        try:
            point_num = len(point_annotation_list['0'])
        except:
            point_num = 0
        if point_num:
            ori_point_annotation = point_annotation_list['0']
            now_point_annotation = point_annotation_list[str(frame_index)]
            # Remove
            while len(ori_point_annotation) < len(now_point_annotation):
                self.annotation_delete(frame_index=frame_index, annotation_index=len(now_point_annotation) - 1)
                changed_list.append(
                    {'title': '[Point num fix]Frame{}:'.format(frame_index), 'content': 'remove a point'})
            # Append
            while len(ori_point_annotation) > len(now_point_annotation):
                self.annotation_append(frame_index)
                changed_list.append(
                    {'title': '[Point num fix]Frame{}:'.format(frame_index), 'content': 'append a point'})
        self.annotation_list = point_annotation_list

        # Prompt fix
        prompt_fix_flag = False
        try:
            prompt_num = len(prompt_annotation_list['0'])
        except:
            prompt_num = 0
        if prompt_num:
            for point_index in range(len(prompt_annotation_list[str(frame_index)])):
                # Prompt fix
                prompt_annotation = prompt_annotation_list[str(frame_index)][point_index]
                if prompt_annotation:
                    # Check other prompt
                    for k, v in prompt_annotation_list['0'][point_index].items():
                        if k == 'status':
                            continue
                        if k not in prompt_annotation:
                            prompt_fix_flag = True
                            changed_list.append(
                                {'title': '[Prompt fix]Frame{}/Point{}:'.format(frame_index, point_index),
                                 'content': 'Append[{}]'.format(k)})
                        elif prompt_annotation[k] != v:
                            prompt_fix_flag = True
                            changed_list.append(
                                {'title': '[Prompt fix]Frame{}/Point{}:'.format(frame_index, point_index),
                                 'content': 'Modify[{}][{}]->[{}]'.format(k, prompt_annotation[k], v)})

                    for k, v in prompt_annotation.items():
                        if k not in prompt_annotation_list['0'][point_index]:
                            prompt_fix_flag = True
                            changed_list.append(
                                {'title': '[Prompt fix]Frame{}/Point{}:'.format(frame_index, point_index),
                                 'content': 'Remove[{}]'.format(k)})
                    if prompt_fix_flag:
                        # Reserve status
                        status = None
                        if prompt_annotation:
                            if 'status' in prompt_annotation:
                                status = prompt_annotation['status']
                        prompt_annotation_list[str(frame_index)][point_index] = prompt_annotation_list['0'][point_index]
                        prompt_annotation_list[str(frame_index)][point_index]['status'] = status
        self.annotation_prompt = prompt_annotation_list

        return changed_list

    def fix_annotation(self, frame_index, annotation_index, direction, step):
        def clamp(val, min_val, max_val):
            return max(min_val, min(val, max_val))

        point = self.annotation_list[str(frame_index)][annotation_index]
        if point is None:
            return
        x = x_fix = point[0]
        y = y_fix = point[1]
        if direction == 0:
            x_fix -= step
        elif direction == 1:
            y_fix -= step
        elif direction == 2:
            x_fix += step
        elif direction == 3:
            y_fix += step
        x_fix = clamp(x_fix, 0, self.ori_size[1] - 1)
        y_fix = clamp(y_fix, 0, self.ori_size[0] - 1)
        if x != x_fix or y != y_fix:
            point_fix = [x_fix, y_fix]
            self.annotation_list[str(frame_index)][annotation_index] = point_fix

    def cancel_annotation(self, frame_index, annotation_index):
        annotation = self.annotation_list[str(frame_index)]
        annotation[annotation_index] = None
        self.annotation_list[str(frame_index)] = annotation

    # Output
    def get_annotation(self, frame_index: int):
        try:
            return self.annotation_list[str(frame_index)]
        except:
            return None

    def get_prompt_annotation(self, frame_index, annotation_index):
        try:
            prompt_annotation = self.annotation_prompt[str(frame_index)][annotation_index]
        except:
            prompt_annotation = None
        return prompt_annotation

    def get_annotation_list(self):
        return self.annotation_list

    def get_annotation_prompt(self):
        return self.annotation_prompt

    def get_keyframe_list(self):
        return self.keyframes_list

    # Get len
    def __len__(self):
        return self.video_len

    # Get a black frame
    def get_black_frame(self):
        return np.zeros((self.scaling_size[0], self.scaling_size[1], 3), dtype=np.uint8)

    # Get original frame
    def get_origin_frame(self, index):
        self.video.set(cv2.CAP_PROP_POS_FRAMES, index)
        _, frame = self.video.read()
        assert frame is not None
        return frame

    # Get pure frame
    def get_pure_frame(self, index):
        frame = self.get_origin_frame(index)
        frame = cv2.resize(frame, (self.scaling_size[1], self.scaling_size[0]))
        return frame

    # Get labeled frame
    def get_labeled_frame(self, index, only_inner_circle=False):
        # 判断是否为标注帧
        is_keyframe = index in self.keyframes_list
        if not is_keyframe:
            return self.get_pure_frame(index)
        # 标注帧
        frame = self.get_pure_frame(index)
        try:
            annotation = self.annotation_list[str(index)]
        except:
            return frame
        scaling = self.scaling
        for pt in annotation:
            if pt is not None:
                pt = (int(pt[0] * scaling), int(pt[1] * scaling))
                cv2.circle(frame, pt, 3, point_color, 1)
                if not only_inner_circle:
                    cv2.circle(frame, pt, 8, point_color, 2)
        return frame

    # Get highlighted frame
    def get_highlighted_labeled_frame(self, frame_index, annotation_index, only_inner_circle=False, inner_size=4):

        is_keyframe = frame_index in self.keyframes_list
        if not is_keyframe:
            return self.get_pure_frame(frame_index)

        frame = self.get_pure_frame(frame_index)
        try:
            annotation = self.annotation_list[str(frame_index)]
        except:
            return frame
        scaling = self.scaling
        for index, pt in enumerate(annotation):
            if pt is not None:
                pt = (int(pt[0] * scaling), int(pt[1] * scaling))
                if index == annotation_index:
                    cv2.circle(frame, pt, inner_size, highlight_color, 1)
                    if not only_inner_circle:
                        cv2.circle(frame, pt, 10, highlight_color, 2)
                else:
                    cv2.circle(frame, pt, 3, point_color, 1)
                    if not only_inner_circle:
                        cv2.circle(frame, pt, 8, point_color, 2)
        return frame

    # Get zoomin frame
    def get_zoomin_frame(self, frame_index, annotation_index, zoom_scale=5):

        is_keyframe = frame_index in self.keyframes_list
        if not is_keyframe:
            return self.get_black_frame()

        scaling = self.scaling
        frame = self.get_highlighted_labeled_frame(frame_index, annotation_index, only_inner_circle=True, inner_size=2)
        try:
            annotation = self.annotation_list[str(frame_index)][annotation_index]
        except:
            return self.get_black_frame()
        if annotation is None:
            return self.get_black_frame()
        annotation_fix = (int(annotation[0] * scaling), int(annotation[1] * scaling))
        # Calculate the clipping size
        append_height = int(1.0 * self.scaling_size[0] / zoom_scale / 2)
        append_width = int(1.0 * self.scaling_size[1] / zoom_scale / 2)
        # Determine the cropping position
        x_left = annotation_fix[0] - append_width
        x_right = annotation_fix[0] + append_width + 1
        y_up = annotation_fix[1] - append_height
        y_down = annotation_fix[1] + append_height + 1
        # Correct the clipping position
        if x_left < 0:
            x_right -= x_left
            x_left = 0
        if x_right > self.scaling_size[1]:
            fix = x_right - self.scaling_size[1]
            x_left -= fix
            x_right -= fix
        if y_up < 0:
            y_down -= y_up
            y_up = 0
        if y_down > self.scaling_size[0]:
            fix = y_down - self.scaling_size[0]
            y_up -= fix
            y_down -= fix
        # Crop picture
        crop_frame = frame[y_up:y_down, x_left:x_right]
        crop_frame = cv2.resize(crop_frame, (self.scaling_size[1], self.scaling_size[0]))
        return crop_frame

    # Get the initial frame of the marker
    def get_begin_frame_index(self, annotation_index):
        frame_index = None
        for index in self.keyframes_list:
            try:
                annotation = self.annotation_list[str(index)]
                if annotation is not None:
                    frame_index = index
                    break
            except:
                continue
        return frame_index

    # Get display updates, where index should be a tuple of length 2
    def __getitem__(self, index):
        frame_index = index[0]
        if frame_index < 0:
            frame_index += len(self)
        annotation_index = index[1]
        # Determine whether it is a marked frame
        is_keyframe = (frame_index in self.keyframes_list)
        if not self.show_label:
            frame = self.get_pure_frame(frame_index)
            if self.show_frame_index:
                frame = cv2.putText(frame, str(frame_index), (0 + 20, 0 + 40), cv2.FONT_HERSHEY_SIMPLEX,
                                    1, (0, 0, 255), 2)
        elif self.show_context:
            # Get main screen
            if self.highlighted:
                frame_main = self.get_highlighted_labeled_frame(frame_index=frame_index,
                                                                annotation_index=annotation_index)
            else:
                frame_main = self.get_labeled_frame(frame_index)
            if self.show_frame_index:
                frame_main = cv2.putText(frame_main, str(frame_index), (0 + 20, 0 + 40), cv2.FONT_HERSHEY_SIMPLEX,
                                         1, (0, 0, 255), 2)
            if self.show_annotation_index and is_keyframe:
                frame_main = cv2.putText(frame_main, str(annotation_index), (0 + 20, self.scaling_size[0] - 20),
                                         cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            # Get the first valid annotation frame
            frame_beg_index = self.get_begin_frame_index(annotation_index=annotation_index)
            if frame_beg_index is not None:
                frame_beg = self.get_zoomin_frame(frame_index=frame_beg_index, annotation_index=annotation_index)
            else:
                frame_beg = self.get_black_frame()
            # Get the current frame annotation information
            frame_now = self.get_zoomin_frame(frame_index=frame_index, annotation_index=annotation_index)
            concat_frame = cv2.vconcat([frame_beg, frame_now])
            concat_frame = cv2.resize(concat_frame, (self.scaling_size[1] // 2, self.scaling_size[0]))
            frame = cv2.hconcat([frame_main, concat_frame])
        else:
            if self.highlighted:
                frame = self.get_highlighted_labeled_frame(frame_index=frame_index, annotation_index=annotation_index)
            else:
                frame = self.get_labeled_frame(index=frame_index)
            if self.show_frame_index:
                frame = cv2.putText(frame, str(frame_index), (0 + 20, 0 + 40), cv2.FONT_HERSHEY_SIMPLEX,
                                    1, (0, 0, 255), 2)
            if self.show_annotation_index:
                frame = cv2.putText(frame, str(annotation_index), (0 + 20, self.scaling_size[0] - 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame


# Video playback class
class VideoFramePlayer(QWidget):
    PlayBtnClicked = pyqtSignal(bool)

    FrameChanged = pyqtSignal(int)
    AnnotationAutoFilled = pyqtSignal(int)
    AnnotationLabeled = pyqtSignal(tuple)
    AnnotationCanceled = pyqtSignal()

    FrameSwitch = pyqtSignal(bool)
    KeyFrameSwitch = pyqtSignal(bool)
    AnnotationSwitch = pyqtSignal(bool)
    VideoSwitch = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.video = None
        self.current_frame = 0
        self.current_annotation = 0
        self.auto_fill_setting = 'From previous frame'

        self.FrameSwitch.connect(self.switch_by_mouse)
        self.KeyFrameSwitch.connect(self.switch_by_mouse)

        # Define timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._next_frame)

        # Initialize video box
        self.monitor = LabelingWidget()
        self.monitor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # ori_frame = np.zeros((600, 800, 3), dtype=np.uint8)
        # image = QImage(ori_frame.data, 800, 600, 2400, QImage.Format.Format_RGB888)
        # pixmap = QPixmap.fromImage(image)
        # self.label.setPixmap(pixmap)

        self.videoPlayBar = VideoPlayBar(self)
        self.keyframeIndicator = MarkerOverlay(self, jump_callback=self._switch_by_marker)

        # Defining signals and slots
        self.videoPlayBar.playBtn.clicked.connect(self._toggle_play)
        self.videoPlayBar.progressSlider.valueChanged.connect(self.check_button)
        self.videoPlayBar.progressSlider.valueChanged.connect(self._switch_by_slider)
        self.videoPlayBar.preBtn.clicked.connect(self._switch_backward)
        self.videoPlayBar.nextBtn.clicked.connect(self._switch_forward)
        self.monitor.Labeled.connect(self._label_at)
        self.monitor.Canceled.connect(self._label_cancel)
        self.monitor.AutoFilled.connect(self._label_auto_filled)

        self.mainLayout = QVBoxLayout()
        self.frameLayout = QHBoxLayout()
        self.frameLayout.addStretch(1)
        self.frameLayout.addWidget(self.monitor, stretch=0)
        self.frameLayout.addStretch(1)
        self.mainLayout.addStretch(1)
        self.mainLayout.addLayout(self.frameLayout)
        self.mainLayout.addStretch(1)

        # Add the slider first, then insert the markerOverlay
        self.mainLayout.addWidget(self.keyframeIndicator)
        self.mainLayout.addWidget(self.videoPlayBar)

        self.setLayout(self.mainLayout)

    # Reinitialize the form
    def reinit(self):
        self.pause_play()
        if self.current_frame == 0:
            self.FrameChanged.emit(0)
        else:
            self.videoPlayBar.set_frames_progress(0)
            self.current_frame = 0
        self.current_annotation = 0
        self.check_button()

    # Get the current video length
    def __len__(self):
        if self.video is None:
            return 0
        else:
            return len(self.video)

    def __getitem__(self, item):
        if self.video is None:
            return None
        else:
            return self.video[item]

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        modifiers = event.modifiers()
        # Roll up
        if delta > 0:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.FrameSwitch.emit(True)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.KeyFrameSwitch.emit(True)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.VideoSwitch.emit(True)
            elif modifiers == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                self.AnnotationSwitch.emit(True)
        # Roll down
        elif delta < 0:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                self.FrameSwitch.emit(False)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.KeyFrameSwitch.emit(False)
            elif modifiers == Qt.KeyboardModifier.ControlModifier:
                self.VideoSwitch.emit(False)
            elif modifiers == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier):
                self.AnnotationSwitch.emit(False)

    def set_current_frame(self, index):
        self.current_frame = index
        self.videoPlayBar.set_frames_progress(index)

    def set_current_annotation(self, index):
        self.current_annotation = index
        self.update_frame()

    def get_prompt_annotation(self, frame_index, annotation_index):
        return self.video.get_prompt_annotation(frame_index=frame_index, annotation_index=annotation_index)

    # Set the video that is currently playing in the form
    def load_video(self, video_path, log_path):
        self.video = VideoManager(video_path=video_path, log_path=log_path)
        self.videoPlayBar.set_frames_num(len(self) - 1)
        self.keyframeIndicator.remake(keyframe_list=self.video.get_keyframe_list(),
                                      progress_bar_len=self.videoPlayBar.get_slider_width())
        self.reinit()
        self.update_frame()

    # Set video playback format
    def set_show_label(self, show_label: bool):
        self.video.set_show_label(show_label)

    def set_show_context(self, show_context: bool):
        self.video.set_show_context(show_context)

    def set_show_frame_index(self, show_frame_index: bool):
        self.video.set_show_frame_index(show_frame_index)

    def set_show_annotation_index(self, show_annotation_index: bool):
        self.video.set_show_annotation_index(show_annotation_index)

    def set_highlighted(self, highlighted: bool):
        self.video.set_highlighted(highlighted)

    def set_video_format(self, show_label: bool, show_context: bool, show_frame_index: bool,
                         show_annotation_index: bool, highlighted: bool):
        if self.video is not None:
            self.video.set_show_label(show_label)
            self.video.set_show_context(show_context)
            self.video.set_show_frame_index(show_frame_index)
            self.video.set_show_annotation_index(show_annotation_index)
            self.video.set_highlighted(highlighted)

    def is_keyframe(self):
        if self.current_frame in self.video.get_keyframe_list():
            return True
        else:
            return False

    # Check frame position and enable or disable buttons
    def check_button(self):
        if self.current_frame == 0:
            self.videoPlayBar.preBtn.setEnabled(False)
        else:
            self.videoPlayBar.preBtn.setEnabled(True)
        if self.current_frame == len(self) - 1:
            self.videoPlayBar.nextBtn.setEnabled(False)
        else:
            self.videoPlayBar.nextBtn.setEnabled(True)

    # Update progress bar information
    def update_progress(self):
        if self.video is None:
            return
        self.videoPlayBar.set_frames_progress(self.current_frame)

    # Set playback frame
    def update_frame(self):
        if self.video is None:
            return
        frame = self[self.current_frame, self.current_annotation]
        height, width, c = frame.shape
        image = QImage(frame.data, width, height, c * width, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(image)
        self.monitor.setPixmap(pixmap)

    # Continue playing, for play button
    def continue_play(self):
        if self.videoPlayBar.get_slider_value() == len(self) - 1:
            self.current_frame = 0
            self.videoPlayBar.set_frames_progress(self.current_frame)
        self.timer.start()
        # self.set_show_label(False)
        self.set_show_annotation_index(False)
        self.videoPlayBar.playBtn.setPlay(True)
        self.PlayBtnClicked.emit(True)

    # Pause
    def pause_play(self):
        self.timer.stop()
        self.set_show_annotation_index(True)
        self.videoPlayBar.playBtn.setPlay(False)
        self.PlayBtnClicked.emit(False)

    # Play button slot function
    def _toggle_play(self):
        if self.video is not None:
            if self.timer.isActive():
                self.pause_play()
            else:
                self.continue_play()

    # Timer slot function
    def _next_frame(self):
        if self.current_frame >= len(self) - 1:
            self.timer.stop()
            self.set_show_annotation_index(True)
            self.videoPlayBar.playBtn.setPlay(False)
            return
        self.current_frame += 1
        self.videoPlayBar.set_frames_progress(self.current_frame)

    # Switch frames forward and backward
    def switch_by_offset(self, direction: bool, step: int):
        # Switch backward
        if direction:
            if self.current_frame > 0:
                if self.current_frame - step >= 0:
                    self.current_frame -= step
                else:
                    self.current_frame = 0
                self.update_progress()
        # Switch forward
        else:
            if self.current_frame < len(self) - 1:
                if self.current_frame + step <= len(self) - 1:
                    self.current_frame += step
                else:
                    self.current_frame = len(self) - 1
                self.update_progress()

    # Mouse switching slot function
    def switch_by_mouse(self, direction: bool):
        if direction:
            self._switch_backward()
        else:
            self._switch_forward()

    # Forward key slot function
    def _switch_backward(self):
        if self.video is None or self.current_frame == 0:
            return
        self.pause_play()
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.NoModifier:
            self.switch_by_offset(direction=True, step=1)
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            keyframe_list = self.video.get_keyframe_list()
            is_keyframe = self.current_frame in keyframe_list
            if is_keyframe:
                self.current_frame = keyframe_list[keyframe_list.index(self.current_frame) - 1]
            else:
                for index, keyframe_index in enumerate(keyframe_list):
                    if keyframe_index > self.current_frame:
                        self.current_frame = keyframe_list[index - 1]
                        break
            self.update_progress()

    # Backward Key Slot Function
    def _switch_forward(self):
        if self.video is None or self.current_frame == len(self) - 1:
            return
        self.pause_play()
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.NoModifier:
            self.switch_by_offset(direction=False, step=1)
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            keyframe_list = self.video.get_keyframe_list()
            is_keyframe = self.current_frame in keyframe_list
            if is_keyframe:
                self.current_frame = keyframe_list[keyframe_list.index(self.current_frame) + 1]
            else:
                for index, keyframe_index in enumerate(keyframe_list):
                    if keyframe_index > self.current_frame:
                        self.current_frame = keyframe_list[index]
                        break
            self.update_progress()

    # Slider slot function
    def _switch_by_slider(self, value: int):
        if self.video is None:
            return
        self.current_frame = value
        self.FrameChanged.emit(self.current_frame)
        self.update_frame()

    # Keyframe indicator slot function
    def _switch_by_marker(self, index):
        if self.video is None:
            return
        self.pause_play()
        self.current_frame = index
        self.update_progress()

    # Get auto-fill settings
    def get_auto_fill_setting(self):
        return self.auto_fill_setting

    # Set auto-fill
    def set_auto_fill_setting(self, auto_fill_setting):
        self.auto_fill_setting = auto_fill_setting

    # Auto Fill
    def _label_auto_filled(self):
        if self.video is None:
            return
        if self.current_frame == 0:
            return
        keyframe_list = self.video.get_keyframe_list()
        if self.current_frame not in keyframe_list:
            return
        self.video.auto_fill(self.current_frame, self.auto_fill_setting)
        self.update_frame()
        self.AnnotationAutoFilled.emit(self.current_frame)

    # Simplify annotation
    def annotation_auto_fix(self, index):
        changed_list = self.video.annotation_auto_fix(index)
        return changed_list

    # Mark point slot function
    def _label_at(self, point: tuple):
        if self.video is None:
            return
        keyframe_list = self.video.get_keyframe_list()
        is_keyframe = self.current_frame in keyframe_list
        if not is_keyframe:
            return
        valid_width = self.video.scaling_size[1]
        valid_height = self.video.scaling_size[0]
        if point[0] >= valid_width or point[1] >= valid_height:
            return
        self.AnnotationLabeled.emit(point)
        # print(point)

    # Unannotate slot function
    def _label_cancel(self):
        if self.video is None:
            return
        keyframe_list = self.video.get_keyframe_list()
        is_keyframe = self.current_frame in keyframe_list
        if not is_keyframe:
            return
        self.AnnotationCanceled.emit()
        # print('Cancel')

    # Get all labels
    def get_all_annotation(self):
        if self.video is None:
            return None
        else:
            return self.video.get_annotation_list()

    def get_all_prompt_annotation(self):
        if self.video is None:
            return None
        else:
            return self.video.get_annotation_prompt()

    def get_annotation(self, index):
        return self.video.get_annotation(index)

    def insert_annotation(self, index):
        self.video.annotation_insert(frame_index=self.current_frame, annotation_index=index)
        self.update_frame()

    def append_annotation(self):
        self.video.annotation_append(frame_index=self.current_frame)
        self.update_frame()

    def delete_annotation(self, index):
        self.video.annotation_delete(frame_index=self.current_frame, annotation_index=index)
        self.update_frame()

    def set_annotation(self, point):
        self.video.set_annotation(frame_index=self.current_frame, annotation_index=self.current_annotation, point=point)
        self.update_frame()

    def set_prompt_annotation(self, frame_index, annotation_index, annotation):
        self.video.set_prompt_annotation(frame_index=frame_index, annotation_index=annotation_index,
                                         annotation=annotation)

    def fix_annotation(self, direction, step):
        self.video.fix_annotation(frame_index=self.current_frame, annotation_index=self.current_annotation,
                                  direction=direction, step=step)
        self.update_frame()

    def cancel_annotation(self):
        self.video.cancel_annotation(frame_index=self.current_frame, annotation_index=self.current_annotation)
        self.update_frame()

    # General function
    def resizeEvent(self, event):
        super().resizeEvent(event)
        slider_width = self.videoPlayBar.get_slider_width()
        self.keyframeIndicator.resize(progress_bar_len=slider_width)

    def closeEvent(self, event):
        if self.video is not None:
            del self.video
        event.accept()


# Test
def labeled(pt):
    print('Label at{}'.format(pt))


def cancel():
    print('Cancel')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = QWidget()
    layout = QVBoxLayout(widget)
    video_player = VideoFramePlayer(widget)
    video_player.load_video(video_path='D:/python/ori_dataset/data3/classification/Deformation/1 (1).mp4',
                            log_path='D:/python/ori_dataset/data3/log/Deformation/1 (1).json')
    video_player.set_current_frame(60)
    video_player.set_current_annotation(1)
    # video_player.set_show_context(False)
    # cv2.imshow('test', video_player[0, 0])
    video_player.update_frame()
    video_player.AnnotationLabeled.connect(labeled)
    video_player.AnnotationCanceled.connect(cancel)

    layout.addWidget(video_player)
    widget.show()

    sys.exit(app.exec())

    # video = VideoManager(video_path='D:/python/ori_dataset/data3/classification/Deformation/1 (1).mp4',
    #                      log_path='D:/python/ori_dataset/data3/log/Deformation/1 (1).json')
    # # video.set_highlighted(True)
    # for i in range(35):
    #     cv2.imshow('test', video[i, 0])
    #     cv2.waitKey()
    # video.set_show_context(False)
    # cv2.imshow('test', video[-1, 0])
    # cv2.waitKey()
