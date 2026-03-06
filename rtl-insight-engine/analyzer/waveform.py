"""
Waveform Simulator — generates synthetic toggle waveforms
based on execution probability and signal dependencies.
"""

import numpy as np
from typing import Dict, List

class WaveformSimulator:

    def __init__(self, records: List[Dict], cycles: int = 64):
        self.records = records
        self.cycles = cycles

    def simulate(self) -> Dict[str, List[int]]:
        """
        Generate synthetic 0/1 waveform per signal.
        Based on execution probability — higher prob = more toggles.
        """
        np.random.seed(42)
        waveforms = {}
        seen = set()

        for r in self.records:
            sig = r['signal']
            if sig in seen:
                continue
            seen.add(sig)

            ep = r.get('execution_probability', 0.5)
            wave = []
            val = 0
            for cycle in range(self.cycles):
                # Toggle probability based on execution probability
                if np.random.random() < ep * 0.6:
                    val = 1 - val
                wave.append(val)
            waveforms[sig] = wave

        return waveforms

    def compute_toggle_count(self, waveforms: Dict) -> Dict[str, int]:
        """Count number of 0→1 transitions per signal."""
        toggles = {}
        for sig, wave in waveforms.items():
            count = sum(1 for i in range(1, len(wave))
                        if wave[i] != wave[i-1])
            toggles[sig] = count
        return toggles