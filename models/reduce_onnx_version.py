import onnx

input_path = "best.onnx"
output_path = "best_v8_opset15.onnx"

print(f"[+] Đang xử lý file: {input_path}")
model = onnx.load(input_path)

# 1. Hạ IR Version về 8 (Dành cho ONNX Runtime 1.10.0)
model.ir_version = 8

# 2. Sửa Opset Import về 15
for imp in model.opset_import:
    if imp.domain == '' or imp.domain == 'ai.onnx':
        print(f" -> Sửa Opset từ {imp.version} về 15")
        imp.version = 15

# 3. Lưu lại file mới
onnx.save(model, output_path)
print(f"[✓] Đã xuất thành công: {output_path}")