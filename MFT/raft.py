import numpy as np
import onnxruntime as ort


class InputPadder:
    """ Pads images such that dimensions are divisible by 8 """

    def __init__(self, dims, mode='sintel'):
        self.ht, self.wd = dims[-2:]
        pad_ht = (((self.ht // 8) + 1) * 8 - self.ht) % 8
        pad_wd = (((self.wd // 8) + 1) * 8 - self.wd) % 8
        if mode == 'sintel' or mode == 'viper':
            self._pad = [pad_wd // 2, pad_wd - pad_wd // 2, pad_ht // 2,
                         pad_ht - pad_ht // 2]  # left, right, top, bottom
        else:
            self._pad = [pad_wd // 2, pad_wd - pad_wd // 2, 0, pad_ht]

    def pad(self, *inputs):
        return [np.pad(x, ((0, 0), (0, 0), (self._pad[2], self._pad[3]), (self._pad[0], self._pad[1])), 'edge') for x in
                inputs]

    def unpad(self, x):
        ht, wd = x.shape[-2:]
        c = [self._pad[2], ht - self._pad[3], self._pad[0], wd - self._pad[1]]
        return x[..., c[0]:c[1], c[2]:c[3]]


class RAFTWrapper:
    def _select_best_provider(self, device):
        available_providers = ort.get_available_providers()
        if ('CUDAExecutionProvider' in available_providers) and device != 'cpu':
            return 'CUDAExecutionProvider'
        return 'CPUExecutionProvider'

    def _prepare_image(self, img):
        # BGR2RGB
        rgb = img[:, :, ::-1]

        # HWC -> CHW
        chw = np.transpose(rgb, (2, 0, 1))

        # add batch dimension
        add_batch = np.expand_dims(chw, axis=0)
        return add_batch.astype(np.float32)

    def __init__(self, checkpoint_path, device):
        # self.C = config
        # self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # Load ONNX Model
        if device != 'cpu':
            try:
                opts = [{"device_id": int(device.split(':')[-1])}]
                self.ort_session = ort.InferenceSession(
                    checkpoint_path,
                    providers=[self._select_best_provider(device=device)],
                    opts=opts
                )
            except:
                self.ort_session = ort.InferenceSession(
                    checkpoint_path,
                    providers=['CPUExecutionProvider']
                )
        else:
            self.ort_session = ort.InferenceSession(
                checkpoint_path,
                providers=['CPUExecutionProvider']
            )

        # 初始化输入填充器
        self.padder = InputPadder

    def compute_flow(self, src_img, dst_img):

        # 1. prepare images
        # Convert to tensor and BGR to RGB
        image1 = self._prepare_image(src_img)
        image2 = self._prepare_image(dst_img)

        # pad the images
        padder = self.padder(image1.shape)
        image1_padded, image2_padded = padder.pad(image1, image2)

        # 2. prepare input
        ort_inputs = {
            "image1": image1_padded,
            "image2": image2_padded,
        }

        # create init flow
        B, _, H, W = image1_padded.shape
        flow_init = np.zeros((B, 2, H // 8, W // 8), dtype=np.float32)
        ort_inputs["flow_init"] = flow_init

        # 3. run
        ort_outputs = self.ort_session.run(None, ort_inputs)
        flow_out, occlusion_out, uncertainty_out = ort_outputs[:3]

        # 4. unpad
        flow_unpadded = padder.unpad(flow_out)
        occlusion_unpadded = padder.unpad(occlusion_out)
        uncertainty_unpadded = padder.unpad(uncertainty_out)

        flow = flow_unpadded[0]  # (2, H, W)

        # softmax
        max_val = np.max(occlusion_unpadded, axis=1, keepdims=True)
        exp_safe = np.exp(occlusion_unpadded - max_val)
        sum_val = np.sum(exp_safe, axis=1, keepdims=True)
        occlusion_prob = exp_safe[:, 1:2, :, :] / sum_val

        # occlusion_prob = torch.softmax(occlusion_tensor, dim=1)[:, 1:2, :, :]
        occlusions = occlusion_prob.squeeze(0)  # (H, W)

        # get sigma
        uncertainty = uncertainty_unpadded.squeeze(0)  # (H, W)
        sigma = np.sqrt(np.exp(uncertainty))

        return flow, occlusions, sigma
