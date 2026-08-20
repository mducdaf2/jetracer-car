import numpy as np
import onnxruntime as ort

class ONNXEngine:
    def __init__(self, model_path):
        # Lấy danh sách providers khả thi trên máy hiện tại
        available_providers = ort.get_available_providers()
        
        # Ưu tiên CUDA, nếu không có sẽ tự lấy CPU mà không báo warning
        providers = [p for p in ['CUDAExecutionProvider', 'CPUExecutionProvider'] if p in available_providers]
        
        self.session = ort.InferenceSession(model_path, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        print(f"💡 ONNXEngine đang chạy trên: {self.session.get_providers()[0]}")

    def infer(self, input_tensor):
        if len(input_tensor.shape) == 3:
            input_tensor = np.expand_dims(input_tensor, axis=0)
        outputs = self.session.run(None, {self.input_name: input_tensor})
        return outputs[0]