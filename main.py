import json, os, time, sys, threading, shutil, math, select, random, textwrap

try:
    import msvcrt
except:
    msvcrt = None
from ascii_art import (
    LAYER_0_DESK,
    UPGRADE_ART,
)
import config
from config import INSPIRE_UPGRADES, format_number, INSPIRATION_MILESTONES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
SAVE_PATH = os.path.join(DATA_DIR, "save.json")

last_tick_time = time.time()
last_render, last_size = "", (0, 0)
work_timer, KEY_PRESSED, running, focus_active_until = 0.0, None, True, 0.0
steam = []
all_upgrades = [u.copy() for u in config.UPGRADES]
view_offset_x = 0
view_offset_y = 0

game = {
    "layer": 0,
    "money": 0.0,
    "fatigue": 0,
    "focus": 0,
    "inspiration": 0,
    "owned": [],
    "focus_unlocked": False,
    "base_work_delay": config.BASE_WORK_DELAY,
    "base_money_gain": config.BASE_MONEY_GAIN,
    "auto_work_unlocked": False,
    "money_since_reset": 0,
    "motivation": 0,
    "motivation_unlocked": False,
    "total_inspirations": 0,
    "caffeine_points": 0.0,
    "inspiration_unlocked": False,
    "inspiration_upgrades": [],
    "work_delay_multiplier": 1.0,
    "money_mult": 1.0,
    "focus_max_bonus": 0,
    "milestones_earned": [],
    "upgrade_levels": {},
    "charge": 0.0,
    "best_charge": 0.0,
    "charge_threshold": [],
    "charge_unlocked": False,
    "battery_tier": 1,
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
    game["base_money_gain"] = config.BASE_MONEY_GAIN
    game["base_work_delay"] = config.BASE_WORK_DELAY
    game.setdefault("money_mult", config.BASE_MONEY_MULT)
    for k, v in {
        "owned": [],
        "focus_unlocked": False,
        "inspiration_unlocked": False,
        "inspiration_upgrades": [],
        "work_delay_multiplier": 1.0,
        "money_mult": game["money_mult"],
        "focus_max_bonus": 0,
        "auto_work_unlocked": False,
        "motivation_unlocked": False,
        "total_inspirations": 0,
        "milestones_earned": [],
        "caffeine_points": 0.0,
        "upgrade_levels": {},
    }.items():
        game.setdefault(k, v)
    if get_inspire_info("inspire_auto_work")[0]:
        game["auto_work_unlocked"] = True
    if get_inspire_info("inspire_motiv")[0]:
        game["motivation_unlocked"] = True
        if game.get("motivation", 0) <= 0:
            game["motivation"] = config.MOTIVATION_MAX
    check_inspiration_milestones()
    save_game()


def save_game():
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(game, f)
    except Exception as e:
        print("Save failed:", e)


def get_term_size():
    try:
        s = shutil.get_terminal_size(fallback=(80, 24))
        return s.columns, s.lines
    except:
        return 80, 24


def convert_old_upgrades():
    new_list = []
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, str):
            new_list.append({"id": u, "level": 1})
        elif isinstance(u, dict):
            new_list.append(u)
    game["inspiration_upgrades"] = new_list


def clear_screen():
    sys.stdout.write("\033[H\033[J")
    sys.stdout.flush()


def check_inspiration_milestones():
    total = game.get("total_inspirations", 0)
    earned = game.setdefault("milestones_earned", [])
    for m in INSPIRATION_MILESTONES:
        req = m["inspirations_required"]
        if req not in earned and total >= req:
            earned.append(req)
            if m["reward_type"] == "xmult":
                game["money_mult"] *= m["reward_value"]
            elif m["reward_type"] == "+mult":
                game["money_mult"] += m["reward_value"]
            elif m["reward_type"] == "-cd":
                game["work_delay_multiplier"] *= m["reward_value"]
    save_game()


