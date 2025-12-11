"""
main.py — game entry and logic. ASCII animation helpers are placed later
after the UI helper functions (boxed_lines, render_frame) so they can
use the rendering utilities without ordering issues.
"""
import json, os, time, sys, threading, shutil, math, select, random, textwrap, subprocess, re, traceback, copy
from collections import deque

try:
    from wcwidth import wcswidth as _wcwidth
except ImportError:
    _wcwidth = None

msvcrt = None
if os.name == "nt":
    try:
        import msvcrt
    except ImportError:
        pass

try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=False)
except ImportError:
    class _ColorCodes:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
        LIGHTBLACK_EX = LIGHTRED_EX = LIGHTGREEN_EX = LIGHTYELLOW_EX = ""
        LIGHTBLUE_EX = LIGHTMAGENTA_EX = LIGHTCYAN_EX = ""

    class _StyleCodes:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

    Fore = Back = _ColorCodes()
    Style = _StyleCodes()

from ascii_art import (
    LAYER_0_DESK,
    UPGRADE_ART,
    UPGRADE_ANIM_ART_FRAMES,
    RPG_ICON_ART,
    RPG_DEFAULT_ICON_ART,
    RPG_ICON_HEIGHT,
    RPG_ICON_WIDTH,
    ENEMY_ASCII_FRAMES,
    BREACH_DOOR_CLOSED_ART,
    BREACH_DOOR_OPEN_ART,
    BREACH_DOOR_UNLOCK_FRAMES,
    EVENT_ANIMATIONS,
)
import config
from config import (
    BASE_MONEY_GAIN,
    BASE_WORK_DELAY,
    BASE_MONEY_MULT,
    INSPIRE_UPGRADES,
    CONCEPT_UPGRADES,
    AUTOMATION_UPGRADES,
    INSPIRATION_UNLOCK_MONEY,
    CONCEPTS_UNLOCK_MONEY,
    BREACH_KEY_BASE_COST,
    BREACH_KEY_MIN_COST,
    BREACH_KEY_MAX_COST,
    BREACH_TARGET_PROGRESS,
    BREACH_SLACK_PROGRESS,
    MOTIVATION_MAX,
    MAX_MOTIVATION_MULT,
    MOTIVATION_REGEN_RATE,
    SAVE_SLOT_COUNT,
    MAIN_LOOP_MIN_DT,
    ENEMY_ANIM_DELAY,
    BORDERS,
    GAME_TITLE,
    UPGRADES,
    LAYER_FLOW,
    LAYER_BY_KEY,
    LAYER_BY_ID,
    CURRENCY_SYMBOL,
    WAKE_TIMER_START,
    WAKE_TIMER_UPGRADES,
    STABILITY_CURRENCY_NAME,
    AUTOMATION_CURRENCY_NAME,
    AUTOMATION_CURRENCY_SUFFIX,
    AUTOMATION_EXCHANGE_RATE,
    STABILITY_REWARD_MULT,
    STABILITY_REWARD_EXP,
    SCIENTIFIC_THRESHOLD_DEFAULT,
    SCIENTIFIC_THRESHOLD_OPTIONS,
    RESONANCE_MAX,
    RESONANCE_START,
    RESONANCE_TARGET_WIDTH,
    RESONANCE_DRIFT_RATE,
    RESONANCE_TUNE_POWER,
    RESONANCE_BASE_INSTABILITY,
    RESONANCE_MIN_INSTABILITY,
    RESONANCE_JUMP_CHANCE,
    RESONANCE_JUMP_POWER,
    RPG_PLAYER_START_HP,
    RPG_PLAYER_START_ATK,
    RPG_NG_HP_BONUS,
    RPG_NG_ATK_BONUS,
    RPG_NG_GOLD_STEP,
    RPG_ENEMIES,
    RPG_DESKTOP_APPS,
    RPG_DESKTOP_COLS,
    RPG_MAP_WIDTH,
    RPG_MAP_HEIGHT,
    RPG_THEME_ROTATION,
    RPG_THEME_BLOCK_SIZE,
    RPG_MAZE_VARIANTS,
    RPG_ROOM_TYPES,
    RPG_ROOM_DESCRIPTIONS,
    RPG_POTION_HEAL_RATIO,
    RPG_LOG_MAX,
    RPG_RELICS,
    RPG_RELIC_LOOKUP,
    RPG_SECRET_ROOM_TYPES,
    RPG_MIN_SECRET_FLOOR,
    RPG_SECRET_BASE_COUNT,
    RPG_SECRET_SCALE,
    RPG_SECRET_BOSS_TEMPLATE,
    RPG_BOSSES,
    RPG_SHOP_STOCK,
    RPG_AURAS,
    RPG_DEFAULT_AURA,
    RPG_BASE_CRIT,
    RPG_FLOOR_MODIFIERS,
    RPG_FLOOR_CAP,
    RPG_GOLD_REWARD_SCALE,
    TIME_STRATA,
    format_number,
    UPGRADE_REPLACEMENT,
    CHALLENGES,
    GUIDE_TOPICS,
    FIELD_GUIDE_UNLOCK_TOTAL,
    CHALLENGE_GROUP_RESET,
    CHALLENGE_LAYER_TARGET,
    CHALLENGE_RESET_LAYER_KEY,
    AUTO_ONLY_UPGRADE_TYPES,
    MANUAL_TAP_THRESHOLD,
    MANUAL_TAP_GAP,
    BROWSER_CURRENCY_NAME,
    BROWSER_NOTICE_DURATION,
    SHOPKEEPER_NAME,
    BROWSER_UPGRADES,
    ESCAPE_MODE,
    ESCAPE_REPLACEMENTS,
    ESCAPE_MACHINE,
    MIRROR_BORDER_ID,
)
from currency import grant_stability_currency

import blackjack

CHALLENGE_BY_ID = {entry["id"]: entry for entry in CHALLENGES}
CHALLENGE_GROUPS = []
for entry in CHALLENGES:
    group = entry.get("group", "Trials")
    if group not in CHALLENGE_GROUPS:
        CHALLENGE_GROUPS.append(group)
if not CHALLENGE_GROUPS:
    CHALLENGE_GROUPS = ["Trials"]
EVENT_GOAL_TYPES = {"phase_lock_completion"}
AUTOMATION_UPGRADE_INDEX = {u.get("id"): i for i, u in enumerate(AUTOMATION_UPGRADES)}
AUTO_BUYER_TARGET_ORDER = [
    u.get("id")
    for u in AUTOMATION_UPGRADES
    if u.get("id") and u.get("id") != "automation_buyers"
]

ROOM_COLOR_MAP = {
    "start": Fore.WHITE,
    "enemy": Fore.RED,
    "elite": Fore.MAGENTA,
    "boss": Fore.LIGHTMAGENTA_EX,
    "treasure": Fore.YELLOW,
    "healer": Fore.CYAN,
    "trap": Fore.LIGHTRED_EX,
    "empty": Fore.LIGHTBLACK_EX,
    "secret": Fore.BLUE,
    "secret_vault": Fore.YELLOW,
    "secret_echo": Fore.CYAN,
    "secret_sentinel": Fore.MAGENTA,
    "secret_exit": Fore.GREEN,
    "exit": Fore.GREEN,
    "stairs": Fore.GREEN,
}

EASTER_EGG_DEFAULT_COOLDOWN = 240.0
MANUAL_WORK_SPAM_THRESHOLD = 5
MANUAL_WORK_SPAM_WINDOW = 10.0
LONG_SESSION_EGG_SECONDS = 5400

SESSION_HINT_FLAGS = set()
GUIDE_REFRESH_INTERVAL = 0.5
_LAST_GUIDE_REFRESH = 0.0


def default_escape_machine_state():
    return {
        "unlocked": False,
        "components": [],
        "ready": False,
        "applied": False,
        "spark_bank": 0,
    }


def compute_browser_effects(unlocks):
    totals = {"max_hp": 0, "atk": 0, "def": 0, "gold": 0}
    for entry in BROWSER_UPGRADES:
        if entry.get("id") not in unlocks:
            continue
        for key, value in (entry.get("effect") or {}).items():
            totals[key] = totals.get(key, 0) + value
    return totals


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
LEGACY_SAVE_PATH = os.path.join(DATA_DIR, "save.json")
ACTIVE_SLOT_INDEX = 2

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RESET_SEQ = getattr(Style, "RESET_ALL", "\x1b[0m")

TERMINAL_TARGET_COLS = 200
TERMINAL_TARGET_ROWS = 55
_TERMINAL_SCALE_CONFIRMED = False

_FULLSCREEN_REQUESTED = False
_INTRO_BOOT_SEQUENCE_PLAYED = False

INTRO_BOOT_STEPS = [
    ("Re-seeding memory anchors", 0.9),
    ("Stitching mirror lattice", 0.8),
    ("Priming Diverter capacitors", 0.7),
    ("Authorizing pilot credentials", 0.6),
]

MACHINE_PANEL_MIN_COLS = TERMINAL_TARGET_COLS + 10
MACHINE_PANEL_MIN_ROWS = TERMINAL_TARGET_ROWS + 5
TYPEWRITER_STEP_DELAY = 0.03
LARGEST_PANEL_MIN_COLS = max(TERMINAL_TARGET_COLS, MACHINE_PANEL_MIN_COLS)
LARGEST_PANEL_MIN_ROWS = max(TERMINAL_TARGET_ROWS, MACHINE_PANEL_MIN_ROWS)


def request_fullscreen():
    global _FULLSCREEN_REQUESTED
    if not getattr(config, "AUTO_FULLSCREEN", True):
        return False
    if _FULLSCREEN_REQUESTED:
        return False
    _FULLSCREEN_REQUESTED = True
    try:
        if sys.platform.startswith("darwin"):
            term_program = (os.environ.get("TERM_PROGRAM") or "").lower()
            if "apple" in term_program:
                script = (
                    "tell application \"Terminal\"\n"
                    "    activate\n"
                    "    try\n"
                    "        tell application \"System Events\" to tell process \"Terminal\" "
                    "to set value of attribute \"AXFullScreen\" of window 1 to true\n"
                    "    end try\n"
                    "end tell"
                )
            elif "iterm" in term_program:
                script = (
                    "tell application \"System Events\"\n"
                    "    tell process \"iTerm2\"\n"
                    "        try\n"
                    "            set value of attribute \"AXFullScreen\" of window 1 to true\n"
                    "        end try\n"
                    "    end tell\n"
                    "end tell"
                )
            else:
                script = ""
            if script:
                subprocess.run(
                    ["osascript", "-e", script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                return True
        elif os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                hwnd = kernel32.GetConsoleWindow()
                if hwnd:
                    # Only maximize the console so Windows users can still resize/minimize.
                    SW_MAXIMIZE = 3
                    user32.ShowWindow(hwnd, SW_MAXIMIZE)
                    user32.SetForegroundWindow(hwnd)
                    return True
            except Exception:
                pass
        cols = max(200, shutil.get_terminal_size((120, 40)).columns)
        rows = max(60, shutil.get_terminal_size((120, 40)).lines)
        sys.stdout.write(f"\033[8;{rows};{cols}t")
        sys.stdout.flush()
        return True
    except Exception:
        return False


def run_intro_boot_sequence():
    global _INTRO_BOOT_SEQUENCE_PLAYED
    if _INTRO_BOOT_SEQUENCE_PLAYED:
        return
    _INTRO_BOOT_SEQUENCE_PLAYED = True
    total = sum(duration for _, duration in INTRO_BOOT_STEPS) or 1.0
    elapsed = 0.0
    for label, duration in INTRO_BOOT_STEPS:
        step_start = time.time()
        while True:
            now = time.time()
            step_elapsed = min(duration, now - step_start)
            pct = min(1.0, (elapsed + step_elapsed) / total)
            bar = build_progress_bar(int(pct * 100), width=28)
            lines = [
                f"{Fore.CYAN}{GAME_TITLE}{Style.RESET_ALL}",
                "Initializing escape stack...",
                label,
                bar,
            ]
            box = boxed_lines(lines, title=" Mirrorwake Boot Sequence ", pad_top=1, pad_bottom=1)
            render_frame(box)
            if step_elapsed >= duration:
                break
            time.sleep(0.05)
        elapsed += duration

def escape_text(text):
    if not ESCAPE_MODE or not isinstance(text, str):
        return text
    stripped = ANSI_ESCAPE.sub("", text)
    stripped = stripped.strip()
    for pattern, replacement in ESCAPE_REPLACEMENTS:
        stripped = re.sub(pattern, replacement, stripped, flags=re.IGNORECASE)
    return stripped


def escape_lines(lines):
    if not ESCAPE_MODE or not isinstance(lines, list):
        return lines
    return [escape_text(line) for line in lines]


def default_rpg_data():
    return {
        "hp": RPG_PLAYER_START_HP,
        "max_hp": RPG_PLAYER_START_HP,
        "atk": RPG_PLAYER_START_ATK,
        "def": 0,
        "xp": 0,
        "level": 1,
        "gold": 0,
        "floor": 1,
        "max_floor": 1,
        "player_pos": None,
        "map": [],
        "state": "explore",
        "current_enemy": None,
        "inventory": {"potion": 1},
        "relics": [],
        "log": [],
        "gold_bonus": 0.0,
        "gear_atk_bonus": 0,
        "gear_def_bonus": 0,
        "gear_trinket_bonus": {},
        "floor_theme": None,
        "theme_ambient_next": 0.0,
        "shop_pending_item": None,
        "aura": RPG_DEFAULT_AURA,
        "shop_owned": [],
        "shop_stock": [],
        "ng_plus": 0,
        "maze_variant": None,
        "pending_variant": None,
        "maze_anim_start": 0.0,
        "maze_anim_until": 0.0,
        "transition_layout": None,
        "transition_center": None,
        "transition_sequence": [],
        "transition_total_cells": 0,
        "transition_reveal": 0,
        "transition_variant": None,
        "transition_step_time": 0.0,
        "transition_last_step": 0.0,
        "event": None,
        "floor_modifier": None,
        "floor_modifier_floor": 0,
        "boss_rewards": [],
        "stairs_prompted": False,
        "shop_purchases_this_floor": 0,
        "secret_origin": None,
        "secret_payload_active": None,
        "browser_bonus": {"max_hp": 0, "atk": 0, "def": 0, "gold": 0},
    }


def default_challenge_state():
    return {
        "active_id": None,
        "baseline": {},
        "started_at": 0.0,
        "event_progress": {},
    }


def challenge_state_data():
    state = game.setdefault("challenge_state", default_challenge_state())
    baseline = state.get("baseline")
    if not isinstance(baseline, dict):
        baseline = {}
        state["baseline"] = baseline
    events = state.get("event_progress")
    if not isinstance(events, dict):
        events = {}
        state["event_progress"] = events
    return state


def current_challenge_id():
    state = challenge_state_data()
    cid = state.get("active_id")
    return cid if isinstance(cid, str) else None


def challenge_event_progress(metric):
    if not metric:
        return 0
    events = challenge_state_data().get("event_progress") or {}
    return events.get(metric, 0)


def increment_challenge_event(metric, amount=1):
    if not metric or amount <= 0:
        return 0
    if not challenge_run_active_flag():
        return 0
    state = challenge_state_data()
    events = state.setdefault("event_progress", {})
    current = events.get(metric, 0)
    events[metric] = current + amount
    return events[metric]


def register_phase_lock_completion():
    if increment_challenge_event("phase_lock_completion", 1):
        check_challenges("phase_lock")


def active_challenge_entry():
    cid = current_challenge_id()
    return CHALLENGE_BY_ID.get(cid) if cid else None


def active_challenge_modifiers():
    entry = active_challenge_entry()
    if not entry:
        return {}
    mods = entry.get("modifiers")
    return mods if isinstance(mods, dict) else {}


def get_challenge_modifier(key, default=None):
    mods = active_challenge_modifiers()
    return mods.get(key, default)


def auto_work_allowed():
    if get_challenge_modifier("disable_auto_work", False):
        return False
    return bool(game.get("auto_work_unlocked", False))


def auto_buyer_allowed():
    if get_challenge_modifier("disable_auto_buyer", False):
        return False
    return bool(game.get("auto_buyer_unlocked", False))


def automation_online():
    if get_challenge_modifier("disable_automation", False):
        return False
    return bool(auto_work_allowed() or auto_buyer_allowed())


def challenges_completed_count():
    return len(set(game.get("challenges_completed", [])))


def total_challenges_configured():
    return len(CHALLENGES)


def all_challenges_cleared():
    total = total_challenges_configured()
    if total == 0:
        return True
    return challenges_completed_count() >= total


def concept_layer_gate_met():
    if game.get("concepts_unlocked", False) or game.get("concept_resets", 0) > 0:
        return True
    return all_challenges_cleared()


def automation_lab_available():
    return automation_online() or bool(game.get("automation_upgrades"))


def challenge_run_active_flag():
    return bool(game.get("challenge_run_active", False))


def instability_challenge_active():
    if not challenge_run_active_flag():
        return False
    entry = active_challenge_entry()
    if not entry:
        return False
    group = (entry.get("group") or "").lower()
    reset_key = CHALLENGE_GROUP_RESET.get(group, "")
    return reset_key == "stability"


def _manual_reset_upgrade_def():
    for upg in WAKE_TIMER_UPGRADES:
        if upg.get("grant_manual_reset"):
            return upg
    return None


def manual_reset_requirement():
    upg = _manual_reset_upgrade_def()
    if not upg:
        return ("Phase Lock", 1)
    name = upg.get("name") or upg.get("id") or "Phase Lock"
    required = max(1, int(upg.get("manual_reset_level", 1)))
    return (name, required)


def manual_reset_unlocked():
    upg = _manual_reset_upgrade_def()
    if not upg:
        return False
    required = max(1, int(upg.get("manual_reset_level", 1)))
    return wake_upgrade_level(upg.get("id")) >= required


def manual_collapse_requirement_text():
    upgrade_name, _ = manual_reset_requirement()
    return f"Manual collapse requires an instability trial or the {upgrade_name} upgrade."


def manual_collapse_available():
    if instability_challenge_active():
        return True
    return manual_reset_unlocked()


def challenge_persistent_state():
    if challenge_run_active_flag():
        backup = game.get("_challenge_backup")
        if isinstance(backup, dict):
            return backup
    return game


def begin_challenge_run(entry):
    if challenge_run_active_flag():
        return False
    backup = copy.deepcopy(game)
    game["_challenge_backup"] = backup
    game["challenge_run_active"] = True
    game["challenge_run_id"] = entry.get("id") if entry else None
    reset_progress_for_challenge(entry)
    label = entry.get("name", "Challenge") if entry else "Challenge"
    set_settings_notice(
        f"Challenge run started: {label}. Layer reset applied; modifiers online.",
        duration=3.0,
    )
    return True


def restore_pre_challenge_state():
    backup = game.pop("_challenge_backup", None)
    game["challenge_run_active"] = False
    game["challenge_run_id"] = None
    if not isinstance(backup, dict):
        return False
    current_knowledge = game.get("knowledge") if isinstance(game, dict) else None
    if isinstance(current_knowledge, dict):
        stored = backup.setdefault("knowledge", {})
        if isinstance(stored, dict):
            for tag, flag in current_knowledge.items():
                if flag:
                    stored[tag] = True
    game.clear()
    game.update(backup)
    ensure_rpg_state()
    apply_inspiration_effects()
    apply_concept_effects()
    apply_automation_effects()
    game.setdefault("_challenge_backup", None)
    return True


def challenge_group_unlocked(group):
    key = (group or "").lower()
    reset_key = CHALLENGE_GROUP_RESET.get(key, key)
    if reset_key == "inspiration":
        return bool(game.get("inspiration_unlocked", False) or game.get("inspiration_resets", 0) > 0)
    if reset_key == "concept":
        return concept_layer_gate_met()
    return True


def challenge_board_pages():
    pages = [g for g in CHALLENGE_GROUPS if challenge_group_unlocked(g)]
    return pages or ["Trials"]


def current_challenge_page_entries():
    pages = challenge_board_pages()
    total = len(pages)
    if total <= 0:
        return [], "Trials", 0, 1
    page_idx = int(game.get("challenge_page", 0))
    page_idx %= total
    game["challenge_page"] = page_idx
    group = pages[page_idx]
    entries = [c for c in CHALLENGES if c.get("group", group) == group]
    return entries, group, page_idx, total


def reset_progress_for_challenge(entry):
    group = (entry or {}).get("group", "Trials") or "Trials"
    reset_key = CHALLENGE_GROUP_RESET.get(group.lower(), "stability")
    if reset_key == "concept":
        wipe_to_concept_baseline(game)
        game["automation_upgrades"] = []
        game["automation_page"] = 0
    elif reset_key == "inspiration":
        wipe_to_inspiration_baseline(game)
    else:
        wipe_to_stability_baseline(game)
    disable_timeflow = reset_key == "stability"
    game["_challenge_disable_wake_lock"] = disable_timeflow
    if disable_timeflow:
        game["wake_timer_infinite"] = False
        game["wake_timer_locked"] = False
        game["wake_timer_notified"] = False
        game["needs_stability_reset"] = False
        game["time_progress"] = 0.0
        game["time_stratum"] = 0
    recalc_wake_timer_state()
    if disable_timeflow:
        cap = game.get("wake_timer_cap", WAKE_TIMER_START)
        game["wake_timer"] = cap
    refresh_knowledge_flags()
    apply_inspiration_effects()
    apply_concept_effects()
    apply_automation_effects()
    if game.get("motivation_unlocked", False):
        clamp_motivation()
    else:
        game["motivation"] = game.get("motivation", 0)
    target_layer = CHALLENGE_LAYER_TARGET.get(reset_key, 0)
    game["layer"] = target_layer
    global work_timer
    work_timer = 0.0
    save_game()


def challenge_layer_reset():
    entry = active_challenge_entry()
    if not entry or not challenge_run_active_flag():
        set_settings_notice("No active challenge to reset.")
        return False
    reset_progress_for_challenge(entry)
    group = (entry.get("group") or "Trials").lower()
    reset_key = CHALLENGE_GROUP_RESET.get(group, "stability")
    layer_key = CHALLENGE_RESET_LAYER_KEY.get(reset_key, "wake")
    label = layer_name(layer_key, "layer")
    if reset_key == "stability":
        notice = "Challenge instability reset applied."
    else:
        notice = f"{label} baseline reapplied for this challenge run only."
    set_settings_notice(notice, duration=3.0)
    return True


def challenge_reset_hint():
    if not challenge_run_active_flag():
        return ""
    entry = active_challenge_entry()
    if not entry:
        return ""
    group = (entry.get("group") or "Trials").lower()
    reset_key = CHALLENGE_GROUP_RESET.get(group, "stability")
    layer_key = CHALLENGE_RESET_LAYER_KEY.get(reset_key, "wake")
    label = layer_name(layer_key, "Layer")
    if reset_key == "stability":
        desc = "instability"
    else:
        desc = f"{label} baseline"
    return (
        f"{Fore.YELLOW}[R] Challenge Reset{Style.RESET_ALL}: reapply"
        f" {desc} just for this run."
    )


def describe_challenge_modifiers(entry):
    mods = (entry or {}).get("modifiers") or {}
    clauses = []

    def add_percent(label, value):
        if not isinstance(value, (int, float)) or value <= 0 or abs(value - 1.0) < 0.01:
            return
        delta = int(round(abs(1 - value) * 100))
        if delta == 0:
            return
        if value < 1:
            clauses.append(f"{label} -{delta}%")
        else:
            clauses.append(f"{label} +{delta}%")

    add_percent("Income", mods.get("money_gain_mult"))
    add_percent("Inspiration gain", mods.get("inspiration_gain_mult"))
    add_percent("Concept gain", mods.get("concept_gain_mult"))
    add_percent("Auto-work delay", mods.get("auto_delay_mult"))
    add_percent("Motivation cap", mods.get("motivation_cap_mult"))
    add_percent("Time velocity", mods.get("time_velocity_mult"))

    cap_mod = mods.get("wake_timer_cap_mult")
    if isinstance(cap_mod, (int, float)) and cap_mod > 0 and abs(cap_mod - 1.0) > 0.01:
        delta = int(round(abs(1.0 - cap_mod) * 100))
        direction = "-" if cap_mod < 1.0 else "+"
        clauses.append(f"Escape window {direction}{delta}%")

    if mods.get("disable_automation") or mods.get("disable_auto_work"):
        clauses.append("Automation disabled")
    if mods.get("disable_auto_buyer"):
        clauses.append("Auto-buyers disabled")

    return clauses


def summarize_challenge_modifiers(entry):
    clauses = describe_challenge_modifiers(entry)
    return ", ".join(clauses) if clauses else ""


def challenge_feature_ready():
    if game.get("challenges_feature_unlocked", False):
        return True
    return bool(game.get("challenge_instability_installed", False))


def ensure_challenge_feature():
    if game.get("challenges_feature_unlocked", False):
        return False
    if not challenge_feature_ready():
        return False
    game["challenges_feature_unlocked"] = True
    if not game.get("challenge_intro_seen", False):
        set_settings_notice("Challenge board unlocked. Press H to review trials.", duration=4.0)
        game["challenge_intro_seen"] = True
    return True


def challenge_feature_active():
    return bool(game.get("challenges_feature_unlocked", False))


def _challenge_goal(info):
    return max(1, int(info.get("goal_value", 1)))


def _challenge_baseline(metric):
    state = challenge_state_data()
    baseline = state.get("baseline", {})
    return baseline.get(metric, challenge_metric(metric))


def activate_challenge(entry):
    if not entry or entry.get("id") is None:
        return False
    if current_challenge_id():
        return False
    if not begin_challenge_run(entry):
        return False
    metric = entry.get("goal_type")
    state = challenge_state_data()
    state["active_id"] = entry["id"]
    if metric and metric not in EVENT_GOAL_TYPES:
        state["baseline"] = {metric: challenge_metric(metric)}
    else:
        state["baseline"] = {}
    state["started_at"] = time.time()
    state["event_progress"] = {}
    if metric == "phase_lock_completion":
        phase_lock = next((u for u in WAKE_TIMER_UPGRADES if u.get("grant_infinite")), None)
        if phase_lock:
            level = wake_upgrade_level(phase_lock.get("id"))
            required = max(1, int(phase_lock.get("infinite_level", 1)))
            if level >= required:
                state["event_progress"][metric] = 1
    set_settings_notice(f"Challenge activated: {entry.get('name', 'Unknown')}.")
    check_challenges("challenge_start")
    return True


def clear_active_challenge(notice=None, duration=2.5):
    state = challenge_state_data()
    state["active_id"] = None
    state["baseline"] = {}
    state["started_at"] = 0.0
    state["event_progress"] = {}
    restore_pre_challenge_state()
    save_game()
    if notice:
        set_settings_notice(notice, duration=duration)


def forfeit_active_challenge():
    entry = active_challenge_entry()
    if not entry:
        return False
    clear_active_challenge(
        notice=f"Challenge forfeited: {entry.get('name', 'Unknown')}. Modifiers lifted."
    )
    return True


def slot_save_path(idx):
    idx = max(0, min(SAVE_SLOT_COUNT - 1, int(idx)))
    return os.path.join(DATA_DIR, f"save_slot_{idx + 1}.json")


def current_save_path():
    return slot_save_path(ACTIVE_SLOT_INDEX)


def default_game_state():
    return {
        "layer": 0,
        "money": 0.0,
        "money_since_reset": 0.0,
        "fatigue": 0,
        "inspiration": 0,
        "concepts": 0,
        "motivation": 0,
        "motivation_unlocked": False,
        "motivation_cap_bonus": 0,
        "motivation_strength_mult": 1.0,
        "owned": [],
        "upgrade_levels": {},
        "auto_work_unlocked": False,
        "auto_buyer_unlocked": False,
        "inspiration_unlocked": False,
        "concepts_unlocked": False,
        "inspiration_upgrades": [],
        "concept_upgrades": [],
        "automation_upgrades": [],
        "work_delay_multiplier": 1.0,
        "money_mult": 1.0,
        "manual_tap_counter": 0,
        "last_manual_press_ts": 0.0,
        "hold_tip_shown": False,
        "scientific_threshold_exp": SCIENTIFIC_THRESHOLD_DEFAULT,
        "insp_page": 0,
        "concept_page": 0,
        "pulses": 0,
        "veils": 0,
        "sigils": 0,
        "knowledge": {},
        "upgrades_unlocked": False,
        "inspiration_resets": 0,
        "intro_played": False,
        "concept_resets": 0,
        "stability_currency": 0.0,
        "automation_currency": 0.0,
        "stability_resets": 0,
        "stability_manual_resets": 0,
            "wake_timer": WAKE_TIMER_START,
        "wake_timer_cap": WAKE_TIMER_START,
        "wake_timer_infinite": False,
        "wake_timer_locked": False,
        "wake_timer_upgrades": {},
        "wake_timer_notified": False,
        "needs_stability_reset": False,
        "play_time": 0.0,
        "last_save_timestamp": 0.0,
        "resonance_val": RESONANCE_START,
        "resonance_target": 50.0,
        "resonance_drift_dir": 1,
        "breach_key_obtained": False,
        "breach_door_open": False,
        "breach_door_manifested": False,
        "settings_disable_steam": False,
        "settings_show_signal_debug": False,
        "settings_notice": "",
        "settings_notice_until": 0.0,
        "settings_cursor": 0,
        "rpg_unlocked": False,
        "rpg_data": default_rpg_data(),
        "rpg_view": "desktop",
        "rpg_icon_index": 0,
        "rpg_desktop_hint": "",
        "rpg_hint_until": 0.0,
        "signal_multiplier": 1.0,
        "time_progress": 0.0,
        "time_velocity": 1.0,
        "time_reward_multiplier": 1.0,
        "browser_tokens": 0,
        "browser_unlocks": [],
        "browser_notice": "",
        "browser_notice_until": 0.0,
        "browser_cycles": 0,
        "challenges_feature_unlocked": False,
        "challenge_intro_seen": False,
        "challenge_state": default_challenge_state(),
        "challenge_cursor": 0,
        "challenge_page": 0,
        "challenges_completed": [],
        "guide_cursor": 0,
        "guide_unlocked": False,
        "guide_seen_topics": [],
        "guide_unread_topics": [],
        "guide_has_new": False,
        "rpg_tutorial_shown": False,
        "challenge_instability_installed": False,
        "automation_page": 0,
        "automation_delay_mult": 1.0,
        "automation_gain_mult": 1.0,
        "automation_synergy_mult": 1.0,
        "_challenge_backup": None,
        "challenge_run_active": False,
        "challenge_run_id": None,
        "quick_travel_target": "work",
        "escape_machine_unlocked": False,
        "escape_machine_ready": False,
        "escape_machine": default_escape_machine_state(),
        "escape_multiplier": 1.0,
        "mirror_reality_active": False,
    }


last_render, last_size = "", (0, 0)
work_timer, KEY_PRESSED, running = 0.0, None, True
steam = []
steam_last_update = time.time()
view_offset_x = 0
view_offset_y = 0
last_manual_time = 0.0
listener_enabled = True

game = default_game_state()


def guide_available():
    return bool(game.get("guide_unlocked", False))


def ensure_field_guide_unlock():
    if guide_available():
        return False
    total_money = max(
        float(game.get("money_since_reset", 0.0)),
        float(game.get("money", 0.0)),
    )
    if total_money >= FIELD_GUIDE_UNLOCK_TOTAL or game.get("stability_resets", 0) >= 1:
        game["guide_unlocked"] = True
        set_settings_notice("Guide synced. Press G anywhere.", duration=3.0)
        save_game()
        refresh_guide_topics()
        return True
    return False


def guide_topic_unlocked(topic):
    if not topic:
        return False
    requirements = topic.get("requires") or {}
    for key, requirement in requirements.items():
        current = game.get(key)
        if callable(requirement):
            if not requirement():
                return False
        elif isinstance(requirement, bool):
            if bool(current) != requirement:
                return False
        elif isinstance(requirement, (int, float)):
            if float(current or 0) < float(requirement):
                return False
        elif isinstance(requirement, str):
            if not game.get(requirement):
                return False
        else:
            if not current:
                return False
    knowledge_requirements = topic.get("requires_known") or []
    for tag in knowledge_requirements:
        if not is_known(tag):
            return False
    unlock_cond = topic.get("unlock_if")
    if unlock_cond:
        fn = unlock_cond
        if isinstance(unlock_cond, str):
            fn = globals().get(unlock_cond)
        if not callable(fn) or not fn():
            return False
    return True


def available_guide_topics():
    if not guide_available():
        return []
    return [topic for topic in GUIDE_TOPICS if guide_topic_unlocked(topic)]


def refresh_guide_topics():
    if not guide_available():
        return False
    seen = set(game.get("guide_seen_topics", []) or [])
    unread = set(game.get("guide_unread_topics", []) or [])
    new_titles = []
    for topic in GUIDE_TOPICS:
        tid = topic.get("id")
        if not tid or tid in seen:
            continue
        if guide_topic_unlocked(topic):
            seen.add(tid)
            unread.add(tid)
            new_titles.append(topic.get("title", tid))
    if not new_titles:
        return False
    game["guide_seen_topics"] = list(seen)
    game["guide_unread_topics"] = [tid for tid in unread if tid in seen]
    game["guide_has_new"] = True
    latest = new_titles[-1]
    set_settings_notice(f"Guide updated: {latest}. Press G to read.", duration=3.5)
    save_game()
    return True


def guide_render_context():
    return {
        "wake": layer_name("wake", "Desk"),
        "corridor": layer_name("corridor", "Hall"),
        "archive": layer_name("archive", "Echo"),
        "sparks": STABILITY_CURRENCY_NAME,
        "currency_symbol": CURRENCY_SYMBOL,
    }


def browser_effect_totals():
    unlocks = game.get("browser_unlocks", [])
    return compute_browser_effects(unlocks)


def sync_browser_bonuses(rpg):
    if not isinstance(rpg, dict):
        return
    desired = browser_effect_totals()
    current = rpg.get("browser_bonus") or {"max_hp": 0, "atk": 0, "def": 0, "gold": 0}
    for key in ("max_hp", "atk", "def"):
        diff = desired.get(key, 0) - current.get(key, 0)
        if not diff:
            continue
        if key == "max_hp":
            rpg["max_hp"] = max(1, rpg.get("max_hp", 1) + diff)
                                                                  
            rpg["hp"] = max(1, min(rpg["max_hp"], rpg.get("hp", rpg["max_hp"]) + diff))
        elif key == "atk":
            rpg["atk"] = max(1, rpg.get("atk", 1) + diff)
        elif key == "def":
            rpg["def"] = max(0, rpg.get("def", 0) + diff)
    rpg["browser_bonus"] = {
        "max_hp": desired.get("max_hp", 0),
        "atk": desired.get("atk", 0),
        "def": desired.get("def", 0),
        "gold": desired.get("gold", 0),
    }


def _rpg_base_hp_for_cycles(cycles):
    cycles = max(0, int(cycles))
    return RPG_PLAYER_START_HP + cycles * RPG_NG_HP_BONUS


def _rpg_base_atk_for_cycles(cycles):
    cycles = max(0, int(cycles))
    return RPG_PLAYER_START_ATK + cycles * RPG_NG_ATK_BONUS


def rpg_base_hp(rpg):
    return _rpg_base_hp_for_cycles(rpg.get("ng_plus", 0))


def rpg_base_atk(rpg):
    return _rpg_base_atk_for_cycles(rpg.get("ng_plus", 0))


def enforce_ng_plus_baseline(rpg):
    if not isinstance(rpg, dict):
        return
    base_hp = rpg_base_hp(rpg)
    base_atk = rpg_base_atk(rpg)
    max_hp = rpg.get("max_hp", base_hp)
    if max_hp < base_hp:
        rpg["max_hp"] = base_hp
        rpg["hp"] = min(base_hp, rpg.get("hp", base_hp) + (base_hp - max_hp))
    else:
        rpg["max_hp"] = max_hp
        if rpg.get("hp", 0) <= 0:
            rpg["hp"] = base_hp
    gear_bonus = rpg.get("gear_atk_bonus", 0)
    baseline_atk = base_atk + gear_bonus
    if rpg.get("atk", 0) < baseline_atk:
        rpg["atk"] = baseline_atk


def ensure_rpg_state():
    defaults = default_rpg_data()
    rpg = game.setdefault("rpg_data", {})
    for key, value in defaults.items():
        if key not in rpg or rpg[key] is None:
            rpg[key] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
    if not isinstance(rpg.get("inventory"), dict):
        rpg["inventory"] = copy.deepcopy(defaults["inventory"])
    if "potion" not in rpg["inventory"]:
        rpg["inventory"]["potion"] = 0
    if not isinstance(rpg.get("relics"), list):
        rpg["relics"] = []
    enforce_ng_plus_baseline(rpg)
    sync_browser_bonuses(rpg)
    if (not rpg.get("map")) and rpg.get("state") not in {"transition", "shop"}:
        generate_rpg_floor(rpg)
    if not rpg.get("player_pos") and rpg.get("map"):
        center_y = len(rpg["map"]) // 2
        center_x = len(rpg["map"][0]) // 2
        rpg["player_pos"] = [center_y, center_x]
    return rpg


def knowledge_store():
    return game.setdefault("knowledge", {})


def is_known(tag):
    if not tag:
        return False
    return bool(knowledge_store().get(tag))


def mark_known(tag):
    if not tag:
        return False
    known = knowledge_store()
    if known.get(tag):
        return False
    known[tag] = True
    return True


def escape_machine_config():
    return ESCAPE_MACHINE or {}


def escape_machine_state():
    machine = game.setdefault("escape_machine", default_escape_machine_state())
    defaults = default_escape_machine_state()
    for key, value in defaults.items():
        machine.setdefault(key, copy.deepcopy(value) if isinstance(value, (dict, list)) else value)
    return machine


def escape_multiplier():
    try:
        return max(1.0, float(game.get("escape_multiplier", 1.0)))
    except Exception:
        return 1.0


def sparks_visible():
    if not game.get("wake_timer_infinite", False):
        return True
    machine = escape_machine_state()
    if machine.get("unlocked") and "stability_core" not in machine.get("components", []):
        return True
    return False


def machine_component_lookup(component_id):
    cfg = escape_machine_config()
    for component in cfg.get("components", []):
        if component.get("id") == component_id:
            return component
    return None


def machine_requirement_met(component):
    if not component:
        return False
    requirement = component.get("requirement") or {}
    req_type = requirement.get("type")
    value = requirement.get("value", 0)
    if req_type == "spark_bank":
        return escape_machine_state().get("spark_bank", 0) >= value
    if req_type == "inspiration_resets":
        return game.get("inspiration_resets", 0) >= value
    if req_type == "concept_resets":
        return game.get("concept_resets", 0) >= value
    if req_type == "rpg_floor":
        rpg = game.get("rpg_data") or {}
        return max(rpg.get("max_floor", 0), rpg.get("floor", 0)) >= value
    return False


def describe_machine_requirement(component):
    requirement = component.get("requirement") or {}
    value = requirement.get("value", 0)
    req_type = requirement.get("type")
    if req_type == "spark_bank":
        progress = escape_machine_state().get("spark_bank", 0)
        return f"Bank Sparks: {format_number(progress)}/{format_number(value)}"
    if req_type == "inspiration_resets":
        current = game.get("inspiration_resets", 0)
        return f"Inspiration resets: {current}/{value}"
    if req_type == "concept_resets":
        current = game.get("concept_resets", 0)
        return f"Concept resets: {current}/{value}"
    if req_type == "rpg_floor":
        rpg = game.get("rpg_data") or {}
        current = max(rpg.get("max_floor", 0), rpg.get("floor", 0))
        return f"RPG floor cleared: {current}/{value}"
    return "Requirement pending"


MACHINE_SPINNER_FRAMES = ["-", "\\", "|", "/"]
MACHINE_BEAM_FRAMES = ["--==", "==--", "<><>", "~==~"]
MACHINE_TRAIL_PATTERN = ["-", "=", "~", "+"]
MACHINE_CORE_FRAMES = ["<>", "><", "::", "**", "==", "//", "\\\\", "||", "--"]
MACHINE_DEPTH_SHADES = ["..", "--", "==", "##", "@@"]
MACHINE_SWIRL_CHARS = list("@#%&*+=-:.")
MACHINE_SHADE_CHARS = list("@%#*+=-:. ")
PORTAL_PHASE_LABELS = [
    "Phase 0 · Dormant Antechamber",
    "Phase 1 · Resonance Collar",
    "Phase 2 · Corridor Lattice",
    "Phase 3 · Echo Frame",
    "Phase 4 · Flux Engine",
]
CREDITS_ROLES = [
    ("Lead Developer", "SadDiamonds"),
    ("Tester", "Isaac"),
    ("Tester & Balancer", "David"),
]


def portal_stage_params(stage, total_components, completion_ratio):
    total_components = max(1, total_components)
    stage = max(0, min(stage, total_components))
    normalized = stage / total_components
    width = 65 + stage * 4
    height = 23 + stage * 2
    tilt = 1.35 - normalized * 0.25
    ring_radius = 6.5 + completion_ratio * 1.25 + stage * 0.2
    ring_thickness = 1.4 + completion_ratio * 0.4 + normalized * 0.25
    halo_gain = 1.8 + normalized * 0.7
    accent_count = stage
    beam_pairs = max(0, stage - 1)
    swirl_speed = 0.15 + normalized * 0.08
    ripple_strength = 0.08 + stage * 0.015
    overlay_chars = ["<>", "[]", "{}", "##", "//"]
    return {
        "width": width,
        "height": height,
        "tilt": tilt,
        "ring_radius": ring_radius,
        "ring_thickness": ring_thickness,
        "halo_gain": halo_gain,
        "accent_count": accent_count,
        "beam_pairs": beam_pairs,
        "swirl_speed": swirl_speed,
        "ripple_strength": ripple_strength,
        "overlay_chars": overlay_chars,
    }


def machine_requirement_ratio(component):
    if not component:
        return 0.0
    requirement = component.get("requirement") or {}
    req_type = requirement.get("type")
    value = requirement.get("value")
    if not value:
        return 1.0 if machine_requirement_met(component) else 0.0
    if req_type == "spark_bank":
        current = escape_machine_state().get("spark_bank", 0)
    elif req_type == "inspiration_resets":
        current = game.get("inspiration_resets", 0)
    elif req_type == "concept_resets":
        current = game.get("concept_resets", 0)
    elif req_type == "rpg_floor":
        rpg = game.get("rpg_data") or {}
        current = max(rpg.get("max_floor", 0), rpg.get("floor", 0))
    else:
        current = 0
    try:
        return max(0.0, min(1.0, float(current) / float(value)))
    except Exception:
        return 0.0


def machine_component_icon(installed, phase, offset=0):
    if installed:
        return f"{Fore.GREEN}[#]{Style.RESET_ALL}"
    frame = MACHINE_SPINNER_FRAMES[(phase + offset) % len(MACHINE_SPINNER_FRAMES)]
    return f"{Fore.CYAN}[{frame}]{Style.RESET_ALL}"


def machine_component_bar(component, installed, phase, width=18):
    width = max(6, int(width))
    if installed:
        return f"{Fore.GREEN}{'#' * width}{Style.RESET_ALL}"
    ratio = machine_requirement_ratio(component)
    filled = int(round(width * ratio))
    if ratio > 0 and filled <= 0:
        filled = 1
    filled = min(width, filled)
    chars = []
    for idx in range(width):
        if idx < filled:
            chars.append("=")
        else:
            chars.append(
                MACHINE_TRAIL_PATTERN[(phase + idx) % len(MACHINE_TRAIL_PATTERN)]
            )
    color = Fore.YELLOW if filled else Fore.MAGENTA
    return f"{color}{''.join(chars)}{Style.RESET_ALL}"


def build_machine_portal_art(
    machine,
    components,
    installed_set,
    phase,
    stage_override=None,
    completion_override=None,
    flare=0.0,
):
    if not components:
        return []
    total = len(components)
    installed_count = sum(1 for comp in components if comp.get("id") in installed_set)
    if completion_override is None:
        completion_ratio = installed_count / total if total else 0.0
    else:
        completion_ratio = max(0.0, min(1.0, float(completion_override)))
    spark_bank = format_number(machine.get("spark_bank", 0))
    stage = stage_override if stage_override is not None else installed_count
    stage_for_params = max(0, min(stage, total))
    params = portal_stage_params(stage_for_params, total, completion_ratio)
    width = params["width"]
    height = params["height"]
    ring_radius = params["ring_radius"]
    ring_thickness = params["ring_thickness"]
    inner_portal = ring_radius - ring_thickness * 0.9
    halo_radius = ring_radius + ring_thickness * params["halo_gain"]
    phase_angle = phase * params["swirl_speed"]
    swirl_offset = phase % len(MACHINE_SWIRL_CHARS)
    shade_count = len(MACHINE_SHADE_CHARS) - 1
    flare = max(0.0, min(1.0, float(flare)))
    accent_angles = []
    if params["accent_count"] > 0:
        for idx in range(params["accent_count"]):
            base_angle = (2 * math.pi * idx / params["accent_count"]) + phase * 0.07
            accent_angles.append(base_angle)
    beam_pairs = params.get("beam_pairs", 0)
    overlays = []
    art_lines = []
    for y in range(-height // 2, height // 2 + 1):
        row_chars = []
        wobble = 1.0 + params["ripple_strength"] * math.sin(phase_angle + y * 0.12)
        for x in range(-width // 2, width // 2 + 1):
            ax = x / 3.0
            ay = y / (params["tilt"] * wobble)
            radius = math.hypot(ax, ay)
            angle = math.atan2(ay, ax)
            char = " "
            color = Style.DIM
            near_accent = False
            for idx, a in enumerate(accent_angles):
                if abs(math.atan2(math.sin(angle - a), math.cos(angle - a))) <= 0.18:
                    near_accent = True
                    accent_char = params["overlay_chars"][idx % len(params["overlay_chars"])]
                    break
            if radius <= inner_portal:
                swirl_idx = int(((angle + math.pi) / (2 * math.pi)) * len(MACHINE_SWIRL_CHARS))
                swirl_idx = (swirl_idx + swirl_offset) % len(MACHINE_SWIRL_CHARS)
                char = MACHINE_SWIRL_CHARS[swirl_idx]
                glow = 0.5 + 0.5 * math.cos(angle * 3 - phase_angle * 2)
                glow += flare * 0.35
                color = Fore.MAGENTA if glow < 0.6 else Fore.LIGHTMAGENTA_EX
            elif abs(radius - ring_radius) <= ring_thickness:
                depth = abs(radius - ring_radius) / ring_thickness
                highlight = 0.65 + 0.35 * math.cos(angle - phase_angle) + flare * 0.25
                intensity = max(0.0, min(1.0, (1.0 - depth) * highlight))
                idx = min(shade_count, int(round(intensity * shade_count)))
                char = MACHINE_SHADE_CHARS[idx]
                if near_accent:
                    char = accent_char
                    color = Fore.YELLOW
                else:
                    color = Fore.CYAN if intensity < 0.55 else Fore.WHITE
            elif radius <= halo_radius:
                haze = (radius - ring_radius) / max(0.001, halo_radius - ring_radius)
                idx = min(len(MACHINE_TRAIL_PATTERN) - 1, int(haze * len(MACHINE_TRAIL_PATTERN)))
                char = MACHINE_TRAIL_PATTERN[idx]
                color = Fore.BLUE
            elif radius <= halo_radius + 2.5:
                char = " ."[(x + y + phase) & 1]
                color = Fore.LIGHTBLACK_EX
            else:
                char = " "
                color = Style.DIM
            row_chars.append(f"{color}{char}{Style.RESET_ALL}")
        art_lines.append("".join(row_chars).rstrip())
    if beam_pairs > 0:
        overlays.append(
            f"      {Fore.LIGHTWHITE_EX}{'=' * (12 + 2 * beam_pairs)}{Style.RESET_ALL}"
        )
    art_lines.append("")
    art_lines.append(
        f"      Flux Horizon: {Fore.GREEN}{completion_ratio * 100:05.1f}%{Style.RESET_ALL}   Components: {installed_count}/{total}"
    )
    art_lines.append(f"      Spark Feed: {Fore.YELLOW}{spark_bank}{Style.RESET_ALL}")
    phase_label_idx = min(len(PORTAL_PHASE_LABELS) - 1, max(0, stage))
    art_lines.append(
        f"      {Fore.LIGHTCYAN_EX}{PORTAL_PHASE_LABELS[phase_label_idx]}{Style.RESET_ALL}"
    )
    art_lines.extend(overlays)
    return art_lines


def build_machine_visual_block(machine, cfg, phase):
    components = cfg.get("components", [])
    installed_set = set(machine.get("components", []))
    return build_machine_portal_art(machine, components, installed_set, phase)


def build_machine_component_block(component, installed_set, phase, idx):
    lines = []
    cid = component.get("id")
    installed = cid in installed_set
    icon = machine_component_icon(installed, phase, idx)
    name = component.get("name", "Component")
    emphasis = Style.BRIGHT if not installed else ""
    reset = Style.RESET_ALL if emphasis else ""
    lines.append(f"{icon} {emphasis}{name}{reset}")
    bar = machine_component_bar(component, installed, phase)
    ratio = 1.0 if installed else machine_requirement_ratio(component)
    status = "Installed" if installed else f"{int(ratio * 100):02d}% forged"
    lines.append(f"    |{bar}| {status}")
    desc = component.get("desc")
    if desc:
        lines.append(f"    {desc}")
    if not installed:
        lines.append(
            f"    {Style.DIM}{describe_machine_requirement(component)}{Style.RESET_ALL}"
        )
    lines.append("")
    return lines


def play_escape_reset_animation(machine):
    cfg = escape_machine_config()
    if not cfg:
        return
    components = cfg.get("components", [])
    if not components:
        return
    installed_set = set(machine.get("components", []))
    frames = 36
    for idx in range(frames):
        work_tick()
        progress = idx / max(1, frames - 1)
        flare = min(1.0, progress * 1.2)
        lines = build_machine_portal_art(
            machine,
            components,
            installed_set,
            phase=idx * 2,
            stage_override=len(components),
            completion_override=max(progress, 0.15),
            flare=flare,
        )
        dots = "." * (1 + (idx % 3))
        lines.append("")
        lines.append(
            f"      {Fore.LIGHTYELLOW_EX}Reality Diverter recalibrating{dots}{Style.RESET_ALL}"
        )
        box = boxed_lines(lines, title=" Diverter Ignition ", pad_top=1, pad_bottom=1)
        render_frame(box)
        time.sleep(0.05 + progress * 0.04)
    time.sleep(0.25)
    clear_screen()


def wait_for_any_keypress(timeout=None):
    global KEY_PRESSED
    start = time.time()
    while True:
        if KEY_PRESSED:
            KEY_PRESSED = None
            return True
        if timeout is not None and (time.time() - start) >= timeout:
            return False
        time.sleep(0.05)


def play_mirror_reality_epilogue():
    narrative_lines = [
        "The Diverter slams shut and the desk dissolves into argent static.",
        "Your memories fracture, scattering into mirrored shards.",
        "A new desk flickers online—familiar, but every panel reversed.",
        "Reality reforms. The machine is silent, its components missing once more.",
        "Some echo of you persists, chasing the next escape.",
    ]
    rendered = []
    clear_screen()
    for line in narrative_lines:
        partial = ""
        for ch in line:
            partial += ch
            preview = rendered + [partial]
            box = boxed_lines(preview, title=" Mirrorfall Narrative ", pad_top=1, pad_bottom=1)
            render_frame(box)
            time.sleep(TYPEWRITER_STEP_DELAY)
        rendered.append(line)
        time.sleep(0.35)
    prompt = f"{Fore.YELLOW}Press any key to reinitialize.{Style.RESET_ALL}"
    box = boxed_lines(rendered + ["", prompt], title=" Mirrorfall Narrative ", pad_top=1, pad_bottom=1)
    render_frame(box)
    wait_for_any_keypress()
    clear_screen()


def maybe_unlock_escape_machine():
    cfg = escape_machine_config()
    if not cfg:
        return False
    machine = escape_machine_state()
    if machine.get("unlocked"):
        return False
    unlock = cfg.get("unlock") or {}
    if game.get("stability_resets", 0) < unlock.get("stability_resets", 0):
        return False
    rpg = game.get("rpg_data") or {}
    rpg_requirement = unlock.get("rpg_max_floor", 0)
    if max(rpg.get("max_floor", 0), rpg.get("floor", 0)) < rpg_requirement:
        return False
    machine["unlocked"] = True
    game["escape_machine_unlocked"] = True
    mark_known("escape_machine")
    set_settings_notice("Reality Diverter schematics downloaded. Press M at the desk.", duration=4.0)
    save_game()
    return True


def check_escape_machine_progress():
    machine = escape_machine_state()
    if not machine.get("unlocked"):
        return maybe_unlock_escape_machine()
    cfg = escape_machine_config()
    updated = False
    components = machine.setdefault("components", [])
    for component in cfg.get("components", []):
        cid = component.get("id")
        if not cid or cid in components:
            continue
        if machine_requirement_met(component):
            components.append(cid)
            updated = True
            message = f"{component.get('name', 'Component')} installed."
            set_settings_notice(message, duration=3.0)
    if updated:
        save_game()
    if not machine.get("ready") and cfg.get("components") and len(components) == len(cfg.get("components", [])):
        machine["ready"] = True
        game["escape_machine_ready"] = True
        set_settings_notice("Reality Diverter assembled. Press M to ignite.", duration=4.0)
        save_game()
        return True
    return updated


def handle_machine_progress_event(source=None):
    changed = maybe_unlock_escape_machine()
    changed |= check_escape_machine_progress()
    return changed


def perform_machine_escape_reset():
    cfg = escape_machine_config()
    machine = escape_machine_state()
    if not machine.get("ready") or machine.get("applied"):
        return False
    multiplier = max(escape_multiplier(), cfg.get("reset_multiplier", 2.0))
    machine_state_for_anim = copy.deepcopy(machine)
    try:
        play_escape_reset_animation(machine_state_for_anim)
        play_mirror_reality_epilogue()
    except Exception:
        pass
    machine["ready"] = False
    machine["applied"] = True
    fresh_machine = default_escape_machine_state()
    fresh_machine["unlocked"] = True
    fresh_machine["components"] = []
    fresh_machine["ready"] = False
    fresh_machine["applied"] = False
    fresh_machine["spark_bank"] = 0
    machine_snapshot = fresh_machine
    knowledge_snapshot = copy.deepcopy(knowledge_store())
    guide_seen = list(game.get("guide_seen_topics", []))
    guide_unlocked = game.get("guide_unlocked", False)
    new_state = default_game_state()
    game.clear()
    game.update(new_state)
    game["knowledge"] = knowledge_snapshot
    game["guide_unlocked"] = guide_unlocked
    game["guide_seen_topics"] = guide_seen
    game["guide_unread_topics"] = []
    game["guide_has_new"] = False
    game["escape_machine"] = machine_snapshot
    game["escape_machine_unlocked"] = True
    game["escape_machine_ready"] = False
    game["escape_multiplier"] = multiplier
    game["mirror_reality_active"] = True
    set_settings_notice(
        f"Mirror reality stabilized. Diverter schematics scrambled; rewards locked at ×{multiplier:.0f}.",
        duration=4.0,
    )
    save_game()
    return True


def open_escape_machine_panel():
    global KEY_PRESSED
    cfg = escape_machine_config()
    if not cfg or not cfg.get("components"):
        set_settings_notice("Reality Diverter schematics unavailable.")
        return
    machine = escape_machine_state()
    if not machine.get("unlocked"):
        set_settings_notice("Reality Diverter not unlocked yet.")
        return
    last_box = None
    last_size = get_term_size()
    while True:
        work_tick()
        phase = int(time.time() * 6)
        machine = escape_machine_state()
        lines = [
            "Reality Diverter Assembly",
            "",
            f"Spark Bank: {format_number(machine.get('spark_bank', 0))}",
            "",
        ]
        visual_lines = build_machine_visual_block(machine, cfg, phase)
        if visual_lines:
            lines.extend(visual_lines)
            lines.append("")
        lines.append("Assembly Log")
        lines.append("")
        installed_set = set(machine.get("components", []))
        for idx, component in enumerate(cfg.get("components", [])):
            lines.extend(
                build_machine_component_block(component, installed_set, phase, idx)
            )
        if machine.get("ready") and not machine.get("applied"):
            mult = cfg.get("reset_multiplier", 2.0)
            lines.append(f"Press Enter to ignite the Diverter and restart with ×{mult:.0f} base rewards.")
        else:
            lines.append("Components install automatically once their requirements are met.")
        lines.append("Press B to return.")
        box = boxed_lines(lines, title=" Diverter Console ", pad_top=1, pad_bottom=1)
        cur_size = get_term_size()
        frame = "\n".join(box)
        if frame != last_box or cur_size != last_size:
            render_frame(box)
            last_box = frame
            last_size = cur_size
        time.sleep(0.05)
        if not KEY_PRESSED:
            continue
        key = KEY_PRESSED
        KEY_PRESSED = None
        try:
            k = key.lower() if isinstance(key, str) else key
        except Exception:
            k = key
        if k in {"b", "q"}:
            return
        if k in {"\r", "\n", "enter"}:
            if machine.get("ready") and not machine.get("applied"):
                if perform_machine_escape_reset():
                    return


def open_credits_panel():
    global KEY_PRESSED
    last_box = None
    last_size = get_term_size()
    while True:
        work_tick()
        lines = [
            "Production Credits",
            "",
            f"{Fore.LIGHTWHITE_EX}{GAME_TITLE.upper()}{Style.RESET_ALL}",
            "",
        ]
        for role, name in CREDITS_ROLES:
            color = Fore.CYAN if "Lead" in role else Fore.LIGHTMAGENTA_EX
            if "Balancer" in role:
                color = Fore.YELLOW
            lines.append(f"{color}{role}{Style.RESET_ALL}")
            lines.append(f"   {name}")
            lines.append("")
        lines.append(f"{Fore.LIGHTBLACK_EX}Thank you for supporting the loop.{Style.RESET_ALL}")
        lines.append("Press B to return.")
        box = boxed_lines(lines, title=" Credits ", pad_top=1, pad_bottom=1)
        cur_size = get_term_size()
        frame = "\n".join(box)
        if frame != last_box or cur_size != last_size:
            render_frame(box)
            last_box = frame
            last_size = cur_size
        time.sleep(0.05)
        if not KEY_PRESSED:
            continue
        key = KEY_PRESSED
        KEY_PRESSED = None
        try:
            k = key.lower() if isinstance(key, str) else key
        except Exception:
            k = key
        if k in {"b", "q", "enter"}:
            return


def motivation_capacity():
    bonus = max(0, int(game.get("motivation_cap_bonus", 0)))
    capacity = max(1, MOTIVATION_MAX + bonus)
    cap_mult = get_challenge_modifier("motivation_cap_mult")
    if isinstance(cap_mult, (int, float)) and cap_mult > 0:
        capacity = max(1, int(round(capacity * cap_mult)))
    return capacity


def motivation_peak_multiplier():
    strength = max(1.0, float(game.get("motivation_strength_mult", 1.0)))
    return MAX_MOTIVATION_MULT * strength


def set_motivation(value):
    cap = motivation_capacity()
    if value is None:
        value = cap
    clamped = max(0.0, min(float(cap), float(value)))
    rounded = round(clamped + 1e-8, 1)
    game["motivation"] = rounded
    return rounded


def clamp_motivation():
    current = game.get("motivation", motivation_capacity())
    return set_motivation(current)


def describe_motivation_state(pct):
    if pct is None:
        return None
    if pct >= 90:
        return f"{Fore.GREEN}Motivation{Style.RESET_ALL}"
    if pct >= 60:
        return f"{Fore.GREEN}.Motivation{Style.RESET_ALL}"
    if pct >= 35:
        return f"{Fore.YELLOW}..Motivation{Style.RESET_ALL}"
    if pct >= 10:
        return f"{Fore.YELLOW}...Motivation{Style.RESET_ALL}"
    return f"{Fore.RED}Burned out{Style.RESET_ALL}"


def build_status_ribbon(calc_insp, calc_conc, mot_pct=None, mot_mult=None):
    segments = []
    if calc_insp is not None and calc_insp > 0:
        segments.append(
            f"{Fore.LIGHTYELLOW_EX}I {format_number(calc_insp)}{Style.RESET_ALL}"
        )
    if calc_conc is not None and calc_conc > 0:
        segments.append(f"{Fore.CYAN}C {format_number(calc_conc)}{Style.RESET_ALL}")
    if resonance_system_active():
        signal_mult = max(0.0, game.get("signal_multiplier", 1.0))
        segments.append(f"{Fore.MAGENTA}Signal ×{signal_mult:.2f}{Style.RESET_ALL}")
    mood = describe_motivation_state(mot_pct)
    if mood:
        if mot_mult is not None and mot_mult > 1:
            segments.append(f"{mood} ×{mot_mult:.2f}")
        else:
            segments.append(mood)
    if not segments:
        return None
    return "  ·  ".join(segments)


def reveal_text(tag, text, placeholder="???"):
                                                         
    return text


def layer_name(key, placeholder="???"):
    layer_def = LAYER_BY_KEY.get(key)
    if not layer_def:
        return placeholder
    fallback = layer_def.get("name", placeholder)
    return reveal_text(f"layer_{key}", fallback, placeholder)


def layer_currency_name(key, placeholder="???"):
    layer_def = LAYER_BY_KEY.get(key)
    if not layer_def:
        return placeholder
    return reveal_text(
        f"currency_{key}", layer_def.get("currency_name", placeholder), placeholder
    )


def layer_currency_suffix(key, placeholder=""):
    layer_def = LAYER_BY_KEY.get(key)
    if not layer_def:
        return placeholder
    return reveal_text(
        f"currency_{key}", layer_def.get("currency_suffix", placeholder), placeholder
    )


def current_layer_label():
    layer_idx = game.get("layer", 0)
    layer_def = LAYER_BY_ID.get(layer_idx)
    if not layer_def:
        return f"Layer {layer_idx}"
    fallback = f"Layer {layer_idx}"
    return reveal_text(
        f"layer_{layer_def['key']}", layer_def.get("name", fallback), fallback
    )


KNOWLEDGE_REQUIREMENTS = {
    "layer_wake": {"money_since_reset": 2_500, "play_time": 120},
    "ui_options_hint": {"money_since_reset": 4_000, "play_time": 180},
    "currency_wake": {"inspiration_resets": 1},
    "ui_currency_clear": {"inspiration_resets": 1},
    "ui_upgrade_catalogue": {"inspiration_resets": 1},
    "ui_auto_prompt": {"concept_resets": 1, "play_time": 480},
    "layer_corridor": {"inspiration_resets": 2},
    "currency_corridor": {"inspiration_resets": 3},
    "layer_archive": {"concept_resets": 2},
    "currency_archive": {"concept_resets": 3},
    "escape_window": {"mystery_revealed": 1},
    "escape_route": {"stability_resets": 1},
    "escape_signal": {"concept_resets": 1},
}


def knowledge_requirements_met(tag):
    reqs = KNOWLEDGE_REQUIREMENTS.get(tag)
    if not reqs:
        return True
    for metric, threshold in reqs.items():
        if metric == "money_since_reset":
            current = game.get("money_since_reset", 0)
        elif metric == "play_time":
            current = game.get("play_time", 0.0)
        elif metric == "inspiration_resets":
            current = game.get("inspiration_resets", 0)
        elif metric == "concept_resets":
            current = game.get("concept_resets", 0)
        else:
            current = game.get(metric, 0)
        if current < threshold:
            return False
    return True


def attempt_reveal(tag):
    if not knowledge_requirements_met(tag):
        return False
    return mark_known(tag)


def get_wake_upgrade_levels():
    raw = game.get("wake_timer_upgrades", {})
    if isinstance(raw, dict):
        cleaned = {}
        for key, value in raw.items():
            try:
                level = int(value)
            except (TypeError, ValueError):
                continue
            if level > 0:
                cleaned[key] = level
        if cleaned != raw:
            game["wake_timer_upgrades"] = cleaned
        return game["wake_timer_upgrades"]
    levels = {}
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                uid = entry.get("id")
                level = entry.get("level", 1)
            else:
                uid = entry
                level = 1
            if not uid:
                continue
            try:
                level = int(level)
            except (TypeError, ValueError):
                level = 0
            if level <= 0:
                continue
            levels[uid] = max(levels.get(uid, 0), level)
    game["wake_timer_upgrades"] = levels
    return game["wake_timer_upgrades"]


def wake_upgrade_level(upg_id):
    if not upg_id:
        return 0
    return get_wake_upgrade_levels().get(upg_id, 0)


def _scaled_series_total(base, scale, level):
    if level <= 0 or base == 0:
        return 0.0
    if abs(scale - 1.0) < 1e-9:
        return float(base) * level
    return float(base) * ((scale**level - 1.0) / (scale - 1.0))


def _scaled_step_value(base, scale, index):
    if base == 0:
        return 0.0
    return float(base) * (scale**index)


def wake_upgrade_total_bonus(upg, level, field, scale_field):
    base = float(upg.get(field, 0) or 0)
    if base == 0 or level <= 0:
        return 0.0
    scale = float(upg.get(scale_field, upg.get("value_mult", 1.0)) or 1.0)
    return _scaled_series_total(base, max(0.0, scale), level)


def wake_upgrade_next_bonus(upg, level, field, scale_field):
    base = float(upg.get(field, 0) or 0)
    if base == 0:
        return 0.0
    scale = float(upg.get(scale_field, upg.get("value_mult", 1.0)) or 1.0)
    return _scaled_step_value(base, max(0.0, scale), level)


def wake_upgrade_cost(upg, current_level=None):
    if current_level is None:
        current_level = wake_upgrade_level(upg.get("id"))
    base_cost = float(upg.get("cost", 0) or 0)
    scale = float(upg.get("cost_scale", upg.get("cost_mult", 1.0)) or 1.0)
    return int(round(base_cost * (scale**current_level)))


def recalc_wake_timer_state():
    purchased = get_wake_upgrade_levels()
    cap = WAKE_TIMER_START
    infinite = game.get("wake_timer_infinite", False)
    challenge_lock = bool(game.get("_challenge_disable_wake_lock", False))
    for upg in WAKE_TIMER_UPGRADES:
        level = purchased.get(upg["id"], 0)
        if level <= 0:
            continue
        time_bonus = wake_upgrade_total_bonus(upg, level, "time_bonus", "time_bonus_scale")
        if time_bonus:
            cap += int(round(time_bonus))
        if upg.get("grant_infinite"):
            required = max(1, int(upg.get("infinite_level", 1)))
            if level >= required:
                infinite = True
    mods = active_challenge_modifiers()
    cap_mult = mods.get("wake_timer_cap_mult", 1.0)
    if isinstance(cap_mult, (int, float)) and cap_mult > 0:
        cap = max(30.0, cap * cap_mult)
    if challenge_lock:
        infinite = False
    game["wake_timer_cap"] = cap
    game["wake_timer_infinite"] = infinite
    if infinite:
        game["wake_timer_locked"] = False
        game["wake_timer_notified"] = False
        game["wake_timer"] = cap
    else:
        remaining = max(0.0, min(game.get("wake_timer", cap), cap))
        game["wake_timer"] = remaining
        game["wake_timer_locked"] = remaining <= 0


def wake_timer_blocked():
    return (not game.get("wake_timer_infinite", False)) and game.get("wake_timer", 0) <= 0


def format_clock(seconds):
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes:02d}:{sec:02d}"


def show_wake_timer_warning():
    if game.get("wake_timer_infinite", False) or not wake_timer_blocked():
        return
    if game.get("wake_timer_notified", False):
        return
    msg = [
        "Collapse underway.",
        f"Failure yields {STABILITY_CURRENCY_NAME}.",
    ]
    tmp = boxed_lines(msg, title=" Collapse Imminent ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(0.9)
    game["wake_timer_notified"] = True


def build_wake_timer_line():
    if game.get("wake_timer_infinite", False):
        return "Escape Window: ∞ (locked open)"
    remaining = max(0, int(game.get("wake_timer", WAKE_TIMER_START)))
    cap = max(1, int(game.get("wake_timer_cap", WAKE_TIMER_START)))
    ratio = remaining / cap if cap else 0
    if ratio > 0.45:
        status = "steady"
    elif ratio > 0.2:
        status = "faltering"
    else:
        status = "critical"
    label = f"Escape Window: {format_clock(remaining)} ({status})"
    if wake_timer_blocked():
        label += "  sealed"
    return label


def veil_text(text, min_visible=1, placeholder="?"):
    return text or ""


def veil_numeric_string(text, reveal_ratio=0.35, placeholder="?"):
    return text or ""


def format_currency(amount):
    rendered = format_number(amount)
    return f"{CURRENCY_SYMBOL}{rendered}"


def save_game():
    ensure_rpg_state()
    game["last_save_timestamp"] = time.time()
    payload = copy.deepcopy(game)
    target_path = current_save_path()
    tmp_path = target_path + ".tmp"
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    try:
        with open(tmp_path, "w") as handle:
            json.dump(payload, handle)
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def load_game():
    candidate_paths = [current_save_path()]
    if ACTIVE_SLOT_INDEX == 0 and os.path.exists(LEGACY_SAVE_PATH):
        candidate_paths.append(LEGACY_SAVE_PATH)
    payload = None
    for path in candidate_paths:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                payload = data
                break
        except Exception:
            continue
    state = default_game_state()
    if payload:
        state.update(payload)
        rpg_state = payload.get("rpg_data")
        if not isinstance(rpg_state, dict):
            rpg_state = default_rpg_data()
        else:
            defaults = default_rpg_data()
            for key, value in defaults.items():
                if key not in rpg_state or rpg_state[key] is None:
                    rpg_state[key] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
        state["rpg_data"] = rpg_state
    if "breach_key_obtained" not in state:
        state["breach_key_obtained"] = False
    if "breach_door_open" not in state:
        state["breach_door_open"] = bool(state.get("rpg_unlocked", False))
    if state.get("breach_door_open"):
        state["rpg_unlocked"] = True
        state["breach_key_obtained"] = True
    if "settings_disable_steam" not in state:
        state["settings_disable_steam"] = False
    if "settings_show_signal_debug" not in state:
        state["settings_show_signal_debug"] = False
    state.setdefault("settings_notice", "")
    state.setdefault("settings_notice_until", 0.0)
    state.setdefault("settings_cursor", 0)
    state.setdefault("breach_door_manifested", bool(state.get("breach_key_obtained", False)))
    state.setdefault("time_progress", 0.0)
    state.setdefault("time_stratum", 0)
    state.setdefault("time_velocity", 1.0)
    state.setdefault("time_reward_multiplier", 1.0)
    state.setdefault("manual_tap_counter", 0)
    state.setdefault("last_manual_press_ts", 0.0)
    state.setdefault("hold_tip_shown", False)
    state.setdefault("automation_currency", 0.0)
    state.setdefault("scientific_threshold_exp", SCIENTIFIC_THRESHOLD_DEFAULT)
    state.setdefault("quick_travel_target", "work")
    state.setdefault("motivation_unlocked", False)
    state.setdefault("motivation_cap_bonus", 0)
    state.setdefault("motivation_strength_mult", 1.0)
    state.setdefault("challenges_feature_unlocked", False)
    state.setdefault("challenge_intro_seen", False)
    state.setdefault("challenge_cursor", 0)
    state.setdefault("challenge_page", 0)
    state.setdefault("challenge_instability_installed", False)
    state.setdefault("guide_cursor", 0)
    state.setdefault("guide_unlocked", False)
    state.setdefault("guide_seen_topics", [])
    state.setdefault("guide_has_new", False)
    state.setdefault("rpg_tutorial_shown", False)
    state.setdefault("automation_upgrades", [])
    state.setdefault("automation_page", 0)
    state.setdefault("automation_delay_mult", 1.0)
    state.setdefault("automation_gain_mult", 1.0)
    state.setdefault("automation_synergy_mult", 1.0)
    state.setdefault("automation_auto_tiers", 0)
    state.setdefault("_challenge_backup", None)
    state.setdefault("challenge_run_active", False)
    state.setdefault("challenge_run_id", None)
    state.setdefault("escape_multiplier", 1.0)
    state.setdefault("mirror_reality_active", False)
    machine_state = state.get("escape_machine")
    if not isinstance(machine_state, dict):
        machine_state = default_escape_machine_state()
    else:
        defaults = default_escape_machine_state()
        for key, value in defaults.items():
            machine_state.setdefault(key, value)
    state["escape_machine"] = machine_state
    state.setdefault("escape_machine_unlocked", machine_state.get("unlocked", False))
    state.setdefault("escape_machine_ready", machine_state.get("ready", False))
    challenge_state = state.get("challenge_state")
    if not isinstance(challenge_state, dict):
        state["challenge_state"] = default_challenge_state()
    else:
        challenge_state.setdefault("active_id", None)
        baseline = challenge_state.get("baseline")
        if not isinstance(baseline, dict):
            challenge_state["baseline"] = {}
        challenge_state.setdefault("started_at", 0.0)
        events = challenge_state.get("event_progress")
        if not isinstance(events, dict):
            challenge_state["event_progress"] = {}
    state.setdefault("challenges_completed", [])
    state.setdefault("auto_buyer_unlocked", False)
    state.setdefault("stability_manual_resets", 0)
    raw_wake_upgrades = state.get("wake_timer_upgrades")
    if isinstance(raw_wake_upgrades, dict):
        cleaned = {}
        for key, value in raw_wake_upgrades.items():
            try:
                lvl = int(value)
            except (TypeError, ValueError):
                continue
            if lvl > 0:
                cleaned[key] = lvl
        state["wake_timer_upgrades"] = cleaned
    elif isinstance(raw_wake_upgrades, list):
        cleaned = {}
        for entry in raw_wake_upgrades:
            if isinstance(entry, dict):
                uid = entry.get("id")
                lvl = entry.get("level", 1)
            else:
                uid = entry
                lvl = 1
            if not uid:
                continue
            try:
                lvl = int(lvl)
            except (TypeError, ValueError):
                lvl = 0
            if lvl <= 0:
                continue
            cleaned[uid] = max(cleaned.get(uid, 0), lvl)
        state["wake_timer_upgrades"] = cleaned
    else:
        state["wake_timer_upgrades"] = {}
    if not state.get("guide_unlocked"):
        total_money = max(
            float(state.get("money_since_reset", 0.0)),
            float(state.get("money", 0.0)),
        )
        if total_money >= FIELD_GUIDE_UNLOCK_TOTAL or state.get("stability_resets", 0) >= 1:
            state["guide_unlocked"] = True
    game.clear()
    game.update(state)
    sync_scientific_threshold(game.get("scientific_threshold_exp"))
    ensure_rpg_state()
    apply_inspiration_effects()
    apply_concept_effects()
    apply_automation_effects()
    recalc_wake_timer_state()
    ensure_challenge_feature()
    if game.get("motivation_unlocked", False):
        clamp_motivation()
    check_challenges("load")
    if not payload:
        save_game()
    return state


def format_duration(seconds):
    seconds = int(seconds or 0)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}h {minutes:02d}m"


def estimate_progress(snapshot):
    if not snapshot:
        return 0
    layer_max = max(1, len(LAYER_FLOW) - 1)
    layer_score = min(snapshot.get("layer", 0), layer_max) / layer_max
    money = max(snapshot.get("money_since_reset", 0), snapshot.get("money", 0))
    wealth_score = min(1.0, math.log10(money + 1) / 8.0)
    progress = (layer_score * 0.7 + wealth_score * 0.3) * 100
    return int(max(0, min(100, round(progress))))


def build_progress_bar(pct, width=16):
    pct = max(0, min(100, pct))
    filled = int((pct / 100) * width)
    return f"[{'#' * filled}{'-' * (width - filled)}] {pct:3d}%"


def breach_key_available():
    return bool(game.get("breach_key_obtained", False))


def breach_door_is_open():
    return bool(game.get("breach_door_open", False))


def open_breach_door():
    if breach_door_is_open():
        return False
    game["breach_door_open"] = True
    game["breach_key_obtained"] = True
    game["rpg_unlocked"] = True
    game["breach_door_manifested"] = True
    lines = [
        "Breach door unlocked.",
        "Use X at the desk to enter the escape room.",
        "Portal stays open permanently.",
    ]
    tmp = boxed_lines(lines, title=" Breach Door ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(1.3)
    set_settings_notice("Breach door remains open.")
    return True

def announce_breach_door_manifestation():
    if game.get("breach_door_manifested", False):
        return
    game["breach_door_manifested"] = True
    lines = [
        "Breach key synced with the desk UI.",
        "Look to the lower-right panel for the entry point.",
        "Press X near it to enter.",
    ]
    tmp = boxed_lines(lines, title=" Breach Key ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(1.2)
    set_settings_notice("Breach door visible on the desk.")


def perform_breach_unlock_sequence():
    for art in BREACH_DOOR_UNLOCK_FRAMES:
        term_w, term_h = get_term_size()
        box_w = max(config.MIN_BOX_WIDTH, term_w - config.BOX_MARGIN * 2)
        inner_w = box_w - 2
        centered = [ansi_center(line, inner_w) for line in art]
        target_block = max(len(centered), max(6, term_h // 3))
        extra_lines = max(0, target_block - len(centered))
        top_pad = extra_lines // 2
        bottom_pad = extra_lines - top_pad
        payload = ["Synchronizing breach lock...", ""]
        payload.extend(["" for _ in range(top_pad)])
        payload.extend(centered)
        payload.extend(["" for _ in range(bottom_pad)])
        tmp = boxed_lines(payload, title=" Breach Door ", pad_top=1, pad_bottom=1)
        render_frame(tmp)
        time.sleep(0.1)
    open_breach_door()


def set_settings_notice(message, duration=2.5):
    game["settings_notice"] = escape_text(message)
    game["settings_notice_until"] = time.time() + duration


def _easter_egg_flags():
    return game.setdefault("easter_egg_flags", {})


def trigger_easter_egg(key, message, duration=3.0, cooldown=EASTER_EGG_DEFAULT_COOLDOWN):
    if not key or not message:
        return False
    flags = _easter_egg_flags()
    now = time.time()
    last = float(flags.get(key, 0.0) or 0.0)
    if last and now - last < cooldown:
        return False
    flags[key] = now
    set_settings_notice(message, duration=duration)
    return True


def track_manual_work_spam(manual):
    if not manual:
        return
    now = time.time()
    last = float(game.get("manual_work_last_time", 0.0) or 0.0)
    counter = int(game.get("manual_work_burst", 0))
    if last and now - last <= MANUAL_WORK_SPAM_WINDOW:
        counter += 1
    else:
        counter = max(0, counter - 1)
    game["manual_work_last_time"] = now
    game["manual_work_burst"] = counter
    if counter >= MANUAL_WORK_SPAM_THRESHOLD and "hold_w_hint" not in SESSION_HINT_FLAGS:
        SESSION_HINT_FLAGS.add("hold_w_hint")
        set_settings_notice("u can hold w yk that?", duration=4.0)
        game["manual_work_burst"] = 0


def check_session_easter_eggs():
    play_time = float(game.get("play_time", 0.0) or 0.0)
    if play_time >= LONG_SESSION_EGG_SECONDS:
        trigger_easter_egg(
            "long_session",
            "Console whispers: take a stretch break.",
            duration=4.0,
            cooldown=999999.0,
        )
    hour = time.localtime().tm_hour
    if 2 <= hour <= 4:
        trigger_easter_egg(
            "graveyard_shift",
            "Graveyard shift acknowledged. Diverter glows pale blue.",
            duration=4.0,
            cooldown=3600.0,
        )


def check_collapse_easter_eggs():
    resets = int(game.get("stability_resets", 0) or 0)
    if resets >= 3:
        trigger_easter_egg(
            "stability_hat_trick",
            "Stabilizer logs: triple collapse achieved.",
            duration=3.5,
            cooldown=999999.0,
        )


def enable_auto_work(show_notice=True):
    if automation_online():
        return False
    game["auto_work_unlocked"] = True
    if show_notice:
        set_settings_notice("Automation cycles synchronized.", duration=3.5)
    attempt_reveal("ui_auto_prompt")
    return True


def enable_auto_buyers(show_notice=True):
    if game.get("auto_buyer_unlocked", False):
        return False
    game["auto_buyer_unlocked"] = True
    if show_notice:
        set_settings_notice("Auto-buyers linked to the lab.", duration=3.5)
    attempt_reveal("ui_auto_prompt")
    return True


def _scientific_options():
    raw = getattr(config, "SCIENTIFIC_THRESHOLD_OPTIONS", SCIENTIFIC_THRESHOLD_OPTIONS)
    try:
        options = sorted({int(x) for x in raw if int(x) >= 3})
    except Exception:
        options = []
    return options or [SCIENTIFIC_THRESHOLD_DEFAULT]


def sync_scientific_threshold(exp=None):
    options = _scientific_options()
    if exp is None:
        exp = game.get("scientific_threshold_exp", options[-1])
    try:
        exp = int(exp)
    except Exception:
        exp = options[-1]
    if exp not in options:
        exp = options[-1]
    game["scientific_threshold_exp"] = exp
    config.SCIENTIFIC_THRESHOLD_EXPONENT = exp
    return exp


def cycle_scientific_threshold():
    options = _scientific_options()
    current = sync_scientific_threshold()
    idx = options.index(current)
    nxt = options[(idx + 1) % len(options)]
    return sync_scientific_threshold(nxt)


def scientific_threshold_label():
    exp = sync_scientific_threshold()
    return f"1e{exp}"


def _quick_travel_targets():
    room_ready = breach_door_is_open()
    targets = [
        {
            "id": "work",
            "label": "Desk",
            "screen": "work",
            "available": True,
            "hint": "Return to the main workstation.",
        }
    ]
    targets.append(
        {
            "id": "rpg",
            "label": "Room",
            "screen": "rpg",
            "available": room_ready,
            "hint": "Unlock the breach door first." if not room_ready else "Explore the room view.",
        }
    )
    return targets


def current_quick_travel_target():
    target = game.get("quick_travel_target", "work") or "work"
    available_ids = {entry["id"] for entry in _quick_travel_targets() if entry["available"]}
    if target not in available_ids:
        target = "work"
        game["quick_travel_target"] = target
    return target


def describe_quick_travel_target(target_id):
    for entry in _quick_travel_targets():
        if entry["id"] != target_id:
            continue
        label = entry["label"]
        if not entry["available"]:
            label += " (locked)"
        return label
    return "Desk"


def open_quick_travel_menu():
    global KEY_PRESSED
    selected = 0
    active = current_quick_travel_target()
    for idx, entry in enumerate(_quick_travel_targets()):
        if entry["id"] == active:
            selected = idx
            break
    while True:
        targets = _quick_travel_targets()
        if not targets:
            return None
        if selected >= len(targets):
            selected = len(targets) - 1
        lines = ["Configure where Quick Travel sends you.", ""]
        for idx, entry in enumerate(targets):
            marker = f"{Fore.CYAN}»{Style.RESET_ALL}" if idx == selected else " "
            label = entry["label"]
            if not entry["available"]:
                label += f" {Style.DIM}(locked){Style.RESET_ALL}"
            lines.append(f"{marker} [{idx + 1}] {label}")
            if entry.get("hint"):
                hint_style = Style.DIM if not entry["available"] else ""
                hint = entry["hint"]
                lines.append(f"    {hint_style}{hint}{Style.RESET_ALL}")
        lines += [
            "",
            f"Use W/S or digits to select. Enter confirms, B cancels.",
        ]
        box = boxed_lines(lines, title=" Quick Travel ", pad_top=1, pad_bottom=1)
        render_frame(box)
        time.sleep(0.05)
        if not KEY_PRESSED:
            continue
        k = KEY_PRESSED.lower() if isinstance(KEY_PRESSED, str) else KEY_PRESSED
        KEY_PRESSED = None
        if isinstance(k, str) and k.startswith("\x1b"):
            if k == "\x1b[A":
                k = "w"
            elif k == "\x1b[B":
                k = "s"
            else:
                continue
        if k == "b":
            return None
        if k in {"w", "s"}:
            delta = -1 if k == "w" else 1
            selected = (selected + delta) % len(targets)
            continue
        if isinstance(k, str) and k.isdigit():
            idx = int(k) - 1
            if 0 <= idx < len(targets):
                selected = idx
            continue
        if k == "enter":
            choice = targets[selected]
            if not choice["available"]:
                continue
            return choice["id"]
def record_manual_press(now):
    prev = float(game.get("last_manual_press_ts", 0.0))
    gap = now - prev if prev else None
    counter = int(game.get("manual_tap_counter", 0))
    if gap is None or gap > MANUAL_TAP_GAP:
        counter = min(9999, counter + 1)
    else:
        counter = max(0, counter - 1)
    game["manual_tap_counter"] = counter
    game["last_manual_press_ts"] = now
    if not game.get("hold_tip_shown", False) and counter >= MANUAL_TAP_THRESHOLD:
        set_settings_notice("Tip: Hold W to work continuously.")
        game["hold_tip_shown"] = True


def get_settings_menu_options():
    options = []
    target = describe_quick_travel_target(current_quick_travel_target())
    quick_text = f"[1] Quick travel target: {target}"
    options.append({"id": "quick_travel", "label": quick_text, "hotkey": "1", "spacer_after": True})

    steam_flag = "OFF" if game.get("settings_disable_steam", False) else "ON"
    options.append({
        "id": "steam",
        "label": f"[2] Coffee steam visuals: {steam_flag}",
        "hotkey": "2",
    })
    signal_flag = "ON" if game.get("settings_show_signal_debug", False) else "OFF"
    options.append({
        "id": "signal_debug",
        "label": f"[3] Show signal multiplier beside gain: {signal_flag}",
        "hotkey": "3",
    })
    options.append({
        "id": "recenter",
        "label": "[4] Recenter desk view",
        "hotkey": "4",
    })
    options.append({
        "id": "scientific",
        "label": f"[5] Scientific cutoff: {scientific_threshold_label()}",
        "hotkey": "5",
    })
    options.append({
        "id": "back",
        "label": "[B] Return to desk",
        "hotkey": "b",
    })
    return options


def settings_menu_move_cursor(delta):
    options = get_settings_menu_options()
    if not options:
        game["settings_cursor"] = 0
        return
    cursor = int(game.get("settings_cursor", 0))
    cursor = max(0, min(len(options) - 1, cursor + delta))
    game["settings_cursor"] = cursor


def activate_settings_option(option_id):
    global view_offset_x, view_offset_y
    if option_id == "back":
        set_settings_notice("Back to the desk.")
        return "back"
    if option_id == "quick_travel":
        destination = open_quick_travel_menu()
        if destination:
            game["quick_travel_target"] = destination
            label = describe_quick_travel_target(destination)
            set_settings_notice(f"Quick travel set to {label}.")
            return ("switch", destination)
        return "stay"
    if option_id == "steam":
        game["settings_disable_steam"] = not game.get("settings_disable_steam", False)
        state = "disabled" if game["settings_disable_steam"] else "enabled"
        set_settings_notice(f"Coffee steam {state}.")
        return "refresh"
    if option_id == "signal_debug":
        game["settings_show_signal_debug"] = not game.get("settings_show_signal_debug", False)
        state = "visible" if game["settings_show_signal_debug"] else "hidden"
        set_settings_notice(f"Signal multiplier {state} next to gain.")
        return "refresh"
    if option_id == "scientific":
        new_exp = cycle_scientific_threshold()
        set_settings_notice(f"Scientific notation after 1e{new_exp}.")
        return "refresh"
    if option_id == "recenter":
        view_offset_x = 0
        view_offset_y = 0
        set_settings_notice("Desk camera recentered.")
        return "refresh"
    return None


def select_settings_option(option_id, options=None):
    options = options or get_settings_menu_options()
    for idx, entry in enumerate(options):
        if entry.get("id") == option_id:
            game["settings_cursor"] = idx
            break


def build_settings_lines():
    options = get_settings_menu_options()
    cursor = int(game.get("settings_cursor", 0))
    if options:
        cursor = max(0, min(len(options) - 1, cursor))
    else:
        cursor = 0
    game["settings_cursor"] = cursor

    def render_option(text, selected):
        if selected:
            return f"{Back.WHITE}{Fore.BLACK} {text} {Style.RESET_ALL}"
        return f"  {text}"

    lines = [f"{Fore.CYAN}Settings Console{Style.RESET_ALL}", ""]
    for idx, option in enumerate(options):
        lines.append(render_option(option["label"], idx == cursor))
        if option.get("spacer_after"):
            lines.append("")
    lines.append(
        f"{Fore.YELLOW}Use Up/Down to move, Enter to activate, B or S to return. , and . switch views.{Style.RESET_ALL}"
    )
    notice = game.get("settings_notice", "")
    if notice and time.time() < game.get("settings_notice_until", 0.0):
        lines += ["", f"{Fore.YELLOW}{notice}{Style.RESET_ALL}"]
    return lines


def handle_settings_menu_input(k):
    if not k:
        return None
    options = get_settings_menu_options()
    if k == "enter":
        if not options:
            return None
        cursor = max(0, min(len(options) - 1, int(game.get("settings_cursor", 0))))
        option_id = options[cursor]["id"]
        return activate_settings_option(option_id)

    key_map = {
        "1": "quick_travel",
        "2": "steam",
        "3": "signal_debug",
        "4": "recenter",
        "5": "scientific",
        "b": "back",
    }
    if k in ("b", "s"):
        select_settings_option("back", options)
        return activate_settings_option("back")
    if k in key_map:
        option_id = key_map[k]
        select_settings_option(option_id, options)
        return activate_settings_option(option_id)
    return None


def load_slot_payload(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def collect_slot_summaries():
    summaries = []
    legacy_exists = os.path.exists(LEGACY_SAVE_PATH)
    for idx in range(SAVE_SLOT_COUNT):
        target_path = slot_save_path(idx)
        data = None
        source_path = None
        legacy = False
        if os.path.exists(target_path):
            data = load_slot_payload(target_path)
            source_path = target_path
        elif idx == 0 and legacy_exists:
            data = load_slot_payload(LEGACY_SAVE_PATH)
            source_path = LEGACY_SAVE_PATH
            legacy = data is not None
        layer_idx = data.get("layer", 0) if data else 0
        layer_info = LAYER_BY_ID.get(layer_idx, {})
        layer_label = layer_info.get("name", f"Layer {layer_idx}")
        border_id = layer_info.get("border_id", layer_idx)
        if data and data.get("mirror_reality_active"):
            border_id = MIRROR_BORDER_ID
        progress_pct = estimate_progress(data)
        last_ts = data.get("last_save_timestamp") if data else None
        last_seen = (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(last_ts))
            if last_ts
            else "--"
        )
        play_time = format_duration(data.get("play_time", 0)) if data else "00h 00m"
        money_label = format_currency(data.get("money", 0)) if data else "0"
        summaries.append(
            {
                "index": idx,
                "display_index": idx + 1,
                "data": data,
                "exists": data is not None,
                "layer_label": layer_label,
                "progress": progress_pct,
                "last_seen": last_seen,
                "play_time": play_time,
                "money": money_label,
                "target_path": target_path,
                "source_path": source_path,
                "legacy": legacy,
                "status": "Legacy" if legacy else ("Active" if data else "Empty"),
                "border_id": border_id,
            }
        )
    return summaries


def build_slot_card(summary, width, height, highlight=False, phase=0):
    layer_border_id = summary.get("border_id", 0)
    style = BORDERS.get(layer_border_id, list(BORDERS.values())[0])
    inner_w = width - 2
    glow_seq = ["·", "*", "o", "+"]
    glow_char = glow_seq[phase % len(glow_seq)] if highlight else style["h"]

    def frame_line(text=""):
        raw = text[:inner_w]
        padded = raw.center(inner_w)
        return f"{style['v']}{padded}{style['v']}"

    lines = []
    top = style["tl"] + glow_char * inner_w + style["tr"]
    lines.append(top)
    header = f"Slot {summary['display_index']}"
    lines.append(frame_line(header))
    if summary["exists"]:
        lines.append(frame_line(summary["layer_label"]))
        bar_width = max(6, inner_w - 2)
        lines.append(frame_line(build_progress_bar(summary["progress"], bar_width)))
        lines.append(frame_line(f"Time {summary['play_time']}"))
        lines.append(frame_line(f"Funds {summary['money']}"))
        lines.append(frame_line(f"Last {summary['last_seen']}"))
        footer_text = "(legacy copy)" if summary["legacy"] else summary["status"]
        lines.append(frame_line(footer_text))
    else:
        lines.append(frame_line("Empty"))
        lines.append(frame_line(""))
        lines.append(frame_line("Ready"))
        lines.append(frame_line(""))
        lines.append(frame_line(""))
        lines.append(frame_line(""))
    target_inner = max(1, height - 1)
    if len(lines) > target_inner:
        lines = lines[:target_inner]
    elif len(lines) < target_inner:
        while len(lines) < target_inner:
            lines.append(frame_line(""))
    accent = glow_char * inner_w if highlight else style["h"] * inner_w
    bottom = style["bl"] + accent + style["br"]
    lines.append(bottom)
    return lines


def render_slot_menu(summaries, highlight_idx=None, phase=0):
    term_w, term_h = get_term_size()
    cols = 2
    rows = 2
    card_w = max(30, term_w // cols - 6)
    card_h = max(12, (term_h - 8) // rows)
    cards = [
        build_slot_card(s, card_w, card_h, highlight=(highlight_idx == i), phase=phase)
        for i, s in enumerate(summaries)
    ]
    grid = []
    for r in range(rows):
        row_cards = cards[r * cols : (r + 1) * cols]
        if not row_cards:
            continue
        for line_idx in range(card_h):
            parts = [card[line_idx] if line_idx < len(card) else " " * card_w for card in row_cards]
            grid.append("   ".join(parts))
        grid.append("")
    
                                                                                                
    buffer = []
    buffer.append("\033[H")                           
    
    title = "Select Save File"
    buffer.append("\033[2K\n")
    buffer.append("\033[2K" + title.center(term_w) + "\n")
    buffer.append("\033[2K\n")
    for line in grid:
        buffer.append("\033[2K" + line.center(term_w) + "\n")
    buffer.append("\033[2K\n")
    buffer.append("\033[2K" + "Use arrows/WASD to move, Enter to load, Shift+D to delete, Q to quit.".center(term_w) + "\n")
    buffer.append("\033[J")                                  
    
    sys.stdout.write("".join(buffer))
    sys.stdout.flush()


def play_slot_select_animation(selected_idx, frames=6, delay=0.08):
    summaries = collect_slot_summaries()
    for phase in range(frames):
        render_slot_menu(summaries, highlight_idx=selected_idx, phase=phase)
        time.sleep(delay)


def finalize_slot_choice(selected):
    global ACTIVE_SLOT_INDEX
    summaries = collect_slot_summaries()
    summary = summaries[selected]
    if summary["legacy"] and summary.get("source_path"):
        shutil.copy2(summary["source_path"], summary["target_path"])
    elif not summary["exists"]:
        template_path = os.path.join(DATA_DIR, "save_slot_template.json")
        if os.path.exists(template_path):
            shutil.copy2(template_path, summary["target_path"])
        else:
            with open(summary["target_path"], "w", encoding="utf-8") as fh:
                json.dump(default_game_state(), fh)
    ACTIVE_SLOT_INDEX = selected
    clear_screen()


def choose_save_slot_windows():
    while msvcrt.kbhit():
        msvcrt.getwch()

    selected = 0
    phase = 0
    summaries = collect_slot_summaries()
    while True:
        render_slot_menu(summaries, highlight_idx=selected, phase=phase)
        phase = (phase + 1) % 8
        frame_end = time.time() + 0.08
        while time.time() < frame_end:
            if not msvcrt.kbhit():
                time.sleep(0.01)
                continue
            ch = msvcrt.getwch()
            if not ch:
                break
            if ch in ("\x00", "\xe0"):
                code = msvcrt.getwch()
                if code == "H":
                    selected = (selected - 2) % SAVE_SLOT_COUNT
                elif code == "P":
                    selected = (selected + 2) % SAVE_SLOT_COUNT
                elif code == "M":
                    selected = (selected + 1) % SAVE_SLOT_COUNT
                elif code == "K":
                    selected = (selected - 1) % SAVE_SLOT_COUNT
                break
            if ch == "D":
                confirm = input(f"Erase slot {selected + 1}? Type YES to confirm: ")
                if confirm.strip().lower() == "yes":
                    path = slot_save_path(selected)
                    if os.path.exists(path):
                        os.remove(path)
                    if selected == 0 and os.path.exists(LEGACY_SAVE_PATH):
                        os.remove(LEGACY_SAVE_PATH)
                    summaries = collect_slot_summaries()
                break
            lower = ch.lower()
            if lower == "q":
                clear_screen()
                print("Exiting (User pressed Q). Press Enter to close.")
                input()
                sys.exit(0)
            if lower == "w":
                selected = (selected - 2) % SAVE_SLOT_COUNT
                continue
            if lower == "s":
                selected = (selected + 2) % SAVE_SLOT_COUNT
                continue
            if lower == "d":
                selected = (selected + 1) % SAVE_SLOT_COUNT
                continue
            if lower == "a":
                selected = (selected - 1) % SAVE_SLOT_COUNT
                continue
            if ch in ("\r", "\n"):
                play_slot_select_animation(selected)
                finalize_slot_choice(selected)
                return
            if ch.isdigit():
                idx = int(ch) - 1
                if 0 <= idx < SAVE_SLOT_COUNT:
                    play_slot_select_animation(idx)
                    finalize_slot_choice(idx)
                    return
            break


def choose_save_slot():
    global ACTIVE_SLOT_INDEX
    if msvcrt is not None and os.name == "nt":
        choose_save_slot_windows()
        return
    selected = 0
    phase = 0
    try:
        import termios, tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)

        try:
            while True:
                summaries = collect_slot_summaries()
                render_slot_menu(summaries, highlight_idx=selected, phase=phase)
                phase = (phase + 1) % 8
                frame_end = time.time() + 0.08
                ch = None
                while time.time() < frame_end:
                    ready, _, _ = select.select([sys.stdin], [], [], 0)
                    if ready:
                        ch = sys.stdin.read(1)
                        break
                    time.sleep(0.01)
                if not ch:
                    continue
                if ch == "\x1b":
                    seq = ch
                    while True:
                        ready, _, _ = select.select([sys.stdin], [], [], 0.002)
                        if not ready:
                            break
                        nxt = sys.stdin.read(1)
                        if not nxt:
                            break
                        seq += nxt
                        if nxt.isalpha():
                            break
                    if seq in ("\x1b[A", "\x1bOA"):
                        selected = (selected - 2) % SAVE_SLOT_COUNT
                        continue
                    if seq in ("\x1b[B", "\x1bOB"):
                        selected = (selected + 2) % SAVE_SLOT_COUNT
                        continue
                    if seq in ("\x1b[C", "\x1bOC"):
                        selected = (selected + 1) % SAVE_SLOT_COUNT
                        continue
                    if seq in ("\x1b[D", "\x1bOD"):
                        selected = (selected - 1) % SAVE_SLOT_COUNT
                        continue
                    continue
                if ch == "D":
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    try:
                        confirm = input(f"Erase slot {selected + 1}? Type YES to confirm: ")
                    finally:
                        tty.setcbreak(fd)
                    if confirm.strip().lower() == "yes":
                        path = slot_save_path(selected)
                        if os.path.exists(path):
                            os.remove(path)
                        if selected == 0 and os.path.exists(LEGACY_SAVE_PATH):
                            os.remove(LEGACY_SAVE_PATH)
                    continue
                lower = ch.lower()
                if lower == "w":
                    selected = (selected - 2) % SAVE_SLOT_COUNT
                    continue
                if lower == "s":
                    selected = (selected + 2) % SAVE_SLOT_COUNT
                    continue
                if lower == "d":
                    selected = (selected + 1) % SAVE_SLOT_COUNT
                    continue
                if lower == "a":
                    selected = (selected - 1) % SAVE_SLOT_COUNT
                    continue
                if lower == "q":
                    clear_screen()
                    print("Exiting.")
                    sys.exit(0)
                if ch in ("\r", "\n"):
                    play_slot_select_animation(selected)
                    finalize_slot_choice(selected)
                    return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
                                                          
        while True:
            summaries = collect_slot_summaries()
            render_slot_menu(summaries, highlight_idx=selected)
            raw_choice = input(">> ").strip()
            lower_choice = raw_choice.lower()
            if lower_choice == "q":
                sys.exit(0)
            if raw_choice == "D":
                confirm = input(f"Erase slot {selected + 1}? Type YES to confirm: ")
                if confirm.strip().lower() == "yes":
                    path = slot_save_path(selected)
                    if os.path.exists(path):
                        os.remove(path)
                    if selected == 0 and os.path.exists(LEGACY_SAVE_PATH):
                        os.remove(LEGACY_SAVE_PATH)
                continue
            if lower_choice in {"w", "a", "s", "d"}:
                if lower_choice == "w":
                    selected = (selected - 2) % SAVE_SLOT_COUNT
                elif lower_choice == "s":
                    selected = (selected + 2) % SAVE_SLOT_COUNT
                elif lower_choice == "d":
                    selected = (selected + 1) % SAVE_SLOT_COUNT
                elif lower_choice == "a":
                    selected = (selected - 1) % SAVE_SLOT_COUNT
                continue
            if lower_choice.isdigit():
                idx = int(lower_choice) - 1
                if 0 <= idx < SAVE_SLOT_COUNT:
                    finalize_slot_choice(idx)
                    return


def refresh_knowledge_flags():
    updated = False
    if game.get("mystery_revealed"):
        updated |= attempt_reveal("layer_wake")
        updated |= attempt_reveal("ui_options_hint")
        updated |= attempt_reveal("currency_wake")
        updated |= attempt_reveal("ui_currency_clear")
        updated |= attempt_reveal("ui_upgrade_catalogue")
        updated |= attempt_reveal("escape_window")
    if game.get("auto_work_unlocked"):
        updated |= attempt_reveal("ui_auto_prompt")
    if game.get("stability_resets", 0) >= 1:
        updated |= attempt_reveal("escape_route")
    if game.get("concept_resets", 0) >= 1:
        updated |= attempt_reveal("escape_signal")
    return updated


def ansi_center(text, width):
    vis = visible_len(text)
    pad_left = max(0, (width - vis) // 2)
    pad_right = max(0, width - vis - pad_left)
    return " " * pad_left + text + " " * pad_right


def visible_len(s):
    clean = ANSI_ESCAPE.sub("", s)
    if _wcwidth:
        return sum(max(_wcwidth(c), 0) for c in clean)
    return len(clean)


def ansi_visible_slice(s: str, start: int, width: int) -> str:
    if width <= 0:
        return ""
    out = []
    esc_buf = []
    vis = 0
    end = start + width
    i = 0
    had_esc = False
    while i < len(s):
        ch = s[i]
        if ch == "\x1b":
            m = ANSI_ESCAPE.match(s, i)
            if m:
                seq = m.group(0)
                esc_buf.append(seq)
                had_esc = True
                i += len(seq)
                continue
            else:
                i += 1
                continue
        if vis >= start and vis < end:
            if esc_buf:
                out.extend(esc_buf)
                esc_buf = []
            out.append(ch)
        vis += 1
        i += 1
        if vis >= end:
            break
    result = "".join(out)
    if had_esc and result and RESET_SEQ and RESET_SEQ not in result:
        result += RESET_SEQ
    return result


def wrap_visible_text(text: str, width: int) -> list[str]:
    if width <= 0:
        return [text or ""]
    if text is None:
        return [""]
    segments = []
    buffer = []
    buffer_width = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\x1b":
            match = ANSI_ESCAPE.match(text, i)
            if match:
                seq = match.group(0)
                buffer.append(seq)
                i += len(seq)
                continue
        if ch == "\n":
            segments.append("".join(buffer))
            buffer = []
            buffer_width = 0
            i += 1
            continue
        char_width = 1
        if _wcwidth:
            w = _wcwidth(ch)
            if w is not None:
                char_width = max(w, 0)
        if buffer_width and buffer_width + char_width > width:
            segments.append("".join(buffer))
            buffer = []
            buffer_width = 0
            continue
        buffer.append(ch)
        buffer_width += char_width
        if buffer_width >= width:
            segments.append("".join(buffer))
            buffer = []
            buffer_width = 0
        i += 1
    if buffer or not segments:
        segments.append("".join(buffer))
    return segments


def pad_visible_line(text, width):
    if width <= 0:
        return ""
    snippet = ansi_visible_slice(text or "", 0, width)
    vis = visible_len(snippet)
    if vis < width:
        snippet += " " * (width - vis)
    return snippet


def get_term_size():
    try:
        s = shutil.get_terminal_size(fallback=(80, 24))
        return s.columns, s.lines
    except:
        return 80, 24


def clear_screen():
    if os.name == "nt":
        os.system("cls")
        sys.stdout.flush()
    else:
        sys.stdout.write("\033[H\033[J")
        sys.stdout.flush()


def run_terminal_scale_calculator():
    global _TERMINAL_SCALE_CONFIRMED
    if _TERMINAL_SCALE_CONFIRMED:
        return
    step_scale = 1.08
    while True:
        cols, rows = get_term_size()
        needed_cols = max(0, TERMINAL_TARGET_COLS - cols)
        needed_rows = max(0, TERMINAL_TARGET_ROWS - rows)
        ratio_cols = TERMINAL_TARGET_COLS / max(cols, 1)
        ratio_rows = TERMINAL_TARGET_ROWS / max(rows, 1)
        ratio_needed = max(ratio_cols, ratio_rows)
        est_steps = 0
        if ratio_needed > 1:
            est_steps = max(1, int(math.ceil(math.log(ratio_needed, step_scale))))
        clear_screen()
        if est_steps > 0:
            print(
                f"Zoom out ~{est_steps} time(s) with Cmd+- (macOS) or Ctrl+- (Windows/Linux). If you are not fullscreened, press f11 then recheck!!"
            )
            print("Press Enter to re-check or type READY when finished.")
        else:
            print("Looks good already—type READY to continue or Enter to re-check.")
        response = input("> ").strip().lower()
        if response == "ready":
            _TERMINAL_SCALE_CONFIRMED = True
            clear_screen()
            break


def ensure_terminal_capacity(min_cols=None, min_rows=None, reason=None):
    min_cols = max(1, int(min_cols or TERMINAL_TARGET_COLS))
    min_rows = max(1, int(min_rows or TERMINAL_TARGET_ROWS))
    while True:
        cols, rows = get_term_size()
        if cols >= min_cols and rows >= min_rows:
            return True
        clear_screen()
        print(
            f"This view needs at least {min_cols} columns × {min_rows} rows. Current size is {cols} × {rows}."
        )
        if reason:
            print(f"Reason: {reason}.")
        print("Zoom out (Cmd+- / Ctrl+-) or resize your terminal, then press Enter to re-check.")
        input("> ")

def render_frame(lines):
    global last_render
    term_w, term_h = get_term_size()
    prepared = [pad_visible_line(line, term_w) for line in lines]
    while len(prepared) < term_h:
        prepared.append(" " * term_w)
    frame = "\033[H" + "\n".join(prepared[:term_h])
    sys.stdout.write(frame)
    sys.stdout.flush()
    last_render = ""


# --- Animated Upgrade Art Helpers ---
from config import UPGRADE_ANIM_FRAMES

def animate_upgrade_art(upgrade_id, duration=1.0, frame_delay=0.18):
    """Display animated ASCII art for a given upgrade."""
    frame_keys = UPGRADE_ANIM_FRAMES.get(upgrade_id)
    if not frame_keys:
        return
    start = time.time()
    idx = 0
    while time.time() - start < duration:
        key = frame_keys[idx % len(frame_keys)]
        art = UPGRADE_ANIM_ART_FRAMES.get(key)
        if not art:
            break
        box = boxed_lines(art, title=f" {upgrade_id.title()} Upgrade ", pad_top=1, pad_bottom=1)
        render_frame(box)
        time.sleep(frame_delay)
        idx += 1

def maybe_animate_upgrade(upgrade_id):
    """Trigger an upgrade animation if configured."""
    try:
        if upgrade_id in UPGRADE_ANIM_FRAMES:
            animate_upgrade_art(upgrade_id)
    except Exception:
        # Fail silently; animation is cosmetic
        pass


def get_inspire_info(upg_id):
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return True, u.get("level", 1)
        elif isinstance(u, str) and u == upg_id:
            return True, 1
    return False, 0


def get_concept_info(upg_id):
    for u in game.get("concept_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return True, u.get("level", 1)
        elif isinstance(u, str) and u == upg_id:
            return True, 1
    return False, 0


def get_automation_info(upg_id):
    for u in game.get("automation_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return True, u.get("level", 1)
        elif isinstance(u, str) and u == upg_id:
            return True, 1
    return False, 0


def wrap_ui_text(text, width=None, reserved=0):
    term_w, _ = get_term_size()
    box_w = max(config.MIN_BOX_WIDTH, term_w - config.BOX_MARGIN * 2)
    inner_w = box_w - 2
    if width is None:
        panel_width = max(int(inner_w * 0.25) - 6, 20)
    else:
        panel_width = max(10, int(width))
    usable = max(8, panel_width - int(reserved))
    clean = ANSI_ESCAPE.sub("", text)
    return textwrap.wrap(clean, width=usable)


def tree_catalogue_meta(upgrades):
    if upgrades is INSPIRE_UPGRADES:
        layer_key = "corridor"
        return {
            "pool_name": layer_name(layer_key),
            "pool_currency": layer_currency_name(layer_key),
            "currency_suffix": layer_currency_suffix(layer_key),
            "holdings_key": "inspiration",
            "applied_key": "inspiration_upgrades",
        }
    if upgrades is AUTOMATION_UPGRADES:
        return {
            "pool_name": "Stabilizer Lab",
            "pool_currency": AUTOMATION_CURRENCY_NAME,
            "currency_suffix": AUTOMATION_CURRENCY_SUFFIX,
            "holdings_key": "automation_currency",
            "applied_key": "automation_upgrades",
        }
    layer_key = "archive"
    return {
        "pool_name": layer_name(layer_key),
        "pool_currency": layer_currency_name(layer_key),
        "currency_suffix": layer_currency_suffix(layer_key),
        "holdings_key": "concepts",
        "applied_key": "concept_upgrades",
    }


def build_tree_lines(upgrades, get_info_fn, page_key):
    term_w, term_h = get_term_size()
    max_lines = term_h // 2 - 6
    meta = tree_catalogue_meta(upgrades)
    suffix_raw = meta.get("currency_suffix")
    suffix = f" {suffix_raw}" if suffix_raw else ""
    pool_currency = meta.get("pool_currency", "")
    holdings_key = meta.get("holdings_key", "concepts")
                                                                                          
    desc_width = max(int(term_w * 0.25) - 6, 18)
    pages, current, used = [], [], 0
    for i, u in enumerate(upgrades, start=1):
        owned, level = get_info_fn(u["id"])
        max_level = u.get("max_level", 1)
        cost = get_tree_cost(u, current_level=level)
        base_value = u.get("base_value", u.get("value", 1.0))
        value_mult = u.get("value_mult", 1.0)
        total_mult = (
            base_value * (value_mult ** max(0, (level - 1)))
            if level > 0
            else base_value
        )
        holdings = game.get(holdings_key, 0)
        can_afford = holdings >= cost and level < max_level
        status_color = (
            Fore.GREEN
            if level >= max_level
            else (Fore.CYAN if can_afford else Fore.RED)
        )
        lvl_text = f"Lv {min(level, max_level)}/{max_level}"
        lines = [
            f"{status_color}{i}. {u['name']}{Style.RESET_ALL}  {Fore.YELLOW}{lvl_text}{Style.RESET_ALL}"
        ]
        if level >= max_level:
            lines.append(
                f"    {Fore.GREEN}MAXED — permanent bonus locked{Style.RESET_ALL}"
            )
        else:
            lines.append(
                f"    Cost: {Fore.LIGHTYELLOW_EX}{format_number(cost)}{suffix}{Style.RESET_ALL}"
            )
            lines.append(
                f"    You:  {Fore.LIGHTYELLOW_EX}{format_number(holdings)}{suffix}{Style.RESET_ALL}"
                f"  ({pool_currency})"
            )
        if u.get("desc"):
            desc_text = f"→ {u['desc']}"
            if level > 0 and u["type"] not in (
                "unlock_motivation",
                "timeflow_bonus",
                "motivation_cap",
                "motivation_strength",
            ):
                desc_text += f" (x{total_mult:.2f})"
            wrapped = wrap_ui_text(desc_text, width=desc_width, reserved=4)
            lines += [f"    {Fore.LIGHTBLACK_EX}{w}{Style.RESET_ALL}" for w in wrapped]
        lines.append(
            f"    {Fore.LIGHTBLACK_EX}{'-' * max(24, desc_width // 2)}{Style.RESET_ALL}"
        )
        if used + len(lines) > max_lines and current:
            pages.append(current)
            current, used = [], 0
        current += lines
        used += len(lines)
    if current:
        pages.append(current)
    current_page = game.setdefault(page_key, 0)
    max_idx = max(0, len(pages) - 1)
    current_page = max(0, min(current_page, max_idx))
    game[page_key] = current_page
    total_pages = max(1, len(pages))
    game[f"{page_key}_pages"] = total_pages
    visible_lines = pages[current_page] if pages else ["(no upgrades)"]
    footer = f"Page {current_page+1}/{total_pages}  (z, x to switch)"
    return visible_lines, footer, len(pages)


def signal_exchange_rate():
    try:
        rate = int(AUTOMATION_EXCHANGE_RATE)
    except Exception:
        rate = 0
    return max(1, rate)


def calculate_signal_exchange_capacity():
    rate = signal_exchange_rate()
    funds = max(0.0, float(game.get("money", 0.0) or 0.0))
    max_bits = int(funds // rate)
    return rate, funds, max_bits


def build_signal_exchange_panel():
    rate, funds, max_bits = calculate_signal_exchange_capacity()
    potential = format_number(max_bits)
    panel = [
        f"{Fore.LIGHTMAGENTA_EX}Signal Exchange{Style.RESET_ALL}",
        f"Rate: {format_currency(rate)} -> 1 {AUTOMATION_CURRENCY_NAME}",
        f"Funds: {format_currency(funds)}  Potential: {potential} {AUTOMATION_CURRENCY_SUFFIX}",
    ]
    if automation_online():
        if max_bits > 0:
            panel.append("[E] Refine max  [R] Custom amount")
        else:
            panel.append(
                f"Need {format_currency(rate)} for 1 {AUTOMATION_CURRENCY_NAME}."
            )
    else:
        panel.append("Automation offline — exchange unavailable.")
    return panel


def automation_upgrade_label(upg_id):
    idx = AUTOMATION_UPGRADE_INDEX.get(upg_id, -1)
    if idx < 0:
        return upg_id
    return AUTOMATION_UPGRADES[idx].get("name", upg_id)


def build_auto_buyer_panel():
    lines = [f"{Fore.CYAN}Auto-Buyers{Style.RESET_ALL}"]
    if not game.get("auto_buyer_unlocked", False):
        lines.append("Complete S-CHAL-1+ to activate auto-buyers.")
        return lines
    tiers = int(game.get("automation_auto_tiers", 0))
    if tiers <= 0:
        lines.append("Install Acquisition Relays to add tiers.")
        return lines
    targets = AUTO_BUYER_TARGET_ORDER
    for tier_idx in range(tiers):
        if tier_idx < len(targets):
            label = automation_upgrade_label(targets[tier_idx])
        else:
            label = "Adaptive sweep"
        lines.append(f"Tier {tier_idx + 1}: {label}")
    if not auto_buyer_allowed():
        lines.append("(Disabled by current challenge.)")
    return lines


def prompt_signal_exchange_amount(max_bits):
    if max_bits <= 0:
        return 0
    lines = [
        "Automation Lab — Signal Exchange",
        f"Max conversion: {format_number(max_bits)} {AUTOMATION_CURRENCY_NAME}",
        "Enter Signal Bits to refine (MAX for all, 0 to cancel).",
    ]
    tmp = boxed_lines(lines, title=" Signal Exchange ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    response = input("> ").strip().lower()
    if response in {"", "0", "cancel", "c"}:
        return 0
    if response in {"max", "all"}:
        return max_bits
    try:
        return max(0, min(max_bits, int(response)))
    except ValueError:
        set_settings_notice("Invalid amount entered.", duration=2.0)
        return 0


def exchange_signal_bits(amount=None, *, prompt=False):
    if not automation_online():
        set_settings_notice("Automation offline — exchange unavailable.")
        return False
    rate, funds, max_bits = calculate_signal_exchange_capacity()
    if max_bits <= 0:
        set_settings_notice(
            f"Need {format_currency(rate)} for 1 {AUTOMATION_CURRENCY_NAME}.",
            duration=3.0,
        )
        return False
    target = max_bits if amount is None else max(0, min(max_bits, int(amount)))
    if prompt:
        target = prompt_signal_exchange_amount(max_bits)
    if target <= 0:
        return False
    cost = target * rate
    game["money"] = max(0.0, float(game.get("money", 0.0)) - cost)
    game["automation_currency"] = game.get("automation_currency", 0.0) + target
    save_game()
    set_settings_notice(
        f"Refined {format_number(target)} {AUTOMATION_CURRENCY_NAME}.",
        duration=2.8,
    )
    return True


def get_tree_cost(upg, current_level=0):
    if upg.get("id") == "concept_breach":
        base = balanced_breach_key_cost()
        scale = upg.get("cost_mult", 1) ** current_level
        return int(max(1, base * scale))
    return int(
        upg.get("base_cost", upg.get("cost", 0))
        * (upg.get("cost_mult", 1) ** current_level)
    )


def balanced_breach_key_cost():
    base = BREACH_KEY_BASE_COST
    min_cost = BREACH_KEY_MIN_COST
    max_cost = BREACH_KEY_MAX_COST
    target = max(1, BREACH_TARGET_PROGRESS)
    slack = max(1, BREACH_SLACK_PROGRESS)
    progress = estimate_progress(game)
    delta = progress - target
    ratio = max(-1.0, min(1.0, delta / float(slack)))
    if ratio < 0:
        span = base - min_cost
        return int(round(base - span * abs(ratio)))
    span = max_cost - base
    return int(round(base + span * ratio))


def apply_inspiration_effects():
    game["motivation_unlocked"] = False
    game["motivation_cap_bonus"] = 0
    game["motivation_strength_mult"] = 1.0
    for entry in game.get("inspiration_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in INSPIRE_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        if u["type"] == "unlock_motivation" and level > 0:
            game["motivation_unlocked"] = True
        elif u["type"] == "motivation_cap" and level > 0:
            base = float(u.get("base_value", u.get("value", 0)))
            mult = float(u.get("value_mult", 1))
            val = base * (mult ** max(0, level - 1))
            game["motivation_cap_bonus"] += int(round(val))
        elif u["type"] == "motivation_strength" and level > 0:
            base = float(u.get("base_value", u.get("value", 1)))
            mult = float(u.get("value_mult", 1))
            val = base * (mult ** max(0, level - 1))
            game["motivation_strength_mult"] *= max(1.0, val)
    if game.get("motivation_unlocked", False):
        clamp_motivation()
    else:
        set_motivation(0)


def apply_concept_effects():
    had_key = game.get("breach_key_obtained", False)
    for entry in game.get("concept_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in CONCEPT_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        if u["type"] == "unlock_rpg" and level > 0:
            game["breach_key_obtained"] = True

    gained_key = game.get("breach_key_obtained", False) and not had_key
    if gained_key:
        announce_breach_door_manifestation()


def apply_automation_effects():
    game["automation_delay_mult"] = 1.0
    game["automation_gain_mult"] = 1.0
    game["automation_synergy_mult"] = 1.0
    game["automation_auto_tiers"] = 0
    for entry in game.get("automation_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in AUTOMATION_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        base = float(u.get("base_value", u.get("value", 1.0)))
        step = float(u.get("value_mult", 1.0))
        val = base * (step ** max(0, level - 1))
        etype = u.get("type")
        if etype == "auto_delay_mult":
            game["automation_delay_mult"] *= max(0.01, val)
        elif etype == "auto_money_mult":
            game["automation_gain_mult"] *= max(0.0, val)
        elif etype == "automation_synergy":
            game["automation_synergy_mult"] *= max(0.0, val)
        elif etype == "auto_buyer_slots" and level > 0:
            game["automation_auto_tiers"] += int(level)


def _auto_buyer_attempt_purchase(upg_id):
    idx = AUTOMATION_UPGRADE_INDEX.get(upg_id, -1)
    if idx < 0:
        return False
    owned, level = get_automation_info(upg_id)
    upg = AUTOMATION_UPGRADES[idx]
    max_level = upg.get("max_level", 1)
    if level >= max_level:
        return False
    cost = get_tree_cost(upg, current_level=level)
    holdings = game.get("automation_currency", 0)
    if holdings < cost:
        return False
    return bool(buy_tree_upgrade(AUTOMATION_UPGRADES, idx, auto=True, save=False))


def process_auto_buyers():
    if not auto_buyer_allowed():
        return False
    tiers = int(game.get("automation_auto_tiers", 0))
    if tiers <= 0:
        return False
    if not AUTO_BUYER_TARGET_ORDER:
        return False
    progress = False
    for tier_idx in range(tiers):
        if game.get("automation_currency", 0) <= 0:
            break
        candidates = (
            [AUTO_BUYER_TARGET_ORDER[tier_idx]]
            if tier_idx < len(AUTO_BUYER_TARGET_ORDER)
            else AUTO_BUYER_TARGET_ORDER
        )
        while True:
            purchased = False
            for target in candidates:
                if _auto_buyer_attempt_purchase(target):
                    purchased = True
                    progress = True
                    break
            if not purchased:
                break
    if progress:
        save_game()
    return progress


def challenge_metric(metric_id):
    if metric_id == "money_since_reset":
        return game.get("money_since_reset", 0.0)
    if metric_id == "play_time":
        return game.get("play_time", 0.0)
    if metric_id == "stability_resets":
        return game.get("stability_resets", 0)
    if metric_id == "stability_manual_resets":
        return game.get("stability_manual_resets", 0)
    if metric_id == "inspiration_resets":
        return game.get("inspiration_resets", 0)
    if metric_id == "concept_resets":
        return game.get("concept_resets", 0)
    return game.get(metric_id, 0)


def challenge_unlocked(info):
    if not info:
        return False
    unlock_metric = info.get("unlock_type")
    if not unlock_metric:
        return True
    threshold = info.get("unlock_value", info.get("goal_value", 0))
    return challenge_metric(unlock_metric) >= threshold


def challenge_progress(info):
    if not info:
        return (0, 1)
    goal = _challenge_goal(info)
    cid = info.get("id")
    completed = cid in game.get("challenges_completed", [])
    if completed:
        return goal, goal
    metric = info.get("goal_type")
    if metric in EVENT_GOAL_TYPES:
        progress = challenge_event_progress(metric)
        return progress, goal
    total = challenge_metric(metric)
    state = challenge_state_data()
    if state.get("active_id") == cid:
        baseline = state.get("baseline", {}).get(metric, total)
        progress = max(0, total - baseline)
    else:
        progress = 0
    return progress, goal


def challenge_reward_summary(info):
    reward = info.get("reward") or {}
    rtype = reward.get("type")
    value = reward.get("value")
    if rtype == "money_mult" and value:
        pct = (float(value) - 1.0) * 100
        return f"+{pct:.0f}% money gain"
    if rtype == "motivation_cap" and value:
        return f"+{int(value)} motivation cap"
    if rtype == "unlock_autowork":
        return "Unlock auto-work"
    if rtype == "unlock_auto_buyer":
        return "Unlock auto-buyers"
    return "Permanent bonus unlocked"


def apply_challenge_reward(info, target_state=None):
    reward = info.get("reward") or {}
    rtype = reward.get("type")
    value = reward.get("value")
    state = target_state if target_state is not None else game
    if rtype == "money_mult" and value:
        mult = max(0.0, float(state.get("money_mult", 1.0)))
        state["money_mult"] = max(0.0, mult * float(value))
    elif rtype == "motivation_cap" and value:
        bonus = int(value)
        state["motivation_cap_bonus"] = state.get("motivation_cap_bonus", 0) + bonus
        if state is game and game.get("motivation_unlocked", False):
            clamp_motivation()
    elif rtype == "unlock_autowork":
        if state is game:
            enable_auto_work(show_notice=True)
        else:
            state["auto_work_unlocked"] = True
    elif rtype == "unlock_auto_buyer":
        if state is game:
            enable_auto_buyers(show_notice=True)
        else:
            state["auto_buyer_unlocked"] = True


def check_challenges(reason=None):
    entry = active_challenge_entry()
    if not entry:
        return False
    persistent_state = challenge_persistent_state()
    completed = set(persistent_state.get("challenges_completed", []))
    cid = entry.get("id")
    if not cid or cid in completed:
        return False
    progress, goal = challenge_progress(entry)
    if progress < goal:
        return False
    completed.add(cid)
    completed_list = list(completed)
    persistent_state["challenges_completed"] = completed_list
    game["challenges_completed"] = completed_list
    apply_challenge_reward(entry, target_state=persistent_state)
    summary = challenge_reward_summary(entry)
    clear_active_challenge(
        notice=f"Challenge complete: {entry.get('name', 'Unknown')} ({summary}).",
        duration=3.5,
    )
    return True


def challenge_status(entry):
    if not entry:
        return "unknown"
    cid = entry.get("id")
    if not cid:
        return "unknown"
    if cid in game.get("challenges_completed", []):
        return "completed"
    if current_challenge_id() == cid:
        return "active"
    if not challenge_unlocked(entry):
        return "locked"
    return "ready"


def challenge_completed(challenge_id):
    if not challenge_id:
        return False
    return challenge_id in game.get("challenges_completed", [])


def challenge_unlock_progress(entry):
    metric = entry.get("unlock_type")
    if not metric:
        return None
    current = challenge_metric(metric)
    goal = entry.get("unlock_value", entry.get("goal_value", 1))
    return current, goal


def challenge_ready_to_claim(entry):
    progress, goal = challenge_progress(entry)
    return progress >= goal and goal > 0


def build_challenge_summary_line():
    if not challenge_feature_ready():
        return (
            f"{Fore.LIGHTBLACK_EX}...{Style.RESET_ALL}"
        )
    if not challenge_feature_active():
        return (
            f"{Fore.LIGHTBLACK_EX}Challenge board syncing — give the Instability Array a moment to calibrate.{Style.RESET_ALL}"
        )
    entry = active_challenge_entry()
    if entry:
        label = entry.get("name", "Challenge")
        group = entry.get("group")
        if group:
            label = f"{label} ({group})"
        progress, goal = challenge_progress(entry)
        ratio = 0 if goal <= 0 else min(1.0, progress / goal)
        pct = int(ratio * 100)
        progress_text = f"{format_number(progress)} / {format_number(goal)}"
        return (
            f"{Fore.LIGHTBLUE_EX}Challenge{Style.RESET_ALL}: {label} — "
            f"{progress_text} ({pct}%)"
        )
    completed_ids = set(game.get("challenges_completed", []))
    ready = [c for c in CHALLENGES if c.get("id") not in completed_ids and challenge_unlocked(c)]
    if not ready:
        if len(completed_ids) == len(CHALLENGES) and CHALLENGES:
            return f"{Fore.LIGHTGREEN_EX}All challenges cleared!{Style.RESET_ALL}"
        return f"{Fore.LIGHTBLACK_EX}Challenges locked — meet unlock goals to begin.{Style.RESET_ALL}"
    return f"No active challenge. Press [H] to open the challenge board."


def build_challenge_board_lines():
    lines = []
    entries = []
    page_label = "Trials"
    page_idx = 0
    total_pages = 1
    if not challenge_feature_active():
        lines.append("Challenge board offline.")
        if challenge_feature_ready():
            lines.append("Instability Array calibrating — please wait a moment.")
        else:
            lines.append("Install the Instability Array in the Stabilizer (T) to enable trials.")
        lines.append("")
        lines.append("Press B to return.")
        return lines, entries, page_label, page_idx, total_pages

    entries, page_label, page_idx, total_pages = current_challenge_page_entries()
    cursor = int(game.get("challenge_cursor", 0))
    if entries:
        cursor = max(0, min(len(entries) - 1, cursor))
    else:
        cursor = 0
    game["challenge_cursor"] = cursor
    completed_ids = set(game.get("challenges_completed", []))

    header = f"Layer page: {page_label} ({page_idx + 1}/{total_pages})"
    lines.append(header)
    lines.append("Optional objectives grant permanent buffs.")
    lines.append("")

    for idx, entry in enumerate(entries):
        status = challenge_status(entry)
        marker = f"{Fore.CYAN}›{Style.RESET_ALL}" if idx == cursor else " "
        display_name = entry.get("name", "Unknown")
        entry_group = entry.get("group")
        if entry_group:
            display_name = f"{display_name} ({entry_group})"
        if status == "completed":
            color = Fore.GREEN
            tag = "CLEARED"
        elif status == "active":
            color = Fore.YELLOW
            tag = "ACTIVE"
        elif status == "ready":
            color = Fore.CYAN
            tag = "READY"
        else:
            color = Fore.LIGHTBLACK_EX
            tag = "LOCKED"
        name_line = f"{marker} {color}{display_name}{Style.RESET_ALL} [{tag}]"
        lines.append(name_line)
        lines.append(f"   {entry['desc']}")
        mod_summary = summarize_challenge_modifiers(entry)
        if mod_summary:
            lines.append(f"   Debuffs: {mod_summary}")
        reward = challenge_reward_summary(entry)
        if reward:
            lines.append(f"   Reward: {reward}")
        if status == "locked":
            unlock = challenge_unlock_progress(entry)
            if unlock:
                current, goal = unlock
                lines.append(
                    f"   Unlock progress: {format_number(current)} / {format_number(goal)}"
                )
        elif status == "active":
            progress, goal = challenge_progress(entry)
            pct = 0 if goal <= 0 else min(100, int((progress / goal) * 100))
            bar = build_progress_bar(pct, width=18)
            lines.append(f"   {bar}")
            lines.append(
                f"   Progress: {format_number(progress)} / {format_number(goal)}"
            )
        elif status == "ready":
            lines.append("   Press Enter to begin tracking this challenge.")
        elif status == "completed":
            lines.append("   Completed!")
        lines.append("")

    if not entries:
        lines.append("No challenges configured for this layer yet.")
    if not CHALLENGES:
        lines.append("No challenges configured.")
    control = "Use W/S to move, Enter to start/claim, F to forfeit, B to exit."
    if total_pages > 1:
        control += "  Z/X switch layer pages."
    if challenge_run_active_flag():
        control += "  R reapplies the active layer reset."
    if manual_collapse_available():
        control += "  L triggers a manual collapse."
    lines.append(f"{Fore.YELLOW}{control}{Style.RESET_ALL}")
    return lines, entries, page_label, page_idx, total_pages


def open_challenge_board():
    global KEY_PRESSED
    if not challenge_feature_ready():
        tmp = boxed_lines(
            ["Challenge board offline.", "Install the Instability Array in the Stabilizer (T) to enable trials."],
            title=" Challenge Board ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(1.2)
        return
    ensure_challenge_feature()
    if not challenge_feature_active():
        tmp = boxed_lines(
            ["Challenge board syncing. Give the Instability Array a moment to stabilize."],
            title=" Challenge Board ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(1.0)
        return
    last_frame = None
    last_size = get_term_size()
    while True:
        work_tick()
        check_challenges("board")
        lines, entries, _, page_idx, total_pages = build_challenge_board_lines()
        entry_count = len(entries)
        box = boxed_lines(lines, title=" Challenge Board ", pad_top=1, pad_bottom=1)
        current_size = get_term_size()
        frame = "\n".join(box)
        if frame != last_frame or current_size != last_size:
            render_frame(box)
            last_frame = frame
            last_size = current_size
        time.sleep(0.05)
        if not KEY_PRESSED:
            continue
        k = KEY_PRESSED
        KEY_PRESSED = None
        if isinstance(k, str):
            if k in {"\r", "\n", "enter"}:
                k = "enter"
            else:
                k = k.lower()
        if k in {"b", "q"}:
            return
        if k in {"w", "s"} and entry_count:
            delta = -1 if k == "w" else 1
            current = int(game.get("challenge_cursor", 0))
            game["challenge_cursor"] = (current + delta) % entry_count
            continue
        if k in {"enter", "a"} and entry_count:
            idx = max(0, min(entry_count - 1, int(game.get("challenge_cursor", 0))))
            entry = entries[idx]
            status = challenge_status(entry)
            if status == "locked":
                set_settings_notice("Meet the unlock requirement first.")
            elif status == "completed":
                set_settings_notice("Challenge already cleared.")
            elif status == "active":
                if challenge_ready_to_claim(entry):
                    check_challenges("manual-claim")
                else:
                    set_settings_notice("Challenge in progress — keep pushing.")
            elif status == "ready":
                activate_challenge(entry)
            continue
        if k in {"z", "x"} and total_pages > 1:
            delta = -1 if k == "z" else 1
            new_page = (page_idx + delta) % total_pages
            game["challenge_page"] = new_page
            game["challenge_cursor"] = 0
            continue
        if k == "f":
            if not forfeit_active_challenge():
                set_settings_notice("No active challenge to forfeit.")
            continue
        if k == "r":
            challenge_layer_reset()
            continue
        if k == "l":
            if manual_collapse_available():
                manual_stability_collapse()
                last_frame = None
            else:
                set_settings_notice(
                    manual_collapse_requirement_text(),
                    duration=2.5,
                )
            continue


def open_guide_book():
    global KEY_PRESSED
    if not guide_available():
        set_settings_notice("Field Guide offline. Earn more to sync it up.", duration=2.5)
        return
    game["guide_has_new"] = False
    unread_topics = set(game.get("guide_unread_topics", []) or [])
    guide_unread_changed = False
    last_frame = None
    last_size = get_term_size()
    while True:
        work_tick()
        topics = available_guide_topics()
        cursor = int(game.get("guide_cursor", 0))
        if topics:
            cursor = max(0, min(len(topics) - 1, cursor))
        else:
            cursor = 0
        game["guide_cursor"] = cursor
        context = guide_render_context()
        lines = ["Mechanics Guide", ""]
        if topics:
            for idx, topic in enumerate(topics):
                marker = f"{Fore.CYAN}›{Style.RESET_ALL}" if idx == cursor else " "
                tid = topic.get("id")
                title = topic["title"]
                if tid and tid in unread_topics:
                    title = f"{Style.BRIGHT}{title}{Style.RESET_ALL}"
                lines.append(f"{marker} {title}")
            lines.append("")
            selected = topics[cursor]
            selected_id = selected.get("id")
            if selected_id and selected_id in unread_topics:
                unread_topics.remove(selected_id)
                game["guide_unread_topics"] = list(unread_topics)
                guide_unread_changed = True
            lines.append(f"{Fore.LIGHTYELLOW_EX}{selected['title']}{Style.RESET_ALL}")
            lines.append("")
            for raw in selected.get("lines", []):
                text = raw.format(**context)
                wrapped = wrap_ui_text(text, width=70, reserved=3)
                for seg in wrapped:
                    lines.append(f"   {seg}")
            if guide_unread_changed:
                save_game()
                guide_unread_changed = False
        else:
            lines.append("No guide pages unlocked yet. Advance further to reveal more mechanics.")
        lines.append("")
        lines.append(f"{Fore.YELLOW}Use W/S to browse, B to exit.{Style.RESET_ALL}")
        box = boxed_lines(lines, title=" Field Guide ", pad_top=1, pad_bottom=1)
        current_size = get_term_size()
        frame = "\n".join(box)
        if frame != last_frame or current_size != last_size:
            render_frame(box)
            last_frame = frame
            last_size = current_size
        time.sleep(0.05)
        if not KEY_PRESSED:
            continue
        k = KEY_PRESSED
        KEY_PRESSED = None
        if isinstance(k, str):
            if k in {"\r", "\n", "enter"}:
                k = "enter"
            else:
                k = k.lower()
        if k == "b":
            return
        if k in {"w", "s"} and topics:
            delta = -1 if k == "w" else 1
            game["guide_cursor"] = (cursor + delta) % len(topics)
def compute_gain_and_delay(auto=False):
    base_gain = BASE_MONEY_GAIN
    base_delay = BASE_WORK_DELAY
    gain_add = 0.0
    gain_mult = 1.0
    delay_mult = 1.0
    mods = active_challenge_modifiers()
    for entry in game.get("inspiration_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in INSPIRE_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        base = float(u.get("base_value", u.get("value", 1)))
        step = float(u.get("value_mult", 1))
        val = base * (step ** max(0, level - 1))
        t = u.get("type")
        if t in ("money_mult", "mult", "money"):
            gain_mult *= val
        elif t in ("add", "value"):
            gain_add += val
        elif t in ("work_mult", "reduce_delay"):
            delay_mult *= val
    for entry in game.get("concept_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in CONCEPT_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        base = float(u.get("base_value", u.get("value", 1)))
        step = float(u.get("value_mult", 1))
        val = base * (step ** max(0, level - 1))
        t = u.get("type")
        if t in ("money_mult", "mult", "money"):
            gain_mult *= val
        elif t == "auto_money_mult":
            if auto:
                gain_mult *= val
        elif t in ("add", "value"):
            gain_add += val
        elif t in ("work_mult", "reduce_delay"):
            delay_mult *= val
        elif t == "unlock_rpg" and level > 0:
            game["breach_key_obtained"] = True
    for uid, lvl in game.get("upgrade_levels", {}).items():
        if lvl <= 0:
            continue
        u = next((x for x in UPGRADES if x["id"] == uid), None)
        if not u:
            continue
        base = float(u.get("base_value", u.get("value", 1)))
        step = float(u.get("value_mult", 1))
        val = base * (step ** max(0, lvl - 1))
        t = u.get("type")
        if t in ("money_mult", "mult", "money"):
            gain_mult *= val
        elif t in ("add", "value"):
            gain_add += val
        elif t in ("work_mult", "reduce_delay", "reduce_cd"):
            delay_mult *= val
        elif t == "unlock_focus" and lvl > 0:
                                                           
            pass
        elif t == "unlock_rpg" and lvl > 0:
            game["breach_key_obtained"] = True

    if game.get("motivation_unlocked", False):
        cap = motivation_capacity()
        peak = motivation_peak_multiplier()
        motivation = max(0, min(cap, game.get("motivation", cap)))
        ratio = motivation / max(1, cap)
        motivation_mult = 1 + ratio * (peak - 1)
        gain_mult *= motivation_mult
    time_reward = get_time_reward_multiplier()
    game["time_reward_multiplier"] = time_reward
    gain_mult *= get_time_money_multiplier(time_reward)
    signal_bonus = max(0.0, get_resonance_efficiency())
    signal_mult = 1.0 + signal_bonus
    game["signal_multiplier"] = signal_mult
    automation_synergy = max(0.0, game.get("automation_synergy_mult", 1.0))
    automation_gain = max(0.0, game.get("automation_gain_mult", 1.0))
    automation_delay = max(0.01, game.get("automation_delay_mult", 1.0))
    if automation_online():
        gain_mult *= automation_synergy if automation_synergy > 0 else 1.0
    if auto:
        gain_mult *= automation_gain if automation_gain > 0 else 1.0
        delay_mult *= automation_delay if automation_delay > 0 else 1.0
    money_gain_mod = mods.get("money_gain_mult")
    if isinstance(money_gain_mod, (int, float)) and money_gain_mod > 0:
        gain_mult *= money_gain_mod
    if auto:
        auto_delay_mod = mods.get("auto_delay_mult")
        if isinstance(auto_delay_mod, (int, float)) and auto_delay_mod > 0:
            delay_mult *= auto_delay_mod

    eff_gain = base_gain * gain_mult + gain_add
    eff_gain *= BASE_MONEY_MULT
    eff_gain *= max(0.0, game.get("money_mult", 1.0))
    eff_gain *= signal_mult
    eff_gain *= escape_multiplier()
    eff_delay = max(base_delay * delay_mult, 0.01)
    return eff_gain, eff_delay


def boxed_lines(
    content_lines, title=None, pad_top=1, pad_bottom=1, margin=config.BOX_MARGIN
):
    term_w, term_h = get_term_size()
    box_w = max(config.MIN_BOX_WIDTH, term_w - margin * 2)
    inner_w = box_w - 2
    layer = game.get("layer", 0)
    layer_def = LAYER_BY_ID.get(layer, {})
    border_key = layer_def.get("border_id", layer)
    if game.get("mirror_reality_active"):
        border_key = MIRROR_BORDER_ID
    style = BORDERS.get(border_key)
    if style is None:
        style = list(BORDERS.values())[0]
    tl, tr, bl, br = style["tl"], style["tr"], style["bl"], style["br"]
    h, v = style["h"], style["v"]

    if title:
        t = f" {title} "
        vis_t = visible_len(t)
        if vis_t >= inner_w:
            top = tl + h * inner_w + tr
        else:
            left = (inner_w - vis_t) // 2
            top = tl + h * left + t + h * (inner_w - left - vis_t) + tr
    else:
        top = tl + h * inner_w + tr
    lines = [top]

    for _ in range(pad_top):
        lines.append(v + " " * inner_w + v)

    for raw in content_lines:
        if raw is None:
            raw = ""
        segs = wrap_visible_text(raw, inner_w)

        for s in segs:
            vis_len = visible_len(s)
            pad = inner_w - vis_len
            if pad < 0:
                pad = 0
            left = pad // 2
            right = pad - left
            line_content = " " * left + s + " " * right
            while visible_len(line_content) > inner_w:
                line_content = line_content[:-1]
            while visible_len(line_content) < inner_w:
                line_content += " "
            lines.append(v + line_content + v)

    for _ in range(pad_bottom):
        lines.append(v + " " * inner_w + v)

    lines.append(bl + h * inner_w + br)
    if layer == 3 and pad_top >= 1:
        try:
            p_count = getattr(config, "LAYER2_PARTICLE_COUNT", 0)
            if p_count > 0:
                p_chars = getattr(config, "LAYER2_PARTICLE_CHARS", ["·", "*", "."])
                p_amp = getattr(config, "LAYER2_PARTICLE_AMPLITUDE", 8)
                p_freq = getattr(config, "LAYER2_PARTICLE_FREQ", 3)
                tick = int(time.time() * float(p_freq))
                top_pad_idx = 1
                if top_pad_idx < len(lines):
                    row = list(lines[top_pad_idx])
                    for i in range(p_count):
                        offset = ((tick * 7 + i * 13) % max(1, p_amp)) - (p_amp // 2)
                        pos = 1 + (inner_w // 2) + offset
                        pos = max(1, min(1 + inner_w - 1, pos))
                        ch = p_chars[(tick + i) % len(p_chars)]
                        if row[pos] == " ":
                            row[pos] = ch
                    lines[top_pad_idx] = "".join(row)
        except Exception:
            pass

    left_margin = max(0, (term_w - box_w) // 2)
    margin_str = " " * left_margin
    assert all(
        visible_len(line[1:-1]) == inner_w for line in lines[1:-1]
    ), "Line width mismatch"
    return [margin_str + l for l in lines]


def render_desk_table():
    global steam, steam_last_update
    table = LAYER_0_DESK.copy()
    total_money = game.get("money_since_reset", 0)
    
    if total_money < 10:
        table[1] = "║     Where am I?       ║"
    elif total_money < 30:
        table[1] = "║      A desk...        ║"
        
    owned_set = set(game.get("owned", []))
    replacement_pairs = getattr(config, "UPGRADE_REPLACEMENT", {}) or {}
    replacement_by_old = {old: new for new, old in replacement_pairs.items()}
    owned_ids = []
    seen = set()
    for entry in config.UPGRADES:
        uid = entry["id"]
        if uid not in owned_set:
            continue
        display_id = replacement_by_old.get(uid)
        if display_id and display_id in owned_set:
            target_id = display_id
        else:
            target_id = uid
        if target_id in seen:
            continue
        seen.add(target_id)
        owned_ids.append(target_id)
                                                                                  
    owned_arts = [uid for uid in owned_ids if uid in UPGRADE_ART]

    # Soft animation overrides: replace static art with timed frames
    anim_overrides = {}
    try:
        now = time.time()
        # keyboard soft animation (toggle every 0.6s)
        if "keyboard" in owned_ids:
            phase = int(now / 0.6) % 2
            key = "keyboard_soft_0" if phase == 0 else "keyboard_soft_1"
            anim_overrides["keyboard"] = UPGRADE_ANIM_ART_FRAMES.get(key, UPGRADE_ART.get("keyboard"))
        if "mech_keyboard" in owned_ids:
            phase = int(now / 0.6) % 2
            key = "mech_keyboard_soft_0" if phase == 0 else "mech_keyboard_soft_1"
            anim_overrides["mech_keyboard"] = UPGRADE_ANIM_ART_FRAMES.get(key, UPGRADE_ART.get("mech_keyboard"))
    except Exception:
        anim_overrides = {}

    empty_indices = [
        i for i, line in enumerate(table) if line.startswith("║") and line.endswith("║")
    ]
    available = list(empty_indices)
    used_indices = set()
    if "coffee" in owned_arts:
        coffee_h = len(UPGRADE_ART["coffee"])
        best_seq = None
        if available:
            center_val = available[len(available) // 2]
        else:
            center_val = None
        for j in range(0, len(available) - coffee_h + 1):
            seq = available[j : j + coffee_h]
            ok = True
            for k in range(coffee_h):
                if seq[k] != available[j] + k:
                    ok = False
                    break
            if not ok:
                continue
            seq_center = seq[coffee_h // 2]
            dist = abs(seq_center - center_val) if center_val is not None else 0
            if best_seq is None or dist < best_seq[0]:
                best_seq = (dist, seq)
        if best_seq:
            _, seq = best_seq
            for line_pos, art_line in zip(seq, UPGRADE_ART["coffee"]):
                table[line_pos] = "║" + art_line.center(23) + "║"
                used_indices.add(line_pos)
            owned_arts.remove("coffee")
    remaining_slots = [i for i in empty_indices if i not in used_indices]
    empty_idx_iter = iter(reversed(remaining_slots))
    for uid in owned_arts:
        art = anim_overrides.get(uid, UPGRADE_ART.get(uid))
        if not art:
            continue
        art_height = len(art)
        art_positions = []
        try:
            for _ in range(art_height):
                art_positions.append(next(empty_idx_iter))
        except StopIteration:
            break
        for line_pos, art_line in zip(reversed(art_positions), art):
            table[line_pos] = "║" + art_line.center(23) + "║"
    if "coffee" in owned_ids:
        coffee_idx = None
        for i, art_id in enumerate(owned_ids):
            if art_id == "coffee":
                coffee_idx = empty_indices[-(i + 1)]
                break
        if coffee_idx is not None:
            coffee_art = UPGRADE_ART["coffee"]
            cup_height = len(coffee_art)
            steam_start_idx = coffee_idx - (cup_height - 1)
            steam_emit_idx = steam_start_idx - 2
            coffee_line = coffee_art[0]
            first_char_idx = next((i for i, c in enumerate(coffee_line) if c != " "), 0)
            last_char_idx = len(coffee_line.rstrip()) - 1
            desk_inner_w = 23
            cup_center = (
                (desk_inner_w // 2)
                + (first_char_idx + last_char_idx) // 2
                - (len(coffee_line) // 2)
            )
            if not game.get("settings_disable_steam", False):
                now = time.time()
                delta = max(0.0, min(0.25, now - steam_last_update))
                steam_last_update = now
                lifetime = max(0.5, float(config.STEAM_LIFETIME))
                speed = max(0.01, float(config.STEAM_SPEED))
                new_steam = []
                for x, y, life in steam:
                    y -= speed * delta
                    life -= delta
                    if life > 0 and y >= 0:
                        new_steam.append((x, y, life))
                steam = new_steam
                spawn_rate = max(0.0, float(config.STEAM_CHANCE))
                spawn_chance = min(1.0, spawn_rate * delta)
                if random.random() < spawn_chance:
                    offset = random.randint(-config.STEAM_SPREAD, config.STEAM_SPREAD)
                    steam.append((cup_center + offset, steam_emit_idx, lifetime))
                for x, y, life in steam:
                    yi = int(round(y))
                    if 0 <= yi < len(table):
                        line = table[yi]
                        if 0 <= x < len(line):
                            progress = 1.0 - (life / lifetime)
                            stage_idx = min(
                                len(config.STEAM_CHARS) - 1,
                                max(0, int(progress * len(config.STEAM_CHARS))),
                            )
                            stage_char = config.STEAM_CHARS[stage_idx]
                            line = line[:x] + stage_char + line[x + 1 :]
                            table[yi] = line
    return table


def perform_work(gain, eff_delay, manual=False):
    global work_timer
    now = time.time()
    if wake_timer_blocked():
        if manual:
            show_wake_timer_warning()
        return False
    game["money"] += gain
    game["money_since_reset"] += gain
    track_manual_work_spam(manual)
    if manual:
        mark_known("ui_work_prompt")
    if game.get("motivation_unlocked", False):
        cap = motivation_capacity()
        current = game.get("motivation", cap)
        set_motivation(current - 1)
    if not manual and auto_work_allowed():
        work_timer = max(0.0, work_timer - eff_delay)
    check_challenges("work")
    save_game()
    return True



def stability_reward_multiplier():
    levels = get_wake_upgrade_levels()
    bonus = 1.0
    for upg in WAKE_TIMER_UPGRADES:
        level = levels.get(upg["id"], 0)
        total = wake_upgrade_total_bonus(
            upg,
            level,
            "stability_bonus",
            "stability_bonus_scale",
        )
        if total > 0:
            bonus += total
    return max(1.0, bonus)


def calculate_stability_reward(money_pool):
    pool = max(0.0, float(money_pool)) + 1.0
    reward = (pool**STABILITY_REWARD_EXP) * STABILITY_REWARD_MULT
    reward *= stability_reward_multiplier()
    reward *= escape_multiplier()
    return max(1, int(round(reward)))


def wipe_to_stability_baseline(state):
    state.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "motivation": 0,
            "owned": [],
            "upgrade_levels": {},
        }
    )
    state["wake_timer"] = state.get("wake_timer_cap", WAKE_TIMER_START)
    state["wake_timer_locked"] = False
    state["wake_timer_notified"] = False
    state["needs_stability_reset"] = False


def perform_stability_collapse(manual=False):
    global work_timer, last_render
    if game.get("wake_timer_infinite", False):
        return
    money_pool = max(game.get("money", 0.0), game.get("money_since_reset", 0.0))
    reward = calculate_stability_reward(money_pool)
    grant_stability_currency(game, reward)
    machine = escape_machine_state()
    machine["spark_bank"] = machine.get("spark_bank", 0) + reward
    handle_machine_progress_event("stability")
    game["stability_resets"] = game.get("stability_resets", 0) + 1
    check_collapse_easter_eggs()
    if manual:
        game["stability_manual_resets"] = game.get("stability_manual_resets", 0) + 1
    lines = [
        "Collapse triggered.",
        f"Recovered {format_number(reward)} {STABILITY_CURRENCY_NAME}.",
        "Spend sparks in the stabilizer menu (T).",
    ]
    if automation_lab_available():
        lines.append("Route spare funds through the Automation Lab to refine Signal Bits.")
    tmp = boxed_lines(lines, title=" Collapse ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(1.2)
    work_timer = 0.0
    wipe_to_stability_baseline(game)
    recalc_wake_timer_state()
    refresh_knowledge_flags()
    check_challenges("stability")
    save_game()
    last_render = ""
    if game.get("wake_timer_infinite", False):
        return
    open_wake_timer_menu(auto_invoked=True)
    last_render = ""


def manual_stability_collapse():
    if not manual_collapse_available():
        set_settings_notice(manual_collapse_requirement_text())
        return False
    if game.get("wake_timer_infinite", False):
        set_settings_notice("Escape window sealed; disable the lock before collapsing.")
        return False
    perform_stability_collapse(manual=True)
    set_settings_notice(
        "Manual collapse triggered. Sparks stored—refine Signal Bits in the lab.",
        duration=3.5,
    )
    return True


def work_tick():
    global last_tick_time, work_timer, _LAST_GUIDE_REFRESH
    now = time.time()
    delta = now - last_tick_time
    last_tick_time = now
    game["play_time"] = game.get("play_time", 0.0) + delta
    check_session_easter_eggs()
    ensure_challenge_feature()
    ensure_field_guide_unlock()
    if now - _LAST_GUIDE_REFRESH >= GUIDE_REFRESH_INTERVAL:
        refresh_guide_topics()
        _LAST_GUIDE_REFRESH = now
    advance_time_flow(delta)
    if not game.get("wake_timer_infinite", False):
        current_timer = game.get("wake_timer", WAKE_TIMER_START)
        if current_timer > 0:
            current_timer = max(0.0, current_timer - delta)
            game["wake_timer"] = current_timer
        if wake_timer_blocked():
            if not game.get("needs_stability_reset", False):
                game["needs_stability_reset"] = True
                perform_stability_collapse()
            return
    game["wake_timer_locked"] = wake_timer_blocked()
    
    update_resonance(delta)

    if game.get("motivation_unlocked", False) and MOTIVATION_REGEN_RATE > 0:
        cap = motivation_capacity()
        current = game.get("motivation", cap)
        regen = MOTIVATION_REGEN_RATE * delta
        if regen > 0 and current < cap:
            set_motivation(current + regen)
    
    auto_ready = auto_work_allowed()
    if auto_ready and not wake_timer_blocked():
        gain, eff_delay = compute_gain_and_delay(auto=True)
        work_timer += delta
        if work_timer >= eff_delay:
            perform_work(gain, eff_delay, manual=False)
    process_auto_buyers()
    if refresh_knowledge_flags():
        save_game()


def get_time_velocity_multiplier_from_upgrades():
    def upgrade_value(defn, level):
        base = float(defn.get("base_value", defn.get("value", 1.0)))
        step = float(defn.get("value_mult", 1.0))
        return base * (step ** max(0, level - 1))

    multiplier = 1.0

    def apply_tree(upgrade_list, catalogue):
        nonlocal multiplier
        for entry in upgrade_list:
            upg_id, level = (
                (entry.get("id"), entry.get("level", 1))
                if isinstance(entry, dict)
                else (entry, 1)
            )
            u = next((x for x in catalogue if x["id"] == upg_id), None)
            if not u or u.get("type") != "time_velocity_mult":
                continue
            multiplier *= upgrade_value(u, level)

    apply_tree(game.get("inspiration_upgrades", []), INSPIRE_UPGRADES)
    apply_tree(game.get("concept_upgrades", []), CONCEPT_UPGRADES)

    for uid, level in game.get("upgrade_levels", {}).items():
        if level <= 0:
            continue
        u = next((x for x in UPGRADES if x["id"] == uid), None)
        if not u or u.get("type") != "time_velocity_mult":
            continue
        multiplier *= upgrade_value(u, level)

    time_mod = get_challenge_modifier("time_velocity_mult")
    if isinstance(time_mod, (int, float)) and time_mod > 0:
        multiplier *= time_mod

    return max(1.0, multiplier)


def compute_time_velocity():
    base = 1.0
    base += 0.3 * game.get("layer", 0)
    base += 0.05 * len(game.get("owned", []))
    upgrade_levels = sum(max(0, lvl) for lvl in game.get("upgrade_levels", {}).values())
    base += 0.02 * upgrade_levels
    base += 0.08 * len(game.get("inspiration_upgrades", []))
    base += 0.12 * len(game.get("concept_upgrades", []))
    money = max(1.0, game.get("money_since_reset", 0.0))
    base += math.log10(money + 1.0) * 0.4
    if automation_online():
        base *= 1.15
    if game.get("concepts_unlocked", False):
        base *= 1.08
    signal = max(0.0, get_resonance_efficiency())
    base *= 1.0 + signal * 0.12
    base *= get_time_velocity_multiplier_from_upgrades()
    return max(1.0, base)


def advance_time_flow(delta):
    strata = TIME_STRATA or []
    if not strata:
        return
    if not timeflow_active():
        game["time_velocity"] = 1.0
        game["time_progress"] = 0.0
        game["time_stratum"] = 0
        return
    velocity = compute_time_velocity()
    game["time_velocity"] = velocity
    progress = game.get("time_progress", 0.0) + delta * velocity
    game["time_progress"] = progress
    idx = int(game.get("time_stratum", 0))
    top = len(strata) - 1
    while idx < top and progress >= strata[idx + 1]["scale"]:
        idx += 1
    game["time_stratum"] = idx


def get_time_reward_multiplier():
    strata = TIME_STRATA or []
    if not strata or not timeflow_active():
        return 1.0
    idx = max(0, min(len(strata) - 1, int(game.get("time_stratum", 0))))
    current = strata[idx]
    progress = game.get("time_progress", 0.0)
    if idx >= len(strata) - 1:
        return float(current.get("reward_mult", 1.0))
    prev_floor = current.get("scale", 0.0) if idx else 0.0
    next_ceiling = strata[idx + 1].get("scale", prev_floor + 1.0)
    span = max(1.0, next_ceiling - prev_floor)
    ratio = max(0.0, min(1.0, (progress - prev_floor) / span))
    cur_mult = float(current.get("reward_mult", 1.0))
    next_mult = float(strata[idx + 1].get("reward_mult", cur_mult))
    return cur_mult + (next_mult - cur_mult) * ratio


def get_time_status():
    strata = TIME_STRATA or []
    if not strata or not timeflow_active():
        return ("", 0.0, 1.0, 1.0)
    progress = max(0.0, game.get("time_progress", 0.0))
    idx = 0
    for i, entry in enumerate(strata):
        if progress >= entry.get("scale", 0.0):
            idx = i
    idx = max(0, min(idx, len(strata) - 1))
    entry = strata[idx]
    scale = max(1.0, entry.get("scale", 1.0))
    label = entry.get("label", f"Tier {idx}") or f"Tier {idx}"
    reward = get_time_reward_multiplier()
    velocity = max(1.0, game.get("time_velocity", 1.0))
    value = progress / scale
    return label, value, reward, velocity


def timeflow_display_unlocked():
    return bool(game.get("wake_timer_infinite", False))


def timeflow_active():
    return bool(
        game.get("wake_timer_infinite", False)
        and not game.get("needs_stability_reset", False)
    )


def get_timebond_level():
    for entry in game.get("concept_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        if upg_id == "concept_timebond":
            return max(0, level)
    return 0


def get_time_velocity_bonus_multiplier():
    if not timeflow_active():
        return 1.0
    velocity = max(1.0, game.get("time_velocity", 1.0))
    if velocity <= 1.0:
        return 1.0
    bonus = max(0.0, math.sqrt(velocity) - 1.0)
                                                                           
    return 1.0 + min(2.5, bonus * 0.35)


def get_time_money_multiplier(time_reward=None):
    if not timeflow_active():
        return 1.0
    velocity_bonus = get_time_velocity_bonus_multiplier()
    level = get_timebond_level()
    if level <= 0:
        return velocity_bonus
    if time_reward is None:
        time_reward = get_time_reward_multiplier()
    excess = max(0.0, time_reward - 1.0)
    if excess <= 0:
        return velocity_bonus
    ratio = min(0.55, 0.12 * level)
    return velocity_bonus * (1.0 + excess * ratio)


def build_time_banner_line(width):
    if not timeflow_active():
        return ""
    label, value, _, _ = get_time_status()
    if value <= 0:
        return ""
    text = f"Timeflow • {value:,.2f} {label}"
    return pad_visible_line(ansi_center(text, width), width)


def build_time_hint_line():
    if not timeflow_display_unlocked():
        return ""
    if not timeflow_active():
        return (
            f"{Fore.BLUE}Timeflow offline{Style.RESET_ALL} — seal the wake window in"
            " the Stabilizer (T)."
        )
    reward = get_time_reward_multiplier()
    velocity = max(1.0, game.get("time_velocity", 1.0))
    money_mult = get_time_money_multiplier(reward)
    return (
        f"{Fore.BLUE}Timeflow{Style.RESET_ALL} vel×{velocity:.2f} |"
        f" reward×{reward:.2f} | income×{money_mult:.2f}"
    )


def build_timeflow_focus_lines():
    if not timeflow_display_unlocked():
        return []
    lines = [f"{Fore.BLUE}Timeflow Directive{Style.RESET_ALL}"]
    bullet = lambda text: lines.append(f"• {text}")
    phase_lock = next((u for u in WAKE_TIMER_UPGRADES if u.get("grant_infinite")), None)
    if game.get("wake_timer_infinite", False):
        bullet("Window sealed — stay active to build velocity.")
    elif phase_lock:
        levels = get_wake_upgrade_levels()
        phase_lock_id = phase_lock.get("id")
        current_level = levels.get(phase_lock_id, 0)
        required = max(1, int(phase_lock.get("infinite_level", 1)))
        cost = format_number(wake_upgrade_cost(phase_lock, current_level))
        sparks = format_number(game.get("stability_currency", 0))
        if current_level >= required:
            bullet("Phase Lock ready — finish a collapse to ignite Timeflow.")
        else:
            remaining = required - current_level
            bonus = wake_upgrade_next_bonus(
                phase_lock,
                current_level,
                "time_bonus",
                "time_bonus_scale",
            )
            bonus_label = f"+{int(round(bonus))}s" if bonus > 0 else "time"
            bullet(
                f"Phase Lock {current_level}/{required} — {bonus_label} per install."
            )
            if sparks_visible():
                bullet(f"Next install {cost} Sparks (bank {sparks}).")
            else:
                bullet("Sparks dormant until the Diverter calls again.")
            bullet("Press [T] to install.")
    else:
        bullet("Spend Sparks in Stabilizer (T) to unlock Phase Lock.")
    if not challenge_completed("stability_drill"):
        bullet("Clear S-CHAL-1 before attempting.")
    return lines


def guide_hotkey_hint():
    topics = available_guide_topics()
    if topics:
        badge = " (!)" if game.get("guide_has_new") else ""
        label = f"{Fore.YELLOW}[G] Guide{badge}{Style.RESET_ALL}"
        return f"{label} — press G for help on {len(topics)} topic(s)."
    if guide_available():
        return ""
    total_money = max(
        float(game.get("money_since_reset", 0.0)),
        float(game.get("money", 0.0)),
    )
    if total_money >= FIELD_GUIDE_UNLOCK_TOTAL or game.get("stability_resets", 0) >= 1:
        return ""
    target = format_currency(FIELD_GUIDE_UNLOCK_TOTAL)
    return (
        f"{Fore.LIGHTBLACK_EX}Guide offline — earn {target} total"
        f".{Style.RESET_ALL}"
    )


def compute_escape_vector_state():
    if not ESCAPE_MODE or not isinstance(game, dict):
        return None
    total_layers = max(1, len(LAYER_FLOW) - 1)
    current_layer = max(0, min(game.get("layer", 0), total_layers))
    layer_ratio = current_layer / total_layers if total_layers else 0.0
    rpg_floor = None
    rpg_data = game.get("rpg_data") or {}
    if isinstance(rpg_data, dict):
        rpg_floor = max(rpg_data.get("floor", 0), rpg_data.get("max_floor", 0))
        if rpg_floor <= 0:
            rpg_floor = None

    cap = max(1, int(game.get("wake_timer_cap", WAKE_TIMER_START)))
    if game.get("wake_timer_infinite", False):
        window_ratio = 1.0
        window_text = "Window locked open"
    else:
        remaining = max(0, min(int(game.get("wake_timer", cap)), cap))
        window_ratio = 1.0 - (remaining / cap)
        window_text = f"Window {format_clock(remaining)}"
        if wake_timer_blocked():
            window_text = "Window sealed"

    resonance_ready = resonance_system_active()
    if resonance_ready:
        signal_val = float(game.get("resonance_val", RESONANCE_START))
        signal_ratio = 1.0 - min(1.0, abs(50.0 - signal_val) / 50.0)
        signal_text = f"Signal {signal_val:05.1f}"
    else:
        signal_ratio = 0.0
        signal_text = "Signal offline"

    if rpg_floor:
        route_text = f"Route floor {rpg_floor}"
    else:
        route_text = f"Route: {current_layer_label()}"
    score = layer_ratio * 0.35 + window_ratio * 0.35 + signal_ratio * 0.30
    phase = "Dormant" if score < 0.35 else ("Aligning" if score < 0.7 else "Surging")
    return {
        "score": max(0.0, min(1.0, score)),
        "window_text": window_text,
        "route_text": route_text,
        "signal_text": signal_text,
        "phase": phase,
    }


def build_escape_meter(value, width):
    value = max(0.0, min(1.0, value))
    bar_width = max(16, min(48, width - 24))
    filled = int(round(value * bar_width))
    filled = min(bar_width, filled)
    empty = max(0, bar_width - filled)
    filled_block = f"{Fore.CYAN}{'#' * filled}{Style.RESET_ALL}" if filled else ""
    empty_block = "-" * empty
    pct = int(round(value * 100))
    return f"[{filled_block}{empty_block}] {pct:3d}%"


def build_escape_banner_lines(width):
    state = compute_escape_vector_state()
    if not state:
        return []
    window_known = is_known("escape_window")
    route_known = is_known("escape_route")
    signal_known = is_known("escape_signal")
    header = f"{Fore.CYAN}GAME{Style.RESET_ALL} · {state['phase']}"
    directive = state["window_text"] if window_known else "Hold the window open"
    details = [directive]
    if route_known and state.get("route_text"):
        details.append(state["route_text"])
    if signal_known and state.get("signal_text"):
        details.append(state["signal_text"])
    summary = "   ".join(details)
    lines = [
        pad_visible_line(ansi_center(header, width), width),
        pad_visible_line(ansi_center(summary, width), width),
    ]
    if window_known:
        meter = build_escape_meter(state["score"], width)
        lines.append(pad_visible_line(ansi_center(meter, width), width))
    else:
        lines.append(
            pad_visible_line(
                ansi_center("Diagnostics calibrating...", width),
                width,
            )
        )
    return lines


def get_tree_selection(upgrades, page_key, digit):
    term_w, term_h = get_term_size()
    max_lines = term_h // 2 - 6
    meta = tree_catalogue_meta(upgrades)
    suffix_raw = meta.get("currency_suffix")
    suffix = f" {suffix_raw}" if suffix_raw else ""
    pool_currency = meta.get("pool_currency", "")
    holdings_key = meta.get("holdings_key", "concepts")
    desc_width = max(int(term_w * 0.25) - 6, 18)

    blocks = []
    for i, u in enumerate(upgrades, start=1):
        owned, level = (
            get_inspire_info(u["id"])
            if upgrades is INSPIRE_UPGRADES
            else get_concept_info(u["id"])
        )
        max_level = u.get("max_level", 1)
        cost = get_tree_cost(u, current_level=level)
        base_value = u.get("base_value", u.get("value", 1.0))
        value_mult = u.get("value_mult", 1.0)
        total_mult = (
            base_value * (value_mult ** max(0, (level - 1)))
            if level > 0
            else base_value
        )
        holdings = game.get(holdings_key, 0)
        can_afford = holdings >= cost and level < max_level
        status_color = (
            Fore.GREEN
            if level >= max_level
            else (Fore.CYAN if can_afford else Fore.RED)
        )
        lvl_text = f"Lv {min(level, max_level)}/{max_level}"
        header = f"{status_color}{i}. {u['name']}{Style.RESET_ALL}  {Fore.YELLOW}{lvl_text}{Style.RESET_ALL}"
        block = [header]
        if level >= max_level:
            block.append(
                f"    {Fore.GREEN}MAXED — permanent bonus locked{Style.RESET_ALL}"
            )
        else:
            cost_line = (
                f"    Cost: {Fore.LIGHTYELLOW_EX}{format_number(cost)}{suffix}{Style.RESET_ALL}"
            )
            have_line = (
                f"    You:  {Fore.LIGHTYELLOW_EX}{format_number(holdings)}{suffix}{Style.RESET_ALL}"
                f"  ({pool_currency})"
            )
            block.extend([cost_line, have_line])
        if u.get("desc"):
            desc_text = f"→ {u['desc']}"
            if level > 0 and u["type"] not in ("unlock_motivation",):
                desc_text += f" (x{total_mult:.2f})"
            wrapped = wrap_ui_text(desc_text, width=desc_width, reserved=4)
            block += [f"    {Fore.LIGHTBLACK_EX}{w}{Style.RESET_ALL}" for w in wrapped]
        block.append(
            f"    {Fore.LIGHTBLACK_EX}{'-' * max(24, desc_width // 2)}{Style.RESET_ALL}"
        )
        blocks.append(block)

    pages = []
    items_per_page = []
    current = []
    used = 0
    items_in_current = 0
    for block in blocks:
        if used + len(block) > max_lines and current:
            pages.append(current)
            items_per_page.append(items_in_current)
            current, used, items_in_current = [], 0, 0
        current += block
        used += len(block)
        items_in_current += 1
    if current:
        pages.append(current)
        items_per_page.append(items_in_current)

    try:
        digit_idx = int(digit) - 1
    except:
        return -1
    if digit_idx < 0:
        return -1
    if digit_idx >= len(upgrades):
        return -1
    return digit_idx


def buy_tree_upgrade(upgrades, idx, *, auto=False, save=True):
    if not (0 <= idx < len(upgrades)):
        return False
    upg = upgrades[idx]
    if upgrades is INSPIRE_UPGRADES:
        owned, level = get_inspire_info(upg["id"])
    elif upgrades is AUTOMATION_UPGRADES:
        owned, level = get_automation_info(upg["id"])
    else:
        owned, level = get_concept_info(upg["id"])
    max_level = upg.get("max_level", 1)
    meta = tree_catalogue_meta(upgrades)
    pool_name = meta.get("pool_name", layer_name("archive"))
    pool_currency = meta.get("pool_currency", layer_currency_name("archive"))
    pool_suffix = meta.get("currency_suffix")
    suffix_text = f" {pool_suffix}" if pool_suffix else ""
    if level >= max_level:
        if not auto:
            msg = f"{upg['name']} is already at max level!"
            tmp = boxed_lines(
                [msg],
                title=f" {pool_name} ",
                pad_top=1,
                pad_bottom=1,
            )
            render_frame(tmp)
            time.sleep(0.7)
        return False
    cost = get_tree_cost(upg, current_level=level)
    pool_key = meta.get("holdings_key", "concepts")
    if game.get(pool_key, 0) < cost:
        if not auto:
            msg = f"Not enough {pool_currency} for {upg['name']} (cost {cost}{suffix_text})."
            tmp = boxed_lines(
                [msg],
                title=f" {pool_name} ",
                pad_top=1,
                pad_bottom=1,
            )
            render_frame(tmp)
            time.sleep(0.7)
        return False
    game[pool_key] -= cost
    applied_list_key = meta.get("applied_key", "concept_upgrades")
    applied = False
    for i, u in enumerate(game.get(applied_list_key, [])):
        if isinstance(u, dict) and u.get("id") == upg["id"]:
            u["level"] = u.get("level", 1) + 1
            applied = True
            break
        elif isinstance(u, str) and u == upg["id"]:
            game[applied_list_key][i] = {"id": u, "level": 2}
            applied = True
            break
    if not applied:
        game.setdefault(applied_list_key, []).append({"id": upg["id"], "level": 1})
    apply_inspiration_effects()
    apply_concept_effects()
    if applied_list_key == "automation_upgrades":
        apply_automation_effects()
    if upgrades is INSPIRE_UPGRADES and upg.get("type") in (
        "unlock_motivation",
        "motivation_cap",
        "motivation_strength",
    ):
        if game.get("motivation_unlocked", False):
            set_motivation(motivation_capacity())
    if save:
        save_game()
    if not auto:
        msg = f"Purchased {upg['name']} level {level + 1}!"
        tmp = boxed_lines(
            [msg],
            title=f" {pool_name} ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        # Cosmetic animation for this upgrade (if available)
        try:
            maybe_animate_upgrade(upg.get("id") if isinstance(upg, dict) else upg)
        except Exception:
            pass
        time.sleep(0.5)
    return True


def calculate_inspiration(money_since_reset):
    normalized = money_since_reset / 100_000
    base_gain = math.floor(((normalized**0.35) * math.log(normalized + 1, 1.5)))
    rate_mult = 1.0
    final_mult = 1.0
    for entry in game.get("inspiration_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in INSPIRE_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        base_val = float(u.get("base_value", u.get("value", 1)))
        val_mult = float(u.get("value_mult", 1))
        val = base_val * (val_mult ** max(0, (level - 1)))
        if u["type"] == "inspire_rate":
            rate_mult *= val
        elif u["type"] == "inspire_mult":
            final_mult *= val
    total = int(base_gain * rate_mult * final_mult)
    gain_mod = get_challenge_modifier("inspiration_gain_mult")
    if isinstance(gain_mod, (int, float)) and gain_mod > 0:
        total = int(max(0, round(total * gain_mod)))
    total = int(max(0, round(total * escape_multiplier())))
    return total


def calculate_concepts(money_since_reset):
    if money_since_reset <= 0:
        return 0
    normalized = money_since_reset / 400_000
    growth_curve = (normalized ** 0.42) * math.log(normalized + 1, 1.25)
    reset_bonus = max(1.0, (1 + game.get("concept_resets", 0)) ** 1.12)
    synergy_bonus = 1.0 + 0.08 * max(0, game.get("inspiration_resets", 0))
    base_gain = max(0, math.floor(growth_curve * reset_bonus * synergy_bonus))
    rate_mult = 1.0
    final_mult = 1.0
    for entry in game.get("concept_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in CONCEPT_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        base_val = float(u.get("base_value", u.get("value", 1)))
        val_mult = float(u.get("value_mult", 1))
        val = base_val * (val_mult ** max(0, (level - 1)))
        if u["type"] == "concept_rate":
            rate_mult *= val
        elif u["type"] == "concept_mult":
            final_mult *= val
            
                                                        
    if game.get("layer", 0) >= 2:
        signal_bonus = max(0.0, get_resonance_efficiency())
        final_mult *= 1.0 + signal_bonus
        
    total = int(base_gain * rate_mult * final_mult)
    gain_mod = get_challenge_modifier("concept_gain_mult")
    if isinstance(gain_mod, (int, float)) and gain_mod > 0:
        total = int(max(0, round(total * gain_mod)))
    total = int(max(0, round(total * escape_multiplier())))
    return total


def predict_next_inspiration_point():
    current_money = game.get("money_since_reset", 0)
    current_insp = calculate_inspiration(current_money)
    next_insp = current_insp + 1
    target_money = ((next_insp - 1) * 25) ** (1 / 0.4)
    remaining = round(max(target_money - current_money, 0), 2)
    return remaining


def predict_next_concept_point():
    current_money = game.get("money_since_reset", 0)
    current_conc = calculate_concepts(current_money)
    target = current_conc + 1
    if target <= 0:
        return 0
    if calculate_concepts(current_money) >= target:
        return 0
    low = int(current_money)
    high = max(low + 1, 1_000_000)
    cap = 10**18
    while calculate_concepts(high) < target and high < cap:
        high = min(high * 2, cap)
    lo = low + 1
    hi = high
    while lo < hi:
        mid = (lo + hi) // 2
        if calculate_concepts(mid) >= target:
            hi = mid
        else:
            lo = mid + 1
    remaining = max(lo - current_money, 0)
    return round(remaining, 2)


def wipe_to_inspiration_baseline(state):
    state.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "owned": [],
            "upgrade_levels": {},
            "inspiration_unlocked": True,
            "layer": max(state.get("layer", 0), 1),
            "motivation": config.MOTIVATION_MAX,
        }
    )


def reset_for_inspiration():
    now = time.time()
    if now - game.get("last_inspiration_reset_time", 0) < 0.05:
        return
    corridor_name = layer_name("corridor")
    corridor_currency = layer_currency_name("corridor")
    if not challenge_completed("stability_drill"):
        tmp = boxed_lines(
            [
                f"{corridor_name} is sealed.",
                "Complete S-CHAL-1 to unlock access.",
            ],
            title=f" {corridor_name} Locked ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(1.0)
        return
    if game.get("money_since_reset", 0) < INSPIRATION_UNLOCK_MONEY:
        tmp = boxed_lines(
            [
                f"{Fore.YELLOW}Reach {format_currency(INSPIRATION_UNLOCK_MONEY)} to enter {corridor_name}.{Style.RESET_ALL}"
            ],
            title=f" {corridor_name} ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(1.0)
        return
    gained = calculate_inspiration(game.get("money_since_reset", 0))
    play_inspiration_reset_animation()
    game["inspiration"] = game.get("inspiration", 0) + gained
    previous_resets = game.get("inspiration_resets", 0)
    wipe_to_inspiration_baseline(game)
    game["inspiration_resets"] = previous_resets + 1
    handle_machine_progress_event("inspiration")
    game["last_inspiration_reset_time"] = now
    attempt_reveal("layer_corridor")
    attempt_reveal("currency_corridor")
    if previous_resets == 0:
        attempt_reveal("currency_wake")
        attempt_reveal("ui_currency_clear")
        attempt_reveal("ui_upgrade_catalogue")
        set_settings_notice("Inspiration systems synced.", duration=3.0)
    refresh_knowledge_flags()
    apply_inspiration_effects()
    if game.get("motivation_unlocked", False):
        set_motivation(motivation_capacity())
    check_challenges("inspiration")
    save_game()
    done_msg = boxed_lines(
        [f"Gained {Fore.LIGHTYELLOW_EX}{gained}{Style.RESET_ALL} {corridor_currency}."],
        title=f" {corridor_name} Gained ",
        pad_top=1,
        pad_bottom=1,
    )
    render_frame(done_msg)
    global last_render
    last_render = ""
    time.sleep(1.0)


def wipe_to_concept_baseline(state):
    state.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "resonance_val": RESONANCE_START,
            "owned": [],
            "upgrade_levels": {},
            "concepts_unlocked": True,
            "layer": max(state.get("layer", 0), 2),
            "inspiration_upgrades": [],
            "inspiration": 0,
            "motivation": 0,
            "motivation_unlocked": False,
            "motivation_cap_bonus": 0,
            "motivation_strength_mult": 1.0,
        }
    )


def reset_for_concepts():
    global last_render
    now = time.time()
    if now - game.get("last_concepts_reset_time", 0) < 0.05:
        return
    archive_name = layer_name("archive")
    archive_currency = layer_currency_name("archive")
    if not concept_layer_gate_met():
        total = total_challenges_configured()
        completed = challenges_completed_count()
        remaining = max(0, total - completed)
        requirement = "Complete all challenges to enter the Echo."
        if total > 0:
            requirement = (
                f"Complete all {total} challenges to enter the Echo "
                f"({completed}/{total} cleared, {remaining} remaining)."
            )
        tmp = boxed_lines(
            ["Challenge lock detected.", requirement],
            title=" Challenge Lock ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        last_render = ""
        time.sleep(1.1)
        return
    if game.get("money_since_reset", 0) < CONCEPTS_UNLOCK_MONEY:
        tmp = boxed_lines(
            [f"Reach {format_currency(CONCEPTS_UNLOCK_MONEY)} to access {archive_name}."],
            title=f" {archive_name} ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        last_render = ""
        time.sleep(1.0)
        return
    gained = calculate_concepts(game.get("money_since_reset", 0))
    play_concepts_animation()
    game["concepts"] = game.get("concepts", 0) + gained
    wipe_to_concept_baseline(game)
    game["automation_upgrades"] = []
    game["automation_page"] = 0
    apply_automation_effects()
    game["concept_resets"] = game.get("concept_resets", 0) + 1
    handle_machine_progress_event("concept")
    ensure_challenge_feature()
    attempt_reveal("layer_archive")
    attempt_reveal("currency_archive")
    attempt_reveal("escape_signal")
    refresh_knowledge_flags()
    apply_concept_effects()
    apply_inspiration_effects()
    check_challenges("concept")
    save_game()
    done_msg = boxed_lines(
        [f"Gained {Fore.CYAN}{gained}{Style.RESET_ALL} {archive_currency}."],
        title=f" {archive_name} Gained ",
        pad_top=1,
        pad_bottom=1,
    )
    render_frame(done_msg)
    time.sleep(1.2)


def open_wake_timer_menu(auto_invoked=False):
    global KEY_PRESSED, last_render
    last_box = None
    last_size = get_term_size()
    while True:
        if not auto_invoked:
            work_tick()
        remaining = "∞" if game.get("wake_timer_infinite", False) else format_clock(game.get("wake_timer", WAKE_TIMER_START))
        lines = [
            "--- STABILIZER ---" if not game.get("wake_timer_infinite", False) else "--- TIMER SEALED ---",
            f"Remaining: {remaining}",
            f"Capacity: {format_clock(game.get('wake_timer_cap', WAKE_TIMER_START))}",
        ]
        if sparks_visible():
            lines.append(f"{STABILITY_CURRENCY_NAME}: {format_number(game.get('stability_currency', 0))}")
        else:
            lines.append("Sparks dormant until the Diverter calls for them.")
        lines.append("")
        if auto_invoked and not game.get("wake_timer_infinite", False):
            lines.append("Collapse complete. Spend sparks to anchor the loop.")
            lines.append("")
        levels = get_wake_upgrade_levels()
        for i, upg in enumerate(WAKE_TIMER_UPGRADES, start=1):
            uid = upg.get("id")
            current_level = levels.get(uid, 0)
            max_level = upg.get("max_level")
            if max_level and current_level >= max_level:
                status = "MAX"
            else:
                status = f"Cost {format_number(wake_upgrade_cost(upg, current_level))} {STABILITY_CURRENCY_NAME}"
            display_name = upg.get("name", upg.get("id", f"Upgrade {i}"))
            accent_name = upg.get("accent")
            accent = getattr(Fore, accent_name, Fore.CYAN)
            title_line = f"{accent}{i}. {display_name}{Style.RESET_ALL}"
            level_line = f"   Lv {current_level} — {status}"
            lines.append(title_line)
            lines.append(level_line)
            desc = upg.get("desc")
            if desc:
                lines.append(f"   {desc}")
            bonus_bits = []
            next_time = wake_upgrade_next_bonus(upg, current_level, "time_bonus", "time_bonus_scale")
            total_time = wake_upgrade_total_bonus(upg, current_level, "time_bonus", "time_bonus_scale")
            if next_time > 0 and (not max_level or current_level < max_level):
                bonus_bits.append(
                    f"+{int(round(next_time))}s (Σ {int(round(total_time))}s)"
                )
            elif total_time > 0:
                bonus_bits.append(f"Σ +{int(round(total_time))}s")
            reward_step = wake_upgrade_next_bonus(upg, current_level, "stability_bonus", "stability_bonus_scale")
            reward_total = wake_upgrade_total_bonus(upg, current_level, "stability_bonus", "stability_bonus_scale")
            if reward_step > 0:
                bonus_bits.append(
                    f"Sparks +{reward_step * 100:.1f}% (Σ {reward_total * 100:.1f}%)"
                )
            elif reward_total > 0:
                bonus_bits.append(f"Sparks Σ +{reward_total * 100:.1f}%")
            extras = []
            if upg.get("grant_infinite"):
                required = max(1, int(upg.get("infinite_level", 1)))
                if current_level < required:
                    remaining_installs = required - current_level
                    extras.append(f"Seal in {remaining_installs} install(s)")
                else:
                    extras.append("Window sealed; extra installs boost Sparks")
            if upg.get("unlock_upgrades"):
                extras.append("Unlocks upgrade bay")
            if upg.get("unlock_challenges"):
                extras.append("Unlocks challenges")
            if bonus_bits:
                lines.append(
                    f"   {Style.DIM}{' | '.join(bonus_bits)}{Style.RESET_ALL}"
                )
            if extras:
                lines.append(
                    f"   {Style.DIM}{' | '.join(extras)}{Style.RESET_ALL}"
                )
            lines.append("")
        lines += ["Press number to install, B to back."]
        box = boxed_lines(lines, title=" Stabilize ", pad_top=1, pad_bottom=1)
        cur_size = get_term_size()
        box_str = "\n".join(box)
        if box_str != last_box or cur_size != last_size:
            render_frame(box)
            last_box = box_str
            last_size = cur_size
        time.sleep(0.05)
        if KEY_PRESSED:
            k_input = KEY_PRESSED
            KEY_PRESSED = None
            try:
                k = k_input.lower()
            except Exception:
                continue
            if k == "b":
                last_render = ""
                return
            if k.isdigit():
                idx = int(k) - 1
                if 0 <= idx < len(WAKE_TIMER_UPGRADES):
                    message = buy_wake_timer_upgrade(WAKE_TIMER_UPGRADES[idx])
                    tmp = boxed_lines([message], title=" Stabilize ", pad_top=1, pad_bottom=1)
                    render_frame(tmp)
                    time.sleep(0.8)


def buy_wake_timer_upgrade(upg):
    uid = upg.get("id")
    levels = get_wake_upgrade_levels()
    current_level = levels.get(uid, 0)
    max_level = upg.get("max_level")
    if max_level and current_level >= max_level:
        return f"{upg['name']} fully calibrated."
    cost = wake_upgrade_cost(upg, current_level)
    if game.get("stability_currency", 0) < cost:
        return f"Need {format_number(cost)} {STABILITY_CURRENCY_NAME} to install {upg['name']}"
    game["stability_currency"] -= cost
    new_level = current_level + 1
    levels[uid] = new_level
    game["wake_timer_upgrades"] = dict(levels)
    extras = []
    if upg.get("unlock_upgrades") and current_level == 0 and not game.get("upgrades_unlocked", False):
        game["upgrades_unlocked"] = True
        extras.append("Upgrade bay rebooted.")
    if upg.get("unlock_challenges") and current_level == 0 and not game.get("challenge_instability_installed", False):
        game["challenge_instability_installed"] = True
        extras.append("Challenge board online.")
        ensure_challenge_feature()
    if upg.get("grant_infinite"):
        required = max(1, int(upg.get("infinite_level", 1)))
        if current_level < required <= new_level:
            register_phase_lock_completion()
    recalc_wake_timer_state()
    game["wake_timer"] = game.get("wake_timer_cap", WAKE_TIMER_START)
    game["wake_timer_locked"] = False
    game["wake_timer_notified"] = False
    save_game()
    if game.get("wake_timer_infinite", False):
        base_msg = f"{upg['name']} Lvl {new_level} sealed the loop. Time is yours now."
    else:
        base_msg = f"{upg['name']} calibrated to Lvl {new_level}. Stability restored."
    if extras:
        base_msg += " " + " ".join(extras)
    return base_msg


def upgrade_is_visible(upgrade):
    if not upgrade:
        return False
    uid = upgrade.get("id")
    owned_ids = set(game.get("owned", []))
    auto_ready = game.get("auto_work_unlocked", False)
    if (
        upgrade.get("type") in AUTO_ONLY_UPGRADE_TYPES
        and uid not in owned_ids
        and not auto_ready
    ):
        return False
    return True


def open_upgrade_menu():
    global KEY_PRESSED, last_render
    if not game.get("upgrades_unlocked", False):
        tmp = boxed_lines(
            [
                "The upgrade bay is dark.",
                f"Restore power via the Stabilizer console ({STABILITY_CURRENCY_NAME}).",
            ],
            title=" Upgrade Bay Offline ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(1.2)
        return
    game.setdefault("upgrade_page", 0)
    last_box = None
    last_size = get_term_size()
    while True:
        work_tick()
        catalogue_known = is_known("ui_upgrade_catalogue")
        unlocked = []
        owned_items = game.get("owned", [])
        for u in config.UPGRADES:
            if not upgrade_is_visible(u):
                continue
            deps = config.UPGRADE_DEPENDENCIES.get(u["id"], [])
            if u.get("unlocked", False) or all(dep in owned_items for dep in deps):
                unlocked.append(u)
        money_available = game.get("money", 0)
        current_money = format_currency(money_available)
        term_w, term_h = get_term_size()
        box_w = max(config.MIN_BOX_WIDTH, term_w - config.BOX_MARGIN * 2)
        inner_w = box_w - 2
        desc_width = max(int(inner_w * 0.5), 30)
        max_content_lines = max(12, term_h - 12)

        header_lines = [
            "--- UPGRADE BAY ---" if catalogue_known else "--- [REDACTED] ---",
            f"Money: {Fore.CYAN}{current_money}{Style.RESET_ALL}",
            "",
        ]

        blocks = []
        for i, u in enumerate(unlocked, start=1):
            level = game.get("upgrade_levels", {}).get(u["id"], 0)
            max_level = u.get("max_level", 1)
            cost = int(u.get("cost", 0) * (u.get("cost_mult", 1) ** level))
            affordable = money_available >= cost
            uid = u["id"]
            known_upgrade = catalogue_known or is_known(f"upgrade_{uid}")
            display_name = u["name"] if known_upgrade else veil_text(u["name"])

            if level >= max_level:
                title_color = Fore.GREEN
            elif affordable:
                title_color = Fore.CYAN
            else:
                title_color = Fore.RED

            block = [
                f"{title_color}{i}. {display_name}{Style.RESET_ALL}",
                f"    {Fore.YELLOW}Lv {level}/{max_level}{Style.RESET_ALL}",
            ]
            if level >= max_level:
                block.append(
                    f"    {Fore.GREEN}MAXED{Style.RESET_ALL}"
                )
            else:
                block.extend(
                    [
                        f"    Cost: {Fore.CYAN}{format_currency(cost)}{Style.RESET_ALL}",
                        f"    Wallet: {Fore.CYAN}{format_currency(money_available)}{Style.RESET_ALL}",
                    ]
                )

            art_key = u.get("art", uid)
            art_lines = UPGRADE_ART.get(art_key, [])
            if art_lines:
                block.extend([
                    "    " + Style.DIM + art + Style.RESET_ALL for art in art_lines
                ])

            if u.get("desc") and known_upgrade:
                effect_text = f"→ {u['desc']}"
                base_val = float(u.get("base_value", u.get("value", 1)))
                val_mult = float(u.get("value_mult", 1))
                val = base_val * (val_mult ** max(0, level - 1))
                if u["type"] in ("mult", "money_mult"):
                    effect_text += f" (x{val:.2f} income)"
                elif u["type"] in ("work_mult", "reduce_delay"):
                    effect_text += f" (×{val:.2f} delay)"
                elif u["type"] == "add":
                    effect_text += f" (+{val:.2f} flat)"
                elif u["type"] == "time_velocity_mult":
                    effect_text += f" (x{val:.2f} time velocity)"
                wrapped = wrap_ui_text(effect_text, width=desc_width, reserved=4)
                block.extend(
                    [f"    {Fore.LIGHTBLACK_EX}{w}{Style.RESET_ALL}" for w in wrapped]
                )
            if i < len(unlocked):
                block.append(
                    f"    {Fore.LIGHTBLACK_EX}{'─' * max(20, desc_width // 2)}{Style.RESET_ALL}"
                )
            blocks.append(block)

        pages = []
        current_block_lines = []
        used_lines = 0
        for block in blocks:
            block_len = len(block)
            if current_block_lines and used_lines + block_len > max_content_lines:
                pages.append(current_block_lines)
                current_block_lines = []
                used_lines = 0
            current_block_lines.extend(block)
            used_lines += block_len
        if current_block_lines or not pages:
            pages.append(current_block_lines)

        total_pages = len(pages)
        page_idx = min(game.get("upgrade_page", 0), total_pages - 1)
        page_idx = max(0, page_idx)
        game["upgrade_page"] = page_idx
        visible_lines = pages[page_idx] if pages else []

        lines = header_lines[:]
        if visible_lines:
            lines.extend(visible_lines)
        else:
            lines.append("No upgrades available.")

        page_hint = f"Page {page_idx + 1}/{max(1, total_pages)}  (Z/X to scroll)"
        lines += ["", page_hint, "Press number to buy, Z/X to scroll, B to back."]
        page_count = total_pages
        box = boxed_lines(lines, title=" UPGRADE BAY ", pad_top=1, pad_bottom=1)
        cur_size = get_term_size()
        box_str = "\n".join(box)
        if box_str != last_box or cur_size != last_size:
            render_frame(box)
            last_box = box_str
            last_size = cur_size
        time.sleep(0.05)
        if KEY_PRESSED:
            k = KEY_PRESSED.lower()
            KEY_PRESSED = None
            if k == "b":
                last_render = ""
                return
            elif k == "z":
                if page_count > 1:
                    game["upgrade_page"] = max(0, game["upgrade_page"] - 1)
                continue
            elif k == "x":
                if page_count > 1:
                    game["upgrade_page"] = min(page_count - 1, game["upgrade_page"] + 1)
                continue
            elif k.isdigit():
                idx = int(k) - 1
                if 0 <= idx < len(unlocked):
                    buy_idx_upgrade(unlocked[idx])
                    last_box = None
                    continue


def buy_idx_upgrade(upg):
    uid = upg["id"]
    game.setdefault("owned", [])
    game.setdefault("upgrade_levels", {})
    current_level = game["upgrade_levels"].get(uid, 0)
    max_level = upg.get("max_level", 1)
    scaled_cost = int(upg["cost"] * (upg.get("cost_mult", 1) ** current_level))

    if current_level >= max_level:
        msg = f"{upg['name']} is already maxed (Lv {current_level}/{max_level})."
    elif game.get("money", 0) < scaled_cost:
        msg = f"Not enough money for {upg['name']} (cost {format_currency(scaled_cost)})."
    else:
        game["money"] -= scaled_cost
        current_level += 1
        game["upgrade_levels"][uid] = current_level
        if uid not in game["owned"]:
            game["owned"].append(uid)
        if not game.get("upgrades_unlocked", False):
            game["upgrades_unlocked"] = True
        mark_known(f"upgrade_{uid}")
        if upg.get("type") == "unlock_rpg" and current_level > 0:
            game["rpg_unlocked"] = True
        msg = f"Purchased {upg['name']} (Lv {current_level}/{max_level})."
    tmp = boxed_lines([msg], title=" UPGRADE BAY ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    # Try to animate the purchased upgrade (cosmetic)
    try:
        maybe_animate_upgrade(uid)
    except Exception:
        pass
    time.sleep(0.7)
    save_game()


def play_inspiration_reset_animation():
    term_w, term_h = get_term_size()
    corridor_name = layer_name("corridor")
    corridor_currency = layer_currency_name("corridor")
    corridor_height = max(8, min(term_h - 4, 18))
    frames = corridor_height * 2
    shimmer_chars = [" ", ".", "·", ":"]

    for frame in range(frames):
        clear_screen()
        lines = []
        depth_shift = max(0, frame - corridor_height)
        for depth in range(corridor_height):
            pad = depth * 2 + depth_shift
            inner = term_w - pad * 2 - 2
            if inner <= 0:
                continue
            filler = shimmer_chars[(depth + frame) % len(shimmer_chars)] * inner
            if depth % 2 == 0:
                left, right = "|", "|"
            else:
                left, right = "/", "\\"
            color = Fore.LIGHTYELLOW_EX if depth > corridor_height // 2 else Fore.WHITE
            line = " " * pad + f"{color}{left}{filler}{right}{Style.RESET_ALL}"
            lines.append(line[:term_w])

        caption = ansi_center(
            f"{Fore.LIGHTYELLOW_EX}{corridor_name} reset in progress...{Style.RESET_ALL}",
            term_w,
        )
        lines.append("")
        lines.append(caption)
        lines.append(
            ansi_center(
                f"{Fore.YELLOW}Hold steady. {corridor_currency} condensing.{Style.RESET_ALL}",
                term_w,
            )
        )
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        time.sleep(0.08)

    clear_screen()
    flash = ansi_center(
        f"{Fore.WHITE}>>> {corridor_name} Passage Engaged <<<{Style.RESET_ALL}", term_w
    )
    sys.stdout.write("\n" * max(term_h // 2 - 1, 0) + flash + "\n")
    sys.stdout.flush()
    time.sleep(0.7)


def play_concepts_animation():
    term_w, term_h = get_term_size()
    archive_name = layer_name("archive")
    archive_currency = layer_currency_name("archive")
    rows = max(10, term_h - 4)
    frames = rows + 12
    amplitude = max(6, term_w // 6)

    for frame in range(frames):
        clear_screen()
        lines = []
        for row in range(rows):
            phase = frame * 0.25 + row * 0.35
            offset = int(math.sin(phase) * amplitude)
            center = term_w // 2 + offset
            color = Fore.CYAN if (row + frame) % 2 == 0 else Fore.BLUE
            glyph = "~" if row % 3 else "-"
            if 0 <= center < term_w:
                left = " " * center
                right = " " * max(term_w - center - 1, 0)
                line = f"{left}{color}{glyph}{Style.RESET_ALL}{right}"
            else:
                line = " " * term_w
            lines.append(line)

        lines.append("")
        lines.append(
            ansi_center(
                f"{Fore.CYAN}{archive_currency} braid themselves into blueprints...{Style.RESET_ALL}",
                term_w,
            )
        )
        lines.append(
            ansi_center(
                f"{Fore.LIGHTBLUE_EX}{archive_name} crystallizes. Stability trembles.{Style.RESET_ALL}",
                term_w,
            )
        )
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        time.sleep(0.07)

    clear_screen()
    flash = ansi_center(
        f"{Fore.CYAN}>>> {archive_name} Resonance Captured <<<{Style.RESET_ALL}", term_w
    )
    sys.stdout.write("\n" * max(term_h // 2 - 1, 0) + flash + "\n")
    sys.stdout.flush()
    time.sleep(0.9)


def open_blackjack_layer():
    global listener_enabled, last_render, view_offset_x, view_offset_y

    listener_enabled = False
    clear_screen()

    starting_money = float(game.get("money", 0.0))
    try:
        print("Entering blackjack casino...\n")
        print(f"Carrying {format_currency(starting_money)} from the main game.\n")
        new_money = blackjack.run_blackjack(starting_money)
        game["money"] = max(0.0, float(new_money))
        save_game()
    except Exception as e:
        err_lines = [
            "Blackjack crashed. Returning to main game.",
            f"Error: {e!r}",
        ]
        tmp = boxed_lines(err_lines, title=" Casino Error ", pad_top=1, pad_bottom=1)
        render_frame(tmp)
        time.sleep(1.5)
    finally:
        listener_enabled = True
        last_render = ""
        view_offset_x = 0
        view_offset_y = 0
        clear_screen()


def key_listener():
    global KEY_PRESSED, running, listener_enabled
    if msvcrt is not None and os.name == "nt":
        while running:
            if not listener_enabled:
                time.sleep(0.02)
                continue
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch:
                    try:
                        KEY_PRESSED = ch.lower()
                    except:
                        KEY_PRESSED = None
            time.sleep(0.02)
    else:
        import tty, termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while running:
                if not listener_enabled:
                    time.sleep(0.02)
                    continue
                r, _, _ = select.select([sys.stdin], [], [], 0)
                if r:
                    ch = sys.stdin.read(1)
                    if ch:
                        if ch == "\x1b":
                            rest = ""
                            while True:
                                r2, _, _ = select.select([sys.stdin], [], [], 0.02)
                                if r2:
                                    more = sys.stdin.read(1)
                                    if not more:
                                        break
                                    rest += more
                                else:
                                    break
                            KEY_PRESSED = ch + rest
                        else:
                            KEY_PRESSED = ch.lower()
                time.sleep(0.02)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def get_screen_tabs():
    tabs = [("work", layer_name("wake", "Main Realm"))]
    if breach_door_is_open() or game.get("rpg_unlocked", False):
        tabs.append(("rpg", "Room"))
    tabs.append(("settings", "Settings"))
    return tabs


def build_tab_bar_text(current_screen):
    tabs = get_screen_tabs()
    if not tabs:
        return ""
    parts = []
    for screen_id, label in tabs:
        label = label or screen_id.title()
        if screen_id == current_screen:
            parts.append(f"{Back.WHITE}{Fore.BLACK} {label} {Style.RESET_ALL}")
        else:
            parts.append(f"{Fore.WHITE}{label}{Style.RESET_ALL}")
    return "  ".join(parts)


def cycle_screen(current_screen, direction):
    tabs = [tab[0] for tab in get_screen_tabs()]
    if not tabs:
        return current_screen
    if current_screen not in tabs:
        return tabs[0]
    idx = tabs.index(current_screen)
    idx = (idx + direction) % len(tabs)
    return tabs[idx]


def render_ui(screen="work"):
    global last_render, last_size, view_offset_x, view_offset_y, Fore
    term_w, term_h = get_term_size()
    current_size = get_term_size()
    resized = current_size != last_size
    auto_ready = auto_work_allowed()
    effective_gain, effective_delay = compute_gain_and_delay(auto=auto_ready)
    prog = (
        min(work_timer / effective_delay, 1.0)
        if auto_ready
        else 0
    )
    bar_len = 36
    filled = int(prog * bar_len)
    work_bar = f"[{'#' * filled}{'-' * (bar_len - filled)}] {int(prog * 100):3d}%"

    if screen == "settings":
        settings_lines = build_settings_lines()
        term_width, term_height = get_term_size()
        padding = max(0, term_height - 4 - len(settings_lines))
        settings_lines += [""] * padding
        tab_line = build_tab_bar_text(screen)
        layer_title = f" {tab_line} " if tab_line else " Settings "
        box = boxed_lines(settings_lines, title=layer_title, pad_top=2, pad_bottom=2)
        view_offset_x = 0
        view_offset_y = 0
        if resized:
            print("\033[2J\033[H", end="")
            last_size = current_size
            last_render = ""
        frame = "\033[H" + "\n".join(box[: term_height])
        if frame != last_render:
            sys.stdout.write(frame)
            sys.stdout.flush()
            last_render = frame
        return

    top_left_lines = []
    bottom_left_lines = []
    middle_lines = []
    insp_title = conc_title = insp_tree_title = conc_tree_title = ""
    status_line = None
    mot_pct = None
    mot_mult = None

    if screen != "settings":
        total_earnings = game.get("money_since_reset", 0)
        wallet_money = max(0.0, game.get("money", 0.0))
        calc_insp = calculate_inspiration(total_earnings)
        calc_conc = calculate_concepts(total_earnings)
        time_next = predict_next_inspiration_point()
        conc_time_next = predict_next_concept_point()

        corridor_name = layer_name("corridor")
        corridor_currency = layer_currency_name("corridor")
        archive_name = layer_name("archive")
        archive_currency = layer_currency_name("archive")
        insp_title = f"=== {Fore.LIGHTYELLOW_EX}{corridor_name}{Style.RESET_ALL} ==="
        insp_tree_title = (
            f"=== {Fore.LIGHTYELLOW_EX}{corridor_name} board{Style.RESET_ALL} ==="
        )
        conc_title = f"=== {Fore.CYAN}{archive_name}{Style.RESET_ALL} ==="
        conc_tree_title = f"=== {Fore.CYAN}{archive_name} board{Style.RESET_ALL} ==="

        time_panel = build_timeflow_focus_lines()
        if time_panel:
            top_left_lines += time_panel + [""]

        inspiration_panel_visible = bool(
            game.get("inspiration_unlocked", False) or game.get("inspiration_resets", 0) > 0
        )
        corridor_gate_cleared = challenge_completed("stability_drill")
        if inspiration_panel_visible:
            top_left_lines += [
                insp_title,
                "",
                f"Holdings: {Fore.LIGHTYELLOW_EX}{format_number(game.get('inspiration', 0))}{Style.RESET_ALL} {corridor_currency}",
            ]
            if total_earnings >= INSPIRATION_UNLOCK_MONEY:
                top_left_lines.append(
                    f"[I] Step into {corridor_name} for {Fore.LIGHTYELLOW_EX}{format_number(calc_insp)}{Style.RESET_ALL} {corridor_currency}"
                )
                top_left_lines.append(
                    f"{Fore.LIGHTYELLOW_EX}{format_number(time_next)}{Style.RESET_ALL} until next {corridor_currency}"
                )
            else:
                top_left_lines.append(
                    f"Reach {format_currency(INSPIRATION_UNLOCK_MONEY)} to approach {corridor_name}."
                )
            top_left_lines.append(f"[1] Open {corridor_name} board")
            if screen == "inspiration":
                visible_lines, footer, _ = build_tree_lines(
                    INSPIRE_UPGRADES, get_inspire_info, "insp_page"
                )
                top_left_lines += [
                    "",
                    insp_tree_title,
                    *visible_lines,
                    "",
                    footer,
                    "",
                    "\033[1m[B] Back to Work\033[0m",
                ]
        else:
            if corridor_gate_cleared:
                top_left_lines.append(
                    f"{Fore.LIGHTYELLOW_EX}{corridor_name}{Style.RESET_ALL} awaits. Reach {format_currency(INSPIRATION_UNLOCK_MONEY)} then press [I] to reset."
                )
            else:
                top_left_lines.append(
                    f"{Fore.LIGHTBLACK_EX}Complete S-CHAL-1 to unlock {corridor_name}.{Style.RESET_ALL}"
                )

        if game.get("motivation_unlocked", False):
            cap = motivation_capacity()
            peak = motivation_peak_multiplier()
            mot = max(0, min(cap, game.get("motivation", cap)))
            mot_ratio = mot / max(1, cap)
            mot_mult = 1 + mot_ratio * (peak - 1)
            mot_pct = int(round(mot_ratio * 100))
            top_left_lines += [
                "",
                f"Motivation: {Fore.GREEN}{round(mot_pct, 0)}%{Style.RESET_ALL} ({mot}/{cap})  x{mot_mult:.2f}",
            ]

        concept_panel_visible = bool(
            game.get("concepts_unlocked", False) or game.get("concept_resets", 0) > 0
        )
        if concept_panel_visible:
            bottom_left_lines += [
                conc_title,
                "",
            ]
            if game.get("concepts_unlocked", False):
                bottom_left_lines.append(
                    f"Holdings: {Fore.CYAN}{format_number(game.get('concepts', 0))}{Style.RESET_ALL} {archive_currency}"
                )
                bottom_left_lines.append(build_resonance_bar())
                rpg_depth = game.get("rpg_data", {}).get("floor", 1)
                bottom_left_lines.append(f"Loop Depth: Floor {rpg_depth}")
                bottom_left_lines.append("")
            if total_earnings >= CONCEPTS_UNLOCK_MONEY:
                bottom_left_lines.append(
                    f"[C] Enter {archive_name} for {Fore.CYAN}{format_number(calc_conc)}{Style.RESET_ALL} {archive_currency}"
                )
                bottom_left_lines.append(
                    f"{Fore.CYAN}{format_number(conc_time_next)}{Style.RESET_ALL} until next {archive_currency}"
                )
                bottom_left_lines.append("")
                bottom_left_lines.append(f"[2] Open {archive_name} board")
            else:
                bottom_left_lines.append(
                    f"Reach {format_currency(CONCEPTS_UNLOCK_MONEY)} to decipher {archive_name}."
                )
                bottom_left_lines.append("")
                bottom_left_lines.append(f"[2] Open {archive_name} board")
            if not concept_layer_gate_met() and CHALLENGES:
                total = total_challenges_configured()
                completed = challenges_completed_count()
                gate_hint = (
                    f"Complete challenges ({completed}/{total}) to unlock {archive_name}."
                    if total
                    else "Complete the current challenge list to unlock the Echo."
                )
                bottom_left_lines.append(
                    f"{Fore.LIGHTBLACK_EX}{gate_hint}{Style.RESET_ALL}"
                )
            if screen == "concepts":
                visible_lines, footer, _ = build_tree_lines(
                    CONCEPT_UPGRADES, get_concept_info, "concept_page"
                )
                bottom_left_lines += [
                    "",
                    conc_tree_title,
                    *visible_lines,
                    "",
                    footer,
                    "\033[1m[B] Back to Work\033[0m",
                ]
        elif inspiration_panel_visible:
            bottom_left_lines.append(
                f"{Fore.LIGHTBLACK_EX}Clear every challenge to unlock {archive_name}.{Style.RESET_ALL}"
            )

        if automation_lab_available():
            auto_entries = game.get("automation_upgrades", [])
            owned_nodes = len(auto_entries)
            invested = sum(
                max(1, int(entry.get("level", 1))) if isinstance(entry, dict) else 1
                for entry in auto_entries
            )
            total_nodes = max(1, len(AUTOMATION_UPGRADES))
            auto_title = f"=== {Fore.MAGENTA}Automation Lab{Style.RESET_ALL} ==="
            bottom_left_lines += [
                "",
                auto_title,
                f"Ranks invested: {invested}  Nodes unlocked: {owned_nodes}/{total_nodes}",
                f"Signal Bits: {Fore.LIGHTMAGENTA_EX}{format_number(game.get('automation_currency', 0))}{Style.RESET_ALL}",
            ]
            if screen == "automation":
                exchange_panel = build_signal_exchange_panel()
                auto_buyer_panel = build_auto_buyer_panel()
                auto_lines, auto_footer, _ = build_tree_lines(
                    AUTOMATION_UPGRADES, get_automation_info, "automation_page"
                )
                bottom_left_lines += [
                    "",
                    *exchange_panel,
                    "",
                    *auto_buyer_panel,
                    "",
                    *auto_lines,
                    "",
                    auto_footer
                    + (
                        "  [E] Exchange  [R] Custom"
                        if automation_online()
                        else ""
                    ),
                    "\033[1m[B] Back to Work\033[0m",
                ]
            else:
                bottom_left_lines.append("[3] Open Automation Lab")

        bottom_left_lines += build_breach_door_lines()

        status_line = build_status_ribbon(calc_insp, calc_conc, mot_pct, mot_mult)
        challenge_line = build_challenge_summary_line()

        middle_lines = []
        time_hint_line = build_time_hint_line()
        if time_hint_line:
            middle_lines.append(time_hint_line)
        guide_hint_line = guide_hotkey_hint()
        if guide_hint_line:
            middle_lines.append(guide_hint_line)
        if game.get("escape_machine_unlocked", False):
            machine = escape_machine_state()
            if machine.get("ready") and not machine.get("applied"):
                middle_lines.append(
                    f"{Fore.LIGHTGREEN_EX}Reality Diverter ready — press [M].{Style.RESET_ALL}"
                )
            else:
                middle_lines.append(
                    f"{Fore.CYAN}Reality Diverter schematics tracked — press [M].{Style.RESET_ALL}"
                )
        if middle_lines:
            middle_lines.append("")
        if status_line:
            middle_lines.append(status_line)
        if challenge_line:
            middle_lines.append(challenge_line)
        reset_hint = challenge_reset_hint()
        if reset_hint:
            middle_lines.append(reset_hint)
        if status_line or challenge_line or reset_hint:
            middle_lines.append("")
        middle_lines.append(build_wake_timer_line())
        if not game.get("wake_timer_infinite", False):
            if sparks_visible():
                sparks_amount = format_number(game.get("stability_currency", 0))
                middle_lines.append(
                    f"{STABILITY_CURRENCY_NAME}: {Fore.MAGENTA}{sparks_amount}{Style.RESET_ALL}"
                )
            middle_lines.append("[T] Stabilize window")
            if manual_collapse_available():
                if instability_challenge_active():
                    middle_lines.append("[L] Collapse now (trial-only)")
                else:
                    upgrade_name, _ = manual_reset_requirement()
                    middle_lines.append(f"[L] Collapse now ({upgrade_name})")
        if automation_lab_available():
            signal_amount = format_number(game.get("automation_currency", 0))
            middle_lines.append(
                f"{AUTOMATION_CURRENCY_NAME}: {Fore.LIGHTMAGENTA_EX}{signal_amount}{Style.RESET_ALL}"
            )
        middle_lines.append("")
        middle_lines += render_desk_table()
        total_money = total_earnings
        mystery_phase = total_money < 100

        show_money = total_money >= 10
        show_gain = total_money >= 30

        wake_currency = layer_currency_name("wake")
        base_money = game.get("money", 0)
        money_str = (
            f"{wake_currency}: {format_currency(base_money)}"
            if show_money
            else f"{wake_currency}: ???"
        )

        gain_segment = ""
        if show_gain or not mystery_phase:
            gain_segment = f"   GAIN: {format_currency(effective_gain)} / cycle"
            if game.get("settings_show_signal_debug", False) and resonance_system_active():
                signal_mult = max(0.0, game.get("signal_multiplier", 1.0))
                gain_segment += f"  [Signal ×{signal_mult:.2f}]"
        delay_segment = (
            f"   DELAY: {effective_delay:.2f}s"
            if (not mystery_phase and game.get("auto_work_unlocked", False))
            else ""
        )
        middle_lines.append(f"{money_str}{gain_segment}{delay_segment}".rstrip())

        if show_money:
            middle_lines.append(work_bar)
        else:
            middle_lines.append("")

        work_prompt = reveal_text("ui_work_prompt", "Hold W to work", "Hold W...")
        auto_prompt = reveal_text("ui_auto_prompt", "Automation: ONLINE", "Automation: ???")
        if game.get("auto_work_unlocked", False):
            middle_lines.append(auto_prompt)
        else:
            middle_lines.append(work_prompt)

        option_payload = "Options: [W] Work  "
        if game.get("upgrades_unlocked", False):
            option_payload += "[U] Upgrades  "
        else:
            option_payload += "[U] Offline  "
        option_payload += "[J] Blackjack  "
        if automation_lab_available():
            option_payload += "[3] Automation  "
        option_payload += "[Q] Quit  [V] Credits"
        options_known = is_known("ui_options_full")
        if mystery_phase and not options_known:
            option_line = reveal_text(
                "ui_options_hint", "Options: [W] Work  [Q] Quit", "Options: [W] ???"
            )
            if game.get("upgrades_unlocked", False):
                option_line += "  [U] ???"
        else:
            option_line = option_payload if options_known else veil_text(option_payload)
        middle_lines += ["", option_line]
        if len(get_screen_tabs()) > 1:
            labels = " / ".join(label or sid.title() for sid, label in get_screen_tabs())
            middle_lines.append(
                f"{Fore.YELLOW}Use , and . to switch views ({labels}).{Style.RESET_ALL}"
            )
        if wake_timer_blocked():
            if sparks_visible():
                middle_lines.append("(Unconscious) Spend Sparks in Stabilize menu (T).")
            else:
                middle_lines.append("(Unconscious) Stabilizer offline until Diverter prep resumes.")
        elif not game.get("upgrades_unlocked", False):
            middle_lines.append("??? offline.")

    term_width, term_height = get_term_size()
    raw_escape_banner = build_escape_banner_lines(term_width)
    raw_banner_line = build_time_banner_line(term_width)
    max_banner_lines = len(raw_escape_banner) + (1 if raw_banner_line else 0)
    content_height = min(term_height, max(4, term_height - max_banner_lines))
    inner_target = max(0, content_height - 4)

    left_w = max(18, int(term_width * 0.25))
    mid_w = max(24, int(term_width * 0.35))
    right_w = max(18, int(term_width * 0.25))
    desired_shift = max(4, int(term_width * 0.03))
    remaining_shift = desired_shift
    steal = min(remaining_shift, max(0, mid_w - 24))
    mid_w -= steal
    remaining_shift -= steal
    if remaining_shift > 0:
        steal = min(remaining_shift, max(0, left_w - 18))
        left_w -= steal
        remaining_shift -= steal
    actual_shift = desired_shift - remaining_shift
    right_w += actual_shift
    left_pad = 2
    right_pad = 2

    def _ljust_with_buffer(text, box_w, pad_left):
        content_w = max(0, box_w - pad_left)
        t = text
        if visible_len(t) > content_w:
            t = ansi_visible_slice(t, 0, content_w)
        vis = visible_len(t)
        pad_right = max(0, content_w - vis)
        return " " * pad_left + t + " " * pad_right

    left_content_w = max(0, left_w - left_pad)
    right_content_w = max(0, right_w - left_pad)

    def wrap_panel_lines(lines, width, exempt_titles):
        if width <= 0:
            return list(lines)
        wrapped = []
        for entry in lines:
            if not entry:
                wrapped.append("")
                continue
            if entry in exempt_titles:
                wrapped.append(entry)
                continue
            segments = wrap_visible_text(entry, width)
            if not segments:
                wrapped.append("")
            else:
                wrapped.extend(segments)
        return wrapped

    title_set = {t for t in (insp_title, insp_tree_title, conc_title, conc_tree_title) if t}
    top_left_lines = wrap_panel_lines(top_left_lines, left_content_w, title_set)
    bottom_left_lines = wrap_panel_lines(bottom_left_lines, right_content_w, title_set)

    while len(top_left_lines) < inner_target:
        top_left_lines.append("")
    while len(bottom_left_lines) < inner_target:
        bottom_left_lines.append("")
    while len(middle_lines) < inner_target:
        middle_lines.insert(0, "")

    column_height = max(inner_target, len(top_left_lines), len(middle_lines), len(bottom_left_lines))

    def pad_column(lines, target, pad_front=False):
        while len(lines) < target:
            if pad_front:
                lines.insert(0, "")
            else:
                lines.append("")

    pad_column(top_left_lines, column_height)
    pad_column(bottom_left_lines, column_height)
    pad_column(middle_lines, column_height, pad_front=True)

    combined_lines = []
    for idx in range(column_height):
        l = top_left_lines[idx]
        m = middle_lines[idx]
        r = bottom_left_lines[idx]
        if l in (insp_title, insp_tree_title, conc_title, conc_tree_title):
            left_part = " " * left_pad + ansi_center(l, left_content_w)
        else:
            left_part = _ljust_with_buffer(l, left_w, left_pad)
        mid_part = ansi_center(m, mid_w)
        if r in (insp_title, insp_tree_title, conc_title, conc_tree_title):
            right_part = " " * left_pad + ansi_center(r, right_content_w)
        else:
            right_part = _ljust_with_buffer(r, right_w, left_pad)
        combined_lines.append(
            left_part + " " * right_pad + mid_part + " " * right_pad + right_part
        )

    max_scroll = max(0, len(combined_lines) - inner_target)
    view_offset_y = max(0, min(view_offset_y, max_scroll))
    window_lines = combined_lines[view_offset_y : view_offset_y + inner_target]
    
    tab_line = build_tab_bar_text(screen)
    if tab_line:
        layer_title = f" {tab_line} "
    else:
        layer_title = f" {current_layer_label()} "
    box = boxed_lines(
        window_lines, title=layer_title, pad_top=1, pad_bottom=1
    )
    box_height = len(box)

    if resized:
        print("\033[2J\033[H", end="")
        last_size = current_size
        last_render = ""
        view_offset_x = 0
        view_offset_y = 0
    banner_space = max(0, term_height - box_height)
    banner_line = raw_banner_line if raw_banner_line and banner_space > 0 else None
    if banner_line:
        banner_space -= 1
    escape_banner = raw_escape_banner[:banner_space]
    visible_lines = [
        pad_visible_line(ansi_visible_slice(line, view_offset_x, term_width), term_width)
        for line in box
    ]
    if escape_banner:
        visible_lines = escape_banner + visible_lines
    if banner_line:
        visible_lines = [banner_line] + visible_lines
    if len(visible_lines) > term_height:
        visible_lines = visible_lines[-term_height:]
    frame = "\033[H" + "\n".join(visible_lines)
    if frame != last_render:
        sys.stdout.write(frame)
        sys.stdout.flush()
        last_render = frame


def typewriter_message(lines, title, speed=0.03):

    global KEY_PRESSED, listener_enabled

    if not lines:
        return

    if ESCAPE_MODE:
        lines = escape_lines(list(lines))
        title = escape_text(title)

    display_lines = [""] * len(lines)

    def _consume_skip_request():
        global KEY_PRESSED
        if not KEY_PRESSED:
            return False
        raw = KEY_PRESSED
        KEY_PRESSED = None
        return isinstance(raw, str) and raw.lower() == "z"

    def _wait_for_z(prompt_text):
        if not listener_enabled:
            return
        prompt_lines = display_lines.copy()
        if prompt_text:
            prompt_lines.append("")
            prompt_lines.append(prompt_text)
        frame = boxed_lines(prompt_lines, title=title, pad_top=1, pad_bottom=1)
        render_frame(frame)
        while True:
            if _consume_skip_request():
                return
            if not listener_enabled:
                return
            time.sleep(0.01)

    for idx, line in enumerate(lines):
        current_line = line or ""
        skip_line = False
        if current_line:
            for char in current_line:
                display_lines[idx] += char
                frame = boxed_lines(display_lines, title=title, pad_top=1, pad_bottom=1)
                render_frame(frame)
                if _consume_skip_request():
                    display_lines[idx] = current_line
                    frame = boxed_lines(display_lines, title=title, pad_top=1, pad_bottom=1)
                    render_frame(frame)
                    skip_line = True
                    break
                time.sleep(speed)
        else:
            display_lines[idx] = ""
        if not skip_line:
            frame = boxed_lines(display_lines, title=title, pad_top=1, pad_bottom=1)
            render_frame(frame)
        prompt = "Press Z to close" if idx == len(lines) - 1 else "Press Z to continue..."
        _wait_for_z(prompt)


def resonance_system_active():
    return game.get("layer", 0) >= 2


def update_resonance(delta):
    if not resonance_system_active():
        return

                           
    if "resonance_val" not in game:
        game["resonance_val"] = RESONANCE_START
        game["resonance_target"] = 50.0
        game["resonance_drift_dir"] = 1

    instability = get_resonance_instability()
    stabilizer_level = get_stabilizer_level()
    cooldown = max(0.0, game.get("resonance_repick_cooldown", 0.0) - delta)
    game["resonance_repick_cooldown"] = cooldown

                                       
    target = game["resonance_target"]
    target += (random.random() - 0.5) * delta * 10.0 * instability
    target = max(10, min(90, target))
    game["resonance_target"] = target

    val = game["resonance_val"]
    drift_speed = RESONANCE_DRIFT_RATE * (0.75 + instability)
    val += game["resonance_drift_dir"] * drift_speed * delta

                                            
    val += (random.random() - 0.5) * instability * 4.0

                                                            
    window = RESONANCE_TARGET_WIDTH
    diff = target - val
    if abs(diff) > window:
        spring = diff * 0.02 * (1.0 + instability)
        val += spring
        if abs(diff) > window * 2:
            game["resonance_drift_dir"] = 1 if diff > 0 else -1
            game["resonance_repick_cooldown"] = min(
                game.get("resonance_repick_cooldown", 0.0), 0.2
            )

                                           
    if random.random() < RESONANCE_JUMP_CHANCE * instability * delta:
        val += (random.random() - 0.5) * RESONANCE_JUMP_POWER * max(1.0, instability)

                                                                                 
    if cooldown <= 0:
        toward_target = 1 if target > val else -1
        bias = min(0.25, stabilizer_level * 0.05)
        prob_toward = 0.5 + bias
        if random.random() < prob_toward:
            game["resonance_drift_dir"] = toward_target
        else:
            game["resonance_drift_dir"] = -toward_target
        min_cd = 0.3 + stabilizer_level * 0.05
        max_cd = 0.6 + stabilizer_level * 0.12
        game["resonance_repick_cooldown"] = random.uniform(min_cd, max_cd)

                      
    if val <= 0 or val >= RESONANCE_MAX:
        game["resonance_drift_dir"] *= -1
    game["resonance_val"] = max(0, min(RESONANCE_MAX, val))


def get_stabilizer_level():
    for entry in game.get("concept_upgrades", []):
        if entry.get("id") == "concept_stabilizer":
            return entry.get("level", 0)
    return 0


def get_resonance_instability():
    instability = RESONANCE_BASE_INSTABILITY
    level = get_stabilizer_level()
    if level:
        instability *= 0.82 ** level
    return max(RESONANCE_MIN_INSTABILITY, instability)


def get_resonance_efficiency():
    if not resonance_system_active():
        return 0.0

    val = game.get("resonance_val", RESONANCE_START)
    target = game.get("resonance_target", 50.0)
    width = max(1e-6, RESONANCE_TARGET_WIDTH)

    dist = abs(val - target)
    if dist <= width:
        needle_ratio = min(1.0, dist / width)
        bonus = 1.5 - 0.7 * needle_ratio                                             
        return max(0.0, bonus)

    overflow = dist - width
    span = max(1.0, RESONANCE_MAX - width)
    normalized = min(1.0, overflow / span)
    penalty = (normalized ** 0.7) * 1.25
    raw = max(0.0, 1.0 - penalty)
    return 0.8 * raw                                                
    

_RESONANCE_GRADIENT = [
    Fore.RED,
    Fore.LIGHTRED_EX,
    Fore.YELLOW,
    Fore.LIGHTGREEN_EX,
    Fore.GREEN,
]


def gradient_color(ratio):
    ratio = max(0.0, min(1.0, ratio))
    steps = len(_RESONANCE_GRADIENT) - 1
    idx = min(steps, int(round((1.0 - ratio) * steps)))
    return _RESONANCE_GRADIENT[idx]


def build_resonance_bar():
    if not resonance_system_active():
        return "Signal: [offline]"
    val = game.get("resonance_val", RESONANCE_START)
    target = game.get("resonance_target", 50.0)
    width = RESONANCE_TARGET_WIDTH
    bar_len = 30
    
    chars = [" "] * bar_len
    colors = [None] * bar_len
    pos_step = RESONANCE_MAX / max(1, (bar_len - 1))
    zone_left = max(0.0, target - width)
    zone_right = min(RESONANCE_MAX, target + width)

    def zone_ratio(position):
        if position < zone_left or position > zone_right:
            return None
        dist = abs(position - target)
        return min(1.0, dist / max(width, 1e-6))

    for i in range(bar_len):
        pos = i * pos_step
        ratio = zone_ratio(pos)
        if ratio is not None:
            chars[i] = "="
            colors[i] = gradient_color(ratio)
        
                 
    val_pct = val / RESONANCE_MAX
    val_idx = int(val_pct * (bar_len - 1))
    val_idx = max(0, min(bar_len - 1, val_idx))
    
    chars[val_idx] = "█" if colors[val_idx] else "|"
    colors[val_idx] = Fore.WHITE
        
    segments = []
    for ch, color in zip(chars, colors):
        if color:
            segments.append(color + ch + Style.RESET_ALL)
        else:
            segments.append(ch)
    bar_str = "".join(segments)
    signal_bonus = max(0.0, get_resonance_efficiency())
    signal_mult = 1.0 + signal_bonus
    game["signal_multiplier"] = signal_mult

    needle_ratio = None
    if zone_left <= val <= zone_right:
        needle_ratio = min(1.0, abs(val - target) / max(width, 1e-6))
    braces_color = gradient_color(needle_ratio) if needle_ratio is not None else Fore.RED
    left_brace = f"{braces_color}[{Style.RESET_ALL}"
    right_brace = f"{braces_color}]{Style.RESET_ALL}"

    approx_pct = int(round(signal_bonus * 100))

    mult_text = f"×{signal_mult:.2f}"
    return f"Signal: {left_brace}{bar_str}{right_brace} {approx_pct}% {mult_text}"


def build_breach_door_lines():
    if not (breach_key_available() or breach_door_is_open()):
        return []
    lines = ["", f"{Fore.LIGHTMAGENTA_EX}Breach Door{Style.RESET_ALL}"]
    art = BREACH_DOOR_OPEN_ART if breach_door_is_open() else BREACH_DOOR_CLOSED_ART
    for row in art:
        lines.append(row)
    if breach_door_is_open():
        prompt = "Press X to enter."
    elif breach_key_available():
        prompt = "Press X to unlock."
    else:
        prompt = "Find the key."
    lines.append(f"{Fore.YELLOW}{prompt}{Style.RESET_ALL}")
    return lines


def rpg_log(msg):
    msg = escape_text(msg)
    rpg = ensure_rpg_state()
    log = rpg.get("log", [])
    log.append(msg)
    if len(log) > RPG_LOG_MAX:
        log = log[-RPG_LOG_MAX:]
    rpg["log"] = log


def _current_event(rpg):
    event = rpg.get("event")
    return event if isinstance(event, dict) else None


def _start_rpg_event(rpg, kind, **data):
    rpg["state"] = "event"
    rpg["event"] = {
        "kind": kind,
        "data": data,
        "frame": 0,
        "next_frame_time": time.time(),
    }


def _clear_rpg_event(rpg):
    rpg["event"] = None
    if rpg.get("state") == "event":
        rpg["state"] = "explore"


def start_campfire_event(rpg, room):
    _start_rpg_event(rpg, "campfire", room=room)
    rpg_log("Campfire ready: [R]est or [L]eave.")


def start_relic_event(rpg, relic):
    _start_rpg_event(rpg, "relic", relic=relic)
    rpg_log(f"Relic online: {Fore.YELLOW}{relic['name']}{Style.RESET_ALL}.")


def start_secret_reveal_event(rpg, room, coords, direction):
    _start_rpg_event(rpg, "secret", room=room, coords=coords, direction=direction)
    rpg_log("Hidden seam opened.")


def resolve_secret_entry(rpg):
    event = _current_event(rpg)
    data = (event or {}).get("data") or {}
    room = data.get("room")
    coords = data.get("coords")
    if not room or not coords:
        _clear_rpg_event(rpg)
        return
    y, x = coords
    room["hidden"] = False
    room["visited"] = True
    layout = rpg.get("map") or []
    if 0 <= y < len(layout) and 0 <= x < len(layout[0]):
        rpg["player_pos"] = [y, x]
    _clear_rpg_event(rpg)
    handle_rpg_room_event(rpg, room)


def build_secret_chamber_layout(payload):
    payload = payload or random.choice(RPG_SECRET_ROOM_TYPES)
    def _room(r_type, visited=False, cleared=False, extra=None):
        data = {"type": r_type, "visited": visited, "cleared": cleared}
        if extra:
            data.update(extra)
        return data

    payload_type = {
        "vault": "secret_vault",
        "echo": "secret_echo",
        "sentinel": "secret_sentinel",
    }.get(payload, "secret_vault")
    layout = [
        [
            _room("start", visited=True, cleared=True),
            _room("empty", cleared=True),
            _room(payload_type, extra={"secret_payload": payload}),
        ],
        [
            _room("empty", cleared=True),
            _room("empty", cleared=True),
            _room("secret_exit"),
        ],
    ]
    start = (0, 0)
    variant = {
        "id": "secret",
        "label": "Secret Annex",
        "width": len(layout[0]),
        "height": len(layout),
        "color": "BLUE",
    }
    return layout, start, variant, payload


def enter_secret_room(rpg, payload, seam_coords, seam_room=None):
    origin_map = rpg.get("map")
    if not origin_map:
        return
    layout, start, variant, payload = build_secret_chamber_layout(payload)
    rpg["secret_origin"] = {
        "map": origin_map,
        "variant": copy.deepcopy(rpg.get("maze_variant")),
        "player_pos": list(seam_coords),
        "seam_coords": list(seam_coords),
        "seam_room": seam_room,
    }
    rpg["map"] = layout
    rpg["player_pos"] = list(start)
    rpg["maze_variant"] = variant
    rpg["state"] = "secret"
    rpg["secret_payload_active"] = payload
    rpg_log("Entered secret annex.")


def exit_secret_room(rpg):
    origin = rpg.get("secret_origin") or {}
    origin_map = origin.get("map")
    if not origin_map:
        rpg_log("No seam remains to exit through.")
        return
    seam_coords = origin.get("seam_coords", origin.get("player_pos", [0, 0]))
    rpg["map"] = origin_map
    rpg["player_pos"] = list(seam_coords)
    rpg["maze_variant"] = origin.get("variant")
    rpg["state"] = "explore"
    seam_room = origin.get("seam_room")
    if seam_room:
        seam_room["type"] = "empty"
        seam_room["cleared"] = True
        seam_room["hidden"] = False
        seam_room["visited"] = True
    rpg["secret_origin"] = None
    rpg["secret_payload_active"] = None
    rpg_log("Returned to the main maze.")


def resolve_secret_payload_room(rpg, room):
    payload = room.get("secret_payload")
    if room.get("secret_resolved") and payload != "sentinel":
        rpg_log("This annex chamber already lies dormant.")
        return
    floor = rpg.get("floor", 1)
    if payload == "vault":
        gold_gain = 100 + floor * 25
        modifier = active_floor_modifier(rpg)
        if modifier:
            gold_gain = int(gold_gain * modifier.get("treasure_gold_bonus", 1.0))
        rpg["gold"] = rpg.get("gold", 0) + gold_gain
        rpg_log(f"Secret vault cleared (+{gold_gain} gold).")
        room["cleared"] = True
        room["secret_resolved"] = True
    elif payload == "echo":
        xp_gain = 90 + floor * 30
        modifier = active_floor_modifier(rpg)
        if modifier:
            xp_gain = int(xp_gain * modifier.get("enemy_xp_mult", 1.0))
        rpg["xp"] = rpg.get("xp", 0) + xp_gain
        rpg_log(f"Secret echo captured (+{xp_gain} XP).")
        check_rpg_level_up(rpg)
        room["cleared"] = True
        room["secret_resolved"] = True
    else:
        if room.get("secret_resolved"):
            rpg_log("Annex encounter already cleared.")
            return
        enemy = build_secret_enemy(rpg, floor)
        room["secret_encounter"] = True
        rpg_log("Secret sentinel detected.")
        start_rpg_combat(rpg, custom_enemy=enemy)


def _advance_event_animation(rpg):
    event = _current_event(rpg)
    if not event:
        return
    anim = EVENT_ANIMATIONS.get(event.get("kind"))
    if not anim:
        return
    frames = anim.get("frames") or []
    if not frames:
        return
    delay = max(0.05, anim.get("delay", 0.3))
    now = time.time()
    next_tick = event.get("next_frame_time", 0.0)
    if now >= next_tick:
        event["frame"] = (event.get("frame", 0) + 1) % len(frames)
        event["next_frame_time"] = now + delay


def _prime_enemy_animation(rpg):
    if not ENEMY_ASCII_FRAMES:
        rpg.pop("enemy_anim", None)
        return
    rpg["enemy_anim"] = {
        "frame": 0,
        "next_frame_time": time.time() + ENEMY_ANIM_DELAY,
    }


def _clear_enemy_animation(rpg):
    rpg.pop("enemy_anim", None)


def _advance_enemy_animation(rpg):
    if rpg.get("state") != "combat" or not rpg.get("current_enemy"):
        _clear_enemy_animation(rpg)
        return
    if not ENEMY_ASCII_FRAMES:
        _clear_enemy_animation(rpg)
        return
    anim = rpg.get("enemy_anim")
    if not isinstance(anim, dict):
        _prime_enemy_animation(rpg)
        anim = rpg.get("enemy_anim")
    if not anim:
        return
    now = time.time()
    next_tick = anim.get("next_frame_time", 0.0)
    if now >= next_tick:
        anim["frame"] = (anim.get("frame", 0) + 1) % len(ENEMY_ASCII_FRAMES)
        anim["next_frame_time"] = now + ENEMY_ANIM_DELAY


def _campfire_heal_amount(rpg):
    floor = rpg.get("floor", 1)
    ratio = 0.45
    if floor <= 1:
        ratio = 0.7
    elif floor == 2:
        ratio = 0.55
    heal = max(15, int(rpg.get("max_hp", 1) * ratio))
    return heal


def resolve_campfire_choice(rpg, rest):
    event = _current_event(rpg)
    room = (event or {}).get("data", {}).get("room") if event else None
    if rest:
        heal = _campfire_heal_amount(rpg)
        prev = rpg.get("hp", 0)
        rpg["hp"] = min(rpg.get("max_hp", 0), prev + heal)
        if room:
            room["cleared"] = True
        rpg_log(f"Campfire restore: +{rpg['hp'] - prev} HP.")
    else:
        rpg_log("Campfire skipped.")
    _clear_rpg_event(rpg)


def resolve_relic_choice(rpg, accept):
    event = _current_event(rpg)
    relic = (event or {}).get("data", {}).get("relic") if event else None
    if not relic:
        _clear_rpg_event(rpg)
        return
    if accept:
        rpg.setdefault("relics", []).append(relic["id"])
        apply_relic_effect(rpg, relic)
        rpg_log(f"Relic bonded: {relic['name']} ({relic['desc']}).")
    else:
        spill = 90 + rpg.get("floor", 1) * 25
        rpg["gold"] = rpg.get("gold", 0) + spill
        rpg_log(f"Relic drained for +{spill} gold.")
    _clear_rpg_event(rpg)


def handle_rpg_event_command(rpg, key):
    event = _current_event(rpg)
    if not event:
        _clear_rpg_event(rpg)
        return
    kind = event.get("kind")
    if kind == "campfire":
        if key == "r":
            resolve_campfire_choice(rpg, True)
        elif key == "l":
            resolve_campfire_choice(rpg, False)
        else:
            rpg_log("Campfire choices: [R]est · [L]eave.")
    elif kind == "relic":
        if key == "a":
            resolve_relic_choice(rpg, True)
        elif key == "d":
            resolve_relic_choice(rpg, False)
        else:
            rpg_log("Relic choices: [A]ttune · [D]rain.")
    elif kind == "secret":
        if key == "h":
            resolve_secret_entry(rpg)
        else:
            rpg_log("Secret door: press [H] to step through.")
    else:
        _clear_rpg_event(rpg)


def build_event_panel_lines(rpg, width):
    event = _current_event(rpg)
    if not event:
        return ["Space ripples, awaiting intent."]
    kind = event.get("kind")
    anim = EVENT_ANIMATIONS.get(kind, {})
    frames = anim.get("frames") or []
    frame_idx = event.get("frame", 0)
    color = anim.get("color", "")
    span = max(10, (width or 0) - 4)
    art_lines = []
    if frames:
        active = frames[frame_idx % len(frames)]
        for raw in active:
            tinted = f"{color}{raw}{Style.RESET_ALL}" if color else raw
            art_lines.append(ansi_center(tinted, span))
    if kind == "campfire":
        heal = _campfire_heal_amount(rpg)
        prompt = [
            "",
            ansi_center(f"Rest here to regain about {heal} HP?", span),
            ansi_center("[R] Rest · [L] Leave it alone", span),
        ]
    elif kind == "relic":
        relic = (event.get("data") or {}).get("relic") if event else None
        desc = relic.get("desc") if relic else "A relic waits."
        name = relic.get("name") if relic else "Unknown Relic"
        prompt = [
            "",
            ansi_center(f"{name}: {desc}", span),
            ansi_center("[A] Attune power · [D] Drain to gold", span),
        ]
    elif kind == "secret":
        direction = (event.get("data") or {}).get("direction", "nearby")
        prompt = [
            "",
            ansi_center(f"The {direction} wall blooms outward.", span),
            ansi_center("[H] Step inside", span),
        ]
    else:
        prompt = []
    return art_lines + prompt


def build_enemy_ascii_lines(rpg, width):
    enemy = rpg.get("current_enemy")
    if not enemy or not ENEMY_ASCII_FRAMES:
        return []
    anim = rpg.get("enemy_anim") or {}
    frame_idx = anim.get("frame", 0)
    frame = ENEMY_ASCII_FRAMES[frame_idx % len(ENEMY_ASCII_FRAMES)]
    span = max(10, (width or 0) - 4)
    color = Fore.MAGENTA if enemy.get("elite") else Fore.RED
    lines = []
    for raw in frame:
        tinted = f"{color}{raw}{Style.RESET_ALL}"
        lines.append(ansi_center(tinted, span))
    return lines


def calculate_ng_gain_from_gold(gold):
    gold = max(0, int(gold))
    if gold <= 0:
        return 1
    tiers = gold // RPG_NG_GOLD_STEP
    capped = min(12, tiers + 1)
    return max(1, capped)


def choose_maze_variant(floor):
    pool = [copy.deepcopy(v) for v in RPG_MAZE_VARIANTS if floor >= v.get("min_floor", 1)]
    if not pool:
        pool = [copy.deepcopy(v) for v in RPG_MAZE_VARIANTS]
    weights = []
    for entry in pool:
        base = max(0.05, float(entry.get("weight", 1.0)))
        floor_bias = max(0, floor - entry.get("min_floor", 1)) * 0.05
        weights.append(base * (1.0 + floor_bias))
    return random.choices(pool, weights=weights, k=1)[0]


def floor_theme_for_floor(floor):
    block_size = max(1, RPG_THEME_BLOCK_SIZE)
    rotation = copy.deepcopy(RPG_THEME_ROTATION) if RPG_THEME_ROTATION else []
    if not rotation:
        rotation = [
            {
                "id": "default",
                "label": "Drifted Corridors",
                "desc": "Bare hallways hum with patient static.",
                "map_color": "CYAN",
                "ambient_lines": [],
            }
        ]
    block = max(0, (max(1, floor) - 1) // block_size)
    entry = rotation[block % len(rotation)]
    entry["block"] = block
    entry["start_floor"] = block * block_size + 1
    entry["end_floor"] = entry["start_floor"] + block_size - 1
    return entry


def ensure_floor_theme(rpg, floor=None):
    floor = floor or rpg.get("floor", 1)
    theme = rpg.get("floor_theme")
    block_size = max(1, RPG_THEME_BLOCK_SIZE)
    block = max(0, (max(1, floor) - 1) // block_size)
    if not theme or theme.get("block") != block:
        theme = floor_theme_for_floor(floor)
        rpg["floor_theme"] = theme
        rpg["theme_ambient_next"] = time.time() + 1.5
        color = _theme_color(theme)
        rpg_log(f"{color}Theme shift → {theme['label']}{Style.RESET_ALL}.")
    return theme


def maybe_emit_theme_ambient(rpg, chance=0.4):
    return


def is_boss_floor(floor):
    return floor in RPG_BOSSES


SIDE_CHAMBER_CHANCE = 0.35
SECRET_ROOM_CHANCE = 0.05
SHOP_MAX_ITEMS_PER_VISIT = 3
SHOP_PURCHASE_LIMIT = 2


def maybe_attach_side_chamber(layout, floor):
    if not layout or random.random() >= SIDE_CHAMBER_CHANCE:
        return layout, None
    height = len(layout)
    width = len(layout[0]) if layout else 0
    annex_width = 2 if width < 10 else 3
    feature_pool = ["treasure", "secret", "elite", "healer"]
    random.shuffle(feature_pool)
    feature_rows = {}
    for idx, row_idx in enumerate(random.sample(range(height), k=min(len(feature_pool), height))):
        feature_rows[row_idx] = feature_pool[idx % len(feature_pool)]
    for row_idx, row in enumerate(layout):
        new_cells = []
        for col in range(annex_width):
            cell = {
                "type": "empty",
                "visited": False,
                "cleared": True,
                "annex": True,
            }
            if col == annex_width - 1:
                cell_type = feature_rows.get(row_idx)
                if cell_type:
                    cell = {
                        "type": cell_type,
                        "visited": False,
                        "cleared": cell_type == "empty",
                        "annex": True,
                    }
                elif random.random() < 0.35:
                    cell = {
                        "type": "enemy",
                        "visited": False,
                        "cleared": False,
                        "annex": True,
                    }
            new_cells.append(cell)
        row.extend(new_cells)
    return layout, {"width": annex_width}


def select_floor_modifier(floor):
    eligible = []
    for entry in RPG_FLOOR_MODIFIERS:
        min_floor = entry.get("min_floor", 1)
        max_floor = entry.get("max_floor", RPG_FLOOR_CAP)
        if floor < min_floor or floor > max_floor:
            continue
        eligible.append(entry)
    if not eligible:
        return None
    weights = [max(0.05, float(e.get("weight", 1.0))) for e in eligible]
    picked = copy.deepcopy(random.choices(eligible, weights=weights, k=1)[0])
    return picked


def ensure_floor_modifier(rpg):
    floor = rpg.get("floor", 1)
    if is_boss_floor(floor):
        rpg["floor_modifier"] = None
        rpg["floor_modifier_floor"] = floor
        return None
    current = rpg.get("floor_modifier") if rpg.get("floor_modifier_floor") == floor else None
    if current:
        return current
    picked = select_floor_modifier(floor)
    rpg["floor_modifier"] = picked
    rpg["floor_modifier_floor"] = floor
    if picked:
        rpg_log(f"Modifier active: {picked['name']} — {picked['desc']}")
    return picked


def active_floor_modifier(rpg):
    mod = rpg.get("floor_modifier")
    if not mod:
        return None
    if rpg.get("floor_modifier_floor") != rpg.get("floor", 0):
        return None
    return mod


def _variant_color_code(variant):
    color_name = (variant or {}).get("color", "WHITE")
    return getattr(Fore, color_name.upper(), Fore.WHITE)


def _theme_color(theme):
    if not theme:
        return Fore.WHITE
    color_name = theme.get("map_color") or theme.get("color") or "WHITE"
    return getattr(Fore, color_name.upper(), Fore.WHITE)


def _enemy_ng_softener(rpg):
    tiers = (rpg or {}).get("ng_plus", 0)
    return max(0.6, 1.0 - 0.04 * tiers)


def _early_floor_scale_factor(floor):
    if floor <= 1:
        return 0.95
    if floor == 2:
        return 0.98
    return 1.0


def _soften_trap_damage(rpg, dmg):
    floor = rpg.get("floor", 1)
    factor = 0.65 if floor <= 1 else (0.85 if floor == 2 else 1.0)
    modifier = active_floor_modifier(rpg)
    trap_mult = modifier.get("trap_damage_mult", 1.0) if modifier else 1.0
    return max(1, int(math.ceil(dmg * factor * trap_mult)))


def _limit_room_spawns(layout, room_type, max_allowed):
    coords = []
    for y, row in enumerate(layout):
        for x, room in enumerate(row):
            if room.get("type") == room_type:
                coords.append((y, x))
    if len(coords) <= max_allowed:
        return
    random.shuffle(coords)
    for y, x in coords[max_allowed:]:
        layout[y][x] = {"type": "enemy", "visited": False, "cleared": False}


def _build_boss_floor_layout(floor):
    layout = [
        [
            {"type": "start", "visited": True, "cleared": True},
            {"type": "healer", "visited": False, "cleared": False},
            {"type": "boss", "visited": False, "cleared": False},
        ],
        [
            {"type": "treasure", "visited": False, "cleared": False},
            {"type": "empty", "visited": False, "cleared": True},
            {"type": "empty", "visited": False, "cleared": True},
        ],
    ]
    return layout, (0, 0)


def _build_layout_for_variant(floor, variant):
    if is_boss_floor(floor):
        return _build_boss_floor_layout(floor)
    width = max(3, int((variant or {}).get("width", RPG_MAP_WIDTH)))
    height = max(3, int((variant or {}).get("height", RPG_MAP_HEIGHT)))
    weights = [entry[1] for entry in RPG_ROOM_TYPES]
    options = [entry[0] for entry in RPG_ROOM_TYPES]
    layout = []
    for _y in range(height):
        row = []
        for _x in range(width):
            typo = random.choices(options, weights=weights, k=1)[0]
            row.append({"type": typo, "visited": False, "cleared": typo == "empty"})
        layout.append(row)
    center_y = height // 2
    center_x = width // 2
    layout[center_y][center_x] = {"type": "start", "visited": True, "cleared": True}
    candidates = [(y, x) for y in range(height) for x in range(width) if (y, x) != (center_y, center_x)]
    exit_y, exit_x = random.choice(candidates)
    exit_type = "boss" if is_boss_floor(floor) else "stairs"
    layout[exit_y][exit_x]["type"] = exit_type
    layout[exit_y][exit_x]["visited"] = False
    layout[exit_y][exit_x]["cleared"] = exit_type == "stairs"
    if not any(room["type"] in ("enemy", "elite") for row in layout for room in row):
        backfill_y, backfill_x = random.choice(candidates)
        layout[backfill_y][backfill_x]["type"] = "enemy"
        layout[backfill_y][backfill_x]["cleared"] = False
        layout[backfill_y][backfill_x]["visited"] = False
    area = width * height
    max_healers = max(1, min(3, area // 18 + 1))
    _limit_room_spawns(layout, "healer", max_healers)
    inject_secret_rooms(layout, floor)
    return layout, (center_y, center_x)


def _build_transition_sequence(layout, start):
    if not layout:
        return []
    height = len(layout)
    width = len(layout[0])
    start = start or (height // 2, width // 2)
    queue = deque([start])
    seen = set()
    order = []
    dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
    while queue:
        y, x = queue.popleft()
        if not (0 <= y < height and 0 <= x < width):
            continue
        if (y, x) in seen:
            continue
        seen.add((y, x))
        order.append((y, x))
        for dy, dx in dirs:
            queue.append((y + dy, x + dx))
    for y in range(height):
        for x in range(width):
            if (y, x) not in seen:
                order.append((y, x))
    return order


def generate_rpg_floor(rpg, variant=None, prepared_layout=None):
    floor = rpg.get("floor", 1)
    theme = ensure_floor_theme(rpg, floor)
    ensure_floor_modifier(rpg)
    if is_boss_floor(floor) and not variant:
        boss = RPG_BOSSES.get(floor, {})
        label = f"{boss.get('name', 'Boss')} Arena"
        selected = {"id": "boss", "label": label, "color": "LIGHTMAGENTA_EX"}
    else:
        selected = copy.deepcopy(variant) if variant else choose_maze_variant(floor)
    if prepared_layout:
        base_layout, center = prepared_layout
        layout = copy.deepcopy(base_layout)
        center_y, center_x = center
    else:
        layout, (center_y, center_x) = _build_layout_for_variant(floor, selected)
    annex_info = None
    if not is_boss_floor(floor):
        layout, annex_info = maybe_attach_side_chamber(layout, floor)
        if annex_info:
            rpg_log("Side chamber attached to the east wall.")
    height = len(layout)
    width = len(layout[0]) if layout else 0
    rpg["map"] = layout
    rpg["player_pos"] = [center_y, center_x]
    rpg["state"] = "explore"
    rpg["current_enemy"] = None
    rpg["maze_variant"] = {
        "id": selected.get("id"),
        "label": selected.get("label", "Unknown Layout"),
        "width": width,
        "height": height,
        "color": theme.get("map_color") if theme else selected.get("color"),
    }
    rpg["pending_variant"] = None
    if is_boss_floor(floor):
        rpg_log(
            f"Boss arena ready: {selected.get('label', 'Boss Arena')} ({height}x{width})."
        )
    else:
        rpg_log(
            f"Floor {floor} layout: {selected.get('label', '???')} ({height}x{width})."
        )


def inject_secret_rooms(layout, floor):
    if floor < RPG_MIN_SECRET_FLOOR:
        return
    if not layout:
        return
    height = len(layout)
    width = len(layout[0]) if layout else 0
    pool = []
    for y in range(height):
        for x in range(width):
            if y not in {0, height - 1} and x not in {0, width - 1}:
                continue
            room = layout[y][x]
            if room.get("type") in {"start", "exit", "stairs", "boss"}:
                continue
            pool.append((y, x))
    if not pool:
        return

    def _spawn_secret(y, x):
        layout[y][x] = {
            "type": "secret",
            "visited": False,
            "cleared": False,
            "hidden": True,
            "secret_payload": random.choice(RPG_SECRET_ROOM_TYPES),
        }

    spawned = False
    for y, x in pool:
        if random.random() <= SECRET_ROOM_CHANCE:
            _spawn_secret(y, x)
            spawned = True
    if not spawned and random.random() <= SECRET_ROOM_CHANCE:
        y, x = random.choice(pool)
        _spawn_secret(y, x)


def current_rpg_room(rpg):
    layout = rpg.get("map") or []
    if not layout:
        return None
    y, x = rpg.get("player_pos", [0, 0])
    if not (0 <= y < len(layout) and 0 <= x < len(layout[0])):
        return None
    return layout[y][x]


def _adjacent_hidden_rooms(rpg):
    layout = rpg.get("map") or []
    if not layout:
        return []
    y, x = rpg.get("player_pos", [0, 0])
    neighbors = []
    directions = [(-1, 0, "north"), (1, 0, "south"), (0, -1, "west"), (0, 1, "east")]
    for dy, dx, label in directions:
        ny, nx = y + dy, x + dx
        if not (0 <= ny < len(layout) and 0 <= nx < len(layout[0])):
            continue
        target = layout[ny][nx]
        if target.get("type") == "secret" and target.get("hidden") and not target.get("visited"):
            neighbors.append((ny, nx, label, target))
    return neighbors


def describe_rpg_room(room):
    if not room:
        return "the void"
    r_type = room.get("type")
    if room.get("hidden") and not room.get("visited"):
        return "a suspicious blank wall"
    if room.get("cleared") and r_type in {"enemy", "elite", "treasure", "trap"}:
        return "the husk of a resolved encounter"
    desc = RPG_ROOM_DESCRIPTIONS.get(r_type, "an unreadable hallway")
    if room.get("annex"):
        desc += " (side annex)"
    return desc


def rpg_room_symbol(room, is_player=False):
    if is_player:
        return "@"
    if not room:
        return "."
    if not room.get("visited"):
        return "░"
    room_type = room.get("type")
    if room_type in {"exit", "stairs"}:
        return "^"
    if room.get("type") == "secret":
        if not room.get("cleared"):
            return "?"
        return "S"
    if room_type in {"secret_vault", "secret_echo", "secret_sentinel"}:
        symbols = {
            "secret_vault": "$",
            "secret_echo": "~",
            "secret_sentinel": "!",
        }
        return symbols.get(room_type, "?")
    if room_type == "secret_exit":
        return "^"
    if not room.get("cleared"):
        symbols = {
            "enemy": "!",
            "elite": "E",
            "boss": "B",
            "treasure": "$",
            "healer": "+",
            "trap": "^",
        }
        return symbols.get(room.get("type"), "?")
    return "."


def _colorize_room_symbol(room, symbol, is_player=False):
    if is_player:
        return f"{Back.WHITE}{Fore.BLACK}{symbol}{Style.RESET_ALL}"
    if symbol == "░" or not room:
        return f"{Fore.LIGHTBLACK_EX}{symbol}{Style.RESET_ALL}"
    if room.get("cleared") and room.get("type") not in {"exit", "stairs"}:
        return f"{Fore.LIGHTBLACK_EX}{symbol}{Style.RESET_ALL}"
    if room.get("annex") and room.get("type") == "empty":
        return f"{Fore.LIGHTCYAN_EX}{symbol}{Style.RESET_ALL}"
    color = ROOM_COLOR_MAP.get(room.get("type"))
    if color:
        return f"{color}{symbol}{Style.RESET_ALL}"
    return symbol


def _colorize_room_label(room, text):
    if not room or (room.get("hidden") and not room.get("visited")):
        return text
    color = ROOM_COLOR_MAP.get(room.get("type"))
    if color:
        return f"{color}{text}{Style.RESET_ALL}"
    return text


def build_rpg_map_lines(rpg):
    layout = rpg.get("map") or []
    if not layout:
        return []
    pos = tuple(rpg.get("player_pos", [0, 0]))
    lines = []
    for y, row in enumerate(layout):
        glyphs = []
        for x, room in enumerate(row):
            symbol = rpg_room_symbol(room, is_player=pos == (y, x))
            glyphs.append(_colorize_room_symbol(room, symbol, is_player=pos == (y, x)))
        lines.append(" ".join(glyphs))
    return lines


def begin_maze_reassembly(rpg, variant=None, duration=1.8):
    floor = rpg.get("floor", 1)
    pending = copy.deepcopy(variant) if variant else choose_maze_variant(floor)
    layout, center = _build_layout_for_variant(floor, pending)
    sequence = _build_transition_sequence(layout, center)
    if not sequence:
        height = len(layout)
        width = len(layout[0]) if layout else 0
        sequence = [(y, x) for y in range(height) for x in range(width)]
    total_cells = max(1, len(sequence))
    rpg["pending_variant"] = pending
    rpg["transition_variant"] = pending
    rpg["transition_layout"] = layout
    rpg["transition_center"] = center
    rpg["transition_sequence"] = sequence
    rpg["transition_total_cells"] = total_cells
    rpg["transition_reveal"] = 0
    rpg["map"] = []
    rpg["player_pos"] = None
    rpg["state"] = "transition"
    now = time.time()
    rpg["maze_anim_start"] = now
    rpg["maze_anim_until"] = now + duration
    step_time = max(0.02, duration / float(total_cells))
    rpg["transition_step_time"] = step_time
    rpg["transition_last_step"] = now
    rpg_log("Maze resetting. Hold position.")


def complete_maze_reassembly(rpg):
    variant = rpg.get("pending_variant") or rpg.get("transition_variant")
    layout = rpg.get("transition_layout")
    center = rpg.get("transition_center")
    prepared = None
    if layout and center is not None:
        prepared = (layout, center)
    generate_rpg_floor(rpg, variant=variant, prepared_layout=prepared)
    rpg["maze_anim_start"] = 0.0
    rpg["maze_anim_until"] = 0.0
    rpg["transition_layout"] = None
    rpg["transition_center"] = None
    rpg["transition_sequence"] = []
    rpg["transition_total_cells"] = 0
    rpg["transition_reveal"] = 0
    rpg["transition_variant"] = None
    rpg["transition_step_time"] = 0.0
    rpg["transition_last_step"] = 0.0


def build_transition_map_lines(rpg, width):
    layout = rpg.get("transition_layout") or []
    variant = rpg.get("transition_variant") or {}
    if not layout:
        return ["Layout rebuild in progress."]
    seq = rpg.get("transition_sequence") or []
    total = max(1, rpg.get("transition_total_cells", len(seq) or 1))
    reveal = max(0, min(total, rpg.get("transition_reveal", 0)))
    built = set(seq[:reveal])
    highlight = seq[reveal] if reveal < len(seq) else None
    color = _variant_color_code(variant)
    lines = []
    for y, row in enumerate(layout):
        glyphs = []
        for x, room in enumerate(row):
            pos = (y, x)
            if pos in built:
                preview = dict(room)
                preview["visited"] = True
                glyph = rpg_room_symbol(preview)
                glyphs.append(f"{color}{glyph}{Style.RESET_ALL}")
            elif highlight == pos:
                glyphs.append(f"{Fore.YELLOW}▒{Style.RESET_ALL}")
            else:
                glyphs.append(f"{Fore.LIGHTBLACK_EX}·{Style.RESET_ALL}")
        lines.append(ansi_center(" ".join(glyphs), width))
    pct = int((reveal / float(total)) * 100)
    caption = f"{color}{variant.get('label', 'Unknown Layout')} reassembling {pct}%{Style.RESET_ALL}"
    return [caption, ""] + lines


def tick_rpg_state(rpg):
    if rpg.get("state") == "transition":
        total = max(1, rpg.get("transition_total_cells", 1))
        reveal = max(0, min(total, rpg.get("transition_reveal", 0)))
        step = max(0.02, rpg.get("transition_step_time", 0.05))
        last_step = rpg.get("transition_last_step", time.time())
        now = time.time()
                                                         
        safety = 0
        while reveal < total and now - last_step >= step and safety < total:
            reveal += 1
            last_step += step
            safety += 1
        rpg["transition_reveal"] = reveal
        rpg["transition_last_step"] = last_step
        if reveal >= total:
            complete_maze_reassembly(rpg)
    elif rpg.get("state") == "event":
        _advance_event_animation(rpg)
    elif rpg.get("state") == "combat":
        _advance_enemy_animation(rpg)


def handle_rpg_room_event(rpg, room):
    if not room:
        return
    r_type = room.get("type")
    if r_type in ("enemy", "elite") and not room.get("cleared"):
        start_rpg_combat(rpg, elite=(r_type == "elite"))
    elif r_type == "boss" and not room.get("cleared"):
        start_rpg_combat(rpg, custom_enemy=build_rpg_boss(rpg.get("floor", 1), rpg))
    elif r_type == "treasure" and not room.get("cleared"):
        rpg_grant_treasure(rpg)
        room["cleared"] = True
    elif r_type == "healer" and not room.get("cleared"):
        if rpg.get("state") != "event":
            start_campfire_event(rpg, room)
    elif r_type == "trap" and not room.get("cleared"):
        dmg = max(6, int(rpg.get("max_hp", 1) * 0.2))
        dmg = _soften_trap_damage(rpg, dmg)
        rpg["hp"] -= dmg
        room["cleared"] = True
        rpg_log(f"Trap triggered: {dmg} damage.")
        if rpg["hp"] <= 0:
            handle_rpg_death(rpg)
    elif r_type in {"exit", "stairs"}:
        if not rpg.get("stairs_prompted"):
            rpg_log("Staircase ready. Press [C] to climb or keep exploring.")
            rpg["stairs_prompted"] = True
    elif r_type == "secret" and not room.get("cleared"):
        resolve_secret_room(rpg, room)
    elif r_type in {"secret_vault", "secret_echo", "secret_sentinel"}:
        resolve_secret_payload_room(rpg, room)
    elif r_type == "secret_exit" and rpg.get("state") == "secret":
        rpg_log("Exit seam ready: press [C] to return.")


def rpg_move(dy, dx):
    rpg = ensure_rpg_state()
    if rpg.get("state") not in {"explore", "secret"}:
        rpg_log("Resolve the current encounter first.")
        return
    layout = rpg.get("map") or []
    if not layout:
        generate_rpg_floor(rpg)
        layout = rpg["map"]
    y, x = rpg.get("player_pos", [0, 0])
    ny, nx = y + dy, x + dx
    if not (0 <= ny < len(layout) and 0 <= nx < len(layout[0])):
        rpg_log("Movement blocked by map edge.")
        return
    target = layout[ny][nx]
    if target.get("hidden") and not target.get("visited"):
        rpg_log("Hidden seam detected. Press [H] to enter.")
        return
    rpg["player_pos"] = [ny, nx]
    room = target
    if not room.get("visited"):
        room["visited"] = True
        desc = describe_rpg_room(room)
        rpg_log(f"Scouted {_colorize_room_label(room, desc)}.")
    if room.get("type") not in {"exit", "stairs"}:
        rpg["stairs_prompted"] = False
    handle_rpg_room_event(rpg, room)
    maybe_emit_theme_ambient(rpg)


def attempt_enter_hidden_room():
    rpg = ensure_rpg_state()
    if rpg.get("state") != "explore":
        rpg_log("Resolve the current encounter first.")
        return
    neighbors = _adjacent_hidden_rooms(rpg)
    if not neighbors:
        rpg_log("No hidden seams detected nearby.")
        return
    if len(neighbors) > 1:
        rpg_log("Multiple seams detected. Face one and try again.")
        return
    ny, nx, label, room = neighbors[0]
    rpg_log(f"Entering {label} seam.")
    start_secret_reveal_event(rpg, room, (ny, nx), label)


def attempt_climb_stairs(rpg=None):
    rpg = rpg or ensure_rpg_state()
    special_mode = rpg.get("state") == "secret"
    if rpg.get("state") != "explore" and not special_mode:
        rpg_log("Resolve the current encounter before climbing.")
        return
    room = current_rpg_room(rpg)
    if not room:
        rpg_log("No staircase here to climb.")
        return
    if special_mode and room.get("type") == "secret_exit":
        exit_secret_room(rpg)
        return
    if room.get("type") not in {"exit", "stairs"}:
        rpg_log("No staircase here to climb.")
        return
    rpg["stairs_prompted"] = False
    rpg_log("Climbing to the next floor.")
    advance_rpg_floor(rpg)


def resolve_secret_room(rpg, room):
    room["hidden"] = False
    payload = room.get("secret_payload") or random.choice(RPG_SECRET_ROOM_TYPES)
    coords = tuple(rpg.get("player_pos", [0, 0]))
    enter_secret_room(rpg, payload, coords, seam_room=room)


def start_rpg_combat(rpg, elite=False, custom_enemy=None):
    enemy = custom_enemy or build_rpg_enemy(rpg.get("floor", 1), elite=elite, rpg=rpg)
    enemy["elite"] = bool(enemy.get("elite") or elite)
    rpg["current_enemy"] = enemy
    rpg["state"] = "combat"
    _prime_enemy_animation(rpg)
    if custom_enemy:
        prefix = ""
    else:
        prefix = "Elite " if elite else ""
    rpg_log(f"Encounter: {prefix}{enemy['name']} engaged.")


def build_rpg_enemy(floor, elite=False, rpg=None):
    pool = [entry for entry in RPG_ENEMIES if floor >= entry.get("min_floor", 1) and floor <= entry.get("max_floor", RPG_FLOOR_CAP)]
    if not pool:
        pool = RPG_ENEMIES[:]
    template = random.choice(pool)
    modifier = active_floor_modifier(rpg)
    hp_mult = modifier.get("enemy_hp_mult", 1.0) if modifier else 1.0
    atk_mult = modifier.get("enemy_atk_mult", 1.0) if modifier else 1.0
    level_pressure = 1.0 + max(0, (rpg or {}).get("level", 1) - 1) * 0.015
    scale = (1.0 + max(0, floor - 1) * 0.32) * level_pressure
    scale *= _enemy_ng_softener(rpg)
    scale *= _early_floor_scale_factor(floor)
    if elite:
        scale *= 1.35
    return {
        "name": template["name"],
        "hp": int(template["hp"] * scale * hp_mult),
        "max_hp": int(template["hp"] * scale * hp_mult),
        "atk": max(1, int(template["atk"] * scale * atk_mult)),
        "xp": int(template["xp"] * scale * (1.4 if elite else 1.0)),
        "gold": int(template.get("gold", 0) * scale * RPG_GOLD_REWARD_SCALE * (1.4 if elite else 1.0)),
        "elite": elite,
        "charging": False,
    }


def build_rpg_boss(floor, rpg):
    template = copy.deepcopy(RPG_BOSSES.get(floor))
    if not template:
        return build_rpg_enemy(floor, elite=True, rpg=rpg)
    hp_scale = max(1.0, 1.0 + 0.04 * rpg.get("ng_plus", 0))
    return {
        "name": template["name"],
        "hp": int(template["hp"] * hp_scale),
        "max_hp": int(template["hp"] * hp_scale),
        "atk": max(1, int(template["atk"] * hp_scale)),
        "xp": int(template["xp"] * hp_scale),
        "gold": int(template["gold"] * RPG_GOLD_REWARD_SCALE * hp_scale),
        "elite": True,
        "charging": False,
        "boss": True,
        "boss_floor": floor,
        "boss_id": template.get("id"),
    }


def build_secret_enemy(rpg, floor):
    scale = (1.0 + max(0, floor - 1) * 0.2) * _enemy_ng_softener(rpg)
    base = RPG_SECRET_BOSS_TEMPLATE
    enemy = {
        "name": base["name"],
        "hp": int(base["hp"] * scale),
        "max_hp": int(base["hp"] * scale),
        "atk": max(1, int(base["atk"] * scale)),
        "xp": int(base["xp"] * (1.1 + floor * 0.05)),
        "gold": int(base["gold"] * (1.1 + floor * 0.05)),
        "elite": True,
        "charging": False,
    }
    return enemy


def calculate_browser_token_gain(rpg, gold_before):
    floor = max(1, rpg.get("floor", 1))
    base = max(1, floor // 2)
    gold_bonus = max(0, gold_before // 350)
    boss_bonus = 2 if is_boss_floor(floor) else 0
    return base + gold_bonus + boss_bonus


def rpg_attack():
    rpg = ensure_rpg_state()
    if rpg.get("state") != "combat":
        rpg_log("Attack misses completely.")
        return
    enemy = rpg.get("current_enemy")
    if not enemy:
        rpg["state"] = "explore"
        return
    dmg = rpg.get("atk", RPG_PLAYER_START_ATK)
    aura_data, _ = _active_aura_data(rpg)
    trinket_bonus = (rpg.get("gear_trinket_bonus") or {}).get("crit_bonus", 0.0)
    crit_chance = min(0.9, RPG_BASE_CRIT + aura_data.get("crit_bonus", 0.0) + trinket_bonus)
    if random.random() < crit_chance:
        dmg = int(dmg * 1.75)
        rpg_log(f"Critical hit: {dmg} damage.")
    else:
        rpg_log(f"Damage dealt: {dmg}.")
    enemy["hp"] -= dmg
    if enemy["hp"] <= 0:
        complete_combat_victory(rpg, enemy)
    else:
        enemy_turn(rpg)


def complete_combat_victory(rpg, enemy):
    modifier = active_floor_modifier(rpg)
    gold_gain = int(enemy.get("gold", 0) * (1 + rpg.get("gold_bonus", 0.0)))
    xp_gain = enemy.get("xp", 0)
    if modifier:
        gold_gain = int(gold_gain * modifier.get("enemy_gold_mult", 1.0))
        xp_gain = int(xp_gain * modifier.get("enemy_xp_mult", 1.0))
    rpg_log(f"Felled {enemy['name']}! +{xp_gain} XP, +{gold_gain} gold.")
    rpg["gold"] = rpg.get("gold", 0) + gold_gain
    rpg["xp"] = rpg.get("xp", 0) + xp_gain
    room = current_rpg_room(rpg)
    if room:
        room["cleared"] = True
        if room.get("secret_encounter"):
            room["secret_resolved"] = True
            room.pop("secret_encounter", None)
    rpg["current_enemy"] = None
    rpg["state"] = "secret" if rpg.get("secret_origin") else "explore"
    _clear_enemy_animation(rpg)
    check_rpg_level_up(rpg)
    if room and room.get("type") == "boss":
        handle_boss_defeat(rpg, room, enemy)


def check_rpg_level_up(rpg):
    leveled = False
    while rpg.get("xp", 0) >= rpg.get("level", 1) * 120:
        req = rpg["level"] * 120
        rpg["xp"] -= req
        rpg["level"] += 1
        rpg["max_hp"] += 12
        rpg["atk"] += 1
        if rpg["level"] % 3 == 0:
            rpg["def"] = rpg.get("def", 0) + 1
        heal = max(8, int(rpg["max_hp"] * 0.4))
        rpg["hp"] = min(rpg["max_hp"], rpg["hp"] + heal)
        leveled = True
        rpg_log(f"Level up → {rpg['level']}.")
    return leveled


def enemy_turn(rpg):
    enemy = rpg.get("current_enemy")
    if not enemy:
        return
    if enemy.get("charging"):
        dmg = int(enemy["atk"] * 1.6)
        enemy["charging"] = False
        rpg_log(f"{enemy['name']} unleashes a charged strike for {dmg} damage!")
    else:
        if random.random() < 0.2:
            enemy["charging"] = True
            rpg_log(f"{enemy['name']} gathers static energy.")
            return
        dmg = enemy["atk"]
        rpg_log(f"{enemy['name']} lashes out for {dmg} damage.")
    defense = max(0, rpg.get("def", 0))
    if defense:
        reduction = min(0.65, defense * 0.05)
        dmg = max(1, int(math.ceil(dmg * (1.0 - reduction))))
    aura_data, _ = _active_aura_data(rpg)
    if aura_data.get("damage_reduction"):
        dmg = max(1, dmg - int(aura_data.get("damage_reduction", 0)))
    rpg["hp"] -= dmg
    if rpg["hp"] <= 0:
        handle_rpg_death(rpg)


def handle_boss_defeat(rpg, room, enemy):
    floor = rpg.get("floor", 1)
    boss_data = RPG_BOSSES.get(floor)
    if boss_data:
        reward = boss_data.get("reward", {})
        apply_boss_reward(rpg, reward, boss_data, floor)
    room["type"] = "stairs"
    room["cleared"] = True
    room["visited"] = True
    rpg_log("Boss defeated — the staircase reinitializes.")


def apply_boss_reward(rpg, reward, boss_data, floor):
    if not reward:
        return
    changed = []
    if reward.get("max_hp"):
        rpg["max_hp"] += reward["max_hp"]
        rpg["hp"] = rpg["max_hp"]
        changed.append(f"Max HP +{reward['max_hp']}")
    if reward.get("atk"):
        rpg["atk"] += reward["atk"]
        changed.append(f"ATK +{reward['atk']}")
    if reward.get("def"):
        rpg["def"] = rpg.get("def", 0) + reward["def"]
        changed.append(f"DEF +{reward['def']}")
    if reward.get("potions"):
        rpg["inventory"]["potion"] = rpg["inventory"].get("potion", 0) + reward["potions"]
        changed.append(f"Potions +{reward['potions']}")
    if changed:
        summary = ", ".join(changed)
        rpg_log(f"{boss_data.get('name', 'Boss')} reward: {summary}.")
    rpg.setdefault("boss_rewards", []).append(
        {
            "boss": boss_data.get("id"),
            "floor": floor,
            "summary": reward.get("desc"),
        }
    )


def handle_rpg_death(rpg):
    gold_before = max(0, int(rpg.get("gold", 0)))
    ng_gain = calculate_ng_gain_from_gold(gold_before)
    token_gain = calculate_browser_token_gain(rpg, gold_before)
    if token_gain > 0:
        game["browser_tokens"] = game.get("browser_tokens", 0) + token_gain
        game["browser_cycles"] = game.get("browser_cycles", 0) + 1
        set_browser_notice(f"Banked +{token_gain} {BROWSER_CURRENCY_NAME}.")
    token_total = game.get("browser_tokens", 0)
    show_rpg_death_screen(rpg, gold_before, ng_gain, token_gain, token_total)
    collapse_to_ng_plus(rpg, gold_spill=gold_before, ng_gain=ng_gain)


def show_rpg_death_screen(rpg, gold_before, ng_gain, token_gain, token_total):
    future_cycles = rpg.get("ng_plus", 0) + ng_gain
    future_hp = _rpg_base_hp_for_cycles(future_cycles)
    future_atk = _rpg_base_atk_for_cycles(future_cycles)
    lines = [
        f"{Fore.RED}LOOP COLLAPSED{Style.RESET_ALL}",
        "",
        f"Floor reached: {Fore.YELLOW}{rpg.get('floor', 1)}{Style.RESET_ALL}",
        f"Gold carried: {Fore.YELLOW}{gold_before}{Style.RESET_ALL}",
        f"NG+ gain: {Fore.MAGENTA}+{ng_gain}{Style.RESET_ALL}",
        f"{BROWSER_CURRENCY_NAME}: {Fore.CYAN}+{token_gain}{Style.RESET_ALL} (Total {token_total})",
        f"Next baseline → HP {Fore.GREEN}{future_hp}{Style.RESET_ALL}  ATK {Fore.CYAN}{future_atk}{Style.RESET_ALL}",
        "",
        f"{Style.DIM}More hoarded gold = stronger reincarnations.{Style.RESET_ALL}",
    ]
    frame = boxed_lines(lines, title=" Loop Collapse Report ", pad_top=1, pad_bottom=1)
    render_frame(frame)
    time.sleep(1.8)


def collapse_to_ng_plus(rpg, gold_spill=0, ng_gain=1):
    gain = max(1, int(ng_gain))
    prev_ng = rpg.get("ng_plus", 0)
    rpg["ng_plus"] = prev_ng + gain
    base_hp = _rpg_base_hp_for_cycles(rpg["ng_plus"])
    base_atk = _rpg_base_atk_for_cycles(rpg["ng_plus"])
    rpg["max_hp"] = base_hp
    rpg["hp"] = base_hp
    rpg["atk"] = base_atk + rpg.get("gear_atk_bonus", 0)
    rpg["level"] = 1
    rpg["xp"] = 0
    rpg["floor"] = 1
    rpg["gold"] = 0
    rpg["current_enemy"] = None
    _clear_enemy_animation(rpg)
    rpg["map"] = []
    rpg["player_pos"] = None
    rpg["maze_variant"] = None
    rpg["shop_stock"] = []
    rpg["state"] = "transition"
    rpg["floor_modifier"] = None
    rpg["floor_modifier_floor"] = 0
    rpg["secret_origin"] = None
    rpg["secret_payload_active"] = None
    rpg["browser_bonus"] = {"max_hp": 0, "atk": 0, "def": 0, "gold": 0}
    sync_browser_bonuses(rpg)
    bonus_gold = (rpg.get("browser_bonus") or {}).get("gold", 0)
    if bonus_gold:
        rpg["gold"] = bonus_gold
    rpg_log(
        f"Loop resets to NG+{rpg['ng_plus']} (gold {gold_spill} → +{gain} tiers, +{RPG_NG_HP_BONUS} base HP each)."
    )
    begin_maze_reassembly(rpg, duration=2.2)


def rpg_use_potion():
    rpg = ensure_rpg_state()
    potions = rpg["inventory"].get("potion", 0)
    if potions <= 0:
        rpg_log("No vials remain.")
        return
    heal = max(10, int(rpg.get("max_hp", 1) * RPG_POTION_HEAL_RATIO))
    rpg["inventory"]["potion"] = potions - 1
    prev = rpg.get("hp", 0)
    rpg["hp"] = min(rpg["max_hp"], prev + heal)
    rpg_log(f"Potion consumed (+{rpg['hp'] - prev} HP).")


def rpg_attempt_flee():
    rpg = ensure_rpg_state()
    if rpg.get("state") != "combat":
        rpg_log("No combat to flee from.")
        return
    if random.random() < 0.55:
        rpg["state"] = "secret" if rpg.get("secret_origin") else "explore"
        rpg["current_enemy"] = None
        _clear_enemy_animation(rpg)
        rpg_log("Flee successful.")
    else:
        rpg_log("Flee failed.")
        enemy_turn(rpg)


def rpg_grant_treasure(rpg):
    roll = random.random()
    modifier = active_floor_modifier(rpg)
    potion_mult = modifier.get("potion_drop_mult", 1.0) if modifier else 1.0
    potion_threshold = max(0.05, min(0.85, 0.35 * potion_mult))
    stat_threshold = min(0.95, potion_threshold + 0.35)
    if roll < potion_threshold:
        rpg["inventory"]["potion"] = rpg["inventory"].get("potion", 0) + 1
        rpg_log("Potion acquired.")
    elif roll < stat_threshold:
        if random.random() < 0.5:
            rpg["atk"] += 2
            rpg_log("Permanent bonus: +2 ATK.")
        else:
            rpg["max_hp"] += 20
            rpg["hp"] = min(rpg["max_hp"], rpg["hp"])
            rpg_log("Permanent bonus: +20 Max HP.")
    else:
        grant_rpg_relic(rpg)


def grant_rpg_relic(rpg):
    available = [rel for rel in RPG_RELICS if rel["id"] not in rpg.get("relics", [])]
    if not available:
        fallback = 100 + 25 * rpg.get("floor", 1)
        modifier = active_floor_modifier(rpg)
        if modifier:
            fallback = int(fallback * modifier.get("treasure_gold_bonus", 1.0))
        rpg["gold"] += fallback
        rpg_log(f"The vault echoes and spills {fallback} gold instead.")
        return
    relic = random.choice(available)
    start_relic_event(rpg, relic)


def apply_relic_effect(rpg, relic):
    effect = relic.get("effect")
    value = relic.get("value", 0)
    if effect == "max_hp":
        rpg["max_hp"] += value
        rpg["hp"] = min(rpg["max_hp"], rpg["hp"])
    elif effect == "atk":
        rpg["atk"] += value
    elif effect == "def":
        rpg["def"] = rpg.get("def", 0) + value
    elif effect == "gold_bonus":
        rpg["gold_bonus"] = rpg.get("gold_bonus", 0.0) + value


def advance_rpg_floor(rpg):
    rpg["floor"] = rpg.get("floor", 1) + 1
    rpg["max_floor"] = max(rpg.get("max_floor", 1), rpg["floor"])
    rpg["stairs_prompted"] = False
    rpg["shop_purchases_this_floor"] = 0
    rpg["secret_origin"] = None
    rpg["secret_payload_active"] = None
    new_floor = rpg["floor"]
    ensure_floor_theme(rpg, new_floor)
    bonus_gold = int((70 + 20 * min(new_floor, 10)) * RPG_GOLD_REWARD_SCALE)
    rpg["gold"] += bonus_gold
    base_heal_ratio = 0.5
    if is_boss_floor(new_floor):
        base_heal_ratio = 0.6
    heal = max(15, int(rpg.get("max_hp", 1) * base_heal_ratio))
    rpg["hp"] = min(rpg["max_hp"], rpg.get("hp", 0) + heal)
    aura_data, _ = _active_aura_data(rpg)
    extra_heal_ratio = aura_data.get("floor_heal")
    if extra_heal_ratio:
        extra = max(5, int(rpg["max_hp"] * extra_heal_ratio))
        rpg["hp"] = min(rpg["max_hp"], rpg["hp"] + extra)
        rpg_log(f"Aura mends +{extra} HP.")
    rpg_log(f"Advanced to Floor {new_floor}. +{bonus_gold} gold, +{heal} HP.")
    if is_boss_floor(new_floor):
        rpg_log("Boss presence detected on this floor.")
    rpg["map"] = []
    rpg["player_pos"] = None
    rpg["current_enemy"] = None
    rpg["maze_variant"] = None
    rpg["floor_modifier"] = None
    rpg["floor_modifier_floor"] = 0
    if not visit_rpg_shop(rpg):
        begin_maze_reassembly(rpg)
    handle_machine_progress_event("rpg")


def rpg_handle_command(k):
    rpg = ensure_rpg_state()
    explore_moves = {
        "w": (-1, 0),
        "s": (1, 0),
        "a": (0, -1),
        "d": (0, 1),
    }
    state = rpg.get("state")
    if state == "event":
        handle_rpg_event_command(rpg, k)
        return
    if state == "shop":
        handle_shop_command(rpg, k)
        return
    if state == "transition":
        rpg_log("The maze is still reassembling.")
        return
    if state == "combat":
        if k == "a":
            rpg_attack()
        elif k == "p":
            rpg_use_potion()
        elif k == "f":
            rpg_attempt_flee()
        else:
            rpg_log("Combat options: [A]ttack, [P]otion, [F]lee.")
    else:
        if k in explore_moves:
            dy, dx = explore_moves[k]
            rpg_move(dy, dx)
        elif k == "p":
            rpg_use_potion()
        elif k == "h":
            attempt_enter_hidden_room()
        elif k == "c":
            attempt_climb_stairs(rpg)


def _desktop_icon_count():
    return len(RPG_DESKTOP_APPS)


def _ensure_desktop_hint_state():
    if time.time() > game.get("rpg_hint_until", 0.0):
        game["rpg_desktop_hint"] = ""
        game["rpg_hint_until"] = 0.0


def set_rpg_desktop_hint(text, duration=2.5):
    game["rpg_desktop_hint"] = escape_text(text)
    game["rpg_hint_until"] = time.time() + duration


def _ensure_browser_notice_state():
    if time.time() > game.get("browser_notice_until", 0.0):
        game["browser_notice"] = ""
        game["browser_notice_until"] = 0.0


def set_browser_notice(text, duration=BROWSER_NOTICE_DURATION):
    game["browser_notice"] = escape_text(text)
    game["browser_notice_until"] = time.time() + duration


def move_rpg_desktop_cursor(direction):
    total = max(1, _desktop_icon_count())
    cols = max(1, RPG_DESKTOP_COLS)
    idx = max(0, min(total - 1, game.get("rpg_icon_index", 0)))
    row, col = divmod(idx, cols)
    if direction == "w" and row > 0:
        idx = (row - 1) * cols + col
        if idx >= total:
            idx = total - 1
    elif direction == "s":
        candidate = (row + 1) * cols + col
        if candidate < total:
            idx = candidate
    elif direction == "a" and col > 0:
        idx -= 1
    elif direction == "d":
        candidate = idx + 1
        if (col + 1) < cols and candidate < total:
            idx = candidate
    game["rpg_icon_index"] = idx


def activate_desktop_icon(index):
    total = _desktop_icon_count()
    if not (0 <= index < total):
        return "noop"
    icon = RPG_DESKTOP_APPS[index]
    ident = icon.get("id")
    if ident == "game":
        game["rpg_view"] = "game"
        set_rpg_desktop_hint("Booting GAME.EXE...")
        return "launch_game"
    if ident == "safari":
        game["rpg_view"] = "browser"
        set_browser_notice("Cache portal connected.")
        return "launch_browser"
    if ident == "trash":
        set_rpg_desktop_hint("Nothing there...")
        return "hint"
    return "noop"


def build_rpg_desktop_view(width, max_lines):
    lines = []
    header = f"{Back.BLUE}{Fore.WHITE} DustOS 98 :: Desktop {Style.RESET_ALL}"
    lines.append(pad_visible_line(header, width))
    lines.append("")
    cols = RPG_DESKTOP_COLS
    col_width = max(RPG_ICON_WIDTH + 6, width // max(1, cols))
    rows = math.ceil(_desktop_icon_count() / cols)
    idx = 0
    for _ in range(rows):
        icon_blocks = [[" " * col_width for _ in range(RPG_ICON_HEIGHT)] for _ in range(cols)]
        labels = [" " * col_width for _ in range(cols)]
        for col in range(cols):
            if idx < _desktop_icon_count():
                icon = RPG_DESKTOP_APPS[idx]
                art = RPG_ICON_ART.get(icon["id"], RPG_DEFAULT_ICON_ART)
                selected = idx == game.get("rpg_icon_index", 0)
                padded = art[:]
                if len(padded) < RPG_ICON_HEIGHT:
                    padded = padded + ["" for _ in range(RPG_ICON_HEIGHT - len(padded))]
                block = []
                for line in padded:
                    snippet = line.center(col_width)
                    block.append(snippet)
                icon_blocks[col] = block
                label = f"> {icon['name']}" if selected else f"  {icon['name']}"
                labels[col] = label.center(col_width)
            idx += 1
        for row_idx in range(RPG_ICON_HEIGHT):
            combined = "".join(icon_blocks[col][row_idx] for col in range(cols))
            lines.append(combined.rstrip())
        lines.append("".join(labels).rstrip())
        lines.append("")
    hint = game.get("rpg_desktop_hint", "")
    if hint:
        lines.append(pad_visible_line(hint, width))
    lines.append("")
    lines.append(
        pad_visible_line(
            "Use arrow keys to move · Enter to open · B to return to the desk",
            width,
        )
    )
    lines.append(pad_visible_line("[,][.] switch realms", width))
    return lines[:max_lines]


def build_browser_view(width, max_lines):
    lines = []
    header = f"{Back.BLUE}{Fore.WHITE} NET.EXE {Style.RESET_ALL} :: CACHE PORTAL"
    top, bottom = _build_crt_header(header, width)
    lines.extend([top, bottom])
    tokens = game.get("browser_tokens", 0)
    cycles = game.get("browser_cycles", 0)
    bonuses = browser_effect_totals()
    ledger_lines = [
        f"{BROWSER_CURRENCY_NAME}: {tokens}",
        f"Loop collapses logged: {cycles}",
    ]
    stat_chunks = []
    for label, key in (("HP", "max_hp"), ("ATK", "atk"), ("DEF", "def")):
        if bonuses.get(key):
            stat_chunks.append(f"+{bonuses[key]} {label}")
    if stat_chunks:
        ledger_lines.append("Baseline boosts: " + ", ".join(stat_chunks))
    if bonuses.get("gold"):
        ledger_lines.append(f"Start loops with +{bonuses['gold']} gold")
    lines += _boxed_block("Cache Ledger", ledger_lines, width)
    lines.append("")

    unlocks = set(game.get("browser_unlocks", []))
    upgrade_lines = []
    if not BROWSER_UPGRADES:
        upgrade_lines.append("No upgrades published yet.")
    else:
        for idx, upgrade in enumerate(BROWSER_UPGRADES, start=1):
            owned = upgrade["id"] in unlocks
            cost = upgrade.get("cost", 0)
            if owned:
                status = "Installed"
                color = Fore.GREEN
            elif tokens >= cost:
                status = f"Press {idx} to install"
                color = Fore.CYAN
            else:
                status = "Need shards"
                color = Fore.LIGHTBLACK_EX
            label = f"{idx}. {upgrade['name']} — {cost} shards"
            upgrade_lines.append(f"{color}{label}{Style.RESET_ALL} ({status})")
            desc = upgrade.get("desc")
            if desc:
                upgrade_lines.append(f"    {Style.DIM}{desc}{Style.RESET_ALL}")
    lines += _boxed_block("Archive Market", upgrade_lines, width)
    lines.append("")

    _ensure_browser_notice_state()
    notice = game.get("browser_notice", "")
    if notice:
        lines.append(pad_visible_line(notice, width))
        lines.append("")
    lines.append(pad_visible_line(f"Digits install · Enter hides · B closes · {BROWSER_CURRENCY_NAME} fuel upgrades", width))
    lines.append(pad_visible_line("[,][.] switch realms", width))
    return lines[:max_lines]


def browser_purchase_upgrade(index):
    if not (0 <= index < len(BROWSER_UPGRADES)):
        set_browser_notice("No such listing.")
        return False
    upgrade = BROWSER_UPGRADES[index]
    owned = set(game.get("browser_unlocks", []) or [])
    if upgrade["id"] in owned:
        set_browser_notice("Already installed.")
        return False
    cost = upgrade.get("cost", 0)
    tokens = game.get("browser_tokens", 0)
    if tokens < cost:
        set_browser_notice("Need more Cache Shards.")
        return False
    owned_list = game.setdefault("browser_unlocks", [])
    owned_list.append(upgrade["id"])
    game["browser_tokens"] = tokens - cost
    rpg = ensure_rpg_state()
    sync_browser_bonuses(rpg)
    set_browser_notice(f"Installed {upgrade['name']}.")
    save_game()
    return True


def handle_browser_input(key):
    if key == "b":
        game["rpg_view"] = "desktop"
        return "exit"
    if key == "enter":
        game["rpg_view"] = "desktop"
        return "minimize"
    if key.isdigit() and key != "0":
        browser_purchase_upgrade(int(key) - 1)
        return "purchase"
    if key == "h":
        set_browser_notice("Digits install upgrades; Enter hides; B exits.")
        return None
    set_browser_notice("Input digits to install, Enter to hide, B to exit.")
    return None


def _boxed_block(title, body_lines, width):
    inner_width = max(6, width - 2)
    title_text = f" {title.upper()} "
    title_pad = max(0, inner_width - visible_len(title_text))
    header = "╭" + title_text + "─" * title_pad + "╮"
    lines = [pad_visible_line(header, width)]
    for raw in body_lines:
        snippet = ansi_visible_slice(raw, 0, inner_width)
        pad_right = max(0, inner_width - visible_len(snippet))
        lines.append(pad_visible_line("│" + snippet + " " * pad_right + "│", width))
    lines.append(pad_visible_line("╰" + "─" * inner_width + "╯", width))
    return lines


def _stat_bar(label, current, maximum, width, color):
    max_val = max(1, maximum)
    ratio = max(0.0, min(1.0, current / max_val))
    max_visible = max(12, width - 4)
    stat_text = f"{current}/{maximum}"
    overhead = len(label) + 5 + len(stat_text)
    bar_span = max(4, max_visible - overhead)
    filled = int(bar_span * ratio)
    empty = max(0, bar_span - filled)
    bar = color + "█" * filled + Style.RESET_ALL + "░" * empty
    return f"{label}: [{bar}] {current}/{maximum}"


def _stylize_map_lines(rpg, width):
    aura_id = (rpg or {}).get("aura") or RPG_DEFAULT_AURA
    aura_color = _aura_color_code(aura_id)
    palette = {
        "@": f"{aura_color}@{Style.RESET_ALL}",
        "!": f"{Fore.RED}!{Style.RESET_ALL}",
        "E": f"{Fore.MAGENTA}E{Style.RESET_ALL}",
        "$": f"{Fore.YELLOW}${Style.RESET_ALL}",
        "+": f"{Fore.GREEN}+{Style.RESET_ALL}",
        "^": f"{Fore.LIGHTRED_EX}^{Style.RESET_ALL}",
        ">": f"{Fore.WHITE}>{Style.RESET_ALL}",
        ".": ".",
        "░": "░",
        "?": f"{Fore.LIGHTBLACK_EX}?{Style.RESET_ALL}",
        "S": f"{Fore.CYAN}S{Style.RESET_ALL}",
    }
    stylized = []
    for raw in build_rpg_map_lines(rpg):
        tokens = raw.split()
        converted = [palette.get(tok, tok) for tok in tokens]
        row = " ".join(converted)
        stylized.append(ansi_center(row, width))
    return stylized


def build_maze_panel_lines(rpg, width):
    state = rpg.get("state")
    if state == "transition":
        return build_transition_map_lines(rpg, width)
    variant = rpg.get("maze_variant") or {}
    color = _variant_color_code(variant)
    caption = f"{color}{variant.get('label', 'Unknown Layout')}{Style.RESET_ALL}"
    dims = variant.get("height"), variant.get("width")
    if all(dims):
        caption = f"{caption} {dims[0]}x{dims[1]}"
    theme = rpg.get("floor_theme")
    span_line = None
    if theme:
        span = f"Floors {theme.get('start_floor', 1)}-{theme.get('end_floor', 1)}"
        t_color = _theme_color(theme)
        span_line = f"{t_color}{theme.get('label')} · {span}{Style.RESET_ALL}"
    map_lines = _stylize_map_lines(rpg, width)
    if not map_lines:
        map_lines = ["Routes obscured in static."]
    modifier = active_floor_modifier(rpg)
    modifier_lines = []
    if modifier:
        modifier_lines = [
            f"Modifier: {modifier['name']} — {modifier['desc']}",
            "",
        ]
    header_lines = [caption]
    if span_line:
        header_lines.append(span_line)
    header_lines.append("")
    return header_lines + modifier_lines + map_lines


def _apply_scanlines(lines):
    return lines


def _build_crt_header(label, width):
    inner = max(2, width - 2)
    trimmed = ansi_visible_slice(label, 0, inner)
    visible = visible_len(trimmed)
    if visible >= inner:
        left_fill = 0
        right_fill = 0
    else:
        padding = inner - visible
        left_fill = padding // 2
        right_fill = padding - left_fill
    top = "╭" + "─" * left_fill + trimmed + "─" * right_fill + "╮"
    bottom = "╰" + "─" * inner + "╯"
    return pad_visible_line(top, width), pad_visible_line(bottom, width)


def _aura_color_code(aura_id):
    data = RPG_AURAS.get(aura_id, RPG_AURAS.get(RPG_DEFAULT_AURA, {}))
    color_name = data.get("color", "CYAN")
    return getattr(Fore, color_name, Fore.CYAN)


def _active_aura_data(rpg):
    aura_id = (rpg or {}).get("aura") or RPG_DEFAULT_AURA
    return RPG_AURAS.get(aura_id, RPG_AURAS.get(RPG_DEFAULT_AURA, {})), aura_id


def set_rpg_aura(rpg, aura_id, source=""):
    aura_id = aura_id or RPG_DEFAULT_AURA
    if aura_id not in RPG_AURAS:
        aura_id = RPG_DEFAULT_AURA
    if rpg.get("aura") == aura_id:
        return
    rpg["aura"] = aura_id
    data = RPG_AURAS.get(aura_id, {})
    label = data.get("label", aura_id.title())
    note = f"Aura tuned to {label}."
    if source:
        note = f"{source}: {note}"
    rpg_log(note)


def describe_rpg_gear_slot(rpg, slot):
    gear = rpg.get("gear", {})
    equipped = gear.get(slot)
    if not equipped:
        return "None"
    return equipped


def _needs_swap_confirmation(rpg, item):
    slot = item.get("slot")
    if slot not in {"weapon", "armor", "trinket", "aura"}:
        return False
    if slot == "aura":
        current_aura = rpg.get("aura")
        return bool(current_aura and current_aura != item.get("aura"))
    gear = rpg.get("gear", {})
    return bool(gear.get(slot))


def _current_slot_label(rpg, slot):
    if slot == "aura":
        aura_id = rpg.get("aura")
        data = RPG_AURAS.get(aura_id, {})
        return data.get("label", aura_id or "None")
    return describe_rpg_gear_slot(rpg, slot)


def _shop_inventory_for_floor(rpg):
    floor = rpg.get("floor", 1)
    owned = set(rpg.get("shop_owned", []))
    eligible = []
    for item in RPG_SHOP_STOCK:
        if floor >= item.get("floor_req", 1) and item.get("id") not in owned:
            eligible.append(copy.deepcopy(item))
    random.shuffle(eligible)
    limit = min(len(eligible), SHOP_MAX_ITEMS_PER_VISIT)
    return eligible[:limit]


def _shop_locked_first_run(rpg):
    return rpg.get("ng_plus", 0) <= 0


def visit_rpg_shop(rpg):
    if _shop_locked_first_run(rpg):
        rpg_log("Shop locked until a loop is completed.")
        return False
    stock = _shop_inventory_for_floor(rpg)
    rpg["shop_stock"] = stock
    if not stock:
        return False
    rpg["state"] = "shop"
    rpg["shop_purchases_this_floor"] = 0
    rpg["shop_locked_first_run"] = False
    rpg["shop_pending_item"] = None
    rpg_log("Shop inventory online for this floor.")
    return True


def purchase_rpg_item(rpg, item):
    cost = item.get("cost", 0)
    if _shop_locked_first_run(rpg):
        rpg_log("Shop unavailable until the first loop ends.")
        return False
    if rpg.get("gold", 0) < cost:
        rpg_log("Insufficient gold for that item.")
        return False
    rpg["gold"] -= cost
    slot = item.get("slot")
    if slot == "weapon":
        equip_rpg_weapon(rpg, item)
    elif slot == "armor":
        equip_rpg_armor(rpg, item)
    elif slot == "aura":
        set_rpg_aura(rpg, item.get("aura"), source="Shop dye swap")
    elif slot == "trinket":
        equip_rpg_trinket(rpg, item)
    elif slot == "boon":
        apply_shop_boon(rpg, item)
    else:
        rpg_log("Item slot unsupported; effect cancelled.")
    if item.get("id") and slot in {"weapon", "armor", "trinket", "aura"}:
        owned = rpg.setdefault("shop_owned", [])
        if item["id"] not in owned:
            owned.append(item["id"])
    rpg["shop_pending_item"] = None
    return True


def close_rpg_shop(rpg):
    if rpg.get("state") == "shop":
        rpg_log("Shop closed for this floor.")
    rpg["shop_stock"] = []
    rpg["shop_pending_item"] = None
    begin_maze_reassembly(rpg)


def select_rpg_shop_item(rpg, index, force=False):
    stock = rpg.get("shop_stock") or []
    if not stock:
        rpg_log("All crates already sold.")
        return
    if not (0 <= index < len(stock)):
        rpg_log("Invalid crate index.")
        return
    if not force and rpg.get("shop_pending_item"):
        rpg["shop_pending_item"] = None
    if rpg.get("shop_purchases_this_floor", 0) >= SHOP_PURCHASE_LIMIT:
        rpg_log("Trade limit reached for this floor.")
        return
    item = stock[index]
    if not force and _needs_swap_confirmation(rpg, item):
        slot = item.get("slot")
        current = _current_slot_label(rpg, slot)
        if slot == "aura" and not rpg.get("aura"):
            current = "no aura"
        rpg["shop_pending_item"] = {"index": index}
        rpg_log(
            f"Swap {current} for {item['name']}? Press [Y] to confirm or [N] to stand pat."
        )
        return
    if purchase_rpg_item(rpg, item):
        rpg["shop_purchases_this_floor"] = rpg.get("shop_purchases_this_floor", 0) + 1
        stock.pop(index)
        if rpg.get("shop_purchases_this_floor", 0) >= SHOP_PURCHASE_LIMIT and stock:
            rpg_log("Trade limit reached; remaining crates sealed.")
            stock.clear()
            close_rpg_shop(rpg)
            return
        if not stock:
            rpg_log("All crates sold.")
            close_rpg_shop(rpg)


def build_shop_panel(rpg):
    lines = [
        "Shop crate rattles between floors.",
        f"Gold: {rpg.get('gold', 0)}",
        f"Weapon: {describe_rpg_gear_slot(rpg, 'weapon')}  Armor: {describe_rpg_gear_slot(rpg, 'armor')}",
        f"Trinket: {describe_rpg_gear_slot(rpg, 'trinket')}",
    ]
    aura_data, _ = _active_aura_data(rpg)
    lines.append(f"Aura: {aura_data.get('label', 'Unknown')}")
    stock = rpg.get("shop_stock") or []
    if not stock:
        lines.append("")
        lines.append("No wares remain.")
        return lines
    lines.append("")
    if _shop_locked_first_run(rpg):
        lines.append(f"{Style.DIM}Shop locked until one loop is cleared.{Style.RESET_ALL}")
        lines.append("")
    limit_note = f"{Style.DIM}Limit: {SHOP_PURCHASE_LIMIT} trades per floor.{Style.RESET_ALL}"
    lines.append(limit_note)
    if rpg.get("shop_pending_item"):
        lines.append(f"{Fore.YELLOW}Swap pending — [Y] confirm or [N] cancel.{Style.RESET_ALL}")
    lines.append("")
    for idx, item in enumerate(stock, start=1):
        affordable = rpg.get("gold", 0) >= item.get("cost", 0)
        color = Fore.CYAN if affordable else Fore.LIGHTBLACK_EX
        desc = item.get("desc")
        lines.append(
            f"{color}{idx}. {item['name']} — {item.get('cost', 0)} gold{Style.RESET_ALL}"
        )
        if desc:
            lines.append(f"    {Style.DIM}{desc}{Style.RESET_ALL}")
    lines.append("")
    lines.append("Digits browse · [Y/N] decide swaps · [Q] exit")
    return lines


def handle_shop_command(rpg, key):
    pending = rpg.get("shop_pending_item")
    if key == "y":
        if pending:
            select_rpg_shop_item(rpg, pending.get("index", -1), force=True)
        else:
            rpg_log("No swap awaiting confirmation.")
        return
    if key == "n":
        if pending:
            rpg["shop_pending_item"] = None
            rpg_log("Loadout unchanged.")
        else:
            rpg_log("Nothing to cancel.")
        return
    if key == "q":
        rpg_log("Shop exit confirmed.")
        close_rpg_shop(rpg)
        return
    if key.isdigit() and key != "0":
        select_rpg_shop_item(rpg, int(key) - 1)
        return
    rpg_log("Use digits to pick crates; Y/N confirm swaps, Q exits.")


def equip_rpg_weapon(rpg, item):
    bonus = int(item.get("atk_bonus", 0))
    prev = rpg.get("gear_atk_bonus", 0)
    rpg["atk"] = max(1, rpg.get("atk", RPG_PLAYER_START_ATK) - prev)
    rpg["gear_atk_bonus"] = bonus
    rpg["atk"] += bonus
    rpg.setdefault("gear", {})["weapon"] = item.get("name", "Unknown Blade")
    rpg_log(f"Equipped {item.get('name', 'weapon')} (+{bonus} ATK).")
    aura_hint = item.get("aura_hint")
    if aura_hint:
        set_rpg_aura(rpg, aura_hint, source="Weapon resonance")


def equip_rpg_armor(rpg, item):
    bonus = int(item.get("def_bonus", 0))
    prev = rpg.get("gear_def_bonus", 0)
    rpg["def"] = max(0, rpg.get("def", 0) - prev)
    rpg["gear_def_bonus"] = bonus
    rpg["def"] += bonus
    rpg.setdefault("gear", {})["armor"] = item.get("name", "Unknown Armor")
    rpg_log(f"Equipped {item.get('name', 'armor')} (+{bonus} DEF).")


def _apply_trinket_stats(rpg, bonus, remove=False):
    if not bonus:
        return
    sign = -1 if remove else 1
    for key, value in bonus.items():
        if not value:
            continue
        adj = sign * value
        if key == "max_hp":
            new_max = max(1, rpg.get("max_hp", RPG_PLAYER_START_HP) + adj)
            current_hp = rpg.get("hp", new_max)
            if remove:
                adjusted = min(new_max, current_hp)
            else:
                adjusted = min(new_max, current_hp + value)
            rpg["max_hp"] = new_max
            rpg["hp"] = max(1, adjusted)
        elif key == "atk":
            rpg["atk"] = max(1, rpg.get("atk", RPG_PLAYER_START_ATK) + adj)
        elif key == "def":
            rpg["def"] = max(0, rpg.get("def", 0) + adj)


def equip_rpg_trinket(rpg, item):
    bonus = copy.deepcopy(item.get("trinket") or {})
    prev = copy.deepcopy(rpg.get("gear_trinket_bonus") or {})
    if prev:
        _apply_trinket_stats(rpg, prev, remove=True)
    if bonus:
        _apply_trinket_stats(rpg, bonus)
    rpg["gear_trinket_bonus"] = bonus
    rpg.setdefault("gear", {})["trinket"] = item.get("name", "Unknown Trinket")
    blips = []
    if bonus.get("max_hp"):
        blips.append(f"+{bonus['max_hp']} HP")
    if bonus.get("atk"):
        blips.append(f"+{bonus['atk']} ATK")
    if bonus.get("def"):
        blips.append(f"+{bonus['def']} DEF")
    if bonus.get("crit_bonus"):
        blips.append(f"+{int(round(bonus['crit_bonus'] * 100))}% crit")
    summary = ", ".join(blips) if blips else "latent circuit hum"
    rpg_log(f"Equipped {item.get('name', 'trinket')} ({summary}).")


def apply_shop_boon(rpg, item):
    floor = max(1, rpg.get("floor", 1))
    name = item.get("name", "Boon")

    def _heal():
        heal = max(20, int(rpg.get("max_hp", 1) * random.uniform(0.25, 0.45)))
        rpg["hp"] = min(rpg.get("max_hp", 1), rpg.get("hp", 1) + heal)
        return f"+{heal} HP"

    def _gold():
        gold_gain = random.randint(70, 140) + floor * 15
        rpg["gold"] = rpg.get("gold", 0) + gold_gain
        return f"+{gold_gain} gold"

    def _xp():
        xp_gain = random.randint(60, 140) + floor * 8
        rpg["xp"] = rpg.get("xp", 0) + xp_gain
        check_rpg_level_up(rpg)
        return f"+{xp_gain} XP"

    def _potion():
        inv = rpg.setdefault("inventory", {})
        inv["potion"] = inv.get("potion", 0) + 1
        return "+1 potion"

    def _aura():
        aura_id = random.choice(list(RPG_AURAS.keys()))
        set_rpg_aura(rpg, aura_id, source=name)
        label = RPG_AURAS.get(aura_id, {}).get("label", aura_id.title())
        return f"Aura set to {label}"

    def _tokens():
        gain = random.randint(1, 3)
        game["browser_tokens"] = game.get("browser_tokens", 0) + gain
        plural = "s" if gain != 1 else ""
        return f"+{gain} cache shard{plural}"

    effect = random.choice([_heal, _gold, _xp, _potion, _aura, _tokens])
    message = effect()
    rpg_log(f"{name}: {message}.")


def build_rpg_game_view(rpg, width, max_lines):
    lines = []
    floor = rpg.get("floor", 1)
    state = rpg.get("state", "explore")
    title_label = f"{Back.BLUE}{Fore.WHITE} GAME.EXE {Style.RESET_ALL} :: FLOOR {floor:02d}"
    header_top, header_bottom = _build_crt_header(title_label, width)
    lines.append(header_top)
    lines.append(header_bottom)

    xp_goal = rpg.get("level", 1) * 120
    vitals_body = [
        f"LV {rpg['level']:02d}   GOLD {rpg['gold']}   POTIONS {rpg['inventory'].get('potion', 0)}",
        _stat_bar("HP", rpg["hp"], rpg["max_hp"], width, Fore.GREEN),
        _stat_bar("XP", rpg["xp"], xp_goal, width, Fore.CYAN),
        f"ATK {rpg['atk']}  DEF {rpg.get('def', 0)}  RELICS {len(rpg.get('relics', []))}",
        f"Stairs ready on Floor {floor:02d}  Best {rpg.get('max_floor', 1):02d}",
    ]
    vitals_body.append(
        f"WPN {describe_rpg_gear_slot(rpg, 'weapon')}  ARM {describe_rpg_gear_slot(rpg, 'armor')}"
    )
    vitals_body.append(f"TRK {describe_rpg_gear_slot(rpg, 'trinket')}")
    aura_data, aura_id = _active_aura_data(rpg)
    vitals_body.append(f"Aura: {aura_data.get('label', aura_id.title())}")
    theme = rpg.get("floor_theme") or floor_theme_for_floor(floor)
    if theme:
        span = f"Floors {theme.get('start_floor', floor)}-{theme.get('end_floor', floor)}"
        color = _theme_color(theme)
        vitals_body.append(f"{color}Theme: {theme.get('label')} ({span}){Style.RESET_ALL}")
        desc = theme.get("desc")
        if desc:
            vitals_body.append(f"   {Style.DIM}{desc}{Style.RESET_ALL}")
    modifier = active_floor_modifier(rpg)
    if modifier:
        vitals_body.append(f"Modifier: {modifier['name']}")
    if is_boss_floor(floor):
        boss = RPG_BOSSES.get(floor)
        if boss:
            vitals_body.append(f"Boss: {boss.get('name')}")
    lines += _boxed_block("Vitals", vitals_body, width)
    lines.append("")

    room = current_rpg_room(rpg)
    at_stairs = room and room.get("type") in {"exit", "stairs"}
    if state == "combat" and rpg.get("current_enemy"):
        enemy = rpg["current_enemy"]
        color = Fore.MAGENTA if enemy.get("elite") else Fore.RED
        header = (
            f"{color}{enemy['name']}{Style.RESET_ALL}  HP {enemy['hp']}/{enemy['max_hp']}  ATK {enemy['atk']}"
        )
        bar = _stat_bar("ENEMY", enemy["hp"], enemy["max_hp"], width, color)
        art_lines = build_enemy_ascii_lines(rpg, width)
        encounter_body = [header, bar]
        if art_lines:
            encounter_body.append("")
            encounter_body.extend(art_lines)
            encounter_body.append("")
        status = "Status: Charging" if enemy.get("charging") else "Status: Tracking"
        encounter_body.append(status)
    elif state == "shop":
        encounter_body = [
            "Shop interface active.",
            "State: Shop",
        ]
    elif state == "transition":
        encounter_body = [
            "Between floors in raw static.",
            "State: Maze reassembling",
        ]
    elif state == "event":
        encounter_body = build_event_panel_lines(rpg, width)
    elif state == "secret":
        payload = rpg.get("secret_payload_active") or "annex"
        encounter_body = [
            f"Secret annex active ({payload}).",
            "State: Secret",
        ]
    else:
        encounter_body = [
            f"Exploring {describe_rpg_room(room)}",
            f"State: {state.title()}",
        ]
        if at_stairs:
            encounter_body.append("Stairs here — press [C] to climb.")
        theme = rpg.get("floor_theme")
        if theme and theme.get("label"):
            color = _theme_color(theme)
            encounter_body.append(f"{color}Theme: {theme['label']}{Style.RESET_ALL}")
    lines += _boxed_block("Encounter", encounter_body, width)
    lines.append("")

    map_lines = build_maze_panel_lines(rpg, width - 4)
    lines += _boxed_block("Maze", map_lines, width)
    lines.append("")

    log_entries = rpg.get("log", [])[-5:]
    if not log_entries:
        log_entries = ["Sensors idle…"]
    log_body = [f"{idx + 1:02d}. {entry}" for idx, entry in enumerate(log_entries)]
    lines += _boxed_block("Log", log_body, width)
    lines.append("")

    if state == "shop":
        lines += _boxed_block("Shop Cart", build_shop_panel(rpg), width)
        lines.append("")

    hidden_adjacent = bool(_adjacent_hidden_rooms(rpg)) if state == "explore" else False

    if state == "combat":
        action_line = "▶ [A]ttack │ [P]otion │ [F]lee │ Enter disabled"
    elif state == "shop":
        action_line = "▶ Digits pick │ [Y/N] confirm │ [Q]uit cart"
    elif state == "transition":
        action_line = "▶ Maze reassembling… hold position"
    elif state == "event":
        action_line = "▶ Event: follow on-screen prompts"
    elif state == "secret":
        action_line = "▶ WASD move │ P potion │ C seam exit"
    else:
        extras = []
        if hidden_adjacent:
            extras.append("H slip seam")
        if at_stairs:
            extras.append("C climb")
        extra_text = " │ " + " │ ".join(extras) if extras else ""
        action_line = f"▶ WASD move │ P potion{extra_text} │ Enter minimize │ B close"
    lines.append(pad_visible_line(action_line, width))
    lines.append(pad_visible_line("[,][.] switch realms", width))

    shaded = _apply_scanlines(lines)
    return shaded[:max_lines]


def build_monitor_frame(inner_lines, glass_width, term_w, term_h, max_inner_lines):
    case_width = min(glass_width + 10, term_w - 4)
    case_width = max(12, case_width)
    glass_width = min(glass_width, case_width - 2)
    gap_total = max(0, case_width - glass_width - 2)
    gap_left = gap_total // 2
    gap_right = gap_total - gap_left
    outer_width = case_width + 2
    left_pad = max(0, (term_w - outer_width) // 2)
    case_extra = 9
    available = max(4, term_h - case_extra)
    max_glass_lines = min(max_inner_lines, max(4, available))
    content = inner_lines[:max_glass_lines]
    while len(content) < max_glass_lines:
        content.append("")
    body = []
    body.append(" " * left_pad + "╭" + "─" * case_width + "╮")
    body.append(" " * left_pad + "│" + " " * case_width + "│")
    body.append(
        " " * left_pad
        + "│"
        + " " * gap_left
        + "┌"
        + "─" * glass_width
        + "┐"
        + " " * gap_right
        + "│"
    )
    for raw in content:
        padded = pad_visible_line(raw, glass_width)
        body.append(
            " " * left_pad
            + "│"
            + " " * gap_left
            + "│"
            + padded
            + "│"
            + " " * gap_right
            + "│"
        )
    body.append(
        " " * left_pad
        + "│"
        + " " * gap_left
        + "└"
        + "─" * glass_width
        + "┘"
        + " " * gap_right
        + "│"
    )
    knob = ("◉" + " " * max(0, case_width - 6) + "▢").center(case_width)
    body.append(" " * left_pad + "│" + knob + "│")
    body.append(" " * left_pad + "╰" + "─" * case_width + "╯")
    stand_center = left_pad + (outer_width // 2)
    body.append(" " * max(0, stand_center - 2) + "╱╲")
    body.append(" " * max(0, stand_center - 4) + "╱────╲")
    body.append(" " * max(0, stand_center - 7) + "└────────┘")
    visible_height = len(body)
    if visible_height >= term_h:
        return body[:term_h]
    top_pad = max(0, (term_h - visible_height) // 2)
    output = ["" for _ in range(top_pad)] + body
    while len(output) < term_h:
        output.append("")
    return output[:term_h]


def handle_rpg_desktop_input(key):
    if key == "b":
        return "exit"
    if key in {"w", "a", "s", "d"}:
        move_rpg_desktop_cursor(key)
        return "move"
    if key == "enter":
        return activate_desktop_icon(game.get("rpg_icon_index", 0))
    return None


def render_rpg_screen():
    global last_render, last_size
    rpg = ensure_rpg_state()
    tick_rpg_state(rpg)
    term_w, term_h = get_term_size()
    current_size = (term_w, term_h)
    resized = current_size != last_size
    usable_w = max(28, int(term_w * 0.72))
    glass_cap = max(6, term_w - 8)
    glass_width = min(usable_w, glass_cap)
    if glass_cap >= 36:
        glass_width = max(36, glass_width)
    max_lines = max(14, term_h - 16)
    view = game.get("rpg_view", "desktop")
    _ensure_desktop_hint_state()
    if view == "desktop" and game.get("rpg_unlocked", False) and not game.get("rpg_tutorial_shown", False):
        set_rpg_desktop_hint("Use arrows to pick GAME.EXE or NET.EXE, Enter to launch, B to return.", duration=4.0)
        game["rpg_tutorial_shown"] = True
    if view == "desktop":
        inner_lines = build_rpg_desktop_view(glass_width, max_lines)
    elif view == "browser":
        inner_lines = build_browser_view(glass_width, max_lines)
    else:
        inner_lines = build_rpg_game_view(rpg, glass_width, max_lines)
    monitor_lines = build_monitor_frame(inner_lines, glass_width, term_w, term_h, max_lines)
    tab_line = build_tab_bar_text("rpg")
    if tab_line:
        monitor_lines.insert(0, ansi_center(tab_line, term_w))
        monitor_lines.insert(1, "")
    while len(monitor_lines) < term_h:
        monitor_lines.append("")
    prepared = [pad_visible_line(line, term_w) for line in monitor_lines[:term_h]]
    escape_banner = build_escape_banner_lines(term_w)
    if escape_banner:
        prepared = escape_banner + prepared
        prepared = prepared[:term_h]
    banner_line = build_time_banner_line(term_w)
    if banner_line:
        prepared = [banner_line] + prepared
        prepared = prepared[:term_h]
    if resized:
        sys.stdout.write("\033[2J\033[H")
        last_size = current_size
        last_render = ""
    frame = "\033[H" + "\n".join(prepared)
    if frame != last_render:
        sys.stdout.write(frame)
        sys.stdout.flush()
        last_render = frame

def main_loop():
    global KEY_PRESSED, running, work_timer, last_tick_time, last_manual_time, last_render
    request_fullscreen()
    ensure_terminal_capacity(
        LARGEST_PANEL_MIN_COLS,
        LARGEST_PANEL_MIN_ROWS,
        reason="largest Diverter interface",
    )
    run_intro_boot_sequence()
    choose_save_slot()
    load_game()
    try:
        if getattr(config, "AUTO_BALANCE_UPGRADES", False) and getattr(
            config, "BALANCE_ADJUSTMENTS", None
        ):
            lines = ["The balancer adjusted upgrade costs:"]
            for table_name, aid, old, new in config.BALANCE_ADJUSTMENTS:
                lines.append(f"{table_name}: {aid}: {old} -> {new}")
            tmp = boxed_lines(lines, title=" Balancer ", pad_top=1, pad_bottom=1)
            render_frame(tmp)
            time.sleep(1.2)
    except Exception:
        pass
    last_tick_time = time.time()
    threading.Thread(target=key_listener, daemon=True).start()

    if not game.get("intro_played", False):
        set_settings_notice("Console boot complete.", duration=3.0)
        game["intro_played"] = True
        save_game()

    if game.get("inspiration_resets", 0) > 0 and not game.get("inspiration_unlocked", False):
        game["inspiration_unlocked"] = True
        save_game()
    current_screen = "work"
    global view_offset_x, view_offset_y
    try:
        while running:
            loop_start = time.time()
            try:
                work_tick()
                update_resonance(0.05)
                rpg_state = game.get("rpg_data")
                if isinstance(rpg_state, dict):
                    tick_rpg_state(rpg_state)

                if not game.get("mystery_revealed", False) and game.get("money_since_reset", 0) >= 100:
                    game["mystery_revealed"] = True
                    set_settings_notice("Deeper escape diagnostics unlocked.", duration=3.0)
                    attempt_reveal("escape_window")
                    refresh_knowledge_flags()
                    save_game()
                    last_render = ""

                if current_screen == "rpg":
                    render_rpg_screen()
                else:
                    render_ui(screen=current_screen)
                
                if KEY_PRESSED:
                    k_raw = KEY_PRESSED
                    KEY_PRESSED = None
                    k = None

                    if isinstance(k_raw, str) and k_raw.startswith("\x1b"):
                        if current_screen == "settings" and k_raw in {"\x1b[A", "\x1b[B"}:
                            delta = -1 if k_raw == "\x1b[A" else 1
                            settings_menu_move_cursor(delta)
                            continue
                        arrow_map = {"\x1b[A": "w", "\x1b[B": "s", "\x1b[C": "d", "\x1b[D": "a"}
                        if current_screen == "rpg" and k_raw in arrow_map:
                            k = arrow_map[k_raw]
                        elif k_raw in arrow_map:
                            if k_raw == "\x1b[A":
                                view_offset_y = max(0, view_offset_y - 1)
                            elif k_raw == "\x1b[B":
                                view_offset_y = max(0, view_offset_y + 1)
                            elif k_raw == "\x1b[C":
                                view_offset_x = max(0, view_offset_x + 2)
                            elif k_raw == "\x1b[D":
                                view_offset_x = max(0, view_offset_x - 2)
                            continue
                        else:
                            continue

                    if k is None:
                        if isinstance(k_raw, str) and k_raw in {"\r", "\n", "enter"}:
                            k = "enter"
                        else:
                            try:
                                k = k_raw.lower()
                            except Exception:
                                k = k_raw

                    if k == "g":
                        if guide_available():
                            open_guide_book()
                            if current_screen == "rpg":
                                render_rpg_screen()
                            else:
                                render_ui(screen=current_screen)
                        else:
                            set_settings_notice(
                                "Field Guide offline. Earn more to sync it up.",
                                duration=2.5,
                            )
                        continue
                    if k in (",", "."):
                        direction = -1 if k == "," else 1
                        next_screen = cycle_screen(current_screen, direction)
                        if next_screen != current_screen:
                            current_screen = next_screen
                            if current_screen != "rpg":
                                last_render = ""
                            continue
                    elif k == "q":
                        if current_screen == "rpg":
                            rpg = ensure_rpg_state()
                            if game.get("rpg_view") == "game" and rpg.get("state") == "shop":
                                handle_shop_command(rpg, "q")
                                continue
                        clear_screen()
                        last_render = ""
                        save_game()
                        running = False
                        break
                    elif current_screen == "rpg":
                        rpg = ensure_rpg_state()
                        view = game.get("rpg_view", "desktop")
                        if view == "desktop":
                            result = handle_rpg_desktop_input(k)
                            if result == "exit":
                                current_screen = "work"
                            continue
                        elif view == "browser":
                            outcome = handle_browser_input(k)
                            if outcome == "exit":
                                current_screen = "work"
                            continue
                        else:
                            if k == "enter":
                                if rpg.get("state") == "shop":
                                    handle_shop_command(rpg, "c")
                                    continue
                                if rpg.get("state") == "combat":
                                    rpg_log("Can't minimize the fight.")
                                else:
                                    game["rpg_view"] = "desktop"
                            elif k == "b":
                                if rpg.get("state") == "shop":
                                    rpg_log("Use C to climb out of the shop.")
                                    continue
                                if rpg.get("state") == "combat":
                                    rpg_log("The foe blocks your escape!")
                                else:
                                    game["rpg_view"] = "desktop"
                                    current_screen = "work"
                            else:
                                rpg_handle_command(k)
                    elif current_screen == "settings":
                        result = handle_settings_menu_input(k)
                        if result == "back":
                            current_screen = "work"
                            last_render = ""
                        elif isinstance(result, tuple) and result and result[0] == "switch":
                            _, target = result
                            current_screen = target
                            last_render = ""
                        elif result == "refresh":
                            last_render = ""
                        continue
                    elif k == "w":
                        now = time.time()
                        record_manual_press(now)
                        if now - last_manual_time > 0.1:
                            gain, eff_delay = compute_gain_and_delay(auto=False)
                            if not game.get("auto_work_unlocked", False):
                                work_timer = 0
                            if perform_work(gain, eff_delay, manual=True):
                                last_manual_time = now
                    elif k == "u":
                        current_screen = "work"
                        clear_screen()
                        open_upgrade_menu()
                        render_ui(screen=current_screen)
                    elif k == "j" and current_screen == "work":
                        open_blackjack_layer()
                        current_screen = "work"
                    elif k == "h" and current_screen == "work":
                        if not challenge_feature_ready():
                            tmp = boxed_lines(
                                [
                                    "Challenge board offline.",
                                    "Install the Instability Array in the Stabilizer (T) to enable trials.",
                                ],
                                title=" Challenge Board ",
                                pad_top=1,
                                pad_bottom=1,
                            )
                            render_frame(tmp)
                            time.sleep(1.0)
                        else:
                            open_challenge_board()
                            render_ui(screen=current_screen)
                    elif k == "r" and current_screen == "work":
                        challenge_layer_reset()
                    elif k == "l" and current_screen == "work":
                        if manual_collapse_available():
                            manual_stability_collapse()
                            render_ui(screen=current_screen)
                        else:
                            set_settings_notice(
                                manual_collapse_requirement_text(),
                                duration=2.5,
                            )
                    elif k == "t" and not game.get("wake_timer_infinite", False):
                        current_screen = "work"
                        clear_screen()
                        open_wake_timer_menu()
                        render_ui(screen=current_screen)
                    elif k == "m" and current_screen == "work":
                        current_screen = "work"
                        clear_screen()
                        open_escape_machine_panel()
                        render_ui(screen=current_screen)
                    elif k == "v" and current_screen == "work":
                        current_screen = "work"
                        clear_screen()
                        open_credits_panel()
                        render_ui(screen=current_screen)
                    elif k == "i":
                        reset_for_inspiration()
                        current_screen = "work"
                    elif k == "c":
                        reset_for_concepts()
                        current_screen = "work"
                    elif current_screen == "work" and k == "x":
                        if breach_key_available() and not breach_door_is_open():
                            perform_breach_unlock_sequence()
                            last_render = ""
                        elif breach_door_is_open():
                            game["rpg_view"] = "desktop"
                            current_screen = "rpg"
                            last_render = ""
                        else:
                            tmp = boxed_lines(
                                ["Breach door locked. Key required."],
                                title=" Breach Door ",
                                pad_top=1,
                                pad_bottom=1,
                            )
                            render_frame(tmp)
                            time.sleep(0.8)
                        continue
                    elif (
                        current_screen == "work"
                        and k == "1"
                        and game.get("inspiration_unlocked", False)
                    ):
                        current_screen = "inspiration"
                    elif (
                        current_screen == "work"
                        and k == "2"
                        and (
                            game.get("concepts_unlocked", False)
                            or game.get("money_since_reset", 0) >= CONCEPTS_UNLOCK_MONEY
                        )
                    ):
                        current_screen = "concepts"
                    elif (
                        current_screen == "work"
                        and k == "3"
                        and automation_lab_available()
                    ):
                        current_screen = "automation"
                    elif current_screen == "inspiration":
                        if k == "b":
                            current_screen = "work"
                        elif k == "z":
                            total_pages = max(1, game.get("insp_page_pages", 1))
                            game["insp_page"] = max(0, min(game.get("insp_page", 0) - 1, total_pages - 1))
                        elif k == "x":
                            total_pages = max(1, game.get("insp_page_pages", 1))
                            if game.get("insp_page", 0) < total_pages - 1:
                                game["insp_page"] = game.get("insp_page", 0) + 1
                        elif k.isdigit():
                            idx = get_tree_selection(INSPIRE_UPGRADES, "insp_page", k)
                            if 0 <= idx < len(INSPIRE_UPGRADES):
                                buy_tree_upgrade(INSPIRE_UPGRADES, idx)
                            time.sleep(0.2)
                    elif current_screen == "concepts":
                        if k == "b":
                            current_screen = "work"
                        elif k == "z":
                            total_pages = max(1, game.get("concept_page_pages", 1))
                            game["concept_page"] = max(0, min(game.get("concept_page", 0) - 1, total_pages - 1))
                        elif k == "x":
                            total_pages = max(1, game.get("concept_page_pages", 1))
                            if game.get("concept_page", 0) < total_pages - 1:
                                game["concept_page"] = game.get("concept_page", 0) + 1
                        elif k.isdigit():
                            idx = get_tree_selection(CONCEPT_UPGRADES, "concept_page", k)
                            if 0 <= idx < len(CONCEPT_UPGRADES):
                                buy_tree_upgrade(CONCEPT_UPGRADES, idx)
                            time.sleep(0.2)
                    elif current_screen == "automation":
                        if k == "b":
                            current_screen = "work"
                        elif k == "z":
                            total_pages = max(1, game.get("automation_page_pages", 1))
                            game["automation_page"] = max(
                                0,
                                min(game.get("automation_page", 0) - 1, total_pages - 1),
                            )
                        elif k == "x":
                            total_pages = max(1, game.get("automation_page_pages", 1))
                            if game.get("automation_page", 0) < total_pages - 1:
                                game["automation_page"] = game.get("automation_page", 0) + 1
                        elif k == "e":
                            exchange_signal_bits()
                        elif k == "r":
                            exchange_signal_bits(prompt=True)
                        elif k.isdigit():
                            idx = get_tree_selection(AUTOMATION_UPGRADES, "automation_page", k)
                            if 0 <= idx < len(AUTOMATION_UPGRADES):
                                buy_tree_upgrade(AUTOMATION_UPGRADES, idx)
                            time.sleep(0.2)
            finally:
                loop_elapsed = time.time() - loop_start
                if loop_elapsed < MAIN_LOOP_MIN_DT:
                    time.sleep(MAIN_LOOP_MIN_DT - loop_elapsed)
    except Exception:
        traceback.print_exc()
        running = False
    finally:
        save_game()


if __name__ == "__main__":
    try:
        request_fullscreen()
        run_terminal_scale_calculator()
        main_loop()
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")