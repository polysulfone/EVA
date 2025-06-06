import sys
import os
import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QApplication, QWidget

from qfluentwidgets import (SubtitleLabel, Slider, SpinBox)


class DatasetLoader:
    def __init__(self, data_path):
        # Check the dataset
        sample_folder = os.path.join(data_path, 'classification')
        log_folder = os.path.join(data_path, 'log')
        assert os.path.exists(sample_folder)
        assert os.path.exists(log_folder)

        # Load videos
        video_list = []
        class_list = os.listdir(sample_folder)
        for class_index, sample_class in enumerate(class_list):
            class_path = os.path.join(sample_folder, sample_class)
            sample_list = os.listdir(class_path)
            for sample_index, sample in enumerate(sample_list):
                if sample[-3::] != 'mp4':
                    continue
                sample_path = os.path.join(class_path, sample)
                video_list.append({'video_name': os.path.join(sample_class, sample),
                                   'class_index': class_index,
                                   'sample_index': sample_index,
                                   'sample_class': sample_class,
                                   'sample_name': sample,
                                   'sample_path': sample_path,
                                   'data_path': data_path
                                   })

        self.video_list = video_list

    def __add__(self, other):
        if isinstance(other, DatasetLoader):
            self.video_list += other.video_list
            index_dict = {}
            for index, sample in enumerate(self.video_list):
                sample_name = sample['sample_class']
                if sample_name not in index_dict:
                    index_dict[sample_name] = {'class_index': sample['class_index'], 'sample_index': 0}
                else:
                    self.video_list[index]['class_index'] = index_dict[sample_name]['class_index']
                self.video_list[index]['sample_index'] = index_dict[sample_name]['sample_index']
                index_dict[sample_name]['sample_index'] += 1

        return self

    def __len__(self):
        return len(self.video_list)

    def __getitem__(self, index):
        return self.video_list[index]


class VideoGroupManager(QWidget):
    VideoChanged = pyqtSignal(int)
    VideoChanging = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.dataset = None

        self.current_video_index = 0

        self.videoNameLabel = SubtitleLabel('Video_Name')

        self.currentFrameEdit = SpinBox(self)
        self.currentFrameEdit.setAccelerated(True)
        self.currentFrameEdit.setMaximum(9999)
        self.currentFrameEdit.valueChanged.connect(self._switch_by_index)

        self.separatorLabel = SubtitleLabel("/")

        self.totalFrameLabel = SubtitleLabel('Video_num')

        self.progressBar = Slider(Qt.Orientation.Horizontal, self)
        # self.progressBar.setFixedWidth(200)
        self.progressBar.setMinimumWidth(200)
        self.progressBar.valueChanged.connect(self._switch_by_index)

        # layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        self.setFixedHeight(40)

        layout.addWidget(self.videoNameLabel, stretch=2)
        layout.addWidget(self.currentFrameEdit)
        layout.addWidget(self.separatorLabel)
        layout.addWidget(self.totalFrameLabel)
        layout.addWidget(self.progressBar, 4)

        self.setLayout(layout)

    def __len__(self):
        if self.dataset is None:
            return 0
        else:
            return len(self.dataset)

    def __getitem__(self, item):
        if self.dataset is None:
            return None
        else:
            sample_path = self.dataset[item]['sample_path']
            log_path = sample_path
            log_path = log_path.replace('classification', 'log')
            log_path = log_path.replace('.mp4', '.json')
            return sample_path, log_path

    def get_current_video_name(self):
        if self.dataset is None:
            return None
        else:
            return self.dataset[self.current_video_index]['video_name']

    def get_current_log_path(self):
        if self.dataset is None:
            return None
        else:
            sample_path = self.dataset[self.current_video_index]['sample_path']
            log_path = sample_path
            log_path = log_path.replace('classification', 'log')
            log_path = log_path.replace('.mp4', '.json')
            return log_path

    def load_dataset(self, data_path):

        self.dataset = DatasetLoader(data_path=data_path)
        self.current_video_index = 0
        video_name = self.dataset[0]['video_name']

        self.videoNameLabel.setText(video_name)
        self.progressBar.setMaximum(len(self) - 1)
        self._switch_by_index(0, react=False)
        self.currentFrameEdit.setMaximum(len(self) - 1)
        self.totalFrameLabel.setText(str(len(self) - 1))
        self.VideoChanged.emit(0)

    def add_dataset(self, data_path):
        new_dataset = DatasetLoader(data_path=data_path)
        self.dataset = self.dataset + new_dataset
        self.progressBar.setMaximum(len(self) - 1)
        self.currentFrameEdit.setMaximum(len(self) - 1)
        self.totalFrameLabel.setText(str(len(self) - 1))

    def switch_by_wheel(self, direction: bool):
        if direction and self.current_video_index > 0:
            self._switch_by_index(self.current_video_index - 1)
        elif not direction and self.current_video_index < len(self) - 1:
            self._switch_by_index(self.current_video_index + 1)

    def _switch_by_index(self, index, react=True):
        if self.dataset is None or index == self.current_video_index:
            return
        if react:
            self.VideoChanging.emit(index)
        self.current_video_index = index
        self.progressBar.setValue(index)
        self.currentFrameEdit.setValue(index)
        video_name = self.dataset[index]['video_name']
        self.videoNameLabel.setText(video_name)
        self.VideoChanged.emit(index)

    def save_annotation_log(self, annotation_log, prompt_log):
        data_path = self.dataset[self.current_video_index]['data_path']
        sample_class = self.dataset[self.current_video_index]['sample_class']
        sample_name = self.dataset[self.current_video_index]['sample_name']
        log_folder_path = os.path.join(data_path, 'log', sample_class)
        if not os.path.exists(log_folder_path):
            os.makedirs(log_folder_path)
        log_path = os.path.join(log_folder_path, sample_name)
        log_path = log_path.replace('.mp4', '.json')
        log_data = {'Tracking_Annotation': annotation_log, 'Text_Annotation': prompt_log}
        with open(log_path, 'w') as f:
            data = json.dumps(log_data)
            f.write(data)

    def save_location_log(self, location):
        pass


def video_changed(index):
    print('Switch to video{}'.format(index))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    video_manager = VideoGroupManager()
    video_manager.load_dataset('D:/python/ori_dataset/data1')
    video_manager.VideoChanged.connect(video_changed)
    video_manager.show()
    sys.exit(app.exec())
