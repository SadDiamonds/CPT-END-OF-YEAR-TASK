# /game/main.py
from __future__ import annotations
import json, os, sys, time, random, textwrap
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

SAVE_FILE = "escape_save.json"
BACKUP_FILE = "escape_save.bak"

def slow_print(s: str, delay: float):
    """Gate output speed; 0 = instant."""
    if delay <= 0:
        print(s)
        return
    for ch in s:
        print(ch, end="", flush=True)
        time.sleep(min(delay, 0.02))
    print()

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def progress_bar(pct: int, width: int = 30) -> str:
    pct = clamp(pct, 0, 100)
    fill = int((pct / 100) * width)
    return f"[{'#' * fill}{'.' * (width - fill)}] {pct:3d}%"

class Renderer:
    """ASCII scenes that evolve with progress."""
    @staticmethod
    def header(gs: "GameState") -> str:
        mode = "Candy HUD" if gs.flags.get("candy_mode") else "Classic HUD"
        return f"\nDay {gs.day} | {gs.location.upper()} | Scrap:{gs.scrap} Keys:{gs.keys} | {progress_bar(gs.progress)}\n<{mode}>\n"

    @staticmethod
    def scene(gs: "GameState") -> str:
        p = gs.progress
        banners = []
        if gs.flags.get("konami_done"):
            banners.append("※ SECRET POWER COURSES THROUGH YOU ※")
        banner = ("\n" + "\n".join(banners) + "\n") if banners else ""
        if gs.location == "cell":
            art = r"""
   ____________________
  |  _  _         _   |
  | | || |  ___  | |  |
  | | || | / _ \ | |  |
  | | || || (_) || |  |
  | |_| \_\\___/ |_|  |
  |    PRISON CELL    |
  |__==__==__==__==___|
     ||      || 
     ||______||   """
            if p >= 10: art += "\nA loose brick reveals a tiny stash."
            if p >= 20: art += "\nThe door lock seems... weaker."
        elif gs.location == "workbench":
            art = r"""
   _____________
  |   WORKBENCH |
  |  tools: []  |
  |__==__==__==_|
  ( )  ( )  ( )      """
            if "lockpick" in gs.inventory:
                art += "\nA crude LOCKPICK gleams with hope."
        elif gs.location == "sewer":
            art = r"""
   ~ ~ ~  SEWERS  ~ ~ ~
  [==]===]   [=== [==]==
   ~  dripping echoes ~  """
            if gs.flags.get("sewer_map"):
                art += "\nYou etched a faint MAP on your palm."
        elif gs.location == "yard_gate":
            art = r"""
   _____________
  |  PRISON YARD|
  |   [ GATE ]  |
  |__==__==__==_|
   Guards pace in patterns... """
        else:
            art = "(void)"
        return banner + art

    @staticmethod
    def toast(msg: str) -> str:
        return f"\n>> {msg}\n"

class SaveManager:
    """Atomic JSON save/load with backup; prevents progress loss."""
    @staticmethod
    def save(gs: "GameState") -> None:
        tmp = SAVE_FILE + ".tmp"
        data = asdict(gs)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            if os.path.exists(SAVE_FILE):
                try:
                    os.replace(SAVE_FILE, BACKUP_FILE)
                except Exception:
                    pass
            os.replace(tmp, SAVE_FILE)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise e

    @staticmethod
    def load() -> Optional["GameState"]:
        cand = None
        for path in (SAVE_FILE, BACKUP_FILE):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return GameState.from_dict(data)
            except Exception:
                cand = None
        return cand

KONAMI = ["up","up","down","down","left","right","left","right","b","a"]

