"""
Phase 2: Collecting Elixirs Module
"""
import math
import time
import random
import pygame
from typing import Dict, List
from config import PHASE2_TIME, ELIXIRS, COINSPERAGENT, BASE_WIDTH, BASE_HEIGHT


class Phase2:
    def __init__(self, game):
        self.game = game
        self.phase_start_time = 0
        self.elixir_coins: Dict[str, List[Dict]] = {"Ash": [], "Team Rocket": []}
        
        # Initialize elixir purchases
        self.init_phase()
    
    def init_phase(self):
        """Initialize phase 2"""
        self.game.ash.coins = COINSPERAGENT
        self.game.rocket.coins = COINSPERAGENT
        self.game.sfx['transition'].play()
        self.doelixirpurchases()
        self.init_elixir_animation()
    
    def doelixirpurchases(self):
        """AI agents purchase elixirs"""
        def buylogic(agent):
            for k in ELIXIRS:
                agent.elixirs[k] = 0
            
            coins = agent.coins
            items = sorted(ELIXIRS.items(), key=lambda kv: kv[1][0] / kv[1][1], reverse=True)
            
            for name, (healamt, price) in items:
                while coins >= price:
                    agent.elixirs[name] = agent.elixirs.get(name, 0) + 1
                    coins -= price
                    if coins < price:
                        break
            
            agent.coins = coins
        
        buylogic(self.game.ash)
        buylogic(self.game.rocket)
    
    def init_elixir_animation(self):
        """Initialize elixir collection animations"""
        for agent_name in ["Ash", "Team Rocket"]:
            agent = self.game.ash if agent_name == "Ash" else self.game.rocket
            count = sum(agent.elixirs.values())
            for i in range(count):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(50, 150)
                self.elixir_coins[agent_name].append({
                    "pos": [self.game.current_width // 2, self.game.current_height // 2],
                    "vel": [math.cos(angle) * radius, math.sin(angle) * radius],
                    "collected": False
                })
    
    def update(self, dt: float) -> bool:
        """Update elixir phase, returns True if should transition to next phase"""
        # Wait for audio to finish before starting phase
        if self.game.waiting_for_audio and not self.game.is_voice_finished("phase2"):
            return False
        
        # Start timer after audio finishes
        if self.phase_start_time == 0:
            self.phase_start_time = time.time()
        
        elapsed = time.time() - self.phase_start_time
        if elapsed > PHASE2_TIME:
            return True
        
        # Animate elixir collection
        for agent_name in ["Ash", "Team Rocket"]:
            target_x = self.game.current_width // 4 if agent_name == "Ash" else 3 * self.game.current_width // 4
            target_y = self.game.current_height // 2
            
            for coin in self.elixir_coins[agent_name]:
                if not coin["collected"]:
                    dx = target_x - coin["pos"][0]
                    dy = target_y - coin["pos"][1]
                    dist = math.hypot(dx, dy)
                    if dist < 10:
                        coin["collected"] = True
                    else:
                        speed = 300 * dt
                        coin["pos"][0] += dx / dist * speed
                        coin["pos"][1] += dy / dist * speed
        
        return False
    
    def format_elixirs(self, elixirs: Dict[str, int]) -> str:
        """Format elixir dict for display"""
        items = [f"{v}x{k}" for k, v in elixirs.items() if v > 0]
        return ", ".join(items) if items else "none"
    
    def draw(self, surf: pygame.Surface):
        """Draw elixir buying phase with animations (NO BATTLE LOG)"""
        bg = self.game.get_scaled_background("elixir")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((60, 40, 100))
        
        overlay = pygame.Surface((self.game.current_width, self.game.current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surf.blit(overlay, (0, 0))
        
        title = self.game.font_huge.render("PHASE 2", True, (255, 200, 100))
        surf.blit(title, title.get_rect(center=(self.game.current_width // 2, int(80 * self.game.current_height / BASE_HEIGHT))))
        
        subtitle = self.game.font_big.render("Collecting Elixirs", True, (200, 255, 200))
        surf.blit(subtitle, subtitle.get_rect(center=(self.game.current_width // 2, int(160 * self.game.current_height / BASE_HEIGHT))))
        
        # Draw animated elixir coins
        elixir_sprite = self.game.get_scaled_sprite("elixir", "elixir")
        for agent_name in ["Ash", "Team Rocket"]:
            for coin in self.elixir_coins[agent_name]:
                if elixir_sprite:
                    rect = elixir_sprite.get_rect(center=(int(coin["pos"][0]), int(coin["pos"][1])))
                    surf.blit(elixir_sprite, rect)
        
        # Show purchases
        y = int(250 * self.game.current_height / BASE_HEIGHT)
        
        ash_title = self.game.font_big.render("Ash's Elixirs:", True, (100, 200, 255))
        surf.blit(ash_title, (self.game.current_width // 4 - ash_title.get_width() // 2, y))
        y += int(60 * self.game.current_height / BASE_HEIGHT)
        for elixir, count in self.game.ash.elixirs.items():
            if count > 0:
                healamt, price = ELIXIRS[elixir]
                text = self.game.font.render(f"{count}x {elixir} (heals {healamt} HP)", True, (255, 255, 255))
                surf.blit(text, (self.game.current_width // 4 - text.get_width() // 2, y))
                y += int(40 * self.game.current_height / BASE_HEIGHT)
        
        y = int(250 * self.game.current_height / BASE_HEIGHT)
        rocket_title = self.game.font_big.render("Team Rocket's Elixirs:", True, (255, 100, 100))
        surf.blit(rocket_title, (3 * self.game.current_width // 4 - rocket_title.get_width() // 2, y))
        y += int(60 * self.game.current_height / BASE_HEIGHT)
        for elixir, count in self.game.rocket.elixirs.items():
            if count > 0:
                healamt, price = ELIXIRS[elixir]
                text = self.game.font.render(f"{count}x {elixir} (heals {healamt} HP)", True, (255, 255, 255))
                surf.blit(text, (3 * self.game.current_width // 4 - text.get_width() // 2, y))
                y += int(40 * self.game.current_height / BASE_HEIGHT)
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0, PHASE2_TIME - elapsed)
        timer = self.game.font_big.render(f"Time: {remaining:.1f}s", True, (255, 255, 100))
        surf.blit(timer, timer.get_rect(center=(self.game.current_width // 2, self.game.current_height - int(120 * self.game.current_height / BASE_HEIGHT))))
        
        self.drawcontrols(surf)
    
    def drawcontrols(self, surf: pygame.Surface):
        """Draw control instructions"""
        controls = "[P] Pause  [R] Resume  [E] Exit  [A] Play Again"
        text = self.game.font_small.render(controls, True, (200, 200, 200))
        surf.blit(text, (self.game.current_width // 2 - text.get_width() // 2, self.game.current_height - int(35 * self.game.current_height / BASE_HEIGHT)))

