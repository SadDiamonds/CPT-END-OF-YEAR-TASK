import json, os, time, sys, threading, shutil, math, select, random, textwrap, subprocess, re, traceback

try:
    import msvcrt
except:
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
    format_number,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
SAVE_PATH = os.path.join(DATA_DIR, "save.json")

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
}


def load_game():
    global game
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r") as f:
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
    save_game()


def save_game():
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(game, f)
    except:
        pass


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
        cost_text = (
            f" - Cost: {format_number(cost)}"
            + ("i" if upgrades is INSPIRE_UPGRADES else "Co")
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
            if rtype in ("x$", "xmult"):
                gain_mult *= rval * buff_mult
            elif rtype == "-cd":
                delay_mult *= rval**buff_mult
    if time.time() < focus_active_until:
        delay_mult *= FOCUS_BOOST_FACTOR
    eff_gain = (base_gain + gain_add) * gain_mult
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
    if layer in (0, 1, 2):
        style = config.BORDERS.get(0, list(config.BORDERS.values())[-1])
    elif layer == 3:
        style = config.BORDERS.get(3, config.BORDERS.get(0))
    else:
        style = config.BORDERS.get(layer, list(config.BORDERS.values())[-1])

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
            p_count = getattr(config, "LAYER3_PARTICLE_COUNT", 0)
            if p_count > 0:
                p_chars = getattr(config, "LAYER3_PARTICLE_CHARS", ["·", "*", "."])
                p_amp = getattr(config, "LAYER3_PARTICLE_AMPLITUDE", 8)
                p_freq = getattr(config, "LAYER3_PARTICLE_FREQ", 3)
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
    owned_ids = [u["id"] for u in config.UPGRADES if u["id"] in game.get("owned", [])]
    for new, old in getattr(config, "UPGRADE_REPLACEMENT", {}).items():
        if new in owned_ids and old in owned_ids:
            owned_ids.remove(old)
    owned_ids.sort(
        key=lambda uid: (
            config.DESK_ORDER.index(uid)
            if uid in getattr(config, "DESK_ORDER", [])
            else 999
        )
    )
    owned_arts = [UPGRADE_ART[uid] for uid in owned_ids if uid in UPGRADE_ART]
    empty_indices = [
        i for i, line in enumerate(table) if line.startswith("║") and line.endswith("║")
    ]
    empty_idx_iter = reversed(empty_indices)
    for art in owned_arts:
        art_height = len(art)
        try:
            art_positions = [next(empty_idx_iter) for _ in range(art_height)]
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
    game["money"] += gain
    game["money_since_reset"] += gain
    if game.get("focus_unlocked", False) and now >= focus_active_until:
        game["focus"] = min(FOCUS_MAX, game.get("focus", 0) + FOCUS_CHARGE_PER_EARN)
    if game.get("motivation_unlocked", False):
        game["motivation"] = max(0, game.get("motivation", 0) - 1)
    if not manual and game.get("auto_work_unlocked", False):
        work_timer = max(0.0, work_timer - eff_delay)
    save_game()


def work_tick():
    global last_tick_time, work_timer
    now = time.time()
    delta = now - last_tick_time
    last_tick_time = now
    gain, eff_delay = compute_gain_and_delay(auto=True)
    if game.get("auto_work_unlocked", False):
        work_timer += delta
        if work_timer >= eff_delay:
            perform_work(gain, eff_delay, manual=False)
    if game.get("charge_unlocked", False):
        game["charge"] += delta
        game["best_charge"] = max(game["best_charge"], game["charge"])
        check_charge_thresholds()


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
    if level >= max_level:
        msg = f"{upg['name']} is already at max level!"
        tmp = boxed_lines(
            [msg],
            title=("Inspiration" if upgrades is INSPIRE_UPGRADES else "Concepts"),
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(0.7)
        return
    cost = get_tree_cost(upg, current_level=level)
    pool_key = "inspiration" if upgrades is INSPIRE_UPGRADES else "concepts"
    if game.get(pool_key, 0) < cost:
        msg = f"Not enough {('Inspiration' if pool_key=='inspiration' else 'Concepts')} for {upg['name']} (cost {cost})!"
        tmp = boxed_lines(
            [msg],
            title=("Inspiration" if upgrades is INSPIRE_UPGRADES else "Concepts"),
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
        title=("Inspiration" if upgrades is INSPIRE_UPGRADES else "Concepts"),
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
    if game.get("money_since_reset", 0) < INSPIRATION_UNLOCK_MONEY:
        tmp = boxed_lines(
            [
                f"{Fore.YELLOW}Reach ${format_number(INSPIRATION_UNLOCK_MONEY)} to Inspire.{Style.RESET_ALL}"
            ],
            title=" Inspire ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
        time.sleep(1.0)
        return
    gained = calculate_inspiration(game.get("money_since_reset", 0))
    play_inspiration_reset_animation()
    game["inspiration"] = game.get("inspiration", 0) + gained
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
    if game.get("motivation_unlocked", False):
        game.update({"motivation": MOTIVATION_MAX})
    apply_inspiration_effects()
    save_game()
    done_msg = boxed_lines(
        [f"Gained {Fore.LIGHTYELLOW_EX}{gained}{Style.RESET_ALL} Inspiration."],
        title=" Inspiration Gained ",
        pad_top=1,
        pad_bottom=1,
    )
    render_frame(done_msg)
    time.sleep(1.2)


def reset_for_concepts():
    now = time.time()
    if now - game.get("last_concepts_reset_time", 0) < 0.05:
        return
    if game.get("money_since_reset", 0) < CONCEPTS_UNLOCK_MONEY:
        tmp = boxed_lines(
            [f"Reach ${format_number(CONCEPTS_UNLOCK_MONEY)} to Conceptualise."],
            title=" Concepts ",
            pad_top=1,
            pad_bottom=1,
        )
        render_frame(tmp)
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
    apply_concept_effects()
    save_game()
    done_msg = boxed_lines(
        [f"Gained {Fore.CYAN}{gained}{Style.RESET_ALL} Concepts."],
        title=" Concepts Gained ",
        pad_top=1,
        pad_bottom=1,
    )
    render_frame(done_msg)
    time.sleep(1.2)


def open_upgrade_menu():
    global KEY_PRESSED
    while True:
        work_tick()
        unlocked = [
            u
            for u in config.UPGRADES
            if u.get("unlocked", False)
            or all(
                dep in game.get("owned", [])
                for dep in config.UPGRADE_DEPENDENCIES.get(u["id"], [])
            )
        ]
        lines = ["--- UPGRADE BAY ---"]
        lines.append(f"Money: ${format_number(game.get('money', 0))}")
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
                f"(Lv {level}/{max_level}) - Cost: ${format_number(cost)}"
                if level < max_level
                else "(MAX)"
            )
            line = f"{i}. {u['name']} {status}"
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
        render_frame(box)
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
        msg = f"Not enough money for {upg['name']} (cost ${scaled_cost})."
    else:
        game["money"] -= scaled_cost
        current_level += 1
        game["upgrade_levels"][uid] = current_level
        if uid not in game["owned"]:
            game["owned"].append(uid)
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

    # Inspiration panel
    top_left_lines = []
    insp_title = f"=== {Fore.LIGHTYELLOW_EX}INSPIRATION{Style.RESET_ALL} ==="
    insp_tree_title = f"=== {Fore.LIGHTYELLOW_EX}INSPIRATION TREE{Style.RESET_ALL} ==="
    conc_title = f"=== {Fore.CYAN}CONCEPTS{Style.RESET_ALL} ==="
    conc_tree_title = f"=== {Fore.CYAN}CONCEPTS TREE{Style.RESET_ALL} ==="
    if (
        game.get("money_since_reset", 0) >= INSPIRATION_UNLOCK_MONEY // 2
        or game.get("inspiration_unlocked", False) == True
    ):
        top_left_lines += [
            insp_title,
            "",
            f"Points: {Fore.LIGHTYELLOW_EX}{format_number(game.get('inspiration', 0))} i{Style.RESET_ALL}",
            "",
        ]
        if game.get("money_since_reset", 0) >= INSPIRATION_UNLOCK_MONEY:
            top_left_lines.append(
                f"[I]nspire for {Fore.LIGHTYELLOW_EX}{format_number(calc_insp)}{Style.RESET_ALL} Inspiration"
            )
            top_left_lines.append(
                f"{Fore.LIGHTYELLOW_EX}{format_number(time_next)}{Style.RESET_ALL} until next point"
            )
            top_left_lines.append("")
            top_left_lines.append("[1] to open Inspiration tree")
        else:
            top_left_lines.append(
                f"Reach ${format_number(INSPIRATION_UNLOCK_MONEY)} to"
                + (
                    "unlock Inspiration"
                    if not game.get("inspiration_unlocked", False)
                    else " Inspire"
                )
            )
            if screen == "inspiration":
                top_left_lines.append("")
            else:
                top_left_lines.append("")
                top_left_lines.append("[1] to open Inspiration tree")
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

    # Concepts panel
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
                f"Points: {Fore.CYAN}{format_number(game.get('concepts', 0))} Co{Style.RESET_ALL}"
            )
            bottom_left_lines.append("")
        if game.get("money_since_reset", 0) >= CONCEPTS_UNLOCK_MONEY:
            bottom_left_lines.append(
                f"[C]onceptualise for {Fore.CYAN}{format_number(calc_conc)}{Style.RESET_ALL} Concepts"
            )
            bottom_left_lines.append(
                f"{Fore.CYAN}{format_number(conc_time_next)}{Style.RESET_ALL} until next point"
            )
            bottom_left_lines.append("")
            bottom_left_lines.append("[2] to open Concepts tree")
        else:
            bottom_left_lines.append(
                (f"Reach ${format_number(CONCEPTS_UNLOCK_MONEY)} to ")
                + ("unlock" if not game.get("concepts_unlocked", False) else "")
                + (
                    "Concepts"
                    if not game.get("concepts_unlocked", False)
                    else "Conceptualise"
                )
            )
            bottom_left_lines.append("")
            bottom_left_lines.append("[2] to open Concepts tree")
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
    middle_lines = []
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
    middle_lines.append(
        f"MONEY: ${format_number(game.get('money', 0))}   GAIN: {format_number(effective_gain)} / cycle"
        + (
            f"   DELAY: {effective_delay:.2f}s"
            if game.get("auto_work_unlocked", False)
            else ""
        )
    )
    middle_lines.append(work_bar)
    middle_lines.append(
        "Auto-work: ENABLED"
        if game.get("auto_work_unlocked", False)
        else "Press W to work"
    )
    middle_lines += ["", "Options: [W]ork  [U]pgrades  [Q]uit"]
    term_width, term_height = get_term_size()
    max_lines = max(len(top_left_lines), len(bottom_left_lines), len(middle_lines))
    while len(top_left_lines) < term_h - 4:
        top_left_lines.append("")
    while len(bottom_left_lines) < term_h - 4:
        bottom_left_lines.append("")
    while len(middle_lines) < term_h - 4:
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
    box = boxed_lines(
        combined_lines, title=f" Layer {game.get('layer', 0)} ", pad_top=1, pad_bottom=1
    )

    if resized:
        print("\033[2J\033[H", end="")
        last_size = current_size
        last_render = ""
        view_offset_x = 0
        view_offset_y = 0
    visible_lines = box[view_offset_y : view_offset_y + term_h]
    visible_lines = [
        ansi_visible_slice(line, view_offset_x, term_w) for line in visible_lines
    ]
    output = "\033[H" + "\n".join(visible_lines)
    if output != last_render:
        sys.stdout.write("\033[H")
        sys.stdout.write(output)
        sys.stdout.flush()
        last_render = output


def main_loop():
    global KEY_PRESSED, running, work_timer, last_tick_time, last_manual_time
    load_game()
    last_tick_time = time.time()
    threading.Thread(target=key_listener, daemon=True).start()
    if game.get("layer", 0) >= 1 and not game.get("inspiration_unlocked", False):
        game["inspiration_unlocked"] = True
        game["layer"] = 1
        save_game()
    current_screen = "work"
    global view_offset_x, view_offset_y
    try:
        while running:
            work_tick()
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
                        # skip normal key processing for escape sequences
                        continue
                    # ignore other escape sequences
                    continue

                # Normal single-character keys
                try:
                    k = k_raw.lower()
                except Exception:
                    k = k_raw

                if k == "q":
                    running = False
                    break
                elif k == "w":
                    now = time.time()
                    if now - last_manual_time > 0.2:
                        gain, eff_delay = compute_gain_and_delay(auto=False)
                        if not game.get("auto_work_unlocked", False):
                            work_timer = 0
                        perform_work(gain, eff_delay, manual=True)
                        last_manual_time = now
                elif k == "u":
                    current_screen = "work"
                    clear_screen()
                    open_upgrade_menu()
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
                        term_w, term_h = get_term_size()
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
