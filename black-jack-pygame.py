import pygame
from sys import exit
import random
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

GAME_WIDTH = 600
GAME_HEIGHT = 600
CARD_WIDTH = 110
CARD_HEIGHT = 154
CARD_SPACING = 5

VALUES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = {"C": ("Трефы", "♣"), "D": ("Бубны", "♦"), "H": ("Червы", "♥"), "S": ("Пики", "♠")}
RANKS = [
    ("A", "Туз", 11), ("2", "2", 2), ("3", "3", 3), ("4", "4", 4), ("5", "5", 5),
    ("6", "6", 6), ("7", "7", 7), ("8", "8", 8), ("9", "9", 9), ("10", "10", 10),
    ("J", "Валет", 10), ("Q", "Дама", 10), ("K", "Король", 10)
]

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "blackjack.db"

def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def initialize_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT NOT NULL, 
                rank TEXT NOT NULL, 
                suit TEXT NOT NULL, 
                value INTEGER NOT NULL CHECK(value BETWEEN 1 AND 21), 
                image TEXT NOT NULL DEFAULT '', 
                is_custom INTEGER NOT NULL DEFAULT 0
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                player_score INTEGER NOT NULL, 
                dealer_score INTEGER NOT NULL, 
                result TEXT NOT NULL, 
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
        """)

        if db.execute("SELECT COUNT(*) FROM cards WHERE is_custom=0").fetchone()[0] == 0:
            for suit, (suit_name, _) in SUITS.items():
                for rank, rank_name, value in RANKS:
                    db.execute(
                        "INSERT INTO cards(name, rank, suit, value, image, is_custom) VALUES(?, ?, ?, ?, ?, 0)",
                        (f"{rank_name} {suit_name.lower()}", rank, suit, value, f"cards/{rank}-{suit}.png")
                    )
            db.commit()

def open_search_window():
    root = tk.Tk()
    root.title("Поиск карт в БД")
    root.geometry("400x350")

    tk.Label(root, text="Введите название карты (например, 'Туз' или 'пики'):").pack(pady=5)
    search_entry = tk.Entry(root, width=30)
    search_entry.pack(pady=5)

    columns = ("name", "value")
    tree = ttk.Treeview(root, columns=columns, show="headings", height=8)
    tree.heading("name", text="Название карты")
    tree.heading("value", text="Очки")
    tree.pack(pady=10, fill=tk.BOTH, expand=True)

    def search():
        for row in tree.get_children():
            tree.delete(row)

        query = search_entry.get().strip()
        with connect_db() as db:
            rows = db.execute("SELECT name, value FROM cards WHERE name LIKE ?", (f"%{query}%",)).fetchall()
            for row in rows:
                tree.insert("", tk.END, values=(row["name"], row["value"]))

    search_button = tk.Button(root, text="Искать", command=search)
    search_button.pack(pady=5)

    search()
    root.mainloop()


class Card:
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
        try:
            self.image = pygame.image.load(f"cards/{value}-{suit}.png")
        except pygame.error:
            self.image = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
            self.image.fill((255, 255, 255))
        self.image = pygame.transform.smoothscale(self.image, (CARD_WIDTH, CARD_HEIGHT))

    def __repr__(self):
        return f"{self.value}-{self.suit}"

    def get_value(self):
        if self.value == "A":
            return 11
        if self.value in ["J", "Q", "K"]:
            return 10
        return int(self.value)


class Player:
    def __init__(self):
        self.hand = []
        self.sum = 0
        self.ace_count = 0

    def add_card(self, card):
        self.hand.append(card)
        self.sum += card.get_value()
        if card.value == "A":
            self.ace_count += 1

    def get_total(self):
        total = self.sum
        aces = self.ace_count
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total


def start_game():
    global deck, dealer, player, hidden_card, game_over, message
    game_over = False
    message = ""
    deck = [Card(value, suit) for suit in SUITS for value in VALUES]
    random.shuffle(deck)

    dealer = Player()
    player = Player()

    hidden_card = deck.pop()
    dealer.add_card(hidden_card)
    dealer.add_card(deck.pop())

    player.add_card(deck.pop())
    player.add_card(deck.pop())


def save_game_result(p_score, d_score, res):
    with connect_db() as db:
        db.execute("INSERT INTO games (player_score, dealer_score, result) VALUES (?, ?, ?)",
                   (p_score, d_score, res))
        db.commit()


def hit():
    if game_over:
        return
    player.add_card(deck.pop())
    if player.get_total() > 21:
        stay()


def stay():
    global game_over, message
    if game_over:
        return

    while dealer.get_total() < 17:
        dealer.add_card(deck.pop())

    dealer_total = dealer.get_total()
    player_total = player.get_total()

    if player_total > 21:
        message = "Вы проиграли (Перебор)"
        res_db = "Луз"
    elif dealer_total > 21 or player_total > dealer_total:
        message = "Вы выиграли!"
        res_db = "Вин"
    elif player_total == dealer_total:
        message = "Ничья"
        res_db = "Ничья"
    else:
        message = "Вы проиграли"
        res_db = "Луз"

    game_over = True
    save_game_result(player_total, dealer_total, res_db)


initialize_db()
pygame.init()
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Black Jack")
clock = pygame.time.Clock()

try:
    back_image = pygame.image.load("cards/BACK.png")
except pygame.error:
    back_image = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    back_image.fill((128, 0, 0))
back_image = pygame.transform.smoothscale(back_image, (CARD_WIDTH, CARD_HEIGHT))

font = pygame.font.SysFont("Arial", 24)
big_font = pygame.font.SysFont("Arial", 36, bold=True)

start_game()


def draw():
    window.fill((53, 101, 77))

    if game_over:
        window.blit(hidden_card.image, (20, 20))
        dealer_text = f"Дилер: {dealer.get_total()}"
    else:
        window.blit(back_image, (20, 20))
        visible_score = dealer.get_total() - hidden_card.get_value()
        dealer_text = f"Дилер: {visible_score} + ?"

    for i in range(1, len(dealer.hand)):
        card = dealer.hand[i]
        x = 20 + (CARD_WIDTH + CARD_SPACING) * i
        window.blit(card.image, (x, 20))

    lbl_dealer = font.render(dealer_text, True, "white")
    window.blit(lbl_dealer, (20, 185))

    for i in range(len(player.hand)):
        card = player.hand[i]
        x = 20 + (CARD_WIDTH + CARD_SPACING) * i
        window.blit(card.image, (x, 250))

    lbl_player = font.render(f"Игрок: {player.get_total()}", True, "white")
    window.blit(lbl_player, (20, 415))

    controls = font.render('Z = Взять | X = Стоять | C = Заново | V = Поиск БД', True, "#e6bd66")
    window.blit(controls, (40, 550))

    if game_over:
        result_text = big_font.render(message, True, "white")
        text_rect = result_text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 2 + 120))
        window.blit(result_text, text_rect)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z:
                hit()
            elif event.key == pygame.K_x:
                stay()
            elif event.key == pygame.K_c:
                start_game()
            elif event.key == pygame.K_v:
                open_search_window()

    draw()
    pygame.display.update()
    clock.tick(60)
