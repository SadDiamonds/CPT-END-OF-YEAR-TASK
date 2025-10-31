import json, os, time, sys, threading, select

# Cross-platform input
try:
    import msvcrt  # Windows
except ImportError:
    msvcrt = None

from ascii_art import LAYER_0_DESK, LAYER_1_INSPIRATION

SAVE_PATH = "data/save.json"
if not os.path.exists("data"):
    os.makedirs("data")

# -----------------------------
# Global variables
# -----------------------------
game = {}
work_timer = 0
WORK_DELAY = 5
KEY_PRESSED = None  # stores last key pressed


# -----------------------------
# Save system
# -----------------------------
def load_save():
    if os.path.exists(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r") as f:
                data = f.read().strip()
                if data:
                    return json.loads(data)
        except json.JSONDecodeError:
            print("Save file empty or corrupted. Starting new game.")
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


def save_game():
    with open(SAVE_PATH, "w") as f:
        json.dump(game, f)


# -----------------------------
# Upgrades
# -----------------------------
all_upgrades = [
    {"name": "Better Desk", "cost": 20, "effect": 1.5, "unlocked": True},
    {"name": "Coffee", "cost": 200, "effect": 2, "unlocked": False},
    {"name": "Overtime", "cost": 1000, "unlocked": False},
    {"name": "Focus Meter", "cost": 5000, "unlocked": False},
]


def apply_upgrade_effect(upg):
    name = upg["name"]
    if name == "Better Desk":
        game["money_mult"] *= upg.get("effect", 1)
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
    print("\n--- Upgrades ---")
    for i, u in enumerate(unlocked, start=1):
        print(f"{i}. {u['name']} - {u['cost']} Money")
    print("Press number of upgrade to buy:")

    global KEY_PRESSED
    while KEY_PRESSED is None:
        time.sleep(0.05)
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
                # Unlock next upgrade
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
    time.sleep(1)


# -----------------------------
# Reset/Inspiration
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
    save_game()


# -----------------------------
# Work mechanics
# -----------------------------
def work_tick():
    global work_timer
    work_timer += 1
    progress = min(work_timer / game.get("work_delay", WORK_DELAY), 1)
    bar_len = 20
    filled = int(progress * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"[{bar}] Working...", end="\r")
    if work_timer >= game.get("work_delay", WORK_DELAY):
        earned = 1 * game.get("money_mult", 1)
        game["money"] += earned
        work_timer = 0
        if game["focus_unlocked"]:
            game["focus"] = min(100, game["focus"] + 10)
        save_game()


def overtime():
    if "Overtime" not in game["money_upgrades"]:
        print("You haven't unlocked Overtime yet.")
        time.sleep(1)
        return
    game["money"] += 3
    game["fatigue"] += 5
    save_game()
    print("Overtime done! +3 Money, +5 Fatigue")
    time.sleep(1)


# -----------------------------
# Display
# -----------------------------
def display_status():
    os.system("cls" if os.name == "nt" else "clear")
    print("╭" + "-" * 50 + "╮")
    print("|{:^50}|".format("ESCAPE: Incremental Game"))
    print("╰" + "-" * 50 + "╯\n")

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
    for i, u in enumerate(all_upgrades, 1):
        if u["unlocked"]:
            print(f"{i}. {u['name']} - {u['cost']} Money")

    print("\nOptions: [Q]uit | [U]pgrade | [O]vertime | [R]eset to Inspiration")


# -----------------------------
# Key Listener
# -----------------------------
def key_listener():
    global KEY_PRESSED
    if sys.platform == "win32":
        while True:
            if msvcrt.kbhit():
                KEY_PRESSED = msvcrt.getwch().lower()
            time.sleep(0.05)
    else:
        import tty, termios

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                dr, dw, de = select.select([sys.stdin], [], [], 0)
                if dr:
                    KEY_PRESSED = sys.stdin.read(1).lower()
                time.sleep(0.05)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


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
    game = load_save()
    print("Welcome to ESCAPE: Incremental Game Prototype")
    time.sleep(1)
    main_loop()
