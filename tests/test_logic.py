"""Headless tests for settings, messages, scheduler, assets and desktop
integration. Run with:  pytest
"""
import json
from datetime import datetime, timedelta

from conftest import TMP
from hoplet import autostart
from hoplet import reminder_scheduler as rs
from hoplet.animation_manager import AnimationLibrary
from hoplet.message_manager import MessageManager
from hoplet.settings import Settings


class FakeClock:
    """Replaces datetime.now() inside reminder_scheduler."""
    now_value = datetime(2026, 11, 25, 10, 0)

    @classmethod
    def now(cls):
        return cls.now_value


rs.datetime = FakeClock


def advance(scheduler, minutes, step=0.5):
    """Move the fake clock forward, polling like the real QTimer would."""
    fired = 0
    for _ in range(int(minutes / step)):
        FakeClock.now_value += timedelta(minutes=step)
        before = scheduler._busy
        scheduler._poll()
        if scheduler._busy and not before:
            fired += 1
    return fired


def test_settings_roundtrip():
    path = TMP / "settings.json"
    s = Settings(interval_minutes=45, snooze_minutes=7, work_start="08:30")
    s.save(path)
    loaded = Settings.load(path)
    assert loaded == s, (loaded, s)
    path.write_text(json.dumps({"interval_minutes": "garbage", "display_seconds": 9999,
                                "work_end": "nope", "unknown_key": 1}))
    bad = Settings.load(path)
    assert bad.interval_minutes == 60 and bad.display_seconds == 300 and bad.work_end == "18:00"
    path.write_text("{not json")
    assert Settings.load(path) == Settings()


def test_working_hours():
    s = Settings(working_hours_enabled=True, work_start="09:00", work_end="18:00")
    assert s.in_working_hours(datetime(2026, 1, 1, 9, 0))
    assert not s.in_working_hours(datetime(2026, 1, 1, 18, 0))
    assert not s.in_working_hours(datetime(2026, 1, 1, 7, 0))
    night = Settings(working_hours_enabled=True, work_start="22:00", work_end="06:00")
    assert night.in_working_hours(datetime(2026, 1, 1, 23, 0))
    assert night.in_working_hours(datetime(2026, 1, 1, 3, 0))
    assert not night.in_working_hours(datetime(2026, 1, 1, 12, 0))


def test_scheduler_interval_and_snooze():
    FakeClock.now_value = datetime(2026, 11, 25, 10, 0)
    s = Settings(interval_minutes=60, snooze_minutes=5)
    sch = rs.ReminderScheduler(s)
    sch.start()
    assert advance(sch, 59) == 0
    assert advance(sch, 1.5) == 1, "should fire at 60 minutes"
    assert advance(sch, 30) == 0, "must not fire again while she's on screen"
    sch.reminder_finished("snoozed")
    assert advance(sch, 4.5) == 0
    assert advance(sch, 1) == 1, "snooze fires after 5 minutes"
    sch.reminder_finished("acknowledged")
    assert advance(sch, 59) == 0
    assert advance(sch, 1.5) == 1


def test_scheduler_pause_and_resume():
    FakeClock.now_value = datetime(2026, 11, 25, 10, 0)
    s = Settings(interval_minutes=30)
    sch = rs.ReminderScheduler(s)
    sch.start()
    s.reminders_enabled = False
    sch.apply_settings()
    assert advance(sch, 120) == 0, "paused: never fires"
    assert sch.status_text() == "Reminders paused"
    s.reminders_enabled = True
    sch.apply_settings()
    assert advance(sch, 1) == 0, "re-enabling must not fire immediately"
    assert advance(sch, 30) == 1


def test_scheduler_working_hours():
    FakeClock.now_value = datetime(2026, 11, 25, 17, 30)
    s = Settings(interval_minutes=60, working_hours_enabled=True, work_start="09:00", work_end="18:00")
    sch = rs.ReminderScheduler(s)
    sch.start()                                     # due 18:30 -> outside hours
    fired_evening = advance(sch, 60 * 15)           # until 08:30 next day
    assert fired_evening == 0, "nothing outside working hours"
    assert sch.next_due == datetime(2026, 11, 26, 10, 0), sch.next_due
    assert advance(sch, 89) == 0                    # 08:30 -> 09:59
    assert advance(sch, 1.5) == 1, "first reminder one interval after work starts"


