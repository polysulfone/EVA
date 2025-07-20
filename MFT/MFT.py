# -*- origami-fold-style: triple-braces; coding: utf-8; -*-
import numpy as np
from types import SimpleNamespace
import logging

from MFT.raft import RAFTWrapper
from MFT.results import FlowOUTrackingResult

logger = logging.getLogger(__name__)

deltas = [np.inf, 1, 2, 4, 8, 16, 32]


class MFT():
    def __init__(self, checkpoint_path, device):
        """Create MFT tracker
        args:
          config: a MFT.config.Config, for example from configs/MFT_cfg.py"""
        self.flower = RAFTWrapper(checkpoint_path=checkpoint_path, device=device)  # init the OF
        self.device = device

    def init(self, img, start_frame_i=0, time_direction=1):
        """Initialize MFT on first frame

        args:
          img: opencv image (numpy uint8 HxWxC array with B, G, R channel order)
          start_frame_i: [optional] init frame number (used for caching)
          time_direction: [optional] forward = +1, or backward = -1 (used for caching)
          flow_cache: [optional] MFT.utils.io.FlowCache (for caching OF on GPU, RAM, or SSD)
          kwargs: [unused] - for compatibility with other trackers

        returns:
          meta: initial frame result container, with initial (zero-motion) MFT.results.FlowOUTrackingResult in meta.result 
        """
        self.img_H, self.img_W = img.shape[:2]
        self.start_frame_i = start_frame_i
        self.current_frame_i = self.start_frame_i
        assert time_direction in [+1, -1]
        self.time_direction = time_direction

        self.memory = {
            self.start_frame_i: {
                'img': img,
                'result': FlowOUTrackingResult.identity((self.img_H, self.img_W))
            }
        }

        self.template_img = img.copy()

        meta = SimpleNamespace()
        meta.result = self.memory[self.start_frame_i]['result'].clone()
        return meta

    def track(self, input_img):
        """Track one frame

        args:
          input_img: opencv image (numpy uint8 HxWxC array with B, G, R channel order)

        returns:
          meta: current frame result container, with MFT.results.FlowOUTrackingResult in meta.result
                The meta.result represents the accumulated flow field from the init frame, to the current frame
        """
        meta = SimpleNamespace()
        self.current_frame_i += self.time_direction

        # OF(init, t) candidates using different deltas
        delta_results = {}
        already_used_left_ids = []

        # chain_timer = general_time_measurer('chain', cuda_sync=True, start_now=False, active=self.C.timers_enabled)
        for delta in deltas:
            # candidates are chained from previous result (init -> t-delta) and flow (t-delta -> t)
            # when tracking backward, the chain consists of previous result (init -> t+delta) and flow(t+delta -> t)

            left_id = self.current_frame_i - delta * self.time_direction
            # right_id = self.current_frame_i

            # we must ensure that left_id is not behind the init frame
            if self.is_before_start(left_id):
                if np.isinf(delta):
                    left_id = self.start_frame_i
                else:
                    continue
            left_id = int(left_id)

            # because of this, different deltas can result in the same left_id, right_id combination
            # let's not recompute the same candidate multiple times
            if left_id in already_used_left_ids:
                continue

            left_img = self.memory[left_id]['img']
            right_img = input_img

            template_to_left = self.memory[left_id]['result']

            left_to_right = get_flowou(self.flower, left_img, right_img)
            # print('\n光流计算:{}\n'.format(block1 - block0))

            delta_results[delta] = chain_results(template_to_left, left_to_right, self.device)

            already_used_left_ids.append(left_id)

        used_deltas = sorted(list(delta_results.keys()), key=lambda delta: 0 if np.isinf(delta) else delta)
        all_results = [delta_results[delta] for delta in used_deltas]
        all_flows = np.stack([result.flow for result in all_results], axis=0)  # (N_delta, xy, H, W)
        all_sigmas = np.stack([result.sigma for result in all_results], axis=0)  # (N_delta, 1, H, W)
        all_occlusions = np.stack([result.occlusion for result in all_results], axis=0)  # (N_delta, 1, H, W)

        scores = -all_sigmas
        scores[all_occlusions > 0.02] = -float('inf')

        selected_delta_i = np.argmax(scores, axis=0, keepdims=True)  # (1, 1, H, W)

        best_flow = np.take_along_axis(all_flows,
                                       indices=selected_delta_i.repeat(2, axis=1),
                                       axis=0)
        best_occlusions = np.take_along_axis(all_occlusions, indices=selected_delta_i, axis=0)
        best_sigmas = np.take_along_axis(all_sigmas, indices=selected_delta_i, axis=0)

        selected_flow, selected_occlusion, selected_sigmas = best_flow, best_occlusions, best_sigmas

        selected_flow = selected_flow.squeeze(0)
        selected_occlusion = selected_occlusion.squeeze(0)
        selected_sigmas = selected_sigmas.squeeze(0)

        result = FlowOUTrackingResult(selected_flow, selected_occlusion, selected_sigmas)

        # mark flows pointing outside of the current image as occluded
        invalid_mask = np.expand_dims(result.invalid_mask(), 0)
        result.occlusion[invalid_mask] = 1

        out_result = result.clone()

        meta.result = out_result

        self.memory[self.current_frame_i] = {'img': input_img,
                                             'result': result}

        return meta

    def is_before_start(self, frame_i):
        return ((self.time_direction > 0 and frame_i < self.start_frame_i) or  # forward
                (self.time_direction < 0 and frame_i > self.start_frame_i))  # backward


