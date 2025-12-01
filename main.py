import json, os, time, sys, threading, shutil, math, select, random, textwrap, subprocess, re, traceback

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
    format_number,
)

import blackjack

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
LEGACY_SAVE_PATH = os.path.join(DATA_DIR, "save.json")
SAVE_SLOT_COUNT = 4
ACTIVE_SLOT_INDEX = 0


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
}


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
    game.setdefault("focus_max_bonus", 0)
    game.setdefault("motivation", 0)
    game.setdefault("charge", 0.0)
    game.setdefault("best_charge", 0.0)
    game.setdefault("charge_threshold", [])
    game.setdefault("battery_tier", 1)
    game.setdefault("insp_page", 0)
    game.setdefault("concept_page", 0)
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
    clear_screen()
    title = "Select Save File"
    print()
    print(title.center(term_w))
    print()
    for line in grid:
        print(line.center(term_w))
    print()
    print("Use arrows to move, Enter to load, D to delete, Q to quit.".center(term_w))


def play_slot_select_animation(selected_idx, frames=6, delay=0.08):
    for phase in range(frames):
        summaries = collect_slot_summaries()
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
    selected = 0
    phase = 0
    while True:
        summaries = collect_slot_summaries()
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
                print("Exiting.")
                sys.exit(0)
            if lower == "d":
                confirm = input(f"Erase slot {selected + 1}? Type YES to confirm: ")
                if confirm.strip().lower() == "yes":
                    path = slot_save_path(selected)
                    if os.path.exists(path):
                        os.remove(path)
                    if selected == 0 and os.path.exists(LEGACY_SAVE_PATH):
                        os.remove(LEGACY_SAVE_PATH)
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
    deleting = False
    try:
        import termios, tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        while True:
            summaries = collect_slot_summaries()
            render_slot_menu(summaries, highlight_idx=selected, phase=phase)
            phase = (phase + 1) % 8
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A":  # up
                    selected = (selected - 2) % SAVE_SLOT_COUNT
                elif seq == "[B":  # down
                    selected = (selected + 2) % SAVE_SLOT_COUNT
                elif seq == "[C":  # right
                    selected = (selected + 1) % SAVE_SLOT_COUNT
                elif seq == "[D":  # left
                    selected = (selected - 1) % SAVE_SLOT_COUNT
                continue
            if ch.lower() == "q":
                clear_screen()
                print("Exiting.")
                sys.exit(0)
            if ch.lower() == "d":
                deleting = True
                confirm = input(f"Erase slot {selected + 1}? Type YES to confirm: ")
                if confirm.strip().lower() == "yes":
                    path = slot_save_path(selected)
                    if os.path.exists(path):
                        os.remove(path)
                    if selected == 0 and os.path.exists(LEGACY_SAVE_PATH):
                        os.remove(LEGACY_SAVE_PATH)
                deleting = False
                continue
            if ch == "\r" or ch == "\n":
                play_slot_select_animation(selected)
                finalize_slot_choice(selected)
                return
    except Exception:
        # fallback to simple input if arrow handling fails
        while True:
            summaries = collect_slot_summaries()
            render_slot_menu(summaries, highlight_idx=selected)
            choice = input(">> ").strip().lower()
            if choice == "q":
                sys.exit(0)
            if choice.isdigit():
                idx = int(choice) - 1
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
    frame = "\n".join(lines)
    clear_screen()
    sys.stdout.write(frame)
    sys.stdout.flush()


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


def wrap_ui_text(text):
    term_w, _ = get_term_size()
    box_w = max(config.MIN_BOX_WIDTH, term_w - config.BOX_MARGIN * 2)
    inner_w = box_w - 2
    panel_width = max(int(inner_w * 0.25) - 6, 20)
    clean = ANSI_ESCAPE.sub("", text)
    return textwrap.wrap(clean, width=panel_width)


