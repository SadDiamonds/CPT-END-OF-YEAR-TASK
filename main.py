import json, os, time, sys, threading, shutil, math, select, random, textwrap, subprocess, re, traceback, copy

try:
    import msvcrt
except ImportError:
    msvcrt = None

try:
    import wcwidth

    _wcwidth = wcwidth.wcwidth
except ImportError:
    _wcwidth = None

try:
    import colorama
    from colorama import Fore, Back, Style
except ImportError:
    print("Colorama not found, installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama"])
    import colorama
    from colorama import Fore, Back, Style
colorama.init(autoreset=False)

from ascii_art import LAYER_0_DESK, UPGRADE_ART
import config
from config import (
    BASE_MONEY_GAIN,
    BASE_WORK_DELAY,
    BASE_MONEY_MULT,
    INSPIRE_UPGRADES, 
    CONCEPT_UPGRADES,
    INSPIRATION_UNLOCK_MONEY,
    CONCEPTS_UNLOCK_MONEY,
    MOTIVATION_MAX,
    MAX_MOTIVATION_MULT,
    FOCUS_BOOST_FACTOR,
    FOCUS_DURATION,
    FOCUS_CHARGE_PER_EARN,
    FOCUS_MAX,
    CHARGE_THRESHOLDS,
    BATTERY_TIERS,
    BORDERS,
    UPGRADES,
    LAYER_FLOW,
    LAYER_BY_KEY,
    LAYER_BY_ID,
    CURRENCY_SYMBOL,
    WAKE_TIMER_START,
    WAKE_TIMER_UPGRADES,
    STABILITY_CURRENCY_NAME,
    STABILITY_REWARD_MULT,
    STABILITY_REWARD_EXP,
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
    RPG_ENEMIES,
    format_number,
)

import blackjack

RPG_DESKTOP_APPS = [
    {
        "id": "game",
        "name": "GAME.EXE",
        "icon": "■",
        "tooltip": "Boot the Anti-Realm client.",
    },
    {
        "id": "safari",
        "name": "Safari",
        "icon": "◎",
        "tooltip": "Nothing beyond the loop answers.",
    },
    {
        "id": "trash",
        "name": "Trash Bin",
        "icon": "♻",
        "tooltip": "Already empty. Lucky.",
    },
]

RPG_DESKTOP_COLS = 2

RPG_ICON_ART = {
    "game": [
        "┌──────────┐",
        "│ █▓██▓██ │",
        "│  GAME.EXE│",
        "│  ENTER→  │",
        "└──────────┘",
    ],
    "safari": [
        "┌──────────┐",
        "│  ╲ ╱  ☼ │",
        "│   ⌖  /  │",
        "│  ╱ ╲     │",
        "└──────────┘",
    ],
    "trash": [
        "┌──────────┐",
        "│  ______  │",
        "│ | ____ | │",
        "│ |______| │",
        "└──────────┘",
    ],
}

_DEFAULT_ICON_ART = [
    "┌────┐",
    "│ ?? │",
    "│ ?? │",
    "└────┘",
]

RPG_ICON_HEIGHT = max(len(art) for art in list(RPG_ICON_ART.values()) + [_DEFAULT_ICON_ART])
RPG_ICON_WIDTH = max(
    max(len(line) for line in art)
    for art in list(RPG_ICON_ART.values()) + [_DEFAULT_ICON_ART]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
LEGACY_SAVE_PATH = os.path.join(DATA_DIR, "save.json")
SAVE_SLOT_COUNT = 4
ACTIVE_SLOT_INDEX = 0


RPG_MAP_WIDTH = 5
RPG_MAP_HEIGHT = 5
RPG_ROOM_TYPES = [
    ("enemy", 0.4),
    ("elite", 0.12),
    ("treasure", 0.13),
    ("healer", 0.08),
    ("trap", 0.12),
    ("empty", 0.15),
]
RPG_ROOM_DESCRIPTIONS = {
    "start": "the anchor chamber",
    "enemy": "a nest of hostile glitches",
    "elite": "a predator built from negative space",
    "treasure": "a vault of broken relics",
    "healer": "a campfire of blue code",
    "trap": "a minefield of static",
    "empty": "a hollow stretch of hallway",
    "exit": "a downward fracture",
}
RPG_POTION_HEAL_RATIO = 0.45
RPG_LOG_MAX = 10
RPG_RELICS = [
    {"id": "heart_shard", "name": "Fractured Heart", "desc": "+25 Max HP", "effect": "max_hp", "value": 25},
    {"id": "blade_loop", "name": "Blade Loop", "desc": "+3 ATK", "effect": "atk", "value": 3},
    {"id": "obsidian_plate", "name": "Obsidian Plate", "desc": "+2 DEF", "effect": "def", "value": 2},
    {"id": "gilded_eye", "name": "Gilded Eye", "desc": "+15% GOLD", "effect": "gold_bonus", "value": 0.15},
]
RPG_RELIC_LOOKUP = {entry["id"]: entry for entry in RPG_RELICS}


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
    }


def slot_save_path(idx):
    idx = max(0, min(SAVE_SLOT_COUNT - 1, int(idx)))
    return os.path.join(DATA_DIR, f"save_slot_{idx + 1}.json")


def current_save_path():
    return slot_save_path(ACTIVE_SLOT_INDEX)


ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RESET_SEQ = Style.RESET_ALL if "Style" in globals() else "\x1b[0m"

last_tick_time = time.time()
last_render, last_size = "", (0, 0)
work_timer, KEY_PRESSED, running, focus_active_until = 0.0, None, True, 0.0
steam = []
view_offset_x = 0
view_offset_y = 0
last_manual_time = 0.0
listener_enabled = True  # used to temporarily disable key_listener during blackjack

game = {
    "layer": 0,
    "money": 0.0,
    "money_since_reset": 0.0,
    "fatigue": 0,
    "focus": 0,
    "inspiration": 0,
    "concepts": 0,
    "motivation": 0,
    "owned": [],
    "upgrade_levels": {},
    "focus_unlocked": False,
    "auto_work_unlocked": False,
    "inspiration_unlocked": False,
    "concepts_unlocked": False,
    "inspiration_upgrades": [],
    "concept_upgrades": [],
    "work_delay_multiplier": 1.0,
    "money_mult": 1.0,
    "focus_max_bonus": 0,
    "charge": 0.0,
    "best_charge": 0.0,
    "charge_threshold": [],
    "charge_unlocked": False,
    "battery_tier": 1,
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
    "stability_resets": 0,
    "wake_timer": WAKE_TIMER_START,
    "wake_timer_cap": WAKE_TIMER_START,
    "wake_timer_infinite": False,
    "wake_timer_locked": False,
    "wake_timer_upgrades": [],
    "wake_timer_notified": False,
    "needs_stability_reset": False,
    "play_time": 0.0,
    "last_save_timestamp": 0.0,
    "resonance_val": RESONANCE_START,
    "resonance_target": 50.0,
    "resonance_drift_dir": 1,
    "rpg_unlocked": False,
    "rpg_data": default_rpg_data(),
    "rpg_view": "desktop",
    "rpg_icon_index": 0,
    "rpg_desktop_hint": "",
    "rpg_hint_until": 0.0,
}


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
    if not rpg.get("map"):
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


def reveal_text(tag, text, placeholder="???"):
    return text if is_known(tag) else placeholder


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


