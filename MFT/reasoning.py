from MFT.MFT import MFT
from MFT.point_tracking import convert_to_point_tracking


class MFT_Reasoner:

    def __init__(self, init_frame, queries, checkpoint_path, device='cuda'):
        self.tracker = MFT(checkpoint_path=checkpoint_path, device=device)
        self.queries = queries

        self.tracker.init(init_frame)

    def compute_next(self, frame):
        meta = self.tracker.track(frame)
        coords, occlusions = convert_to_point_tracking(meta.result, self.queries)
        return coords, occlusions
