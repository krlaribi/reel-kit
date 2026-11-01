# Pre-review QA for a vertical video render: catches the mechanical faults you'd otherwise find by eye.
# Run it on every draft and final before you send the link.
#
#   uv run --with numpy --with pillow --with imageio-ffmpeg python qa/qa.py <render.mp4> [--sheet]
#
# Checks:
#   black frames      a frame (almost) all black mid-video: a skipped frame on a zoom or cut
#   dropouts          one frame much darker than both neighbours: an oversized layer dropped by the renderer
#   frozen stretches  > 1.5 s where nothing on screen moves
#   shot length       average and longest shot (short-form sweet spot is 1.5–2.5 s)
#   flicker           repeated bright/dark pulses in a 2 s window (a flash should fire once, then stop)
#   silent gaps       > 1.2 s of near-silence mid-video: a shot nobody voiced
#   level             peak and RMS of the mix (voice-over ≈ −16 to −20 dBFS RMS, never clipping)
# --sheet also writes <render>-SHEET.png: one frame every 2 s with timecodes, for review at a glance.
# Exit code 1 when a fault is found, so it can gate a render script or CI.
# Uses ffmpeg from FFMPEG, then PATH, then the imageio-ffmpeg package.
import shutil, subprocess, sys, os
import numpy as np

def find_ffmpeg():
    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if ff: return ff
    try:
        import imageio_ffmpeg                    # bundled binary, so `uv run --with imageio-ffmpeg` needs no install
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found: install it, set FFMPEG, or run with imageio-ffmpeg")


FF = find_ffmpeg()
W, H = 108, 192                                   # analysis size (1/10 of 1080×1920)


def ff(args, **kw):
    return subprocess.run([FF, "-hide_banner", "-loglevel", "error", *args], capture_output=True, **kw)


def probe(path):
    err = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    fps = 30.0
    for tok in err.split(","):
        if " fps" in tok:
            try: fps = float(tok.strip().split(" ")[0])
            except ValueError: pass
    return fps


