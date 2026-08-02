#!/usr/bin/env python3
"""Export a fixed-shape SenseVoice ONNX for TensorRT benchmarking."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch import nn
from funasr import AutoModel


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = Path.home() / ".cache" / "modelscope" / "hub" / "iic" / "SenseVoiceSmall"
DEFAULT_OUTPUT = ROOT / "artifacts" / "group1_voice" / "onnx_export" / "sensevoice_static"


class StaticSenseVoiceExport(nn.Module):
    """Hard-code benchmark-time control inputs for a TRT-friendlier graph."""

    def __init__(self, export_model: nn.Module, frames: int, language_id: int, textnorm_id: int) -> None:
        super().__init__()
        self.embed = export_model.embed
        self.encoder = export_model.encoder
        self.ctc = export_model.ctc
        self.frames = frames
        device = next(self.embed.parameters()).device
        self.register_buffer(
            "language_query",
            self.embed(torch.tensor([language_id], dtype=torch.int32, device=device)).unsqueeze(1).detach(),
            persistent=False,
        )
        self.register_buffer(
            "textnorm_query",
            self.embed(torch.tensor([textnorm_id], dtype=torch.int32, device=device)).unsqueeze(1).detach(),
            persistent=False,
        )
        self.register_buffer(
            "event_emo_query",
            self.embed(torch.tensor([[1, 2]], dtype=torch.int32, device=device)).detach(),
            persistent=False,
        )
        self.register_buffer(
            "speech_lengths_new",
            torch.tensor([frames + 4], dtype=torch.int32, device=device),
            persistent=False,
        )

    def forward(self, speech: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        speech = torch.cat((self.textnorm_query, speech), dim=1)
        speech = torch.cat((self.language_query, self.event_emo_query, speech), dim=1)
        encoder_out, encoder_out_lens = self.encoder(speech, self.speech_lengths_new)
        if isinstance(encoder_out, tuple):
            encoder_out = encoder_out[0]
        ctc_logits = self.ctc.ctc_lo(encoder_out)
        return ctc_logits, encoder_out_lens


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--frames", type=int, default=51)
    parser.add_argument("--opset-version", type=int, default=18)
    parser.add_argument("--language-id", type=int, default=0)
    parser.add_argument("--textnorm-id", type=int, default=14)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.model.is_dir():
        raise FileNotFoundError(f"Model directory not found: {args.model}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    auto_model = AutoModel(model=str(args.model), device=args.device, disable_update=True)
    export_model = auto_model.model.export(device=args.device, max_seq_len=512)
    export_model = export_model.to(device=args.device)
    export_model.eval()
    static_model = StaticSenseVoiceExport(
        export_model=export_model,
        frames=args.frames,
        language_id=args.language_id,
        textnorm_id=args.textnorm_id,
    ).to(device=args.device)
    static_model.eval()

    speech = torch.randn(1, args.frames, 560, device=args.device)
    output_path = args.output_dir / f"model_b1_f{args.frames}.onnx"

    with torch.no_grad():
        torch.onnx.export(
            static_model,
            (speech,),
            str(output_path),
            verbose=False,
            do_constant_folding=True,
            opset_version=args.opset_version,
            input_names=["speech"],
            output_names=["ctc_logits", "encoder_out_lens"],
            dynamic_axes=None,
            dynamo=False,
        )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
