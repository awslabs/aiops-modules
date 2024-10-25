from ultralytics import YOLO

# Load a YOLO11n model
model = YOLO("yolo11n.pt")

# Start tuning hyperparameters for YOLO11n training on the COCO8 dataset
result_grid = model.tune(data="coco8.yaml", use_ray=True)

print(result_grid)
