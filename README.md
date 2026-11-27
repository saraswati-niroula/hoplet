# Hoplet

**A little hopping companion for your desktop: Linux, Windows and macOS.**

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

## Download

No Python or terminal needed. Get the file for your computer from the
[latest release](https://github.com/saraswati-niroula/hoplet/releases/latest):

| Your computer | Download | Then |
|---|---|---|
| **Windows** 10 / 11 | `Hoplet-Setup.exe` | run it and click through the installer |
| **Mac** with Apple silicon (M1 or newer) | `Hoplet-macOS-arm64.dmg` | open it and drag **Hoplet** into **Applications** |
| **Mac** with an Intel processor | `Hoplet-macOS-intel.dmg` | same as above |
| **Linux** | `Hoplet-x86_64.AppImage` | right-click → *Properties* → allow running as a program, then double-click it |

Not sure which Mac you have? Apple menu → **About This Mac**: *Chip: Apple M…* means
Apple silicon, *Processor: Intel* means Intel.

### The first time you open it

Hoplet isn't signed with a paid developer certificate (yet), so Windows and macOS
show a warning the first time. This only happens once.

- **Windows:** if you see *"Windows protected your PC"*, click **More info**, then
  **Run anyway**.
- **macOS:** if you see *"Hoplet can't be opened"* or *"Apple could not verify…"*,
  click **Done** (not *Move to Trash*). Then open **System Settings → Privacy &
  Security**, scroll down to the message about Hoplet and click **Open Anyway**.
  Enter your password if asked. Hoplet then opens normally from now on.

After that, Hoplet lives in your system tray (the menu bar on a Mac) and starts by
itself when you log in. To see it right away, click its tray icon and choose
**Show reminder now**.

## Install with pipx

For people comfortable with a terminal. Hoplet needs **Python 3.9+**. Install it with [pipx](https://pipx.pypa.io/), which
keeps it in its own little environment.

**Linux**: pipx and one small system library:

```bash
sudo apt install pipx libxcb-cursor0        # Debian / Ubuntu
# sudo dnf install pipx xcb-util-cursor     # Fedora
# sudo pacman -S python-pipx xcb-util-cursor   # Arch
```

**Windows**: install Python from [python.org](https://www.python.org/downloads/)
(tick *Add python.exe to PATH*), then in a terminal:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath        # then open a new terminal
```

**macOS**: with [Homebrew](https://brew.sh/):

```bash
brew install pipx
pipx ensurepath              # then open a new terminal
```

Then, on any system, install and start it:

```bash
pipx install hoplet
hoplet
```

That's it. Hoplet now lives in your system tray (the menu bar on macOS) and
starts automatically when you log in (you can turn that off in Settings). On
Linux it also shows up in your app menu, and on Windows in the Start Menu. The
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

Open **Settings…** from the tray or the right-click menu. Preferences are saved in
`settings.json` in Hoplet's settings folder:

| System | Settings folder | Cache and log |
|---|---|---|
| Linux | `~/.config/hoplet/` | `~/.cache/hoplet/` |
| Windows | `%APPDATA%\Hoplet\` | `%LOCALAPPDATA%\Hoplet\Cache\` |
| macOS | `~/Library/Application Support/Hoplet/` | `~/Library/Caches/Hoplet/` |


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

Create `messages.json` in the settings folder (see [Settings](#settings)). Any category you include replaces the
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
   (use `boy` for the boy character). On Windows and macOS, use the
   `characters` folder inside the settings folder instead:
   `hoplet --export-character "$env:APPDATA\Hoplet\characters\girl"` (Windows PowerShell) or
   `hoplet --export-character ~/Library/Application\ Support/Hoplet/characters/girl` (macOS). Hoplet now uses this folder instead of
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
hoplet --uninstall      # removes the menu/Start Menu entry, autostart entry and cache
pipx uninstall hoplet
```

If you used a download instead: on **Windows**, go to *Settings → Apps → Hoplet →
Uninstall*. On a **Mac**, quit Hoplet from the menu bar and drag it from
Applications to the Trash. On **Linux**, run the AppImage with `--uninstall`,
then delete the file.

Your settings and custom art are kept unless you delete them yourself
(`hoplet --uninstall` prints where they are).

## Troubleshooting

- **Nothing appears:** check `companion.log` in the cache folder (see
  [Settings](#settings)), or run `hoplet --show-now -v` in a terminal.
- **"needs the libxcb-cursor0 system library":** install it as shown in [Install with pipx](#install-with-pipx).
- **Wayland:** Wayland doesn't let apps position their own windows or stay on
  top, so Hoplet automatically runs through XWayland. You don't need to do anything.
- **No tray icon:** see the GNOME note in [Install with pipx](#install-with-pipx); the right-click
  menu on the character always works.

Hoplet runs on Linux desktops on X11 or XWayland (GNOME, KDE, XFCE, …),
Windows 10/11 and macOS. On macOS it has no Dock icon; find it in the menu bar.

## Development

Get the code and set up a virtual environment with an editable install, so
your code changes take effect the next time you start Hoplet:

**Linux / macOS**

```bash
git clone https://github.com/saraswati-niroula/hoplet.git
cd hoplet
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/saraswati-niroula/hoplet.git
cd hoplet
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

(If PowerShell refuses to run the activate script, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.)

Then, with the environment active:

```bash
hoplet --show-now --interval-seconds 30 -v   # run it, with fast visits for testing
pytest                                       # headless tests
python tests/manual/desktop_flow.py          # Linux/X11 only: drives the real window on your desktop
```

To pick up code changes, quit Hoplet (tray menu → **Quit**) and start it again.
If you also have a pipx-installed Hoplet running, quit that one first: only one
Hoplet runs at a time.

Code tour (`src/hoplet/`):

| Module | Responsibility |
|---|---|
| `main.py` | command line, app wiring, Wayland → XWayland setup |
| `character.py` | the floating window: state machine, hop physics, speech bubble, drag, click-through mask |
| `animation_manager.py` | loads frame folders or sprite sheets, plays clips |
| `reminder_scheduler.py` | when to visit: interval, snooze, working hours, sleep detection |
| `placeholder_art.py` | draws the built-in girl and boy in any theme |
| `character_assets.py` | picks custom art or the built-in characters (cached in the cache folder) |
| `themes.py` | color themes; add one line to `THEMES` for a new theme |
| `message_manager.py` | random lines with `{name}`/`{minutes}` placeholders |
| `settings.py`, `settings_dialog.py` | preferences and the settings window |
| `tray.py`, `autostart.py` | tray icon, app-menu and login entries (per OS) |

Notes:

- On Linux the character is an X11 *override-redirect* window with a shape mask.
  That's what makes it stay on top, click-through and focus-free, and lets it hop
  in from beyond the screen edge. On Windows and macOS it's a frameless,
  always-on-top tool window with the same mask.
- Platform-specific code lives in `main.py` (startup), `paths.py` (folders) and
  `autostart.py` (Start Menu, login entries).
- PySide6 6.12.0 crashes on Python < 3.12 (`none_dealloc: deallocating None`),
  so `pyproject.toml` keeps those Python versions on PySide6 < 6.12.

### Building the standalone apps

The `packaging/` folder turns Hoplet into apps that don't need Python
(PyInstaller), and the `apps.yml` workflow builds them on Windows, macOS and
Linux. To build one locally, on the system you're building for:

```bash
pip install -e ".[app]"
pyinstaller packaging/hoplet.spec --noconfirm   # dist/Hoplet/ or dist/Hoplet.app
packaging/linux/build_appimage.sh               # Linux: dist/Hoplet-x86_64.AppImage
packaging/macos/build_dmg.sh                    # macOS: dist/Hoplet-macOS-<arch>.dmg
```

The Windows installer needs [Inno Setup](https://jrsoftware.org/isinfo.php); see
`apps.yml` for the exact commands. For test builds without a release, run the
workflow by hand (*Actions → Apps → Run workflow*) and download the results from
the run's *Artifacts*.

### Releasing

1. Bump `__version__` in `src/hoplet/__init__.py`.
2. Create a GitHub Release with the tag `v` + that version (e.g. `v0.1.0`).
   The `release.yml` workflow publishes the package to PyPI, and `apps.yml`
   builds the Windows, macOS and Linux downloads and attaches them to the release.
   One-time setup: on pypi.org, add this repository as a *trusted publisher*
   (workflow `release.yml`, environment `pypi`).

## License

[MIT](LICENSE)
