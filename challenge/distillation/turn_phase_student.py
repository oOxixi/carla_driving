"""Serve the pinned FP32 candidate on the existing Planner V2 test endpoint."""
import argparse
from pathlib import Path

import torch
import onnxruntime as ort

from challenge.planner.student_adapter import StudentPlanAdapter
from challenge.runtime.student_x86 import OnnxModel
from challenge.student.preprocess import StudentPreprocessor
from qwen_service.server import QwenHTTPServer
from qwen_service.service import QwenDecisionService, QwenServiceConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    a = parser.parse_args()
    torch.set_num_threads(1)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    runtime = OnnxModel(str(a.model), session_options=options)
    if runtime.model_sha256 != "e8e4cb0f500a848b0462015d7f80f7716316aa5364cd3494526c72724d04a63c":
        raise ValueError("Wrong FP32 candidate")
    if runtime.metadata.get("post_turn_speed_contract") != "explicit-v2":
        raise ValueError("Missing explicit-v2 input contract")
    pre = StudentPreprocessor(post_turn_speed=True)
    adapter = StudentPlanAdapter(model_id=runtime.metadata["model_id"])

    class Backend:
        production_ready = False
        model_id = runtime.metadata["model_id"]

        def health(self):
            return True, "isolated CPU FP32 development replay"

        def infer(self, request):
            image = (a.root / request["rgb_ref"]).resolve()
            if not image.is_relative_to(a.root.resolve()) or not image.is_file():
                raise ValueError("Missing same-frame RGB in run root")
            feed = dict(zip((x.name for x in runtime.inputs),
                            (x.numpy() for x in pre({**request, "rgb_ref": str(image)}).as_tuple()), strict=True))
            output = dict(zip((x.name for x in runtime.outputs), map(torch.from_numpy, runtime.run(feed)), strict=True))
            return adapter.decode(request, output)

    service = QwenDecisionService(Backend(), config=QwenServiceConfig(timeout_ms=15000), qwen_mode="planner_v2")
    with QwenHTTPServer(("127.0.0.1", a.port), service) as server:
        try:
            server.serve_forever()
        finally:
            service.close()


if __name__ == "__main__":
    main()
