# How I make a reel: the principles

I make 60–100 second documentary reels about how an idea, a technology or a business really worked
([@anatomyofideass](https://www.instagram.com/anatomyofideass/)). The aim in one line: **explain like Vox, edit like A24.**
Clear explanations, fewer and truer images, and silence used as punctuation.

Ten rules I keep coming back to. None of them needs my tools; they work in CapCut or Premiere as well as in code.

## Story

**1. Pick a story with a turn.** A topic is ready when you can say it in one sentence with a "but" in the middle:
*"Switzerland invented the quartz watch, but Japan sold it."* No turn, no reel.

**2. Write the last image first.** Decide the final frame before any line of script, then keep only the beats the viewer needs to feel it.

**3. A script is a chain of questions.** People leave when a question is answered and no new one is asked.
Open the next question before the last one closes, and join your beats with "because", never "and then".

**4. Study before you make.** Take apart two or three reels you admire, frame by frame. Steal moves, never footage.
([reel-teardown](https://github.com/krlaribi/reel-teardown) does this for you.)

## Pictures

**5. Show what is said, on its word.** Every person, place and product named in the voice appears when it's said.

**6. Make every number an object.** A share is a grid of people going dark, money is a price tag, time is a real clock.

**7. One silence.** At the turn, drop the music for a few seconds. It will be the loudest moment in the reel.

**8. End on the frame you opened on.** The reel loops, and people watch it again.

## Process

**9. Approve words before pictures, pictures before the edit.** Each change is cheaper at the step before.
A script change after the voice is recorded is the most expensive change there is.

**10. Let a machine check before a person looks.** Run [`qa/qa.py`](../qa/qa.py) on every export, and turn every note you get twice
into one checkable line in a `CHECKS.md` that the [reel-qa agent](../.claude/agents/reel-qa.md) reads on every render.

---

See the rules at work in one reel: the [full teardown of *Quartz*](https://github.com/krlaribi/reel-teardown/blob/main/examples/quartz/BREAKDOWN.md).
