"""
Normalization Layer — maps all metric values to 0–1 scale.
"""

import numpy as np
from typing import List, Dict

def normalize(records: List[Dict]) -> List[Dict]:
    """Min-max normalize each metric column independently."""
    if not records:
        return records

    metric_keys = [
        'initial_weight', 'impact_score', 'susceptibility',
        'execution_probability', 'structural_complexity'
    ]

    for key in metric_keys:
        vals = np.array([r[key] for r in records], dtype=float)
        mn, mx = vals.min(), vals.max()
        if mx - mn < 1e-9:
            normed = np.full_like(vals, 0.5)
        else:
            normed = (vals - mn) / (mx - mn)
        for r, v in zip(records, normed):
            r[f'{key}_norm'] = round(float(v), 4)

    return records