def frames(path, w=W, h=H):
    raw = ff(["-i", path, "-vf", f"scale={w}:{h},format=gray", "-f", "image2pipe", "-c:v", "rawvideo", "-"]).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def audio(path, sr=16000):
    raw = ff(["-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "wav", "-c:a", "pcm_s16le", "-"]).stdout
    i = raw.find(b"data") + 8 if b"data" in raw[:200] else 44   # skip the wav header
    return np.frombuffer(raw[i:i + (len(raw) - i) // 2 * 2], np.int16).astype(np.float32) / 32768, sr


def tc(t): return f"{int(t // 60)}:{t % 60:05.2f}"


def spans(mask, fps, min_len):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]: j += 1
            if (j - i) / fps >= min_len: out.append((i / fps, j / fps))
            i = j
        else: i += 1
    return out


def main():
    path = sys.argv[1]
    fps = probe(path)
    f = frames(path)
    n = len(f); dur = n / fps
    mean = f.mean(axis=(1, 2))
    diff = np.r_[0, np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))]
    issues, checks, notes = [], [], []   # issues fail the QA; checks are for a human glance (a planned hold is a deliberate freeze)

    # black frames (skip the first and last 0.2 s: a hard open/close is allowed)
    edge = int(0.2 * fps)
    peak = f.max(axis=(1, 2))                    # dark shots still carry content; an empty frame has none
    blk = [i for i in range(edge, n - edge) if peak[i] < 24]
    if blk: issues.append(f"BLACK FRAMES: {len(blk)} at " + ", ".join(tc(i / fps) for i in blk[:12]) + (" …" if len(blk) > 12 else ""))

    # single-frame dropouts: darker than both neighbours by > 45 %
    drop = [i for i in range(1, n - 1) if mean[i] < 0.55 * min(mean[i - 1], mean[i + 1]) and mean[i] >= 4]
    if drop: issues.append(f"DROPOUTS (1-frame dark flashes): {len(drop)} at " + ", ".join(tc(i / fps) for i in drop[:12]))

    # frozen stretches: whole frame changes by < 0.15 grey levels per frame for > 1.5 s
    frozen = spans(diff < 0.15, fps, 1.5)
    if frozen: checks.append("FROZEN (nothing moves > 1.5 s): " + ", ".join(f"{tc(a)}–{tc(b)}" for a, b in frozen))

    # shot cuts: frame difference spikes well above the local motion level
    base = np.convolve(diff, np.ones(9) / 9, mode="same")
    cuts = [i for i in range(1, n) if diff[i] > 18 and diff[i] > 3 * base[i]]
    edges = [0] + cuts + [n]
    shots = np.diff(edges) / fps
    notes.append(f"shots: {len(shots)}, average {shots.mean():.2f} s, longest {shots.max():.2f} s at {tc(edges[int(shots.argmax())] / fps)}")
    long = [(edges[k] / fps, s) for k, s in enumerate(shots) if s > 4.5]
    if long: checks.append("LONG SHOTS (> 4.5 s, check the camera keeps moving): " + ", ".join(f"{tc(a)} ({s:.1f} s)" for a, s in long))

    # flicker: ≥ 4 brightness reversals of > 6 grey levels inside any 2 s window
    d = np.diff(mean)
    rev = [i for i in range(1, len(d)) if abs(d[i]) > 6 and abs(d[i - 1]) > 6 and np.sign(d[i]) != np.sign(d[i - 1])]
    flick, k = [], 0
    while k < len(rev):
        grp = [r for r in rev if rev[k] <= r < rev[k] + 2 * fps]
        if len(grp) >= 4: flick.append(rev[k] / fps); k += len(grp)
        else: k += 1
    if flick: issues.append("FLICKER (repeating pulses, should fire once): " + ", ".join(tc(t) for t in flick))

    # audio: silent gaps mid-reel and levels
    a, sr = audio(path)
    if len(a):
        win = int(0.05 * sr)
        rms = np.sqrt(np.convolve(a ** 2, np.ones(win) / win, mode="same")[::win] + 1e-12)
        db = 20 * np.log10(rms)
        quiet = spans(db < -45, 1 / 0.05, 1.2)
        quiet = [(s, e) for s, e in quiet if s > 0.5 and e < len(a) / sr - 2.0]
        if quiet: issues.append("SILENT GAPS (> 1.2 s, is this shot voiced?): " + ", ".join(f"{tc(s)}–{tc(e)}" for s, e in quiet))
        apk = 20 * np.log10(np.abs(a).max() + 1e-9)
        tot = 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)
        notes.append(f"audio: peak {apk:.1f} dBFS, RMS {tot:.1f} dBFS")
        if apk > -0.5: issues.append(f"CLIPPING: peak {apk:.1f} dBFS")
    else:
        issues.append("NO AUDIO TRACK")

    print(f"QA  {os.path.basename(path)}  ·  {dur:.1f} s  ·  {fps:g} fps  ·  {n} frames")
    for s in notes: print("  ·", s)
    print("  ✓ no faults" if not issues else "\n".join("  ✗ " + s for s in issues))
    for s in checks: print("  ? " + s)

    if "--sheet" in sys.argv:
        from PIL import Image, ImageDraw
        tw, th, cols = 216, 384, 8
        big = frames(path, tw, th)
        idx = list(range(0, len(big), int(2 * fps)))
        rows = (len(idx) + cols - 1) // cols
        sheet = Image.new("L", (cols * tw, rows * (th + 22)), 255)
        dr = ImageDraw.Draw(sheet)
        for k, i in enumerate(idx):
            x, y = (k % cols) * tw, (k // cols) * (th + 22)
            sheet.paste(Image.fromarray(big[i].astype(np.uint8)), (x, y))
            dr.text((x + 6, y + th + 4), tc(i / fps), fill=0)
        out = os.path.splitext(path)[0] + "-SHEET.png"
        sheet.save(out); print("  sheet:", out)
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
