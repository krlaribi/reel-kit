# reel-kit

Small command-line tools I use to make short-form documentary reels with code and Claude Code.
Each one does one job in the production line, and each was written because I kept doing that job by hand.

<p align="center">
  <img src="docs/quartz.gif" width="280" alt="Opening of the reel 'Quartz': a Swiss village in 1967, then a grid of watchmakers emptying out">
  <br><sub>The opening of <i>Quartz</i>, checked with these tools before it went out. More on <a href="https://www.instagram.com/anatomyofideass/">@anatomyofideass</a>.</sub>
</p>

| Tool | What it does |
|---|---|
| [`qa/qa.py`](qa/qa.py) | Checks a render before anyone sees it: black frames, one-frame dropouts, frozen stretches, flicker, silent gaps, clipping, shot lengths. Writes a contact sheet with timecodes. Exits 1 on a fault, so it can gate a render. |
| [`.claude/agents/reel-qa.md`](.claude/agents/reel-qa.md) | A Claude Code agent that runs `qa.py`, reads the contact sheet, goes through your checklist and answers **READY** or **NOT READY** with timecodes. It reports; it never edits. |
| [`teardown/teardown.py`](teardown/teardown.py) | Turns a reference video you want to learn from into a study folder: contact sheets every 0.33 s, a cut list and a word-timed transcript. |
| [`voice/fix.py`](voice/fix.py) | Cleans a home-recorded voice-over: echo removal, tone, gate, compression, loudness at about −18 dBFS. |
| [`voice/closemic.py`](voice/closemic.py) | Repairs close-mic takes: mouth clicks, plosive pops, harsh S's, hot peaks. |
| [`voice/lift.py`](voice/lift.py) | Changes a voice-over's pace and pitch without artefacts. |

## Setup

You need [uv](https://docs.astral.sh/uv/). It fetches every Python dependency on the fly, ffmpeg included, so there's nothing else to install.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/krlaribi/reel-kit && cd reel-kit
```

## Use

**Check a render**

```bash
uv run --with numpy --with pillow --with imageio-ffmpeg python qa/qa.py out/my-reel.mp4 --sheet
```

```
QA  my-reel.mp4  ·  72.9 s  ·  30 fps  ·  2186 frames
  · shots: 36, average 2.02 s, longest 7.50 s at 0:28.87
  · audio: peak -0.7 dBFS, RMS -16.9 dBFS
  ✓ no faults
  ? LONG SHOTS (> 4.5 s, check the camera keeps moving): 0:28.87 (7.5 s), 1:08.03 (4.8 s)
  sheet: out/my-reel-SHEET.png
```

`✗` lines are faults. `?` lines are for a human glance: a long hold can be on purpose.

**Let Claude Code check it.** Copy `.claude/agents/reel-qa.md` into your project's `.claude/agents/`, optionally write a
`CHECKS.md` with your own rules (one checkable line each), then ask Claude Code *"is out/my-reel.mp4 ready?"*.

**Study a reference**

```bash
uv run --with pillow --with imageio-ffmpeg --with faster-whisper python teardown/teardown.py refs/that-reel video.mp4
```

Open `refs/that-reel/sheets/` to see every cut and how long each shot holds, or hand the folder to Claude and ask what makes it work.
If a platform serves picture and sound as separate streams, pass the audio as a third argument.
Only study videos you have the right to use.

**Clean a voice-over**

```bash
uv run --with-requirements voice/requirements.txt python voice/fix.py take.wav take-clean.wav
uv run --with-requirements voice/requirements.txt python voice/closemic.py take-clean.wav take-final.wav   # close-mic takes only
uv run --with-requirements voice/requirements.txt python voice/lift.py take-final.wav take-fast.wav 1.05 0.5  # 5 % faster, half a semitone up
```

## Why

I'm a marketer, not an engineer. I make documentary reels on [Instagram @anatomyofideass](https://www.instagram.com/anatomyofideass/)
entirely in code, with Claude Code as my editor. Every time I caught the same mistake twice by eye, I turned the check into a tool.
This repo is those tools.

## Licence

MIT. See [LICENSE](LICENSE).
