import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QGridLayout, QMessageBox, 
    QProgressBar, QScrollArea, QGroupBox, QFrame
)
from PyQt5.QtGui import QFont, QColor, QPalette
from PyQt5.QtCore import Qt
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum

class PlayAction(Enum):
    HIT = "Pedir"
    STAND = "Plantarse" 
    DOUBLE = "Doblar"
    SPLIT = "Dividir"
    SURRENDER = "Rendirse"

class GameResult(Enum):
    WIN = "Ganada"
    LOSE = "Perdida"
    PUSH = "Empate"
    PENDING = "En juego"

@dataclass
class GameState:
    player_cards: List[str]
    dealer_card: str
    dealer_hidden_card: str  # Nueva: carta oculta del crupier
    table_cards: List[str]
    num_decks: int
    running_count: int
    true_count: float
    decks_remaining: float

@dataclass
class SessionStats:
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    total_hands: int = 0
    
    @property
    def win_percentage(self) -> float:
        if self.total_hands == 0:
            return 0.0
        return (self.wins / self.total_hands) * 100

class BlackjackStrategy:
    """Implementación completa de estrategia básica de blackjack"""
    
    HARD_STRATEGY = {
        **{(i, j): PlayAction.HIT for i in range(5, 12) for j in range(2, 12)},
        **{(12, j): PlayAction.STAND if 4 <= j <= 6 else PlayAction.HIT for j in range(2, 12)},
        **{(i, j): PlayAction.STAND if 2 <= j <= 6 else PlayAction.HIT for i in range(13, 17) for j in range(2, 12)},
        **{(i, j): PlayAction.STAND for i in range(17, 22) for j in range(2, 12)},
    }
    
    SOFT_STRATEGY = {
        **{(i, j): PlayAction.HIT if j >= 7 else PlayAction.DOUBLE for i in range(13, 18) for j in range(2, 12)},
        **{(18, j): PlayAction.STAND if j in [2,7,8] else PlayAction.DOUBLE if 3 <= j <= 6 else PlayAction.HIT for j in range(2, 12)},
        **{(i, j): PlayAction.STAND for i in range(19, 22) for j in range(2, 12)},
    }

    @staticmethod
    def get_card_value(card: str) -> int:
        if card in ['J', 'Q', 'K']:
            return 10
        elif card == 'A':
            return 11
        else:
            return int(card)

    @staticmethod 
    def calculate_hand_value(cards: List[str]) -> Tuple[int, bool]:
        total = 0
        aces = 0
        
        for card in cards:
            if card == 'A':
                aces += 1
                total += 11
            else:
                total += BlackjackStrategy.get_card_value(card)
        
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
            
        is_soft = aces > 0 and total <= 21
        return total, is_soft

    @staticmethod
    def determine_winner(player_cards: List[str], dealer_cards: List[str]) -> GameResult:
        """Determina el ganador de la mano"""
        if not player_cards or not dealer_cards:
            return GameResult.PENDING
            
        player_total, _ = BlackjackStrategy.calculate_hand_value(player_cards)
        dealer_total, _ = BlackjackStrategy.calculate_hand_value(dealer_cards)
        
        # Player busted
        if player_total > 21:
            return GameResult.LOSE
            
        # Dealer busted, player didn't
        if dealer_total > 21:
            return GameResult.WIN
            
        # Both have blackjack
        player_bj = len(player_cards) == 2 and player_total == 21
        dealer_bj = len(dealer_cards) == 2 and dealer_total == 21
        
        if player_bj and dealer_bj:
            return GameResult.PUSH
        elif player_bj and not dealer_bj:
            return GameResult.WIN
        elif dealer_bj and not player_bj:
            return GameResult.LOSE
            
        # Compare totals
        if player_total > dealer_total:
            return GameResult.WIN
        elif dealer_total > player_total:
            return GameResult.LOSE
        else:
            return GameResult.PUSH

    @classmethod
    def get_optimal_play(cls, player_cards: List[str], dealer_card: str, 
                        true_count: float = 0, can_double: bool = True, 
                        can_split: bool = True) -> Tuple[PlayAction, str]:
        
        if not player_cards:
            return PlayAction.HIT, "Necesitas cartas para jugar"
            
        player_total, is_soft = cls.calculate_hand_value(player_cards)
        dealer_value = cls.get_card_value(dealer_card) if dealer_card != 'A' else 11
        
        # Manos hard
        key = (player_total, dealer_value)
        if key in cls.HARD_STRATEGY:
            action = cls.HARD_STRATEGY[key]
            if action == PlayAction.DOUBLE and not can_double:
                action = PlayAction.HIT
                
            # Ajustes basados en true count
            if true_count >= 2:
                if player_total == 16 and dealer_value == 10:
                    action = PlayAction.STAND
                elif player_total == 15 and dealer_value == 10:
                    action = PlayAction.STAND
                    
            return action, f"Mano hard {player_total}: {action.value}"
        
        # Fallback
        if player_total >= 17:
            return PlayAction.STAND, "Mano alta, plantarse"
        return PlayAction.HIT, "Pedir carta"