def get_inspire_info(upg_id):
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return True, u.get("level", 1)
        elif isinstance(u, str) and u == upg_id:
            return True, 1
    return False, 0


def render_battery(charge, tier=None):
    if tier is None:
        tier = game.get("battery_tier", 1)
    tier_info = config.BATTERY_TIERS.get(tier, config.BATTERY_TIERS[1])
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

    battery_block = [
        "┌" + "─" * inner_w + "┐",
        f"│{val_str}│",
        "├" + "─" * inner_w + "┤",
        *rows,
        "└" + "─" * inner_w + "┘",
    ]
    return battery_block

def check_research_requirement():
    total_rows = 5
    filled_rows = int((game["charge"] / game["max_charge"]) * total_rows)
    if filled_rows >= 3:
        game["next_reset_unlocked"] = True


def wrap_ui_text(text):
    term_w, _ = get_term_size()
    box_w = max(config.MIN_BOX_WIDTH, term_w - config.BOX_MARGIN * 2)
    inner_w = box_w - 2
    panel_width = max(int(inner_w * 0.25) - 6, 20)
    return textwrap.wrap(text, width=panel_width)


def apply_upgrade_effects():
    game.setdefault("upgrade_levels", {})
    for upg in config.UPGRADES:
        uid = upg["id"]
        level = game["upgrade_levels"].get(uid, 0)
        if upg.get("type") == "unlock_focus" and level > 0:
            game["focus_unlocked"] = True


def total_inspiration(amount=1):
    game["total_inspirations"] = game.get("total_inspirations", 0) + amount
    earned = game.setdefault("milestones_earned", [])
    for m in INSPIRATION_MILESTONES:
        req = m["inspirations_required"]
        if req not in earned and game["total_inspirations"] >= req:
            earned.append(req)
            if m["reward_type"] == "xmult":
                game["money_mult"] *= m["reward_value"]
            elif m["reward_type"] == "+mult":
                game["money_mult"] += m["reward_value"]
            elif m["reward_type"] == "-cd":
                game["work_delay_multiplier"] *= m["reward_value"]
    save_game()


def render_milestones_lines():
    lines = ["=== MILESTONES ==="]
    total_insp = game.get("total_inspirations", 0)
    earned = set(game.get("milestones_earned", []))
    for m in INSPIRATION_MILESTONES:
        req = m.get("inspirations_required", 0)
        rtype = m.get("reward_type", "")
        rval = m.get("reward_value", "")
        unlocked = req in earned or total_insp >= req
        status = "✓" if unlocked else "✗"
        if rtype == "xmult":
            desc = f"x${rval}"
        elif rtype == "+mult":
            desc = f"+${rval}"
        elif rtype in ("-cd", "reduce_cd"):
            desc = f"/{rval} work delay"
        else:
            desc = f"{rtype} {rval}"
        lines.append(f"{status} {req} i → {desc}")
    return lines


def apply_viewport(lines):
    term_w, term_h = get_term_size()
    visible_lines = lines[view_offset_y : view_offset_y + term_h]
    return [line[view_offset_x : view_offset_x + term_w] for line in visible_lines]


