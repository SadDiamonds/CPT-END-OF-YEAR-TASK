# main.py
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

from config import INSPIRE_UPGRADES, format_number

# Save file path
SAVE_PATH = "data/save.json"
if not os.path.exists("data"):
    os.makedirs("data")

last_tick_time = time.time()

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
}

# runtime variables
work_timer = 0.0
KEY_PRESSED = None
running = True
focus_active_until = 0.0  # timestamp when focus effect ends

# coffee art cuz why not
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
    game.setdefault("owned", [])
    game.setdefault("focus_unlocked", False)
    game.setdefault("inspiration_unlocked", False)
    game.setdefault("inspiration_upgrades", [])
    game.setdefault("work_delay_multiplier", 1.0)
    game.setdefault("money_mult", 1.0)
    game.setdefault("focus_max_bonus", 0)
    game.setdefault("base_work_delay", config.BASE_WORK_DELAY)
    game.setdefault("base_money_gain", config.BASE_MONEY_GAIN)
    game.setdefault("auto_work_unlocked", False)
    game.setdefault("motivation_unlocked", False)

    if "inspire_auto_work" in game.get("inspiration_upgrades", []):
        game["auto_work_unlocked"] = True
    if "inspire_motiv" in game.get("inspiration_upgrades", []):
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
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def get_upgrade_level(upg_id):
    for u in game.get("inspiration_upgrades", []):
        # make sure u is a dict with "id"
        if isinstance(u, dict) and u.get("id") == upg_id:
            return u.get("level", 0)
    return 0


def is_inspire_owned(upg_id):
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, str):
            if u == upg_id:
                return True
        elif isinstance(u, dict):
            if u.get("id") == upg_id:
                return True
    return False


def get_inspire_level(upg_id):
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return u.get("level", 1)
        elif isinstance(u, str) and u == upg_id:
            return 1  # old format, level 1
    return 0

def has_inspire_upgrade(upg_id):
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, dict) and u.get("id") == upg_id:
            return True
        elif isinstance(u, str) and u == upg_id:  # old format support
            return True
    return False

def convert_old_upgrades():
    """Convert old string-format inspiration upgrades to dicts with a level."""
    new_list = []
    for u in game.get("inspiration_upgrades", []):
        if isinstance(u, str):
            # Convert to dict, level 1
            new_list.append({"id": u, "level": 1})
        elif isinstance(u, dict):
            new_list.append(u)
    game["inspiration_upgrades"] = new_list


def wrap_ui_text(text, panel_width_ratio=0.25):
    """Wrap text to fit left panel (or other panel) dynamically."""
    term_w, _ = get_term_size()
    panel_width = int(term_w * panel_width_ratio) - 4  # some padding
    return textwrap.wrap(text, width=panel_width)
# -----------------------------
# Compute gain and delay and math stuff
# -----------------------------
def compute_gain_and_delay():
    """Return (effective_gain, effective_delay) after all upgrades"""
    base_gain = game.get("base_money_gain", config.BASE_MONEY_GAIN)
    base_delay = game.get("base_work_delay", config.BASE_WORK_DELAY)

    gain_add = 0
    gain_mult = 1.0
    delay_mult = 1.0

    # Normal upgrades
    for u in all_upgrades:
        if u["id"] in game.get("owned", []):
            if u["type"] == "add":
                gain_add += u.get("value", 0)
            elif u["type"] == "mult":
                gain_mult *= u.get("value", 1)
            elif u["type"] == "reduce_delay":
                delay_mult *= u.get("value", 1)
            elif u["type"] == "unlock_focus":
                game["focus_unlocked"] = True

    # Inspiration upgrades
    for entry in game.get("inspiration_upgrades", []):
        # Handle both old saves (string) and new saves (dict)
        if isinstance(entry, dict):
            upg_id = entry.get("id")
            level = entry.get("level", 1)
        else:
            upg_id = entry
            level = 1

        # Find the upgrade definition
        u = next((x for x in config.INSPIRE_UPGRADES if x["id"] == upg_id), None)
        if not u:
            continue

        # Apply effects according to type
        if u["type"] == "money_mult":
            base_value = u.get("base_value", u.get("value", 1))
            value_mult = u.get("value_mult", 1.0)
            total_value = base_value * (value_mult ** (level - 1))
            gain_mult *= total_value

        elif u["type"] == "work_mult":
            base_value = u.get("base_value", u.get("value", 1))
            value_mult = u.get("value_mult", 1.0)
            total_value = base_value * (value_mult ** (level - 1))
            delay_mult *= total_value

        elif u["type"] == "focus_max":
            base_value = u.get("base_value", u.get("value", 0))
            value_mult = u.get("value_mult", 1.0)
            total_value = base_value * (value_mult ** (level - 1))
            game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + total_value

    eff_gain = (base_gain + gain_add) * gain_mult
    eff_delay = base_delay * delay_mult

    if time.time() < focus_active_until:
        eff_delay *= config.FOCUS_BOOST_FACTOR

    motivation = game.get("motivation", config.MOTIVATION_MAX)
    # Scale from 1 → MAX_MOTIVATION_MULT
    motivation_mult = 1 + (motivation / config.MOTIVATION_MAX) * (config.MAX_MOTIVATION_MULT - 1)
    eff_gain = ((base_gain + gain_add) * gain_mult) * motivation_mult

    return eff_gain, eff_delay


