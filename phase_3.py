"""
Phase 3: Battle Module
"""
import math
import time
import random
import pygame
from typing import Tuple
from models import Agent, BattleState, BattleAction, BActEnum
from config import (PHASE3_TIME, TYPEADV, FIELDBOOST, ELIXIRS, 
                   TYPECOLOR, BASE_WIDTH, BASE_HEIGHT, BASE_ATTACKICONSIZE)


class Phase3:
    def __init__(self, game):
        self.game = game
        self.phase_start_time = 0
        self.nextdecisiontime = 0
        self.last_action = {"Ash": "WAITING", "Team Rocket": "WAITING"}
        
        # Initialize battle
        self.init_phase()
    
    def init_phase(self):
        """Initialize phase 3"""
        self.game.sfx['transition'].play()
    
    def update(self, dt: float) -> Tuple[bool, str]:
        """Update battle phase, returns (should_transition, winner)"""
        # Wait for audio to finish before starting phase
        if self.game.waiting_for_audio and not self.game.is_voice_finished("phase3"):
            return False, None
        
        # Start timer after audio finishes
        if self.phase_start_time == 0:
            self.phase_start_time = time.time()
            self.nextdecisiontime = time.time() + 1.0
        
        ash_alive = any(p.alive for p in self.game.ash.team)
        rocket_alive = any(p.alive for p in self.game.rocket.team)
        
        if not ash_alive or not rocket_alive:
            winner = "Team Rocket" if not ash_alive else "Ash"
            return True, winner
        
        elapsed = time.time() - self.phase_start_time
        if elapsed > PHASE3_TIME:
            ash_hp = sum(p.hp for p in self.game.ash.team)
            rocket_hp = sum(p.hp for p in self.game.rocket.team)
            if ash_hp > rocket_hp:
                winner = "Ash"
            elif rocket_hp > ash_hp:
                winner = "Team Rocket"
            else:
                winner = "Draw"
            return True, winner
        
        now = time.time()
        if now < self.nextdecisiontime:
            return False, None
        
        self.nextdecisiontime = now + 0.7
        
        # Get AI decisions - CORRECTED to match original code
        from ash_ai_agent import decide_action as ash_decide
        from team_rocket_ai_agent import decide_action as rocket_decide
        
        # EQUAL depth for both agents - matching original pokemon_battle_arena4.py line 1094-1095
        ashact = ash_decide(self.game.ash, self.game.rocket, self.game.bs, meisash=True, depth=3)
        rocketact = rocket_decide(self.game.rocket, self.game.ash, self.game.bs, meisash=False, depth=3)
        
        stepbattle(self.game.ash, self.game.rocket, self.game.bs, ashact, rocketact, self.game, self)
        
        return False, None
    
    def draw(self, surf: pygame.Surface):
        """Draw battle phase with battleground background (NO BATTLE LOG)"""
        bg = self.game.get_scaled_background("battle")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            fieldcolor = TYPECOLOR.get(self.game.fieldtype, (50, 50, 50))
            bgcolor = tuple(c // 3 for c in fieldcolor)
            surf.fill(bgcolor)
        
        self.drawbattlescene(surf)
        self.draweffects(surf)
        self.drawhud(surf)
    
    def drawbattlescene(self, surf: pygame.Surface):
        """Draw battle arena with Pokemon"""
        cx, cy = self.game.current_width // 2, self.game.current_height // 2
        
        a = self.game.ash.team[self.game.bs.ashactive]
        r = self.game.rocket.team[self.game.bs.rocketactive]
        
        # Calculate attack animations
        now = time.time()
        ashlunge = 0
        rocketlunge = 0
        
        for side, _, endtime in reversed(self.game.activeattackeffects):
            progress = 1.0 - max(0, (endtime - now) / 0.7)
            if 0 < progress < 1:
                scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
                lunge = math.sin(progress * math.pi) * 60 * scale
                if side.name == "Ash":
                    ashlunge = lunge
                else:
                    rocketlunge = lunge
        
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        offset_x = int(300 * scale)
        
        # Draw Pokemon
        if a.alive:
            ashsprite = self.game.get_scaled_sprite(a.name, "battle")
            if ashsprite:
                pos = (cx - offset_x + ashlunge, cy + a.boboffset)
                rect = ashsprite.get_rect(center=pos)
                surf.blit(ashsprite, rect)
                self.drawpokemonhp(surf, a, cx - int(400 * scale), cy + int(120 * scale))
                # Action label BEHIND pokemon (left side)
                action_text = self.game.font.render(f"{self.last_action['Ash']}", True, (255, 255, 100))
                action_bg = self.game.font.render(f"{self.last_action['Ash']}", True, (0, 0, 0))
                action_x = cx - offset_x - int(200 * scale)
                action_y = cy
                surf.blit(action_bg, (action_x + 2, action_y + 2))
                surf.blit(action_text, (action_x, action_y))
        
        if r.alive:
            rocketsprite = self.game.get_scaled_sprite(r.name, "battle")
            if rocketsprite:
                pos = (cx + offset_x - rocketlunge, cy + r.boboffset)
                rect = rocketsprite.get_rect(center=pos)
                surf.blit(rocketsprite, rect)
                self.drawpokemonhp(surf, r, cx + int(200 * scale), cy + int(120 * scale))
                # Action label BEHIND pokemon (right side)
                action_text = self.game.font.render(f"{self.last_action['Team Rocket']}", True, (255, 255, 100))
                action_bg = self.game.font.render(f"{self.last_action['Team Rocket']}", True, (0, 0, 0))
                action_x = cx + offset_x + int(100 * scale)
                action_y = cy
                surf.blit(action_bg, (action_x + 2, action_y + 2))
                surf.blit(action_text, (action_x, action_y))
        
        # Draw trainer info panels
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        panel_y = int(100 * scale)
        self.drawtrainerinfo(surf, self.game.ash, int(30 * scale), panel_y)
        self.drawtrainerinfo(surf, self.game.rocket, self.game.current_width - int(400 * scale), panel_y)
    
    def drawpokemonhp(self, surf: pygame.Surface, pokemon, x: int, y: int):
        """Draw Pokemon HP bar"""
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        w, h = int(250 * scale), int(24 * scale)
        frac = pokemon.displayhp / pokemon.maxhp if pokemon.maxhp > 0 else 0
        
        pygame.draw.rect(surf, (40, 40, 40), (x, y, w, h), border_radius=int(8 * scale))
        if frac > 0.5:
            color = (80, 220, 80)
        elif frac > 0.25:
            color = (220, 220, 80)
        else:
            color = (220, 80, 80)
        pygame.draw.rect(surf, color, (x, y, int(w * frac), h), border_radius=int(8 * scale))
        pygame.draw.rect(surf, (255, 255, 255), (x, y, w, h), int(3 * scale), border_radius=int(8 * scale))
        
        hptext = self.game.font.render(f"{int(pokemon.displayhp)}/{pokemon.maxhp}", True, (255, 255, 255))
        surf.blit(hptext, (x + w // 2 - hptext.get_width() // 2, y + int(3 * scale)))
        
        nametext = self.game.font_big.render(pokemon.name, True, (255, 255, 255))
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            outline = self.game.font_big.render(pokemon.name, True, (0, 0, 0))
            surf.blit(outline, (x + ox, y - int(35 * scale) + oy))
        surf.blit(nametext, (x, y - int(35 * scale)))
    
    def drawtrainerinfo(self, surf: pygame.Surface, agent: Agent, x: int, y: int):
        """Draw trainer info panel"""
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        panel_width = int(360 * scale)
        panel_height = int(260 * scale)
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, (255, 255, 255), (x, y, panel_width, panel_height), int(3 * scale), border_radius=int(12 * scale))
        
        trainersprite = self.game.get_scaled_sprite(agent.name, "trainer")
        if trainersprite:
            surf.blit(trainersprite, (x + int(10 * scale), y + int(10 * scale)))
        
        name = self.game.font_big.render(agent.name, True, (255, 255, 100))
        surf.blit(name, (x + int(100 * scale), y + int(25 * scale)))
        
        activeidx = self.game.bs.ashactive if agent.name == "Ash" else self.game.bs.rocketactive
        py = y + int(95 * scale)
        for i, p in enumerate(agent.team):
            prefix = "▶ " if i == activeidx and p.alive else "  "
            color = (255, 255, 255) if p.alive else (120, 120, 120)
            status = "✓" if p.alive else "✗"
            text = self.game.font_small.render(f"{prefix}{p.name} {status}", True, color)
            surf.blit(text, (x + int(15 * scale), py))
            
            if p.alive:
                barw = int(120 * scale)
                barh = int(10 * scale)
                frac = p.displayhp / p.maxhp
                pygame.draw.rect(surf, (60, 60, 60), (x + int(200 * scale), py + int(3 * scale), barw, barh))
                pygame.draw.rect(surf, (80, 200, 80), (x + int(200 * scale), py + int(3 * scale), int(barw * frac), barh))
            
            py += int(35 * scale)
        
        elixir_text = f"Elixirs: {self.format_elixirs(agent.elixirs)}"
        elixir = self.game.font_small.render(elixir_text, True, (200, 255, 200))
        surf.blit(elixir, (x + int(15 * scale), py + int(12 * scale)))
    
    def format_elixirs(self, elixirs):
        """Format elixir dict for display"""
        items = [f"{v}x{k}" for k, v in elixirs.items() if v > 0]
        return ", ".join(items) if items else "none"
    
    def draweffects(self, surf: pygame.Surface):
        """Draw battle effects"""
        cx, cy = self.game.current_width // 2, self.game.current_height // 2
        now = time.time()
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        
        # Draw attack icons
        lastashattack = None
        lastrocketattack = None
        
        for side, attacker, endtime in reversed(self.game.activeattackeffects):
            if side.name == "Ash" and lastashattack is None:
                lastashattack = (attacker, endtime)
            elif side.name == "Team Rocket" and lastrocketattack is None:
                lastrocketattack = (attacker, endtime)
        
        if lastashattack:
            attacker, endtime = lastashattack
            progress = 1 - (endtime - now) / 0.7
            target_size = self.game.get_scaled_size(BASE_ATTACKICONSIZE)
            size = (int(target_size[0] * (1 + progress * 0.6)), int(target_size[1] * (1 + progress * 0.6)))
            alpha = int(255 * (1 - progress))
            
            icon_name = None
            if attacker.name == "Pikachu":
                icon_name = "electricright"
            elif attacker.name == "Charmander":
                icon_name = "fireright"
            elif attacker.name == "Squirtle":
                icon_name = "waterright"
            
            if icon_name:
                original = self.game.sprites.get(f"{icon_name}_original")
                if original:
                    scaledicon = pygame.transform.smoothscale(original, size)
                    scaledicon.set_alpha(alpha)
                    posx = cx - int(100 * scale)
                    iconrect = scaledicon.get_rect(center=(posx, cy))
                    surf.blit(scaledicon, iconrect)
        
        if lastrocketattack:
            attacker, endtime = lastrocketattack
            progress = 1 - (endtime - now) / 0.7
            target_size = self.game.get_scaled_size(BASE_ATTACKICONSIZE)
            size = (int(target_size[0] * (1 + progress * 0.6)), int(target_size[1] * (1 + progress * 0.6)))
            alpha = int(255 * (1 - progress))
            
            icon_name = None
            if attacker.name == "Meowth":
                icon_name = "electricleft"
            elif attacker.name == "Weezing":
                icon_name = "fireleft"
            elif attacker.name == "Wobbuffet":
                icon_name = "waterleft"
            
            if icon_name:
                original = self.game.sprites.get(f"{icon_name}_original")
                if original:
                    scaledicon = pygame.transform.smoothscale(original, size)
                    scaledicon.set_alpha(alpha)
                    posx = cx + int(100 * scale)
                    iconrect = scaledicon.get_rect(center=(posx, cy))
                    surf.blit(scaledicon, iconrect)
        
        # Draw damage popups
        for popup in self.game.damagepopups:
            progress = (now - popup.starttime) / popup.duration
            yoffset = -80 * progress * scale
            alpha = int(255 * (1 - progress ** 2))
            fontsurf = self.game.font_huge.render(popup.text, True, popup.color)
            fontsurf.set_alpha(alpha)
            pos = (popup.pos[0], popup.pos[1] + yoffset)
            surf.blit(fontsurf, fontsurf.get_rect(center=pos))
        
        # Draw particles
        for p in self.game.particles:
            alpha = int(255 * (p.lifespan / p.startlife))
            size = int(12 * (p.lifespan / p.startlife) * scale)
            if size > 0:
                partsurf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                color = (*p.color, alpha)
                pygame.draw.circle(partsurf, color, (size, size), size)
                surf.blit(partsurf, (p.pos[0] - size, p.pos[1] - size), special_flags=pygame.BLEND_RGBA_ADD)
    
    def drawhud(self, surf: pygame.Surface):
        """Draw HUD with phase info and timer (NO BATTLE LOG)"""
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        pygame.draw.rect(surf, (20, 20, 20, 220), (0, 0, self.game.current_width, int(90 * scale)))
        
        title = self.game.font_big.render("PHASE 3: BATTLE!", True, (255, 255, 100))
        surf.blit(title, (int(30 * scale), int(25 * scale)))
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0, PHASE3_TIME - elapsed)
        timer_color = (255, 100, 100) if remaining < 20 else (100, 255, 100)
        timer = self.game.font_big.render(f"Time: {remaining:.1f}s", True, timer_color)
        surf.blit(timer, (self.game.current_width - timer.get_width() - int(30 * scale), int(25 * scale)))
        
        fieldcolor = TYPECOLOR.get(self.game.fieldtype, (255, 255, 255))
        field = self.game.font.render(f"Field: {self.game.fieldtype}", True, fieldcolor)
        surf.blit(field, (self.game.current_width // 2 - field.get_width() // 2, int(35 * scale)))
        
        # Draw controls
        self.drawcontrols(surf)
    
    def drawcontrols(self, surf: pygame.Surface):
        """Draw control instructions"""
        controls = "[P] Pause  [R] Resume  [E] Exit  [A] Play Again"
        text = self.game.font_small.render(controls, True, (200, 200, 200))
        surf.blit(text, (self.game.current_width // 2 - text.get_width() // 2, self.game.current_height - int(35 * self.game.current_height / BASE_HEIGHT)))


# ==================== BATTLE LOGIC ====================
def computedamage(attacker, defender, fieldtype: str) -> int:
    """Calculate battle damage with type advantages"""
    base = max(5, attacker.atk - defender.dfn // 2)
    mult = 1.0
    
    if (attacker.ptype, defender.ptype) in TYPEADV:
        mult *= TYPEADV[(attacker.ptype, defender.ptype)]
    
    if attacker.ptype == fieldtype:
        mult *= FIELDBOOST
    
    mult *= random.uniform(0.8, 1.2)
    
    return int(round(base * mult))


def stepbattle(ash: Agent, rocket: Agent, bs: BattleState, ashact: BattleAction, rocketact: BattleAction, game, phase3):
    """Execute one battle turn"""
    def apply(agent, act, activeidxref):
        if act.kind == BActEnum.SWAP and isinstance(act.arg, int):
            if 0 <= act.arg < len(agent.team) and agent.team[act.arg].alive:
                activeidxref[0] = act.arg
                if game:
                    game.sfx['swap'].play()
                    phase3.last_action[agent.name] = "SWAP"
        elif act.kind == BActEnum.HEAL and isinstance(act.arg, str) and agent.elixirs.get(act.arg, 0) > 0:
            healamt, _ = ELIXIRS[act.arg]
            agent.team[activeidxref[0]].heal(healamt)
            agent.elixirs[act.arg] -= 1
            if game:
                game.sfx['heal'].play()
                pos = game.getpokemonscreenpos("ash" if agent.name == "Ash" else "rocket")
                game.addparticleeffect(pos, (100, 255, 100), 25)
                phase3.last_action[agent.name] = "HEAL"
    
    ashidx, rocidx = [bs.ashactive], [bs.rocketactive]
    apply(ash, ashact, ashidx)
    apply(rocket, rocketact, rocidx)
    
    if game:
        if ashact.kind == BActEnum.DEFEND:
            phase3.last_action["Ash"] = "DEFEND"
        if rocketact.kind == BActEnum.DEFEND:
            phase3.last_action["Team Rocket"] = "DEFEND"
    
    ashdef, rocdef = (ashact.kind == BActEnum.DEFEND), (rocketact.kind == BActEnum.DEFEND)
    
    if ashact.kind == BActEnum.ATTACK and ash.team[ashidx[0]].alive and rocket.team[rocidx[0]].alive:
        dmg = computedamage(ash.team[ashidx[0]], rocket.team[rocidx[0]], bs.fieldtype)
        if rocdef:
            dmg = int(dmg * 0.5)
        rocket.team[rocidx[0]].takedamage(dmg)
        if game:
            game.sfx['attack'].play()
            game.addattackeffect(ash, ash.team[ashidx[0]])
            game.adddamagepopup(dmg, "rocket")
            game.triggerscreenshake(6)
            phase3.last_action["Ash"] = "ATTACK"
    
    if rocketact.kind == BActEnum.ATTACK and rocket.team[rocidx[0]].alive and ash.team[ashidx[0]].alive:
        dmg = computedamage(rocket.team[rocidx[0]], ash.team[ashidx[0]], bs.fieldtype)
        if ashdef:
            dmg = int(dmg * 0.5)
        ash.team[ashidx[0]].takedamage(dmg)
        if game:
            game.sfx['attack'].play()
            game.addattackeffect(rocket, rocket.team[rocidx[0]])
            game.adddamagepopup(dmg, "ash")
            game.triggerscreenshake(6)
            phase3.last_action["Team Rocket"] = "ATTACK"
    
    if not ash.team[ashidx[0]].alive:
        for i, p in enumerate(ash.team):
            if p.alive:
                ashidx[0] = i
                break
    if not rocket.team[rocidx[0]].alive:
        for i, p in enumerate(rocket.team):
            if p.alive:
                rocidx[0] = i
                break
    
    bs.ashactive, bs.rocketactive = ashidx[0], rocidx[0]


def stepbattle_simulation(ash: Agent, rocket: Agent, bs: BattleState, ashact: BattleAction, rocketact: BattleAction):
    """Execute one battle turn for simulation (no visual/sound effects)"""
    def apply(agent, act, activeidxref):
        if act.kind == BActEnum.SWAP and isinstance(act.arg, int):
            if 0 <= act.arg < len(agent.team) and agent.team[act.arg].alive:
                activeidxref[0] = act.arg
        elif act.kind == BActEnum.HEAL and isinstance(act.arg, str) and agent.elixirs.get(act.arg, 0) > 0:
            healamt, _ = ELIXIRS[act.arg]
            agent.team[activeidxref[0]].heal(healamt)
            agent.elixirs[act.arg] -= 1
    
    ashidx, rocidx = [bs.ashactive], [bs.rocketactive]
    apply(ash, ashact, ashidx)
    apply(rocket, rocketact, rocidx)
    
    ashdef, rocdef = (ashact.kind == BActEnum.DEFEND), (rocketact.kind == BActEnum.DEFEND)
    
    if ashact.kind == BActEnum.ATTACK and ash.team[ashidx[0]].alive and rocket.team[rocidx[0]].alive:
        dmg = computedamage(ash.team[ashidx[0]], rocket.team[rocidx[0]], bs.fieldtype)
        if rocdef:
            dmg = int(dmg * 0.5)
        rocket.team[rocidx[0]].takedamage(dmg)
    
    if rocketact.kind == BActEnum.ATTACK and rocket.team[rocidx[0]].alive and ash.team[ashidx[0]].alive:
        dmg = computedamage(rocket.team[rocidx[0]], ash.team[ashidx[0]], bs.fieldtype)
        if ashdef:
            dmg = int(dmg * 0.5)
        ash.team[ashidx[0]].takedamage(dmg)
    
    if not ash.team[ashidx[0]].alive:
        for i, p in enumerate(ash.team):
            if p.alive:
                ashidx[0] = i
                break
    if not rocket.team[rocidx[0]].alive:
        for i, p in enumerate(rocket.team):
            if p.alive:
                rocidx[0] = i
                break
    
    bs.ashactive, bs.rocketactive = ashidx[0], rocidx[0]

