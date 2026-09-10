"""Fixed-shape, structured-output Student V0 using J6P-friendly operators."""

from __future__ import annotations

import torch
from torch import Tensor, nn

from .contract import (
    BEHAVIORS,
    COMPLETION_TYPES,
    ON_FAILURE,
    REPLAN_CONDITIONS,
    StudentShapeContract,
    TARGET_LANES,
)


class TinyVisionEncoder(nn.Module):
    def __init__(self, output_width: int = 512) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        channels = (3, 32, 64, 128, 256, 384)
        for input_channels, output_channels in zip(channels, channels[1:]):
            layers.extend((
                nn.Conv2d(input_channels, output_channels, kernel_size=3, stride=2, padding=1),
                nn.ReLU(inplace=False),
            ))
        self.features = nn.Sequential(*layers)
        # The fifth stride-2 block produces a fixed 7x7 map.  A 2x2 average
        # pool retains a coarse 3x3 spatial grid, unlike global pooling which
        # made left/right objects nearly indistinguishable.
        self.pool = nn.AvgPool2d(kernel_size=2, stride=2)
        self.projection = nn.Linear(channels[-1] * 3 * 3, output_width)
        self.activation = nn.ReLU(inplace=False)

    def forward(self, rgb: Tensor) -> Tensor:
        value = self.pool(self.features(rgb)).flatten(1)
        return self.activation(self.projection(value))


class FixedVectorEncoder(nn.Module):
    def __init__(self, input_width: int, output_width: int = 512) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_width, output_width),
            nn.ReLU(inplace=False),
            nn.Linear(output_width, output_width),
            nn.ReLU(inplace=False),
        )

    def forward(self, value: Tensor) -> Tensor:
        return self.layers(value)


class StudentPlannerV0(nn.Module):
    """About 21M FP32 parameters; no dynamic axes or Python control flow."""

    model_id = "student-v0-r2-fp32"

    def __init__(self, contract: StudentShapeContract | None = None) -> None:
        super().__init__()
        self.contract = contract or StudentShapeContract()
        width = 512
        self.vision_encoder = TinyVisionEncoder(width)
        self.text_encoder = FixedVectorEncoder(self.contract.text_length, width)
        self.target_encoder = FixedVectorEncoder(
            self.contract.max_targets * self.contract.target_features, width,
        )
        self.state_encoder = FixedVectorEncoder(self.contract.state_features, width)
        self.fusion = nn.Sequential(
            nn.Linear(width * 4, 3072),
            nn.ReLU(inplace=False),
            nn.Linear(3072, 3072),
            nn.ReLU(inplace=False),
            nn.Linear(3072, 1024),
            nn.ReLU(inplace=False),
        )
        fused_width = 1024
        steps = self.contract.max_steps
        self.plan_length_head = nn.Linear(fused_width, steps)
        self.behavior_head = nn.Linear(fused_width, steps * len(BEHAVIORS))
        self.target_pointer_head = nn.Linear(fused_width, steps * (self.contract.max_targets + 1))
        self.target_lane_head = nn.Linear(fused_width, steps * len(TARGET_LANES))
        self.target_speed_head = nn.Linear(fused_width, steps)
        self.completion_head = nn.Linear(fused_width, steps * len(COMPLETION_TYPES))
        self.failure_head = nn.Linear(fused_width, steps * len(ON_FAILURE))
        self.confidence_head = nn.Linear(fused_width, 1)
        self.confirmation_head = nn.Linear(fused_width, 1)
        self.replan_head = nn.Linear(fused_width, len(REPLAN_CONDITIONS))

    def forward(
        self,
        rgb: Tensor,
        text_tokens: Tensor,
        targets: Tensor,
        state: Tensor,
    ) -> tuple[Tensor, ...]:
        batch = rgb.shape[0]
        visual = self.vision_encoder(rgb)
        text = self.text_encoder(text_tokens)
        target = self.target_encoder(targets.flatten(1))
        state_value = self.state_encoder(state)
        fused = self.fusion(torch.cat((visual, text, target, state_value), dim=1))
        steps = self.contract.max_steps
        return (
            self.plan_length_head(fused),
            self.behavior_head(fused).reshape(batch, steps, len(BEHAVIORS)),
            self.target_pointer_head(fused).reshape(
                batch, steps, self.contract.max_targets + 1,
            ),
            self.target_lane_head(fused).reshape(batch, steps, len(TARGET_LANES)),
            torch.sigmoid(self.target_speed_head(fused)).reshape(batch, steps) * 50.0,
            self.completion_head(fused).reshape(batch, steps, len(COMPLETION_TYPES)),
            self.failure_head(fused).reshape(batch, steps, len(ON_FAILURE)),
            torch.sigmoid(self.confidence_head(fused)),
            self.confirmation_head(fused),
            self.replan_head(fused),
        )


__all__ = ["StudentPlannerV0", "TinyVisionEncoder"]
