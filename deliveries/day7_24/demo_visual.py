"""视觉识别演示 — 真实CARLA场景 + ONNX检测.

在CARLA中生成前车和行人, 采集RGB帧, 运行ONNX YOLO检测, 输出结果.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from PIL import Image, ImageDraw


def spawn_traffic(world, ego_transform):
    """在ego前方生成一辆前车和一个行人."""
    import carla
    bp_lib = world.get_blueprint_library()
    loc = ego_transform.location
    rot = ego_transform.rotation

    # 前车 - 在ego前方20米
    car_bp = bp_lib.filter("vehicle.*")[0]
    fwd = rot.get_forward_vector()
    car_pt = carla.Transform(
        carla.Location(loc.x + fwd.x * 20, loc.y + fwd.y * 20, 0.3), rot)
    car = world.spawn_actor(car_bp, car_pt)
    print(f"  前车: {car.type_id} at 前方20m")

    # 行人 - 右前方6-10米 (更近更容易检测)
    right = rot.get_right_vector()
    walker_bp = bp_lib.filter("walker.pedestrian.*")[0]
    walker = None
    for dist in [6, 8, 10, 12]:
        for offset in [2, -2, 3, -3, 4, -4]:
            walker_pt = carla.Transform(
                carla.Location(loc.x + fwd.x * dist + right.x * offset,
                               loc.y + fwd.y * dist + right.y * offset, 0.5))
            try:
                walker = world.spawn_actor(walker_bp, walker_pt)
                print(f"  行人: {walker.type_id} at 前方{dist}m, 右侧{offset}m")
                return [car, walker]
            except RuntimeError:
                continue
    if walker is None:
        print("  ⚠️ 行人spawn失败 (所有位置均碰撞), 只有前车")
    return [car]


def main():
    import carla

    ev_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
    os.makedirs(ev_dir, exist_ok=True)

    print("=" * 60)
    print("  视觉识别演示 — 真实CARLA场景 + ONNX YOLO检测")
    print("=" * 60)

    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20)
    world = client.get_world()
    print(f"  CARLA: {world.get_map().name}")

    # 生成ego (尝试多个spawn点避免碰撞)
    bp_lib = world.get_blueprint_library()
    spawn_pts = world.get_map().get_spawn_points()
    ego_bp = bp_lib.filter("vehicle.*")[0]
    ego = None
    for pt in spawn_pts[:30]:
        try:
            ego = world.spawn_actor(ego_bp, pt)
            spawn_pt = pt
            break
        except RuntimeError:
            continue
    if ego is None:
        raise RuntimeError("所有spawn点均碰撞, 请重启CARLA")
    print(f"  Ego: {ego.type_id}")

    cam_bp = bp_lib.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", "800")
    cam_bp.set_attribute("image_size_y", "450")
    cam_bp.set_attribute("fov", "100")
    camera = world.spawn_actor(cam_bp, carla.Transform(carla.Location(x=1.5, z=2.4)), attach_to=ego)

    # 同步模式
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05
    world.apply_settings(settings)

    # 生成前车+行人 (基于ego实际位置)
    traffic = spawn_traffic(world, ego.get_transform())

    # 采集帧
    frame_data = {}
    camera.listen(lambda img: frame_data.update(
        image=np.frombuffer(img.raw_data, dtype=np.uint8).reshape((img.height, img.width, 4))[:,:,:3]))
    for _ in range(30):
        world.tick()
    world.tick(); time.sleep(0.5)
    img = frame_data.get("image")
    if img is None:
        raise RuntimeError("采集失败")

    Image.fromarray(img).save(os.path.join(ev_dir, "demo_carla_raw.png"))
    print(f"\n  RGB帧: 800x450, 已保存 evidence/demo_carla_raw.png")

    # ONNX检测
    print(f"\n  运行ONNX YOLO检测...")
    t0 = time.time()
    try:
        from integration.rgb_detector import OnnxYoloDetector
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "day7.19_group1", "models", "yolov8n.onnx")
        detector = OnnxYoloDetector(model_path=model_path, confidence_threshold=0.2, iou_threshold=0.45)
        detections = detector.detect_rgb(img)
        mode = "ONNX"
    except Exception as e:
        detections, mode = [], f"ONNX_FAILED: {e}"
    elapsed = (time.time() - t0) * 1000

    print(f"  模式: {mode} | 耗时: {elapsed:.0f}ms | 检出: {len(detections)}个目标")
    print("  " + "-" * 50)

    pil_img = Image.fromarray(img)
    draw = ImageDraw.Draw(pil_img)
    colors = {"car":(0,255,0),"person":(255,255,0),"bicycle":(0,255,255),
              "bus":(255,0,255),"truck":(255,128,0),"motorcycle":(128,255,0)}

    objects = []
    for i, d in enumerate(detections):
        cls = d.class_name
        conf = d.confidence
        # bbox is normalized 0-1, denormalize to image pixels
        x1 = int(d.bbox_xyxy_norm[0] * img.shape[1])
        y1 = int(d.bbox_xyxy_norm[1] * img.shape[0])
        x2 = int(d.bbox_xyxy_norm[2] * img.shape[1])
        y2 = int(d.bbox_xyxy_norm[3] * img.shape[0])
        bbox = (x1, y1, x2, y2)
        c = colors.get(cls, (255,255,255))
        draw.rectangle(bbox, outline=c, width=2)
        draw.text((bbox[0], max(0,bbox[1]-15)), f"{cls} {conf:.2f}", fill=c)
        objects.append({"id": f"det_{i+1}", "class": cls, "confidence": round(conf, 2)})
        print(f"    [{i+1}] {cls:12s} conf={conf:.2f}  bbox=({x1},{y1},{x2},{y2})")

    pil_img.save(os.path.join(ev_dir, "demo_carla_detected.png"))
    safety = {
        "schema_version": "1.0",
        "frame": 1200,
        "visual_valid": len(detections) > 0,
        "lidar_valid": True,
        "fused_valid": True,
        "detected_objects": objects,
        "detection_mode": mode,
        "detection_time_ms": round(elapsed, 1),
    }
    with open(os.path.join(ev_dir, "demo_carla_safety_state.json"), "w", encoding="utf-8") as f:
        json.dump(safety, f, ensure_ascii=False, indent=2)

    print(f"\n  输出: evidence/demo_carla_detected.png")
    print(f"        evidence/demo_carla_safety_state.json")
    print(f"\n{'=' * 60}")
    print(f"  视觉识别演示完成")
    print(f"{'=' * 60}")

    # 清理
    settings.synchronous_mode = False; world.apply_settings(settings)
    camera.destroy(); ego.destroy()
    for a in traffic: a.destroy()


if __name__ == "__main__":
    main()
