# PsychoPy Python Scripting — Agent Context Document

> Reference for coding agents writing psychophysics experiments in pure Python using PsychoPy. No Builder/GUI — code only.

## Installation

```bash
pip install psychopy
```

Use a virtual environment. The package pulls in all core dependencies (pyglet, numpy, scipy, etc.).

---

## Core Modules

| Module              | Import                        | Purpose |
|---------------------|-------------------------------|---------|
| `psychopy.visual`   | `from psychopy import visual` | Window, all visual stimuli (TextStim, ImageStim, GratingStim, Rect, Circle, etc.) |
| `psychopy.core`     | `from psychopy import core`   | Clocks, timers, `wait()`, `quit()` |
| `psychopy.clock`    | `from psychopy import clock`  | Additional timing utilities (MonotonicClock, CountdownTimer, StaticPeriod) |
| `psychopy.event`    | `from psychopy import event`  | Keyboard (`getKeys`, `waitKeys`) and `Mouse` input |
| `psychopy.data`     | `from psychopy import data`   | TrialHandler, StairHandler, QuestHandler, ExperimentHandler — trial sequencing and data saving |
| `psychopy.monitors` | `from psychopy import monitors` | Monitor calibration profiles for accurate spatial units |
| `psychopy.sound`    | `from psychopy import sound`  | Audio playback (`Sound` class) |
| `psychopy.gui`      | `from psychopy import gui`    | Dialogue boxes for participant info |
| `psychopy.hardware` | `from psychopy import hardware` | Device interfaces (serial, parallel, etc.) |
| `psychopy.iohub`    | `from psychopy import iohub`  | Asynchronous high-precision event monitoring (keyboard, mouse, eye trackers) |

---

## Window Setup

### Constructor (key parameters)

```python
win = visual.Window(
    size=(1920, 1080),      # pixels
    fullscr=False,          # True for production (enables VSync)
    monitor='testMonitor',  # monitor profile name or Monitor object
    units='deg',            # 'deg', 'cm', 'pix', 'norm', 'height'
    color=(0, 0, 0),        # background color
    colorSpace='rgb',
    screen=0,               # display index for multi-monitor
    waitBlanking=True,      # wait for VSync on flip
    allowGUI=True,          # show OS window decorations
    checkTiming=True,
)
```

### `win.flip(clearBuffer=True)`

Swaps front/back buffers. Returns the wall-clock timestamp of the flip (useful for timing verification). `clearBuffer=True` (default) clears the back buffer after swap — everything must be redrawn each frame.

### Development vs. Production

- **Development:** `fullscr=False` — prevents lockout if your script hangs.
- **Production:** `fullscr=True` — enables proper VSync for frame-accurate timing.
- **Always** implement an escape key: check for `'escape'` in your main loop and call `core.quit()`.

---

## Monitor Calibration

Required for using `'deg'` or `'cm'` units (which you should prefer over `'pix'` or `'norm'` for psychophysics).

```python
from psychopy import monitors

mon = monitors.Monitor('myMonitor')
mon.setSizePix((1920, 1080))   # screen resolution
mon.setWidth(53.0)              # viewable screen width in cm
mon.setDistance(57.0)           # viewing distance in cm
mon.save()

win = visual.Window(monitor=mon, units='deg', fullscr=False)
```

---

## Timing

### Clocks

```python
trial_clock = core.Clock()            # resets to 0 on creation
trial_clock.reset()                    # reset to 0
t = trial_clock.getTime()             # seconds since last reset

countdown = core.CountdownTimer(5.0)   # counts down from 5s
while countdown.getTime() > 0:
    pass  # do work

mono = core.MonotonicClock()           # high-precision, cannot be reset to arbitrary time
```

### Frame-Based Timing (preferred for stimulus presentation)

Control stimulus duration by counting screen refreshes, not by calling `core.wait()`.

```python
# Show stimulus for exactly 60 frames
for frame in range(60):
    stim.draw()
    win.flip()
```

**Why:** `win.flip()` synchronizes to the monitor's refresh rate (VSync). Counting frames gives you hardware-locked timing precision. `core.wait()` is only ~1 ms accurate and doesn't sync to the display.