# -----------------------------
# Terminal utilities
# -----------------------------
def get_term_size():
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        return size.columns, size.lines
    except Exception:
        return 80, 24


def boxed_lines(
    content_lines, title=None, pad_top=1, pad_bottom=1, margin=config.BOX_MARGIN
):
    term_w, term_h = get_term_size()
    box_w = max(config.MIN_BOX_WIDTH, term_w - margin * 2)
    inner_w = box_w - 2

    # Pick border style based on layer
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
    clear_screen()
    effective_gain, effective_delay = compute_gain_and_delay()
    prog = (
        min(work_timer / effective_delay, 1.0)
        if game.get("auto_work_unlocked", False)
        else 0
    )

    bar_len = 36
    filled = int(prog * bar_len)
    work_bar = (
        "[" + "#" * filled + "-" * (bar_len - filled) + "] " + f"{int(prog*100):3d}%"
    )

    # -----------------------------
    # Left panel (~25%)
    # -----------------------------
    calc_insp = calculate_inspiration(money_since_reset)
    time_next = predict_next_point()
    left_lines = []

    if game.get("inspiration_unlocked", False):
        if screen == "work":
            left_lines.append("=== INSPIRATION ===")
            left_lines.append(f"Points: {game.get('inspiration', 0)}")
            left_lines.append("")
            left_lines.append("[1] Open Inspiration Tree")
            left_lines.append("")

            if game.get("money", 0) >= 1000:
                insp_msg = (
                    f"You realise all your work is for naught, "
                    f"and you decide to leave behind everything "
                    f"for {'an' if calc_insp==1 else str(calc_insp)} Inspiration."
                )
                wrapped_lines = wrap_ui_text(insp_msg)
                left_lines.extend(wrapped_lines)
                left_lines.append("")
                left_lines.append(
                    f"[I]nspire for {format_number(calc_insp)} Inspiration"
                )
                left_lines.append("")
                left_lines.append(f"{format_number(time_next)} until next point")
        elif screen == "inspiration":
            left_lines.append("=== INSPIRATION TREE ===")
            left_lines.append(f"Points: {game.get('inspiration', 0)}")
            left_lines.append("")

            for i, u in enumerate(INSPIRE_UPGRADES, start=1):
                level = get_inspire_level(u["id"])
                cost = get_inspire_cost(u, current_level=level)

                base_value = u.get("base_value", 1.0)
                value_mult = u.get("value_mult", 1.0)
                total_mult = (
                    base_value * (value_mult ** (level - 1))
                    if level > 0
                    else base_value
                )

                owned = (
                    "(MAX)"
                    if level == u.get("max_level", 1)
                    else f"(lvl {level}/{u.get('max_level', '?')})" if level > 1 else ""
                )
                left_lines.append(
                    f"{i}. {u['name']} {owned}"
                    + (
                        f" - Cost: {format_number(cost)}"
                        if level < u.get("max_level", 1)
                        else ""
                    )
                )

                if u.get("desc"):
                    desc_text = f"→ {u['desc']}"
                    if level > 0 and not u["id"] == "inspire_motiv":
                        desc_text += f" (x{total_mult:.2f})"
                    elif u["id"] == "inspire_motiv":
                        desc_text += f" (x{1 + round(((game.get("motivation", config.MOTIVATION_MAX) / config.MOTIVATION_MAX) * (config.MAX_MOTIVATION_MULT - 1)),2)})"
                    wrapped_desc = wrap_ui_text(desc_text)
                    left_lines.extend(["     " + line for line in wrapped_desc])

            left_lines.append("")
            left_lines.append("[B] Back to Work")

    else:
        if game.get("money", 0) >= 1000:
            insp_msg = (
                f"You realise all your work is for naught, "
                f"and you decide to leave behind everything "
                f"for {'an' if calc_insp==1 else str(calc_insp)} Inspiration."
            )
            wrapped_lines = wrap_ui_text(insp_msg)
            left_lines.extend(wrapped_lines)
            left_lines.append("")
            left_lines.append(f"[I]nspire for {calc_insp} Inspiration")
        else:
            left_lines.append("Reach $1000 to unlock Inspiration")

    # -----------------------------
    # Right panel (~50%)
    # -----------------------------
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
        right_lines.append(f"FOCUS: {int(fprog*100):3d}%")
        right_lines.append("[" + "#" * ffilled + "-" * (fbar_len - ffilled) + "]")
        right_lines.append("")

    # Work info
    right_lines.append(
        f"MONEY: ${format_number(game.get('money',0))}   GAIN: {format_number(effective_gain)} / cycle   DELAY: {effective_delay:.2f}s"
    )
    right_lines.append(work_bar)
    right_lines.append(
        ("Auto-work: ENABLED" if is_auto_work_unlocked() else "Press W to work")
        + (
            f"   Motivation: {int((game.get('motivation', config.MOTIVATION_MAX)/config.MOTIVATION_MAX)*100)}%"
            if has_inspire_upgrade("inspire_motiv")
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

    # -----------------------------
    # Combine columns
    # -----------------------------
    max_lines = max(len(left_lines), len(right_lines))
    for _ in range(len(left_lines), max_lines):
        left_lines.append("")
    for _ in range(len(right_lines), max_lines):
        right_lines.append("")

    left_w = int(get_term_size()[0] * 0.25)
    right_w = int(get_term_size()[0] * 0.50)
    spacing = 4

    combined_lines = [
        l.ljust(left_w) + " " * spacing + r.ljust(right_w)
        for l, r in zip(left_lines, right_lines)
    ]

    # -----------------------------
    # Box and render
    # -----------------------------
    box = boxed_lines(
        combined_lines,
        title=f" ESCAPE — Layer {game.get('layer',0)} ",
        pad_top=1,
        pad_bottom=1,
    )
    print("\033[H" + "\n".join(box), end="", flush=True)


def render_desk_table():
    global steam
    table = LAYER_0_DESK.copy()

    # --- Place owned items ---
    owned_ids = [u["id"] for u in all_upgrades if u["id"] in game.get("owned", [])]
    owned_arts = [UPGRADE_ART[uid] for uid in owned_ids if uid in UPGRADE_ART]

    empty_indices = [
        i for i, line in enumerate(table) if line.strip() == "║                       ║"
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

    # --- Add coffee steam ---
    if "coffee" in owned_ids:
        # find bottom index of coffee
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
                    stage_idx = min(len(config.STEAM_CHARS) - 1, (config.STEAM_LIFETIME - life) // 3)
                    new_steam.append((x, y, stage_idx, life))
            steam = new_steam

            # Randomly emit new puff from center
            if random.random() < config.STEAM_CHANCE:
                offset = random.randint(-config.STEAM_SPREAD, config.STEAM_SPREAD)
                steam.append((cup_center + offset, steam_emit_idx, 0, config.STEAM_LIFETIME))

            # Overlay steam on table
            for x, y, stage_idx, _ in steam:
                yi = int(round(y))
                if 0 <= yi < len(table):
                    line = table[yi]
                    if 0 <= x < len(line):
                        line = line[:x] + config.STEAM_CHARS[stage_idx] + line[x + 1:]
                        table[yi] = line

    return table
# -----------------------------
# Work tick
# -----------------------------
def work_tick():
    global last_tick_time
    # Work tick — only runs if auto-work is unlocked
    now = time.time()
    delta = now - last_tick_time
    last_tick_time = now

    gain, eff_delay = compute_gain_and_delay()
    focus_active = now < focus_active_until

    if is_auto_work_unlocked():
        work_timer += delta
        if work_timer >= eff_delay:
            game["money"] += gain
            game["money_since_reset"] += gain
            if game.get("focus_unlocked", False) and not focus_active:
                game["focus"] = min(
                    config.FOCUS_MAX,
                    game.get("focus", 0) + config.FOCUS_CHARGE_PER_EARN,
                )
            work_timer -= eff_delay
            save_game()
    else:
        work_timer = 0  # reset so the bar doesn’t auto-fill


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
def is_auto_work_unlocked():
    return "inspire_auto_work" in game.get("inspiration_upgrades", [])


def open_upgrade_menu():
    global KEY_PRESSED

    while True:
        # build menu content
        unlocked = get_unlocked_upgrades()
        lines = ["--- UPGRADE BAY ---"]
        for i, u in enumerate(unlocked, start=1):
            owned = "(owned)" if is_inspire_owned(u["id"]) else ""
            typ = u.get("type", "mult")
            val = u.get("value", 0)
            if typ == "unlock_focus":
                val_display = ""
            elif typ == "add":
                val_display = f"+{val}"
            elif typ == "mult":
                val_display = f"x{val}"
            else:
                val_display = str(val)
            lines.append(
                f"{i}. {u['name']} - ${u['cost']} {owned} [{typ} {val_display}]"
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
                    break  # refresh menu after action


def buy_idx_upgrade(upg):
    uid = upg["id"]
    if uid in game.get("owned", []):
        tmp = boxed_lines(
            [f"You already own {upg['name']}."],
            title=" Upgrade ",
            pad_top=1,
            pad_bottom=1,
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)
        return

    if game.get("money", 0) >= upg["cost"]:
        game["money"] -= upg["cost"]
        game["owned"].append(uid)

        # apply special effects
        if upg.get("type") == "unlock_focus":
            game["focus_unlocked"] = True

        save_game()
        tmp = boxed_lines(
            [f"Purchased {upg['name']}!"], title=" Upgrade ", pad_top=1, pad_bottom=1
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)
    else:
        tmp = boxed_lines(
            [f"Not enough money to buy {upg['name']} (cost ${upg['cost']})."],
            title=" Upgrade ",
            pad_top=1,
            pad_bottom=1,
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)


def get_unlocked_upgrades():
    unlocked = []
    for i, upg in enumerate(all_upgrades):
        if i == 0 or all_upgrades[i - 1]["id"] in game.get("owned", []):
            unlocked.append(upg)
    return unlocked


# -----------------------------
# Inspiration
# -----------------------------
def open_inspire_menu():
    global KEY_PRESSED
    while True:
        upgrades = [
            u
            for u in config.INSPIRE_UPGRADES
            if u["id"] not in game.get("inspiration_upgrades", [])
        ]
        lines = ["--- INSPIRE BAY ---"]
        for i, u in enumerate(upgrades, start=1):
            lines.append(f"{i}. {u['name']} - Cost: {u['cost']} Inspire")

        if not upgrades:
            lines.append("All upgrades purchased!")

        lines.append("")
        lines.append("Press number to buy, B to back.")

        box = boxed_lines(lines, title=" Inspire ", pad_top=1, pad_bottom=1)
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(box))

        while True:
            time.sleep(0.05)
            if KEY_PRESSED:
                k = KEY_PRESSED.lower()
                KEY_PRESSED = None
                if k == "b":
                    return
                if k.isdigit():
                    idx = int(k) - 1
                    if 0 <= idx < len(upgrades):
                        buy_inspire_upgrade(upgrades[idx])
                    break

# Handler for levels
def get_inspire_cost(upg, current_level=0):
    base_cost = upg.get("base_cost", upg.get("cost", 0))
    mult = upg.get("cost_mult", 1)
    return int(base_cost * (mult ** current_level))

def get_inspire_value(upg):
    if "base_value" in upg:
        return upg["base_value"] * (upg.get("value_mult", 1) ** upg.get("level", 0))
    return upg.get("value", 1)


def buy_inspire_upgrade(upg):
    # Handle multi-level upgrades
    is_multilevel = "base_cost" in upg
    current_level = upg.get("level", 0)
    max_level = upg.get("max_level", 1)

    cost = get_inspire_cost(upg)

    if game.get("inspiration", 0) < cost:
        tmp = boxed_lines(
            [f"Not enough Inspire to buy {upg['name']}."],
            title=" Inspire ",
            pad_top=1,
            pad_bottom=1,
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)
        return

    if is_multilevel and current_level >= max_level:
        tmp = boxed_lines(
            [f"{upg['name']} is already max level!"],
            title=" Inspire ",
            pad_top=1,
            pad_bottom=1,
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)
        return

    # Deduct and upgrade
    game["inspiration"] -= cost

    if is_multilevel:
        upg["level"] = current_level + 1
        value = get_inspire_value(upg)
    else:
        value = upg.get("value", 1)
        game.setdefault("inspiration_upgrades", []).append(upg["id"])

    # Apply effect
    if upg["type"] == "work_mult":
        game["work_delay_multiplier"] = game.get("work_delay_multiplier", 1.0) * value
    elif upg["type"] == "money_mult":
        game["money_mult"] = game.get("money_mult", 1.0) * value
    elif upg["type"] == "focus_max":
        game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + value
    elif upg["type"] == "unlock_motivation":
        game["motivation_unlocked"] = True
    elif upg["type"] == "auto_work":
        game["auto_work_unlocked"] = True

    save_game()

    # Confirmation message
    msg = (
        f"Upgraded {upg['name']} to Lv.{upg['level']}!"
        if is_multilevel
        else f"Purchased {upg['name']}!"
    )
    tmp = boxed_lines([msg], title=" Inspire ", pad_top=1, pad_bottom=1)
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(tmp))
    time.sleep(1.2)


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
    gained = calculate_inspiration(money_since_reset)

    play_inspiration_reset_animation()

    # apply reset
    game["inspiration"] = game.get("inspiration", 0) + gained
    game.update(
        {
            "money": 0.0,
            "money_since_reset": 0.0,
            "fatigue": 0,
            "focus": 0,
            "owned": [],
            "focus_unlocked": False,
            "inspiration_unlocked": True,
            "layer": max(game.get("layer", 0), 1),
            "motivation": 100,
            "motivation_unlocked": True,
        }
    )
    save_game()
    
    # display lore-friendly message
    done_msg = boxed_lines(
        [f"You wake from a strange dream... Gained {gained} Inspiration!"],
        title=" Inspiration Gained ",
        pad_top=1,
        pad_bottom=1,
    )
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(done_msg))
    time.sleep(1.5)


def handle_inspire_purchase(idx):
    upgrades = config.INSPIRE_UPGRADES
    if not (0 <= idx < len(upgrades)):
        return

    upg = upgrades[idx]
    max_level = upg.get("max_level", 1)
    current_level = get_inspire_level(upg["id"])

    if current_level >= max_level:
        msg = f"{upg['name']} is already at max level!"
        tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.0)
        return

    cost = get_inspire_cost(upg, current_level=current_level)

    if game.get("inspiration", 0) < cost:
        msg = f"Not enough Inspiration for {upg['name']} (cost {cost})!"
        tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.0)
        return

    # Deduct cost
    game["inspiration"] -= cost

    # Find existing upgrade
    found = False
    for i, u in enumerate(game.get("inspiration_upgrades", [])):
        if (isinstance(u, dict) and u.get("id") == upg["id"]) or (isinstance(u, str) and u == upg["id"]):
            if isinstance(u, dict):
                u["level"] += 1
            else:
                game["inspiration_upgrades"][i] = {"id": u, "level": 2}
            found = True
            break

    if not found:
        game.setdefault("inspiration_upgrades", []).append({"id": upg["id"], "level": 1})

    # Apply effects
    value = get_inspire_value(upg) * (current_level + 1 if "base_value" in upg else 1)
    if upg["type"] == "money_mult":
        game["money_mult"] = game.get("money_mult", 1.0) * value
    elif upg["type"] == "work_mult":
        game["work_delay_multiplier"] = game.get("work_delay_multiplier", 1.0) * value
    elif upg["type"] == "focus_max":
        game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + value
    elif upg["type"] == "unlock_motivation":
        game["motivation_unlocked"] = True
    elif upg["type"] == "auto_work":
        game["auto_work_unlocked"] = True

    save_game()
    msg = f"Purchased {upg['name']} level {current_level + 1}!"
    tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(tmp))
    time.sleep(0.7)


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

        # Randomly emit new Zs gradually
        if len(zs) < num_zs and random.random() < 0.3:
            zs.append(
                {
                    "y": term_h - 4,
                    "x": term_w // 2 + random.randint(-10, 10),
                    "life": z_lifetime,
                }
            )

        # Draw Zs
        for z in zs:
            y, x = int(z["y"]), int(z["x"])
            if 0 <= y < term_h and 0 <= x < term_w:
                row = screen[y]
                screen[y] = row[:x] + "Z" + row[x + 1 :]

        # Print screen
        print("\n".join(screen))

        # Update Zs: move up and fade
        for z in zs:
            z["y"] -= 1
            z["x"] += random.choice([-1, 0, 1])
            z["life"] -= 1

        # Remove dead Zs
        zs = [z for z in zs if z["life"] > 0]

        time.sleep(0.2)

    # Final big exclamation mark
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
# Reset
# -----------------------------
def calculate_inspiration(money_since_reset):
    money_since_reset = game.get("money_since_reset", 0)

    return math.floor(((money_since_reset**0.4) / 25) + 1)