def recalc_wake_timer_state():
    purchased = set(game.get("wake_timer_upgrades", []))
    cap = WAKE_TIMER_START
    infinite = game.get("wake_timer_infinite", False)
    for upg in WAKE_TIMER_UPGRADES:
        if upg["id"] in purchased:
            cap += upg.get("time_bonus", 0)
            if upg.get("grant_infinite"):
                infinite = True
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
        "Your vision tunnels as the loop crushes in.",
        f"Collapse is inevitable. The implosion will mint {STABILITY_CURRENCY_NAME}.",
    ]
    tmp = boxed_lines(msg, title=" Collapse Imminent ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(0.9)
    game["wake_timer_notified"] = True


def build_wake_timer_line():
    if game.get("wake_timer_infinite", False):
        return "Stability: ∞ (secured)"
    remaining = max(0, int(game.get("wake_timer", WAKE_TIMER_START)))
    cap = max(1, int(game.get("wake_timer_cap", WAKE_TIMER_START)))
    ratio = remaining / cap if cap else 0
    if ratio > 0.45:
        status = "steady"
    elif ratio > 0.2:
        status = "faltering"
    else:
        status = "critical"
    label = f"Stability: {format_clock(remaining)} ({status})"
    if wake_timer_blocked():
        label += "  collapsing"
    return label


def veil_text(text, min_visible=1, placeholder="?"):
    if not text:
        return placeholder * 3
    result = []
    visible_in_word = 0
    for ch in text:
        if ch.isalnum():
            if visible_in_word < min_visible:
                result.append(ch)
                visible_in_word += 1
            else:
                result.append(placeholder)
        else:
            result.append(ch)
            visible_in_word = 0
    return "".join(result)


def veil_numeric_string(text, reveal_ratio=0.35, placeholder="?"):
    if not text:
        return placeholder * 3
    chars = list(text)
    signal_indices = [i for i, ch in enumerate(chars) if ch.isalnum()]
    reveal_count = max(1, int(len(signal_indices) * reveal_ratio))
    for offset, idx in enumerate(signal_indices):
        if offset >= reveal_count:
            chars[idx] = placeholder
    return "".join(chars)


def format_currency(amount):
    rendered = format_number(amount)
    return f"{CURRENCY_SYMBOL}{rendered}"


def load_game():
    global game
    slot_path = current_save_path()
    source_path = slot_path
    if (not os.path.exists(slot_path)) and ACTIVE_SLOT_INDEX == 0 and os.path.exists(LEGACY_SAVE_PATH):
        source_path = LEGACY_SAVE_PATH
    if os.path.exists(source_path):
        try:
            with open(source_path, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                game.update(data)
        except:
            pass
    game.setdefault("money_mult", BASE_MONEY_MULT)
    game.setdefault("focus_unlocked", False)
    game.setdefault("auto_work_unlocked", False)
    game.setdefault("inspiration_unlocked", False)
    game.setdefault("concepts_unlocked", False)
    game.setdefault("inspiration_upgrades", [])
    game.setdefault("concept_upgrades", [])
    game.setdefault("upgrade_levels", {})
    game.setdefault("resonance_repick_cooldown", 0.0)
    game.setdefault("focus_max_bonus", 0)
    game.setdefault("motivation", 0)
    game.setdefault("charge", 0.0)
    game.setdefault("best_charge", 0.0)
    game.setdefault("charge_threshold", [])
    game.setdefault("battery_tier", 1)
    game.setdefault("insp_page", 0)
    game.setdefault("concept_page", 0)
    game.setdefault("rpg_view", "desktop")
    game.setdefault("rpg_icon_index", 0)
    game.setdefault("rpg_desktop_hint", "")
    game.setdefault("rpg_hint_until", 0.0)
    game.setdefault("mystery_revealed", False)
    game.setdefault("pulses", 0)
    game.setdefault("veils", 0)
    game.setdefault("sigils", 0)
    game.setdefault("knowledge", {})
    game.setdefault("upgrades_unlocked", False)
    game.setdefault("inspiration_resets", 0)
    game.setdefault("intro_played", False)
    game.setdefault("concept_resets", 0)
    game.setdefault("stability_currency", 0.0)
    game.setdefault("stability_resets", 0)
    game.setdefault("wake_timer", WAKE_TIMER_START)
    game.setdefault("wake_timer_cap", WAKE_TIMER_START)
    game.setdefault("wake_timer_infinite", False)
    game.setdefault("wake_timer_locked", False)
    game.setdefault("wake_timer_upgrades", [])
    game.setdefault("wake_timer_notified", False)
    game.setdefault("needs_stability_reset", False)
    game.setdefault("play_time", 0.0)
    game.setdefault("last_save_timestamp", 0.0)
    if game.get("money_since_reset", 0) >= 100:
        game["mystery_revealed"] = True
    ensure_rpg_state()
    recalc_wake_timer_state()
    if not game.get("upgrades_unlocked", False) and game.get("owned"):
        game["upgrades_unlocked"] = True
    refresh_knowledge_flags()
    save_game()


def save_game():
    try:
        game["last_save_timestamp"] = time.time()
    except Exception:
        game["last_save_timestamp"] = time.time()
    target_path = current_save_path()
    try:
        with open(target_path, "w") as f:
            json.dump(game, f)
    except:
        pass


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
    while len(lines) < height - 1:
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
    
    # Use ANSI codes to reset cursor and overwrite instead of clearing screen to prevent flicker
    buffer = []
    buffer.append("\033[H")  # Move cursor to top-left
    
    title = "Select Save File"
    buffer.append("\033[2K\n")
    buffer.append("\033[2K" + title.center(term_w) + "\n")
    buffer.append("\033[2K\n")
    for line in grid:
        buffer.append("\033[2K" + line.center(term_w) + "\n")
    buffer.append("\033[2K\n")
    buffer.append("\033[2K" + "Use arrows/WASD to move, Enter to load, Shift+D to delete, Q to quit.".center(term_w) + "\n")
    buffer.append("\033[J")  # Clear remaining screen content
    
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
        try:
            shutil.copy(summary["source_path"], summary["target_path"])
        except Exception:
            pass
    ACTIVE_SLOT_INDEX = selected
    clear_screen()


def choose_save_slot_windows():
    # Clear any pending input
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
                if ch in ("\r", "\n"):
                    play_slot_select_animation(selected)
                    finalize_slot_choice(selected)
                    return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        # fallback to simple input if arrow handling fails
        while True:
            summaries = collect_slot_summaries()
            render_slot_menu(summaries, highlight_idx=selected)
            raw_choice = input(">> ").strip()
            lower_choice = raw_choice.lower()
            if lower_choice == "q":
                sys.exit(0)
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
            if raw_choice == "D":
                confirm = input(f"Erase slot {selected + 1}? Type YES to confirm: ")
                if confirm.strip().lower() == "yes":
                    path = slot_save_path(selected)
                    if os.path.exists(path):
                        os.remove(path)
                    if selected == 0 and os.path.exists(LEGACY_SAVE_PATH):
                        os.remove(LEGACY_SAVE_PATH)
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
    if game.get("auto_work_unlocked"):
        updated |= attempt_reveal("ui_auto_prompt")
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


def render_battery(charge, tier=None):
    if tier is None:
        tier = game.get("battery_tier", 1)
    tier_info = BATTERY_TIERS.get(tier, BATTERY_TIERS[1])
    cap = tier_info["cap"]
    total_rows = tier_info["rows"]
    inner_w = 13
    filled_rows = int((charge / cap) * total_rows)
    val_str = (str(format_number(int(charge))) + " Ω").center(inner_w)
    rows = []
    for i in range(total_rows):
        if i < filled_rows:
            rows.append("│" + "█" * inner_w + "│")
        else:
            rows.append("│" + " " * inner_w + "│")
    return [
        "┌" + "─" * inner_w + "┐",
        f"│{val_str}│",
        "├" + "─" * inner_w + "┤",
        *rows,
        "└" + "─" * inner_w + "┘",
    ]


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


def build_tree_lines(upgrades, get_info_fn, page_key):
    term_w, term_h = get_term_size()
    max_lines = term_h // 2 - 6
    layer_key = "corridor" if upgrades is INSPIRE_UPGRADES else "archive"
    suffix_raw = layer_currency_suffix(layer_key)
    suffix = f" {suffix_raw}" if suffix_raw else ""
    pool_currency = layer_currency_name(layer_key)
    holdings_key = "inspiration" if upgrades is INSPIRE_UPGRADES else "concepts"
    # Left column in the main UI is ~25% of the terminal width; reserve padding for indent
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
            if level > 0 and u["type"] not in ("unlock_motivation", "unlock_autowork"):
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
    current_page = max(0, min(current_page, len(pages) - 1))
    visible_lines = pages[current_page] if pages else ["(no upgrades)"]
    footer = f"Page {current_page+1}/{len(pages) if pages else 1}  (z, x to switch)"
    return visible_lines, footer, len(pages)


def get_tree_cost(upg, current_level=0):
    return int(
        upg.get("base_cost", upg.get("cost", 0))
        * (upg.get("cost_mult", 1) ** current_level)
    )


def apply_inspiration_effects():
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


def apply_concept_effects():
    for entry in game.get("concept_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        u = next((x for x in CONCEPT_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        if u["type"] == "unlock_autowork" and level > 0:
            game["auto_work_unlocked"] = True


def get_charge_bonus():
    charge = game.get("charge", 0)
    return 1.5 ** (math.log10(charge + 0.1))


def compute_gain_and_delay(auto=False):
    base_gain = BASE_MONEY_GAIN
    base_delay = BASE_WORK_DELAY
    gain_add = 0.0
    gain_mult = 1.0
    delay_mult = 1.0
    game["focus_max_bonus"] = 0
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
        elif t in ("focus_max", "focus_max_bonus"):
            game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + val
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
        elif t in ("focus_max", "focus_max_bonus"):
            game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + val
        elif t == "unlock_focus" and lvl > 0:
            game["focus_unlocked"] = True
        elif t == "unlock_charge" and lvl > 0:
            game["charge_unlocked"] = True
        elif t == "unlock_rpg" and lvl > 0:
            game["rpg_unlocked"] = True

    if game.get("motivation_unlocked", False):
        motivation = game.get("motivation", MOTIVATION_MAX)
        motivation_mult = 1 + (motivation / max(1, MOTIVATION_MAX)) * (
            MAX_MOTIVATION_MULT - 1
        )
        gain_mult *= motivation_mult
    buff_mult = get_charge_bonus()
    for t in CHARGE_THRESHOLDS:
        if t["amount"] in game.get("charge_threshold", []):
            rtype, rval = t["reward_type"], t["reward_value"]
            if rtype in ("x¤", "xmult"):
                gain_mult *= rval * buff_mult
            elif rtype == "-cd":
                delay_mult *= rval**buff_mult
    if time.time() < focus_active_until:
        delay_mult *= FOCUS_BOOST_FACTOR
    
    # Apply Resonance Efficiency
    res_eff = get_resonance_efficiency()
    gain_mult *= res_eff
    
    eff_gain = base_gain * gain_mult + gain_add
    eff_gain *= BASE_MONEY_MULT
    eff_gain *= game.get("money_mult", 1.0)
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
        segs = []
        if visible_len(raw) <= inner_w:
            segs.append(raw)
        else:
            words = raw.split(" ")
            cur = ""
            for w in words:
                if cur == "":
                    cur = w
                elif len(cur) + 1 + len(w) <= inner_w:
                    cur += " " + w
                else:
                    segs.append(cur)
                    cur = w
            if cur:
                while len(cur) > inner_w:
                    segs.append(cur[:inner_w])
                    cur = cur[inner_w:]
                if cur:
                    segs.append(cur)

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
    global steam
    table = LAYER_0_DESK.copy()
    total_money = game.get("money_since_reset", 0)
    
    if total_money < 10:
        table[1] = "║     Where am I?       ║"
    elif total_money < 30:
        table[1] = "║      A desk...        ║"
    elif total_money < 100:
        table[1] = "║     A workspace       ║"
    elif total_money < 1000:
        table[1] = "║    System Terminal    ║"
    elif total_money < 5000:
        table[1] = "║    Command Center     ║"
        
    owned_ids = [u["id"] for u in config.UPGRADES if u["id"] in game.get("owned", [])]
    for new, old in getattr(config, "UPGRADE_REPLACEMENT", {}).items():
        if new in owned_ids and old in owned_ids:
            owned_ids.remove(old)
    # keep the order from config.UPGRADES (don't sort) so placement is predictable
    owned_arts = [uid for uid in owned_ids if uid in UPGRADE_ART]

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
        art = UPGRADE_ART.get(uid)
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
            new_steam = []
            for x, y, stage, life in steam:
                y -= config.STEAM_SPEED
                life -= 1
                if life > 0 and y >= 0:
                    stage_idx = min(
                        len(config.STEAM_CHARS) - 1,
                        (config.STEAM_LIFETIME - life) // 3,
                    )
                    new_steam.append((x, y, stage_idx, life))
            steam = new_steam
            if random.random() < config.STEAM_CHANCE:
                offset = random.randint(-config.STEAM_SPREAD, config.STEAM_SPREAD)
                steam.append(
                    (cup_center + offset, steam_emit_idx, 0, config.STEAM_LIFETIME)
                )
            for x, y, stage_idx, _ in steam:
                yi = int(round(y))
                if 0 <= yi < len(table):
                    line = table[yi]
                    if 0 <= x < len(line):
                        line = line[:x] + config.STEAM_CHARS[stage_idx] + line[x + 1 :]
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
    if manual:
        mark_known("ui_work_prompt")
    if game.get("motivation_unlocked", False):
        game["motivation"] = max(0, game.get("motivation", 0) - 1)
    if not manual and game.get("auto_work_unlocked", False):
        work_timer = max(0.0, work_timer - eff_delay)
    save_game()
    return True



def calculate_stability_reward(money_pool):
    pool = max(0.0, float(money_pool)) + 1.0
    reward = int((pool**STABILITY_REWARD_EXP) * STABILITY_REWARD_MULT)
    return max(1, reward)


def perform_stability_collapse():
    global work_timer, last_render
    if game.get("wake_timer_infinite", False):
        return
    money_pool = max(game.get("money", 0.0), game.get("money_since_reset", 0.0))
    reward = calculate_stability_reward(money_pool)
    game["stability_currency"] = game.get("stability_currency", 0.0) + reward
    game["stability_resets"] = game.get("stability_resets", 0) + 1
    lines = [
        "The desk roars and everything folds inward.",
        f"You claw back {format_number(reward)} {STABILITY_CURRENCY_NAME}.",
        "Permanent stabilizers await.",
    ]
    tmp = boxed_lines(lines, title=" Collapse ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(1.2)
    work_timer = 0.0
    game.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "focus": 0,
            "charge": 0.0,
            "best_charge": 0.0,
            "charge_threshold": [],
            "motivation": 0,
            "owned": [],
            "upgrade_levels": {},
        }
    )
    game["wake_timer"] = game.get("wake_timer_cap", WAKE_TIMER_START)
    game["wake_timer_locked"] = False
    game["wake_timer_notified"] = False
    game["needs_stability_reset"] = False
    recalc_wake_timer_state()
    refresh_knowledge_flags()
    save_game()
    last_render = ""
    if game.get("wake_timer_infinite", False):
        return
    open_wake_timer_menu(auto_invoked=True)
    last_render = ""


def work_tick():
    global last_tick_time, work_timer
    now = time.time()
    delta = now - last_tick_time
    last_tick_time = now
    game["play_time"] = game.get("play_time", 0.0) + delta
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
    
    gain, eff_delay = compute_gain_and_delay(auto=True)
    if game.get("auto_work_unlocked", False) and not wake_timer_blocked():
        work_timer += delta
        if work_timer >= eff_delay:
            perform_work(gain, eff_delay, manual=False)
    if game.get("charge_unlocked", False):
        game["charge"] += delta
        game["best_charge"] = max(game["best_charge"], game["charge"])
        check_charge_thresholds()
    if refresh_knowledge_flags():
        save_game()


def check_charge_thresholds():
    earned = game.setdefault("charge_threshold", [])
    total = game.get("best_charge", 0)
    for t in CHARGE_THRESHOLDS:
        req = t["amount"]
        if req not in earned and total >= req:
            earned.append(req)


def activate_focus():
    global focus_active_until
    if not game.get("focus_unlocked", False):
        return False, "Focus not unlocked."
    if game.get("focus", 0) < 10:
        return False, "Not enough focus charge."
    game["focus"] = 0
    focus_active_until = time.time() + FOCUS_DURATION
    save_game()
    return True, f"Focus active for {FOCUS_DURATION}s."


def get_tree_selection(upgrades, page_key, digit):
    term_w, term_h = get_term_size()
    max_lines = term_h // 2 - 6
    layer_key = "corridor" if upgrades is INSPIRE_UPGRADES else "archive"
    suffix_raw = layer_currency_suffix(layer_key)
    suffix = f" {suffix_raw}" if suffix_raw else ""
    pool_currency = layer_currency_name(layer_key)
    holdings_key = "inspiration" if upgrades is INSPIRE_UPGRADES else "concepts"
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
            if level > 0 and u["type"] not in ("unlock_motivation", "unlock_autowork"):
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

    page = max(0, min(game.get(page_key, 0), max(0, len(pages) - 1)))
    try:
        digit_idx = int(digit) - 1
    except:
        return -1
    if digit_idx < 0:
        return -1
    start_idx = sum(items_per_page[:page]) if page > 0 else 0
    return start_idx + digit_idx


def buy_tree_upgrade(upgrades, idx):
    if not (0 <= idx < len(upgrades)):
        return
    upg = upgrades[idx]
    owned, level = (
        get_inspire_info(upg["id"])
        if upgrades is INSPIRE_UPGRADES
        else get_concept_info(upg["id"])
    )
    max_level = upg.get("max_level", 1)
    layer_key = "corridor" if upgrades is INSPIRE_UPGRADES else "archive"
    pool_name = layer_name(layer_key)
    pool_currency = layer_currency_name(layer_key)
    pool_suffix = layer_currency_suffix(layer_key)
    suffix_text = f" {pool_suffix}" if pool_suffix else ""
    if level >= max_level:
        msg = f"{upg['name']} is already at max level!"
        tmp = boxed_lines(
            [msg],
            title=f" {pool_name} ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(0.7)
        return
    cost = get_tree_cost(upg, current_level=level)
    pool_key = "inspiration" if upgrades is INSPIRE_UPGRADES else "concepts"
    if game.get(pool_key, 0) < cost:
        msg = f"Not enough {pool_currency} for {upg['name']} (cost {cost}{suffix_text})."
        tmp = boxed_lines(
            [msg],
            title=f" {pool_name} ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(0.7)
        return
    game[pool_key] -= cost
    applied_list_key = (
        "inspiration_upgrades" if upgrades is INSPIRE_UPGRADES else "concept_upgrades"
    )
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
    save_game()
    msg = f"Purchased {upg['name']} level {level + 1}!"
    tmp = boxed_lines(
        [msg],
        title=f" {pool_name} ",
        pad_top=1,
        pad_bottom=1,
    )
    render_frame(tmp)
    time.sleep(0.5)


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
    return int(base_gain * rate_mult * final_mult)


def calculate_concepts(money_since_reset):
    normalized = money_since_reset / 1_000_000
    base_gain = math.floor(((normalized**0.30) * math.log(normalized + 1, 1.4)))
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
            
    # Apply Resonance Efficiency to Echo gain
    if game.get("layer", 0) >= 2:
        res_eff = get_resonance_efficiency()
        final_mult *= res_eff
        
    return int(base_gain * rate_mult * final_mult)


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


def reset_for_inspiration():
    now = time.time()
    if now - game.get("last_inspiration_reset_time", 0) < 0.05:
        return
    corridor_name = layer_name("corridor")
    corridor_currency = layer_currency_name("corridor")
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
    game.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "focus": 0,
            "owned": [],
            "upgrade_levels": {},
            "focus_unlocked": False,
            "inspiration_unlocked": True,
            "layer": max(game.get("layer", 0), 1),
            "charge": 0.0,
            "best_charge": 0.0,
            "charge_threshold": [],
            "charge_unlocked": False,
        }
    )
    game["inspiration_resets"] = previous_resets + 1
    game["last_inspiration_reset_time"] = now
    attempt_reveal("layer_corridor")
    attempt_reveal("currency_corridor")
    if previous_resets == 0:
        attempt_reveal("currency_wake")
        attempt_reveal("ui_currency_clear")
        attempt_reveal("ui_upgrade_catalogue")
        memory_lines = [
            "A fissure opens in your memory as the Hall answers.",
            "The desk stops hissing long enough to whisper names back to you.",
            "Values sharpen. Schematics regain a few letters.",
            "Someone else sounds relieved that you remember at all.",
        ]
        typewriter_message(memory_lines, title=" Memory Thread ", speed=0.04)
        time.sleep(0.8)
        clear_screen()
    if game.get("motivation_unlocked", False):
        game.update({"motivation": MOTIVATION_MAX})
    refresh_knowledge_flags()
    apply_inspiration_effects()
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


def reset_for_concepts():
    now = time.time()
    if now - game.get("last_concepts_reset_time", 0) < 0.05:
        return
    archive_name = layer_name("archive")
    archive_currency = layer_currency_name("archive")
    if game.get("money_since_reset", 0) < CONCEPTS_UNLOCK_MONEY:
        tmp = boxed_lines(
            [f"Reach {format_currency(CONCEPTS_UNLOCK_MONEY)} to access {archive_name}."],
            title=f" {archive_name} ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        global last_render
        last_render = ""
        time.sleep(1.0)
        return
    gained = calculate_concepts(game.get("money_since_reset", 0))
    play_concepts_animation()
    game["concepts"] = game.get("concepts", 0) + gained
    game.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "resonance_val": RESONANCE_START,
            "focus": 0,
            "owned": [],
            "upgrade_levels": {},
            "concepts_unlocked": True,
            "layer": max(game.get("layer", 0), 2),
            "inspiration_upgrades": [],
            "inspiration": 0,
            "charge": 0.0,
            "best_charge": 0.0,
            "charge_threshold": [],
            "charge_unlocked": False,
        }
    )
    game["concept_resets"] = game.get("concept_resets", 0) + 1
    attempt_reveal("layer_archive")
    attempt_reveal("currency_archive")
    apply_concept_effects()
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
            f"{STABILITY_CURRENCY_NAME}: {format_number(game.get('stability_currency', 0))}",
            "",
        ]
        if auto_invoked and not game.get("wake_timer_infinite", False):
            lines.append("Collapse complete. Spend sparks to anchor the loop.")
            lines.append("")
        purchased = set(game.get("wake_timer_upgrades", []))
        for i, upg in enumerate(WAKE_TIMER_UPGRADES, start=1):
            owned = upg["id"] in purchased
            cost_label = format_number(upg.get("cost", 0))
            status = (
                "INSTALLED"
                if owned
                else f"Cost {cost_label} {STABILITY_CURRENCY_NAME}"
            )
            bonus = "Grants infinite time" if upg.get("grant_infinite") else f"+{upg.get('time_bonus', 0)}s stability"
            lines.append(f"{i}. {upg['name']} - {status}")
            desc = upg.get("desc")
            if desc:
                lines.append(f"   {desc}")
            effect_lines = [bonus]
            if upg.get("unlock_upgrades"):
                effect_lines.append("Unlocks the upgrade bay")
            for info in effect_lines:
                lines.append(f"   {info}")
        lines += ["", "Press number to install, B to back."]
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
    purchased = game.setdefault("wake_timer_upgrades", [])
    if upg["id"] in purchased:
        return f"{upg['name']} already installed."
    cost = upg.get("cost", 0)
    if game.get("stability_currency", 0) < cost:
        return f"Need {format_number(cost)} {STABILITY_CURRENCY_NAME} to install {upg['name']}"
    game["stability_currency"] -= cost
    purchased.append(upg["id"])
    if upg.get("grant_infinite"):
        game["wake_timer_infinite"] = True
    extras = []
    if upg.get("unlock_upgrades") and not game.get("upgrades_unlocked", False):
        game["upgrades_unlocked"] = True
        extras.append("Upgrade bay rebooted.")
    recalc_wake_timer_state()
    game["wake_timer"] = game.get("wake_timer_cap", WAKE_TIMER_START)
    game["wake_timer_locked"] = False
    game["wake_timer_notified"] = False
    save_game()
    if game.get("wake_timer_infinite", False):
        base_msg = f"{upg['name']} sealed the loop. Time is yours now."
    else:
        base_msg = f"{upg['name']} installed. Stability restored."
    if extras:
        base_msg += " " + " ".join(extras)
    return base_msg


