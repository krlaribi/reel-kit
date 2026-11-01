# Close-mic repair: mouth clicks, plosive pops, harsh S's, hot peaks. usage: closemic.py in.wav out.wav
# Run after fix.py --light (echo removal and tone first, then this repair).
import sys, numpy as np, soundfile as sf, scipy.signal as ss, librosa
from pedalboard import Pedalboard, Limiter
y, sr = sf.read(sys.argv[1]); y = y if y.ndim == 1 else y.mean(1)

# 1. mouth clicks: short spikes above 4 kHz -> pull that band down for ~6 ms around each one
b, a = ss.butter(4, 4000 / (sr / 2), 'high'); hf = ss.filtfilt(b, a, y)
env = np.abs(hf); loc = ss.medfilt(env, int(sr * 0.02) // 2 * 2 + 1) + 1e-5
g = np.ones_like(y); w = int(sr * 0.003)
for i in np.where(env / loc > 25)[0]: g[max(0, i - w):i + w] = 0.15
g = np.convolve(g, np.hanning(w) / np.hanning(w).sum(), 'same')
y = (y - hf) + hf * g

# 2-3. STFT gains: plosive pops (low-frequency bursts) and harsh S's (5-11 kHz spikes)
n_fft, hop = 1024, 240
Y = librosa.stft(y, n_fft=n_fft, hop_length=hop); P = np.abs(Y) ** 2
fr = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
band = lambda lo, hi: 10 * np.log10(P[(fr >= lo) & (fr < hi)].sum(0) + 1e-12)
lo, mid, sib = band(20, 150), band(300, 3000), band(5000, 11000)
tot = 10 * np.log10(P.sum(0) + 1e-12); sp = tot > np.percentile(tot, 95) - 30
G = np.ones_like(P)
r = lo - mid; pop = sp & (r > np.median(r[sp]) + 8)
G[np.ix_(fr < 180, pop)] = 10 ** (-12 / 20)                 # cut the thump, keep the voice
over = np.clip((sib - mid) - (-6), 0, 12)                   # de-ess: S's more than 6 dB under mids get pulled back
G[fr >= 4500, :] *= 10 ** (-over / 20)
G = ss.convolve2d(G, np.ones((1, 3)) / 3, mode='same', boundary='symm')
y = librosa.istft(Y * G, hop_length=hop, length=len(y))

# 4. hot peaks
y = Pedalboard([Limiter(threshold_db=-3, release_ms=60)])(y.astype(np.float32), sr)
pk = np.abs(y).max()
if pk > 10 ** (-1 / 20): y = y * (10 ** (-1 / 20) / pk)
sf.write(sys.argv[2], y, sr)
