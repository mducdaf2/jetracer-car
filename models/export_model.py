import tensorrt as trt

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

def convert_onnx_to_engine(onnx_file_path, engine_file_path):
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    config = builder.create_builder_config()
    parser = trt.OnnxParser(network, TRT_LOGGER)

    # Đọc file ONNX
    with open(onnx_file_path, 'rb') as model:
        if not parser.parse(model.read()):
            print("Lỗi parse file ONNX:")
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            return False

    # Cấu hình bộ nhớ đệm và chế độ FP16
    config.max_workspace_size = 1 << 30  # 1GB RAM
    if builder.platform_has_tf32 or builder.has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)

    print("⏳ Đang build TensorRT Engine (quá trình này mất khoảng 2-5 phút)...")
    engine = builder.build_engine(network, config)

    if engine is None:
        print("❌ Build Engine thất bại!")
        return False

    with open(engine_file_path, "wb") as f:
        f.write(engine.serialize())
    print("✅ Đã tạo thành công file best.engine!")
    return True



if __name__ == '__main__':
    convert_onnx_to_engine("best.onnx", "best.engine")