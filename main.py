# main.py (cleaned and merged)
import json, os, time, sys, threading, shutil
import math
import select
import random
import textwrap

# Cross-platform modules
try:
    import msvcrt  # Windows-only
except Exception:
    msvcrt = None

from ascii_art import (
    LAYER_0_DESK,
    LAYER_1_UPGRADE,
    LAYER_2_INSPIRATION,
    LAYER_FOCUS_MODE,
    UPGRADE_ART,
)

import config
from config import INSPIRE_UPGRADES, format_number, INSPIRATION_MILESTONES

# Save file path
SAVE_PATH = "data/save.json"
if not os.path.exists("data"):
    os.makedirs("data")

last_tick_time = time.time()
last_render = ""
last_size = (0, 0)

# -----------------------------
# Game state (persistent)
# -----------------------------
game = {
    "layer": 0,
    "money": 0.0,
    "fatigue": 0,
    "focus": 0,  # 0..100 focus charge
    "inspiration": 0,
    "owned": [],  # list of upgrade ids purchased
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
}

# runtime variables
work_timer = 0.0
KEY_PRESSED = None
running = True
focus_active_until = 0.0  # timestamp when focus effect ends

# coffee art
steam = []

# copy upgrades (so config.UPGRADES not mutated)
all_upgrades = [u.copy() for u in config.UPGRADES]

money_since_reset = game.get("money_since_reset", game.get("money", 0))
layer = game.get("layer", 0)


# -----------------------------
# Persistence
# -----------------------------
def load_game():
    global game
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    game.update(data)
        except Exception:
            print("Warning: save file corrupted, starting with defaults.")
    # Defaults
    fields_defaults = {
        "owned": [],
        "focus_unlocked": False,
        "inspiration_unlocked": False,
        "inspiration_upgrades": [],
        "work_delay_multiplier": 1.0,
        "money_mult": 1.0,
        "focus_max_bonus": 0,
        "base_work_delay": config.BASE_WORK_DELAY,
        "base_money_gain": config.BASE_MONEY_GAIN,
        "auto_work_unlocked": False,
        "motivation_unlocked": False,
        "total_inspirations": 0,
        "milestones_earned": [],
        "caffeine_points": 0.0,
        "upgrade_levels": {},
    }
    for k, v in fields_defaults.items():
        game.setdefault(k, v)

    # Derived unlocks from inspiration upgrades (legacy/modern)
    owned, _ = get_inspire_info("inspire_auto_work")
    if owned:
        game["auto_work_unlocked"] = True
    owned, _ = get_inspire_info("inspire_motiv")
    if owned:
        game["motivation_unlocked"] = True


def save_game():
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(game, f)
    except Exception as e:
        print("Warning: failed to save:", e)


# -----------------------------
# Helpers
# -----------------------------
def get_term_size():
    """Return (columns, rows) of terminal."""
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        return (size.columns, size.lines)
    except Exception:
        return (80, 24)


def convert_old_upgrades():
    """Convert old string-format inspiration upgrades to dicts with a level."""
    new_list = []
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, str):
            new_list.append({"id": u, "level": 1})
        elif isinstance(u, dict):
            new_list.append(u)
    game["inspiration_upgrades"] = new_list


def get_inspire_info(upg_id):
    """Return (owned: bool, level: int) for a given inspiration upgrade id."""
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return True, u.get("level", 1)
        elif isinstance(u, str) and u == upg_id:
            return True, 1
    return False, 0


def wrap_ui_text(text, panel_width_ratio=0.25):
    """Wrap text to fit left panel dynamically."""
    term_w, _ = get_term_size()
    panel_width = int(term_w * panel_width_ratio) - 4  # some padding
    return textwrap.wrap(text, width=panel_width)


def apply_upgrade_effects():
    """Reapply non-numeric immediate effects for saved upgrades on load."""
    game.setdefault("upgrade_levels", {})
    for upg in config.UPGRADES:
        uid = upg["id"]
        level = game["upgrade_levels"].get(uid, 0)
        if level > 0:
            apply_single_upgrade_effect(upg, level)


def total_inspiration(amount=1):
    game["total_inspirations"] = game.get("total_inspirations", 0) + amount
    check_inspiration_milestones()


def check_inspiration_milestones():
    total = game.get("total_inspirations", 0)
    earned = game.setdefault("milestones_earned", [])
    for milestone in INSPIRATION_MILESTONES:
        req = milestone["inspirations_required"]
        if req not in earned and total >= req:
            earned.append(req)
            apply_milestone_reward(milestone)
    save_game()


