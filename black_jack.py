import random
from main import (
  buy_idx_upgrade
  game.money
)


# ---------- Card + Deck logic ----------

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["♠", "♥", "♦", "♣"]  # Change to "S", "H", "D", "C" if your terminal has issues.

BLACKJACK_PAYOUT = 1.5  # 3:2 payout


def return_to_game(): 
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

def create_deck():
    """Return a shuffled 52-card deck."""
    deck = [(rank, suit) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def hand_value(hand):
    """Compute best blackjack value for a hand."""
    value = 0
    aces = 0
    for rank, suit in hand:
        if rank in ["J", "Q", "K"]:
            value += 10
        elif rank == "A":
            aces += 1
            value += 11  # initially count aces as 11
        else:
            value += int(rank)

    # Adjust aces from 11 to 1 if we bust
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1

    return value


# ---------- ASCII Art ----------

def card_ascii(card):
    """Return a list of strings representing one card as ASCII art."""
    if card is None:
        # Face-down card
        return [
            "┌─────────┐",
            "│░░░░░░░░░│",
            "│░░░░░░░░░│",
            "│░░░░░░░░░│",
            "│░░░░░░░░░│",
            "│░░░░░░░░░│",
            "└─────────┘",
        ]
    rank, suit = card
    rank_str_left = rank.ljust(2)
    rank_str_right = rank.rjust(2)
    return [
        "┌─────────┐",
        f"│{rank_str_left}       │",
        "│         │",
        f"│    {suit}    │",
        "│         │",
        f"│       {rank_str_right}│",
        "└─────────┘",
    ]


def join_cards(cards):
    """Take a list of cards and return a single multi-line string of them next to each other."""
    lines_per_card = [card_ascii(c) for c in cards]
    joined_lines = ["  ".join(line[i] for line in lines_per_card) for i in range(len(lines_per_card[0]))]
    return "\n".join(joined_lines)


def print_hand(label, hand, hide_first=False):
    """Print a hand with ASCII cards and total value (if not hidden)."""
    print(label)
    display_cards = []
    for i, c in enumerate(hand):
        if hide_first and i == 0:
            display_cards.append(None)
        else:
            display_cards.append(c)
    print(join_cards(display_cards))
    if not hide_first:
        print(f"Total: {hand_value(hand)}")
    print()


# ---------- Game Round (with betting) ----------

def play_round(bet):
    """
    Play one round of Blackjack with the given bet.
    Returns the net chip change (float): positive if player wins, negative if loses, 0 if push.
    """
    deck = create_deck()

    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]

    print("\n==============================")
    print(f"        NEW ROUND  (Bet: {bet})")
    print("==============================\n")

    # Check for natural blackjack first
    player_total = hand_value(player_hand)
    dealer_total = hand_value(dealer_hand)

    print_hand("Dealer's hand:", dealer_hand, hide_first=True)
    print_hand("Your hand:", player_hand)

    # Both Blackjack -> push
    if player_total == 21 and dealer_total == 21:
        print("Both you and the dealer have Blackjack. It's a push!\n")
        return 0.0

    # Player Blackjack only
    if player_total == 21:
        winnings = bet * BLACKJACK_PAYOUT
        print(f"Blackjack! You win {winnings} chips (3:2 payout).\n")
        return winnings

    # Dealer Blackjack only
    if dealer_total == 21:
        print_hand("Dealer's hand:", dealer_hand, hide_first=False)
        print(f"Dealer has Blackjack. You lose {bet} chips.\n")
        return -bet

    # Player turn
    while True:
        choice = input("Hit or Stand? [h/s] ").strip().lower()
        if choice not in ("h", "s"):
            print("Please type 'h' to hit or 's' to stand.")
            continue

        if choice == "h":
            player_hand.append(deck.pop())
            print()
            print_hand("Your hand:", player_hand)
            player_total = hand_value(player_hand)
            if player_total > 21:
                print(f"You bust! Dealer wins. You lose {bet} chips.\n")
                return -bet
        else:
            break

    # Dealer turn
    print("\nDealer reveals their hand:")
    print_hand("Dealer's hand:", dealer_hand, hide_first=False)

    while hand_value(dealer_hand) < 17:
        input("Dealer hits. Press Enter to continue...")
        dealer_hand.append(deck.pop())
        print_hand("Dealer's hand:", dealer_hand, hide_first=False)

    dealer_total = hand_value(dealer_hand)
    player_total = hand_value(player_hand)

    if dealer_total > 21:
        print(f"Dealer busts. You win {bet} chips!\n")
        return bet
    elif dealer_total > player_total:
        print(f"Dealer wins. You lose {bet} chips.\n")
        return -bet
    elif dealer_total < player_total:
        print(f"You win {bet} chips!\n")
        return bet
    else:
        print("It's a push (tie). No chips won or lost.\n")
        return 0.0


# ---------- UI + Main loop ----------

def print_title():
    title = r"""
 ____  _            _        _            _    
| __ )| | __ _  ___| | __   | |__   ___  | | __
|  _ \| |/ _` |/ __| |/ /   | '_ \ / _ \ | |/ /
| |_) | | (_| | (__|   < _  | |_) |  __/ |   < 
|____/|_|\__,_|\___|_|\_(_) |_.__/ \___| |_|\_\
                                              
          ASCII Blackjack (with betting)
    """
    print(title)


def get_starting_chips():
    while True:
        starting = input("Enter starting chips (default 100): ").strip()
        if starting == "":
            return 100.0
        try:
            val = float(starting)
            if val <= 0:
                print("Please enter a positive number.")
                continue
            return val
        except ValueError:
            print("Please enter a valid number.")


def get_bet(bankroll):
    while True:
        bet_str = input(f"Place your bet (1 - {int(bankroll)}): ").strip()
        try:
            bet = float(bet_str)
            if bet <= 0:
                print("Bet must be greater than 0.")
            elif bet > bankroll:
                print("You can't bet more than you have.")
            else:
                return bet
        except ValueError:
            print("Please enter a valid number.")


def main():
    print_title()
    print("Welcome to ASCII Blackjack with betting!")
    print("Try to get as close to 21 as possible without going over.")
    print("Dealer hits on 16 and stands on 17+.")
    print("Blackjack pays 3:2.\n")
    print("Press B To Return\n")

    bankroll = get_starting_chips()
    print(f"\nYou are starting with {bankroll:.2f} chips.\n")

    while True:
        if bankroll <= 0:
            print("You are out of chips. Game over!")
            break

        print(f"Current chips: {bankroll:.2f}")
        bet = get_bet(bankroll)

        net_change = play_round(bet)
        bankroll += net_change
        print(f"Chip change this round: {net_change:+.2f}")
        print(f"New total chips: {bankroll:.2f}\n")

        if bankroll <= 0:
            print("You have no chips left. The house wins this time.\n")
            break

        again = input("Play another round? [y/n] ").strip().lower()
        if again != "y":
            print("\nThanks for playing. Cashing you out with "
                  f"{bankroll:.2f} chips. Goodbye!")
            break


if __name__ == "__main__":
    main()
