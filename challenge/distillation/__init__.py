"""A3 knowledge-distillation training boundary."""

from .label_encoder import DistillationLabelEncoder, LabelEncodingError

__all__ = ["DistillationLabelEncoder", "LabelEncodingError"]