class CardCountingEngine:
    HI_LO_VALUES = {
        '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
        '7': 0, '8': 0, '9': 0,
        '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
    }
    
    @classmethod
    def calculate_counts(cls, all_cards: List[str], num_decks: int) -> Tuple[int, float, float]:
        running_count = sum(cls.HI_LO_VALUES.get(card, 0) for card in all_cards)
        cards_dealt = len(all_cards)
        decks_remaining = max(0.5, num_decks - (cards_dealt / 52.0))
        true_count = running_count / decks_remaining
        
        return running_count, round(true_count, 2), round(decks_remaining, 2)
    
    @staticmethod
    def get_betting_advantage(true_count: float) -> Tuple[str, str]:
        if true_count >= 3:
            return "Alta", "green"
        elif true_count >= 1:
            return "Media", "orange" 
        elif true_count <= -2:
            return "Muy Baja", "red"
        else:
            return "Neutra", "gray"

class EnhancedCardButton(QPushButton):
    def __init__(self, label: str, main_ui_reference, parent=None):
        super().__init__(label, parent)
        self.card_label = label
        self.main_ui = main_ui_reference
        self.selected_count = 0
        self.max_count = 4
        self.setFixedSize(60, 80)
        self.setFont(QFont("Arial", 12, QFont.Bold))
        self.setup_style()
        self.update_display()
        
    def setup_style(self):
        self.setStyleSheet("""
            QPushButton {
                border: 2px solid #333;
                border-radius: 8px;
                background-color: white;
                color: black;
            }
            QPushButton:hover {
                border-color: #0066cc;
                background-color: #f0f8ff;
            }
        """)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.selected_count < self.max_count:
                self.selected_count += 1
        elif event.button() == Qt.RightButton:
            if self.selected_count > 0:
                self.selected_count -= 1
        
        self.update_display()
        if self.main_ui:
            self.main_ui.update_analysis()
        
    def update_display(self):
        text = f"{self.card_label}"
        if self.selected_count > 0:
            text += f"\n({self.selected_count})"
            
        self.setText(text)
        
        if self.selected_count == 0:
            color = "white"
        elif self.selected_count <= 2:
            color = "#90EE90"
        elif self.selected_count == 3:
            color = "#FFD700"
        else:
            color = "#FF6B6B"
            
        self.setStyleSheet(f"""
            QPushButton {{
                border: 2px solid #333;
                border-radius: 8px;
                background-color: {color};
                color: black;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: #0066cc;
                opacity: 0.8;
            }}
        """)
        
    def reset(self):
        self.selected_count = 0
        self.update_display()
        
    def get_selected_cards(self) -> List[str]:
        return [self.card_label] * self.selected_count
        
    def add_cards(self, count: int):
        """Agrega cartas al contador (para función de terminar partida)"""
        self.selected_count = min(self.selected_count + count, self.max_count)
        self.update_display()