def apply_milestone_reward(milestone):
    reward_type = milestone["reward_type"]
    reward_value = milestone["reward_value"]
    if reward_type == "xmult":
        game["money_mult"] *= reward_value
    elif reward_type == "+mult":
        game["money_mult"] += reward_value
    elif reward_type == "-cd":
        game["work_delay_multiplier"] *= reward_value


def render_milestones_lines():
    """Return milestone lines for UI."""
    lines = []
    total_insp = game.get("total_inspirations", 0)
    earned = set(game.get("milestones_earned", []))
    lines.append("=== MILESTONES ===")
    for m in config.INSPIRATION_MILESTONES:
        req = m.get("inspirations_required", 0)
        rtype = m.get("reward_type", "")
        rval = m.get("reward_value", "")
        unlocked = req in earned or total_insp >= req
        status = "✓" if unlocked else "✗"
        if rtype == "xmult":
            reward_desc = f"x${rval}"
        elif rtype in ("+mult",):
            reward_desc = f"+${rval}"
        elif rtype in ("-cd", "reduce_cd"):
            reward_desc = f"/{rval} work delay"
        else:
            reward_desc = str(rtype) + " " + str(rval)
        lines.append(f"{status} {req} i → {reward_desc}")
    return lines


# -----------------------------
# Compute gain and delay
# -----------------------------
def compute_gain_and_delay():
    base_gain = game.get("base_money_gain", config.BASE_MONEY_GAIN)
    base_delay = game.get("base_work_delay", config.BASE_WORK_DELAY)

    gain_add = 0.0
    gain_mult = 1.0
    delay_mult = game.get("work_delay_multiplier", 1.0)

    # Normal upgrades
    lvl_map = game.get("upgrade_levels", {})
    for u in all_upgrades:
        uid = u["id"]
        level = int(lvl_map.get(uid, 0))
        if level <= 0:
            continue

        typ = u.get("type", "mult")
        if typ == "add":
            base_val = float(u.get("base_value", u.get("value", 0)))
            gain_add += base_val * level
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

    # Inspiration upgrades
    applied_ids = set()
    for entry in game.get("inspiration_upgrades", []):
        if isinstance(entry, dict):
            upg_id = entry.get("id")
            level = entry.get("level", 1)
        else:
            upg_id = entry
            level = 1

        if upg_id in applied_ids:
            continue
        applied_ids.add(upg_id)

        u = next((x for x in config.INSPIRE_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue

        base = float(u.get("base_value", u.get("value", 1)))
        val_mult = float(u.get("value_mult", 1))
        total_value = base * (val_mult ** max(0, (level - 1)))
        if u["type"] == "money_mult":
            gain_mult *= total_value
        elif u["type"] == "work_mult":
            delay_mult *= total_value
        elif u["type"] == "focus_max":
            game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + total_value
        elif u["type"] == "unlock_motivation":
            game["motivation_unlocked"] = True
            game["motivation"] = config.MOTIVATION_MAX
        elif u["type"] == "auto_work":
            game["auto_work_unlocked"] = True

    # Focus bonus
    eff_gain = (base_gain + gain_add) * gain_mult
    eff_delay = base_delay * delay_mult
    if time.time() < focus_active_until:
        eff_delay *= config.FOCUS_BOOST_FACTOR

    # Motivation multiplier
    motivation = game.get("motivation", config.MOTIVATION_MAX)
    motivation_mult = 1 + (motivation / config.MOTIVATION_MAX) * (
        config.MAX_MOTIVATION_MULT - 1
    )
    eff_gain *= motivation_mult

    # Global money multiplier
    eff_gain *= game.get("money_mult", 1.0)

    # Safety cap
    eff_delay = max(eff_delay, 0.01)
    return eff_gain, eff_delay


# -----------------------------
# Terminal UI utilities
# -----------------------------
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

    # Top border
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
        segments = []
        if len(raw) <= inner_w:
            segments.append(raw)
        else:
            words = raw.split(" ")
            cur = ""
            for w in words:
                if cur == "":
                    cur = w
                elif len(cur) + 1 + len(w) <= inner_w:
                    cur += " " + w
                else:
                    segments.append(cur)
                    cur = w
            if cur:
                while len(cur) > inner_w:
                    segments.append(cur[:inner_w])
                    cur = cur[inner_w:]
                if cur:
                    segments.append(cur)
        for seg in segments:
            lines.append(v + seg.center(inner_w) + v)

    for _ in range(pad_bottom):
        lines.append(v + " " * inner_w + v)

    lines.append(bl + h * inner_w + br)
    left_margin = max(0, (term_w - box_w) // 2)
    margin_str = " " * left_margin
    return [margin_str + l for l in lines]


# -----------------------------
# Render UI
# -----------------------------
def render_ui(screen="work"):
    global last_render, last_size

    # detect resizing
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

    # Left panel (~25%)
    calc_insp = calculate_inspiration(money_since_reset)
    time_next = predict_next_point()

    top_left_lines = []
    if game.get("inspiration_unlocked", False):
        if screen == "work":
            top_left_lines.append("=== INSPIRATION ===")
            top_left_lines.append(
                f"Points: {format_number(game.get('inspiration', 0))} i"
            )
            top_left_lines.append("")
            top_left_lines.append("[1] Open Inspiration Tree")
            top_left_lines.append("")
            if game.get("money", 0) >= 1000:
                top_left_lines.append(
                    f"[I]nspire for {format_number(calc_insp)} Inspiration"
                )
                top_left_lines.append(f"{format_number(time_next)} until next point")
        elif screen == "inspiration":
            top_left_lines.append("=== INSPIRATION TREE ===")
            top_left_lines.append(
                f"Points: {format_number(game.get('inspiration', 0))} i"
            )
            top_left_lines.append("")
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
                    if level > 0 and u["type"] != "unlock_motivation":
                        desc_text += f" (x{total_mult:.2f})"
                    elif u["type"] == "unlock_motivation":
                        motiv = game.get("motivation", config.MOTIVATION_MAX)
                        motiv_mult = 1 + round(
                            (
                                (motiv / config.MOTIVATION_MAX)
                                * (config.MAX_MOTIVATION_MULT - 1)
                            ),
                            2,
                        )
                        desc_text += f" (x{motiv_mult})"
                    wrapped_desc = wrap_ui_text(desc_text)
                    top_left_lines.extend(["     " + line for line in wrapped_desc])
            top_left_lines.append("")
            top_left_lines.append("[B] Back to Work")
    elif 100000 > game.get("money_since_reset", 0) >= 50000:
        top_left_lines.append("       === INSPIRATION ===")
        top_left_lines.append("")
        top_left_lines.append("Reach $1000 to unlock Inspiration")
    elif game.get("money_since_reset", 0) >= 100000:
        top_left_lines.append("       === INSPIRATION ===")
        top_left_lines.append("")
        desc_texts = [
            "You realise the pointlessness of this mundane work",
            "Perhaps there is more to life than work?",
            f"[I]nspire for {format_number(calc_insp)} Inspiration",
        ]
        for desc in desc_texts:
            wrapped = wrap_ui_text(desc)
            top_left_lines.extend(["   " + line for line in wrapped])
        else:
            top_left_lines.append("")

    # Bottom-left: milestones
    bottom_left_lines = []
    if game.get("inspiration_unlocked", False):
        bottom_left_lines.append("")
        bottom_left_lines.extend(render_milestones_lines())

    # Right panel (~50%)
    right_lines = []

    # Desk
    if LAYER_0_DESK:
        right_lines.extend(render_desk_table())

    # Focus bar
    if game.get("focus_unlocked", False):
        focus_max = config.FOCUS_MAX + game.get("focus_max_bonus", 0)
        fprog = min(game.get("focus", 0) / float(focus_max), 1.0)
        fbar_len = 36
        ffilled = int(fprog * fbar_len)
        right_lines.append(f"FOCUS: {int(fprog * 100):3d}%")
        right_lines.append("[" + "#" * ffilled + "-" * (fbar_len - ffilled) + "]")
        right_lines.append("")

    # Work info
    owned_motiv, _ = get_inspire_info("inspire_motiv")
    right_lines.append(
        f"MONEY: ${format_number(game.get('money', 0))}   GAIN: {format_number(effective_gain)} / cycle"
        + (
            f"   DELAY: {effective_delay:.2f}s"
            if game.get("auto_work_unlocked", False)
            else ""
        )
    )
    right_lines.append(work_bar)
    right_lines.append(
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

    # Owned upgrades
    owned_names = [u["name"] for u in all_upgrades if u["id"] in game.get("owned", [])]
    right_lines.append("")
    right_lines.append(
        "Owned Upgrades: " + (", ".join(owned_names) if owned_names else "(none)")
    )

    # Options
    options = "[W]ork  [U]pgrade  [F]ocus"
    if game.get("inspiration_unlocked", False):
        options += "  [I]nspire"
    options += "  [Q]uit"
    right_lines.append("")
    right_lines.append("Options: " + options)

    # Combine panels and pad vertically
    term_width, term_height = get_term_size()

    # Position milestones at ~50% terminal height
    top_height = len(top_left_lines)
    desired_midpoint = term_height // 2
    gap_lines = max(0, desired_midpoint - top_height)
    left_lines = top_left_lines + ([""] * gap_lines) + bottom_left_lines

    # Bottom-stick right panel
    right_content_height = len(right_lines)
    total_box_height_right = (
        right_content_height + 1 + 1 + 2
    )  # pad_top + pad_bottom + border
    empty_lines_needed_right = max(term_height - total_box_height_right, 0)
    right_lines = ([""] * empty_lines_needed_right) + right_lines

    # Equalize lengths
    max_lines = max(len(left_lines), len(right_lines))
    while len(left_lines) < max_lines:
        left_lines.append("")
    while len(right_lines) < max_lines:
        right_lines.append("")

    combined_lines = [
        l.ljust(int(term_width * 0.25)) + " " * 4 + r.ljust(int(term_width * 0.50))
        for l, r in zip(left_lines, right_lines)
    ]

    # Box and render
    box = boxed_lines(
        combined_lines, title=f" Layer {game.get('layer', 0)} ", pad_top=1, pad_bottom=1
    )
    if resized:
        print("\033[2J\033[H", end="")  # clear screen on resize
        last_size = current_size
        last_render = ""

    output = "\033[H" + "\n".join(box)
    if output != last_render:
        os.system("cls" if os.name == "nt" else "clear")
        print(output, end="", flush=True)
        last_render = output


def render_desk_table():
    global steam
    table = LAYER_0_DESK.copy()

    # Place owned items
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
            inner_width = 23
            table[line_pos] = "       ║" + art_line.center(inner_width) + "║"

    # Add coffee steam
    if "coffee" in owned_ids:
        coffee_idx = None
        for i, art_id in enumerate(owned_ids):
            if art_id == "coffee":
                coffee_idx = empty_indices[-(i + 1)]
                break

        if coffee_idx is not None:
            coffee_art = UPGRADE_ART["coffee"]
            cup_height = len(coffee_art)
            steam_start_idx = coffee_idx - (cup_height - 1)  # top line of cup
            steam_emit_idx = steam_start_idx - 2  # 2 line above cup

            # Correct horizontal center of cup
            coffee_line = coffee_art[0]
            first_char_idx = next((i for i, c in enumerate(coffee_line) if c != " "), 0)
            last_char_idx = len(coffee_line.rstrip()) - 1
            cup_center = 9 + (first_char_idx + last_char_idx) // 2  # table padding = 9

            # Move existing steam upward and advance fade
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

            # Randomly emit new puff from center
            if random.random() < config.STEAM_CHANCE:
                offset = random.randint(-config.STEAM_SPREAD, config.STEAM_SPREAD)
                steam.append(
                    (cup_center + offset, steam_emit_idx, 0, config.STEAM_LIFETIME)
                )

            # Overlay steam on table
            for x, y, stage_idx, _ in steam:
                yi = int(round(y))
                if 0 <= yi < len(table):
                    line = table[yi]
                    if 0 <= x < len(line):
                        line = line[:x] + config.STEAM_CHARS[stage_idx] + line[x + 1 :]
                        table[yi] = line

    return table


# -----------------------------
# Work cycle helpers
# -----------------------------
def perform_work(gain, eff_delay, manual=False):
    """Apply work cycle effects (manual or auto)."""
    global work_timer
    now = time.time()
    game["money"] += gain
    game["money_since_reset"] += gain

    # Focus charge
    if game.get("focus_unlocked", False) and now >= focus_active_until:
        game["focus"] = min(
            config.FOCUS_MAX,
            game.get("focus", 0) + config.FOCUS_CHARGE_PER_EARN,
        )

    # Motivation drain
    if game.get("motivation_unlocked", False):
        game["motivation"] = max(
            0, game.get("motivation", 0) - config.MOTIVATION_DRAIN_PER_WORK
        )

    # Caffeine points accumulation while auto (approximate per cycle)
    if "coffee" in game.get("owned", []):
        # add per-cycle rate scaled by delay (approximate)
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


# -----------------------------
# Focus activation
# -----------------------------
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


# -----------------------------
# Upgrade menu
# -----------------------------
def open_upgrade_menu():
    global KEY_PRESSED
    while True:
        unlocked = get_unlocked_upgrades()
        lines = ["--- UPGRADE BAY ---"]
        for i, u in enumerate(unlocked, start=1):
            level = game.get("upgrade_levels", {}).get(u["id"], 0)
            owned_flag = (u["id"] in game.get("owned", [])) or (level > 0)
            owned = "(owned)" if owned_flag else ""
            typ = u.get("type", "mult")

            # display local effect
            if typ == "mult":
                base = float(u.get("base_value", u.get("value", 1)))
                val_mult = float(u.get("value_mult", 1))
                effective = base * (val_mult ** max(0, (level - 1)))
                val_display = f"x{format_number(effective)}"
            elif typ == "add":
                base = float(u.get("base_value", u.get("value", 1)))
                effective = base * level
                val_display = f"+{format_number(effective)}"
            elif typ == "reduce_delay":
                base = float(u.get("base_value", u.get("value", 1)))
                val_mult = float(u.get("value_mult", 1))
                effective = base * (val_mult**level)
                val_display = f"/{format_number(effective)}"
            else:
                val_display = ""

            lvl = level
            cost = int(u.get("cost", 0) * (u.get("cost_mult", 1) ** lvl))
            lines.append(
                f"{i}. {u['name']} (Lv {level}/{u.get('max_level', 1)}) - Cost: ${format_number(cost)} {owned} [{typ} {val_display}]"
            )

        lines.append("")
        lines.append("Press number to buy, B to back.")
        box = boxed_lines(lines, title=" UPGRADE BAY ", pad_top=1, pad_bottom=1)
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(box))

        # wait for user input
        while True:
            time.sleep(0.05)
            if KEY_PRESSED:
                k = KEY_PRESSED.lower()
                KEY_PRESSED = None
                if k == "b":
                    return
                if k.isdigit():
                    idx = int(k) - 1
                    if 0 <= idx < len(unlocked):
                        buy_idx_upgrade(unlocked[idx])
                        break


def apply_single_upgrade_effect(upg, level):
    if upg.get("type") == "unlock_focus" and level > 0:
        game["focus_unlocked"] = True


def buy_idx_upgrade(upg):
    uid = upg["id"]

    # Ensure numeric types
    upg["base_value"] = float(upg.get("base_value", 1))
    upg["value_mult"] = float(upg.get("value_mult", 1))
    upg["cost_mult"] = float(upg.get("cost_mult", 1))

    # Ensure save fields exist
    game.setdefault("owned", [])
    game.setdefault("upgrade_levels", {})

    current_level = game["upgrade_levels"].get(uid, 0)
    max_level = upg.get("max_level", 1)
    base_cost = upg["cost"]
    cost_mult = upg.get("cost_mult", 1)
    scaled_cost = int(base_cost * (cost_mult**current_level))

    if current_level >= max_level:
        msg = f"{upg['name']} is already maxed (Lv {current_level}/{max_level})."
    elif game.get("money", 0) < scaled_cost:
        msg = f"Not enough money for {upg['name']} (cost ${scaled_cost})."
    else:
        # Purchase
        game["money"] -= scaled_cost
        current_level += 1
        game["upgrade_levels"][uid] = current_level

        # Add to owned list if not present
        if uid not in game["owned"]:
            game["owned"].append(uid)

        # Apply upgrade effect immediately
        apply_single_upgrade_effect(upg, current_level)

        msg = f"Purchased {upg['name']} Lv {current_level}/{max_level}!"
        save_game()

    os.system("cls" if os.name == "nt" else "clear")
    tmp = boxed_lines([msg], title=" Upgrade ", pad_top=1, pad_bottom=1)
    print("\n".join(tmp))
    time.sleep(1.2)


def get_unlocked_upgrades():
    unlocked = []
    for i, upg in enumerate(all_upgrades):
        if i == 0:
            unlocked.append(upg)
            continue
        prev = all_upgrades[i - 1]
        prev_owned = (prev["id"] in game.get("owned", [])) or (
            game.get("upgrade_levels", {}).get(prev["id"], 0) > 0
        )
        if prev_owned:
            unlocked.append(upg)
    return unlocked


# -----------------------------
# Inspiration (unified)
# -----------------------------
def get_inspire_cost(upg, current_level=0):
    base_cost = upg.get("base_cost", upg.get("cost", 0))
    mult = upg.get("cost_mult", 1)
    return int(base_cost * (mult**current_level))


def buy_inspiration_upgrade_by_index(idx):
    upgrades = config.INSPIRE_UPGRADES
    if not (0 <= idx < len(upgrades)):
        return
    upg = upgrades[idx]
    owned, level = get_inspire_info(upg["id"])
    max_level = upg.get("max_level", 1)

    if level >= max_level:
        msg = f"{upg['name']} is already at max level!"
        tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.0)
        return

    cost = get_inspire_cost(upg, current_level=level)
    if game.get("inspiration", 0) < cost:
        msg = f"Not enough Inspiration for {upg['name']} (cost {cost})!"
        tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.0)
        return

    # Deduct
    game["inspiration"] -= cost

    # Apply or add
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

    save_game()
    msg = f"Purchased {upg['name']} level {level + 1}!"
    tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(tmp))
    time.sleep(0.7)


