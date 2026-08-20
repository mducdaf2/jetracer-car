import cv2
import numpy as np

class YOLOProcessor:
    def __init__(self, img_size=640, conf_thresh=0.45, iou_thresh=0.45, classes=None):
        self.img_size = img_size
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        self.classes = classes or [
            'green-light', 'left-turn-sign', 'prohibition-sign', 
            'red-light', 'right-turn-sign', 'straight-ahead-sign'
        ]

    def preprocess(self, img0):
        h, w = img0.shape[:2]
        img = cv2.resize(img0, (self.img_size, self.img_size))
        img = img[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.ascontiguousarray(img), h, w

    def postprocess(self, output, original_h, original_w):
        predictions = np.squeeze(output).T
        boxes, confidences, class_ids = [], [], []
        
        x_factor = original_w / self.img_size
        y_factor = original_h / self.img_size
        
        for row in predictions:
            classes_scores = row[4:]
            class_id = int(np.argmax(classes_scores))
            confidence = float(classes_scores[class_id])
            
            if confidence >= self.conf_thresh:
                cx, cy, w, h = row[0], row[1], row[2], row[3]
                left = int((cx - 0.5 * w) * x_factor)
                top = int((cy - 0.5 * h) * y_factor)
                width = int(w * x_factor)
                height = int(h * y_factor)
                
                boxes.append([left, top, width, height])
                confidences.append(confidence)
                class_ids.append(class_id)
                
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_thresh, self.iou_thresh)
        
        results = []
        if len(indices) > 0:
            # Dùng np.asarray().flatten() để tương thích mọi phiên bản OpenCV (3.x, 4.x)
            flat_indices = np.asarray(indices).flatten()
            for i in flat_indices:
                results.append({
                    'box': boxes[i],
                    'confidence': confidences[i],
                    'class_name': self.classes[class_ids[i]]
                })
        return results

    def draw_bboxes(self, img0, detections):
        for det in detections:
            x, y, w, h = det['box']
            label = f"{det['class_name']} {det['confidence']:.2f}"
            cv2.rectangle(img0, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(img0, label, (x, max(y - 10, 20)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return img0

class RoadProcessor:
    """Xử lý riêng cho Mô hình Road Direction (Phân loại đa nhãn 3 hướng: Thẳng, Trái, Phải)"""
    def __init__(self, img_size=(160, 160), threshold=0.5):
        self.img_size = img_size
        self.threshold = threshold
        # Danh sách label tương ứng với 3 đầu ra của Model
        self.labels = ['Thẳng', 'Rẽ Trái', 'Rẽ Phải']
        
        # Mean & Std chuẩn ImageNet
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def preprocess(self, frame):
        """Preprocess: Resize 160x160 -> RGB -> Normalize ImageNet -> CHW -> Batching"""
        img = cv2.resize(frame, self.img_size)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        
        # Normalize ImageNet
        img = (img - self.mean) / self.std
        
        # HWC -> CHW -> (1, 3, 160, 160)
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, axis=0)
        return img

    def postprocess(self, raw_output):
        """
        Postprocess: 
        1. Biến đổi Logits -> Probabilities bằng Sigmoid
        2. So sánh với Threshold để lọc ra danh sách hướng đi khả dĩ
        """
        # Nếu raw_output có dạng (1, 3) -> duỗi phẳng về (3,)
        logits = raw_output.squeeze()
        
        # Tính xác suất bằng Sigmoid
        probs = 1.0 / (1.0 + np.exp(-logits))
        
        # Lấy danh sách các hướng có xác suất >= threshold
        possible_directions = []
        scores = {}
        
        for i, label in enumerate(self.labels):
            score = float(probs[i])
            scores[label] = round(score, 4)
            if score >= self.threshold:
                possible_directions.append(label)
                
        return {
            "possible_directions": possible_directions, # Ví dụ: ['Thẳng', 'Rẽ Phải']
            "probabilities": scores                     # Raw score: {'Thẳng': 0.92, 'Rẽ Trái': 0.05, 'Rẽ Phải': 0.81}
        }