"""
Game Intro Page Module
"""
import pygame
import time
from config import INTRO_TIME, BASE_WIDTH, BASE_HEIGHT


class GameIntro:
    def __init__(self, game):
        self.game = game
        self.intro_start_time = time.time()
    
    def update(self, dt: float) -> bool:
        """Update intro, returns True if should transition to next phase"""
        if not self.game.voice_played["intro"]:
            self.game.play_voice("intro")
        
        elapsed = time.time() - self.intro_start_time
        if elapsed > INTRO_TIME:
            return True
        return False
    
    def draw(self, surf: pygame.Surface):
        """Draw intro screen with background image"""
        bg = self.game.get_scaled_background("intro")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((20, 40, 60))
        
        overlay = pygame.Surface((self.game.current_width, self.game.current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surf.blit(overlay, (0, 0))
        
        title_text = "Pokemon Battle Arena"
        for offset in [(-3, -3), (-3, 3), (3, -3), (3, 3)]:
            title_outline = self.game.font_title.render(title_text, True, (0, 0, 0))
            surf.blit(title_outline, (self.game.current_width // 2 - title_outline.get_width() // 2 + offset[0], int(80 * self.game.current_height / BASE_HEIGHT) + offset[1]))
        title = self.game.font_title.render(title_text, True, (255, 255, 100))
        surf.blit(title, (self.game.current_width // 2 - title.get_width() // 2, int(80 * self.game.current_height / BASE_HEIGHT)))
        
        subtitle = self.game.font_big.render("AI Battle System", True, (255, 255, 255))
        surf.blit(subtitle, subtitle.get_rect(center=(self.game.current_width // 2, int(180 * self.game.current_height / BASE_HEIGHT))))
        
        rules = [
            "GAME RULES",
            "",
            "Two AI agents compete: Ash vs Team Rocket",
            "",
            "Phase 1 (30s): Catch 3 Pokemon using A* pathfinding",
            "Phase 2 (5s): Buy healing elixirs with coins",
            "Phase 3 (130s): Turn-based Pokemon battle",
            "  - Minimax with Alpha-Beta Pruning + Fuzzy Logic",
            "  - Type advantages: Fire>Electric, Electric>Water, Water>Fire",
            "",
            "Controls: [P] Pause  [R] Resume  [E] Exit  [A] Play Again",
            "",
            "Starting in a moment...",
        ]
        
        y = int(260 * self.game.current_height / BASE_HEIGHT)
        for line in rules:
            if line == "GAME RULES":
                for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                    outline = self.game.font_big.render(line, True, (0, 0, 0))
                    surf.blit(outline, (self.game.current_width // 2 - outline.get_width() // 2 + ox, y + oy))
                text = self.game.font_big.render(line, True, (255, 255, 100))
            elif line.startswith("Phase"):
                text = self.game.font.render(line, True, (100, 255, 200))
            elif line == "":
                y += int(5 * self.game.current_height / BASE_HEIGHT)
                continue
            else:
                text = self.game.font_small.render(line, True, (255, 255, 255))
            surf.blit(text, (self.game.current_width // 2 - text.get_width() // 2, y))
            y += int(28 * self.game.current_height / BASE_HEIGHT)