def reset_for_inspiration():
    # check minimum money requirement
    if game.get("money", 0) < 1000:
        tmp = boxed_lines(
            ["Not enough money to reset for Inspiration."],
            title=" Inspire ",
            pad_top=1,
            pad_bottom=1,
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)
        return

    # calculate gained inspiration
    gained = calculate_inspiration(game.get("money_since_reset", 0))

    play_inspiration_reset_animation()

    total_inspiration(1)
    game["inspiration"] = game.get("inspiration", 0) + gained

    # apply reset
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
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(done_msg))
    time.sleep(1.5)


def play_inspiration_reset_animation():
    """Plays a dynamic comic-style floating Z animation (~3s)."""
    term_w, term_h = shutil.get_terminal_size(fallback=(80, 24))

    num_zs = 5  # max Zs on screen
    frames = 15
    z_lifetime = 6  # frames each Z lasts
    zs = []

    for frame in range(frames):
        os.system("cls" if os.name == "nt" else "clear")
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

    os.system("cls" if os.name == "nt" else "clear")
    print("\n" * (term_h // 2))
    print("!".center(term_w))
    time.sleep(0.6)


# -----------------------------
# Key listener
# -----------------------------
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


# -----------------------------
# Reset math
# -----------------------------
def calculate_inspiration(money_since_reset):
    # using current game value to keep consistent
    money_since_reset = game.get("money_since_reset", 0)
    return math.floor(((money_since_reset**0.4) / 25) + 1)


def predict_next_point():
    current_money = game.get("money_since_reset", 0)
    current_insp = calculate_inspiration(current_money)
    next_insp = current_insp + 1
    target_money = ((next_insp - 1) * 25) ** (1 / 0.4)
    remaining = round(max(target_money - current_money, 0), 2)
    return remaining


# -----------------------------
# Main loop
# -----------------------------
def main_loop():
    global KEY_PRESSED, running, work_timer, last_tick_time
    load_game()
    convert_old_upgrades()
    apply_upgrade_effects()

    last_tick_time = time.time()

    listener = threading.Thread(target=key_listener, daemon=True)
    listener.start()

    if game.get("layer", 0) >= 1 and not game.get("inspiration_unlocked", False):
        game["inspiration_unlocked"] = True
        game["layer"] = 1
        save_game()

    current_screen = "work"

    try:
        while running:
            # Auto-work tick
            work_tick()

            # Render UI
            render_ui(screen=current_screen)

            # Handle input non-blocking
            if KEY_PRESSED:
                k = KEY_PRESSED.lower()
                KEY_PRESSED = None

                # Quit
                if k == "q":
                    running = False
                    break

                # Work (manual)
                elif k == "w":
                    gain, eff_delay = compute_gain_and_delay()
                    # Manual work is instant; reset bar if auto not enabled
                    if not game.get("auto_work_unlocked", False):
                        work_timer = 0
                    perform_work(gain, eff_delay, manual=True)

                # Upgrade menu
                elif k == "u":
                    open_upgrade_menu()
                    current_screen = "work"

                # Focus
                elif k == "f":
                    ok, msg = activate_focus()
                    tmp = boxed_lines([msg], title=" Focus ", pad_top=1, pad_bottom=1)
                    os.system("cls" if os.name == "nt" else "clear")
                    print("\n".join(tmp))
                    time.sleep(1.0)

                # Inspiration reset
                elif k == "i":
                    reset_for_inspiration()
                    current_screen = "work"

                # Screen-specific
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
        os.system("cls" if os.name == "nt" else "clear")
        print("Saved. Bye!")


# -----------------------------
# Entry
# -----------------------------
if __name__ == "__main__":
    main_loop()
