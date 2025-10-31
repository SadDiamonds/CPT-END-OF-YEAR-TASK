import json, os, time, sys, threading

global KEY_PRESSED

# Cross-platform non-blocking input
try:
    import msvcrt  # Windows
except ImportError:
    import select, tty, termios  # macOS/Linux

from ascii_art import LAYER_0_DESK, LAYER_1_INSPIRATION

SAVE_PATH = "data/save.json"
if not os.path.exists("data"):
    os.makedirs("data")

work_timer = 0
WORK_DELAY = 5  # seconds per money gain
KEY_PRESSED = None  # Store key pressed


# -----------------------------
# Save System
# -----------------------------
def load_save():
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r") as f:
                data = f.read().strip()
                if data:
                    return json.loads(data)
        except json.JSONDecodeError:
            print("Save file empty or corrupted, starting new game.")
    return {
        "layer": 0,
        "money": 0,
        "fatigue": 0,
        "focus": 0,
        "inspiration": 0,
        "money_upgrades": [],
        "focus_unlocked": False,
        "money_mult": 1,
        "work_delay": WORK_DELAY,
    }


def save_game(data):
    with open(SAVE_PATH, "w") as f:
        json.dump(data, f)


game = load_save()

all_upgrades = [
    {"name": "Better Desk", "cost": 20, "effect": 1.5, "unlocked": True},
    {"name": "Coffee", "cost": 200, "effect": 2, "unlocked": False},
    {"name": "Overtime", "cost": 1000, "unlocked": False},
    {"name": "Focus Meter", "cost": 5000, "unlocked": False},
]


# -----------------------------
# Utilities
# -----------------------------
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def display_status():
    clear_screen()
    if game["layer"] == 0:
        print(LAYER_0_DESK)
    else:
        print(LAYER_1_INSPIRATION)
    print(f"\nLayer: {game['layer']}")
    print(
        f"Money: ${game['money']:.1f} | Fatigue: {game['fatigue']} | Focus: {game['focus']}/100 | Inspiration: {game['inspiration']}"
    )

    if game["focus_unlocked"]:
        focus_bar_len = 20
        focus_progress = int((game["focus"] / 100) * focus_bar_len)
        focus_bar = "#" * focus_progress + "-" * (focus_bar_len - focus_progress)
        print(f"Focus: [{focus_bar}]")

    print("\nUpgrades:")
    for i, upg in enumerate(all_upgrades, start=1):
        if upg["unlocked"]:
            print(f"{i}. {upg['name']} - {upg['cost']} Money")

    print("\nOptions: [Q]uit | [U]pgrade | [O]vertime | [R]eset to Inspiration")


# -----------------------------
# Work Mechanics
# -----------------------------
def work_tick():
    global work_timer
    work_timer += 1

    # Draw progress bar
    bar_len = 20
    progress = min(work_timer / game["work_delay"], 1)
    filled = int(progress * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"[{bar}] Working...", end="\r")

    # Gain money if timer reached
    if work_timer >= game["work_delay"]:
        earned = 1 * game.get("money_mult", 1)
        game["money"] += earned
        work_timer = 0
        if game["focus_unlocked"]:
            game["focus"] = min(100, game["focus"] + 10)
        save_game(game)


def overtime():
    if "Overtime" not in game["money_upgrades"]:
        print("You haven't unlocked Overtime yet.")
        time.sleep(1)
        return
    game["money"] += 3
    game["fatigue"] += 5
    save_game(game)
    print("Overtime done! +3 Money, +5 Fatigue")
    time.sleep(1)


# -----------------------------
# Upgrades
# -----------------------------
def apply_upgrade_effect(upg):
    name = upg["name"]
    if name == "Better Desk":
        game["money_mult"] = game.get("money_mult", 1) * upg.get("effect", 1)
    elif name == "Coffee":
        game["work_delay"] = max(
            0.5, game.get("work_delay", WORK_DELAY) / upg.get("effect", 1)
        )
    elif name == "Overtime":
        game["overtime_unlocked"] = True
    elif name == "Focus Meter":
        game["focus_unlocked"] = True


def buy_upgrade():
    unlocked = [u for u in all_upgrades if u["unlocked"]]
    for i, u in enumerate(unlocked, start=1):
        print(f"{i}. {u['name']} - {u['cost']} Money")

    global KEY_PRESSED
    print("Press number of upgrade to buy:")
    while KEY_PRESSED is None:
        time.sleep(0.1)
    choice = KEY_PRESSED
    KEY_PRESSED = None

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(unlocked):
            upg = unlocked[idx]
            if game["money"] >= upg["cost"]:
                game["money"] -= upg["cost"]
                if upg["name"] not in game["money_upgrades"]:
                    game["money_upgrades"].append(upg["name"])
                apply_upgrade_effect(upg)
                # Unlock next
                for next_upg in all_upgrades:
                    if not next_upg["unlocked"]:
                        next_upg["unlocked"] = True
                        break
            else:
                print("Not enough money!")
        else:
            print("Invalid choice!")
    else:
        print("Enter a number!")


# -----------------------------
# Reset Layer
# -----------------------------
def reset_inspiration():
    if game["money"] < 100:
        print("Need at least $100 to convert to Inspiration.")
        time.sleep(1)
        return
    gained = game["money"] // 50
    game["inspiration"] += gained
    print(f"Reset! Gained {gained} Inspiration.")
    time.sleep(1)
    game.update(
        {
            "money": 0,
            "fatigue": 0,
            "focus": 0,
            "money_upgrades": [],
            "focus_unlocked": False,
            "money_mult": 1,
            "work_delay": WORK_DELAY,
            "layer": 1,
        }
    )
    save_game(game)


# -----------------------------
# Key listener
# -----------------------------
def key_listener():
    global KEY_PRESSED
    while True:
        if sys.platform == "win32":
            if msvcrt.kbhit():
                KEY_PRESSED = msvcrt.getwch().lower()
        else:
            dr, dw, de = select.select([sys.stdin], [], [], 0)
            if dr:
                KEY_PRESSED = sys.stdin.read(1).lower()
        time.sleep(0.05)


# -----------------------------
# Main Loop
# -----------------------------
def main_loop():
    global KEY_PRESSED
    listener = threading.Thread(target=key_listener, daemon=True)
    listener.start()
    try:
        while True:
            display_status()
            work_tick()
            time.sleep(1)
            if KEY_PRESSED:
                key = KEY_PRESSED
                KEY_PRESSED = None
                if key == "q":
                    print("Exiting game...")
                    break
                elif key == "u":
                    buy_upgrade()
                elif key == "o":
                    overtime()
                elif key == "r":
                    reset_inspiration()
    except KeyboardInterrupt:
        print("\nExiting game...")


if __name__ == "__main__":
    print("Welcome to ESCAPE: Incremental Game Prototype")
    time.sleep(1)
    main_loop()
