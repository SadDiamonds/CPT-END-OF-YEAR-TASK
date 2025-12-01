BASE_MONEY_GAIN = 1.0
BASE_WORK_DELAY = 6.7
BASE_MONEY_MULT = 1.0

CURRENCY_SYMBOL = "¤"
STABILITY_CURRENCY_NAME = "Stability Sparks"
STABILITY_REWARD_MULT = 0.4
STABILITY_REWARD_EXP = 0.42

WAKE_TIMER_START = 90
WAKE_TIMER_UPGRADES = [
    {
        "id": "wake_console",
        "name": "Power Relay",
        "cost": 5,
        "time_bonus": 0,
        "unlock_upgrades": True,
        "desc": "Unlocks upgrades",
    },
    {
        "id": "wake_breath",
        "name": "Steady Breath",
        "cost": 80,
        "time_bonus": 60,
        "desc": "Adds one precious minute before collapse.",
    },
    {
        "id": "wake_anchor",
        "name": "Anchor Points",
        "cost": 320,
        "time_bonus": 180,
        "desc": "Tether the loop, +3 minutes.",
    },
    {
        "id": "wake_lock",
        "name": "Phase Lock",
        "cost": 1400,
        "time_bonus": 0,
        "grant_infinite": True,
        "desc": "Seal the breach and stop the timer forever.",
    },
]

LAYER_FLOW = [
    {
        "id": 0,
        "key": "wake",
        "name": "Desk",
        "currency_name": "Clicks",
        "currency_suffix": "Cl",
        "storage_key": "money",
        "unlock_money": 0,
        "border_id": 0,
        "desc": "The desk hums with angles that do not meet.",
    },
    {
        "id": 1,
        "key": "corridor",
        "name": "Hall",
        "currency_name": "Marks",
        "currency_suffix": "Mk",
        "storage_key": "inspiration",
        "unlock_money": 100_000,
        "border_id": 1,
        "desc": "Footsteps echo a beat before you take them.",
    },
    {
        "id": 2,
        "key": "archive",
        "name": "Stacks",
        "currency_name": "Threads",
        "currency_suffix": "Th",
        "storage_key": "concepts",
        "unlock_money": 100_000_000,
        "border_id": 2,
        "desc": "Shelves lean away from your gaze, hiding spines.",
    },
    {
        "id": 3,
        "key": "dreamwalk",
        "name": "Dreamtrail",
        "currency_name": "Pulse",
        "currency_suffix": "Pu",
        "storage_key": "pulses",
        "unlock_money": 5_000_000_000_000,
        "border_id": 3,
        "desc": "Dreams run parallel until you step across.",
    },
    {
        "id": 4,
        "key": "persona",
        "name": "Maskroom",
        "currency_name": "Veil",
        "currency_suffix": "Ve",
        "storage_key": "veils",
        "unlock_money": 10**18,
        "border_id": 4,
        "desc": "Masks decide which version of you answers.",
    },
    {
        "id": 5,
        "key": "threshold",
        "name": "Gate",
        "currency_name": "Seal",
        "currency_suffix": "Se",
        "storage_key": "sigils",
        "unlock_money": 10**24,
        "border_id": 4,
        "desc": "Beyond the arch the watcher finally notices.",
    },
]

LAYER_BY_KEY = {entry["key"]: entry for entry in LAYER_FLOW}
LAYER_BY_ID = {entry["id"]: entry for entry in LAYER_FLOW}

FOCUS_BOOST_FACTOR = 0.5
FOCUS_DURATION = 12
FOCUS_CHARGE_PER_EARN = 12
FOCUS_MAX = 100

INSPIRATION_UNLOCK_MONEY = LAYER_BY_KEY["corridor"]["unlock_money"]
CONCEPTS_UNLOCK_MONEY = LAYER_BY_KEY["archive"]["unlock_money"]

MOTIVATION_MAX = 100
MAX_MOTIVATION_MULT = 3.0

STEAM_SPEED = 0.1
STEAM_CHANCE = 0.2
STEAM_SPREAD = 3
STEAM_LIFETIME = 8
STEAM_CHARS = ["~", "^", "."]
CAFFEINE_POINT_RATE = 1

MIN_BOX_WIDTH = 50
BOX_MARGIN = 4