### `core.wait(secs, hogCPUperiod=0.2)`

Halts execution for `secs` seconds. For the last `hogCPUperiod` seconds, it busy-waits for precision. Use for inter-trial intervals where frame accuracy isn't critical.

### StaticPeriod

Insert a precisely-timed interval during which you can do work (load images, etc.):

```python
isi = core.StaticPeriod(screenHz=60, win=win)
isi.start(0.5)           # 500ms period begins
# ... do loading work here ...
isi.complete()           # blocks until the 500ms has elapsed
```

---

## Visual Stimuli

All stimuli share: `draw()` to render to back buffer, `.pos`, `.size`, `.color`, `.units`, `.opacity`, `.ori` (orientation).

| Class | Usage |
|-------|-------|
| `visual.TextStim(win, text='Hello', pos=(0,0), height=1.0, color='white', wrapWidth=20, alignText='center')` | Text display |
| `visual.ImageStim(win, image='file.png', pos=(0,0), size=(5,5))` | Image display |
| `visual.GratingStim(win, tex='sin', mask='gauss', sf=4, size=5)` | Gabor patches, gratings |
| `visual.Rect(win, width=2, height=2, fillColor='red')` | Rectangle |
| `visual.Circle(win, radius=1, fillColor='blue')` | Circle |
| `visual.ShapeStim(win, vertices=[...])` | Arbitrary polygons |

### Draw Loop Pattern

```python
# Everything visible must be drawn every frame before flip
fixation.draw()
stim.draw()
win.flip()
```

`win.flip()` clears the back buffer. If you don't redraw something, it disappears.

---

## Input Handling

### Keyboard (`psychopy.event`)

```python
# Non-blocking: check what's been pressed
keys = event.getKeys(keyList=['space', 'escape'], timeStamped=trial_clock)
# Returns: [('space', 0.523), ...] if timeStamped, else ['space', ...]

# Blocking: wait for a keypress
keys = event.waitKeys(maxWait=5.0, keyList=['left', 'right'])
# Returns: ['left'] or None on timeout
```

**Always call `event.clearEvents()` before a response window** to flush stale keypresses.

### Mouse (`psychopy.event.Mouse`)

```python
mouse = event.Mouse(win=win)
pos = mouse.getPos()                           # (x, y) in window units
buttons = mouse.getPressed(getTime=True)       # [btn0, btn1, btn2], [t0, t1, t2]
inside = mouse.isPressedIn(some_shape)         # click inside a stimulus
```

### iohub (high-precision alternative)

For experiments requiring sub-millisecond input precision, use `psychopy.iohub` instead of `psychopy.event`. It runs input monitoring on a separate process.

---

## Trial Management & Data

### TrialHandler

Manages trial sequencing with built-in randomization and data recording.

```python
conditions = data.importConditions('conditions.xlsx')  # or list of dicts
# e.g. [{'stim': 'A', 'correct': 'left'}, {'stim': 'B', 'correct': 'right'}]

trials = data.TrialHandler(
    trialList=conditions,
    nReps=5,                    # repetitions of each condition
    method='random',            # 'random', 'sequential', 'fullRandom'
    seed=42,                    # reproducibility
)

for trial in trials:
    # trial is a dict: {'stim': 'A', 'correct': 'left'}
    # ... present stimulus, collect response ...
    trials.addData('response', resp)
    trials.addData('rt', rt)

trials.saveAsWideText('data.csv')
```

### ExperimentHandler

Wraps one or more TrialHandlers for automatic, comprehensive logging.

```python
exp = data.ExperimentHandler(
    name='myExperiment',
    extraInfo={'participant': '01', 'session': 1},
    dataFileName='data/participant01',
    savePickle=True,
    saveWideText=True,
)

trials = data.TrialHandler(trialList=conditions, nReps=3)
exp.addLoop(trials)

for trial in trials:
    # ... run trial ...
    exp.addData('response', resp)
    exp.addData('rt', rt)
    exp.nextEntry()         # advance to next row in output

# Data auto-saved on garbage collection, or call:
exp.close()
```

### Adaptive Methods

