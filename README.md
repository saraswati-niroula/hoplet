# Hoplet

**A little hopping companion for your Linux desktop.**

Every so often, a tiny chibi friend hops onto the bottom of your screen to remind
you to stand up, stretch, drink some water or rest your eyes. Then it hops
away again. It's a desktop pet, not a nagging productivity tool.

<p align="center"><img src="docs/characters.png" alt="Hoplet characters in six color themes" width="720"></p>

<p align="center"><img src="docs/visit.png" alt="Hoplet visiting with a reminder" width="220"></p>

- Pick a **girl or boy** character, give it **your own name**, and choose a **color theme**
  (Sakura pink, Fresh mint, Lavender, Sky blue, Peach, Sunny yellow)
- Smooth hop-in / wave / celebrate / hop-away animations
- **Okay, let's go!** to celebrate, or **Remind me in 5 minutes** to snooze
- Drag it around, click it for a happy hop, right-click for a menu
- Transparent and click-through: it never gets in the way of your other windows and never steals keyboard focus
- Working hours, pause, snooze length, size, autostart at login
- Lightweight: no CPU at all between visits

## Install

Hoplet needs **Python 3.9+** and one small system library:

```bash
sudo apt install pipx libxcb-cursor0        # Debian / Ubuntu
# sudo dnf install pipx xcb-util-cursor     # Fedora
# sudo pacman -S python-pipx xcb-util-cursor   # Arch
```

Then install and start it:

```bash
pipx install hoplet
hoplet
```

That's it. Hoplet now lives in your system tray, shows up in your app menu, and
starts automatically when you log in (you can turn that off in Settings). The
first visit is one interval (60 minutes by default) after starting. To see it
right away, use **Show reminder now** in the tray menu, or run `hoplet --show-now`.

