#!/usr/bin/env python3
"""Turn a reference video into a study folder: contact sheets, cut list, word-timed transcript.

  uv run --with pillow --with imageio-ffmpeg --with faster-whisper python teardown/teardown.py <out-folder> <video> [<audio>]

<video> is a local file or a direct .mp4 link. Pass <audio> too when the platform serves picture
and sound as separate streams (DASH); they are muxed into src.mp4.
Writes src.mp4, cuts.txt (seconds), sheets/ (a frame every 0.33 s with its time printed, 8x5 per
sheet), transcript.txt (skipped if faster-whisper is missing) and stats.txt (duration, shots, pace). Hand the folder to Claude, or
read the sheets yourself, to see exactly how a video is paced and cut.
Uses ffmpeg from FFMPEG, then PATH, then the imageio-ffmpeg package. Study videos you have the right to use.
"""
import glob, os, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageChops, ImageStat


def find_ffmpeg():
    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if ff: return ff
    try:
        import imageio_ffmpeg                    # bundled binary, so `uv run --with imageio-ffmpeg` needs no install
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found: install it, set FFMPEG, or run with imageio-ffmpeg")


FF = find_ffmpeg()


def ff(*args):
    subprocess.run([FF, "-v", "error", "-y", *args], check=True)


def fetch(src, dst):
    if os.path.exists(src):
        shutil.copy(src, dst)
    else:
        subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "-o", dst, src], check=True)


def main(out, video, audio=None):
    os.makedirs(out + "/sheets", exist_ok=True)
    tmp = tempfile.mkdtemp()
    fetch(video, f"{tmp}/v.mp4")
    if audio:
        fetch(audio, f"{tmp}/a.mp4")
        ff("-i", f"{tmp}/v.mp4", "-i", f"{tmp}/a.mp4", "-c", "copy", "-map", "0:v", "-map", "1:a", out + "/src.mp4")
    else:
        shutil.copy(f"{tmp}/v.mp4", out + "/src.mp4")

    # frames at 6 fps, cuts from frame differences, sheets at 3 fps (8x5 per sheet)
    fps = 6
    ff("-i", out + "/src.mp4", "-r", str(fps), "-s", "270x480", f"{tmp}/f%04d.jpg")
    fr = sorted(glob.glob(f"{tmp}/f*.jpg"))
    cuts, prev = [], None
    for i, f in enumerate(fr):
        im = Image.open(f).convert("L").resize((90, 160))
        if prev is not None and ImageStat.Stat(ImageChops.difference(im, prev)).mean[0] > 22:
            cuts.append(round(i / fps, 2))
        prev = im
    open(out + "/cuts.txt", "w").write(" ".join(map(str, cuts)) + "\n")
    dur = len(fr) / fps
    shots = [b - a for a, b in zip([0] + cuts, cuts + [dur])]
    stats = [f"duration {dur:.1f} s", f"shots {len(shots)}, average {dur / len(shots):.2f} s, longest {max(shots):.2f} s",
             f"first cut {cuts[0] if cuts else dur:.2f} s, cuts in the first 3 s: {sum(c < 3 for c in cuts)}"]
    sel, n, W, H = fr[::2], 40, 270, 480
    for s in range(0, len(sel), n):
        chunk = sel[s:s + n]
        sh = Image.new("RGB", (W * 8, H * ((len(chunk) + 7) // 8)), "black")
        for j, f in enumerate(chunk):
            im = Image.open(f)
            dr = ImageDraw.Draw(im)
            dr.rectangle([0, 0, 62, 22], fill="black")
            dr.text((4, 4), f"{(s + j) * 2 / fps:5.2f}", fill="yellow")
            sh.paste(im, ((j % 8) * W, (j // 8) * H))
        a, b = s * 2 / fps, (s + len(chunk) - 1) * 2 / fps
        sh.save(f"{out}/sheets/s{s // n + 1:02d}_{a:04.1f}-{b:04.1f}.jpg", quality=82)

    # transcript
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        open(out + "/stats.txt", "w").write("\n".join(stats) + "\n")
        print("faster-whisper not installed: no transcript"); print("\n".join(stats)); return
    import numpy as np                           # raw 16 kHz samples, so Whisper never has to decode the file itself
    pcm = subprocess.run([FF, "-v", "error", "-i", out + "/src.mp4", "-vn", "-ac", "1", "-ar", "16000",
                          "-f", "f32le", "-"], check=True, capture_output=True).stdout
    segs, _ = WhisperModel("small", compute_type="int8").transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True)
    words = []
    with open(out + "/transcript.txt", "w") as t:
        for s in segs:
            t.write(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}\n")
            t.write("   " + " ".join(f"{w.word.strip()}@{w.start:.2f}" for w in s.words) + "\n")
            words += s.words
    if words:
        spoken = words[-1].end - words[0].start
        stats += [f"words {len(words)}, {len(words) / spoken:.1f} words/s while speaking",
                  f"first word at {words[0].start:.2f} s, words in the first 3 s: {sum(w.start < 3 for w in words)}"]
    open(out + "/stats.txt", "w").write("\n".join(stats) + "\n")
    print("\n".join(stats))


if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(*sys.argv[1:4])
