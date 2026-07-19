from __future__ import annotations

import argparse
import json

import onnxruntime as ort


def shape_to_list(shape):
    result = []

    for value in shape:
        if isinstance(value, int):
            result.append(value)
        else:
            result.append(str(value))

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "model",
        nargs="?",
        default="models/yolov8n.onnx",
    )
    args = parser.parse_args()

    session = ort.InferenceSession(
        args.model,
        providers=["CPUExecutionProvider"],
    )

    info = {
        "providers": session.get_providers(),
        "inputs": [
            {
                "name": item.name,
                "shape": shape_to_list(item.shape),
                "type": item.type,
            }
            for item in session.get_inputs()
        ],
        "outputs": [
            {
                "name": item.name,
                "shape": shape_to_list(item.shape),
                "type": item.type,
            }
            for item in session.get_outputs()
        ],
    }

    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
