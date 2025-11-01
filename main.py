# main.py
import json, os, time, sys, threading, shutil
import math
import select

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

from config import INSPIRE_UPGRADES

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

    if "inspire_auto_work" in game.get("inspiration_upgrades", []):
        game["auto_work_unlocked"] = True


def save_game():
    try:
        with open(SAVE_PATH, "w") as f:
            json.dump(game, f)
    except Exception as e:
        print("Warning: failed to save:", e)


# -----------------------------
# Compute gain and delay
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
    for u in config.INSPIRE_UPGRADES:
        if u["id"] in game.get("inspiration_upgrades", []):
            if u["type"] == "money_mult":
                gain_mult *= u.get("value", 1)
            elif u["type"] == "work_mult":
                delay_mult *= u.get("value", 1)
            elif u["type"] == "focus_max":
                game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + u.get(
                    "value", 0
                )

    eff_gain = (base_gain + gain_add) * gain_mult
    eff_delay = base_delay * delay_mult

    if time.time() < focus_active_until:
        eff_delay *= config.FOCUS_BOOST_FACTOR

    motivation = game.get("motivation", config.MOTIVATION_MAX)
    motivation_mult = (motivation / config.MOTIVATION_MAX) * 4 + 1  # 1x→5x
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
    calc_insp = calculate_inspiration(layer, money_since_reset)
    time_next = predict_next_point()
    left_lines = []

    if game.get("inspiration_unlocked", False):
        if screen == "work":
            left_lines.append("    === INSPIRATION ===")
            left_lines.append(f"        Points: {game.get('inspiration',0)}")
            left_lines.append("")
            left_lines.append(" [1] Open Inspiration Tree ")
            left_lines.append("")
            if game.get("money", 0) >= 1000:
                left_lines.append(f"    You realise that all this work...")
                left_lines.append("is all for naught,")
                left_lines.append(f"you decide to leave behind everything in")
                left_lines.append(
                    f"return for {'an' if calc_insp==1 else str(calc_insp)} Inspiration"
                )
                left_lines.append("")
                left_lines.append(f"[I]nspire for {calc_insp} Inspiration")
                if game.get("inspiration_unlocked", False):
                    left_lines.append("")
                    left_lines.append(f"{time_next} until next point")
        elif screen == "inspiration":
            left_lines.append("=== INSPIRATION TREE ===")
            left_lines.append(f"      Points: {game.get('inspiration',0)}")
            left_lines.append("")
            tree = INSPIRE_UPGRADES
            for i, u in enumerate(tree, start=1):
                owned = (
                    "(owned)" if u["id"] in game.get("inspiration_upgrades", []) else ""
                )
                effect = f" → {u.get('desc', '')}" if u.get("desc") else ""
                left_lines.append(f" {i}. {u['name']} - Cost: {u['cost']} {owned}")
                if effect:
                    left_lines.append(f"     {effect}")
            left_lines.append("")
            left_lines.append(" [B] Back to Work ")
    elif game.get("money", 0) >= 1000:
        left_lines.append(f"    You realise that all this work...")
        left_lines.append("is all for naught,")
        left_lines.append(f"you decide to leave behind everything in")
        left_lines.append(
            f"return for {'an' if calc_insp==1 else str(calc_insp)} Inspiration"
        )
        left_lines.append("")
        left_lines.append(f"[I]nspire for {calc_insp} Inspiration")
    else:
        left_lines.append("Reach $1000 to unlock Inspiration")

    # -----------------------------
    # Right panel (~50%)
    # -----------------------------
    right_lines = []

    # 1️ Desk table at top
    if LAYER_0_DESK:
        right_lines.extend(render_desk_table())

    # 2️ Focus bar below desk
    if game.get("focus_unlocked", False):
        focus_max = config.FOCUS_MAX + game.get("focus_max_bonus", 0)
        fprog = min(game.get("focus", 0) / float(focus_max), 1.0)
        fbar_len = 36
        ffilled = int(fprog * fbar_len)
        focus_label_line = f"FOCUS: {int(fprog*100):3d}%"
        focus_bar_line = "[" + "#" * ffilled + "-" * (fbar_len - ffilled) + "]"
        right_lines.append(focus_label_line)
        right_lines.append(focus_bar_line)
        right_lines.append("")

    # 3️ Work info
    right_lines.append(
        f"MONEY: ${game.get('money',0):.2f}   GAIN: {effective_gain:.2f} / cycle   DELAY: {effective_delay:.2f}s"
    )
    right_lines.append(work_bar)
    right_lines.append(
        "Auto-work: " + ("ENABLED" if is_auto_work_unlocked() else "MANUAL (press W)")
    )

    # 4️ Owned upgrades
    owned_names = [u["name"] for u in all_upgrades if u["id"] in game.get("owned", [])]
    right_lines.append("")
    right_lines.append(
        "Owned Upgrades: " + (", ".join(owned_names) if owned_names else "(none)")
    )

    # 5️ Options
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
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(box))


