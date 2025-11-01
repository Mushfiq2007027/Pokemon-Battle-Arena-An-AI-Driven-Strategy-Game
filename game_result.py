"""
Game Result Page Module
"""
import math
import time
import pygame
from config import BASE_WIDTH, BASE_HEIGHT


class GameResult:
    def __init__(self, game, winner):
        self.game = game
        self.winner = winner
        self.phase_start_time = time.time()
        self.celebration_time = time.time()
        
        # Play appropriate voice
        if self.winner == "Draw":
            self.game.play_voice("draw")
        elif self.winner == "Ash":
            self.game.play_voice("ash_wins")
        else:
            self.game.play_voice("rocket_wins")
        
        self.game.sfx['gameover'].play()
    
    def update(self, dt: float):
        """Update game over screen"""
        pass
    
    def draw(self, surf: pygame.Surface):
        """Draw game over screen with winner image and celebration (NO BATTLE LOG)"""
        # Gradient background
        for y in range(self.game.current_height):
            ratio = y / self.game.current_height
            if self.winner == "Ash":
                color = (int(20 + ratio * 60), int(40 + ratio * 100), int(100 + ratio * 140))
            elif self.winner == "Team Rocket":
                color = (int(100 + ratio * 120), int(20 + ratio * 60), int(40 + ratio * 100))
            else:
                color = (int(60 + ratio * 80), int(60 + ratio * 80), int(60 + ratio * 80))
            pygame.draw.line(surf, color, (0, y), (self.game.current_width, y))
        
        y = int(120 * self.game.current_height / BASE_HEIGHT)
        if self.winner == "Draw":
            title = self.game.font_huge.render("IT'S A DRAW!", True, (255, 255, 255))
        else:
            title = self.game.font_huge.render(f"{self.winner} WINS!", True, (255, 255, 100))
        surf.blit(title, title.get_rect(center=(self.game.current_width // 2, y)))
        
        # Winner sprite with animation
        if self.winner != "Draw":
            elapsed = time.time() - self.celebration_time
            scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
            bounce = abs(math.sin(elapsed * 4)) * 30 * scale
            
            winner_sprite = self.game.get_scaled_sprite(self.winner, "trainer")
            if winner_sprite:
                big_sprite = pygame.transform.scale(winner_sprite, (int(200 * scale), int(200 * scale)))
                rect = big_sprite.get_rect(center=(self.game.current_width // 2, int((y + 180) * self.game.current_height / BASE_HEIGHT + bounce)))
                surf.blit(big_sprite, rect)
            
            congrats = self.game.font_big.render("🏆 CONGRATULATIONS! 🏆", True, (255, 215, 0))
            surf.blit(congrats, congrats.get_rect(center=(self.game.current_width // 2, int((y + 340) * self.game.current_height / BASE_HEIGHT))))
            
            # Particle effects
            if int(elapsed * 10) % 5 == 0:
                for _ in range(3):
                    self.game.addparticleeffect((self.game.current_width // 2, int((y + 180) * self.game.current_height / BASE_HEIGHT)), (255, 215, 0), 10)
        
        # Stats section
        y = self.game.current_height - int(300 * self.game.current_height / BASE_HEIGHT)
        stats = [
            "Final Stats:",
            "",
            f"Ash - {sum(p.hp for p in self.game.ash.team)} HP remaining",
            f"Team Rocket - {sum(p.hp for p in self.game.rocket.team)} HP remaining",
            "",
            "Controls:",
            "[A] Play Again    [E] Exit",
        ]
        
        for line in stats:
            if line == "Final Stats:" or line == "Controls:":
                text = self.game.font_big.render(line, True, (255, 255, 100))
            elif line == "":
                y += int(12 * self.game.current_height / BASE_HEIGHT)
                continue
            else:
                text = self.game.font.render(line, True, (255, 255, 255))
            surf.blit(text, text.get_rect(center=(self.game.current_width // 2, y)))
            y += int(38 * self.game.current_height / BASE_HEIGHT)