def open_upgrade_menu():
    global KEY_PRESSED
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
        unlocked = [
            u
            for u in config.UPGRADES
            if u.get("unlocked", False)
            or all(
                dep in game.get("owned", [])
                for dep in config.UPGRADE_DEPENDENCIES.get(u["id"], [])
            )
        ]
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
                    f"    {Fore.GREEN}MAXED — persists across collapses{Style.RESET_ALL}"
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
                global last_render
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
        if upg.get("type") == "unlock_focus" and current_level > 0:
            game["focus_unlocked"] = True
        elif upg.get("type") == "unlock_charge" and current_level > 0:
            game["charge_unlocked"] = True
        elif upg.get("type") == "unlock_rpg" and current_level > 0:
            game["rpg_unlocked"] = True
        msg = f"Purchased {upg['name']} (Lv {current_level}/{max_level})."
    tmp = boxed_lines([msg], title=" UPGRADE BAY ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
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
            f"{Fore.LIGHTYELLOW_EX}{corridor_name} inhales everything you built...{Style.RESET_ALL}",
            term_w,
        )
        lines.append("")
        lines.append(caption)
        lines.append(
            ansi_center(
                f"{Fore.YELLOW}Hold steady. {corridor_currency} condense on the far door.{Style.RESET_ALL}",
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
        print(f"You are bringing {format_currency(starting_money)} from the main game.\n")
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
    if game.get("rpg_unlocked", False):
        tabs.append(("rpg", "Anti-Realm"))
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
    effective_gain, effective_delay = compute_gain_and_delay(
        auto=game.get("auto_work_unlocked", False)
    )
    prog = (
        min(work_timer / effective_delay, 1.0)
        if game.get("auto_work_unlocked", False)
        else 0
    )
    bar_len = 36
    filled = int(prog * bar_len)
    work_bar = f"[{'#' * filled}{'-' * (bar_len - filled)}] {int(prog * 100):3d}%"

    calc_insp = calculate_inspiration(game.get("money_since_reset", 0))
    calc_conc = calculate_concepts(game.get("money_since_reset", 0))
    time_next = predict_next_inspiration_point()
    conc_time_next = predict_next_concept_point()

    top_left_lines = []
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
    if (
        game.get("money_since_reset", 0) >= INSPIRATION_UNLOCK_MONEY // 2
        or game.get("inspiration_unlocked", False) is True
    ):
        top_left_lines += [
            insp_title,
            "",
            f"Holdings: {Fore.LIGHTYELLOW_EX}{format_number(game.get('inspiration', 0))}{Style.RESET_ALL} {corridor_currency}",
            "",
        ]
        if game.get("money_since_reset", 0) >= INSPIRATION_UNLOCK_MONEY:
            top_left_lines.append(
                f"[I] Step into {corridor_name} for {Fore.LIGHTYELLOW_EX}{format_number(calc_insp)}{Style.RESET_ALL} {corridor_currency}"
            )
            top_left_lines.append(
                f"{Fore.LIGHTYELLOW_EX}{format_number(time_next)}{Style.RESET_ALL} until next {corridor_currency}"
            )
            top_left_lines.append("")
            top_left_lines.append(f"[1] Open {corridor_name} board")
        else:
            top_left_lines.append(
                f"Reach {format_currency(INSPIRATION_UNLOCK_MONEY)} to approach {corridor_name}."
            )
            if screen == "inspiration":
                top_left_lines.append("")
            else:
                top_left_lines.append("")
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

    bottom_left_lines = []
    if (game.get("money_since_reset", 0) >= CONCEPTS_UNLOCK_MONEY // 2) or game.get(
        "concepts_unlocked", False
    ):
        bottom_left_lines += [
            conc_title,
            "",
        ]
        if game.get("concepts_unlocked", False):
            bottom_left_lines.append(
                f"Holdings: {Fore.CYAN}{format_number(game.get('concepts', 0))}{Style.RESET_ALL} {archive_currency}"
            )
            bottom_left_lines.append(build_resonance_bar())
            bottom_left_lines.append("")
        if game.get("money_since_reset", 0) >= CONCEPTS_UNLOCK_MONEY:
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

    middle_lines = [build_wake_timer_line()]
    if not game.get("wake_timer_infinite", False):
        sparks_amount = format_number(game.get("stability_currency", 0))
        middle_lines.append(
            f"{STABILITY_CURRENCY_NAME}: {Fore.MAGENTA}{sparks_amount}{Style.RESET_ALL}"
        )
        middle_lines.append("[T] Buy stabilizers")
    middle_lines.append("")
    middle_lines += render_desk_table()
    if game.get("focus_unlocked", False):
        focus_max = FOCUS_MAX + game.get("focus_max_bonus", 0)
        fprog = min(game.get("focus", 0) / float(focus_max), 1.0)
        fbar_len = 36
        ffilled = int(fprog * fbar_len)
        middle_lines += [
            f"FOCUS: {int(fprog * 100):3d}%",
            "[" + "#" * ffilled + "-" * (fbar_len - ffilled) + "]",
            "",
        ]

    total_money = game.get("money_since_reset", 0)
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

    gain_segment = (
        f"   GAIN: {format_currency(effective_gain)} / cycle"
        if show_gain or not mystery_phase
        else ""
    )
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

    work_prompt = reveal_text("ui_work_prompt", "Press W to work", "Press W...")
    auto_prompt = reveal_text("ui_auto_prompt", "Auto-work: ENABLED", "Auto-work: ???")
    if game.get("auto_work_unlocked", False):
        middle_lines.append(auto_prompt)
    else:
        middle_lines.append(work_prompt)

    option_payload = "Options: [W] Work  "
    if game.get("upgrades_unlocked", False):
        option_payload += "[U] Upgrades  "
    else:
        option_payload += "[U] Offline  "
    option_payload += "[J] Blackjack  [Q] Quit"
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
        middle_lines.append(f"{Fore.YELLOW}Use , and . to switch realms.{Style.RESET_ALL}")
    if wake_timer_blocked():
        middle_lines.append("(Unconscious) Spend Sparks in Stabilize menu (T).")
    elif not game.get("upgrades_unlocked", False):
        middle_lines.append("??? offline.")

    term_width, term_height = get_term_size()
    while len(top_left_lines) < term_height - 4:
        top_left_lines.append("")
    while len(bottom_left_lines) < term_height - 4:
        bottom_left_lines.append("")
    while len(middle_lines) < term_height - 4:
        middle_lines.insert(0, "")

    left_w = int(term_width * 0.25)
    mid_w = int(term_width * 0.35)
    right_w = int(term_width * 0.25)
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
    combined_lines = []
    for l, m, r in zip(top_left_lines, middle_lines, bottom_left_lines):
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
    
    tab_line = build_tab_bar_text(screen)
    if tab_line:
        layer_title = f" {tab_line} "
    else:
        layer_title = f" {current_layer_label()} "
    box = boxed_lines(
        combined_lines, title=layer_title, pad_top=1, pad_bottom=1
    )

    if resized:
        print("\033[2J\033[H", end="")
        last_size = current_size
        last_render = ""
        view_offset_x = 0
        view_offset_y = 0
    visible_lines = box[view_offset_y : view_offset_y + term_height]
    visible_lines = [
        pad_visible_line(ansi_visible_slice(line, view_offset_x, term_width), term_width)
        for line in visible_lines
    ]
    frame = "\033[H" + "\n".join(visible_lines)
    if frame != last_render:
        sys.stdout.write(frame)
        sys.stdout.flush()
        last_render = frame


def typewriter_message(lines, title, speed=0.03):
    """Render dialogue with a typewriter effect and Z-to-skip controls."""

    global KEY_PRESSED, listener_enabled

    if not lines:
        return

    display_lines = [""] * len(lines)

    def _consume_skip_request():
        """Return True if Z was pressed (consuming the key)."""
        global KEY_PRESSED
        if not KEY_PRESSED:
            return False
        raw = KEY_PRESSED
        KEY_PRESSED = None
        return isinstance(raw, str) and raw.lower() == "z"

    def _wait_for_z(prompt_text):
        """Pause until the player presses Z, unless listener is disabled."""
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


def update_resonance(delta):
    if game.get("layer", 0) < 2:
        return

    # Initialize if missing
    if "resonance_val" not in game:
        game["resonance_val"] = RESONANCE_START
        game["resonance_target"] = 50.0
        game["resonance_drift_dir"] = 1

    instability = get_resonance_instability()
    stabilizer_level = get_stabilizer_level()
    cooldown = max(0.0, game.get("resonance_repick_cooldown", 0.0) - delta)
    game["resonance_repick_cooldown"] = cooldown

    # Target wanders more when unstable
    target = game["resonance_target"]
    target += (random.random() - 0.5) * delta * 10.0 * instability
    target = max(10, min(90, target))
    game["resonance_target"] = target

    val = game["resonance_val"]
    drift_speed = RESONANCE_DRIFT_RATE * (0.75 + instability)
    val += game["resonance_drift_dir"] * drift_speed * delta

    # Add jitter proportional to instability
    val += (random.random() - 0.5) * instability * 4.0

    # Erratic jumps during high instability
    if random.random() < RESONANCE_JUMP_CHANCE * instability * delta:
        val += (random.random() - 0.5) * RESONANCE_JUMP_POWER * max(1.0, instability)

    # Decide whether to re-choose drift direction (rate now governed by cooldown)
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

    # Bounce off edges
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
    if game.get("layer", 0) < 2:
        return 1.0
        
    val = game.get("resonance_val", RESONANCE_START)
    target = game.get("resonance_target", 50.0)
    width = RESONANCE_TARGET_WIDTH
    
    # Check for upgrades that widen the sweet spot?
    # For now just use constant
    
    dist = abs(val - target)
    if dist <= width:
        return 1.5 # Bonus for being in tune
    
    # Accelerated falloff when outside the colored zone
    overflow = dist - width
    span = RESONANCE_MAX - width
    normalized = min(1.0, overflow / max(span, 1e-6))
    penalty = (normalized ** 0.7) * 1.25
    return max(0.0, 1.0 - penalty)
    

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
        
    # Draw needle
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
    eff = get_resonance_efficiency()

    needle_ratio = None
    if zone_left <= val <= zone_right:
        needle_ratio = min(1.0, abs(val - target) / max(width, 1e-6))
    braces_color = gradient_color(needle_ratio) if needle_ratio is not None else Fore.RED
    left_brace = f"{braces_color}[{Style.RESET_ALL}"
    right_brace = f"{braces_color}]{Style.RESET_ALL}"

    if needle_ratio is None:
        approx_pct = int(round(max(0.0, eff) * 100))
    else:
        approx_pct = int(round(150 - needle_ratio * 70))

    legend = "center≈150% → edges≈80% (outside plummets to 0%)"
    return f"Signal: {left_brace}{bar_str}{right_brace} {approx_pct}%  ({legend})"


def rpg_log(msg):
    rpg = ensure_rpg_state()
    log = rpg.get("log", [])
    log.append(msg)
    if len(log) > RPG_LOG_MAX:
        log = log[-RPG_LOG_MAX:]
    rpg["log"] = log


def generate_rpg_floor(rpg):
    layout = []
    weights = [entry[1] for entry in RPG_ROOM_TYPES]
    options = [entry[0] for entry in RPG_ROOM_TYPES]
    for _y in range(RPG_MAP_HEIGHT):
        row = []
        for _x in range(RPG_MAP_WIDTH):
            typo = random.choices(options, weights=weights, k=1)[0]
            row.append({"type": typo, "visited": False, "cleared": typo == "empty"})
        layout.append(row)
    center_y = RPG_MAP_HEIGHT // 2
    center_x = RPG_MAP_WIDTH // 2
    layout[center_y][center_x] = {"type": "start", "visited": True, "cleared": True}
    candidates = [(y, x) for y in range(RPG_MAP_HEIGHT) for x in range(RPG_MAP_WIDTH) if (y, x) != (center_y, center_x)]
    exit_y, exit_x = random.choice(candidates)
    layout[exit_y][exit_x]["type"] = "exit"
    layout[exit_y][exit_x]["visited"] = False
    layout[exit_y][exit_x]["cleared"] = False
    if not any(room["type"] in ("enemy", "elite") for row in layout for room in row):
        backfill_y, backfill_x = random.choice(candidates)
        layout[backfill_y][backfill_x]["type"] = "enemy"
        layout[backfill_y][backfill_x]["cleared"] = False
        layout[backfill_y][backfill_x]["visited"] = False
    rpg["map"] = layout
    rpg["player_pos"] = [center_y, center_x]
    rpg["state"] = "explore"
    rpg["current_enemy"] = None
    rpg_log(f"The maze reshapes itself for Floor {rpg.get('floor', 1)}.")


def current_rpg_room(rpg):
    layout = rpg.get("map") or []
    if not layout:
        return None
    y, x = rpg.get("player_pos", [0, 0])
    if not (0 <= y < len(layout) and 0 <= x < len(layout[0])):
        return None
    return layout[y][x]


def describe_rpg_room(room):
    if not room:
        return "the void"
    r_type = room.get("type")
    if room.get("cleared") and r_type in {"enemy", "elite", "treasure", "trap"}:
        return "the husk of a resolved encounter"
    return RPG_ROOM_DESCRIPTIONS.get(r_type, "an unreadable hallway")


def rpg_room_symbol(room, is_player=False):
    if is_player:
        return "@"
    if not room or not room.get("visited"):
        return "░"
    if room.get("type") == "exit":
        return ">"
    if not room.get("cleared"):
        symbols = {
            "enemy": "!",
            "elite": "E",
            "treasure": "$",
            "healer": "+",
            "trap": "^",
        }
        return symbols.get(room.get("type"), "?")
    return "."


def build_rpg_map_lines(rpg):
    layout = rpg.get("map") or []
    if not layout:
        return []
    pos = tuple(rpg.get("player_pos", [0, 0]))
    lines = []
    for y, row in enumerate(layout):
        glyphs = []
        for x, room in enumerate(row):
            glyphs.append(rpg_room_symbol(room, is_player=pos == (y, x)))
        lines.append(" ".join(glyphs))
    return lines


def handle_rpg_room_event(rpg, room):
    if not room:
        return
    r_type = room.get("type")
    if r_type in ("enemy", "elite") and not room.get("cleared"):
        start_rpg_combat(rpg, elite=(r_type == "elite"))
    elif r_type == "treasure" and not room.get("cleared"):
        rpg_grant_treasure(rpg)
        room["cleared"] = True
    elif r_type == "healer" and not room.get("cleared"):
        heal = max(10, int(rpg.get("max_hp", 1) * 0.4))
        rpg["hp"] = min(rpg["max_hp"], rpg.get("hp", 0) + heal)
        room["cleared"] = True
        rpg_log(f"Blue fire knits {heal} HP back together.")
    elif r_type == "trap" and not room.get("cleared"):
        dmg = max(6, int(rpg.get("max_hp", 1) * 0.2))
        rpg["hp"] -= dmg
        room["cleared"] = True
        rpg_log(f"Static spikes bite for {dmg} damage!")
        if rpg["hp"] <= 0:
            handle_rpg_death(rpg)
    elif r_type == "exit":
        advance_rpg_floor(rpg)


def rpg_move(dy, dx):
    rpg = ensure_rpg_state()
    if rpg.get("state") != "explore":
        rpg_log("You must resolve the encounter first.")
        return
    layout = rpg.get("map") or []
    if not layout:
        generate_rpg_floor(rpg)
        layout = rpg["map"]
    y, x = rpg.get("player_pos", [0, 0])
    ny, nx = y + dy, x + dx
    if not (0 <= ny < len(layout) and 0 <= nx < len(layout[0])):
        rpg_log("The void disagrees with that direction.")
        return
    rpg["player_pos"] = [ny, nx]
    room = layout[ny][nx]
    if not room.get("visited"):
        room["visited"] = True
        rpg_log(f"You scout {describe_rpg_room(room)}.")
    handle_rpg_room_event(rpg, room)


def start_rpg_combat(rpg, elite=False):
    enemy = build_rpg_enemy(rpg.get("floor", 1), elite=elite)
    rpg["current_enemy"] = enemy
    rpg["state"] = "combat"
    prefix = "Elite " if elite else ""
    rpg_log(f"{prefix}{enemy['name']} manifests!")


def build_rpg_enemy(floor, elite=False):
    template = random.choice(RPG_ENEMIES)
    scale = 1.0 + max(0, floor - 1) * 0.25
    if elite:
        scale *= 1.35
    return {
        "name": template["name"],
        "hp": int(template["hp"] * scale),
        "max_hp": int(template["hp"] * scale),
        "atk": max(1, int(template["atk"] * scale)),
        "xp": int(template["xp"] * scale * (1.4 if elite else 1.0)),
        "gold": int(template.get("gold", 0) * scale * (1.4 if elite else 1.0)),
        "elite": elite,
        "charging": False,
    }


def rpg_attack():
    rpg = ensure_rpg_state()
    if rpg.get("state") != "combat":
        rpg_log("There is nothing to strike.")
        return
    enemy = rpg.get("current_enemy")
    if not enemy:
        rpg["state"] = "explore"
        return
    dmg = rpg.get("atk", RPG_PLAYER_START_ATK)
    if random.random() < 0.15:
        dmg = int(dmg * 1.75)
        rpg_log(f"Critical hit! You deal {dmg} damage.")
    else:
        rpg_log(f"You deal {dmg} damage.")
    enemy["hp"] -= dmg
    if enemy["hp"] <= 0:
        complete_combat_victory(rpg, enemy)
    else:
        enemy_turn(rpg)


def complete_combat_victory(rpg, enemy):
    gold_gain = int(enemy.get("gold", 0) * (1 + rpg.get("gold_bonus", 0.0)))
    xp_gain = enemy.get("xp", 0)
    rpg_log(f"Felled {enemy['name']}! +{xp_gain} XP, +{gold_gain} gold.")
    rpg["gold"] = rpg.get("gold", 0) + gold_gain
    rpg["xp"] = rpg.get("xp", 0) + xp_gain
    room = current_rpg_room(rpg)
    if room:
        room["cleared"] = True
    rpg["current_enemy"] = None
    rpg["state"] = "explore"
    check_rpg_level_up(rpg)


def check_rpg_level_up(rpg):
    leveled = False
    while rpg.get("xp", 0) >= rpg.get("level", 1) * 120:
        req = rpg["level"] * 120
        rpg["xp"] -= req
        rpg["level"] += 1
        rpg["max_hp"] += 15
        rpg["atk"] += 2
        rpg["hp"] = rpg["max_hp"]
        leveled = True
        rpg_log(f"Level up! You are now level {rpg['level']}.")
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
    dmg = max(1, dmg - rpg.get("def", 0))
    rpg["hp"] -= dmg
    if rpg["hp"] <= 0:
        handle_rpg_death(rpg)


def handle_rpg_death(rpg):
    loss = int(rpg.get("gold", 0) * 0.2)
    if loss:
        rpg_log(f"You collapse and drop {loss} gold.")
    else:
        rpg_log("You collapse and the maze spits you out.")
    rpg["gold"] = max(0, rpg.get("gold", 0) - loss)
    rpg["hp"] = rpg.get("max_hp", RPG_PLAYER_START_HP)
    rpg["state"] = "explore"
    rpg["current_enemy"] = None
    if rpg.get("map"):
        center_y = len(rpg["map"]) // 2
        center_x = len(rpg["map"][0]) // 2
        rpg["player_pos"] = [center_y, center_x]
        rpg["map"][center_y][center_x]["visited"] = True


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
    rpg_log(f"You drink a sparking vial (+{rpg['hp'] - prev} HP).")


def rpg_attempt_flee():
    rpg = ensure_rpg_state()
    if rpg.get("state") != "combat":
        rpg_log("There is nothing to flee from.")
        return
    if random.random() < 0.55:
        rpg["state"] = "explore"
        rpg["current_enemy"] = None
        rpg_log("You vanish into another branch of the maze.")
    else:
        rpg_log("The foe cuts off your escape!")
        enemy_turn(rpg)


def rpg_grant_treasure(rpg):
    roll = random.random()
    if roll < 0.35:
        rpg["inventory"]["potion"] = rpg["inventory"].get("potion", 0) + 1
        rpg_log("You pocket a fresh potion.")
    elif roll < 0.7:
        if random.random() < 0.5:
            rpg["atk"] += 2
            rpg_log("Your strikes hum hotter (+2 ATK).")
        else:
            rpg["max_hp"] += 20
            rpg["hp"] = min(rpg["max_hp"], rpg["hp"])
            rpg_log("New marrow grows (+20 Max HP).")
    else:
        grant_rpg_relic(rpg)


def grant_rpg_relic(rpg):
    available = [rel for rel in RPG_RELICS if rel["id"] not in rpg.get("relics", [])]
    if not available:
        fallback = 100 + 25 * rpg.get("floor", 1)
        rpg["gold"] += fallback
        rpg_log(f"The vault echoes and spills {fallback} gold instead.")
        return
    relic = random.choice(available)
    rpg.setdefault("relics", []).append(relic["id"])
    apply_relic_effect(rpg, relic)
    rpg_log(f"Relic found: {relic['name']} ({relic['desc']}).")


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
    bonus_gold = 150 + 40 * rpg["floor"]
    rpg["gold"] += bonus_gold
    heal = max(15, int(rpg.get("max_hp", 1) * 0.5))
    rpg["hp"] = min(rpg["max_hp"], rpg.get("hp", 0) + heal)
    rpg_log(f"You descend deeper. +{bonus_gold} gold, +{heal} HP.")
    generate_rpg_floor(rpg)


def rpg_handle_command(k):
    rpg = ensure_rpg_state()
    explore_moves = {
        "w": (-1, 0),
        "s": (1, 0),
        "a": (0, -1),
        "d": (0, 1),
    }
    if rpg.get("state") == "combat":
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


def _desktop_icon_count():
    return len(RPG_DESKTOP_APPS)


def _ensure_desktop_hint_state():
    if time.time() > game.get("rpg_hint_until", 0.0):
        game["rpg_desktop_hint"] = ""
        game["rpg_hint_until"] = 0.0


def set_rpg_desktop_hint(text, duration=2.5):
    game["rpg_desktop_hint"] = text
    game["rpg_hint_until"] = time.time() + duration


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
        set_rpg_desktop_hint("Internet Explorer peers into static. No signal found.")
        return "hint"
    if ident == "trash":
        set_rpg_desktop_hint("Trash Bin reports: already empty.")
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
                art = RPG_ICON_ART.get(icon["id"], _DEFAULT_ICON_ART)
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


def build_rpg_game_view(rpg, width, max_lines):
    lines = []
    title = (
        f"{Back.BLUE}{Fore.WHITE} GAME.EXE — Floor {rpg.get('floor', 1)} {Style.RESET_ALL}"
    )
    lines.append(pad_visible_line(title, width))
    lines.append("".ljust(width, "─"))
    xp_goal = rpg.get("level", 1) * 120
    stats = (
        f"LV {rpg['level']}  HP {rpg['hp']}/{rpg['max_hp']}  ATK {rpg['atk']}  DEF {rpg.get('def', 0)}  "
        f"XP {rpg['xp']}/{xp_goal}  GOLD {rpg['gold']}  POTIONS {rpg['inventory'].get('potion', 0)}"
    )
    lines.append(pad_visible_line(stats, width))
    relics = rpg.get("relics", [])
    if relics:
        names = ", ".join(
            RPG_RELIC_LOOKUP.get(rid, {"name": "Unknown"})["name"]
            for rid in relics[:3]
        )
        more = "..." if len(relics) > 3 else ""
        lines.append(pad_visible_line(f"Relics: {names}{more}", width))
    lines.append("")
    for row in build_rpg_map_lines(rpg):
        lines.append(pad_visible_line(ansi_center(row, width), width))
    lines.append("")
    room = current_rpg_room(rpg)
    lines.append(pad_visible_line(f"Room: {describe_rpg_room(room)}", width))
    lines.append("")
    if rpg.get("state") == "combat" and rpg.get("current_enemy"):
        enemy = rpg["current_enemy"]
        lines.append(
            pad_visible_line(
                f"{Fore.MAGENTA}{enemy['name']}{Style.RESET_ALL}  HP {enemy['hp']}/{enemy['max_hp']}  ATK {enemy['atk']}",
                width,
            )
        )
        bar_len = max(12, width - 10)
        pct = max(0, enemy["hp"]) / max(1, enemy["max_hp"])
        filled = int(pct * bar_len)
        bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"
        lines.append(pad_visible_line(bar, width))
        lines.append("")
    lines.append("".ljust(width, "─"))
    for msg in rpg.get("log", [])[-6:]:
        lines.append(pad_visible_line(msg, width))
    lines.append("".ljust(width, "─"))
    if rpg.get("state") == "combat":
        action_line = "[A]ttack  [P]otion  [F]lee  (Enter: minimize disabled in combat)"
    else:
        action_line = "WASD move · P potion · Enter to minimize · B to close"
    lines.append(pad_visible_line(action_line, width))
    lines.append(pad_visible_line("[,][.] switch realms", width))
    return lines[:max_lines]


def build_monitor_frame(inner_lines, glass_width, term_w, term_h):
    glass_width = max(30, glass_width)
    glass_width = min(glass_width, term_w - 4)
    case_width = glass_width + 4
    left_pad = max(0, (term_w - case_width) // 2)
    max_glass_lines = max(12, term_h - 8)
    content = inner_lines[:max_glass_lines]
    while len(content) < max_glass_lines:
        content.append("")
    output = []
    visible_height = max_glass_lines + 6
    top_margin = max(0, (term_h - visible_height) // 2)
    output.extend(["" for _ in range(top_margin)])
    output.append(" " * left_pad + "╭" + "─" * case_width + "╮")
    output.append(" " * left_pad + "│" + " " * case_width + "│")
    output.append(
        " " * left_pad + "│" + "┌" + "─" * glass_width + "┐" + "│"
    )
    for raw in content:
        padded = pad_visible_line(raw, glass_width)
        output.append(
            " " * left_pad + "│" + "│" + padded + "│" + "│"
        )
    output.append(
        " " * left_pad + "│" + "└" + "─" * glass_width + "┘" + "│"
    )
    knob = ("◉" + " " * max(0, glass_width - 8) + "▢").center(glass_width)
    output.append(" " * left_pad + "│" + knob + "│")
    output.append(" " * left_pad + "╰" + "─" * case_width + "╯")
    stand_center = left_pad + (case_width // 2)
    output.append(" " * max(0, stand_center - 2) + "╭┴╮")
    output.append(" " * max(0, stand_center - 4) + "╱____╲")
    return output


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
    term_w, term_h = get_term_size()
    current_size = (term_w, term_h)
    resized = current_size != last_size
    usable_w = max(32, term_w - 6)
    glass_width = min(term_w - 6, usable_w)
    glass_width = max(30, glass_width)
    max_lines = max(18, term_h - 10)
    view = game.get("rpg_view", "desktop")
    _ensure_desktop_hint_state()
    if view == "desktop":
        inner_lines = build_rpg_desktop_view(glass_width, max_lines)
    else:
        inner_lines = build_rpg_game_view(rpg, glass_width, max_lines)
    monitor_lines = build_monitor_frame(inner_lines, glass_width, term_w, term_h)
    tab_line = build_tab_bar_text("rpg")
    if tab_line:
        monitor_lines.insert(0, ansi_center(tab_line, term_w))
        monitor_lines.insert(1, "")
    while len(monitor_lines) < term_h:
        monitor_lines.append("")
    prepared = [pad_visible_line(line, term_w) for line in monitor_lines[:term_h]]
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
        msg = [
            "You wake at a desk whose corners refuse to meet.",
            "The dark hums like something counting you.",
            "You don't remember how you got here.",
            "",
            "Something tilts when you try to stand.",
        ]
        typewriter_message(msg, title=" ??? ", speed=0.05)
        game["intro_played"] = True
        save_game()
        time.sleep(1.0)

    if game.get("layer", 0) >= 1 and not game.get("inspiration_unlocked", False):
        game["inspiration_unlocked"] = True
        game["layer"] = 1
        save_game()
    current_screen = "work"
    global view_offset_x, view_offset_y
    try:
        while running:
            work_tick()
            update_resonance(0.05)

            if not game.get("mystery_revealed", False) and game.get("money_since_reset", 0) >= 100:
                game["mystery_revealed"] = True
                msg = [
                    "The desk pays attention when you tap long enough.",
                    "The value it hands back isn't money, but it obeys.",
                    "",
                    "Somewhere outside, a fourth shadow tilts its head."
                ]
                typewriter_message(msg, title=" Discovery ", speed=0.04)
                time.sleep(1.5)
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

                if k in (",", "."):
                    direction = -1 if k == "," else 1
                    next_screen = cycle_screen(current_screen, direction)
                    if next_screen != current_screen:
                        current_screen = next_screen
                        if current_screen != "rpg":
                            last_render = ""
                        continue
                
                elif k == "q":
                    clear_screen()
                    last_render = ""
                    running = False
                    break
                
                elif current_screen == "rpg":
                    rpg = ensure_rpg_state()
                    view = game.get("rpg_view", "desktop")
                    if view == "desktop":
                        result = handle_rpg_desktop_input(k)
                        if result == "exit":
                            current_screen = "work"
                    else:
                        if k == "enter":
                            if rpg.get("state") == "combat":
                                rpg_log("Can't minimize the fight.")
                            else:
                                game["rpg_view"] = "desktop"
                        elif k == "b":
                            if rpg.get("state") == "combat":
                                rpg_log("The foe blocks your escape!")
                            else:
                                game["rpg_view"] = "desktop"
                                current_screen = "work"
                        else:
                            rpg_handle_command(k)
                
                elif k == "w":
                    now = time.time()
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
                elif k == "t" and not game.get("wake_timer_infinite", False):
                    current_screen = "work"
                    clear_screen()
                    open_wake_timer_menu()
                    render_ui(screen=current_screen)
                elif k == "f":
                    ok, msg = activate_focus()
                    tmp = boxed_lines([msg], title=" Focus ", pad_top=1, pad_bottom=1)
                    render_frame(tmp)
                    time.sleep(1.0)
                elif k == "i":
                    reset_for_inspiration()
                    current_screen = "work"
                elif k == "c":
                    reset_for_concepts()
                    current_screen = "work"
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
                elif current_screen == "inspiration":
                    if k == "b":
                        current_screen = "work"
                    elif k == "z":
                        game["insp_page"] = max(0, game["insp_page"] - 1)
                    elif k == "x":
                        game["insp_page"] = game["insp_page"] + 1
                    elif k.isdigit():
                        idx = get_tree_selection(INSPIRE_UPGRADES, "insp_page", k)
                        if 0 <= idx < len(INSPIRE_UPGRADES):
                            buy_tree_upgrade(INSPIRE_UPGRADES, idx)
                        time.sleep(0.2)
                elif current_screen == "concepts":
                    if k == "b":
                        current_screen = "work"
                    elif k == "z":
                        game["concept_page"] = max(0, game["concept_page"] - 1)
                    elif k == "x":
                        game["concept_page"] = game["concept_page"] + 1
                    elif k.isdigit():
                        idx = get_tree_selection(CONCEPT_UPGRADES, "concept_page", k)
                        if 0 <= idx < len(CONCEPT_UPGRADES):
                            buy_tree_upgrade(CONCEPT_UPGRADES, idx)
                        time.sleep(0.2)
    except Exception:
        traceback.print_exc()
        running = False
    finally:
        save_game()


if __name__ == "__main__":
    try:
        main_loop()
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")