UPGRADES = [
    {
        "id": "keyboard",
        "name": "Basic Keyboard",
        "cost": 45,
        "type": "mult",
        "base_value": 1.35,
        "value_mult": 1.18,
        "max_level": 5,
        "cost_mult": 1.85,
        "desc": "Calibrate your fingers. 1.35x base, +18% per level",
        "unlocked": True,
    },
    {
        "id": "coffee",
        "name": "Coffee",
        "cost": 160,
        "type": "reduce_delay",
        "base_value": 0.965,
        "value_mult": 0.95,
        "max_level": 3,
        "cost_mult": 2.2,
        "desc": "Keep the loop awake. -3.5% auto delay, -5% per level",
        "unlocked": False,
    },
    {
        "id": "cup_holder",
        "name": "Cup Holder",
        "cost": 260,
        "type": "add",
        "base_value": 4.0,
        "max_level": 1,
        "cost_mult": 3.0,
        "desc": "Makes space for rituals. +4 income",
        "unlocked": False,
    },
    {
        "id": "monitor",
        "name": "Dusty Monitor",
        "cost": 520,
        "type": "add",
        "base_value": 6,
        "value_mult": 1.4,
        "max_level": 4,
        "cost_mult": 2.2,
        "desc": "Shaky pixels, steady gains. +6 base, +40% per level",
        "unlocked": False,
    },
    {
        "id": "ergonomic_chair",
        "name": "Ergonomic Chair",
        "cost": 950,
        "type": "mult",
        "base_value": 1.28,
        "value_mult": 1.22,
        "max_level": 3,
        "cost_mult": 2.3,
        "desc": "Spine remembers. 1.28x base, +22% per level",
        "unlocked": False,
    },
    {
        "id": "dual_monitors",
        "name": "Dual Monitors",
        "cost": 1800,
        "type": "add",
        "base_value": 14.0,
        "value_mult": 1.45,
        "max_level": 3,
        "cost_mult": 2.35,
        "desc": "Mirrored horizons. +14 income, +45% per level",
        "unlocked": False,
    },
    {
        "id": "mech_keyboard",
        "name": "Mechanical Keyboard",
        "cost": 3600,
        "type": "mult",
        "base_value": 1.6,
        "value_mult": 1.24,
        "max_level": 4,
        "cost_mult": 2.6,
        "desc": "Reality clicks louder. 1.6x base, +24% per level",
        "unlocked": False,
    },
    {
        "id": "lamp",
        "name": "Desk Lamp",
        "cost": 5400,
        "type": "reduce_delay",
        "base_value": 0.93,
        "value_mult": 0.94,
        "max_level": 4,
        "cost_mult": 2.6,
        "unlocked": False,
    },
    {
        "id": "whiteboard",
        "name": "Whiteboard",
        "cost": 8200,
        "type": "add",
        "base_value": 32.0,
        "value_mult": 1.4,
        "max_level": 5,
        "cost_mult": 3.0,
        "unlocked": False,
    },
]

UPGRADE_DEPENDENCIES = {
    "coffee": ["keyboard"],
    "cup_holder": ["keyboard"],
    "monitor": ["keyboard"],
    "ergonomic_chair": ["cup_holder"],
    "dual_monitors": ["monitor"],
    "mech_keyboard": ["keyboard"],
    "lamp": ["monitor"],
    "whiteboard": ["lamp"],
}

INSPIRE_UPGRADES = [
    {
        "id": "inspire_motiv",
        "name": "Motivation",
        "cost": 1,
        "type": "unlock_motivation",
        "value": 1,
        "max_level": 1,
        "cost_mult": 1.3,
        "desc": "Unlocks Motivation (buff that decays over work)",
    },
    {
        "id": "inspire_efficiency",
        "name": "Efficient Worker",
        "base_cost": 2,
        "type": "money_mult",
        "max_level": 10,
        "cost_mult": 1.75,
        "base_value": 1.25,
        "value_mult": 1.15,
        "desc": "×1.25 base, +15% per level",
    },
    {
        "id": "inspire_focus_cap",
        "name": "Mindspace",
        "base_cost": 5,
        "type": "focus_max",
        "max_level": 3,
        "cost_mult": 2.0,
        "value": 100,
        "desc": "+100 Focus cap per level",
    },
    {
        "id": "inspire_scaling",
        "name": "Creative Momentum",
        "base_cost": 10,
        "type": "money_mult",
        "max_level": 8,
        "cost_mult": 1.9,
        "base_value": 1.2,
        "value_mult": 1.12,
        "desc": "Stacking income boost",
    },
    {
        "id": "ip_rate",
        "name": "Insight Flow",
        "base_cost": 15,
        "type": "inspire_rate",
        "max_level": 6,
        "cost_mult": 2.2,
        "base_value": 1.5,
        "value_mult": 1.12,
        "desc": "×1.5 Inspiration gain, +12% per level",
    },
]