> **Ubuntu / GNOME:** the tray icon uses the *AppIndicator* extension, which Ubuntu
> enables by default. On other GNOME setups, install
> [AppIndicator and KStatusNotifierItem Support](https://extensions.gnome.org/extension/615/appindicator-support/),
> or just right-click Hoplet for Settings and Quit.

## Using Hoplet

| What | How |
|---|---|
| Accept a reminder | **Okay, let's go!**: it celebrates, cheers you on and hops away |
| Snooze | **Remind me in 5 minutes** (the length is configurable) |
| Ignore it | it leaves on its own after the display time (40 s by default), and waits a little longer while your mouse is on it |
| Move it | drag it anywhere |
| Say hi | click it |
| Menu | right-click it, or use the tray icon: *Show reminder now*, *Pause reminders*, *Settings…*, *Quit* |

Scheduling is gentle by design. Outside your working hours it stays quiet, and
the first visit of the day comes one interval *after* work starts. Suspending
your computer counts as a break, so it won't nag you the moment you wake it up.

## Settings

Open **Settings…** from the tray or the right-click menu. Preferences are saved to
`~/.config/hoplet/settings.json`:

| Setting | Default | |
|---|---|---|
| Name | `Hoplet` | what your companion is called (shown in the tray and its messages) |
| Character | Girl | Girl or Boy |
| Color theme | Sakura pink | colors the outfit, speech bubble, buttons, settings window and tray icon |
| Size | Medium | Small, Medium or Large |
| Remind me | every 60 min | 30 / 45 / 60 / 90 (any value works in the JSON file) |
| Snooze for | 5 min | |
| Stay on screen | 40 s | |
| Working hours | off | e.g. 09:00–18:00; overnight ranges like 22:00–06:00 work too |
| Start at login | on | |

## Make it yours

### Your own messages

Create `~/.config/hoplet/messages.json`. Any category you include replaces the
built-in one (see the
[built-in messages](src/hoplet/assets/messages.json) for all categories):

```json
{
  "reminders": [
    "{name} says: water time!",
    "Shoulders down, jaw relaxed~",
    "Time for a lap around the room!"
  ]
}
```

`{name}` becomes your companion's name, and `{minutes}` (in `snooze` lines)
becomes the snooze time. Restart Hoplet to load changes.

### Your own character art

Hoplet's built-in characters are drawn by code. To use your own art:

1. Export a template to see the expected format:
   ```bash
   hoplet --export-character ~/.local/share/hoplet/characters/girl --gender girl
   ```
   (use `boy` for the boy character). Hoplet now uses this folder instead of
   the built-in art for that character.
2. Replace the PNG frames with your own drawings. There are six animations:

   | Animation | Shows | Tips |
   |---|---|---|
   | `idle` | standing, breathing, blinking | 8–16 frames, with a blink near the end |
   | `enter` | **one hop**: crouch → jump → air → land | played once per hop; Hoplet moves it along the arc |
   | `walk` | one small step or hop | |
   | `remind` | waving or talking | plays for about 4 s on arrival |
   | `happy` | cheering | loops while celebrating |
   | `leave` | like `enter` (can be identical) | |

   - Use **transparent PNGs**, all the same size, with **feet at the bottom edge, centered**.
   - Draw at about 1.5–2× the on-screen size (e.g. 240×300 for 210 px tall).
   - Don't bake the jump height into hop frames. Hoplet moves the character up
     and down and adds squash and stretch itself, so frames only need the *pose*.
   - A missing animation falls back to `idle`, so you can replace one animation at a time.
   - An optional 64×64 `icon.png` (the face) becomes the tray icon.
3. Tune `animations.json` in that folder:
   ```json
   {
     "display_height": 210,
     "facing": "front",
     "animations": {
       "idle":  { "frames": "idle/*.png", "fps": 8, "loop": true },
       "enter": { "sheet": "enter.png", "frame_width": 240, "frame_height": 300, "count": 6, "fps": 10 }
     }
   }
   ```
   - Each animation is either a folder of frames (`frames`, loaded in filename
     order) or a sprite sheet (`sheet`, plus the frame size, and optionally
     `count` and `columns`).
   - For `enter`, `leave` and `walk`, one cycle (frames ÷ fps) is the length of
     one hop.
   - `facing`: set `"left"` or `"right"` for side-view art, and Hoplet mirrors it
     when it moves the other way. `"front"` never mirrors.

With custom art, the color theme still styles the speech bubble and settings window.

## Uninstall

```bash
hoplet --uninstall      # removes the menu entry, autostart entry and cache
pipx uninstall hoplet
```

Your settings (`~/.config/hoplet/`) and custom art (`~/.local/share/hoplet/`)
are kept unless you delete them yourself.

## Troubleshooting

- **Nothing appears:** check the log at `~/.cache/hoplet/companion.log`, or run
  `hoplet --show-now -v` in a terminal.
- **"needs the libxcb-cursor0 system library":** install it as shown in [Install](#install).
- **Wayland:** Wayland doesn't let apps position their own windows or stay on
  top, so Hoplet automatically runs through XWayland. You don't need to do anything.
- **No tray icon:** see the GNOME note in [Install](#install); the right-click
  menu on the character always works.

Hoplet is built for Linux desktops on X11 or XWayland (GNOME, KDE, XFCE, …).
Windows and macOS are untested.

## Development

```bash
git clone <this repository> && cd hoplet
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/hoplet --show-now --interval-seconds 30 -v   # fast visits for testing
.venv/bin/pytest                                       # headless tests
.venv/bin/python tests/manual/desktop_flow.py          # drives the real window on your desktop
```

Code tour (`src/hoplet/`):

| Module | Responsibility |
|---|---|
| `main.py` | command line, app wiring, Wayland → XWayland setup |
| `character.py` | the floating window: state machine, hop physics, speech bubble, drag, click-through mask |
| `animation_manager.py` | loads frame folders or sprite sheets, plays clips |
| `reminder_scheduler.py` | when to visit: interval, snooze, working hours, sleep detection |
| `placeholder_art.py` | draws the built-in girl and boy in any theme |
| `character_assets.py` | picks custom art or the built-in characters (cached in `~/.cache/hoplet/`) |
| `themes.py` | color themes; add one line to `THEMES` for a new theme |
| `message_manager.py` | random lines with `{name}`/`{minutes}` placeholders |
| `settings.py`, `settings_dialog.py` | preferences and the settings window |
| `tray.py`, `autostart.py` | tray icon, app-menu and login entries |

Notes:

- The character is an X11 *override-redirect* window with a shape mask. That's
  what makes it stay on top, click-through and focus-free, and lets it hop in
  from beyond the screen edge.
- PySide6 6.12.0 crashes on Python < 3.12 (`none_dealloc: deallocating None`),
  so `pyproject.toml` keeps those Python versions on PySide6 < 6.12.

### Releasing

1. Bump `__version__` in `src/hoplet/__init__.py`.
2. Create a GitHub Release. The `release.yml` workflow builds the package and publishes it to PyPI.
   One-time setup: on pypi.org, add this repository as a *trusted publisher*
   (workflow `release.yml`, environment `pypi`).

## License

[MIT](LICENSE)
