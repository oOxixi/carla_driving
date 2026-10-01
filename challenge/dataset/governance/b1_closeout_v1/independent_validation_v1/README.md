# B1 Independent Validation v1

Dataset version: `b1_independent_validation_v1`

This frozen Independent Validation set contains the **240 samples /
240 groups** remaining from the D2 v1.1 reserved pool after the
300-sample Calibration v1 allocation.

Identity rule:

`D2 v1.1 reserved pool (540) - Calibration v1 (300) = Independent Validation v1 (240)`

This set is **not training data**, **not development data**,
**not calibration data**, and is **not designated Frozen Test by B1**.

The case identities are frozen in `case_manifest.json` and bound by
`case_set_digest.json`.

A3 must not use these cases or labels for training, model selection,
hyperparameter tuning, or error-driven iteration.
