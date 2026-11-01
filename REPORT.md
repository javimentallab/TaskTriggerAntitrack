# REPORT — TaskTriggerAntitrack

[Versión en español](REPORT.es.md)

Technical report on merging **Alarm** and **Resume terminals** into a single desktop
application.

## 1. Origin

| Tool | Stack | What it did |
|------|-------|-------------|
| **Alarm** (`proyecto_alarma 1.2`) | Python + tkinter + pygame | A list of alarms with a start and end time; it picked a **random firing time** inside the range; when it fired it played a `.wav`, showed a pop-up and **ran a program** or opened a file/URL. |
| **Resume terminals** | PowerShell + WPF | At a **fixed time**, it focused every window matching a title filter and typed a text + **Enter** (to resume Claude when the usage limit resets). |

## 2. Merged model

They become a single **task scheduler** where each entry combines two independent axes:

- **When** — `fixed` (time `HH:MM`) or `random` (a random moment in `[from, to]`), with
  `daily` to reschedule it every day.
- **What** — `terminal` (type text + Enter into windows matching a filter) or `program`
  (run a program / open a file or URL).
- **Extras** — `sound` and `popup` (a pop-up with a message).

The result: Resume terminals **gains** the random time and Alarm **gains** typing into
terminals. Any combination is valid (for example, opening a URL at a random time, or
typing `continua` into the terminals at a fixed time).

## 3. Random interval: anti-tracking

Firing at a random time within a range is an **anti-tracking** feature, not a mere
embellishment:

- A task that always opens a website or runs a program at **exactly the same time** creates
  a **predictable schedule**. An observer (of the network traffic or the system) can
  anticipate *when* the connection will happen and **link** it to the user.
- By **randomising** the time within a wide window, the exact moment is no longer predictable
  on each run: the **time signature** disappears and the link "known time → specific website
  or program" is broken.
- With *Repeat every day*, the random time is **drawn again** every day, so the pattern does
  not settle from one day to the next either.

Implementation: `compute_next()` takes the day's `[start, end]` window (windows that cross
midnight are supported), discards the part already gone, and picks
`start + random(0, remaining_seconds)`.

## 4. Technical decisions

- **Python/tkinter base** (Alarm's) because it is cross-platform; porting to Linux with fewer
  dependencies and files was already a goal of the Alarm project.
- **No pip dependencies.** `pygame` was removed: the sound uses `winsound` (Windows), `afplay`
  (macOS) or `aplay`/`paplay` (Linux).
- **Typing into windows without external libraries:**
  - *Windows*: `ctypes` over `user32`/`kernel32`. Enumeration with `EnumWindows`, real focus
    with the `AttachThreadInput` + `SetForegroundWindow` trick (it gets past Windows' focus
    lock), and typing with `SendInput` using `KEYEVENTF_UNICODE` (literal text, no keyboard
    maps) + `VK_RETURN`.
  - *Linux (X11)*: `xdotool search --name` + `windowactivate` + `type` + `key Return`.
- **Firing in a separate thread.** The action (sound + typing/program) runs in a
  `threading.Thread` so the interface does not freeze; the pop-up is shown **after** the
  typing so it does not steal focus from the terminals.
- **Persistence** in `alarms.json` with the next firing (`next_fire`) already computed; on
  startup, firings whose time has passed are recalculated.

## 5. Known limitations

- The window has to stay **open** to fire (it is not a service). For persistent firing, create
  a Scheduled Task (Windows) or a `.timer`/cron job (Linux) that launches the script.
- On **Wayland**, typing into other apps' windows may be restricted by the compositor.
- Unicode typing skips characters outside the BMP (irrelevant for typical commands).

## 6. Structure

```
tasktriggerantitrack.py     application (GUI + scheduler + actions)
tta_lang.py                 interface texts in 15 languages
tasktriggerantitrack.cmd    launcher without a console (Windows)
alarm_sound.wav             firing sound
icon.ico                    icon (clock + random arrows)
alarms.json                 saved tasks (not versioned)
```