# @profile
def get_flowou(flower, left_img, right_img):
    """Compute flow from left_img to right_img. Possibly with caching.

    args:
        flower: flow wrapper
        left_img: (H, W, 3) BGR np.uint8 image
        right_img: (H, W, 3) BGR np.uint8 image

    returns:
        flowou: FlowOUTrackingResult
    """

    flow_left_to_right, occlusions, sigmas = flower.compute_flow(left_img, right_img)

    # flow_left_to_right = torch.tensor(flow_left_to_right, device='cuda')
    # occlusions = torch.tensor(occlusions, device='cuda')
    # sigmas = torch.tensor(sigmas, device='cuda')

    flowou = FlowOUTrackingResult(flow_left_to_right, occlusions, sigmas)
    return flowou


def chain_results(left_result, right_result, device):
    try:
        import cupy as cp
        use_cuda = False
        if (device != 'cpu') and (cp.cuda.runtime.getDeviceCount() > int(device.split(':')[-1])):
            cp.cuda.Device(int(device.split(':')[-1])).use()
            use_cuda = True
    except:
        use_cuda = False

    # use_cuda = False

    if use_cuda:
        flow = left_result.chain(cp.asarray(right_result.flow), use_cuda)
    else:
        flow = left_result.chain(right_result.flow, use_cuda)
    if use_cuda:
        occlusions = cp.maximum(cp.asarray(left_result.occlusion),
                                left_result.warp_backward(cp.asarray(right_result.occlusion), use_cuda))

        sigmas = cp.sqrt(cp.square(cp.asarray(left_result.sigma)) +
                         cp.square(left_result.warp_backward(cp.asarray(right_result.sigma), use_cuda)))
    else:
        occlusions = np.maximum(left_result.occlusion,
                                left_result.warp_backward(right_result.occlusion, use_cuda))

        sigmas = np.sqrt(np.square(left_result.sigma) +
                         np.square(left_result.warp_backward(right_result.sigma, use_cuda)))
    if use_cuda:
        flow = flow.get()
        occlusions = occlusions.get()
        sigmas = sigmas.get()
    # print('\n光流连接:{}\n遮挡与不确定性:{}\n'.format(block1 - block0, block2 - block1))
    return FlowOUTrackingResult(flow, occlusions, sigmas)