def test_scheduler_sleep_gap():
    FakeClock.now_value = datetime(2026, 11, 25, 10, 0)
    s = Settings(interval_minutes=60)
    sch = rs.ReminderScheduler(s)
    sch.start()
    sch._last_poll = FakeClock.now_value
    FakeClock.now_value += timedelta(hours=3)       # laptop was suspended
    sch._poll()
    assert not sch._busy, "waking up counts as a break, not an overdue reminder"
    assert sch.next_due == FakeClock.now_value + timedelta(minutes=60)


def test_interval_change_applies():
    FakeClock.now_value = datetime(2026, 11, 25, 10, 0)
    s = Settings(interval_minutes=90)
    sch = rs.ReminderScheduler(s)
    sch.start()
    s.interval_minutes = 30
    sch.apply_settings()
    assert sch.next_due == FakeClock.now_value + timedelta(minutes=30)


def test_messages():
    path = TMP / "messages.json"
    path.write_text(json.dumps({"reminders": ["a", "b"], "snooze": ["back in {minutes}!"]}))
    m = MessageManager(path)
    picks = [m.reminder() for _ in range(20)]
    assert all(x != y for x, y in zip(picks, picks[1:])), "no immediate repeats"
    assert m.snooze(5) == "back in 5!"
    assert m.encouragement()                         # falls back to defaults
    assert MessageManager(TMP / "missing.json").reminder()


def test_desktop_integration():
    import sys
    autostart.sync(True)
    for path in (autostart.AUTOSTART_FILE, autostart.LAUNCHER_FILE):
        assert str(TMP) in str(path), path                      # sandboxed by conftest
        text = path.read_text()
        assert f"Exec={sys.executable} -m hoplet" in text and "Name=Hoplet" in text
    assert "X-GNOME-Autostart-enabled=true" in autostart.AUTOSTART_FILE.read_text()
    assert autostart.is_enabled()
    autostart.set_enabled(False)
    assert not autostart.is_enabled() and autostart.LAUNCHER_FILE.exists()
    assert autostart.remove_all() == [autostart.LAUNCHER_FILE]


def test_character_name():
    m = MessageManager()
    m.name = "Momo"
    lines = {m.pick("goodbyes") for _ in range(30)}
    assert "Momo will check on you later!" in lines
    assert not any("{name}" in line for line in lines)
    path = TMP / "odd.json"
    path.write_text(json.dumps({"reminders": ["{unknown} and {name} and {"]}))
    odd = MessageManager(path)
    odd.name = "Pip"
    assert odd.reminder() == "{unknown} and {name} and {", "broken templates are shown as-is"
    path.write_text(json.dumps({"reminders": ["{unknown} meets {name}"]}))
    odd = MessageManager(path)
    odd.name = "Pip"
    assert odd.reminder() == "{unknown} meets Pip"

    s = Settings(character_name="   Momo   the   Bunny  ")
    s.validate()
    assert s.character_name == "Momo the Bunny"
    s.character_name = "   "
    s.validate()
    assert s.character_name == "Hoplet"
    s.character_name = "x" * 50
    s.validate()
    assert len(s.character_name) == 24

    FakeClock.now_value = datetime(2026, 11, 25, 10, 0)
    sch = rs.ReminderScheduler(Settings(character_name="Momo", interval_minutes=30))
    sch.start()
    assert sch.status_text() == "Momo will visit at 10:30"


def test_user_messages_override():
    from hoplet import message_manager
    from hoplet.paths import USER_MESSAGES_FILE
    USER_MESSAGES_FILE.parent.mkdir(parents=True, exist_ok=True)
    USER_MESSAGES_FILE.write_text(json.dumps({"reminders": ["Drink tea, {name}!"]}))
    try:
        m = message_manager.MessageManager()
        m.name = "you"
        assert m.reminder() == "Drink tea, you!"
        assert m.encouragement()               # other categories still come from the bundle
    finally:
        USER_MESSAGES_FILE.unlink()


def test_cli_export_and_uninstall(capsys):
    from hoplet import main
    from hoplet.paths import CACHE_DIR
    out = TMP / "exported"
    assert main.main(["--export-character", str(out), "--gender", "boy", "--theme", "peach"]) == 0
    assert (out / "animations.json").exists() and len(list(out.glob("*/frame_*.png"))) == 52
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    autostart.sync(True)
    assert main.main(["--uninstall"]) == 0
    assert not CACHE_DIR.exists() and not autostart.is_enabled() and not autostart.LAUNCHER_FILE.exists()
    assert "pipx uninstall hoplet" in capsys.readouterr().out


def test_bundled_assets_present():
    from hoplet.paths import APP_ICON, DEFAULT_MESSAGES_FILE
    assert APP_ICON.exists() and DEFAULT_MESSAGES_FILE.exists()
    data = json.loads(DEFAULT_MESSAGES_FILE.read_text())
    assert len(data["reminders"]) >= 7


