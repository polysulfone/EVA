import numpy as np
try:
    import cupy as cp
except:
    pass


def normalize_coords(coordinates, H, W, use_cuda=False):
    """Normalize coordinates to be in [-1, 1] range as usedi in F.grid_sample.
    args:
        coordinates: (N H W xy) coordinates
    """
    if use_cuda:
        scales = cp.array([2 / (W - 1), 2 / (H - 1)], dtype=cp.float32)
    else:
        scales = np.array([2 / (W - 1), 2 / (H - 1)], dtype=np.float32)
    coordinates_normed = coordinates * scales - 1  # maps to [-1, 1]
    return coordinates_normed


def bilinear_sample(data, coords):
    """
    args:
        data: (batch, C, H, W) tensor
        coords: (batch, ...outshape..., xy) tensor of coordinates
    returns:
        sampled: (batch, ...outshape..., C) tensor
    """
    assert len(coords.shape) >= 3
    assert coords.shape[-1] == 2

    norm_coords = normalize_coords(coords, data.shape[2], data.shape[3])
    grid_coords = np.expand_dims(norm_coords, 0)
    sampled_flat = grid_sample(data, grid_coords)
    sampled = np.reshape(sampled_flat, (1, sampled_flat.shape[-1], 1))
    return sampled


def unravel_indices(indices, shape, stack_dim=-1, np_order=False, use_cuda=False):
    r"""Converts flat indices into unraveled coordinates in a target shape.

    Args:
        indices: A tensor of (flat) indices, (*, N).
        shape: The targeted shape, (D,).

    Returns:
        The unraveled coordinates, (*, N, D).

    From https://github.com/pytorch/pytorch/issues/35674#issuecomment-739560051
    """

    coord = []

    for dim in reversed(shape):
        coord.append(indices % dim)
        if use_cuda:
            indices = cp.divide(indices, dim).astype(cp.int64)
        else:
            indices = np.divide(indices, dim).astype(np.int64)

    if use_cuda:
        if np_order:  # row, column (y, x)
            coord = cp.stack(coord[::-1], axis=stack_dim)
        else:  # column, row (x, y)
            coord = cp.stack(coord, axis=stack_dim)
    else:
        if np_order:  # row, column (y, x)
            coord = np.stack(coord[::-1], axis=stack_dim)
        else:  # column, row (x, y)
            coord = np.stack(coord, axis=stack_dim)

    return coord


def torch_get_featuremap_coords(feature_map,
                                keep_shape=False,
                                use_cuda=False):
    """ get coordinate map corresponding to a feature map

    args:
        feature_map: (..., H, W) tensor
        keep_shape: boolean (default False). Setting it to True does not flatten the output coordinates

    returns:
        xy: (2, H*W) tensor with x, y coordinates.  (2, H, W) tensor if keep_shape == True
    """
    if type(feature_map) is tuple and len(feature_map) == 2:
        H, W = feature_map
    else:
        H, W = feature_map.shape[-2:]

    if use_cuda:
        xy = unravel_indices(cp.arange(H * W, ), (H, W), stack_dim=0, use_cuda=use_cuda)
    else:
        xy = unravel_indices(np.arange(H * W, ), (H, W), stack_dim=0, use_cuda=use_cuda)

    if keep_shape:
        if use_cuda:
            xy = cp.reshape(xy, (2, H, W))
        else:
            xy = np.reshape(xy, (2, H, W))
    return xy


def grid_sample(input, grid, use_cuda=False):
    import time
    start = time.time()
    N, C, H_in, W_in = input.shape
    N, H_out, W_out, _ = grid.shape
    if use_cuda:
        batch_norm = cp.arange(N).reshape((N, 1, 1))
        fix_input = cp.empty((N, C, H_in+1, W_in+1))
    else:
        batch_norm = np.arange(N).reshape((N, 1, 1))
        fix_input = np.random.random((N, C, H_in + 1, W_in + 1))

    fix_input[:, :, :H_in, :W_in] = input
    fix_input[:, :, :H_in, W_in] = input[:, :, :, W_in - 1]
    fix_input[:, :, H_in, :W_in] = input[:, :, H_in - 1, :]
    fix_input[:, :, H_in, W_in] = input[:, :, H_in - 1, W_in - 1]

    mask = (grid >= -1) & (grid <= 1)

    if use_cuda:

        param = cp.array([W_in - 1, H_in - 1]).reshape(1, 1, 1, 2)
        param = (param * (grid + 1) / 2) * mask
        coor1 = (param + 1).astype(cp.int32)
        coor0 = coor1 - 1
        param = cp.abs(param - coor0)

    else:

        param = np.array([W_in - 1, H_in - 1]).reshape(1, 1, 1, 2)
        param = (param * (grid + 1) / 2) * mask
        coor0 = param.astype(np.int32)
        coor1 = coor0 + 1
        param = np.abs(param - coor0)

    x0 = coor0[..., 0]
    y0 = coor0[..., 1]
    x1 = coor1[..., 0]
    y1 = coor1[..., 1]

    left_top_value = fix_input[batch_norm, :, y0, x0]
    right_top_value = fix_input[batch_norm, :, y0, x1]
    left_bottom_value = fix_input[batch_norm, :, y1, x0]
    right_bottom_value = fix_input[batch_norm, :, y1, x1]

    param_x = param[..., 0:1]
    param_y = param[..., 1:2]
    left_top = left_top_value * (1 - param_x) * (1 - param_y)
    left_bottom = left_bottom_value * (1 - param_x) * param_y
    right_top = right_top_value * param_x * (1 - param_y)
    right_bottom = right_bottom_value * param_x * param_y
    result = (left_bottom + left_top + right_bottom + right_top)
    if use_cuda:
        output = cp.transpose(result, (0, 3, 1, 2))
    else:
        output = np.transpose(result, (0, 3, 1, 2))

    end = time.time()
    # print('\n填充耗时:{}'.format(end-start))
    return output
