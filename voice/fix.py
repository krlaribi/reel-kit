# Voice-over clean-up: echo removal, tone, gate, compression, loudness.
#   python fix.py in.wav out.wav [--light] [--taps N] [--dry]
# --light skips gate and compression, --dry skips echo removal (close-mic takes),
# --taps sets echo-removal strength (10 default, 30 for echoey rooms).
import sys, numpy as np, soundfile as sf, librosa
from nara_wpe.wpe import wpe
from nara_wpe.utils import stft, istft
from pedalboard import (Pedalboard, HighpassFilter, LowShelfFilter, PeakFilter, HighShelfFilter,
                        Compressor, NoiseGate, Limiter, Gain)
inp, out = sys.argv[1], sys.argv[2]; light = '--light' in sys.argv
taps = int(sys.argv[sys.argv.index('--taps') + 1]) if '--taps' in sys.argv else 10
y, sr = sf.read(inp); y = y if y.ndim == 1 else y.mean(1)
if sr != 48000: y = librosa.resample(y, orig_sr=sr, target_sr=48000); sr = 48000
# 1. dereverb (WPE)
if '--dry' not in sys.argv:
  Y = stft(y[None], size=1024, shift=256).transpose(2, 0, 1)
  Z = wpe(Y, taps=taps, delay=3, iterations=3, statistics_mode='full').transpose(1, 2, 0)
  y = istft(Z, size=1024, shift=256)[0][:len(y)]
# 2. tone: less boom and mud, more presence and air
chain = [HighpassFilter(80), LowShelfFilter(160, -4.0, 0.7), PeakFilter(320, -3.0, 1.0),
         PeakFilter(3500, 4.0, 0.9), HighShelfFilter(8000, 3.0, 0.7)]
if not light:
    chain += [NoiseGate(threshold_db=-50, ratio=4, attack_ms=2, release_ms=120),
              Compressor(threshold_db=-20, ratio=2.5, attack_ms=8, release_ms=120)]
y = Pedalboard(chain)(y.astype(np.float32), sr)
# 3. loudness to ~-16 LUFS-ish (RMS of speech) and peak limit
rms = np.sqrt(np.mean(y[np.abs(y) > 0.01]**2)); y = y * (10**(-18/20) / rms)
y = Pedalboard([Limiter(threshold_db=-1.5, release_ms=80)])(y.astype(np.float32), sr)
pk = np.abs(y).max()
if pk > 10**(-1/20): y = y * (10**(-1/20) / pk)  # hard ceiling at -1 dBFS
sf.write(out, y, sr, subtype='PCM_24')