def render_desk_table():
    table = LAYER_0_DESK.copy()

    owned_ids = [u["id"] for u in all_upgrades if u["id"] in game.get("owned", [])]
    owned_arts = [UPGRADE_ART[uid] for uid in owned_ids if uid in UPGRADE_ART]

    # Indices of empty lines inside the table (where we can place art)
    empty_indices = [
        i for i, line in enumerate(table) if line.strip() == "║                       ║"
    ]

    # Fill from bottom to top for realistic desk stacking
    empty_idx_iter = reversed(empty_indices)
    for art in owned_arts:
        art_height = len(art)
        try:
            # Take the next N empty lines from bottom for the art
            art_positions = [next(empty_idx_iter) for _ in range(art_height)]
        except StopIteration:
            break  # no more space

        # Place each line of the art into the table at the corresponding position
        for line_pos, art_line in zip(reversed(art_positions), art):
            inner_width = 23  # width inside the ║ ║
            table[line_pos] = "       ║" + art_line.center(inner_width) + "║"

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
            owned = "(owned)" if u["id"] in game.get("owned", []) else ""
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

def buy_inspire_upgrade(upg):
    if game.get("inspiration", 0) >= upg["cost"]:
        game["inspiration"] -= upg["cost"]
        if "inspiration_upgrades" not in game:
            game["inspiration_upgrades"] = []
        game["inspiration_upgrades"].append(upg["id"])

        # Apply effects
        if upg["type"] == "work_mult":
            game["work_delay_multiplier"] = (
                game.get("work_delay_multiplier", 1.0) * upg["value"]
            )
        elif upg["type"] == "money_mult":
            game["money_mult"] = game.get("money_mult", 1.0) * upg["value"]
        elif upg["type"] == "focus_max":
            game["focus_max_bonus"] = game.get("focus_max_bonus", 0) + upg["value"]
        save_game()
        tmp = boxed_lines(
            [f"Purchased {upg['name']}!"], title=" Inspire ", pad_top=1, pad_bottom=1
        )
        os.system("cls" if os.name == "nt" else "clear")
        print("\n".join(tmp))
        time.sleep(1.2)
    else:
        tmp = boxed_lines(
            [f"Not enough Inspire to buy {upg['name']}."],
            title=" Inspire ",
            pad_top=1,
            pad_bottom=1,
        )
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
    gained = calculate_inspiration(layer, money_since_reset)

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

    if upg["id"] in game.get("inspiration_upgrades", []):
        msg = f"You already own {upg['name']}!"
    elif game.get("inspiration", 0) >= upg["cost"]:
        game["inspiration"] -= upg["cost"]
        game.setdefault("inspiration_upgrades", []).append(upg["id"])
        save_game()
        msg = f"Purchased {upg['name']}!"
    else:
        msg = f"Not enough Inspiration for {upg['name']}!"

    # Show confirmation
    tmp = boxed_lines([msg], title="Inspiration", pad_top=1, pad_bottom=1)
    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(tmp))
    time.sleep(0.7)


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
def calculate_inspiration(layer, money_since_reset):

    return math.floor(((money_since_reset**0.4) / 25) + 1)


def predict_next_point():
    gain, eff_delay = compute_gain_and_delay()
    remaining = max(eff_delay - work_timer, 0)
    return remaining


# -----------------------------
# Main loop
# -----------------------------
def main_loop():
    """Main game loop with proper inspiration upgrade handling."""
    global KEY_PRESSED, running, work_timer, last_tick_time
    load_game()

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

                    # Always start fresh — ignore any half-filled progress
                    work_timer = 0

                    # Shorter manual delay (instant or near-instant)
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