def compute_gain_and_delay():
    base_gain = game.get("base_money_gain", config.BASE_MONEY_GAIN)
    base_delay = game.get("base_work_delay", config.BASE_WORK_DELAY)
    gain_add = 0.0
    gain_mult = 1.0
    delay_mult = game.get("work_delay_multiplier", 1.0)
    lvl_map = game.get("upgrade_levels", {})
    for u in all_upgrades:
        uid = u["id"]
        level = int(lvl_map.get(uid, 0))
        if level <= 0:
            continue
        typ = u.get("type", "mult")
        if typ == "add":
            gain_add += float(u.get("base_value", u.get("value", 0))) * level
        elif typ == "mult":
            base = float(u.get("base_value", u.get("value", 1)))
            val_mult = float(u.get("value_mult", 1))
            effective = base * (val_mult ** max(0, (level - 1)))
            gain_mult *= effective
        elif typ == "reduce_delay":
            base_val = float(u.get("base_value", u.get("value", 1)))
            val_mult = float(u.get("value_mult", 1))
            effective = base_val * (val_mult ** max(0, (level - 1)))
            delay_mult *= effective
        elif typ == "unlock_focus":
            game["focus_unlocked"] = True
    applied_ids = set()
    for entry in game.get("inspiration_upgrades", []):
        upg_id, level = (
            (entry.get("id"), entry.get("level", 1))
            if isinstance(entry, dict)
            else (entry, 1)
        )
        if upg_id in applied_ids:
            continue
        applied_ids.add(upg_id)
        u = next((x for x in INSPIRE_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue
        base = float(u.get("base_value", u.get("value", 1)))
        val_mult = float(u.get("value_mult", 1))
        val = base * (val_mult ** max(0, (level - 1)))
        if u["type"] == "money_mult":
            gain_mult *= val
        elif u["type"] == "work_mult":
            delay_mult *= val
        elif u["type"] == "focus_max":
            game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + val
        elif u["type"] == "unlock_motivation":
            game["motivation_unlocked"] = True
        elif u["type"] == "auto_work":
            game["auto_work_unlocked"] = True
        elif u["type"] == "unlock_charge":
            game["charge_unlocked"] = True
        elif u["type"] == "battery_t2":
            game["battery_tier"] = 2
    buff_mult = get_charge_bonus()
    for t in config.CHARGE_THRESHOLDS:
        if t["amount"] in game.get("charge_threshold", []):
            if t["reward_type"] == "x$":
                gain_mult *= t["reward_value"] * buff_mult
            elif t["reward_type"] == "-cd":
                delay_mult *= t["reward_value"] ** buff_mult
    eff_gain = (base_gain + gain_add) * gain_mult
    eff_delay = base_delay * delay_mult
    if time.time() < focus_active_until:
        eff_delay *= config.FOCUS_BOOST_FACTOR
    motivation = game.get(
        "motivation", config.MOTIVATION_MAX if game.get("motivation_unlocked") else 0
    )
    motivation_mult = 1 + (motivation / max(1, config.MOTIVATION_MAX)) * (
        config.MAX_MOTIVATION_MULT - 1
    )
    gain_mult *= get_charge_bonus()
    eff_gain *= motivation_mult
    eff_gain *= config.BASE_MONEY_MULT
    eff_gain *= game.get("money_mult", 1.0)
    eff_delay = max(eff_delay, 0.01)
    return eff_gain, eff_delay


def boxed_lines(
    content_lines, title=None, pad_top=1, pad_bottom=1, margin=config.BOX_MARGIN
):
    term_w, term_h = get_term_size()
    box_w = max(config.MIN_BOX_WIDTH, term_w - margin * 2)
    inner_w = box_w - 2
    layer = game.get("layer", 0)
    style = config.BORDERS.get(layer, list(config.BORDERS.values())[-1])
    tl, tr, bl, br = style["tl"], style["tr"], style["bl"], style["br"]
    h, v = style["h"], style["v"]
    if title:
        t = f" {title} "
        if len(t) >= inner_w:
            top = tl + h * inner_w + tr
        else:
            left = (inner_w - len(t)) // 2
            top = tl + h * left + t + h * (inner_w - left - len(t)) + tr
    else:
        top = tl + h * inner_w + tr
    lines = [top]
    for _ in range(pad_top):
        lines.append(v + " " * inner_w + v)
    for raw in content_lines:
        if raw is None:
            raw = ""
        segs = []
        if len(raw) <= inner_w:
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
            lines.append(v + s.center(inner_w) + v)
    for _ in range(pad_bottom):
        lines.append(v + " " * inner_w + v)
    lines.append(bl + h * inner_w + br)
    left_margin = max(0, (term_w - box_w) // 2)
    margin_str = " " * left_margin
    return [margin_str + l for l in lines]


def render_ui(screen="work"):
    global last_render, last_size, view_offset_x, view_offset_y
    current_size = get_term_size()
    resized = current_size != last_size
    effective_gain, effective_delay = compute_gain_and_delay()
    prog = (
        min(work_timer / effective_delay, 1.0)
        if game.get("auto_work_unlocked", False)
        else 0
    )
    bar_len = 36
    filled = int(prog * bar_len)
    work_bar = f"[{'#' * filled}{'-' * (bar_len - filled)}] {int(prog * 100):3d}%"
    calc_insp = calculate_inspiration(game.get("money_since_reset", 0))
    time_next = predict_next_point()
    top_left_lines = []
    if game.get("inspiration_unlocked", False):
        if screen == "work":
            top_left_lines += [
                "=== INSPIRATION ===",
                f"Points: {format_number(game.get('inspiration', 0))} i",
                "",
                "[1] Open Inspiration Tree",
                "",
            ]
            if game.get("money", 0) >= 1000:
                top_left_lines.append(
                    f"[I]nspire for {format_number(calc_insp)} Inspiration"
                )
                top_left_lines.append(f"{format_number(time_next)} until next point")
        elif screen == "inspiration":
            top_left_lines += [
                "=== INSPIRATION TREE ===",
                f"Points: {format_number(game.get('inspiration', 0))} i",
                "",
            ]
            for i, u in enumerate(INSPIRE_UPGRADES, start=1):
                owned, level = get_inspire_info(u["id"])
                max_level = u.get("max_level", 1)
                cost = get_inspire_cost(u, current_level=level)
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
                    f" - Cost: {format_number(cost)}i" if level < max_level else ""
                )
                top_left_lines.append(f"{i}. {u['name']} {owned_text}{cost_text}")
                if u.get("desc"):
                    desc_text = f"→ {u['desc']}"
                    if level > 0 and u["type"] not in (
                        "unlock_motivation",
                        "unlock_charge",
                        "auto_work",
                    ):
                        desc_text += f" (x{total_mult:.2f})"
                    elif u["type"] == "unlock_motivation":
                        motiv = game.get("motivation", config.MOTIVATION_MAX)
                        motiv_mult = 1 + (
                            (motiv / config.MOTIVATION_MAX)
                            * (config.MAX_MOTIVATION_MULT - 1)
                        )
                        desc_text += f" (x{motiv_mult:.2f})"
                    wrapped = wrap_ui_text(desc_text)
                    top_left_lines += ["     " + w for w in wrapped]
            top_left_lines += ["", "[B] Back to Work"]
    elif 100000 > game.get("money_since_reset", 0) >= 50000:
        top_left_lines += [
            "       === INSPIRATION ===",
            "",
            "Reach $1000 to unlock Inspiration",
        ]
    elif game.get("money_since_reset", 0) >= 100000:
        top_left_lines += ["       === INSPIRATION ===", ""]
        for desc in [
            "You realise the pointlessness of this mundane work",
            "Perhaps there is more to life than work?",
            f"[I]nspire for {format_number(calc_insp)} Inspiration",
        ]:
            wrapped = wrap_ui_text(desc)
            top_left_lines += ["   " + line for line in wrapped]
        top_left_lines.append("")
    bottom_left_lines = []
    if game.get("inspiration_unlocked", False):
        bottom_left_lines += [""] + render_milestones_lines()
    middle_lines = []
    middle_lines += render_desk_table()
    if game.get("focus_unlocked", False):
        focus_max = config.FOCUS_MAX + game.get("focus_max_bonus", 0)
        fprog = min(game.get("focus", 0) / float(focus_max), 1.0)
        fbar_len = 36
        ffilled = int(fprog * fbar_len)
        middle_lines += [
            f"FOCUS: {int(fprog * 100):3d}%",
            "[" + "#" * ffilled + "-" * (fbar_len - ffilled) + "]",
            "",
        ]
    owned_motiv, _ = get_inspire_info("inspire_motiv")
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
        (
            "Auto-work: ENABLED"
            if game.get("auto_work_unlocked", False)
            else "Press W to work"
        )
        + (
            f"   Motivation: {int((game.get('motivation', config.MOTIVATION_MAX)/config.MOTIVATION_MAX)*100)}%"
            if owned_motiv
            else ""
        )
    )
    owned_names = [u["name"] for u in all_upgrades if u["id"] in game.get("owned", [])]
    middle_lines += [
        "",
        "Owned Upgrades: " + (", ".join(owned_names) if owned_names else "(none)"),
    ]
    options = "[W]ork  [U]pgrade  [F]ocus"
    if game.get("inspiration_unlocked", False):
        options += "  [I]nspire"
    options += "  [Q]uit"
    middle_lines += ["", "Options: " + options]
    term_width, term_height = get_term_size()
    top_height = len(top_left_lines)
    desired_midpoint = term_height // 2
    gap_lines = max(0, desired_midpoint - top_height)
    left_lines = top_left_lines + ([""] * gap_lines) + bottom_left_lines
    right_content_height = len(middle_lines)
    total_box_height_middle = right_content_height + 1 + 1 + 2
    empty_lines_needed_middle = max(term_height - total_box_height_middle, 0)
    middle_lines = ([""] * empty_lines_needed_middle) + middle_lines
    right_lines = []
    col_width = int(term_width * 0.25)
    if game.get("charge_unlocked", False):
        right_lines.append("=== BATTERY ===".center(col_width))
        battery_art = render_battery(game.get("charge", 0), tier=game.get("battery_tier", 1))
        right_lines += [line.center(col_width) for line in battery_art]
        buff_mult = get_charge_bonus()
        right_lines.append(f"Buffs all charge thresholds by x{buff_mult:.2f}".center(col_width))
        right_lines.append("Milestones:".center(col_width))
        for t in config.CHARGE_THRESHOLDS:
            req = t["amount"]
            status = "✓" if req in game.get("charge_threshold", []) else "✗"
            eff_value = t["reward_value"] * buff_mult
            desc = f"{status} {req}Ω → {t['reward_type']} {eff_value:.2f}"
            right_lines.append(desc.center(col_width))
    max_lines = max(len(left_lines), len(middle_lines), len(right_lines))
    while len(left_lines) < max_lines:
        left_lines.append("")
    while len(middle_lines) < max_lines:
        middle_lines.append("")
    while len(right_lines) < max_lines:
        right_lines.append("")
    combined_lines = [
        l.ljust(int(term_width * 0.25))
        + " " * 2
        + m.ljust(int(term_width * 0.35))
        + " " * 2
        + r.ljust(int(term_width * 0.25))
        for l, m, r in zip(left_lines, middle_lines, right_lines)
    ]
    box = boxed_lines(
        combined_lines, title=f" Layer {game.get('layer', 0)} ", pad_top=1, pad_bottom=1
    )
    if resized:
        print("\033[2J\033[H", end="")
        last_size = current_size
        last_render = ""
        view_offset_x = 0
        view_offset_y = 0
    term_w, term_h = get_term_size()
    visible_lines = box[view_offset_y : view_offset_y + term_h]
    visible_lines = [
        line[view_offset_x : view_offset_x + term_w] for line in visible_lines
    ]
    output = "\033[H" + "\n".join(visible_lines)
    if output != last_render:
        clear_screen()
        print(output, end="", flush=True)
        last_render = output


def render_desk_table():
    global steam
    table = LAYER_0_DESK.copy()
    owned_ids = [u["id"] for u in all_upgrades if u["id"] in game.get("owned", [])]
    for new, old in config.UPGRADE_REPLACEMENT.items():
        if new in owned_ids and old in owned_ids:
            owned_ids.remove(old)
    owned_ids.sort(
        key=lambda uid: (
            config.DESK_ORDER.index(uid) if uid in config.DESK_ORDER else 999
        )
    )
    owned_arts = [UPGRADE_ART[uid] for uid in owned_ids if uid in UPGRADE_ART]
    empty_indices = [
        i
        for i, line in enumerate(table)
        if line.startswith("       ║") and line.endswith("║")
    ]
    empty_idx_iter = reversed(empty_indices)
    for art in owned_arts:
        art_height = len(art)
        try:
            art_positions = [next(empty_idx_iter) for _ in range(art_height)]
        except StopIteration:
            break
        for line_pos, art_line in zip(reversed(art_positions), art):
            table[line_pos] = "       ║" + art_line.center(23) + "║"
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
            cup_center = 9 + (first_char_idx + last_char_idx) // 2
            new_steam = []
            for x, y, stage, life in steam:
                y -= config.STEAM_SPEED
                life -= 1
                if life > 0 and y >= 0:
                    stage_idx = min(
                        len(config.STEAM_CHARS) - 1, (config.STEAM_LIFETIME - life) // 3
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
        game["focus"] = min(
            config.FOCUS_MAX, game.get("focus", 0) + config.FOCUS_CHARGE_PER_EARN
        )
    if game.get("motivation_unlocked", False):
        game["motivation"] = max(
            0, game.get("motivation", 0) - config.MOTIVATION_DRAIN_PER_WORK
        )
    if "coffee" in game.get("owned", []):
        game["caffeine_points"] = (
            game.get("caffeine_points", 0.0) + eff_delay * config.CAFFEINE_POINT_RATE
        )
    if not manual:
        work_timer = max(0.0, work_timer - eff_delay)
    save_game()


def work_tick():
    global last_tick_time, work_timer
    now = time.time()
    delta = now - last_tick_time
    last_tick_time = now
    gain, eff_delay = compute_gain_and_delay()
    if game.get("auto_work_unlocked", False):
        work_timer += delta
        if work_timer >= eff_delay:
            perform_work(gain, eff_delay, manual=False)

    game["charge"] += delta
    game["best_charge"] = max(game["best_charge"], game["charge"])
    check_charge_thresholds()


def check_charge_thresholds():
    earned = game.setdefault("charge_threshold", [])
    total = game.get("best_charge", 0)
    for t in config.CHARGE_THRESHOLDS:
        req = t["amount"]
        if req not in earned and total >= req:
            earned.append(req)
            if t["reward_type"] == "xmult":
                game["money_mult"] *= t["reward_value"]
            elif t["reward_type"] == "-cd":
                game["work_delay_multiplier"] *= t["reward_value"]


def get_charge_bonus():
    charge = game.get("charge", 0)
    scale = 1.5 ** (math.log10(charge+0.1))
    return scale

def activate_focus():
    global focus_active_until
    if not game.get("focus_unlocked", False):
        return False, "Focus not unlocked."
    if game.get("focus", 0) < 10:
        return False, "Not enough focus charge."
    game["focus"] = 0
    focus_active_until = time.time() + config.FOCUS_DURATION
    save_game()
    return True, f"Focus active for {config.FOCUS_DURATION}s."


def open_upgrade_menu():
    global KEY_PRESSED
    while True:
        unlocked = get_unlocked_upgrades()
        lines = ["--- UPGRADE BAY ---"]
        for i, u in enumerate(unlocked, start=1):
            level = game.get("upgrade_levels", {}).get(u["id"], 0)
            owned_flag = (u["id"] in game.get("owned", [])) or (level > 0)
            typ = u.get("type", "mult")
            if typ == "mult":
                base = float(u.get("base_value", u.get("value", 1)))
                val_mult = float(u.get("value_mult", 1))
                effective = base * (val_mult ** max(0, (level) - 1))
                val_display = f"x{format_number(effective)}"
            elif typ == "add":
                base = float(u.get("base_value", u.get("value", 1)))
                effective = base * (level + 1)
                if level < u.get("max_level"):
                    val_display = f"+{format_number(effective)}"
                else:
                    max_effective = base * level
                    val_display = f"+{format_number(max_effective)}"
            elif typ == "reduce_delay":
                base = float(u.get("base_value", u.get("value", 1)))
                val_mult = float(u.get("value_mult", 1))
                effective = base * (val_mult**level)
                val_display = f"/{format_number(effective)}"
            else:
                val_display = ""
            cost = int(u.get("cost", 0) * (u.get("cost_mult", 1) ** level))
            lines.append(
                f"{i}. {u['name']} (Lv {level}/{u.get('max_level', 1)}) - Cost: ${format_number(cost)} {'(owned)' if owned_flag else ''} [{val_display}]"
            )
        lines += ["", "Press number to buy, B to back."]
        box = boxed_lines(lines, title=" UPGRADE BAY ", pad_top=1, pad_bottom=1)
        clear_screen()
        print("\n".join(box))
        while True:
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
                        break


def apply_single_upgrade_effect(upg, level):
    if upg.get("type") == "unlock_focus" and level > 0:
        game["focus_unlocked"] = True
    elif upg.get("type") == "unlock_charge" and level > 0:
        game["charge_unlocked"] = True


def buy_idx_upgrade(upg):
    uid = upg["id"]
    upg["base_value"] = float(upg.get("base_value", 1))
    upg["value_mult"] = float(upg.get("value_mult", 1))
    upg["cost_mult"] = float(upg.get("cost_mult", 1))
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
        apply_single_upgrade_effect(upg, current_level)
        msg = f"Purchased {upg['name']} Lv {current_level}/{max_level}!"
        save_game()
    clear_screen()
    tmp = boxed_lines([msg], title=" Upgrade ", pad_top=1, pad_bottom=1)
    print("\n".join(tmp))
    time.sleep(1.2)


def get_unlocked_upgrades():
    unlocked = []
    levels = game.get("upgrade_levels", {})
    owned = game.get("owned", [])

    def is_unlocked(upg_id):
        deps = config.UPGRADE_DEPENDENCIES.get(upg_id, [])
        for dep in deps:
            if dep == "auto_work":
                if not game.get("auto_work_unlocked", False):
                    return False
            elif levels.get(dep, 0) < 1 and dep not in owned:
                return False
        return True

    for upg in all_upgrades:
        if is_unlocked(upg["id"]):
            unlocked.append(upg)
    return unlocked


def get_inspire_cost(upg, current_level=0):
    return int(
        upg.get("base_cost", upg.get("cost", 0))
        * (upg.get("cost_mult", 1) ** current_level)
    )


def buy_inspiration_upgrade_by_index(idx):
    upgrades = INSPIRE_UPGRADES
    if not (0 <= idx < len(upgrades)):
        return
    upg = upgrades[idx]
    owned, level = get_inspire_info(upg["id"])
    max_level = upg.get("max_level", 1)
    if level >= max_level:
        msg = f"{upg['name']} is already at max level!"
        tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
        clear_screen()
        print("\n".join(tmp))
        time.sleep(1.0)
        return
    cost = get_inspire_cost(upg, current_level=level)
    if game.get("inspiration", 0) < cost:
        msg = f"Not enough Inspiration for {upg['name']} (cost {cost})!"
        tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
        clear_screen()
        print("\n".join(tmp))
        time.sleep(1.0)
        return
    game["inspiration"] -= cost
    applied = False
    for i, u in enumerate(game.get("inspiration_upgrades", [])):
        if isinstance(u, dict) and u.get("id") == upg["id"]:
            u["level"] = u.get("level", 1) + 1
            applied = True
            break
        elif isinstance(u, str) and u == upg["id"]:
            game["inspiration_upgrades"][i] = {"id": u, "level": 2}
            applied = True
            break
    if not applied:
        game.setdefault("inspiration_upgrades", []).append(
            {"id": upg["id"], "level": 1}
        )
    check_inspiration_milestones()
    save_game()
    msg = f"Purchased {upg['name']} level {level + 1}!"
    tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
    clear_screen()
    print("\n".join(tmp))
    time.sleep(0.7)


def reset_for_inspiration():
    if game.get("money", 0) < 1000:
        tmp = boxed_lines(
            ["Not enough money to reset for Inspiration."],
            title=" Inspire ",
            pad_top=1,
            pad_bottom=1,
        )
        clear_screen()
        print("\n".join(tmp))
        time.sleep(1.2)
        return
    gained = calculate_inspiration(game.get("money_since_reset", 0))
    play_inspiration_reset_animation()
    total_inspiration(1)
    game["inspiration"] = game.get("inspiration", 0) + gained
    check_inspiration_milestones()
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
        game.update({"motivation": config.MOTIVATION_MAX})
    save_game()
    done_msg = boxed_lines(
        [f"You wake from a strange dream... Gained {gained} Inspiration!"],
        title=" Inspiration Gained ",
        pad_top=1,
        pad_bottom=1,
    )
    clear_screen()
    print("\n".join(done_msg))
    time.sleep(1.5)


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


def key_listener():
    global KEY_PRESSED, running
    if msvcrt is not None and os.name == "nt":
        while running:
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
                r, _, _ = select.select([sys.stdin], [], [], 0)
                if r:
                    ch = sys.stdin.read(1)
                    if ch:
                        KEY_PRESSED = ch.lower()
                time.sleep(0.02)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

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
        u = next((x for x in config.INSPIRE_UPGRADES if x["id"] == upg_id), None)
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

def predict_next_point():
    current_money = game.get("money_since_reset", 0)
    current_insp = calculate_inspiration(current_money)
    next_insp = current_insp + 1
    target_money = ((next_insp - 1) * 25) ** (1 / 0.4)
    remaining = round(max(target_money - current_money, 0), 2)
    return remaining


def main_loop():
    global KEY_PRESSED, running, work_timer, last_tick_time
    load_game()
    convert_old_upgrades()
    apply_upgrade_effects()
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
                k = KEY_PRESSED.lower()
                KEY_PRESSED = None
                if k == "q":
                    running = False
                    break
                elif k == "w":
                    gain, eff_delay = compute_gain_and_delay()
                    if not game.get("auto_work_unlocked", False):
                        work_timer = 0
                    perform_work(gain, eff_delay, manual=True)
                elif k == "u":
                    open_upgrade_menu()
                    current_screen = "work"
                    clear_screen()
                    render_ui(screen=current_screen)
                elif k == "f":
                    ok, msg = activate_focus()
                    tmp = boxed_lines([msg], title=" Focus ", pad_top=1, pad_bottom=1)
                    clear_screen()
                    print("\n".join(tmp))
                    time.sleep(1.0)
                elif k == "i":
                    reset_for_inspiration()
                    current_screen = "work"
                elif k == "\x1b[A":  # up
                    view_offset_y = max(view_offset_y - 1, 0)
                elif k == "\x1b[B":  # down
                    view_offset_y += 1
                elif k == "\x1b[C":  # right
                    view_offset_x += 2
                elif k == "\x1b[D":  # left
                    view_offset_x = max(view_offset_x - 2, 0)
                elif (
                    current_screen == "work"
                    and k == "1"
                    and game.get("inspiration_unlocked", False)
                ):
                    current_screen = "inspiration"
                elif current_screen == "inspiration":
                    if k == "b":
                        current_screen = "work"
                    elif k.isdigit():
                        idx = int(k) - 1
                        buy_inspiration_upgrade_by_index(idx)
                        render_ui(screen="inspiration")
                        time.sleep(0.3)
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