class BlackjackPremiumUI(QMainWindow):
    CARD_LABELS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blackjack Premium - Análisis Estratégico Avanzado")
        self.setMinimumSize(1200, 800)
        
        # Estado del juego
        self.game_state = GameState([], "", "", [], 6, 0, 0.0, 6.0)
        self.session_stats = SessionStats()
        
        # Componentes UI
        self.dealer_combo = None
        self.dealer_hidden_combo = None
        self.decks_combo = None
        self.player_buttons = []
        self.table_buttons = []
        self.info_panel = None
        self.advantage_bar = None
        self.stats_label = None
        
        self.setup_ui()
        self.setup_tooltips()
        self.reset_game()
        
    def setup_ui(self):
        central = QWidget()
        main_layout = QHBoxLayout()
        
        # Panel izquierdo - Controles
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Panel derecho - Análisis
        right_panel = self.create_analysis_panel()
        main_layout.addWidget(right_panel, 1)
        
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        
    def create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("🃏 Blackjack Strategy Analyzer")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Estadísticas de sesión
        stats_group = QGroupBox("📊 Estadísticas de Sesión")
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Arial", 10))
        self.stats_label.setStyleSheet("QLabel { background: #e8f5e8; padding: 10px; border-radius: 5px; }")
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Configuración del juego
        config_group = QGroupBox("Configuración del Juego")
        config_layout = QVBoxLayout()
        
        # Número de barajas
        deck_layout = QHBoxLayout()
        deck_layout.addWidget(QLabel("Número de barajas:"))
        self.decks_combo = QComboBox()
        self.decks_combo.addItems([str(i) for i in range(1, 9)])
        self.decks_combo.setCurrentText("6")
        self.decks_combo.currentTextChanged.connect(self.on_decks_changed)
        deck_layout.addWidget(self.decks_combo)
        config_layout.addLayout(deck_layout)
        
        # Carta visible del dealer
        dealer_layout = QHBoxLayout()
        dealer_layout.addWidget(QLabel("Carta visible del crupier:"))
        self.dealer_combo = QComboBox()
        self.dealer_combo.addItems([""] + self.CARD_LABELS)
        self.dealer_combo.currentTextChanged.connect(self.update_analysis)
        dealer_layout.addWidget(self.dealer_combo)
        config_layout.addLayout(dealer_layout)
        
        # Carta oculta del dealer (para terminar partida)
        hidden_layout = QHBoxLayout()
        hidden_layout.addWidget(QLabel("Carta oculta del crupier:"))
        self.dealer_hidden_combo = QComboBox()
        self.dealer_hidden_combo.addItems([""] + self.CARD_LABELS)
        hidden_layout.addWidget(self.dealer_hidden_combo)
        config_layout.addLayout(hidden_layout)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Cartas del jugador
        player_group = QGroupBox("Tus Cartas (Click izq: +1, Click der: -1)")
        player_layout = QGridLayout()
        self.player_buttons = []
        
        for i, label in enumerate(self.CARD_LABELS):
            btn = EnhancedCardButton(label, self, player_group)
            self.player_buttons.append(btn)
            player_layout.addWidget(btn, i // 7, i % 7)
            
        player_group.setLayout(player_layout)
        layout.addWidget(player_group)
        
        # Cartas de la mesa
        table_group = QGroupBox("Cartas Visibles en Mesa/Otros Jugadores")
        table_layout = QGridLayout()
        self.table_buttons = []
        
        for i, label in enumerate(self.CARD_LABELS):
            btn = EnhancedCardButton(label, self, table_group)
            self.table_buttons.append(btn)
            table_layout.addWidget(btn, i // 7, i % 7)
            
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Botones de acción
        btn_layout = QVBoxLayout()
        
        # Botón terminar partida (NUEVO)
        finish_btn = QPushButton("🎯 Terminar Partida")
        finish_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; padding: 12px; font-size: 14px; }")
        finish_btn.clicked.connect(self.finish_hand)
        btn_layout.addWidget(finish_btn)
        
        # Botones existentes en fila
        existing_btns = QHBoxLayout()
        
        reset_btn = QPushButton("🔄 Nueva Mano")
        reset_btn.setStyleSheet("QPushButton { background-color: #17a2b8; color: white; font-weight: bold; padding: 10px; }")
        reset_btn.clicked.connect(self.reset_hand_only)
        existing_btns.addWidget(reset_btn)
        
        new_shoe_btn = QPushButton("🗂️ Nuevo Zapato")
        new_shoe_btn.setStyleSheet("QPushButton { background-color: #fd7e14; color: white; font-weight: bold; padding: 10px; }")
        new_shoe_btn.clicked.connect(self.reset_game)
        existing_btns.addWidget(new_shoe_btn)
        
        help_btn = QPushButton("❓ Ayuda")
        help_btn.setStyleSheet("QPushButton { background-color: #6c757d; color: white; font-weight: bold; padding: 10px; }")
        help_btn.clicked.connect(self.show_help)
        existing_btns.addWidget(help_btn)
        
        btn_layout.addLayout(existing_btns)
        layout.addLayout(btn_layout)
        
        panel.setLayout(layout)
        return panel
        
    def create_analysis_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("📊 Análisis Estratégico")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Barra de ventaja
        advantage_group = QGroupBox("Ventaja del Jugador")
        advantage_layout = QVBoxLayout()
        
        self.advantage_bar = QProgressBar()
        self.advantage_bar.setRange(-10, 10)
        self.advantage_bar.setValue(0)
        self.advantage_bar.setFormat("Neutro")
        advantage_layout.addWidget(self.advantage_bar)
        
        advantage_group.setLayout(advantage_layout)
        layout.addWidget(advantage_group)
        
        # Panel de información
        self.info_panel = QLabel("")
        self.info_panel.setFont(QFont("Monaco", 10))
        self.info_panel.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                color: #212529;
            }
        """)
        self.info_panel.setWordWrap(True)
        self.info_panel.setAlignment(Qt.AlignTop)
        
        scroll = QScrollArea()
        scroll.setWidget(self.info_panel)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        panel.setLayout(layout)
        return panel
    
    def finish_hand(self):
        """NUEVA FUNCIÓN: Termina la mano actual y actualiza estadísticas"""
        # Verificar que tengamos la información necesaria
        if not self.game_state.player_cards:
            QMessageBox.warning(self, "Advertencia", "No hay cartas del jugador para terminar la partida.")
            return
            
        if not self.game_state.dealer_card:
            QMessageBox.warning(self, "Advertencia", "Falta la carta visible del crupier.")
            return
            
        hidden_card = self.dealer_hidden_combo.currentText()
        if not hidden_card:
            QMessageBox.warning(self, "Advertencia", "Debes seleccionar la carta oculta del crupier.")
            return
        
        # Determinar resultado
        dealer_cards = [self.game_state.dealer_card, hidden_card]
        result = BlackjackStrategy.determine_winner(self.game_state.player_cards, dealer_cards)
        
        # Actualizar estadísticas
        self.session_stats.total_hands += 1
        if result == GameResult.WIN:
            self.session_stats.wins += 1
        elif result == GameResult.LOSE:
            self.session_stats.losses += 1
        elif result == GameResult.PUSH:
            self.session_stats.pushes += 1
            
        # Mover cartas del jugador a mesa automáticamente
        player_cards_count = {}
        for card in self.game_state.player_cards:
            player_cards_count[card] = player_cards_count.get(card, 0) + 1
            
        # Agregar cartas del jugador a botones de mesa
        for i, btn in enumerate(self.table_buttons):
            if btn.card_label in player_cards_count:
                btn.add_cards(player_cards_count[btn.card_label])
                
        # Agregar carta oculta del dealer a mesa
        for btn in self.table_buttons:
            if btn.card_label == hidden_card:
                btn.add_cards(1)
                break
        
        # Resetear solo las cartas del jugador
        for btn in self.player_buttons:
            btn.reset()
            
        # Resetear combos para nueva mano
        self.dealer_combo.setCurrentIndex(0)
        self.dealer_hidden_combo.setCurrentIndex(0)
        
        # Actualizar análisis y mostrar resultado
        self.update_analysis()
        self.update_stats_display()
        
        # Mostrar mensaje de resultado
        result_msg = {
            GameResult.WIN: "🎉 ¡Ganaste esta mano!",
            GameResult.LOSE: "😞 Perdiste esta mano.",
            GameResult.PUSH: "🤝 Empate en esta mano."
        }
        
        player_total, _ = BlackjackStrategy.calculate_hand_value(self.game_state.player_cards)
        dealer_total, _ = BlackjackStrategy.calculate_hand_value(dealer_cards)
        
        QMessageBox.information(
            self, 
            "Resultado de la Mano",
            f"{result_msg[result]}\n\n"
            f"Tu mano: {player_total}\n"
            f"Mano del crupier: {dealer_total}\n\n"
            f"Las cartas han sido movidas automáticamente a 'visibles en mesa'."
        )
    
    def reset_hand_only(self):
        """Resetea solo la mano actual, mantiene el zapato y estadísticas"""
        for btn in self.player_buttons:
            btn.reset()
        self.dealer_combo.setCurrentIndex(0)
        self.dealer_hidden_combo.setCurrentIndex(0)
        self.update_analysis()
    
    def update_stats_display(self):
        """Actualiza la visualización de estadísticas"""
        stats_text = f"""