def test_animation_library():
    from hoplet import character_assets
    from hoplet.themes import THEMES
    for gender in ("girl", "boy"):
        folder = character_assets.character_dir(gender, THEMES["mint"])
        assert str(TMP) in str(folder), folder
        lib = AnimationLibrary(folder)
        for name in ("idle", "enter", "walk", "remind", "happy", "leave"):
            clip = lib.get(name)
            assert clip.name == name and clip.frames, (gender, name)
        assert lib.get("nonexistent").name == "idle"
        assert lib.frame_size[1] == 210
        assert AnimationLibrary(folder, scale=0.8).frame_size[1] == 168
        assert (folder / "icon.png").exists()


def test_every_theme_and_gender_renders():
    from hoplet import placeholder_art
    from hoplet.themes import THEMES
    for theme in THEMES.values():
        theme.dialog_qss()                      # also writes the themed svg icons
        assert (theme.ui_icons() / "check.svg").exists()
        for gender in ("girl", "boy"):
            img = placeholder_art.render(placeholder_art.Pose(), placeholder_art.Look(gender, theme))
            assert not img.isNull() and img.pixelColor(120, 120).alpha() == 255, (gender, theme.key)


def test_custom_art_takes_priority():
    from hoplet import character_assets
    from hoplet import placeholder_art
    from hoplet.themes import THEMES
    original = character_assets.CUSTOM_CHARACTERS_DIR
    character_assets.CUSTOM_CHARACTERS_DIR = TMP / "custom"
    try:
        assert character_assets.custom_dir("boy") is None
        placeholder_art.generate(TMP / "custom" / "boy", "boy", THEMES["peach"])
        assert character_assets.character_dir("boy", THEMES["sky"]) == TMP / "custom" / "boy"
        assert character_assets.character_dir("girl", THEMES["sky"]) != TMP / "custom" / "girl"
    finally:
        character_assets.CUSTOM_CHARACTERS_DIR = original


def test_look_settings_validation():
    s = Settings(character="dragon", theme="neon")
    s.validate()
    assert s.character == "girl" and s.theme == "sakura"


def test_sprite_sheet_loading():
    from PySide6.QtGui import QColor, QPixmap
    d = TMP / "sheetchar"
    d.mkdir()
    sheet = QPixmap(400, 100)
    sheet.fill(QColor("red"))
    sheet.save(str(d / "idle.png"))
    (d / "animations.json").write_text(json.dumps({
        "display_height": 50,
        "animations": {"idle": {"sheet": "idle.png", "frame_width": 100, "frame_height": 100, "fps": 4}}}))
    lib = AnimationLibrary(d)
    assert len(lib.get("idle").frames) == 4 and lib.frame_size == (50, 50)
    assert lib.get("walk").name == "idle"


def test_tray_menu_actions_emit():
    """Every tray menu item must actually emit its signal when clicked."""
    from hoplet.tray import Tray
    from PySide6.QtGui import QIcon
    tray = Tray(lambda: "status", QIcon())
    fired = []
    tray.show_now.connect(lambda: fired.append("show_now"))
    tray.settings_requested.connect(lambda: fired.append("settings"))
    tray.quit_requested.connect(lambda: fired.append("quit"))
    tray.pause_toggled.connect(lambda p: fired.append(f"pause={p}"))
    for action in tray._menu.actions():
        if action.isEnabled() and action.text():
            action.trigger()
    assert fired == ["show_now", "pause=True", "settings", "quit"], fired


def test_settings_dialog():
    from hoplet.settings_dialog import SettingsDialog
    s = Settings(interval_minutes=45, working_hours_enabled=True, work_start="08:00")
    dlg = SettingsDialog(s)
    assert dlg.interval.currentData() == 45 and dlg.hours_box.isChecked()
    dlg.interval.setCurrentIndex(dlg.interval.findData(90))
    dlg.snooze.setValue(10)
    dlg.name.setText("Momo")
    assert dlg.title.text().startswith("Momo") and "Momo" in dlg.subtitle.text()
    dlg.character.setCurrentIndex(dlg.character.findData("boy"))
    dlg.theme.setCurrentIndex(dlg.theme.findData("mint"))
    assert "#86D9C0".lower() in dlg.styleSheet().lower(), "dialog restyles live"
    assert not dlg.preview.pixmap().isNull()
    dlg.apply_to(s)
    assert s.interval_minutes == 90 and s.snooze_minutes == 10 and s.work_start == "08:00"
    assert s.character == "boy" and s.theme == "mint" and s.character_name == "Momo"