def build_tree_lines(upgrades, get_info_fn, page_key):
    term_w, term_h = get_term_size()
    max_lines = term_h // 2 - 6
    pool_suffix = (
        layer_currency_suffix("corridor")
        if upgrades is INSPIRE_UPGRADES
        else layer_currency_suffix("archive")
    )
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
        owned_text = (
            "(MAX)"
            if level >= max_level
            else (f"(lvl {level}/{max_level})" if level > 0 else "")
        )
        suffix_text = f" {pool_suffix}" if pool_suffix else ""
        cost_text = (
            f" - Cost: {format_number(cost)}{suffix_text}"
            if level < max_level
            else ""
        )
        line_head = f"{i}. {u['name']} {owned_text}{cost_text}"
        lines = [line_head]
        if u.get("desc"):
            desc_text = f"→ {u['desc']}"
            if level > 0 and u["type"] not in ("unlock_motivation", "unlock_autowork"):
                desc_text += f" (x{total_mult:.2f})"
            if u["type"] == "unlock_motivation":
                motiv = game.get("motivation", MOTIVATION_MAX)
                motiv_mult = 1 + (motiv / MOTIVATION_MAX) * (MAX_MOTIVATION_MULT - 1)
                desc_text += f" (x{motiv_mult:.2f})"
            wrapped = wrap_ui_text(desc_text)
            lines += ["     " + w for w in wrapped]
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
        owned_text = (
            "(MAX)"
            if level >= max_level
            else (f"(lvl {level}/{max_level})" if level > 0 else "")
        )
        cost_text = (
            f" - Cost: {format_number(cost)}"
            + ("i" if upgrades is INSPIRE_UPGRADES else "Co")
            if level < max_level
            else ""
        )
        head = f"{i}. {u['name']} {owned_text}{cost_text}"
        block = [head]
        if u.get("desc"):
            desc_text = f"→ {u['desc']}"
            if level > 0 and u["type"] not in ("unlock_motivation", "unlock_autowork"):
                desc_text += f" (x{total_mult:.2f})"
            wrapped = wrap_ui_text(desc_text)
            block += ["     " + w for w in wrapped]
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
            "focus": 0,
            "owned": [],
            "upgrade_levels": {},
            "concepts_unlocked": True,
            "layer": max(game.get("layer", 0), 2),
            "inspiration_upgrades": [],
            "inspiration": 0,
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
        lines = ["--- UPGRADE BAY ---" if catalogue_known else "--- [REDACTED] ---"]
        lines.append(f"Money: {format_currency(game.get('money', 0))}")
        lines.append("")
        for i, u in enumerate(unlocked, start=1):
            term_w, _ = get_term_size()
            box_w = max(config.MIN_BOX_WIDTH, term_w - config.BOX_MARGIN * 2)
            inner_w = box_w - 2
            panel_width = max(int(inner_w * 0.25), 20)
            level = game.get("upgrade_levels", {}).get(u["id"], 0)
            max_level = u.get("max_level", 1)
            cost = int(u.get("cost", 0) * (u.get("cost_mult", 1) ** level))
            status = (
                f"(Lv {level}/{max_level}) - Cost: {format_currency(cost)}"
                if level < max_level
                else "(MAX)"
            )
            uid = u["id"]
            known_upgrade = catalogue_known or is_known(f"upgrade_{uid}")
            display_name = u["name"] if known_upgrade else veil_text(u["name"])
            line = f"{i}. {display_name} {status if known_upgrade else status}"
            lines.append(line.ljust(panel_width))
            if u.get("desc"):
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
                wrapped = wrap_ui_text(effect_text)
                lines += ["   " + w for w in wrapped]
        lines += ["", "Press number to buy, B to back."]
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
        msg = f"Purchased {upg['name']} Lv {current_level}/{max_level}."
    tmp = boxed_lines([msg], title=" UPGRADE BAY ", pad_top=1, pad_bottom=1)
    render_frame(tmp)
    time.sleep(0.7)
    save_game()