<b>Manos jugadas:</b> {self.session_stats.total_hands}<br>
<b>Ganadas:</b> <span style='color: green;'>{self.session_stats.wins}</span> | 
<b>Perdidas:</b> <span style='color: red;'>{self.session_stats.losses}</span> | 
<b>Empates:</b> <span style='color: gray;'>{self.session_stats.pushes}</span><br>
<b>% Victorias:</b> <span style='color: blue;'>{self.session_stats.win_percentage:.1f}%</span>
        """
        self.stats_label.setText(stats_text)
        
    def setup_tooltips(self):
        self.dealer_combo.setToolTip("Selecciona la carta visible del crupier")
        self.dealer_hidden_combo.setToolTip("Carta oculta del crupier (solo para terminar partida)")
        self.decks_combo.setToolTip("Número de barajas en el zapato (shoe)")
        
        for btn in self.player_buttons + self.table_buttons:
            btn.setToolTip("Click izquierdo: +1 carta\nClick derecho: -1 carta")
            
    def on_decks_changed(self):
        self.game_state.num_decks = int(self.decks_combo.currentText())
        max_cards = self.game_state.num_decks * 4
        for btn in self.player_buttons + self.table_buttons:
            btn.max_count = max_cards
        self.update_analysis()
        
    def reset_game(self):
        """Reset completo: nuevo zapato, resetea estadísticas"""
        # Resetear botones
        for btn in self.player_buttons + self.table_buttons:
            btn.reset()
            
        # Resetear combos
        self.dealer_combo.setCurrentIndex(0)
        self.dealer_hidden_combo.setCurrentIndex(0)
        
        # Resetear estado y estadísticas
        self.game_state = GameState([], "", "", [], int(self.decks_combo.currentText()), 0, 0.0, float(self.decks_combo.currentText()))
        self.session_stats = SessionStats()
        
        self.update_analysis()
        self.update_stats_display()
        
    def update_analysis(self):
        try:
            dealer_card = self.dealer_combo.currentText()
            player_cards = []
            table_cards = []
            
            for btn in self.player_buttons:
                player_cards.extend(btn.get_selected_cards())
                
            for btn in self.table_buttons:
                table_cards.extend(btn.get_selected_cards())
                
            self.game_state.player_cards = player_cards
            self.game_state.dealer_card = dealer_card
            self.game_state.table_cards = table_cards
            
            # Calcular conteos
            all_cards = player_cards + table_cards + ([dealer_card] if dealer_card else [])
            running_count, true_count, decks_remaining = CardCountingEngine.calculate_counts(
                all_cards, self.game_state.num_decks
            )
            
            self.game_state.running_count = running_count
            self.game_state.true_count = true_count
            self.game_state.decks_remaining = decks_remaining
            
            # Obtener recomendación estratégica
            if player_cards and dealer_card:
                optimal_play, explanation = BlackjackStrategy.get_optimal_play(
                    player_cards, dealer_card, true_count, can_double=True, can_split=True
                )
                player_total, is_soft = BlackjackStrategy.calculate_hand_value(player_cards)
            else:
                optimal_play = None
                explanation = "Selecciona tus cartas y la carta del crupier"
                player_total = 0
                is_soft = False
                
            # Actualizar interfaz
            self.update_advantage_bar(true_count)
            self.update_info_panel(optimal_play, explanation, player_total, is_soft)
            
        except Exception as e:
            self.info_panel.setText(f"Error en análisis: {str(e)}")
            
    def update_advantage_bar(self, true_count: float):
        advantage_text, color = CardCountingEngine.get_betting_advantage(true_count)
        
        bar_value = max(-10, min(10, int(true_count * 2)))
        self.advantage_bar.setValue(bar_value)
        self.advantage_bar.setFormat(f"{advantage_text} (TC: {true_count})")
        
        color_map = {
            "green": "#28a745",
            "orange": "#fd7e14", 
            "red": "#dc3545",
            "gray": "#6c757d"
        }
        
        self.advantage_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color_map.get(color, "#6c757d")};
                border-radius: 3px;
            }}
        """)
        
    def update_info_panel(self, optimal_play, explanation, player_total, is_soft):
        info_text = f"""
<b>📈 ANÁLISIS ESTRATÉGICO COMPLETO</b><br><br>

<b>🎯 Estado Actual:</b><br>
• Cartas del jugador: {', '.join(self.game_state.player_cards) if self.game_state.player_cards else 'Ninguna'}<br>
• Valor de la mano: {player_total} {'(Soft)' if is_soft else '(Hard)' if player_total > 0 else ''}<br>
• Carta del crupier: {self.game_state.dealer_card or 'No seleccionada'}<br>
• Cartas en mesa: {len(self.game_state.table_cards)} cartas<br><br>

<b>🧮 Conteo de Cartas (Hi-Lo):</b><br>
• Running Count: {self.game_state.running_count}<br>
• True Count: {self.game_state.true_count}<br>
• Barajas restantes: {self.game_state.decks_remaining}<br>
• Total cartas jugadas: {len(self.game_state.player_cards + self.game_state.table_cards) + (1 if self.game_state.dealer_card else 0)}<br><br>

<b>🎲 RECOMENDACIÓN ÓPTIMA:</b><br>
<span style='color: #28a745; font-size: 14px; font-weight: bold;'>
{optimal_play.value if optimal_play else 'Pendiente'}
</span><br>
<i>{explanation}</i><br><br>

<b>💡 Instrucciones:</b><br>
1. Marca tus cartas y carta visible del crupier<br>
2. Sigue la recomendación matemática<br>
3. Al terminar, selecciona carta oculta del crupier<br>
4. Haz click en "Terminar Partida" para resultado automático<br><br>

<b>📊 El conteo se mantiene hasta cambiar zapato</b>
        """
        
        self.info_panel.setText(info_text)
        
    def show_help(self):
        help_text = """
🃏 GUÍA DE USO - BLACKJACK PREMIUM CON ESTADÍSTICAS

📋 NUEVO: TERMINAR PARTIDA AUTOMÁTICA
• Marca tus cartas y carta visible del crupier
• Juega siguiendo las recomendaciones
• Al terminar, selecciona la carta oculta del crupier
• Haz click en "Terminar Partida"
• El sistema determinará automáticamente si ganaste/perdiste
• Todas las cartas se mueven automáticamente a "visibles en mesa"

🎯 CONTROLES:
• Click izq/der en cartas: +1/-1 carta
• "Nueva Mano": Solo resetea tu mano (mantiene zapato y conteo)
• "Nuevo Zapato": Reset completo (nuevas barajas, resetea estadísticas)
• "Terminar Partida": Finaliza mano automáticamente

📊 ESTADÍSTICAS:
• Seguimiento automático de victorias/derrotas/empates
• Porcentaje de victorias en tiempo real
• Estadísticas se mantienen durante toda la sesión

🧮 CONTEO DE CARTAS:
• Se mantiene automáticamente entre manos
• Solo se resetea al cambiar zapato
• True Count ajustado por barajas restantes

⚖️ AVISO: Solo para fines educativos e investigación.
        """
        
        msg = QMessageBox()
        msg.setWindowTitle("Ayuda - Blackjack Premium")
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = BlackjackPremiumUI()
    window.show()
    
    sys.exit(app.exec_())
