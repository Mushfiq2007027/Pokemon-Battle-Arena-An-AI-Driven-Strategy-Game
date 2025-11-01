"""
Team Rocket AI Agent - Minimax with Alpha-Beta Pruning
"""
import random
from typing import Tuple, Optional, List
from models import Agent, BattleState, BattleAction, BActEnum, Pokemon
from config import TYPEADV, ELIXIRS
from utils import FuzzyLogic


def evalstate(ash: Agent, rocket: Agent, bs: BattleState) -> int:
    """Evaluate battle state - PERFECTLY EQUAL for both agents"""
    ashhp = sum(p.hp for p in ash.team)
    rockethp = sum(p.hp for p in rocket.team)
    
    ashalive = sum(1 for p in ash.team if p.alive)
    rocketalive = sum(1 for p in rocket.team if p.alive)
    
    return (ashhp - rockethp) + (ashalive - rocketalive) * 30


def legalactions(agent: Agent, activeidx: int, opppokemon: Pokemon) -> List[BattleAction]:
    """Get legal actions using fuzzy logic"""
    acts = [BattleAction(BActEnum.ATTACK), BattleAction(BActEnum.DEFEND)]
    
    activepoke = agent.team[activeidx]
    
    bench_has_advantage = False
    best_swap_idx = None
    for i, p in enumerate(agent.team):
        if i != activeidx and p.alive:
            if (p.ptype, opppokemon.ptype) in TYPEADV:
                bench_has_advantage = True
                best_swap_idx = i
                break
    
    if bench_has_advantage:
        hp_percent = (activepoke.hp / activepoke.maxhp) * 100
        swap_strength = FuzzyLogic.should_swap(
            activepoke.ptype,
            opppokemon.ptype,
            True,
            hp_percent
        )
        if swap_strength > 0.5:
            acts.append(BattleAction(BActEnum.SWAP, arg=best_swap_idx))
    
    has_elixir = any(v > 0 for v in agent.elixirs.values())
    if has_elixir and activepoke.hp < activepoke.maxhp:
        hp_percent = (activepoke.hp / activepoke.maxhp) * 100
        enemy_hp_percent = (opppokemon.hp / opppokemon.maxhp) * 100
        
        heal_strength = FuzzyLogic.should_heal(hp_percent, True, enemy_hp_percent)
        if heal_strength > 0.4:
            avail = [k for k, v in agent.elixirs.items() if v > 0]
            if avail:
                best_elixir = max(avail, key=lambda n: ELIXIRS[n][0])
                acts.append(BattleAction(BActEnum.HEAL, arg=best_elixir))
    
    return acts


def cloneagent(a: Agent) -> Agent:
    """Deep clone agent for minimax simulation"""
    return Agent(
        name=a.name,
        team=[Pokemon(p.name, p.ptype, p.maxhp, p.hp, p.atk, p.dfn, p.alive) for p in a.team],
        coins=a.coins,
        fuel=a.fuel,
        elixirs=dict(a.elixirs),
        position=a.position,
        targetpos=a.targetpos
    )


def decide_action(me: Agent, opp: Agent, bs: BattleState, meisash: bool, depth: int = 3) -> BattleAction:
    """Team Rocket's decision making using Minimax with Alpha-Beta Pruning - CORRECTED VERSION"""
    
    def recurse(a: Agent, b: Agent, s: BattleState, ply: int, maximizing: bool, alpha: float, beta: float) -> Tuple[int, Optional[BattleAction]]:
        if ply == 0 or all(not p.alive for p in a.team) or all(not p.alive for p in b.team):
            score = evalstate(a if meisash else b, b if meisash else a, s)
            return (score if meisash else -score), None
        
        bestval = -1e9 if maximizing else 1e9
        bestact = None
        
        currentactiveidx = s.ashactive if maximizing else s.rocketactive
        oppactiveidx = s.rocketactive if maximizing else s.ashactive
        agentforactions = a if maximizing else b
        oppforactions = b if maximizing else a
        
        actions = legalactions(agentforactions, currentactiveidx, oppforactions.team[oppactiveidx])
        
        # Shuffle for maximum randomness
        random.shuffle(actions)
        
        for act in actions:
            aclone, bclone = cloneagent(a), cloneagent(b)
            sclone = BattleState(s.fieldtype, s.ashactive, s.rocketactive)
            
            # Import stepbattle from phase_3 to simulate
            from phase_3 import stepbattle_simulation
            
            myact = act
            oppact = BattleAction(BActEnum.ATTACK)
            ashact = myact if maximizing else oppact
            rocketact = oppact if maximizing else myact
            
            stepbattle_simulation(aclone, bclone, sclone, ashact, rocketact)
            val, _ = recurse(aclone, bclone, sclone, ply - 1, not maximizing, alpha, beta)
            
            if maximizing:
                if val > bestval:
                    bestval, bestact = val, act
                alpha = max(alpha, bestval)
            else:
                if val < bestval:
                    bestval, bestact = val, act
                beta = min(beta, bestval)
            
            if beta <= alpha:
                break
        
        return bestval, bestact
    
    _, action = recurse(
        me if meisash else opp,
        opp if meisash else me,
        bs,
        depth,
        meisash,
        -1e9,
        1e9
    )
    return action or BattleAction(BActEnum.ATTACK)