@dataclass
class GameState:
    player: str = "Prisoner"
    day: int = 1
    location: str = "cell"
    progress: int = 0
    scrap: int = 0
    keys: int = 0
    inventory: List[str] = field(default_factory=list)
    unlocks: Dict[str, bool] = field(default_factory=lambda: {"workbench": False, "sewer": False, "yard_gate": False})
    flags: Dict[str, bool] = field(default_factory=dict)
    difficulty: str = "Standard"
    text_speed: float = 0.0  # 0 = instant
    ascii_on: bool = True
    input_history: List[str] = field(default_factory=list)
    rng_seed: int = field(default_factory=lambda: random.randint(10_000, 9_999_999))

    def rng(self) -> random.Random:
        return random.Random(self.rng_seed + self.day * 997 + self.progress * 13)

    def add_progress(self, n: int, why: str = ""):
        before = self.progress
        self.progress = clamp(self.progress + n, 0, 100)
        if self.progress >= 100:
            self.flags["escaped"] = True
        if (before // 10) != (self.progress // 10) and why:
            slow_print(Renderer.toast(f"Milestone reached: {self.progress}% ({why})"), self.text_speed)

    def record_input(self, token: str):
        self.input_history.append(token.lower())
        if len(self.input_history) > len(KONAMI):
            self.input_history = self.input_history[-len(KONAMI):]
        if self.input_history[-len(KONAMI):] == KONAMI and not self.flags.get("konami_done"):
            self.flags["konami_done"] = True
            self.add_progress(5, "Konami Secret")
            self.scrap += 3

    @staticmethod
    def from_dict(d: Dict) -> "GameState":
        gs = GameState()
        gs.__dict__.update(d)
        # Safety: ensure required keys
        for key in ["unlocks","flags"]:
            if key not in gs.__dict__ or not isinstance(gs.__dict__[key], dict):
                gs.__dict__[key] = {}
        if "input_history" not in gs.__dict__:
            gs.input_history = []
        return gs

# ---------- Game Systems ----------

def prompt(gs: GameState, q: str) -> str:
    s = input(q).strip()
    gs.record_input(s)
    return s

def notify(gs: GameState, s: str):
    slow_print(Renderer.toast(s), gs.text_speed)

def menu_main() -> None:
    gs = None
    while True:
        clear()
        print(r"""
███████╗███████╗ ██████╗ █████╗ ██████╗ ██████╗ ███████╗
██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝
█████╗  ███████╗██║     ███████║██████╔╝██████╔╝█████╗  
██╔══╝  ╚════██║██║     ██╔══██║██╔═══╝ ██╔══██╗██╔══╝  
███████╗███████║╚██████╗██║  ██║██║     ██║  ██║███████╗
╚══════╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝
                  ESCAPE: THE CELL
""")
        print("1) New Game   2) Continue   3) Level/Challenges   4) Help   5) Settings   6) Quit")
        choice = input("> ").strip()
        if choice == "1":
            gs = wizard_new_game()
            game_loop(gs)
        elif choice == "2":
            gs = SaveManager.load()
            if gs:
                game_loop(gs)
            else:
                input("No valid save found. Press Enter.")
        elif choice == "3":
            challenges_menu()
        elif choice == "4":
            help_screen()
        elif choice == "5":
            settings_menu()
        elif choice == "6":
            clear(); print("Bye."); sys.exit(0)
        else:
            pass

def wizard_new_game() -> GameState:
    clear()
    name = input("Your name (or CANDYBOX for special HUD): ").strip() or "Prisoner"
    difficulty = ""
    while difficulty not in ("Chill","Standard","Hardcore"):
        difficulty = input("Difficulty [Chill/Standard/Hardcore]: ").strip().title() or "Standard"
    gs = GameState(player=name, difficulty=difficulty)
    if name.upper() == "CANDYBOX":
        gs.flags["candy_mode"] = True
    if difficulty == "Chill":
        gs.text_speed = 0.0; gs.scrap = 3
    elif difficulty == "Standard":
        gs.text_speed = 0.0
    else:
        gs.text_speed = 0.0; gs.flags["permadeath"] = True
    notify(gs, f"Welcome, {gs.player}. Theme: ESCAPE. Survive, scavenge, slip away.")
    return gs

def help_screen():
    clear()
    print(textwrap.dedent("""
    HOW TO PLAY
    - Each day pick actions. Gather SCRAP to craft a LOCKPICK.
    - Unlock rooms as progress rises. Beat minigames to advance.
    - Type 'inv' for inventory, 'save' to save, 'p' to pause.
    - Secrets exist. Try odd verbs.
    Commands (examples): wait, search, craft, move, pick, left/right, up/down, talk, help
    """))
    input("Press Enter.")

def settings_menu():
    clear()
    print("SETTINGS")
    print("1) Text speed  2) Toggle ASCII  3) Back")
    s = input("> ").strip()
    if s == "1":
        try:
            val = float(input("Seconds per char (0 for instant): ").strip())
        except Exception:
            val = 0.0
        val = max(0.0, min(0.05, val))
        dummy = SaveManager.load() or GameState()
        dummy.text_speed = val
        SaveManager.save(dummy)  # store preference for future sessions
        print("Saved default speed for future new games. (Current game unaffected.)")
        input("Enter")
    elif s == "2":
        dummy = SaveManager.load() or GameState()
        dummy.ascii_on = not dummy.ascii_on
        SaveManager.save(dummy)
        print(f"ASCII now {'ON' if dummy.ascii_on else 'OFF'} for future sessions.")
        input("Enter")

def challenges_menu():
    clear()
    print("CHALLENGES (practice minigames, no save):")
    print("1) Lockpick   2) Tunnel Shuffle   3) Guard Bluff   4) Back")
    c = input("> ").strip()
    rng = random.Random(42)
    gs = GameState()
    if c == "1":
        lockpick_puzzle(gs, training=True)
    elif c == "2":
        tunnel_shuffle(gs, rng, training=True)
    elif c == "3":
        guard_bluff(gs, rng, training=True)
    else:
        return
    input("Practice done. Enter.")

def pause_menu(gs: GameState) -> bool:
    print("\n[P]ause: 1) Save  2) Inventory  3) Help  4) Back to Menu (Quit)  5) Cancel")
    c = input("> ").strip()
    if c == "1":
        SaveManager.save(gs); notify(gs, "Game saved.")
    elif c == "2":
        show_inventory(gs)
    elif c == "3":
        help_screen()
    elif c == "4":
        confirm = input("Really quit to main menu? [y/N] ").strip().lower()
        if confirm == "y":
            if gs.flags.get("permadeath") and not gs.flags.get("escaped"):
                notify(gs, "Hardcore: unsaved progress will be lost.")
            return True
    return False

def show_inventory(gs: GameState):
    clear()
    print(Renderer.header(gs))
    print("INVENTORY:")
    if gs.inventory:
        for i, item in enumerate(gs.inventory, 1):
            print(f" {i}. {item}")
    else:
        print(" (empty)")
    print(f"\nScrap: {gs.scrap}   Keys: {gs.keys}")
    input("\nEnter to return.")

# ---------- Scenes ----------

def game_loop(gs: GameState):
    while True:
        clear()
        if gs.ascii_on: print(Renderer.scene(gs))
        print(Renderer.header(gs))
        if gs.flags.get("escaped"):
            end_screen(gs)
            input("Press Enter to return to menu.")
            return
        if gs.location == "cell":
            scene_cell(gs)
        elif gs.location == "workbench":
            scene_workbench(gs)
        elif gs.location == "sewer":
            scene_sewer(gs)
        elif gs.location == "yard_gate":
            scene_yard(gs)
        else:
            gs.location = "cell"

def scene_cell(gs: GameState):
    print("Actions: [wait] [search] [pushups] [move] [inv] [save] [p]ause")
    s = prompt(gs, "> ").lower()
    if s in ("p", "pause"):
        if pause_menu(gs): return
    elif s == "inv":
        show_inventory(gs)
    elif s == "save":
        SaveManager.save(gs); notify(gs, "Saved.")
    elif s == "wait":
        gs.day += 1
        delta = 1 + (1 if gs.difficulty=="Chill" else 0)
        gs.scrap += delta
        notify(gs, f"You bide time. +{delta} scrap from scrounging.")
        if gs.scrap >= 10 and not gs.unlocks["workbench"]:
            gs.unlocks["workbench"] = True
            notify(gs, "You discover a WORKBENCH behind a panel. [move -> workbench]")
            gs.add_progress(5, "Found a new area")
    elif s == "pushups":
        gs.day += 1
        gs.add_progress(1, "Discipline")
        notify(gs, "You strengthen resolve. Progress inches forward.")
    elif s == "search":
        gs.day += 1
        rng = gs.rng()
        found = rng.choice([0,1,1,2,3])
        gs.scrap += found
        notify(gs, f"You search cracks. +{found} scrap.")
        # Hidden verbs
    elif s == "xyzzy" and not gs.flags.get("xyzzy"):
        gs.flags["xyzzy"] = True; gs.keys += 1
        notify(gs, "A secret key materializes from thin air. (+1 key)")
    elif s == "look under bed" and not gs.flags.get("bed_loot"):
        gs.flags["bed_loot"] = True; gs.scrap += 5
        notify(gs, "A taped bundle! (+5 scrap)")
    elif s == "whistle":
        gs.flags["guard_hint"] = True
        notify(gs, "You catch a guard's rhythm… (useful at the yard.)")
    elif s.startswith("move"):
        dest = s.replace("move","").strip()
        if dest == "":
            print("Where? [workbench] [sewer] [yard]")
            dest = input("> ").strip().lower()
        if dest.startswith("work") and gs.unlocks["workbench"]:
            gs.location = "workbench"
        elif dest.startswith("sew") and gs.unlocks["sewer"]:
            gs.location = "sewer"
        elif dest.startswith("yard") and gs.unlocks["yard_gate"]:
            gs.location = "yard_gate"
        else:
            notify(gs, "That way is still blocked.")
    else:
        notify(gs, "Nothing happens.")

def scene_workbench(gs: GameState):
    print("Workbench: [craft lockpick] [move] [inv] [save] [p]")
    s = prompt(gs, "> ").lower()
    if s in ("p","pause"):
        if pause_menu(gs): return
    elif s == "inv":
        show_inventory(gs)
    elif s == "save":
        SaveManager.save(gs); notify(gs, "Saved.")
    elif s.startswith("craft"):
        if "lockpick" in gs.inventory:
            notify(gs, "You already crafted a lockpick.")
            return
        if gs.scrap < 10:
            notify(gs, "Need 10 scrap.")
            return
        ok = lockpick_puzzle(gs)
        if ok:
            gs.scrap -= 10
            gs.inventory.append("lockpick")
            gs.add_progress(10, "Lock opened")
            gs.unlocks["sewer"] = True
            notify(gs, "Cell door opens to a dank SEWER access.")
        else:
            notify(gs, "Pick snaps. Try again tomorrow.")
            gs.day += 1
    elif s.startswith("move"):
        print("Where? [cell] [sewer]")
        d = input("> ").strip().lower()
        if d.startswith("cell"):
            gs.location = "cell"
        elif d.startswith("sew") and gs.unlocks["sewer"]:
            gs.location = "sewer"
        else:
            notify(gs, "Blocked.")
    else:
        notify(gs, "You fiddle with junk, accomplishing little.")

def lockpick_puzzle(gs: GameState, training: bool=False) -> bool:
    rng = gs.rng()
    pin = rng.randint(1, 9)
    tries = {"Chill":4,"Standard":3,"Hardcore":2}[gs.difficulty]
    slow_print("Align the pins (1–9).", gs.text_speed)
    while tries > 0:
        s = input(f"Pin guess ({tries} tries): ").strip()
        if not s.isdigit(): print("…numbers only."); continue
        g = int(s)
        if g == pin:
            print("Click! The pin sets.")
            if not training: gs.day += 1
            return True
        tries -= 1
        if g < pin: print("Too low.")
        elif g > pin: print("Too high.")
    print("The tension wrench slips.")
    return False

def scene_sewer(gs: GameState):
    print("Sewer: [tunnel] [move] [inv] [save] [p]")
    s = prompt(gs, "> ").lower()
    if s in ("p","pause"):
        if pause_menu(gs): return
    elif s == "inv":
        show_inventory(gs)
    elif s == "save":
        SaveManager.save(gs); notify(gs, "Saved.")
    elif s == "tunnel":
        rng = gs.rng()
        loot, got_map = tunnel_shuffle(gs, rng)
        gs.scrap += loot
        if got_map: gs.flags["sewer_map"] = True
        if gs.progress < 50: gs.add_progress(10, "Found an exit route")
        gs.unlocks["yard_gate"] = True
        notify(gs, "You surface into the yard shadows. YARD GATE now accessible.")
        gs.location = "yard_gate"
    elif s.startswith("move"):
        d = input("Where? [cell] [workbench] [yard] ").strip().lower()
        if d.startswith("cell"):
            gs.location = "cell"
        elif d.startswith("work") and gs.unlocks["workbench"]:
            gs.location = "workbench"
        elif d.startswith("yard") and gs.unlocks["yard_gate"]:
            gs.location = "yard_gate"
        else:
            notify(gs, "No such path (yet).")
    else:
        notify(gs, "Rats squeak back at you.")

def tunnel_shuffle(gs: GameState, rng: random.Random, training: bool=False) -> Tuple[int,bool]:
    print("TUNNEL SHUFFLE: choose [left]/[right] 5 times. Traps/loot abound.")
    steps, loot, got_map = 5, 0, False
    for i in range(1, steps+1):
        choice = input(f"Step {i}/5: ").strip().lower()
        if choice not in ("left","right"): print("You hesitate and lose time."); continue
        roll = rng.random()
        if roll < 0.15:
            print("Rusty grate cuts you. You retreat. (-time)")
            if not training: gs.day += 1
        elif roll < 0.55:
            gain = rng.choice([1,1,2,3])
            loot += gain
            print(f"You find scrap! (+{gain})")
        elif roll < 0.70:
            print("You find a dropped KEY!")
            if not training: gs.keys += 1
        elif roll < 0.90 and not got_map:
            print("You notice repeating markings… (you memorize a MAP.)")
            got_map = True
        else:
            print("A quiet stretch. Nothing happens.")
    return loot, got_map

def scene_yard(gs: GameState):
    print("Yard Gate: [distract] [code] [move] [inv] [save] [p]")
    s = prompt(gs, "> ").lower()
    if s in ("p","pause"):
        if pause_menu(gs): return
    elif s == "inv":
        show_inventory(gs)
    elif s == "save":
        SaveManager.save(gs); notify(gs, "Saved.")
    elif s == "distract":
        rng = gs.rng()
        win = guard_bluff(gs, rng)
        if win:
            notify(gs, "Guard fooled. Window to act!")
            gs.add_progress(20, "Access to final lock")
        else:
            if gs.difficulty == "Hardcore":
                notify(gs, "Caught. Hardcore permadeath.")
                if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
                input("Game over. Enter.")
                menu_main()
                return
            notify(gs, "You are sent back to your cell.")
            gs.location = "cell"; gs.day += 1
    elif s == "code":
        success = code_lock(gs)
        if success:
            gs.add_progress(100 - gs.progress, "Freedom")
            gs.flags["escaped"] = True
        else:
            notify(gs, "Wrong code. Alarms chirp—back to the cell.")
            gs.location = "cell"; gs.day += 1
    elif s.startswith("move"):
        d = input("Where? [cell] [sewer] ").strip().lower()
        if d.startswith("cell"): gs.location = "cell"
        elif d.startswith("sew"): gs.location = "sewer"
    else:
        notify(gs, "The yard is tense; choose carefully.")

def guard_bluff(gs: GameState, rng: random.Random, training: bool=False) -> bool:
    print("GUARD BLUFF (win 2 of 3). Choose: [rock/paper/scissors]")
    score_p = score_g = 0
    bias = 0.1 if gs.flags.get("guard_hint") else 0.0
    mapping = ["rock","paper","scissors"]
    for rnd in range(3):
        you = input(f"Round {rnd+1}: ").strip().lower()
        if you not in mapping: print("Stammering counts as a loss."); score_g += 1; continue
        # Slight bias: guard more likely to lose if you whistled pattern
        if rng.random() < (0.34 + bias):
            guard = mapping[(mapping.index(you)+1)%3]  # guard picks losing move
        else:
            guard = rng.choice(mapping)
        print(f"Guard plays: {guard}")
        if you == guard: print("Tie.")
        elif (you, guard) in (("rock","scissors"),("paper","rock"),("scissors","paper")):
            print("You win this round.")
            score_p += 1
        else:
            print("Guard wins this round.")
            score_g += 1
    win = score_p >= 2
    if not training and win: gs.day += 1
    return win

def code_lock(gs: GameState) -> bool:
    rng = gs.rng()
    code = rng.randint(111, 999)
    hints = []
    if gs.flags.get("sewer_map"): hints.append("First digit is odd.")
    if gs.keys > 0: hints.append("You can reroll once by using a key.")
    print("FINAL LOCK: enter a 3-digit code.")
    if hints: print("Hints:", "; ".join(hints))
    attempt = input("Code: ").strip()
    if attempt == "use key" and gs.keys > 0:
        gs.keys -= 1
        code = rng.randint(111, 999)
        print("(The tumblers reset.)")
        attempt = input("Code: ").strip()
    if not attempt.isdigit(): return False
    return int(attempt) == code

def end_screen(gs: GameState):
    clear()
    if gs.ascii_on:
        print(r"""
     _________     ________________     _________
    /  ______/    /  ___/  _  \   \   /  / ____/
   /  /_____     /  /  /  /_\  \   \_/  /___
  /____   _/    /  /  /    |    \       \  _/ 
 /____/__/     /__/   \____|__  /\__/\__/_/   
                           \/                """)
    print(f"\nFreedom! {gs.player}, you escaped in {gs.day} days on {gs.difficulty}.")
    SaveManager.save(gs)

# ---------- Entry ----------

if __name__ == "__main__":
    try:
        menu_main()
    except KeyboardInterrupt:
        print("\nExiting... Bye.")
