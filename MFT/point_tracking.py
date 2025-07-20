import numpy as np

from MFT.utils import bilinear_sample

def convert_to_point_tracking(MFT_result, queries):
    """Convert MFT results to point-tracking results.

    args:
      MFT_result: MFT.results.FlowOUTrackingResult
      queries: (N xy) tensor with query coordinates on the init frame

    returns:
      current_coords: numpy array with coordinates in the current frame, shape (N, xy)
      current_occlusions: numpy array with occlusions in the current frame, shape (N, )
    """
    current_coords = MFT_result.warp_forward_points(queries)
    current_occlusions = bilinear_sample(np.expand_dims(MFT_result.occlusion, 0),
                                         np.expand_dims(queries, 0)).squeeze(0).squeeze(1)

    return current_coords, current_occlusions