def predict_next_point():
    current_money = game.get("money_since_reset", 0)
    current_insp = calculate_inspiration(current_money)

    # Find the minimum money needed to get one more inspiration
    # Formula inversion: next_insp = floor((x^0.4)/25 + 1)
    next_insp = current_insp + 1

    # Solve for x: (x^0.4)/25 + 1 >= next_insp
    target_money = ((next_insp - 1) * 25) ** (1 / 0.4)

    remaining = round(max(target_money - current_money, 0), 2)
    return remaining


# -----------------------------
# Main loop
# -----------------------------
def main_loop():
    """Main game loop with proper inspiration upgrade handling."""
    global KEY_PRESSED, running, work_timer, last_tick_time
    load_game()
    convert_old_upgrades()

    last_tick_time = time.time()  # properly initialize

    listener = threading.Thread(target=key_listener, daemon=True)
    listener.start()

    if game.get("layer", 0) >= 1 and not game.get("inspiration_unlocked", False):
        game["inspiration_unlocked"] = True
        game["layer"] = 1
        save_game()

    current_screen = "work"

    try:
        while running:
            # -----------------------------
            # Work tick
            # -----------------------------
            now = time.time()
            delta = now - last_tick_time
            last_tick_time = now

            gain, eff_delay = compute_gain_and_delay()
            focus_active = now < focus_active_until

            # Only increment timer if auto-work is unlocked
            if game.get("auto_work_unlocked", False):
                work_timer += delta
                if work_timer >= eff_delay:
                    game["money"] += gain
                    work_timer -= eff_delay
                    if game.get("focus_unlocked", False) and not focus_active:
                        game["focus"] = min(
                            config.FOCUS_MAX,
                            game.get("focus", 0) + config.FOCUS_CHARGE_PER_EARN,
                        )
                    if game.get("motivation_unlocked", False):
                        game["motivation"] = max(
                            0, game["motivation"] - config.MOTIVATION_DRAIN_PER_WORK
                        )
                    save_game()
            else:
                # Keep bar frozen until W is pressed
                pass

            # -----------------------------
            # Render UI
            # -----------------------------
            render_ui(screen=current_screen)

            # -----------------------------
            # Handle input non-blocking
            # -----------------------------
            if KEY_PRESSED:
                k = KEY_PRESSED.lower()
                KEY_PRESSED = None

                # Quit
                if k == "q":
                    running = False
                    break
                # Work screen
                elif k == "w":
                    current_screen = "work"
                    gain, eff_delay = compute_gain_and_delay()
                    focus_active = now < focus_active_until

                    # If auto-work is disabled we reset the timer so manual work
                    # uses the manual short-cooldown behaviour. If auto-work is
                    # enabled, do NOT reset work_timer so the auto-work progress
                    # bar continues uninterrupted.
                    if not game.get("auto_work_unlocked", False):
                        work_timer = 0

                    # Perform manual work (instant)
                    game["money"] += gain
                    game["money_since_reset"] += gain
                    if game.get("focus_unlocked", False) and not focus_active:
                        game["focus"] = min(
                            config.FOCUS_MAX,
                            game.get("focus", 0) + config.FOCUS_CHARGE_PER_EARN,
                        )
                    if game.get("motivation_unlocked", False):
                        game["motivation"] = max(
                            0, game["motivation"] - config.MOTIVATION_DRAIN_PER_WORK
                        )
                    save_game()


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
                        handle_inspire_purchase(idx)
                        # immediately refresh UI to show gain/delay changes
                        render_ui(screen="inspiration")
                        time.sleep(0.3)

            time.sleep(0.05)  # small tick interval, avoids skipping work cycles

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