def play_inspiration_reset_animation():
    term_w, term_h = shutil.get_terminal_size(fallback=(80, 24))
    num_zs = 5
    frames = 15
    z_lifetime = 6
    zs = []
    for frame in range(frames):
        clear_screen()
        screen = [" " * term_w for _ in range(term_h)]
        if len(zs) < num_zs and random.random() < 0.3:
            zs.append(
                {
                    "y": term_h - 4,
                    "x": term_w // 2 + random.randint(-10, 10),
                    "life": z_lifetime,
                }
            )
        for z in zs:
            y, x = int(z["y"]), int(z["x"])
            if 0 <= y < term_h and 0 <= x < term_w:
                row = screen[y]
                screen[y] = row[:x] + "Z" + row[x + 1 :]
        print("\n".join(screen))
        for z in zs:
            z["y"] -= 1
            z["x"] += random.choice([-1, 0, 1])
            z["life"] -= 1
        zs = [z for z in zs if z["life"] > 0]
        time.sleep(0.2)
    clear_screen()
    print("\n" * (term_h // 2))
    print("!".center(term_w))
    time.sleep(0.6)


def play_concepts_animation():
    term_w, term_h = shutil.get_terminal_size(fallback=(80, 24))
    frames = 22
    shards = []
    for f in range(frames):
        clear_screen()
        screen = [" " * term_w for _ in range(term_h)]
        if random.random() < 0.35:
            shards.append(
                {
                    "y": term_h - 4,
                    "x": term_w // 2 + random.randint(-14, 14),
                    "life": random.randint(4, 8),
                }
            )
        for s in shards:
            y, x = int(s["y"]), int(s["x"])
            if 0 <= y < term_h and 0 <= x < term_w:
                ch = random.choice(["*", "o", "+", "·"])
                row = screen[y]
                screen[y] = row[:x] + ch + row[x + 1 :]
        print("\n".join(screen))
        new_shards = []
        for s in shards:
            s["y"] -= 1 + random.random() * 0.6
            s["x"] += random.choice([-1, 0, 1])
            s["life"] -= 1
            if s["life"] > 0 and s["y"] >= 0:
                new_shards.append(s)
        shards = new_shards
        time.sleep(0.09)
    clear_screen()
    mid = term_h // 2
    lines = [" " * term_w for _ in range(term_h)]
    title = "Ah HA"
    lines[mid] = title.center(term_w)
    print("\n".join(lines))
    time.sleep(0.7)


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

    sparks_amount = format_number(game.get("stability_currency", 0))
    middle_lines = [
        build_wake_timer_line(),
        f"{STABILITY_CURRENCY_NAME}: {Fore.MAGENTA}{sparks_amount}{Style.RESET_ALL}",
    ]
    if not game.get("wake_timer_infinite", False):
        middle_lines.append("[T] Spend stabilizers")
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
        ansi_visible_slice(line, view_offset_x, term_width) for line in visible_lines
    ]
    output = "\033[H" + "\n".join(visible_lines)
    if output != last_render:
        sys.stdout.write("\033[H")
        sys.stdout.write(output)
        sys.stdout.flush()
        last_render = output


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

            render_ui(screen=current_screen)
            if KEY_PRESSED:
                k_raw = KEY_PRESSED
                KEY_PRESSED = None
                if isinstance(k_raw, str) and k_raw.startswith("\x1b"):
                    if k_raw in ("\x1b[A", "\x1b[B", "\x1b[C", "\x1b[D"):
                        if k_raw == "\x1b[A":
                            view_offset_y = max(0, view_offset_y - 1)
                        elif k_raw == "\x1b[B":
                            view_offset_y = max(0, view_offset_y + 1)
                        elif k_raw == "\x1b[C":
                            view_offset_x = max(0, view_offset_x + 2)
                        elif k_raw == "\x1b[D":
                            view_offset_x = max(0, view_offset_x - 2)
                        continue
                    continue

                try:
                    k = k_raw.lower()
                except Exception:
                    k = k_raw

                if k == "q":
                    running = False
                    break
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
                elif k == "t":
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
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        save_game()
        clear_screen()
        print("Saved. Bye!")


if __name__ == "__main__":
    main_loop()
    os.system("cls" if os.name == "nt" else "clear")
