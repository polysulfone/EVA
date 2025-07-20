import numpy as np
try:
    import cupy as cp
except:
    pass
from MFT.utils import torch_get_featuremap_coords, normalize_coords, grid_sample

class FlowOUTrackingResult(object):
    def __init__(self, flow, occlusion=None, sigma=None):
        """
        Stores optical flow, occlusion map and flow sigma map.

        flow: (xy-delta, H, W) tensor
        occlusion: (1, H, W) tensor
        sigma: (1, H, W) tensor
        """
        assert len(flow.shape) == 3
        assert flow.shape[0] == 2
        self.H, self.W = flow.shape[1:]
        if occlusion is None:
            occlusion = np.zeros((1, self.H, self.W), dtype=np.float32)
        if sigma is None:
            sigma = np.zeros((1, self.H, self.W), dtype=np.float32)

        assert flow.shape == (2, self.H, self.W)
        assert occlusion.shape == (1, self.H, self.W)
        assert sigma.shape == (1, self.H, self.W)

        assert np.all(occlusion >= 0)
        assert np.all(occlusion <= 1.000001)
        assert np.all(sigma >= 0)

        self.flow = flow  # (xy-delta, H, W) tensor
        self.occlusion = occlusion  # (1, H, W) tensor
        self.sigma = sigma  # (1, H, W) tensor

    # def __repr__(self):
    #     cls = self.__class__.__name__
    #     txt = f'<{cls} ({self.H} x {self.W}) has flow, occlusion, sigma>'
    #     return txt

    # def cpu(self):
    #     self.flow = self.flow.cpu()
    #     self.occlusion = self.occlusion.cpu()
    #     self.sigma = self.sigma.cpu()
    #     return self
    #
    # def cuda(self):
    #     self.flow = self.flow.cuda()
    #     self.occlusion = self.occlusion.cuda()
    #     self.sigma = self.sigma.cuda()
    #     return self

    def clone(self):
        return FlowOUTrackingResult(self.flow.copy(),
                                    self.occlusion.copy(),
                                    self.sigma.copy())

    # @classmethod
    # def read(self, path):
    #     flow, occlusions, sigmas = io_utils.read_flowou(path)
    #     return FlowOUTrackingResult(torch.from_numpy(flow),
    #                                 torch.from_numpy(occlusions),
    #                                 torch.from_numpy(sigmas))

    @classmethod
    def identity(cls, flow_shape):
        """Create a zero-flow, zero-sigma, zero-occlusion result

        args:
            flow_shape: (H, W) tuple"""
        xy = 2
        flow = np.zeros((xy, flow_shape[0], flow_shape[1]), dtype=np.float32)
        occlusion = np.zeros((1, flow_shape[0], flow_shape[1]), dtype=np.float32)
        sigma = np.zeros((1, flow_shape[0], flow_shape[1]), dtype=np.float32)

        return FlowOUTrackingResult(flow, occlusion=occlusion, sigma=sigma)

    def chain(self, flow, use_cuda=False):
        """Chain 'flow' after our result.

        With 'self.flow' from A to B, and 'flow' from B to C, this
        function produces a flow from A to C by bilinear
        interpolation.

        args:
            flow: (xy H W) tensor with flow from B to C
        return:
            chained_flow: (xy H W) tensor with flow from A to C
        """
        import time
        flow_shape = flow.shape
        assert flow_shape[0] == 2

        block0 = time.time()
        coords_A = torch_get_featuremap_coords((flow_shape[1], flow_shape[2]),
                                               keep_shape=True, use_cuda=use_cuda)
        block1 = time.time()
        if use_cuda:
            coords_B = coords_A + cp.asarray(self.flow)
            coords_B_normed = normalize_coords(cp.transpose(cp.expand_dims(coords_B, 0), (0, 2, 3, 1)),
                                               flow_shape[1], flow_shape[2], use_cuda=use_cuda)
        else:
            coords_B = coords_A + self.flow
            coords_B_normed = normalize_coords(np.transpose(np.expand_dims(coords_B, 0), (0, 2, 3, 1)),
                                               flow_shape[1], flow_shape[2], use_cuda=use_cuda)
        block2 = time.time()

        flow_BC = flow

        if use_cuda:
            flow_BC_sampled = grid_sample(cp.expand_dims(flow_BC, 0),
                                          coords_B_normed, use_cuda=use_cuda).squeeze(0)
        else:
            flow_BC_sampled = grid_sample(np.expand_dims(flow_BC, 0),
                                          coords_B_normed, use_cuda=use_cuda).squeeze(0)
        block3 = time.time()
        chained_flow = coords_B + flow_BC_sampled - coords_A

        # print('\n获取特征图:{}\n归一化坐标:{}\n格子取样:{}\n'.format(block1 - block0, block2 - block1, block3 - block2))
        return chained_flow

    def warp_backward(self, img, use_cuda=False):
        """Sample the img data using the right end of 'self.flow'

        args:
            img: (C, H, W) tensor

        return:
            img_sampled: (C, flow_H, flow_W) tensor
        """
        assert len(img.shape) == 3
        assert img.shape[1:] == (self.H, self.W)
        coords_A = torch_get_featuremap_coords((self.H, self.W), keep_shape=True, use_cuda=use_cuda)
        if use_cuda:
            coords_B = coords_A + cp.asarray(self.flow)
            coords_B_normed = normalize_coords(cp.transpose(cp.expand_dims(coords_B, 0), (0, 2, 3, 1)),
                                               self.H, self.W, use_cuda=use_cuda)
            img_sampled = grid_sample(cp.expand_dims(img, 0),
                                      coords_B_normed, use_cuda=use_cuda).squeeze(0)
        else:
            coords_B = coords_A + self.flow
            coords_B_normed = normalize_coords(np.transpose(np.expand_dims(coords_B, 0), (0, 2, 3, 1)),
                                               self.H, self.W, use_cuda=use_cuda)

            img_sampled = grid_sample(np.expand_dims(img, 0),
                                      coords_B_normed, use_cuda=use_cuda).squeeze(0)
        return img_sampled

    def warp_forward_points(self, points):
        """Warp the points using the stored optical flow.

        args:
            points: (N xy) tensor with source coordinates.
        return:
            warped_points: (N xy) tensor with warped coordinates
        """

        points_normed = normalize_coords(np.expand_dims(np.expand_dims(points, 0), 0),
                                         H=self.H, W=self.W)
        flow = self.flow
        flow_sampled = grid_sample(np.expand_dims(flow, 0), points_normed).squeeze(0).squeeze(1)
        flow_sampled = np.transpose(flow_sampled, (1, 0))
        warped_points = points + flow_sampled
        return warped_points

    # def sample(self, points):
    #     """Sample the results at the given points.
    #
    #     args:
    #         points: (N xy) tensor with query coordinates
    #     return:
    #         sampled_flow: (xy N)
    #         sampled_occlusions: (1 N)
    #         sampled_sigmas: (1 N)
    #     """
    #     points = ensure_torch(points).to(torch.float32)
    #     N = points.shape[0]
    #     device = points.device
    #     # (we will keep N points in the usual Width dimension and keep Height = 1)
    #     points_normed = interpolation.normalize_coords(einops.rearrange(points, 'N xy -> 1 1 N xy', xy=2),
    #                                                    H=self.H, W=self.W)
    #
    #     flow = self.flow.to(device).to(torch.float32)
    #     sampled_flow = F.grid_sample(einops.rearrange(flow, 'xy H W -> 1 xy H W', xy=2),
    #                                  points_normed, align_corners=True)
    #     sampled_flow = einops.rearrange(sampled_flow, '1 xy 1 N -> xy N', xy=2, N=N)
    #     sampled_occlusions = F.grid_sample(
    #         einops.rearrange(self.occlusion.to(device).to(torch.float32), '1 H W -> 1 1 H W'),
    #         points_normed, align_corners=True)
    #     sampled_occlusions = einops.rearrange(sampled_occlusions, '1 c 1 N -> c N', c=1, N=N)
    #     sampled_sigmas = F.grid_sample(
    #         einops.rearrange(self.sigma.to(device).to(torch.float32), '1 H W -> 1 1 H W'),
    #         points_normed, align_corners=True)
    #     sampled_sigmas = einops.rearrange(sampled_sigmas, '1 c 1 N -> c N', c=1, N=N)
    #     return sampled_flow, sampled_occlusions, sampled_sigmas

    # def warp_forward(self, img, mask=None, border=None):
    #     """Warp img forward by self.flow, only warp values that are not masked.
    #
    #     args:
    #         img: (H, W, ...) array / tensor with values to be warped
    #         mask: [optional] (H, W) binary array / tensor. Only values with mask==True will be warped
    #         border: [optional] border value
    #
    #     returns:
    #         warped_img: (H, W, ...) array with warped values
    #     """
    #     device = self.flow.device
    #     assert img.shape[:2] == (self.H, self.W)
    #
    #     H, W = img.shape[:2]
    #     xs, ys = np.meshgrid(np.arange(W), np.arange(H))
    #     assert xs.shape == (H, W)
    #     assert ys.shape == (H, W)
    #     assert xs[0, 0] == xs[1, 0]
    #
    #     # debugging
    #     vmin, vmax = img.min(), img.max()
    #
    #     src_coords = np.dstack((xs, ys))
    #     query_coords_flat = einops.rearrange(src_coords, 'H W xy -> (H W) xy')
    #
    #     dst_coords = torch.from_numpy(src_coords).to(device) + einops.rearrange(self.flow,
    #                                                                             'xy H W -> H W xy',
    #                                                                             xy=2, H=H, W=W)
    #     pixel_positions_flat = einops.rearrange(dst_coords, 'H W xy -> (H W) xy', xy=2)
    #     pixel_values_flat = einops.rearrange(img, 'H W ... -> (H W) ...')
    #     if mask is not None:
    #         pixel_mask = mask[query_coords_flat[:, 1], query_coords_flat[:, 0]]
    #         pixel_positions_flat = pixel_positions_flat[pixel_mask, :]
    #         pixel_values_flat = ensure_torch(pixel_values_flat).to(device)[pixel_mask, ...]
    #
    #     pixel_values_flat = ensure_torch(pixel_values_flat)
    #     assert torch.all(pixel_values_flat >= vmin)
    #     assert torch.all(pixel_values_flat <= vmax)
    #
    #     accum, counts = interpolation.bilinear_splat(pixel_values_flat.to(pixel_positions_flat.device),
    #                                                  pixel_positions_flat,
    #                                                  (H, W))
    #     warped_img = accum.clone()
    #     count_mask = einops.rearrange(counts, 'H W 1 -> H W') > 0
    #     warped_img[count_mask] /= counts[count_mask]
    #
    #     out_vmin = warped_img.min()
    #     out_vmax = warped_img.max()
    #
    #     eps = 5e-3
    #     # errors = output < (min(vmin, 0) - eps)
    #     assert torch.all(out_vmin >= min(vmin, 0) - eps)  # 0 for the places without any data
    #     assert torch.all(out_vmax <= max(vmax, 0) + eps)
    #
    #     if border is not None:
    #         warped_img[~count_mask] = border
    #
    #     return warped_img.cpu().numpy()

    def invalid_mask(self):
        """Compute a mask of invalid self.flows, i.e. pointing outside of the image.

        returns:
            invalid_mask: (H, W) bool tensor, with True meaning the flow is invalid
        """
        coords_A = torch_get_featuremap_coords((self.H, self.W), keep_shape=True)
        coords_B = coords_A + self.flow  # xy, H, W

        invalid_mask = np.logical_or(
            np.any(coords_B < 0, axis=0),
            np.logical_or(
                coords_B[0, :, :] >= self.W,
                coords_B[1, :, :] >= self.H))
        return invalid_mask
