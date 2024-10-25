from ultralytics import YOLO

# Load a model
model = YOLO("yolo11s")  # load a pretrained model (recommended for training)

# Train the model
results = model.train(data="coco8.yaml", epochs=100, imgsz=640)