CONCEPT_UPGRADES = [
    {
        "id": "concept_autowork",
        "name": "Auto‑Work",
        "cost": 1,
        "type": "unlock_autowork",
        "value": 1,
        "max_level": 1,
        "cost_mult": 1.3,
        "desc": "Unlocks automatic work cycles",
    },
    {
        "id": "concept_autospeed",
        "name": "Automation Speed",
        "base_cost": 5,
        "type": "work_mult",
        "max_level": 10,
        "cost_mult": 2.0,
        "base_value": 0.95,
        "value_mult": 0.95,
        "desc": "Reduces auto‑work delay",
    },
    {
        "id": "concept_autoeff",
        "name": "Automation Efficiency",
        "base_cost": 10,
        "type": "auto_money_mult",
        "max_level": 10,
        "cost_mult": 2.0,
        "base_value": 1.2,
        "value_mult": 1.1,
        "desc": "Boosts auto‑work money gain",
    },
    {
        "id": "concept_rate",
        "name": "Conceptual Drift",
        "base_cost": 20,
        "type": "concept_rate",
        "max_level": 6,
        "cost_mult": 2.2,
        "base_value": 1.5,
        "value_mult": 1.12,
        "desc": "×1.5 Co gain, +12% per level",
    },
    {
        "id": "concept_mastery",
        "name": "Eureka",
        "base_cost": 25,
        "type": "money_mult",
        "max_level": 8,
        "cost_mult": 2.3,
        "base_value": 1.3,
        "value_mult": 1.15,
        "desc": "BIG x¤ boost",
    },
]

CHARGE_THRESHOLDS = [
    {"amount": 0, "reward_type": "x¤", "reward_value": 1.1},
    {"amount": 500, "reward_type": "x¤", "reward_value": 1.2},
]

BATTERY_TIERS = {
    1: {"cap": 1000, "rows": 5},
    2: {"cap": 100000, "rows": 10},
    3: {"cap": 10000000, "rows": 15},
}