```python
# Staircase (up-down)
staircase = data.StairHandler(
    startVal=10,
    nReversals=6,
    stepSizes=[4, 2, 1],       # step size decreases at each reversal
    nUp=1, nDown=3,             # 1-up 3-down rule
    stepType='lin',             # 'lin', 'db', 'log'
    minVal=0, maxVal=20,
)

for intensity in staircase:
    # ... present at `intensity`, get response ...
    staircase.addResponse(1)   # 1 = correct, 0 = incorrect
```

### Data Output Formats

| Method                | Format | Use case |
|-----------------------|--------|----------|
| `saveAsWideText()`    | CSV/TSV | One row per trial — R/SPSS/pandas compatible |
| `saveAsExcel()`       | XLSX   | Multiple worksheets with summaries |
| `saveAsPickle()`      | Pickle | Full Python object reimport |
| `saveAsJson()`        | JSON   | Data interchange |

---

## Participant Info Dialog

```python
info = {'participant': '', 'session': '001', 'age': ''}
dlg = gui.DlgFromDict(info, title='Experiment Setup', order=['participant', 'session', 'age'])
if not dlg.OK:
    core.quit()
```

---

## Minimal Experiment Skeleton

```python
from psychopy import visual, core, event, data, gui, monitors

# --- Setup ---
mon = monitors.Monitor('lab', width=53, distance=57)
mon.setSizePix((1920, 1080))

win = visual.Window(monitor=mon, units='deg', fullscr=False, color=(-1,-1,-1))
fixation = visual.TextStim(win, text='+', height=2)
stim = visual.TextStim(win, text='', height=2)

conditions = [{'word': 'LEFT', 'correct': 'left'}, {'word': 'RIGHT', 'correct': 'right'}]
trials = data.TrialHandler(conditions, nReps=3, method='random')
trial_clock = core.Clock()

# --- Run ---
try:
    for trial in trials:
        # Fixation (30 frames ≈ 500ms at 60Hz)
        for frame in range(30):
            fixation.draw()
            win.flip()

        # Stimulus
        stim.text = trial['word']
        event.clearEvents()
        trial_clock.reset()

        resp = None
        while resp is None:
            stim.draw()
            win.flip()
            keys = event.getKeys(keyList=['left', 'right', 'escape'], timeStamped=trial_clock)
            for key, rt in keys:
                if key == 'escape':
                    core.quit()
                resp = key
                trials.addData('response', resp)
                trials.addData('rt', rt)
                trials.addData('correct', int(resp == trial['correct']))

    trials.saveAsWideText('results.csv')

finally:
    win.close()
    core.quit()
```

---

## Agent Rules

1. **Never use `core.wait()` for stimulus duration.** Count frames with `win.flip()`.
2. **Always redraw every visible stimulus before each `win.flip()`.** The back buffer clears.
3. **Use `'deg'` or `'cm'` units** with a calibrated Monitor. Avoid `'pix'` and `'norm'`.
4. **Set `fullscr=False` in development**, `True` in production.
5. **Always implement escape key** (`'escape'` → `core.quit()`).
6. **Use `data.TrialHandler` + `data.ExperimentHandler`** for trials and logging. Do not write custom CSV loops.
7. **Call `event.clearEvents()` before each response window** to prevent stale keypress contamination.
8. **Wrap in `try/finally`** calling `win.close()` and `core.quit()` for clean shutdown.

---

## Reference Links

- [API Index](https://psychopy.org/api/index.html)
- [Visual stimuli](https://psychopy.org/api/visual.html)
- [Core (clocks, timing)](https://psychopy.org/api/core.html)
- [Event (keyboard, mouse)](https://psychopy.org/api/event.html)
- [Data (trials, handlers)](https://psychopy.org/api/data.html)
- [Monitors](https://psychopy.org/api/monitors.html)
- [Sound](https://psychopy.org/api/sound.html)
- [iohub](https://psychopy.org/api/iohub.html)
- [Coder view docs](https://psychopy.org/coder/index.html)
- [GitHub repo](https://github.com/psychopy/psychopy)
- [Workshop: coding an experiment](https://workshops.psychopy.org/3days/day3/codingAnExperiment.html)