BORDERS = {
    0: {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"},
    1: {"tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│"},
    2: {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
    3: {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"},
    4: {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "║"},
}

LAYER2_PARTICLE_CHARS = ["·", "*", ".", "'"]
LAYER2_PARTICLE_COUNT = 3
LAYER2_PARTICLE_AMPLITUDE = 12
LAYER2_PARTICLE_FREQ = 3


def format_number(n):
    neg = n < 0
    n = abs(n)

    suffixes = [
        (10**303, "e303"),
        (10**300, "e300"),
        (10**297, "e297"),
        (10**294, "e294"),
        (10**291, "e291"),
        (10**288, "e288"),
        (10**285, "e285"),
        (10**282, "e282"),
        (10**279, "e279"),
        (10**276, "e276"),
        (10**273, "e273"),
        (10**270, "e270"),
        (10**267, "e267"),
        (10**264, "e264"),
        (10**261, "e261"),
        (10**258, "e258"),
        (10**255, "e255"),
        (10**252, "e252"),
        (10**249, "e249"),
        (10**246, "e246"),
        (10**243, "e243"),
        (10**240, "e240"),
        (10**237, "e237"),
        (10**234, "e234"),
        (10**231, "e231"),
        (10**228, "e228"),
        (10**225, "e225"),
        (10**222, "e222"),
        (10**219, "e219"),
        (10**216, "e216"),
        (10**213, "e213"),
        (10**210, "e210"),
        (10**207, "e207"),
        (10**204, "e204"),
        (10**201, "e201"),
        (10**198, "e198"),
        (10**195, "e195"),
        (10**192, "e192"),
        (10**189, "e189"),
        (10**186, "e186"),
        (10**183, "e183"),
        (10**180, "e180"),
        (10**177, "e177"),
        (10**174, "e174"),
        (10**171, "e171"),
        (10**168, "e168"),
        (10**165, "e165"),
        (10**162, "e162"),
        (10**159, "e159"),
        (10**156, "e156"),
        (10**153, "e153"),
        (10**150, "e150"),
        (10**147, "e147"),
        (10**144, "e144"),
        (10**141, "e141"),
        (10**138, "e138"),
        (10**135, "e135"),
        (10**132, "e132"),
        (10**129, "e129"),
        (10**126, "e126"),
        (10**123, "e123"),
        (10**120, "e120"),
        (10**117, "e117"),
        (10**114, "e114"),
        (10**111, "e111"),
        (10**108, "e108"),
        (10**105, "e105"),
        (10**102, "e102"),
        (10**99, "e99"),
        (10**96, "e96"),
        (10**93, "e93"),
        (10**90, "e90"),
        (10**87, "e87"),
        (10**84, "e84"),
        (10**81, "e81"),
        (10**78, "e78"),
        (10**75, "e75"),
        (10**72, "e72"),
        (10**69, "e69"),
        (10**66, "e66"),
        (10**63, "e63"),
        (10**60, "e60"),
        (10**57, "e57"),
        (10**54, "e54"),
        (10**51, "e51"),
        (10**48, "e48"),
        (10**45, "e45"),
        (10**42, "e42"),
        (10**39, "e39"),
        (10**36, "e36"),
        (10**33, "De"),
        (10**30, "No"),
        (10**27, "Oc"),
        (10**24, "Sp"),
        (10**21, "Sx"),
        (10**18, "Qn"),
        (10**15, "Qd"),
        (10**12, "T"),
        (10**9, "B"),
        (10**6, "M"),
        (10**3, "K"),
    ]

    for value, symbol in suffixes:
        if n >= value:
            s = f"{n / value:.2f}".rstrip("0").rstrip(".")
            return f"-{s}{symbol}" if neg else f"{s}{symbol}"

    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"-{s}" if neg else s


AUTO_BALANCE_UPGRADES = True
BALANCE_DELTA = 0.3
BALANCE_MIN_MULT = 1.07
BALANCE_MAX_MULT = 5.0
PRINT_BALANCE_CHANGES = False

BALANCE_ADJUSTMENTS = []


def _normalize_upgrade_costs():
    if not AUTO_BALANCE_UPGRADES:
        return

    def effect_strength_for(u):
        try:
            vm = u.get("value_mult")
            if vm is not None:
                f = float(vm)
                return f if f >= 1.0 else (1.0 / f if f > 0 else 1.0)
        except Exception:
            pass

        for key in ("base_value", "value"):
            if key in u:
                try:
                    f = float(u[key])
                    if u.get("type") in ("add", "value"):
                        denom = max(1.0, BASE_MONEY_GAIN)
                        return max(1.0, 1.0 + (f / denom))
                    if u.get("type") in ("work_mult", "reduce_delay"):
                        return f if f >= 1.0 else (1.0 / f if f > 0 else 1.0)
                    return f if f >= 1.0 else 1.0
                except Exception:
                    pass
        return 1.0

    def ensure_list(lst, table_name):
        adjustments = []
        for u in lst:
            try:
                strength = effect_strength_for(u)
                desired = round(
                    max(
                        BALANCE_MIN_MULT,
                        min(BALANCE_MAX_MULT, strength + BALANCE_DELTA),
                    ),
                    2,
                )
                cur = float(u.get("cost_mult", desired))
                if cur < desired:
                    u["cost_mult"] = desired
                    adjustments.append((u.get("id"), cur, desired))
            except Exception:
                continue
        if adjustments:
            BALANCE_ADJUSTMENTS.extend(
                [(table_name, aid, old, new) for (aid, old, new) in adjustments]
            )
        if PRINT_BALANCE_CHANGES and adjustments:
            print(f"[BALANCE] Adjusted cost_mult in {table_name}:")
            for aid, old, new in adjustments:
                print(f"  {aid}: {old} -> {new}")

    ensure_list(UPGRADES, "UPGRADES")
    ensure_list(INSPIRE_UPGRADES, "INSPIRE_UPGRADES")
    ensure_list(CONCEPT_UPGRADES, "CONCEPT_UPGRADES")


_normalize_upgrade_costs()
