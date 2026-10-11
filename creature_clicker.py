#!/usr/bin/env python3
"""
Procedural Creature Clicker v3
Boss fights, falling orbs, active abilities, mutations, bestiary, stats, settings, and more!
"""

import pygame, sys, math, random, hashlib, colorsys, json, os, time, array

# ─────────────── INIT ───────────────
pygame.init()
SOUND_ENABLED = False
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    SOUND_ENABLED = True
except Exception:
    pass
WIDTH, HEIGHT = 1100, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Procedural Creature Clicker v3")
clock = pygame.time.Clock()
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "creature_save.json")

# ─────────────── COLORS ───────────────
BG_TOP = (12, 10, 35); BG_BOT = (40, 35, 85); PANEL_BG = (22, 20, 55)
PANEL_BORDER = (75, 65, 150); WHITE = (255, 255, 255); GOLD = (255, 215, 0)
CYAN = (0, 230, 255); GREEN = (80, 255, 120); RED = (255, 80, 80)
ORANGE = (255, 160, 50); PURPLE = (180, 100, 255); PINK = (255, 120, 200)
DARK_PURPLE = (55, 38, 110); MUTED = (155, 150, 195); DIM = (95, 90, 135)
DARK_RED = (120, 20, 20); YELLOW = (255, 255, 80); DARK_GREEN = (20, 80, 30)

# ─────────────── FONTS ───────────────
font_xl = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 36, bold=True)
font_lg = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 24, bold=True)
font_md = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 18)
font_sm = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 14)
font_xs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 11)
font_xxs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 9)

# ─────────────── PROCEDURAL SOUND ───────────────
def make_sound(freq=440, duration=0.08, volume=0.12, wave="sine"):
    try:
        sr = 22050; ns = int(sr * duration); buf = array.array('h')
        for i in range(ns):
            t = i / sr; env = min(1.0, min(i/(sr*0.005), (ns-i)/(sr*0.01)))
            v = math.sin(2*math.pi*freq*t) if wave=="sine" else (1.0 if math.sin(2*math.pi*freq*t)>0 else -1.0) if wave=="square" else random.uniform(-1,1)
            buf.append(max(-32767, min(32767, int(v*volume*env*32767))))
        return pygame.mixer.Sound(buffer=buf)
    except: return None

snd_click = make_sound(520,0.06,0.10,"sine"); snd_crit = make_sound(880,0.15,0.15,"square")
snd_buy = make_sound(660,0.08,0.08,"sine"); snd_achieve = make_sound(1047,0.25,0.12,"sine")
snd_combo = make_sound(700,0.05,0.06,"sine"); snd_prestige = make_sound(440,0.5,0.15,"sine")
snd_orb = make_sound(1200,0.1,0.08,"sine"); snd_ability = make_sound(660,0.3,0.12,"sine")
snd_boss_hit = make_sound(300,0.1,0.10,"square"); snd_boss_die = make_sound(200,0.4,0.15,"noise")
snd_mutation = make_sound(500,0.2,0.10,"sine")

def play(snd):
    if snd:
        try: snd.play()
        except: pass

# ─────────────── SEEDED RNG ───────────────
class SeededRNG:
    def __init__(self, seed_str="default"):
        h = hashlib.sha256(seed_str.encode()).digest()
        self.state = int.from_bytes(h[:8], 'big'); self.pool = []; self._refill()
    def _refill(self):
        for _ in range(256):
            self.state = (self.state*6364136223846793005+1442695040888963407)&0xFFFFFFFFFFFFFFFF
            self.pool.append(((self.state>>16)&0xFFFFFFFF)/0xFFFFFFFF)
    def next(self):
        if not self.pool:
            self._refill()
            return self.pool.pop(0)

    def rand(self,lo,hi): return lo+self.next()*(hi-lo)
    def randint(self,lo,hi): return int(self.next()*(hi-lo+1))+lo
    def choice(self,lst): return lst[self.randint(0,len(lst)-1)]

# ─────────────── GENOME ───────────────
class Genome:
    def __init__(self, seed="creature_1"):
        self.seed=seed; self.rng=SeededRNG(seed)
        self.hue_offset=self.rng.rand(0,1); self.hue_speed=self.rng.rand(0.02,0.08)
        self.body_width_ratio=self.rng.rand(0.85,1.15)
        self.limb_style=self.rng.choice(["stubby","spindly","tentacle","crab"])
        self.wing_style=self.rng.choice(["feathered","bat","crystal","insect"])
        self.tail_style=self.rng.choice(["curved","spiked","forked","flame","tentacle"])
        self.eye_style=self.rng.choice(["round","slit","compound","cyclops"])
        self.pattern_type=self.rng.choice(["spots","stripes","rings","scales","none"])
        self.horn_style=self.rng.choice(["pointed","curved","crystal","antler"])
        self.mouth_style=self.rng.choice(["smile","teeth","beak","tentacles","lamprey"])
        self.aura_style=self.rng.choice(["glow","sparks","rings","dna_helix","constellation"])
        self.ear_type=self.rng.choice(["none","pointed","frilled","antenna"])
        self.leg_count_bias=self.rng.choice([2,4,6,8])
    def level(self,td):
        return 0 if td<=0 else math.log10(td+1)*2.5
    def body_size(self,td): return 30+min(self.level(td),12)*4.2
    def body_segments(self,td): return 1+int(min(self.level(td),10)/2.5)
    def body_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+lv*self.hue_speed+t*0.02)%1.0
        sat=0.5+min(lv,8)*0.05; val=0.6+min(lv,10)*0.03
        r,g,b=colorsys.hsv_to_rgb(hue,min(sat,0.95),min(val,0.95))
        return(int(r*255),int(g*255),int(b*255))
    def accent_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+0.4+lv*self.hue_speed*0.7+t*0.015)%1.0
        r,g,b=colorsys.hsv_to_rgb(hue,0.7,0.8); return(int(r*255),int(g*255),int(b*255))
    def eye_count(self,td): return 1 if self.eye_style=="cyclops" else min(2+int(self.level(td)/3),8)
    def eye_size(self,td): return 5+min(self.level(td),8)*1.2
    def limb_count(self,td):
        lv=self.level(td); return 0 if lv<1.5 else min(self.leg_count_bias,int(lv/1.5)*2)
    def limb_length(self,td): return min(self.level(td),8)*6
    def has_wings(self,td): return self.level(td)>=4.0
    def wing_size(self,td): return 0 if not self.has_wings(td) else min((self.level(td)-4.0)*12,80)
    def tail_length(self,td):
        lv=self.level(td); return 0 if lv<1.0 else min((lv-1.0)*15,120)
    def spike_count(self,td): return int(min(self.level(td),10)*0.8)
    def spike_size(self,td): lv=self.level(td); return 0 if lv<2 else min((lv-2)*3,25)
    def has_pattern(self,td): return self.level(td)>=3.0 and self.pattern_type!="none"
    def pattern_opacity(self,td): return 0 if not self.has_pattern(td) else min((self.level(td)-3.0)/3.0,1.0)
    def has_aura(self,td): return self.level(td)>=5.5
    def aura_intensity(self,td): return 0 if not self.has_aura(td) else min((self.level(td)-5.5)/4.0,1.0)
    def has_horns(self,td): return self.level(td)>=3.5
    def horn_count(self,td): return 0 if not self.has_horns(td) else min(int((self.level(td)-3.5)*1.5)+1,6)
    def horn_size(self,td): return 0 if not self.has_horns(td) else min((self.level(td)-3.5)*5,35)
    def mouth_complexity(self,td): return min(self.level(td)/8.0,1.0)
    def has_ears(self,td): return self.ear_type!="none" and self.level(td)>=2.0
    def ear_size(self,td): return 0 if not self.has_ears(td) else min((self.level(td)-2.0)*5,30)
    def bioluminescence(self,td): return min(self.level(td)/12.0,1.0)
    def proc_name(self,td):
        lv=self.level(td)
        pf=["Proto","Nano","Micro","Alpha","Beta","Gamma","Mega","Giga","Ultra","Hyper","Nova","Cosmic","Elder","Ancient","Omega"]
        bd=["Spore","Cell","Blob","Flop","Wurm","Crawler","Slinker","Lurker","Stalker","Drake","Wyrm","Serpent","Leviathan","Titan","Colossus","Behemoth"]
        sf=["ling","ite","us","ax","on","ix","ar","oth","ius","os","ux","ath","eon","ion","ium","or"]
        return f"{pf[min(int(lv/1.2),len(pf)-1)]}{bd[min(int(lv/1.0),len(bd)-1)]}{sf[min(int(lv/2.0),len(sf)-1)]}"
    def click_multiplier(self,td): return 1+self.level(td)*0.4
    def cps_multiplier(self,td): return 1+self.level(td)*0.3
    def to_dict(self):
        return {k:getattr(self,k) for k in ["seed","hue_offset","hue_speed","body_width_ratio",
            "limb_style","wing_style","tail_style","eye_style","pattern_type","horn_style",
            "mouth_style","aura_style","ear_type","leg_count_bias"]}
    @classmethod
    def from_dict(cls,d):
        g=cls.__new__(cls); g.seed=d["seed"]; g.rng=SeededRNG(g.seed)
        for k in ["hue_offset","hue_speed","body_width_ratio","limb_style","wing_style","tail_style",
                   "eye_style","pattern_type","horn_style","mouth_style","aura_style","ear_type","leg_count_bias"]:
            setattr(g,k,d[k])
        return g
Genome.has_wings_at_level=lambda s,lv:lv>=4.0; Genome.has_horns_at_level=lambda s,lv:lv>=3.5
Genome.has_aura_at_level=lambda s,lv:lv>=5.5; Genome.has_pattern_at_level=lambda s,lv:lv>=3.0

# ─────────────── ACHIEVEMENTS (with rewards) ───────────────
ACHIEVEMENTS = [
    {"id":"first_click","name":"First Contact","desc":"Click the creature","reward_type":"click","reward":1},
    {"id":"click_100","name":"Clicker","desc":"Click 100 times","reward_type":"click","reward":2},
    {"id":"click_1k","name":"Click Master","desc":"Click 1,000 times","reward_type":"click","reward":5},
    {"id":"click_10k","name":"Click Legend","desc":"Click 10,000 times","reward_type":"click","reward":20},
    {"id":"dna_100","name":"DNA Collector","desc":"Earn 100 total DNA","reward_type":"cps","reward":1},
    {"id":"dna_10k","name":"Gene Hoarder","desc":"Earn 10K total DNA","reward_type":"cps","reward":5},
    {"id":"dna_1m","name":"Biotech Baron","desc":"Earn 1M total DNA","reward_type":"click","reward":50},
    {"id":"dna_1b","name":"Genome God","desc":"Earn 1B total DNA","reward_type":"cps","reward":200},
    {"id":"dna_1t","name":"Singularity","desc":"Earn 1T total DNA","reward_type":"click","reward":5000},
    {"id":"combo_5","name":"Combo Starter","desc":"Reach 5x combo","reward_type":"crit_chance","reward":0.01},
    {"id":"combo_20","name":"Combo Frenzy","desc":"Reach 20x combo","reward_type":"crit_chance","reward":0.02},
    {"id":"combo_50","name":"Combo Madness","desc":"Reach 50x combo","reward_type":"crit_mult","reward":1},
    {"id":"crit_first","name":"Lucky Strike","desc":"First critical hit","reward_type":"click","reward":3},
    {"id":"crit_10","name":"Critical Mass","desc":"10 critical hits","reward_type":"crit_chance","reward":0.01},
    {"id":"upgrade_first","name":"Investor","desc":"First upgrade","reward_type":"cps","reward":2},
    {"id":"upgrade_50","name":"Hoarder","desc":"50 total upgrades","reward_type":"cps","reward":20},
    {"id":"prestige_1","name":"Rebirth","desc":"First prestige","reward_type":"click","reward":100},
    {"id":"prestige_5","name":"Transcendence","desc":"Prestige 5 times","reward_type":"prestige_bonus","reward":0.5},
    {"id":"level_5","name":"Evolved","desc":"Reach evo level 5","reward_type":"cps","reward":10},
    {"id":"level_10","name":"Advanced","desc":"Reach evo level 10","reward_type":"click","reward":200},
    {"id":"level_15","name":"Apex","desc":"Reach evo level 15","reward_type":"cps","reward":500},
    {"id":"cps_100","name":"Automation","desc":"Reach 100 DNA/sec","reward_type":"cps","reward":25},
    {"id":"cps_10k","name":"Factory","desc":"Reach 10K DNA/sec","reward_type":"click","reward":500},
    {"id":"boss_1","name":"Boss Slayer","desc":"Defeat first boss","reward_type":"click","reward":50},
    {"id":"boss_10","name":"Boss Hunter","desc":"Defeat 10 bosses","reward_type":"crit_chance","reward":0.03},
    {"id":"orb_50","name":"Orb Catcher","desc":"Collect 50 orbs","reward_type":"cps","reward":15},
    {"id":"mutation_5","name":"Mutant","desc":"Experience 5 mutations","reward_type":"click","reward":30},
]

# ─────────────── ACTIVE ABILITIES ───────────────
ABILITIES = [
    {"id":"storm","name":"DNA Storm","key":"Q","desc":"10x click for 5s","duration":5,"cooldown":30,"unlock_dna":500,"color":CYAN},
    {"id":"warp","name":"Time Warp","key":"W","desc":"10x CPS for 8s","duration":8,"cooldown":45,"unlock_dna":5000,"color":PURPLE},
    {"id":"surge","name":"Crit Surge","key":"E","desc":"100% crit for 6s","duration":6,"cooldown":35,"unlock_dna":50000,"color":RED},
    {"id":"frenzy","name":"Frenzy","key":"R","desc":"No combo decay 10s","duration":10,"cooldown":40,"unlock_dna":500000,"color":GREEN},
]

# ─────────────── MUTATION EVENTS ───────────────
MUTATIONS = [
    {"id":"dna_frenzy","name":"DNA Frenzy","desc":"2x all income!","mult_type":"all","mult_value":2.0,"duration":30,"color":GOLD},
    {"id":"golden_touch","name":"Golden Touch","desc":"3x click power!","mult_type":"click","mult_value":3.0,"duration":25,"color":YELLOW},
    {"id":"slow_meta","name":"Slow Metabolism","desc":"0.5x CPS...","mult_type":"cps","mult_value":0.5,"duration":20,"color":RED},
    {"id":"lucky_stars","name":"Lucky Stars","desc":"25% crit chance!","mult_type":"crit","mult_value":25.0,"duration":20,"color":ORANGE},
    {"id":"evolve_burst","name":"Evolution Burst","desc":"Visual evolution +3!","mult_type":"evo","mult_value":3.0,"duration":35,"color":PINK},
    {"id":"mega_combo","name":"Mega Combo","desc":"Combo starts at 10x!","mult_type":"combo","mult_value":10.0,"duration":15,"color":CYAN},
]

# ─────────────── BOSS DATA ───────────────
BOSS_NAMES = ["Alpha Slime","Crystal Golem","Shadow Wraith","Void Serpent","Storm Titan","Chaos Beast","Dimensional Eye","Cosmic Horror"]
BOSS_COLORS = [(100,200,100),(150,180,255),(120,50,180),(80,0,120),(200,200,50),(200,50,50),(200,100,255),(100,0,200)]

# ─────────────── BACKGROUND ───────────────
class Starfield:
    def __init__(self):
        self.stars=[{"x":random.uniform(0,WIDTH),"y":random.uniform(0,HEIGHT),
            "b":random.uniform(0.2,1),"s":random.uniform(1,4),"sz":random.uniform(0.5,2.5),"al":random.uniform(0,8)} for _ in range(200)]
    def draw(self,surf,lv,t):
        for s in self.stars:
            if lv<s["al"]:
                continue
                a=min(1,(lv-s["al"])*0.5); tw=(math.sin(t*s["s"]+s["x"])+1)*0.5

                br=s["b"]*a*(0.4+0.6*tw); c=int(255*br); sz=max(1,int(s["sz"]*(0.5+a*0.5)))

            if sz<=1:
                surf.set_at((int(s["x"])%WIDTH,int(s["y"])%HEIGHT),(c,c,min(255,int(c*1.1))))
            else: pygame.draw.circle(surf,(c,c,min(255,int(c*1.1))),(int(s["x"])%WIDTH,int(s["y"])%HEIGHT),sz)

class AmbientParticle:
    def __init__(self): self.reset(); self.y=random.uniform(0,HEIGHT)
    def reset(self):
        self.x=random.uniform(0,WIDTH); self.y=-5; self.vy=random.uniform(10,30)
        self.vx=random.uniform(-8,8); self.sz=random.uniform(1,3); self.a=random.uniform(0.1,0.4)
        self.color=random.choice([(100,200,255),(150,100,255),(100,255,150)])
    def update(self,dt):
        self.x+=self.vx*dt; self.y+=self.vy*dt
        if self.y>HEIGHT+10:
            self.reset()
    def draw(self,surf,lv):
        if lv<2:
            return; a=min(1,(lv-2)*0.2)*self.a; c=tuple(int(v*a) for v in self.color)
            pygame.draw.circle(surf,c,(int(self.x),int(self.y)),max(1,int(self.sz)))


# ─────────────── EFFECTS ───────────────
class Particle:
    def __init__(self,x,y,color,vx=None,vy=None,lifetime=1.0,size=4):
        self.x=x;self.y=y;self.color=color;self.vx=vx or random.uniform(-80,80);self.vy=vy or random.uniform(-120,-30)
        self.lifetime=self.max_life=lifetime;self.size=size
    def update(self,dt): self.x+=self.vx*dt;self.y+=self.vy*dt;self.vy+=100*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,self.lifetime/self.max_life);c=tuple(int(v*a) for v in self.color);sz=max(1,int(self.size*a))
        pygame.draw.circle(s,c,(int(self.x),int(self.y)),sz)
    @property
    def alive(self): return self.lifetime>0

class FloatingText:
    def __init__(self,x,y,text,color=GOLD,size="md"):
        self.x=x;self.y=y;self.text=text;self.color=color;self.lifetime=self.max_life=1.4
        self.font={"sm":font_sm,"md":font_md,"lg":font_lg}[size]
    def update(self,dt): self.y-=55*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,min(1,self.lifetime/(self.max_life*0.5)))
        c=tuple(int(v*a+bg*(1-a)) for v,bg in zip(self.color,BG_TOP))
        t=self.font.render(self.text,True,c);s.blit(t,(self.x-t.get_width()//2,int(self.y)))
    @property
    def alive(self): return self.lifetime>0

class Toast:
    def __init__(self,title,desc,icon_color=GOLD):
        self.title=title;self.desc=desc;self.icon_color=icon_color;self.lifetime=self.max_life=4.0;self.slide=0
    def update(self,dt): self.lifetime-=dt;self.slide=min(1,self.slide+dt*5)
    def draw(self,s,idx):
        if self.lifetime<=0:
            return; fade=min(1,self.lifetime/1.0)
            tx=WIDTH-320+(320+10-int(330*self.slide)); y=20+idx*60; w,h=300,52

            ts=pygame.Surface((w,h),pygame.SRCALPHA)

            pygame.draw.rect(ts,(30,25,70,int(220*fade)),(0,0,w,h),border_radius=10)

            pygame.draw.rect(ts,(*self.icon_color,int(200*fade)),(0,0,w,h),2,border_radius=10)

            s.blit(ts,(int(tx),y))

            pygame.draw.circle(s,self.icon_color,(int(tx+18),y+16),8)

            star=font_xs.render("*",True,WHITE);s.blit(star,(int(tx+14),y+9))

            tc=tuple(int(min(255,v*fade)) for v in GOLD);tt=font_sm.render(self.title,True,tc);s.blit(tt,(int(tx+34),y+6))

            dc=tuple(int(min(255,v*fade)) for v in MUTED);dt2=font_xs.render(self.desc,True,dc);s.blit(dt2,(int(tx+34),y+26))

    @property
    def alive(self): return self.lifetime>0

class Sparkline:
    def __init__(self,mp=120): self.data=[];self.max_p=mp;self.timer=0;self.interval=0.5
    def update(self,dt,v):
        self.timer+=dt
        if self.timer>=self.interval:
            self.timer=0;self.data.append(v)
        if len(self.data)>self.max_p:
            self.data.pop(0)
    def draw(self,s,x,y,w,h,color=CYAN):
        if len(self.data)<2:
            return;mv=max(self.data) or 1
            pygame.draw.rect(s,DARK_PURPLE,(x,y,w,h),border_radius=4)

            pygame.draw.rect(s,PANEL_BORDER,(x,y,w,h),1,border_radius=4)

            pts=[(int(x+2+(i/(self.max_p-1))*(w-4)),int(y+h-2-(v/mv)*(h-4))) for i,v in enumerate(self.data)]

        if len(pts)>1:
            pygame.draw.lines(s,color,False,pts,1)
            lbl=font_xxs.render(f"{fmt(self.data[-1])}/s",True,MUTED);s.blit(lbl,(x+3,y+1))


# ─────────────── FALLING ORBS ───────────────
class DNAOrb:
    def __init__(self, total_dna):
        self.x=random.uniform(30,590); self.y=-20; self.vy=random.uniform(30,60)
        self.vx=random.uniform(-10,10); self.alive=True; self.pulse=random.uniform(0,6)
        # Value scales with progression
        scale = max(1, math.log10(total_dna+1))
        r = random.random()
        if r < 0.6:
            self.value=scale*5; self.radius=8; self.color=GREEN; self.name="Small"
        elif r < 0.85: self.value=scale*25; self.radius=12; self.color=CYAN; self.name="Medium"
        elif r < 0.97: self.value=scale*150; self.radius=16; self.color=PURPLE; self.name="Large"
        else: self.value=scale*1000; self.radius=20; self.color=GOLD; self.name="Golden!"
    def update(self,dt):
        self.y+=self.vy*dt; self.x+=self.vx*dt+math.sin(self.y*0.02)*0.5; self.pulse+=dt*4
        if self.y>HEIGHT+30:
            self.alive=False
    def draw(self,s):
        p=0.7+0.3*math.sin(self.pulse); r=int(self.radius*p)
        gs=pygame.Surface((r*4,r*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,40),(r*2,r*2),r*2)
        pygame.draw.circle(gs,(*self.color,120),(r*2,r*2),r)
        pygame.draw.circle(gs,(*WHITE,180),(r*2,r*2),max(2,r//2))
        s.blit(gs,(int(self.x-r*2),int(self.y-r*2)))
    def hit_test(self,mx,my): return math.sqrt((mx-self.x)**2+(my-self.y)**2)<self.radius*1.5

# ─────────────── BOSS ───────────────
class Boss:
    def __init__(self, tier, total_dna):
        self.tier=min(tier, len(BOSS_NAMES)-1)
        self.name=BOSS_NAMES[self.tier]; self.color=BOSS_COLORS[self.tier]
        self.max_hp=int((100+self.tier*300)*(1+math.log10(total_dna+1)*2))
        self.hp=self.max_hp; self.x=310; self.y=300; self.alive=True
        self.reward=int(self.max_hp*5*(1+self.tier*0.5))
        self.timer=45+self.tier*10; self.flash=0; self.shake=0
        self.spawn_anim=1.0
    def update(self,dt):
        self.timer-=dt; self.flash=max(0,self.flash-dt); self.shake=max(0,self.shake-dt)
        self.spawn_anim=max(0,self.spawn_anim-dt*2)
        if self.timer<=0:
            self.alive=False
        if self.hp<=0:
            self.alive=False
    def damage(self,amount):
        self.hp-=amount; self.flash=0.15; self.shake=0.08
    def draw(self,s,t):
        if not self.alive:
            return
            sx=int(self.shake*20*(random.random()*2-1)); sy=int(self.shake*15*(random.random()*2-1))

            cx,cy=self.x+sx,self.y+sy; scale=min(1,self.spawn_anim)*1.0

        # Warning flash
        if self.spawn_anim>0.5:
            ws=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            a=int(60*(self.spawn_anim-0.5)*2*(math.sin(t*15)+1)*0.5)
            ws.fill((*RED,max(0,min(255,a)))); s.blit(ws,(0,0))
        # Body
        bob=math.sin(t*1.5)*8*scale; size=(50+self.tier*10)*scale
        # Aura
        asurf=pygame.Surface((int(size*6),int(size*6)),pygame.SRCALPHA)
        pulse=(math.sin(t*3)+1)*0.5
        pygame.draw.circle(asurf,(*self.color,int(30*(0.5+0.5*pulse))),(int(size*3),int(size*3)),int(size*2.5))
        s.blit(asurf,(int(cx-size*3),int(cy-size*3+bob)))
        # Spiky body
        pts=[]
        for a in range(0,360,15):
            rad=math.radians(a); spike=math.sin(a*3+t*2)*5*scale
            r=size+spike+(15 if a%30<15 else 0)*scale
            pts.append((cx+math.sin(rad)*r,cy+math.cos(rad)*r*0.8+bob))
        body_c=self.color if self.flash<=0 else WHITE
        pygame.draw.polygon(s,body_c,pts)
        pygame.draw.polygon(s,tuple(min(255,c+60) for c in self.color),pts,2)
        # Eyes
        for side in [-1,1]:
            ex=int(cx+side*15*scale); ey=int(cy-10*scale+bob)
            pygame.draw.circle(s,WHITE,(ex,ey),int(8*scale))
            pygame.draw.circle(s,(200,0,0),(ex+int(side*2*scale),ey),int(4*scale))
            pygame.draw.circle(s,WHITE,(ex+int(side*1*scale),ey-int(2*scale)),max(1,int(2*scale)))
        # HP bar
        bw=200; bh=12; bx=cx-bw//2; by=cy-int(size*1.2+bob)
        pygame.draw.rect(s,DARK_RED,(bx,by,bw,bh),border_radius=4)
        hw=int(bw*max(0,self.hp/self.max_hp))
        if hw>0:
            for px in range(hw):
                ratio=px/bw; c=(int(200*(1-ratio)+50*ratio),int(50+150*ratio),50)
                pygame.draw.line(s,c,(bx+px,by),(bx+px,by+bh-1))
        pygame.draw.rect(s,WHITE,(bx,by,bw,bh),1,border_radius=4)
        hp_txt=font_xs.render(f"{max(0,self.hp):.0f}/{self.max_hp}",True,WHITE)
        s.blit(hp_txt,(cx-hp_txt.get_width()//2,by-1))
        # Name & timer
        nt=font_md.render(f"BOSS: {self.name}",True,RED)
        s.blit(nt,(cx-nt.get_width()//2,by-22))
        tc=RED if self.timer<10 else ORANGE if self.timer<20 else MUTED
        tt=font_sm.render(f"Time: {self.timer:.0f}s  |  Reward: {fmt(self.reward)}",True,tc)
        s.blit(tt,(cx-tt.get_width()//2,by+bh+4))

# ─────────────── UPGRADES ───────────────
UPGRADES = [
    {"name":"Click Power","desc":"+1 DNA/click","base_cost":10,"cost_mult":1.15,"type":"click","value":1,"key":"1"},
    {"name":"Auto Cell","desc":"+0.5 DNA/sec","base_cost":25,"cost_mult":1.18,"type":"cps","value":0.5,"key":"2"},
    {"name":"Click Boost","desc":"+3 DNA/click","base_cost":200,"cost_mult":1.15,"type":"click","value":3,"key":"3"},
    {"name":"Amoeba Swarm","desc":"+2 DNA/sec","base_cost":500,"cost_mult":1.18,"type":"cps","value":2,"key":"4"},
    {"name":"Mega Click","desc":"+15 DNA/click","base_cost":5e3,"cost_mult":1.15,"type":"click","value":15,"key":"5"},
    {"name":"Bacteria Colony","desc":"+10 DNA/sec","base_cost":1e4,"cost_mult":1.18,"type":"cps","value":10,"key":"6"},
    {"name":"Hyper Click","desc":"+100 DNA/click","base_cost":1e5,"cost_mult":1.15,"type":"click","value":100,"key":"7"},
    {"name":"Biome Engine","desc":"+75 DNA/sec","base_cost":2e5,"cost_mult":1.18,"type":"cps","value":75,"key":"8"},
    {"name":"Omega Click","desc":"+1K DNA/click","base_cost":2e6,"cost_mult":1.15,"type":"click","value":1000,"key":"9"},
    {"name":"Evolution Core","desc":"+500 DNA/sec","base_cost":5e6,"cost_mult":1.18,"type":"cps","value":500,"key":"0"},
    {"name":"Singularity Tap","desc":"+10K/click","base_cost":5e7,"cost_mult":1.15,"type":"click","value":1e4,"key":""},
    {"name":"Genesis Engine","desc":"+5K DNA/sec","base_cost":1e8,"cost_mult":1.18,"type":"cps","value":5e3,"key":""},
]
BUY_AMOUNTS=[1,10,100,-1]; BUY_LABELS=["x1","x10","x100","MAX"]

# ─────────────── CREATURE RENDERER (compact) ───────────────
# ─────────────── CREATURE RENDERER ───────────────
class CreatureRenderer:
    def __init__(self, genome):
        self.g = genome

    def draw(self, surface, cx, cy, td, t, hover=False):
        g = self.g
        sf = 1.0 + hover * 0.07
        bob = math.sin(t * 2.0) * 6
        color = g.body_color(td, t)
        acc = g.accent_color(td, t)
        bs = g.body_size(td) * sf
        cy_b = cy + bob
        # Shadow
        sw, sh = int(bs * 2.2), max(4, int(bs * 0.3))
        shadow_surf = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 40), (0, 0, sw * 2, sh * 2))
        surface.blit(shadow_surf, (cx - sw, cy + bs * 0.9))
        # Draw layers
        if g.has_aura(td):
            self._draw_aura(surface, cx, cy_b, bs, td, t, color, acc)
        if g.tail_length(td) > 0:
            self._draw_tail(surface, cx, cy_b, bs, td, t, color, acc)
        if g.limb_count(td) > 0:
            self._draw_limbs(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_wings(td):
            self._draw_wings(surface, cx, cy_b, bs, td, t, color, acc)
        self._draw_body(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_pattern(td):
            self._draw_pattern(surface, cx, cy_b, bs, td, t, color, acc)
        if g.spike_count(td) > 0:
            self._draw_spikes(surface, cx, cy_b, bs, td, t, acc)
        hx, hy = cx - bs * 0.6, cy_b - bs * 0.5
        if g.has_ears(td):
            self._draw_ears(surface, hx, hy, bs, td, t, color, acc)
        if g.has_horns(td):
            self._draw_horns(surface, hx, hy, bs, td, t, acc)
        self._draw_eyes(surface, hx, hy, bs, td, t, color)
        self._draw_mouth(surface, hx, hy, bs, td, t, acc)
        # Bioluminescent glow
        bio = g.bioluminescence(td)
        if bio > 0.1:
            gs = pygame.Surface((int(bs * 4), int(bs * 4)), pygame.SRCALPHA)
            pulse = (math.sin(t * 3) + 1) * 0.5
            a = int(bio * (30 + 25 * pulse))
            pygame.draw.circle(gs, (*color, a), (int(bs * 2), int(bs * 2)), int(bs * 1.6))
            surface.blit(gs, (int(cx - bs * 2), int(cy_b - bs * 2)))

    def _draw_body(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        segs = g.body_segments(td)
        if segs <= 1:
            pts = []
            for a in range(360):
                r = math.radians(a)
                w = math.sin(r * 3 + t * 3) * 3 + math.sin(r * 5 + t * 2) * 2
                rx = (bs + w) * g.body_width_ratio
                ry = bs * 0.85 + w * 0.5
                pts.append((cx + math.sin(r) * rx, cy + math.cos(r) * ry))
            pygame.draw.polygon(s, col, pts)
            hl_r = max(3, int(bs * 0.3))
            hl_color = tuple(min(255, c + 60) for c in col)
            pygame.draw.circle(s, hl_color, (int(cx - bs * 0.25), int(cy - bs * 0.3)), hl_r)
        else:
            tl = bs * 2 * segs * 0.6
            sr = bs * 0.65
            for i in range(segs):
                ratio = i / max(segs - 1, 1)
                wave = math.sin(t * 2 + i * 0.8) * 12 * (1 - ratio * 0.3)
                sx = cx - tl / 2 + ratio * tl + wave
                sy = cy + ratio * bs * 0.3
                sri = sr * (1 - ratio * 0.25)
                wb = math.sin(t * 3 + i * 2) * 2
                sp = []
                for a in range(360):
                    rad = math.radians(a)
                    sp.append((sx + math.sin(rad) * (sri + wb), sy + math.cos(rad) * (sri * 0.8 + wb * 0.5)))
                seg_c = tuple(int(c * (1 - ratio * 0.15)) for c in col)
                pygame.draw.polygon(s, seg_c, sp)
                if i == 0:
                    pygame.draw.circle(s, tuple(min(255, c + 50) for c in col),
                                       (int(sx - sri * 0.2), int(sy - sri * 0.3)), max(2, int(sri * 0.3)))

    def _draw_eyes(self, s, hx, hy, bs, td, t, col):
        g = self.g
        count = g.eye_count(td)
        es = g.eye_size(td)
        style = g.eye_style
        if style == "cyclops":
            positions = [(0, 0)]
            es *= 1.8
        elif style == "compound":
            positions = []
            for row in range(min((count + 2) // 3, 3)):
                c_in_row = min(count - row * 3, 3)
                for c_ in range(c_in_row):
                    positions.append((c_ - (c_in_row - 1) / 2, row - 0.5))
            es *= 0.7
        else:
            positions = [(i - (count - 1) / 2, 0) for i in range(count)]
        for px, py in positions:
            ex = hx + px * es * 1.6
            ey = hy + py * es * 1.6 - bs * 0.1
            if style == "slit":
                pygame.draw.ellipse(s, WHITE, (int(ex - es), int(ey - es * 0.7), int(es * 2), int(es * 1.4)))
                pygame.draw.ellipse(s, (20, 20, 40),
                    (int(ex - es * 0.15), int(ey - es * 0.6), int(es * 0.3), int(es * 1.2)))
            elif style == "compound":
                for ci in range(6):
                    angle = ci * math.pi * 2 / 6 + t * 0.5
                    cr = es * 0.6
                    ccx = ex + math.cos(angle) * es * 0.4
                    ccy = ey + math.sin(angle) * es * 0.4
                    pygame.draw.circle(s, (200, 200, 255), (int(ccx), int(ccy)), max(1, int(cr)))
                    pygame.draw.circle(s, (30, 30, 60), (int(ccx), int(ccy)), max(1, int(cr * 0.5)))
            else:
                pygame.draw.circle(s, WHITE, (int(ex), int(ey)), int(es))
                look = math.sin(t * 2) * es * 0.2
                pr = es * 0.5
                pygame.draw.circle(s, (20, 20, 40), (int(ex + look), int(ey)), int(pr))
                pygame.draw.circle(s, WHITE, (int(ex + look - pr * 0.3), int(ey - pr * 0.3)), max(1, int(pr * 0.3)))

    def _draw_mouth(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        comp = g.mouth_complexity(td)
        if comp < 0.1:
            return
        mx_p = hx + bs * 0.3
        my_p = hy + bs * 0.2
        style = g.mouth_style
        if style == "smile" or comp < 0.3:
            mw = bs * 0.5 * comp
            mh = bs * 0.2 * comp
            if mw > 3:
                pygame.draw.arc(s, acc,
                    (int(mx_p - mw), int(my_p - mh), int(mw * 2), int(mh * 2)),
                    math.pi + 0.3, 2 * math.pi - 0.3, max(1, int(2 * comp + 1)))
        if comp > 0.3:
            if style == "teeth":
                tw = bs * 0.4
                for i in range(int(3 + comp * 5)):
                    tx = mx_p - tw / 2 + (i / max(int(3 + comp * 5) - 1, 1)) * tw
                    th = 3 + comp * 5
                    pygame.draw.polygon(s, WHITE, [
                        (int(tx - 2), int(my_p)), (int(tx + 2), int(my_p)), (int(tx), int(my_p + th))])
            elif style == "beak":
                bl = bs * 0.4 * comp
                pygame.draw.polygon(s, (255, 200, 80), [
                    (int(mx_p), int(my_p - 4)), (int(mx_p + bl), int(my_p)), (int(mx_p), int(my_p + 4))])
            elif style == "tentacles":
                for i in range(int(2 + comp * 4)):
                    ba = -0.5 + i * (1.0 / max(int(2 + comp * 4) - 1, 1))
                    pts = [(int(mx_p), int(my_p))]
                    for j in range(1, 6):
                        tr = j / 5
                        w = math.sin(t * 5 + i + j * 0.7) * 8 * tr
                        pts.append((int(mx_p + tr * bs * 0.5 * comp + w),
                                    int(my_p + tr * bs * 0.3 * comp + ba * bs * 0.2 * tr)))
                    if len(pts) > 1:
                        pygame.draw.lines(s, acc, False, pts, max(1, int(2)))
            elif style == "lamprey":
                mr = int(bs * 0.15 * comp)
                if mr > 2:
                    pygame.draw.circle(s, (40, 10, 10), (int(mx_p), int(my_p)), mr)
                    for i in range(int(6 + comp * 10)):
                        a = i * math.pi * 2 / int(6 + comp * 10)
                        pygame.draw.line(s, WHITE,
                            (int(mx_p + math.cos(a) * mr * 0.6), int(my_p + math.sin(a) * mr * 0.6)),
                            (int(mx_p + math.cos(a) * mr), int(my_p + math.sin(a) * mr)), 1)

    def _draw_limbs(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        count = g.limb_count(td)
        length = g.limb_length(td)
        style = g.limb_style
        if count == 0 or length < 3:
            return
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            idx = i // 2
            tp = count // 2
            spread = bs * 1.2
            bx = cx - spread / 2 + (idx / max(tp - 1, 1)) * spread if tp > 1 else cx
            by = cy + bs * 0.6
            anim = math.sin(t * 4 + i * 1.2) * 0.3
            if style == "tentacle":
                pts = [(int(bx + side * bs * 0.4), int(by))]
                for j in range(1, 8):
                    tr = j / 7
                    w = math.sin(t * 5 + i + j * 0.8) * 12 * tr
                    pts.append((int(bx + side * (bs * 0.4 + length * tr) + w),
                                int(by + length * tr * 0.5 + anim * length * tr)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(4)))
            elif style == "crab":
                kx = bx + side * (bs * 0.5 + length * 0.5)
                ky = by + length * 0.3 + anim * 10
                fx = kx + side * length * 0.4
                fy = by + length * 0.8
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(kx), int(ky)), max(2, int(4)))
                pygame.draw.line(s, acc, (int(kx), int(ky)),
                               (int(fx), int(fy)), max(2, int(3)))
                if i < 2:
                    cs = max(2, int(bs * 0.15))
                    pygame.draw.circle(s, col, (int(fx), int(fy)), cs)
            elif style == "spindly":
                px, py = bx + side * bs * 0.3, by
                for j in range(3):
                    tr = (j + 1) / 3
                    nx = px + side * length * 0.35
                    ny = py + length * 0.3 + anim * 8 * tr
                    pygame.draw.line(s, acc, (int(px), int(py)), (int(nx), int(ny)), max(1, int(2)))
                    pygame.draw.circle(s, col, (int(nx), int(ny)), max(1, int(3)))
                    px, py = nx, ny
            else:  # stubby
                fx = bx + side * (bs * 0.5 + length * 0.3)
                fy = by + length * 0.7 + anim * 8
                lw = max(3, int(bs * 0.15))
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(fx), int(fy)), lw)
                pygame.draw.circle(s, col, (int(fx), int(fy)), max(2, int(lw * 0.8)))

    def _draw_wings(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        ws = g.wing_size(td)
        if ws < 3:
            return
        style = g.wing_style
        flap = math.sin(t * 3) * 15
        for side in [-1, 1]:
            if style == "bat":
                pts = [
                    (cx + side * bs * 0.3, cy - bs * 0.3),
                    (cx + side * ws, cy - bs * 0.5 + flap),
                    (cx + side * ws * 0.7, cy - bs * 0.1 + flap * 0.6),
                    (cx + side * ws * 1.1, cy + bs * 0.1 + flap * 0.8),
                    (cx + side * ws * 0.5, cy + bs * 0.2)]
                wc = tuple(max(0, c - 50) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])
                pygame.draw.polygon(s, acc, [(int(p[0]), int(p[1])) for p in pts], 2)
            elif style == "feathered":
                for layer in range(3):
                    off = layer * 8
                    pts = [
                        (cx + side * bs * 0.2, cy - bs * 0.2),
                        (cx + side * (ws - off), cy - bs * (0.6 + layer * 0.2) + flap * (1 - layer * 0.2)),
                        (cx + side * (ws * 0.8 - off), cy + bs * 0.1 + flap * 0.5)]
                    lc = tuple(min(255, c + layer * 20) for c in col)
                    pygame.draw.polygon(s, lc, [(int(p[0]), int(p[1])) for p in pts])
            elif style == "crystal":
                for j in range(4):
                    a = math.radians(-30 + j * 25 + side * 20) + math.sin(t * 2) * 0.1
                    d = ws * (0.6 + j * 0.12)
                    tx = cx + side * math.cos(a) * d
                    ty = cy - abs(math.sin(a)) * d * 0.7 + flap * 0.3
                    pts = [(int(cx + side * bs * 0.3), int(cy - bs * 0.3)),
                           (int(tx), int(ty)),
                           (int(cx + side * 10), int(cy))]
                    als = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    pygame.draw.polygon(als, (*acc, 100), pts)
                    s.blit(als, (0, 0))
                    pygame.draw.polygon(s, acc, pts, 1)
            else:  # insect
                pts = [
                    (cx + side * bs * 0.2, cy - bs * 0.1),
                    (cx + side * ws, cy - bs * 0.8 + flap),
                    (cx + side * ws * 0.9, cy - bs * 0.2 + flap * 0.4),
                    (cx + side * ws * 0.3, cy + bs * 0.3)]
                wc = tuple(max(0, c - 30) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])

    def _draw_tail(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        length = g.tail_length(td)
        if length < 3:
            return
        style = g.tail_style
        segs = max(3, int(length / 10))
        pts = []
        for i in range(segs + 1):
            tr = i / segs
            w = math.sin(t * 3 + tr * 4) * (10 + tr * 15)
            tx = cx + bs * 0.7 + tr * length + w
            ty = cy + tr * bs * 0.3 + math.sin(t * 2 + tr * 3) * 5
            pts.append((tx, ty))
            sr = max(2, int(bs * 0.3 * (1 - tr * 0.7)))
            sc = tuple(int(c * (1 - tr * 0.2)) for c in col)
            pygame.draw.circle(s, sc, (int(tx), int(ty)), sr)
        if style == "spiked":
            for i in range(2, segs, 2):
                tr = i / segs
                px, py = pts[i]
                sh = 8 + tr * 10
                pygame.draw.polygon(s, acc, [(int(px - 3), int(py)),
                                                  (int(px + 3), int(py)),
                                                  (int(px), int(py - sh))])
        elif style == "forked":
            tx, ty = pts[-1]
            fl = length * 0.2
            for d in [-1, 1]:
                pygame.draw.line(s, acc, (int(tx), int(ty)),
                               (int(tx + fl + math.sin(t * 4 + d) * 5), int(ty + d * fl * 0.5)),
                               max(1, int(3)))
        elif style == "flame":
            tx, ty = pts[-1]
            for _ in range(5):
                fc = random.choice([(255, 100, 0), (255, 200, 0), (255, 50, 0)])
                pygame.draw.circle(s, fc,
                                   (int(tx + random.randint(-8, 12)), int(ty + random.randint(-12, 12))),
                                   random.randint(3, int(6 + g.level(td))))
        elif style == "tentacle":
            tx, ty = pts[-1]
            for d in [-1, 1]:
                tent_pts = [(int(tx), int(ty))]
                for j in range(1, 5):
                    tr = j / 4
                    w = math.sin(t * 6 + d + j) * 8
                    tent_pts.append((int(tx + d * tr * 20 + w), int(ty + tr * 15)))
                if len(tent_pts) > 1:
                    pygame.draw.lines(s, acc, False, tent_pts, max(1, int(2)))

    def _draw_spikes(self, s, cx, cy, bs, td, t, acc):
        g = self.g
        count = g.spike_count(td)
        size = g.spike_size(td)
        if count < 1 or size < 2:
            return
        for i in range(count):
            a = (i / count) * math.pi * 2 + 0.5
            if math.sin(a) > 0.2:
                continue
            sx = cx + math.cos(a) * bs * 0.85
            sy = cy + math.sin(a) * bs * 0.85
            pygame.draw.polygon(s, acc, [
                (int(sx - math.sin(a) * 3), int(sy + math.cos(a) * 3)),
                (int(sx + math.sin(a) * 3), int(sy - math.cos(a) * 3)),
                (int(sx + math.cos(a) * size), int(sy + math.sin(a) * size))])

    def _draw_horns(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        count = g.horn_count(td)
        size = g.horn_size(td)
        style = g.horn_style
        if count < 1 or size < 3:
            return
        for i in range(count):
            off = (i - (count - 1) / 2) * 12 if count > 1 else 0
            bx, by = hx + off, hy - bs * 0.4
            if style == "pointed":
                pygame.draw.polygon(s, acc, [(int(bx - 4), int(by)),
                                                  (int(bx + 4), int(by)),
                                                  (int(bx + off * 0.3), int(by - size))])
            elif style == "curved":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.4 + math.sin(tr * math.pi) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
            elif style == "crystal":
                pygame.draw.polygon(s, acc, [(int(bx), int(by - size)),
                                                  (int(bx - 5), int(by)),
                                                  (int(bx + 5), int(by))])
            elif style == "antler":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.5 + math.sin(tr * 3) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
                if len(pts) > 3:
                    bp = pts[2]
                    pygame.draw.line(s, acc, bp,
                                   (int(bp[0] + (15 if off >= 0 else -15)), int(bp[1] - 10)),
                                   max(1, int(2)))

    def _draw_ears(self, s, hx, hy, bs, td, t, col, acc):
        g = self.g
        es = g.ear_size(td)
        if es < 3:
            return
        if g.ear_type == "pointed":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.5
                ey = hy - bs * 0.3
                pygame.draw.polygon(s, col, [(int(ex - 8), int(ey)),
                                                  (int(ex + 8), int(ey)),
                                                  (int(ex + side * 5), int(ey - es))])
                pygame.draw.polygon(s, acc, [(int(ex - 8), int(ey)),
                                                   (int(ex + 8), int(ey)),
                                                   (int(ex + side * 5), int(ey - es))], 1)
        elif g.ear_type == "frilled":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.4
                ey = hy - bs * 0.2
                fp = []
                for j in range(8):
                    a = math.radians(-90 + (j / 7) * 60 * side)
                    r = es * (0.5 + math.sin(j * 1.5) * 0.3)
                    fp.append((int(ex + math.cos(a) * r * side), int(ey + math.sin(a) * r)))
                if len(fp) > 2:
                    pygame.draw.lines(s, acc, False, fp, 2)
        elif g.ear_type == "antenna":
            for side in [-1, 1]:
                bx = hx + side * bs * 0.3
                by = hy - bs * 0.3
                w = math.sin(t * 5 + side) * 5
                tx = bx + side * es * 0.5 + w
                ty = by - es + w
                pygame.draw.line(s, acc, (int(bx), int(by)), (int(tx), int(ty)), 2)
                glow = (math.sin(t * 4 + side * 2) + 1) * 0.5
                gc = tuple(int(min(255, c * (0.5 + 0.5 * glow))) for c in acc)
                pygame.draw.circle(s, gc, (int(tx), int(ty)), max(2, int(4 * glow + 2)))

    def _draw_pattern(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        op = g.pattern_opacity(td)
        pt = g.pattern_type
        if op < 0.05:
            return
        pc = tuple(int(c * op + bg * (1 - op)) for c, bg in zip(acc, col))
        if pt == "spots":
            for i in range(int(5 + g.level(td) * 1.5)):
                a = i * 2.3 + 0.5
                d = bs * (0.2 + (i % 3) * 0.2)
                pygame.draw.circle(s, pc, (int(cx + math.cos(a) * d), int(cy + math.sin(a) * d * 0.7)),
                                   max(2, int(bs * 0.1 * op)))
        elif pt == "stripes":
            for i in range(-3, 4):
                sx = cx + i * bs * 0.25
                sh = int(bs * 1.2)
                pygame.draw.line(s, pc,
                    (int(sx + math.sin(i + t) * 3), int(cy - sh // 2)),
                    (int(sx + math.sin(i + t + 1) * 3), int(cy + sh // 2)),
                    max(1, int(2 * op)))
        elif pt == "rings":
            for i in range(1, 4):
                pygame.draw.circle(s, pc, (int(cx), int(cy)),
                                   int(bs * 0.3 * i * op), max(1, int(2 * op)))
        elif pt == "scales":
            for row in range(-2, 3):
                for c_ in range(-2, 3):
                    sx = cx + c_ * bs * 0.3 + (row % 2) * bs * 0.15
                    sy = cy + row * bs * 0.25
                    if math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2) < bs * 0.8:
                        sr = int(bs * 0.12 * op)
                        pygame.draw.arc(s, pc,
                            (int(sx - sr), int(sy - sr), sr * 2, sr * 2),
                            0, math.pi, max(1, int(1.5 * op)))

    def _draw_aura(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        intensity = g.aura_intensity(td)
        style = g.aura_style
        if intensity < 0.05:
            return
        if style == "glow":
            for layer in range(3):
                r = int(bs * (1.5 + layer * 0.4) * intensity)
                a = int(30 * intensity * (1 - layer * 0.25))
                gs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                p = (math.sin(t * 3 + layer) + 1) * 0.5
                pygame.draw.circle(gs, (*col, int(a * (0.7 + 0.3 * p))),
                                   (r + 2, r + 2), r)
                s.blit(gs, (cx - r - 2, cy - r - 2))
        elif style == "sparks":
            for i in range(int(8 * intensity)):
                a = t * (1.5 + i * 0.3) + i * math.pi * 2 / 8
                d = (bs * 1.2 + math.sin(t * 2 + i) * 15) * intensity
                c = acc if i % 2 else col
                pygame.draw.circle(s, c, (int(cx + math.cos(a) * d),
                                              int(cy + math.sin(a) * d * 0.7)),
                                   max(1, int(3 * intensity)))
        elif style == "rings":
            for i in range(2):
                ra = t * (1 + i * 0.7) + i * 1.5
                rx = int((bs * 1.5 + i * 15) * intensity)
                ry = int((bs * 0.4 + i * 8) * intensity)
                rs = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
                pygame.draw.ellipse(rs, (*acc, int(80 * intensity)), (2, 2, rx * 2, ry * 2),
                                 max(1, int(2 * intensity)))
                rot = pygame.transform.rotate(rs, math.degrees(ra))
                s.blit(rot, (cx - rot.get_width() // 2, cy - rot.get_height() // 2))
        elif style == "dna_helix":
            for i in range(int(20 * intensity)):
                tr = i / max(int(20 * intensity) - 1, 1)
                a = tr * math.pi * 4 + t * 2
                d = bs * 1.3 * intensity
                for strand in [0, math.pi]:
                    sx = cx + math.cos(a + strand) * d * math.sin(tr * math.pi)
                    sy = cy - bs + tr * bs * 2
                    pygame.draw.circle(s, col if strand == 0 else acc, (int(sx), int(sy)),
                                       max(1, int(2 * intensity)))
        elif style == "constellation":
            sp = []
            for i in range(int(10 * intensity)):
                seed = i * 7.3 + 1.2
                a = seed * 2.1 + t * 0.3
                d = bs * (0.8 + (seed % 0.6) * 0.8) * intensity
                sx = cx + math.cos(a) * d
                sy = cy + math.sin(a) * d * 0.7
                sp.append((int(sx), int(sy)))
                tw = (math.sin(t * 3 + i * 2) + 1) * 0.5
                pygame.draw.circle(s, WHITE, (int(sx), int(sy)),
                                   max(1, int((1 + tw) * 2 * intensity)))
            for i in range(len(sp)):
                for j in range(i + 1, len(sp)):
                    dx = sp[i][0] - sp[j][0]
                    dy = sp[i][1] - sp[j][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < bs * 1.5 * intensity:
                        ls = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        al = max(0, min(255, int(40 * intensity * (1 - d / (bs * 1.5 * intensity)))))
                        pygame.draw.line(ls, (*acc, al), sp[i], sp[j], 1)
                        s.blit(ls, (0, 0))

# ─────────────── GAME STATE ───────────────
class Game:
    def __init__(self):
        self.dna=0.0;self.total_dna=0.0;self.total_clicks=0;self.total_crits=0
        self.total_upgrades_bought=0;self.click_power=1;self.cps=0.0
        self.upgrade_counts=[0]*len(UPGRADES)
        self.particles=[];self.float_texts=[];self.toasts=[]
        self.t=0.0;self.creature_hover=False;self.shop_scroll=0;self.max_scroll=0
        self.creature_cx=320;self.creature_cy=360
        self.shake_x=0;self.shake_y=0;self.shake_time=0
        # Prestige
        self.prestige_count=0;self.prestige_mult=1.0
        # Combo
        self.combo=0;self.combo_timer=0;self.combo_decay=1.2;self.max_combo=0
        # Crits
        self.crit_chance=0.05;self.crit_mult=5.0
        # Achievement bonus tracking
        self.ach_bonus_click=0;self.ach_bonus_cps=0;self.ach_bonus_crit=0;self.ach_bonus_prestige=0;self.ach_bonus_crit_mult=0
        # Buy amount
        self.buy_amount_idx=0;self.display_dna=0.0
        # UI panels
        self.show_traits=False;self.show_bestiary=False;self.show_stats=False;self.show_settings=False;self.show_achievements_panel=False
        self.hovered_upgrade=-1;self.panel_scroll=0
        # Background
        self.starfield=Starfield();self.ambient_particles=[AmbientParticle()for _ in range(30)]
        self.sparkline=Sparkline()
        # Achievements
        self.achievements_unlocked=set()
        # Milestones
        self.last_milestone=0;self.milestones=[10,100,1e3,1e4,1e5,1e6,1e7,1e8,1e9,1e10,1e11,1e12]
        # Auto-save
        self.autosave_timer=0;self.save_time=time.time();self.play_time=0.0
        # Boss system
        self.boss=None;self.boss_timer=random.uniform(60,120);self.bosses_defeated=0;self.boss_tier=0
        # Orbs
        self.orbs=[];self.orb_timer=0;self.orbs_collected=0
        # Abilities
        self.ability_cooldowns=[0.0]*len(ABILITIES);self.ability_actives=[0.0]*len(ABILITIES)
        self.abilities_unlocked=[False]*len(ABILITIES)
        # Mutations
        self.active_mutation=None;self.mutation_timer=0;self.mutations_experienced=0;self.mutation_event_timer=random.uniform(45,90)
        # Bestiary
        self.bestiary=[]
        # Settings
        self.sound_on=SOUND_ENABLED;self.particle_quality=2  # 0=low,1=med,2=high
        # Genome
        seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed);self.renderer=CreatureRenderer(self.genome);self.seed_display=seed
        self._try_load()

    def _try_load(self):
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE,'r') as f: data=json.load(f)
            self.dna=data.get("dna",0);self.total_dna=data.get("total_dna",0)
            self.total_clicks=data.get("total_clicks",0);self.total_crits=data.get("total_crits",0)
            self.total_upgrades_bought=data.get("total_upgrades_bought",0)
            self.click_power=data.get("click_power",1);self.cps=data.get("cps",0)
            self.upgrade_counts=data.get("upgrade_counts",[0]*len(UPGRADES))
            self.prestige_count=data.get("prestige_count",0);self.prestige_mult=data.get("prestige_mult",1.0)
            self.max_combo=data.get("max_combo",0);self.achievements_unlocked=set(data.get("achievements",[]))
            self.buy_amount_idx=data.get("buy_amount_idx",0);self.save_time=data.get("save_time",time.time())
            self.play_time=data.get("play_time",0);self.bosses_defeated=data.get("bosses_defeated",0)
            self.boss_tier=data.get("boss_tier",0);self.orbs_collected=data.get("orbs_collected",0)
            self.mutations_experienced=data.get("mutations_experienced",0)
            self.ach_bonus_click=data.get("ach_bonus_click",0);self.ach_bonus_cps=data.get("ach_bonus_cps",0)
            self.ach_bonus_crit=data.get("ach_bonus_crit",0);self.ach_bonus_prestige=data.get("ach_bonus_prestige",0)
            self.ach_bonus_crit_mult=data.get("ach_bonus_crit_mult",0)
            self.bestiary=data.get("bestiary",[]);self.sound_on=data.get("sound_on",SOUND_ENABLED)
            self.particle_quality=data.get("particle_quality",2)
            self.genome=Genome.from_dict(data["genome"]);self.renderer=CreatureRenderer(self.genome);self.seed_display=self.genome.seed
            # Offline progress
            elapsed=time.time()-self.save_time
            if elapsed>5:
                cps_val=self.effective_cps();off_earn=cps_val*elapsed*0.5
                if off_earn>0:
                    self.dna+=off_earn;self.total_dna+=off_earn
                    self.toasts.append(Toast("Welcome Back!",f"Earned {fmt(off_earn)} DNA away ({elapsed/60:.1f}m)",CYAN))
        except Exception as e: print(f"Load failed: {e}")

    def save(self):
        try:
            data={"dna":self.dna,"total_dna":self.total_dna,"total_clicks":self.total_clicks,
                "total_crits":self.total_crits,"total_upgrades_bought":self.total_upgrades_bought,
                "click_power":self.click_power,"cps":self.cps,"upgrade_counts":self.upgrade_counts,
                "prestige_count":self.prestige_count,"prestige_mult":self.prestige_mult,
                "max_combo":self.max_combo,"achievements":list(self.achievements_unlocked),
                "buy_amount_idx":self.buy_amount_idx,"save_time":time.time(),"play_time":self.play_time,
                "bosses_defeated":self.bosses_defeated,"boss_tier":self.boss_tier,
                "orbs_collected":self.orbs_collected,"mutations_experienced":self.mutations_experienced,
                "ach_bonus_click":self.ach_bonus_click,"ach_bonus_cps":self.ach_bonus_cps,
                "ach_bonus_crit":self.ach_bonus_crit,"ach_bonus_prestige":self.ach_bonus_prestige,
                "ach_bonus_crit_mult":self.ach_bonus_crit_mult,
                "bestiary":self.bestiary,"sound_on":self.sound_on,"particle_quality":self.particle_quality,
                "genome":self.genome.to_dict()}
            with open(SAVE_FILE,'w') as f: json.dump(data,f,indent=2)
        except Exception as e: print(f"Save failed: {e}")

    def prestige(self):
        if self.total_dna<1e6:
            return
            bonus=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige

            self.prestige_count+=1;self.prestige_mult+=bonus

            self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),

            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            self.dna=0;self.total_dna=0;self.click_power=1;self.cps=0

            self.upgrade_counts=[0]*len(UPGRADES);self.combo=0;self.combo_timer=0;self.last_milestone=0

            self.total_clicks=0;self.total_crits=0;self.total_upgrades_bought=0;self.sparkline=Sparkline()

            self.boss=None;self.boss_timer=random.uniform(60,120);self.active_mutation=None

            self.toasts.append(Toast("PRESTIGE!",f"+{bonus:.2f}x permanent (now {self.prestige_mult:.2f}x)",GOLD))

            self._play(snd_prestige);self._burst(self.creature_cx,self.creature_cy,80,[GOLD,CYAN,WHITE,PURPLE]);self.save()


    def _trait_summary(self):
        g=self.genome;td=self.total_dna
        return{"limbs":g.limb_style,"wings":g.wing_style,"eyes":g.eye_style,"tail":g.tail_style,
               "horns":g.horn_style,"mouth":g.mouth_style,"aura":g.aura_style,"pattern":g.pattern_type,
               "ears":g.ear_type,"level":f"{g.level(td):.1f}"}

    def upgrade_cost(self,idx):
        upg=UPGRADES[idx];base=upg["base_cost"];cm=upg["cost_mult"];owned=self.upgrade_counts[idx];amt=self.get_buy_amount()
        if amt==-1:
            total=0;count=0
            while True:
                c=int(base*(cm**(owned+count)));total+=c;count+=1
                if self.dna-total<c or count>10000:
                    total-=c;count-=1;break
            return total,count
        else:total=sum(int(base*(cm**(owned+i)))for i in range(amt));return total,amt

    def get_buy_amount(self):return BUY_AMOUNTS[self.buy_amount_idx]

    def effective_click(self):
        m=self.genome.click_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("click"))
        if self.ability_actives[0]>0:
            m*=10  # DNA Storm
            return(self.click_power+self.ach_bonus_click)*m


    def effective_cps(self):
        m=self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("cps"))
        if self.ability_actives[1]>0:
            m*=10  # Time Warp
            return(self.cps+self.ach_bonus_cps)*m


    def effective_crit_chance(self):
        c=self.crit_chance+self.ach_bonus_crit
        if self.ability_actives[2]>0:
            c=1.0  # Crit Surge
            mut=self._get_mutation_mult("crit")

        if mut>0:
            c=max(c,mut/100)
            return min(c,1.0)


    def effective_crit_mult(self):
        return self.crit_mult+self.ach_bonus_crit_mult

    def _get_mutation_mult(self,mtype):
        if not self.active_mutation:
            return 0
        if self.active_mutation["mult_type"]==mtype:
            return self.active_mutation["mult_value"]-1
        if self.active_mutation["mult_type"]=="all"and mtype in("click","cps"):
            return self.active_mutation["mult_value"]-1
            return 0


    def _play(self,snd):
        if snd and self.sound_on:
            try:snd.play()
            except:pass

    def click_creature(self,mx,my):
        self.total_clicks+=1;self.combo+=1;self.combo_timer=self.combo_decay
        # Mutation combo boost
        if self.active_mutation and self.active_mutation["mult_type"]=="combo":
            self.combo=max(self.combo,int(self.active_mutation["mult_value"]))
        if self.combo>self.max_combo:
            self.max_combo=self.combo
            combo_mult=1.0+(self.combo-1)*0.1

            is_crit=random.random()<self.effective_crit_chance()

        if is_crit:
            self.total_crits+=1;combo_mult*=self.effective_crit_mult()
            earned=self.effective_click()*combo_mult

            self.dna+=earned;self.total_dna+=earned;color=self.genome.body_color(self.total_dna,self.t)

            pcount=max(1,self.particle_quality)

            if is_crit:
                for _ in range(random.randint(5,15)*pcount):
                    self.particles.append(Particle(mx,my,random.choice([GOLD,ORANGE,RED,WHITE]),lifetime=random.uniform(0.4,1.0),size=random.randint(3,9)))
                self.float_texts.append(FloatingText(mx,my-30,f"CRIT! +{fmt(earned)}",ORANGE,"lg"))
            self.shake_time=0.15;self._play(snd_crit)
        else:
            for _ in range(random.randint(2,4+min(self.combo,10))*pcount):
                self.particles.append(Particle(mx,my,color,lifetime=random.uniform(0.2,0.6),size=random.randint(2,5)))
            prefix=f"{self.combo}x "if self.combo>1 else""
            self.float_texts.append(FloatingText(mx,my-20,f"{prefix}+{fmt(earned)}",GOLD))
            self._play(snd_click)
        if self.combo>1 and self.combo%5==0:
            self._play(snd_combo)
        # Damage boss if active
        if self.boss and self.boss.alive:
            self.boss.damage(earned)
            self._play(snd_boss_hit)
            if self.boss.hp<=0:
                self.dna+=self.boss.reward;self.total_dna+=self.boss.reward
                self.float_texts.append(FloatingText(self.boss.x,self.boss.y-60,f"BOSS DEFEATED! +{fmt(self.boss.reward)}",GOLD,"lg"))
                self._play(snd_boss_die);self.bosses_defeated+=1;self.boss_tier+=1
                self._burst(self.boss.x,self.boss.y,50,[GOLD,RED,ORANGE]);self.boss=None
        self._check_achievements();self._check_milestones()

    def buy_upgrade(self,idx):
        total_cost,amount=self.upgrade_cost(idx)
        if self.dna>=total_cost and amount>0:
            self.dna-=total_cost;self.upgrade_counts[idx]+=amount;upg=UPGRADES[idx]
            if upg["type"]=="click":
                self.click_power+=upg["value"]*amount
            elif upg["type"]=="cps":self.cps+=upg["value"]*amount
            self.total_upgrades_bought+=amount;self._play(snd_buy);self._check_achievements();return True
        return False

    def activate_ability(self,idx):
        if idx>=len(ABILITIES):
            return
            ab=ABILITIES[idx]

        if not self.abilities_unlocked[idx]:
            return
        if self.ability_cooldowns[idx]>0 or self.ability_actives[idx]>0:
            return
            self.ability_actives[idx]=ab["duration"];self.ability_cooldowns[idx]=ab["cooldown"]

            self.toasts.append(Toast(f"{ab['name']}!",ab["desc"],ab["color"]))

            self._play(snd_ability);self._burst(self.creature_cx,self.creature_cy,20,[ab["color"]])


    def collect_orb(self,orb,mx,my):
        self.dna+=orb.value;self.total_dna+=orb.value;self.orbs_collected+=1;orb.alive=False
        self.float_texts.append(FloatingText(mx,my-15,f"+{fmt(orb.value)} {orb.name}",orb.color))
        for _ in range(8):
            self.particles.append(Particle(mx,my,orb.color,lifetime=0.5,size=3))
            self._play(snd_orb);self._check_achievements()


    def _start_mutation(self):
        mut=random.choice(MUTATIONS)
        self.active_mutation=mut;self.mutation_timer=mut["duration"];self.mutations_experienced+=1
        self.toasts.append(Toast(f"Mutation: {mut['name']}!",mut["desc"],mut["color"]))
        self._play(snd_mutation);self._check_achievements()

    def _grant_achievement_reward(self,ach):
        rt=ach["reward_type"];rv=ach["reward"]
        if rt=="click":
            self.ach_bonus_click+=rv
        elif rt=="cps":self.ach_bonus_cps+=rv
        elif rt=="crit_chance":self.ach_bonus_crit+=rv
        elif rt=="crit_mult":self.ach_bonus_crit_mult+=rv
        elif rt=="prestige_bonus":self.ach_bonus_prestige+=rv

    def _check_achievements(self):
        checks={"first_click":lambda:self.total_clicks>=1,"click_100":lambda:self.total_clicks>=100,
            "click_1k":lambda:self.total_clicks>=1000,"click_10k":lambda:self.total_clicks>=10000,
            "dna_100":lambda:self.total_dna>=100,"dna_10k":lambda:self.total_dna>=1e4,
            "dna_1m":lambda:self.total_dna>=1e6,"dna_1b":lambda:self.total_dna>=1e9,"dna_1t":lambda:self.total_dna>=1e12,
            "combo_5":lambda:self.max_combo>=5,"combo_20":lambda:self.max_combo>=20,"combo_50":lambda:self.max_combo>=50,
            "crit_first":lambda:self.total_crits>=1,"crit_10":lambda:self.total_crits>=10,
            "upgrade_first":lambda:self.total_upgrades_bought>=1,"upgrade_50":lambda:self.total_upgrades_bought>=50,
            "prestige_1":lambda:self.prestige_count>=1,"prestige_5":lambda:self.prestige_count>=5,
            "level_5":lambda:self.genome.level(self.total_dna)>=5,"level_10":lambda:self.genome.level(self.total_dna)>=10,
            "level_15":lambda:self.genome.level(self.total_dna)>=15,
            "cps_100":lambda:self.effective_cps()>=100,"cps_10k":lambda:self.effective_cps()>=1e4,
            "boss_1":lambda:self.bosses_defeated>=1,"boss_10":lambda:self.bosses_defeated>=10,
            "orb_50":lambda:self.orbs_collected>=50,"mutation_5":lambda:self.mutations_experienced>=5}
        for ach in ACHIEVEMENTS:
            if ach["id"]not in self.achievements_unlocked:
                chk=checks.get(ach["id"])
                if chk and chk():
                    self.achievements_unlocked.add(ach["id"]);self._grant_achievement_reward(ach)
                    self.toasts.append(Toast(f"Achievement: {ach['name']}",f"{ach['desc']} (+reward!)",GOLD))
                    self._play(snd_achieve)

    def _check_milestones(self):
        for m in self.milestones:
            if self.total_dna>=m and self.last_milestone<m:
                self.last_milestone=m;self.shake_time=0.1
                self.float_texts.append(FloatingText(self.creature_cx,self.creature_cy-100,f"MILESTONE: {fmt(m)} DNA!",CYAN,"lg"))
                self._burst(self.creature_cx,self.creature_cy,30,[GOLD,CYAN,GREEN,PINK,PURPLE])

    def _burst(self,x,y,n,colors):
        for _ in range(n):
            a=random.uniform(0,2*math.pi);sp=random.uniform(60,200)
            self.particles.append(Particle(x,y,random.choice(colors),math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.6,1.5),random.randint(3,7)))

    def update(self,dt):
        self.t+=dt;self.play_time+=dt
        # Combo decay (unless Frenzy active)
        if self.ability_actives[3]<=0:
            if self.combo_timer>0:
                self.combo_timer-=dt
                if self.combo_timer<=0:
                    self.combo=0
        # Auto DNA
        auto=self.effective_cps()*dt;self.dna+=auto;self.total_dna+=auto
        self._check_achievements();self._check_milestones()
        # Particles
        for p in self.particles:
            p.update(dt)
            self.particles=[p for p in self.particles if p.alive]

        for ft in self.float_texts:
            ft.update(dt)
            self.float_texts=[ft for ft in self.float_texts if ft.alive]

        for t in self.toasts:
            t.update(dt)
            self.toasts=[t for t in self.toasts if t.alive]

        # Shake
        if self.shake_time>0:
            self.shake_time-=dt;i=self.shake_time*40;self.shake_x=random.uniform(-i,i);self.shake_y=random.uniform(-i,i)
        else:self.shake_x=self.shake_y=0
        # Ambient
        for ap in self.ambient_particles:
            ap.update(dt)
            self.sparkline.update(dt,self.effective_cps())

        # Animated DNA
        diff=self.dna-self.display_dna;self.display_dna+=diff*min(1,dt*10)
        if abs(diff)<0.5:
            self.display_dna=self.dna
        # Auto-save
        self.autosave_timer+=dt
        if self.autosave_timer>=30:
            self.autosave_timer=0;self.save()
        # Boss timer
        if not self.boss:
            self.boss_timer-=dt
            if self.boss_timer<=0:
                self.boss=Boss(self.boss_tier,self.total_dna);self.boss_timer=random.uniform(90,180)
        else:self.boss.update(dt)
        # Orb spawning
        self.orb_timer+=dt
        if self.orb_timer>random.uniform(2,5):
            self.orb_timer=0;self.orbs.append(DNAOrb(self.total_dna))
        for orb in self.orbs:
            orb.update(dt)
            self.orbs=[o for o in self.orbs if o.alive]

        # Ability timers
        for i in range(len(ABILITIES)):
            if self.ability_actives[i]>0:
                self.ability_actives[i]=max(0,self.ability_actives[i]-dt)
            if self.ability_cooldowns[i]>0:
                self.ability_cooldowns[i]=max(0,self.ability_cooldowns[i]-dt)
                if not self.abilities_unlocked[i] and self.total_dna>=ABILITIES[i]["unlock_dna"]:
                    self.abilities_unlocked[i]=True
                    self.toasts.append(Toast(f"Ability Unlocked!",f"{ABILITIES[i]['name']} [{ABILITIES[i]['key']}]",ABILITIES[i]["color"]))
        # Mutation timer
        if self.active_mutation:
            self.mutation_timer-=dt
            if self.mutation_timer<=0:
                self.active_mutation=None
        else:
            self.mutation_event_timer-=dt
            if self.mutation_event_timer<=0:
                self._start_mutation();self.mutation_event_timer=random.uniform(60,120)

    def new_creature(self):
        self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),
            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed)

            self.renderer=CreatureRenderer(self.genome);self.seed_display=seed

            self.toasts.append(Toast("New Creature!",f"Seed: {seed}",CYAN))

            self._burst(self.creature_cx,self.creature_cy,40,[CYAN,GREEN,PINK])


    def draw(self,surface):
        mx,my=pygame.mouse.get_pos();evo_lv=self.genome.level(self.total_dna)
        # BG
        for y in range(HEIGHT):
            ratio=y/HEIGHT;ls=min(evo_lv*2,30)
            r=int((BG_TOP[0]+ls*0.3)*(1-ratio)+(BG_BOT[0]+ls*0.5)*ratio)
            g=int((BG_TOP[1]+ls*0.1)*(1-ratio)+(BG_BOT[1]+ls*0.2)*ratio)
            b=int(min(255,(BG_TOP[2]+ls*0.8)*(1-ratio)+(BG_BOT[2]+ls*0.6)*ratio))
            pygame.draw.line(surface,(min(255,r),min(255,g),min(255,b)),(0,y),(WIDTH,y))
        self.starfield.draw(surface,evo_lv,self.t)
        for ap in self.ambient_particles:
            ap.draw(surface,evo_lv)
        # Orbs (behind panels)
        for orb in self.orbs:
            orb.draw(surface)
            so=(int(self.shake_x),int(self.shake_y))

        # ── Left Panel ──
        pygame.draw.rect(surface,PANEL_BG,(15+so[0],15+so[1],620,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(15+so[0],15+so[1],620,750),2,border_radius=15)
        title=font_xl.render("Procedural Creature Clicker",True,CYAN)
        surface.blit(title,(325-title.get_width()//2+so[0],22+so[1]))
        name=self.genome.proc_name(self.total_dna);color=self.genome.body_color(self.total_dna,self.t)
        surface.blit(font_lg.render(name,True,color),(325-font_lg.size(name)[0]//2+so[0],62+so[1]))
        evo_display = evo_lv
        if self.active_mutation and self.active_mutation["mult_type"]=="evo":
            evo_display += self.active_mutation["mult_value"]
        stage_txt=font_sm.render(f"Evo Lv: {evo_display:.1f} | Prestige: {self.prestige_count} ({self.prestige_mult:.2f}x)",True,MUTED)
        surface.blit(stage_txt,(325-stage_txt.get_width()//2+so[0],90+so[1]))
        # Trait tags
        traits=[]
        gd=self.genome
        if gd.limb_count(self.total_dna)>0:
            traits.append(f"{gd.limb_count(self.total_dna)} {gd.limb_style}")
        if gd.has_wings(self.total_dna):
            traits.append(f"{gd.wing_style} wings")
        if gd.eye_count(self.total_dna)>2:
            traits.append(f"{gd.eye_count(self.total_dna)} {gd.eye_style}")
        if gd.has_horns(self.total_dna):
            traits.append(f"{gd.horn_count(self.total_dna)} {gd.horn_style}")
        if gd.tail_length(self.total_dna)>0:
            traits.append(f"{gd.tail_style} tail")
        if gd.has_pattern(self.total_dna):
            traits.append(gd.pattern_type)
        if gd.has_aura(self.total_dna):
            traits.append(f"{gd.aura_style} aura")
        if traits:
            tt=font_xs.render(" | ".join(traits[:6]),True,DIM);surface.blit(tt,(325-tt.get_width()//2+so[0],108+so[1]))
        # Mutation banner
        if self.active_mutation:
            mut=self.active_mutation;flash=(math.sin(self.t*6)+1)*0.5
            mc=tuple(int(min(255,c*(0.6+0.4*flash)))for c in mut["color"])
            mt=font_md.render(f"MUTATION: {mut['name']} ({self.mutation_timer:.0f}s)",True,mc)
            surface.blit(mt,(325-mt.get_width()//2+so[0],125+so[1]))
        # Boss
        if self.boss and self.boss.alive:
            self.boss.draw(surface,self.t)
        else:
            # Creature
            dist=math.sqrt((mx-self.creature_cx)**2+(my-self.creature_cy)**2)
            bsize=self.genome.body_size(self.total_dna)
            self.creature_hover=dist<bsize*1.5 and not self.show_traits and not self.show_bestiary and not self.show_stats and not self.show_settings and not self.show_achievements_panel
            self.renderer.draw(surface,self.creature_cx+so[0],self.creature_cy+so[1],self.total_dna,self.t,self.creature_hover)
            if self.creature_hover:
                hint=font_sm.render("Click me!",True,WHITE);surface.blit(hint,(self.creature_cx-hint.get_width()//2,int(self.creature_cy+bsize+15)))
        for p in self.particles:
            p.draw(surface)
        for ft in self.float_texts:
            ft.draw(surface)
        # DNA + Combo
        dna_txt=font_xl.render(f"{fmt(self.display_dna)}",True,GOLD);surface.blit(dna_txt,(325-dna_txt.get_width()//2,490))
        if self.combo>1:
            cc=ORANGE if self.combo<10 else RED if self.combo<30 else PURPLE
            ct=font_lg.render(f"COMBO x{self.combo}",True,cc);surface.blit(ct,(325-ct.get_width()//2,468))
            bw=min(200,200*(self.combo_timer/self.combo_decay))
            pygame.draw.rect(surface,DARK_PURPLE,(225,493,200,4),border_radius=2)
            if bw>0:
                pygame.draw.rect(surface,cc,(225,493,int(bw),4),border_radius=2)
        surface.blit(font_md.render("DNA Points",True,MUTED),(325-font_md.size("DNA Points")[0]//2,525))
        # Stats line
        sl=f"Click: {fmt(self.effective_click())} | CPS: {fmt(self.effective_cps())} | Crit: {self.effective_crit_chance()*100:.0f}% | Bosses: {self.bosses_defeated}"
        surface.blit(font_xs.render(sl,True,MUTED),(325-font_xs.size(sl)[0]//2,550))
        sl2=f"Total: {fmt(self.total_dna)} | Clicks: {self.total_clicks} | Orbs: {self.orbs_collected} | Mutations: {self.mutations_experienced}"
        surface.blit(font_xs.render(sl2,True,DIM),(325-font_xs.size(sl2)[0]//2,565))
        # Sparkline
        self.sparkline.draw(surface,195,585,260,32,CYAN)
        # Ability bar
        ab_y=625
        surface.blit(font_xs.render("Abilities:",True,MUTED),(30,ab_y+2))
        for i,ab in enumerate(ABILITIES):
            ax=110+i*120;aw=110;ah=36;ar=pygame.Rect(ax,ab_y,aw,ah)
            unlocked=self.abilities_unlocked[i]
            on=self.ability_actives[i]>0;cd=self.ability_cooldowns[i]>0
            if on:
                ac=(40,80,40);bc=GREEN
            elif cd:ac=(30,25,50);bc=DIM
            elif unlocked:ac=(35,50,90);bc=ab["color"]
            else:ac=(20,18,35);bc=(40,35,60)
            pygame.draw.rect(surface,ac,ar,border_radius=6);pygame.draw.rect(surface,bc,ar,1,border_radius=6)
            # Cooldown overlay
            if cd and unlocked:
                cdr=self.ability_cooldowns[i]/ab["cooldown"]
                ch=int(ah*cdr)
                if ch>0:
                    cs=pygame.Surface((aw,ch),pygame.SRCALPHA);cs.fill((0,0,0,100));surface.blit(cs,(ax,ab_y))
                    cd_txt=font_xxs.render(f"{self.ability_cooldowns[i]:.0f}s",True,WHITE);surface.blit(cd_txt,(ax+aw//2-cd_txt.get_width()//2,ab_y+ah//2-cd_txt.get_height()//2))

            elif on:
                on_txt=font_xxs.render(f"{self.ability_actives[i]:.1f}s",True,GREEN);surface.blit(on_txt,(ax+aw//2-on_txt.get_width()//2,ab_y+ah//2-on_txt.get_height()//2))
            tc=WHITE if unlocked else DIM
            nt=font_xs.render(f"[{ab['key']}] {ab['name']}",True,tc);surface.blit(nt,(ax+4,ab_y+3))
            dt_txt=font_xxs.render(ab["desc"] if unlocked else f"Unlock: {fmt(ab['unlock_dna'])} DNA",True,MUTED if unlocked else (50,45,80))
            surface.blit(dt_txt,(ax+4,ab_y+19))
        # Trait detail panel
        if self.show_traits:
            self._draw_trait_panel(surface,so)
        # Other panels
        if self.show_bestiary:
            self._draw_bestiary(surface,so)
        if self.show_stats:
            self._draw_stats(surface,so)
        if self.show_settings:
            self._draw_settings(surface,so)
        if self.show_achievements_panel:
            self._draw_achievements_panel(surface,so)
        # ── Right Panel: Shop ──
        pygame.draw.rect(surface,PANEL_BG,(650,15,435,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(650,15,435,750),2,border_radius=15)
        surface.blit(font_lg.render("Upgrades",True,CYAN),(867-font_lg.size("Upgrades")[0]//2,22))
        surface.blit(font_sm.render(f"DNA: {fmt(self.dna)}",True,GOLD),(665,52))
        # Buy amount
        surface.blit(font_xs.render("Buy:",True,MUTED),(830,55))
        for bi,bl in enumerate(BUY_LABELS):
            bx=865+bi*38;sel=bi==self.buy_amount_idx;bc=GREEN if sel else(40,35,80)
            pygame.draw.rect(surface,bc,(bx,52,34,16),border_radius=4)
            if sel:
                pygame.draw.rect(surface,WHITE,(bx,52,34,16),1,border_radius=4)
                surface.blit(font_xs.render(bl,True,WHITE if sel else DIM),(bx+17-font_xs.size(bl)[0]//2,53))

        # Upgrade list
        clip=pygame.Rect(655,74,425,500);surface.set_clip(clip);self.max_scroll=max(0,len(UPGRADES)*46-490)
        self.hovered_upgrade=-1
        for i,upg in enumerate(UPGRADES):
            tc,am=self.upgrade_cost(i);ca=self.dna>=tc and am>0;by=80+i*46-self.shop_scroll
            if 70<by<575:
                r=pygame.Rect(665,by,405,40);hov=r.collidepoint(mx,my)
                if hov:
                    self.hovered_upgrade=i
                    c=(40,35,90)if ca else(18,16,42)

                if ca and hov:
                    c=(55,48,110)
                    pygame.draw.rect(surface,c,r,border_radius=8);pygame.draw.rect(surface,GREEN if ca else DIM,r,1,border_radius=8)

                    key=upg.get("key","")

                if key:
                    surface.blit(font_xs.render(f"[{key}]",True,DIM),(r.x+5,r.y+4))
                    surface.blit(font_sm.render(f"{upg['name']} (x{self.upgrade_counts[i]})",True,WHITE if ca else DIM),(r.x+30,r.y+2))

                    surface.blit(font_xs.render(upg["desc"],True,MUTED if ca else(50,45,80)),(r.x+30,r.y+21))

                    cs=fmt(tc)

                if am>1:
                    cs+=f" (x{am})"
                    surface.blit(font_sm.render(cs,True,GREEN if ca else RED),(r.right-font_sm.size(cs)[0]-8,r.y+11))

        surface.set_clip(None)
        if self.max_scroll>0:
            sr=self.shop_scroll/self.max_scroll;bh=max(20,int(500*(500/(500+self.max_scroll))))
            pygame.draw.rect(surface,DIM,(1072,82+int(sr*(490-bh)),4,bh),border_radius=2)
        # Progress
        py_=590;next_m=None
        for m in self.milestones:
            if self.total_dna<m:
                next_m=m;break
        if not next_m:
            next_m=self.milestones[-1]*10
            pygame.draw.rect(surface,DARK_PURPLE,(665,py_,410,10),border_radius=5)

            prev_m=self.milestones[max(0,self.milestones.index(next_m)-1)]if next_m in self.milestones else 0

            prog=min(1,max(0,(self.total_dna-prev_m)/(next_m-prev_m)))if next_m>prev_m else 1

            fw=int(410*prog)

            if fw>0:
                for px in range(fw):
                    ratio=px/410;c=(int(60+120*ratio),int(40+180*ratio),int(180+75*ratio))
                pygame.draw.line(surface,c,(665+px,py_),(665+px,py_+9))

        pygame.draw.rect(surface,PANEL_BORDER,(665,py_,410,10),1,border_radius=5)
        surface.blit(font_xxs.render(f"Next: {fmt(next_m)} ({prog*100:.1f}%)",True,MUTED),(667,py_+12))
        # Buttons
        can_prestige=self.total_dna>=1e6
        pb=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige if can_prestige else 0
        pr=pygame.Rect(665,620,130,28);ph=pr.collidepoint(mx,my)
        pygame.draw.rect(surface,(150,30,30)if can_prestige else DARK_RED,pr,border_radius=5)
        pygame.draw.rect(surface,RED if can_prestige else DIM,pr,1,border_radius=5)
        surface.blit(font_sm.render(f"Prestige [P]"if can_prestige else"Prestige (1M)",True,WHITE if can_prestige else DIM),
            (pr.centerx-font_sm.size(f"Prestige [P] +{pb:.1f}x"if can_prestige else"Prestige (1M)")[0]//2,pr.centery-7))
        nr=pygame.Rect(800,620,130,28)
        pygame.draw.rect(surface,(50,80,150)if nr.collidepoint(mx,my)else(35,55,110),nr,border_radius=5)
        pygame.draw.rect(surface,CYAN,nr,1,border_radius=5)
        surface.blit(font_sm.render("New [N]",True,WHITE),(nr.centerx-25,nr.centery-7))
        br=pygame.Rect(935,620,140,28)
        pygame.draw.rect(surface,(50,50,100)if br.collidepoint(mx,my)else(30,28,65),br,border_radius=5)
        pygame.draw.rect(surface,PANEL_BORDER,br,1,border_radius=5)
        surface.blit(font_sm.render("Bestiary [B]",True,WHITE),(br.centerx-38,br.centery-7))
        # Bottom bar
        bb=pygame.Rect(665,660,410,24)
        pygame.draw.rect(surface,(30,28,65),bb,border_radius=4);pygame.draw.rect(surface,PANEL_BORDER,bb,1,border_radius=4)
        bt="[T]raits [D]stats [A]achieve [M]settings [S]save [Tab]buy"
        surface.blit(font_xxs.render(bt,True,MUTED),(bb.centerx-font_xxs.size(bt)[0]//2,bb.centery-5))
        # Bottom info
        info=f"Achievements: {len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)} | Time: {int(self.play_time//3600)}h{int(self.play_time%3600//60)}m | Autosave 30s"
        surface.blit(font_xxs.render(info,True,DIM),(325-font_xxs.size(info)[0]//2,HEIGHT-15))
        # Tooltip
        if self.hovered_upgrade>=0:
            self._draw_tooltip(surface,self.hovered_upgrade,mx,my)
        # Toasts
        for i,toast in enumerate(self.toasts):
            toast.draw(surface,i)

    def _draw_trait_panel(self,s,so):
        px,py,pw,ph=25,150,610,280
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,230),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*PANEL_BORDER,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        gd=self.genome;td=self.total_dna;rows=[
            ("Body Size",f"{gd.body_size(td):.1f}"),("Segments",f"{gd.body_segments(td)}"),
            ("Eyes",f"{gd.eye_count(td)} ({gd.eye_style})"),("Limbs",f"{gd.limb_count(td)} ({gd.limb_style})"),
            ("Wings",f"{gd.wing_size(td):.0f} ({gd.wing_style})"if gd.has_wings(td)else"None"),
            ("Tail",f"{gd.tail_length(td):.0f} ({gd.tail_style})"),
            ("Horns",f"{gd.horn_count(td)} ({gd.horn_style})"if gd.has_horns(td)else"None"),
            ("Pattern",f"{gd.pattern_type}"if gd.has_pattern(td)else"None"),
            ("Aura",f"{gd.aura_style}"if gd.has_aura(td)else"None"),
            ("Click Mult",f"{gd.click_multiplier(td):.2f}x"),("CPS Mult",f"{gd.cps_multiplier(td):.2f}x"),
            ("Prestige",f"{self.prestige_mult:.2f}x"),("Ach Bonus Click",f"+{self.ach_bonus_click}"),
            ("Ach Bonus CPS",f"+{self.ach_bonus_cps}"),("Crit Chance",f"{self.effective_crit_chance()*100:.1f}%"),
            ("Crit Mult",f"{self.effective_crit_mult():.1f}x"),
        ]
        cols=3;cw=pw//cols
        for idx,(label,val)in enumerate(rows):
            col=idx%cols;row=idx//cols;x=px+10+col*cw+so[0];y=py+8+row*17+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+font_xs.size(label+":")[0]+4,y))

    def _draw_bestiary(self,s,so):
        px,py,pw,ph=50,80,560,580
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*CYAN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Bestiary",True,CYAN),(px+pw//2-font_lg.size("Bestiary")[0]//2+so[0],py+10+so[1]))
        if not self.bestiary:
            surface.blit(font_sm.render("No creatures yet! Prestige or press N to add entries.",True,MUTED),(px+20+so[0],py+50+so[1]))
        else:
            for i,entry in enumerate(sorted(self.bestiary,key=lambda e:
                e.get("total_dna",0),reverse=True)):
                if i>15:
                    break;ey=py+45+i*32+so[1];ex=px+15+so[0]
                # Mini creature name
                surface.blit(font_sm.render(f"{entry.get('name','?')}",True,GOLD),(ex,ey))
                tr=entry.get("traits",{})
                parts=[f"{tr.get('limbs','?')} limbs",f"{tr.get('eyes','?')} eyes",f"{tr.get('tail','?')} tail",f"Lv {tr.get('level','?')}"]
                surface.blit(font_xs.render(" | ".join(parts),True,MUTED),(ex,ey+15))
                surface.blit(font_xs.render(f"DNA: {fmt(entry.get('total_dna',0))} | Prestige #{entry.get('prestige','?')}",True,DIM),(ex+350,ey+7))

    def _draw_stats(self,s,so):
        px,py,pw,ph=50,80,560,500
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GREEN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Statistics",True,GREEN),(px+pw//2-font_lg.size("Statistics")[0]//2+so[0],py+10+so[1]))
        hrs=int(self.play_time//3600);mins=int(self.play_time%3600//60);secs=int(self.play_time%60)
        cps_v=self.effective_cps();click_v=self.effective_click()
        rows=[
            ("Play Time",f"{hrs}h {mins}m {secs}s"),("Total DNA Earned",fmt(self.total_dna)),
            ("Current DNA",fmt(self.dna)),("Total Clicks",f"{self.total_clicks:,}"),
            ("Click Rate",f"{self.total_clicks/max(1,self.play_time):.1f}/s" if self.play_time>1 else "N/A"),
            ("Per Click",fmt(click_v)),("Per Second",fmt(cps_v)),
            ("Total Crits",f"{self.total_crits:,} ({self.total_crits/max(1,self.total_clicks)*100:.1f}%)" if self.total_clicks>0 else "0"),
            ("Max Combo",f"{self.max_combo}x"),("Upgrades Bought",f"{self.total_upgrades_bought:,}"),
            ("Prestige Count",f"{self.prestige_count}"),("Prestige Mult",f"{self.prestige_mult:.2f}x"),
            ("Bosses Defeated",f"{self.bosses_defeated}"),("Boss Tier",f"{self.boss_tier}"),
            ("Orbs Collected",f"{self.orbs_collected}"),("Mutations",f"{self.mutations_experienced}"),
            ("Achievement Bonus Click",f"+{self.ach_bonus_click}"),("Achievement Bonus CPS",f"+{self.ach_bonus_cps}"),
            ("Achievement Bonus Crit",f"+{self.ach_bonus_crit*100:.1f}%"),
            ("Creature Seed",self.seed_display),
        ]
        for idx,(label,val)in enumerate(rows):
            col=idx%2;row=idx//2;x=px+15+col*280+so[0];y=py+42+row*21+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+140,y))

    def _draw_settings(self,s,so):
        px,py,pw,ph=200,100,350,350
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*ORANGE,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Settings",True,ORANGE),(px+pw//2-font_lg.size("Settings")[0]//2+so[0],py+10+so[1]))
        mx,my=pygame.mouse.get_pos()
        # Sound toggle
        sr=pygame.Rect(px+20+so[0],py+50+so[1],150,30);sh=sr.collidepoint(mx,my)
        pygame.draw.rect(surface,(40,80,40)if self.sound_on else(80,30,30)if sh else DARK_RED,sr,border_radius=5)
        surface.blit(font_sm.render(f"Sound: {'ON' if self.sound_on else 'OFF'}",True,WHITE),(sr.x+10,sr.y+7))
        # Particle quality
        for qi,ql in enumerate(["Low","Med","High"]):
            qr=pygame.Rect(px+20+qi*105+so[0],py+95+so[1],95,30)
            qs=qi==self.particle_quality;qh=qr.collidepoint(mx,my)
            pygame.draw.rect(surface,(50,50,100)if(qs or qh)else(30,28,60),qr,border_radius=5)
            if qs:
                pygame.draw.rect(surface,WHITE,qr,1,border_radius=5)
                surface.blit(font_sm.render(f"Particles: {ql}",True,WHITE if qs else MUTED),(qr.x+5,qr.y+7))

        # Reset button
        rr=pygame.Rect(px+20+so[0],py+145+so[1],150,30)
        pygame.draw.rect(surface,(120,30,30)if rr.collidepoint(mx,my)else DARK_RED,rr,border_radius=5)
        surface.blit(font_sm.render("Reset Save [X]",True,RED if rr.collidepoint(mx,my)else DIM),(rr.x+10,rr.y+7))
        # Info
        lines=["Controls:","[Q/W/E/R] Activate abilities","[1-0] Buy upgrades",
               "[P] Prestige  [N] New creature","[B] Bestiary  [T] Traits",
               "[D] Stats  [A] Achievements","[M] Settings  [S] Save",
               "[Tab] Cycle buy amount","[X in Settings] Reset save","[ESC] Quit"]
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,MUTED if i>0 else WHITE),(px+20+so[0],py+190+i*16+so[1]))

    def _draw_achievements_panel(self,s,so):
        px,py,pw,ph=30,50,600,620
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GOLD,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})",True,GOLD),
            (px+pw//2-font_lg.size(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})")[0]//2+so[0],py+8+so[1]))
        clip=pygame.Rect(px+5,py+35,pw-10,ph-40);surface.set_clip(clip)
        for i,ach in enumerate(ACHIEVEMENTS):
            unlocked=ach["id"]in self.achievements_unlocked;ay=py+38+i*22
            if ay<py+30 or ay>py+ph-10:
                continue
                c=GOLD if unlocked else(40,35,60)

                icon="*"if unlocked else "o"

                surface.blit(font_xs.render(f"[{icon}] {ach['name']}",True,WHITE if unlocked else DIM),(px+15+so[0],ay+so[1]))

                surface.blit(font_xxs.render(f"{ach['desc']} | Reward: +{ach['reward']} {ach['reward_type']}",True,MUTED if unlocked else(50,45,70)),(px+200+so[0],ay+2+so[1]))

        surface.set_clip(None)

    def _draw_tooltip(self,surface,idx,mx,my):
        upg=UPGRADES[idx];tc,am=self.upgrade_cost(idx);lines=[upg["name"],upg["desc"],
            f"Type: {upg['type'].upper()}",f"Cost mult: x{upg['cost_mult']}/lv",
            f"Owned: {self.upgrade_counts[idx]}",f"Cost ({am}): {fmt(tc)}"]
        if upg["type"]=="click":
            nv=self.effective_click()+upg["value"]*am*self.genome.click_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"Click after: {fmt(nv)}")
        else:
            nv=self.effective_cps()+upg["value"]*am*self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"CPS after: {fmt(nv)}")
        tw=max(font_xs.size(l)[0]for l in lines)+16;th=len(lines)*15+10
        tx=min(mx+15,WIDTH-tw-5);ty=min(my+15,HEIGHT-th-5)
        tip=pygame.Surface((tw,th),pygame.SRCALPHA);pygame.draw.rect(tip,(10,8,30,230),(0,0,tw,th),border_radius=6)
        pygame.draw.rect(tip,(*PANEL_BORDER,200),(0,0,tw,th),1,border_radius=6);surface.blit(tip,(tx,ty))
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,GOLD if i==0 else MUTED),(tx+8,ty+5+i*15))


def fmt(n):
    if n<0:
        return"-"+fmt(-n)
    if n<1000:
        return f"{n:.1f}"if isinstance(n,float)and n!=int(n)else str(int(n))
        sfx=["","K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc"];t=0

    while n>=1000 and t<len(sfx)-1:
        n/=1000;t+=1
        return f"{n:.0f}{sfx[t]}"if n>=100 else f"{n:.1f}{sfx[t]}"if n>=10 else f"{n:.2f}{sfx[t]}"



# ─────────────── MAIN ───────────────
def main():
    game=Game();running=True
    while running:
        dt=clock.tick(60)/1000;dt=min(dt,0.05);mx,my=pygame.mouse.get_pos()
        close_panels=lambda:any([game.show_traits,game.show_bestiary,game.show_stats,game.show_settings,game.show_achievements_panel])
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                game.save();running=False
            elif event.type==pygame.KEYDOWN:
                k=event.key
                if k==pygame.K_ESCAPE:
                    if close_panels():
                        game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                    else:game.save();running=False
                elif k==pygame.K_s:game.save();game.toasts.append(Toast("Saved!","Game saved",GREEN))
                elif k==pygame.K_p:game.prestige()
                elif k==pygame.K_n:game.new_creature()
                elif k==pygame.K_t:game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_b:game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_d:game.show_stats=not game.show_stats;game.show_traits=game.show_bestiary=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_a:game.show_achievements_panel=not game.show_achievements_panel;game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=False
                elif k==pygame.K_m:game.show_settings=not game.show_settings;game.show_traits=game.show_bestiary=game.show_stats=game.show_achievements_panel=False
                elif k==pygame.K_TAB:game.buy_amount_idx=(game.buy_amount_idx+1)%len(BUY_AMOUNTS)
                elif k==pygame.K_q:game.activate_ability(0)
                elif k==pygame.K_w:game.activate_ability(1)
                elif k==pygame.K_e:game.activate_ability(2)
                elif k==pygame.K_r:game.activate_ability(3)
                km={pygame.K_1:0,pygame.K_2:1,pygame.K_3:2,pygame.K_4:3,pygame.K_5:4,pygame.K_6:5,pygame.K_7:6,pygame.K_8:7,pygame.K_9:8,pygame.K_0:9}
                if k in km:
                    game.buy_upgrade(km[k])
            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==1:
                    # Check orbs first
                    for orb in game.orbs:
                        if orb.alive and orb.hit_test(mx,my):
                            game.collect_orb(orb,mx,my);break
                    else:
                        if game.creature_hover and not close_panels():
                            game.click_creature(mx,my)
                            for i in range(len(UPGRADES)):
                                by=80+i*46-game.shop_scroll;r=pygame.Rect(665,by,405,40)
                                if r.collidepoint(mx,my):
                                    game.buy_upgrade(i)
                        for bi in range(len(BUY_LABELS)):
                            if pygame.Rect(865+bi*38,52,34,16).collidepoint(mx,my):
                                game.buy_amount_idx=bi
                        if pygame.Rect(665,620,130,28).collidepoint(mx,my):
                            game.prestige()
                        if pygame.Rect(800,620,130,28).collidepoint(mx,my):
                            game.new_creature()
                        if pygame.Rect(935,620,140,28).collidepoint(mx,my):
                            game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        if pygame.Rect(665,660,410,24).collidepoint(mx,my):
                            game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        # Settings panel clicks
                        if game.show_settings:
                            spx,spy=200+int(game.shake_x),100+int(game.shake_y)
                            if pygame.Rect(spx+20,spy+50,150,30).collidepoint(mx,my):
                                game.sound_on=not game.sound_on
                                for qi in range(3):
for                                f pygame.Rect(spx+20+qi*105,spy+95,95,30).collidepoint(mx,my):

                                    game.particle_quality=qi
                            if pygame.Rect(spx+20,spy+145,150,30).collidepoint(mx,my):
                                if os.path.exists(SAVE_FILE):
                                    os.remove(SAVE_FILE)
                                    game.toasts.append(Toast("Reset!","Save file deleted. Restart to start fresh.",RED))

                        # Ability bar clicks
                        for ai in range(len(ABILITIES)):
                            ar=pygame.Rect(110+ai*120,625,110,36)
                            if ar.collidepoint(mx,my):
                                game.activate_ability(ai)
                elif event.button==4:game.shop_scroll=max(0,game.shop_scroll-40)
                elif event.button==5:game.shop_scroll=min(game.max_scroll,game.shop_scroll+40)
        # Ambient particles
        if game.effective_cps()>0 and random.random()<dt*2*game.particle_quality:
            a=random.uniform(0,2*math.pi);d=random.uniform(40,80)
            c=game.genome.accent_color(game.total_dna,game.t)
            game.particles.append(Particle(game.creature_cx+math.cos(a)*d,game.creature_cy+math.sin(a)*d*0.7,c,random.uniform(-15,15),random.uniform(-35,-10),0.5,random.randint(2,4)))
        game.update(dt);game.draw(screen);pygame.display.flip()
    pygame.quit();sys.exit()

if __name__=="__main__":

    main()

/usr/bin/env python3
"""
Procedural Creature Clicker v3
Boss fights, falling orbs, active abilities, mutations, bestiary, stats, settings, and more!
"""

import pygame, sys, math, random, hashlib, colorsys, json, os, time, array

# ─────────────── INIT ───────────────
pygame.init()
SOUND_ENABLED = False
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    SOUND_ENABLED = True
except Exception:
    pass
WIDTH, HEIGHT = 1100, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Procedural Creature Clicker v3")
clock = pygame.time.Clock()
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "creature_save.json")

# ─────────────── COLORS ───────────────
BG_TOP = (12, 10, 35); BG_BOT = (40, 35, 85); PANEL_BG = (22, 20, 55)
PANEL_BORDER = (75, 65, 150); WHITE = (255, 255, 255); GOLD = (255, 215, 0)
CYAN = (0, 230, 255); GREEN = (80, 255, 120); RED = (255, 80, 80)
ORANGE = (255, 160, 50); PURPLE = (180, 100, 255); PINK = (255, 120, 200)
DARK_PURPLE = (55, 38, 110); MUTED = (155, 150, 195); DIM = (95, 90, 135)
DARK_RED = (120, 20, 20); YELLOW = (255, 255, 80); DARK_GREEN = (20, 80, 30)

# ─────────────── FONTS ───────────────
font_xl = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 36, bold=True)
font_lg = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 24, bold=True)
font_md = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 18)
font_sm = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 14)
font_xs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 11)
font_xxs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 9)

# ─────────────── PROCEDURAL SOUND ───────────────
def make_sound(freq=440, duration=0.08, volume=0.12, wave="sine"):
    try:
        sr = 22050; ns = int(sr * duration); buf = array.array('h')
        for i in range(ns):
            t = i / sr; env = min(1.0, min(i/(sr*0.005), (ns-i)/(sr*0.01)))
            v = math.sin(2*math.pi*freq*t) if wave=="sine" else (1.0 if math.sin(2*math.pi*freq*t)>0 else -1.0) if wave=="square" else random.uniform(-1,1)
            buf.append(max(-32767, min(32767, int(v*volume*env*32767))))
        return pygame.mixer.Sound(buffer=buf)
    except: return None

snd_click = make_sound(520,0.06,0.10,"sine"); snd_crit = make_sound(880,0.15,0.15,"square")
snd_buy = make_sound(660,0.08,0.08,"sine"); snd_achieve = make_sound(1047,0.25,0.12,"sine")
snd_combo = make_sound(700,0.05,0.06,"sine"); snd_prestige = make_sound(440,0.5,0.15,"sine")
snd_orb = make_sound(1200,0.1,0.08,"sine"); snd_ability = make_sound(660,0.3,0.12,"sine")
snd_boss_hit = make_sound(300,0.1,0.10,"square"); snd_boss_die = make_sound(200,0.4,0.15,"noise")
snd_mutation = make_sound(500,0.2,0.10,"sine")

def play(snd):
    if snd:
        try: snd.play()
        except: pass

# ─────────────── SEEDED RNG ───────────────
class SeededRNG:
    def __init__(self, seed_str="default"):
        h = hashlib.sha256(seed_str.encode()).digest()
        self.state = int.from_bytes(h[:8], 'big'); self.pool = []; self._refill()
    def _refill(self):
        for _ in range(256):
            self.state = (self.state*6364136223846793005+1442695040888963407)&0xFFFFFFFFFFFFFFFF
            self.pool.append(((self.state>>16)&0xFFFFFFFF)/0xFFFFFFFF)
    def next(self):
        if not self.pool:
            self._refill()
            return self.pool.pop(0)

    def rand(self,lo,hi): return lo+self.next()*(hi-lo)
    def randint(self,lo,hi): return int(self.next()*(hi-lo+1))+lo
    def choice(self,lst): return lst[self.randint(0,len(lst)-1)]

# ─────────────── GENOME ───────────────
class Genome:
    def __init__(self, seed="creature_1"):
        self.seed=seed; self.rng=SeededRNG(seed)
        self.hue_offset=self.rng.rand(0,1); self.hue_speed=self.rng.rand(0.02,0.08)
        self.body_width_ratio=self.rng.rand(0.85,1.15)
        self.limb_style=self.rng.choice(["stubby","spindly","tentacle","crab"])
        self.wing_style=self.rng.choice(["feathered","bat","crystal","insect"])
        self.tail_style=self.rng.choice(["curved","spiked","forked","flame","tentacle"])
        self.eye_style=self.rng.choice(["round","slit","compound","cyclops"])
        self.pattern_type=self.rng.choice(["spots","stripes","rings","scales","none"])
        self.horn_style=self.rng.choice(["pointed","curved","crystal","antler"])
        self.mouth_style=self.rng.choice(["smile","teeth","beak","tentacles","lamprey"])
        self.aura_style=self.rng.choice(["glow","sparks","rings","dna_helix","constellation"])
        self.ear_type=self.rng.choice(["none","pointed","frilled","antenna"])
        self.leg_count_bias=self.rng.choice([2,4,6,8])
    def level(self,td):
        return 0 if td<=0 else math.log10(td+1)*2.5
    def body_size(self,td): return 30+min(self.level(td),12)*4.2
    def body_segments(self,td): return 1+int(min(self.level(td),10)/2.5)
    def body_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+lv*self.hue_speed+t*0.02)%1.0
        sat=0.5+min(lv,8)*0.05; val=0.6+min(lv,10)*0.03
        r,g,b=colorsys.hsv_to_rgb(hue,min(sat,0.95),min(val,0.95))
        return(int(r*255),int(g*255),int(b*255))
    def accent_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+0.4+lv*self.hue_speed*0.7+t*0.015)%1.0
        r,g,b=colorsys.hsv_to_rgb(hue,0.7,0.8); return(int(r*255),int(g*255),int(b*255))
    def eye_count(self,td): return 1 if self.eye_style=="cyclops" else min(2+int(self.level(td)/3),8)
    def eye_size(self,td): return 5+min(self.level(td),8)*1.2
    def limb_count(self,td):
        lv=self.level(td); return 0 if lv<1.5 else min(self.leg_count_bias,int(lv/1.5)*2)
    def limb_length(self,td): return min(self.level(td),8)*6
    def has_wings(self,td): return self.level(td)>=4.0
    def wing_size(self,td): return 0 if not self.has_wings(td) else min((self.level(td)-4.0)*12,80)
    def tail_length(self,td):
        lv=self.level(td); return 0 if lv<1.0 else min((lv-1.0)*15,120)
    def spike_count(self,td): return int(min(self.level(td),10)*0.8)
    def spike_size(self,td): lv=self.level(td); return 0 if lv<2 else min((lv-2)*3,25)
    def has_pattern(self,td): return self.level(td)>=3.0 and self.pattern_type!="none"
    def pattern_opacity(self,td): return 0 if not self.has_pattern(td) else min((self.level(td)-3.0)/3.0,1.0)
    def has_aura(self,td): return self.level(td)>=5.5
    def aura_intensity(self,td): return 0 if not self.has_aura(td) else min((self.level(td)-5.5)/4.0,1.0)
    def has_horns(self,td): return self.level(td)>=3.5
    def horn_count(self,td): return 0 if not self.has_horns(td) else min(int((self.level(td)-3.5)*1.5)+1,6)
    def horn_size(self,td): return 0 if not self.has_horns(td) else min((self.level(td)-3.5)*5,35)
    def mouth_complexity(self,td): return min(self.level(td)/8.0,1.0)
    def has_ears(self,td): return self.ear_type!="none" and self.level(td)>=2.0
    def ear_size(self,td): return 0 if not self.has_ears(td) else min((self.level(td)-2.0)*5,30)
    def bioluminescence(self,td): return min(self.level(td)/12.0,1.0)
    def proc_name(self,td):
        lv=self.level(td)
        pf=["Proto","Nano","Micro","Alpha","Beta","Gamma","Mega","Giga","Ultra","Hyper","Nova","Cosmic","Elder","Ancient","Omega"]
        bd=["Spore","Cell","Blob","Flop","Wurm","Crawler","Slinker","Lurker","Stalker","Drake","Wyrm","Serpent","Leviathan","Titan","Colossus","Behemoth"]
        sf=["ling","ite","us","ax","on","ix","ar","oth","ius","os","ux","ath","eon","ion","ium","or"]
        return f"{pf[min(int(lv/1.2),len(pf)-1)]}{bd[min(int(lv/1.0),len(bd)-1)]}{sf[min(int(lv/2.0),len(sf)-1)]}"
    def click_multiplier(self,td): return 1+self.level(td)*0.4
    def cps_multiplier(self,td): return 1+self.level(td)*0.3
    def to_dict(self):
        return {k:getattr(self,k) for k in ["seed","hue_offset","hue_speed","body_width_ratio",
            "limb_style","wing_style","tail_style","eye_style","pattern_type","horn_style",
            "mouth_style","aura_style","ear_type","leg_count_bias"]}
    @classmethod
    def from_dict(cls,d):
        g=cls.__new__(cls); g.seed=d["seed"]; g.rng=SeededRNG(g.seed)
        for k in ["hue_offset","hue_speed","body_width_ratio","limb_style","wing_style","tail_style",
                   "eye_style","pattern_type","horn_style","mouth_style","aura_style","ear_type","leg_count_bias"]:
            setattr(g,k,d[k])
        return g
Genome.has_wings_at_level=lambda s,lv:lv>=4.0; Genome.has_horns_at_level=lambda s,lv:lv>=3.5
Genome.has_aura_at_level=lambda s,lv:lv>=5.5; Genome.has_pattern_at_level=lambda s,lv:lv>=3.0

# ─────────────── ACHIEVEMENTS (with rewards) ───────────────
ACHIEVEMENTS = [
    {"id":"first_click","name":"First Contact","desc":"Click the creature","reward_type":"click","reward":1},
    {"id":"click_100","name":"Clicker","desc":"Click 100 times","reward_type":"click","reward":2},
    {"id":"click_1k","name":"Click Master","desc":"Click 1,000 times","reward_type":"click","reward":5},
    {"id":"click_10k","name":"Click Legend","desc":"Click 10,000 times","reward_type":"click","reward":20},
    {"id":"dna_100","name":"DNA Collector","desc":"Earn 100 total DNA","reward_type":"cps","reward":1},
    {"id":"dna_10k","name":"Gene Hoarder","desc":"Earn 10K total DNA","reward_type":"cps","reward":5},
    {"id":"dna_1m","name":"Biotech Baron","desc":"Earn 1M total DNA","reward_type":"click","reward":50},
    {"id":"dna_1b","name":"Genome God","desc":"Earn 1B total DNA","reward_type":"cps","reward":200},
    {"id":"dna_1t","name":"Singularity","desc":"Earn 1T total DNA","reward_type":"click","reward":5000},
    {"id":"combo_5","name":"Combo Starter","desc":"Reach 5x combo","reward_type":"crit_chance","reward":0.01},
    {"id":"combo_20","name":"Combo Frenzy","desc":"Reach 20x combo","reward_type":"crit_chance","reward":0.02},
    {"id":"combo_50","name":"Combo Madness","desc":"Reach 50x combo","reward_type":"crit_mult","reward":1},
    {"id":"crit_first","name":"Lucky Strike","desc":"First critical hit","reward_type":"click","reward":3},
    {"id":"crit_10","name":"Critical Mass","desc":"10 critical hits","reward_type":"crit_chance","reward":0.01},
    {"id":"upgrade_first","name":"Investor","desc":"First upgrade","reward_type":"cps","reward":2},
    {"id":"upgrade_50","name":"Hoarder","desc":"50 total upgrades","reward_type":"cps","reward":20},
    {"id":"prestige_1","name":"Rebirth","desc":"First prestige","reward_type":"click","reward":100},
    {"id":"prestige_5","name":"Transcendence","desc":"Prestige 5 times","reward_type":"prestige_bonus","reward":0.5},
    {"id":"level_5","name":"Evolved","desc":"Reach evo level 5","reward_type":"cps","reward":10},
    {"id":"level_10","name":"Advanced","desc":"Reach evo level 10","reward_type":"click","reward":200},
    {"id":"level_15","name":"Apex","desc":"Reach evo level 15","reward_type":"cps","reward":500},
    {"id":"cps_100","name":"Automation","desc":"Reach 100 DNA/sec","reward_type":"cps","reward":25},
    {"id":"cps_10k","name":"Factory","desc":"Reach 10K DNA/sec","reward_type":"click","reward":500},
    {"id":"boss_1","name":"Boss Slayer","desc":"Defeat first boss","reward_type":"click","reward":50},
    {"id":"boss_10","name":"Boss Hunter","desc":"Defeat 10 bosses","reward_type":"crit_chance","reward":0.03},
    {"id":"orb_50","name":"Orb Catcher","desc":"Collect 50 orbs","reward_type":"cps","reward":15},
    {"id":"mutation_5","name":"Mutant","desc":"Experience 5 mutations","reward_type":"click","reward":30},
]

# ─────────────── ACTIVE ABILITIES ───────────────
ABILITIES = [
    {"id":"storm","name":"DNA Storm","key":"Q","desc":"10x click for 5s","duration":5,"cooldown":30,"unlock_dna":500,"color":CYAN},
    {"id":"warp","name":"Time Warp","key":"W","desc":"10x CPS for 8s","duration":8,"cooldown":45,"unlock_dna":5000,"color":PURPLE},
    {"id":"surge","name":"Crit Surge","key":"E","desc":"100% crit for 6s","duration":6,"cooldown":35,"unlock_dna":50000,"color":RED},
    {"id":"frenzy","name":"Frenzy","key":"R","desc":"No combo decay 10s","duration":10,"cooldown":40,"unlock_dna":500000,"color":GREEN},
]

# ─────────────── MUTATION EVENTS ───────────────
MUTATIONS = [
    {"id":"dna_frenzy","name":"DNA Frenzy","desc":"2x all income!","mult_type":"all","mult_value":2.0,"duration":30,"color":GOLD},
    {"id":"golden_touch","name":"Golden Touch","desc":"3x click power!","mult_type":"click","mult_value":3.0,"duration":25,"color":YELLOW},
    {"id":"slow_meta","name":"Slow Metabolism","desc":"0.5x CPS...","mult_type":"cps","mult_value":0.5,"duration":20,"color":RED},
    {"id":"lucky_stars","name":"Lucky Stars","desc":"25% crit chance!","mult_type":"crit","mult_value":25.0,"duration":20,"color":ORANGE},
    {"id":"evolve_burst","name":"Evolution Burst","desc":"Visual evolution +3!","mult_type":"evo","mult_value":3.0,"duration":35,"color":PINK},
    {"id":"mega_combo","name":"Mega Combo","desc":"Combo starts at 10x!","mult_type":"combo","mult_value":10.0,"duration":15,"color":CYAN},
]

# ─────────────── BOSS DATA ───────────────
BOSS_NAMES = ["Alpha Slime","Crystal Golem","Shadow Wraith","Void Serpent","Storm Titan","Chaos Beast","Dimensional Eye","Cosmic Horror"]
BOSS_COLORS = [(100,200,100),(150,180,255),(120,50,180),(80,0,120),(200,200,50),(200,50,50),(200,100,255),(100,0,200)]

# ─────────────── BACKGROUND ───────────────
class Starfield:
    def __init__(self):
        self.stars=[{"x":random.uniform(0,WIDTH),"y":random.uniform(0,HEIGHT),
            "b":random.uniform(0.2,1),"s":random.uniform(1,4),"sz":random.uniform(0.5,2.5),"al":random.uniform(0,8)} for _ in range(200)]
    def draw(self,surf,lv,t):
        for s in self.stars:
            if lv<s["al"]:
                continue
                a=min(1,(lv-s["al"])*0.5); tw=(math.sin(t*s["s"]+s["x"])+1)*0.5

                br=s["b"]*a*(0.4+0.6*tw); c=int(255*br); sz=max(1,int(s["sz"]*(0.5+a*0.5)))

            if sz<=1:
                surf.set_at((int(s["x"])%WIDTH,int(s["y"])%HEIGHT),(c,c,min(255,int(c*1.1))))
            else: pygame.draw.circle(surf,(c,c,min(255,int(c*1.1))),(int(s["x"])%WIDTH,int(s["y"])%HEIGHT),sz)

class AmbientParticle:
    def __init__(self): self.reset(); self.y=random.uniform(0,HEIGHT)
    def reset(self):
        self.x=random.uniform(0,WIDTH); self.y=-5; self.vy=random.uniform(10,30)
        self.vx=random.uniform(-8,8); self.sz=random.uniform(1,3); self.a=random.uniform(0.1,0.4)
        self.color=random.choice([(100,200,255),(150,100,255),(100,255,150)])
    def update(self,dt):
        self.x+=self.vx*dt; self.y+=self.vy*dt
        if self.y>HEIGHT+10:
            self.reset()
    def draw(self,surf,lv):
        if lv<2:
            return; a=min(1,(lv-2)*0.2)*self.a; c=tuple(int(v*a) for v in self.color)
            pygame.draw.circle(surf,c,(int(self.x),int(self.y)),max(1,int(self.sz)))


# ─────────────── EFFECTS ───────────────
class Particle:
    def __init__(self,x,y,color,vx=None,vy=None,lifetime=1.0,size=4):
        self.x=x;self.y=y;self.color=color;self.vx=vx or random.uniform(-80,80);self.vy=vy or random.uniform(-120,-30)
        self.lifetime=self.max_life=lifetime;self.size=size
    def update(self,dt): self.x+=self.vx*dt;self.y+=self.vy*dt;self.vy+=100*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,self.lifetime/self.max_life);c=tuple(int(v*a) for v in self.color);sz=max(1,int(self.size*a))
        pygame.draw.circle(s,c,(int(self.x),int(self.y)),sz)
    @property
    def alive(self): return self.lifetime>0

class FloatingText:
    def __init__(self,x,y,text,color=GOLD,size="md"):
        self.x=x;self.y=y;self.text=text;self.color=color;self.lifetime=self.max_life=1.4
        self.font={"sm":font_sm,"md":font_md,"lg":font_lg}[size]
    def update(self,dt): self.y-=55*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,min(1,self.lifetime/(self.max_life*0.5)))
        c=tuple(int(v*a+bg*(1-a)) for v,bg in zip(self.color,BG_TOP))
        t=self.font.render(self.text,True,c);s.blit(t,(self.x-t.get_width()//2,int(self.y)))
    @property
    def alive(self): return self.lifetime>0

class Toast:
    def __init__(self,title,desc,icon_color=GOLD):
        self.title=title;self.desc=desc;self.icon_color=icon_color;self.lifetime=self.max_life=4.0;self.slide=0
    def update(self,dt): self.lifetime-=dt;self.slide=min(1,self.slide+dt*5)
    def draw(self,s,idx):
        if self.lifetime<=0:
            return; fade=min(1,self.lifetime/1.0)
            tx=WIDTH-320+(320+10-int(330*self.slide)); y=20+idx*60; w,h=300,52

            ts=pygame.Surface((w,h),pygame.SRCALPHA)

            pygame.draw.rect(ts,(30,25,70,int(220*fade)),(0,0,w,h),border_radius=10)

            pygame.draw.rect(ts,(*self.icon_color,int(200*fade)),(0,0,w,h),2,border_radius=10)

            s.blit(ts,(int(tx),y))

            pygame.draw.circle(s,self.icon_color,(int(tx+18),y+16),8)

            star=font_xs.render("*",True,WHITE);s.blit(star,(int(tx+14),y+9))

            tc=tuple(int(min(255,v*fade)) for v in GOLD);tt=font_sm.render(self.title,True,tc);s.blit(tt,(int(tx+34),y+6))

            dc=tuple(int(min(255,v*fade)) for v in MUTED);dt2=font_xs.render(self.desc,True,dc);s.blit(dt2,(int(tx+34),y+26))

    @property
    def alive(self): return self.lifetime>0

class Sparkline:
    def __init__(self,mp=120): self.data=[];self.max_p=mp;self.timer=0;self.interval=0.5
    def update(self,dt,v):
        self.timer+=dt
        if self.timer>=self.interval:
            self.timer=0;self.data.append(v)
        if len(self.data)>self.max_p:
            self.data.pop(0)
    def draw(self,s,x,y,w,h,color=CYAN):
        if len(self.data)<2:
            return;mv=max(self.data) or 1
            pygame.draw.rect(s,DARK_PURPLE,(x,y,w,h),border_radius=4)

            pygame.draw.rect(s,PANEL_BORDER,(x,y,w,h),1,border_radius=4)

            pts=[(int(x+2+(i/(self.max_p-1))*(w-4)),int(y+h-2-(v/mv)*(h-4))) for i,v in enumerate(self.data)]

        if len(pts)>1:
            pygame.draw.lines(s,color,False,pts,1)
            lbl=font_xxs.render(f"{fmt(self.data[-1])}/s",True,MUTED);s.blit(lbl,(x+3,y+1))


# ─────────────── FALLING ORBS ───────────────
class DNAOrb:
    def __init__(self, total_dna):
        self.x=random.uniform(30,590); self.y=-20; self.vy=random.uniform(30,60)
        self.vx=random.uniform(-10,10); self.alive=True; self.pulse=random.uniform(0,6)
        # Value scales with progression
        scale = max(1, math.log10(total_dna+1))
        r = random.random()
        if r < 0.6:
            self.value=scale*5; self.radius=8; self.color=GREEN; self.name="Small"
        elif r < 0.85: self.value=scale*25; self.radius=12; self.color=CYAN; self.name="Medium"
        elif r < 0.97: self.value=scale*150; self.radius=16; self.color=PURPLE; self.name="Large"
        else: self.value=scale*1000; self.radius=20; self.color=GOLD; self.name="Golden!"
    def update(self,dt):
        self.y+=self.vy*dt; self.x+=self.vx*dt+math.sin(self.y*0.02)*0.5; self.pulse+=dt*4
        if self.y>HEIGHT+30:
            self.alive=False
    def draw(self,s):
        p=0.7+0.3*math.sin(self.pulse); r=int(self.radius*p)
        gs=pygame.Surface((r*4,r*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,40),(r*2,r*2),r*2)
        pygame.draw.circle(gs,(*self.color,120),(r*2,r*2),r)
        pygame.draw.circle(gs,(*WHITE,180),(r*2,r*2),max(2,r//2))
        s.blit(gs,(int(self.x-r*2),int(self.y-r*2)))
    def hit_test(self,mx,my): return math.sqrt((mx-self.x)**2+(my-self.y)**2)<self.radius*1.5

# ─────────────── BOSS ───────────────
class Boss:
    def __init__(self, tier, total_dna):
        self.tier=min(tier, len(BOSS_NAMES)-1)
        self.name=BOSS_NAMES[self.tier]; self.color=BOSS_COLORS[self.tier]
        self.max_hp=int((100+self.tier*300)*(1+math.log10(total_dna+1)*2))
        self.hp=self.max_hp; self.x=310; self.y=300; self.alive=True
        self.reward=int(self.max_hp*5*(1+self.tier*0.5))
        self.timer=45+self.tier*10; self.flash=0; self.shake=0
        self.spawn_anim=1.0
    def update(self,dt):
        self.timer-=dt; self.flash=max(0,self.flash-dt); self.shake=max(0,self.shake-dt)
        self.spawn_anim=max(0,self.spawn_anim-dt*2)
        if self.timer<=0:
            self.alive=False
        if self.hp<=0:
            self.alive=False
    def damage(self,amount):
        self.hp-=amount; self.flash=0.15; self.shake=0.08
    def draw(self,s,t):
        if not self.alive:
            return
            sx=int(self.shake*20*(random.random()*2-1)); sy=int(self.shake*15*(random.random()*2-1))

            cx,cy=self.x+sx,self.y+sy; scale=min(1,self.spawn_anim)*1.0

        # Warning flash
        if self.spawn_anim>0.5:
            ws=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            a=int(60*(self.spawn_anim-0.5)*2*(math.sin(t*15)+1)*0.5)
            ws.fill((*RED,max(0,min(255,a)))); s.blit(ws,(0,0))
        # Body
        bob=math.sin(t*1.5)*8*scale; size=(50+self.tier*10)*scale
        # Aura
        asurf=pygame.Surface((int(size*6),int(size*6)),pygame.SRCALPHA)
        pulse=(math.sin(t*3)+1)*0.5
        pygame.draw.circle(asurf,(*self.color,int(30*(0.5+0.5*pulse))),(int(size*3),int(size*3)),int(size*2.5))
        s.blit(asurf,(int(cx-size*3),int(cy-size*3+bob)))
        # Spiky body
        pts=[]
        for a in range(0,360,15):
            rad=math.radians(a); spike=math.sin(a*3+t*2)*5*scale
            r=size+spike+(15 if a%30<15 else 0)*scale
            pts.append((cx+math.sin(rad)*r,cy+math.cos(rad)*r*0.8+bob))
        body_c=self.color if self.flash<=0 else WHITE
        pygame.draw.polygon(s,body_c,pts)
        pygame.draw.polygon(s,tuple(min(255,c+60) for c in self.color),pts,2)
        # Eyes
        for side in [-1,1]:
            ex=int(cx+side*15*scale); ey=int(cy-10*scale+bob)
            pygame.draw.circle(s,WHITE,(ex,ey),int(8*scale))
            pygame.draw.circle(s,(200,0,0),(ex+int(side*2*scale),ey),int(4*scale))
            pygame.draw.circle(s,WHITE,(ex+int(side*1*scale),ey-int(2*scale)),max(1,int(2*scale)))
        # HP bar
        bw=200; bh=12; bx=cx-bw//2; by=cy-int(size*1.2+bob)
        pygame.draw.rect(s,DARK_RED,(bx,by,bw,bh),border_radius=4)
        hw=int(bw*max(0,self.hp/self.max_hp))
        if hw>0:
            for px in range(hw):
                ratio=px/bw; c=(int(200*(1-ratio)+50*ratio),int(50+150*ratio),50)
                pygame.draw.line(s,c,(bx+px,by),(bx+px,by+bh-1))
        pygame.draw.rect(s,WHITE,(bx,by,bw,bh),1,border_radius=4)
        hp_txt=font_xs.render(f"{max(0,self.hp):.0f}/{self.max_hp}",True,WHITE)
        s.blit(hp_txt,(cx-hp_txt.get_width()//2,by-1))
        # Name & timer
        nt=font_md.render(f"BOSS: {self.name}",True,RED)
        s.blit(nt,(cx-nt.get_width()//2,by-22))
        tc=RED if self.timer<10 else ORANGE if self.timer<20 else MUTED
        tt=font_sm.render(f"Time: {self.timer:.0f}s  |  Reward: {fmt(self.reward)}",True,tc)
        s.blit(tt,(cx-tt.get_width()//2,by+bh+4))

# ─────────────── UPGRADES ───────────────
UPGRADES = [
    {"name":"Click Power","desc":"+1 DNA/click","base_cost":10,"cost_mult":1.15,"type":"click","value":1,"key":"1"},
    {"name":"Auto Cell","desc":"+0.5 DNA/sec","base_cost":25,"cost_mult":1.18,"type":"cps","value":0.5,"key":"2"},
    {"name":"Click Boost","desc":"+3 DNA/click","base_cost":200,"cost_mult":1.15,"type":"click","value":3,"key":"3"},
    {"name":"Amoeba Swarm","desc":"+2 DNA/sec","base_cost":500,"cost_mult":1.18,"type":"cps","value":2,"key":"4"},
    {"name":"Mega Click","desc":"+15 DNA/click","base_cost":5e3,"cost_mult":1.15,"type":"click","value":15,"key":"5"},
    {"name":"Bacteria Colony","desc":"+10 DNA/sec","base_cost":1e4,"cost_mult":1.18,"type":"cps","value":10,"key":"6"},
    {"name":"Hyper Click","desc":"+100 DNA/click","base_cost":1e5,"cost_mult":1.15,"type":"click","value":100,"key":"7"},
    {"name":"Biome Engine","desc":"+75 DNA/sec","base_cost":2e5,"cost_mult":1.18,"type":"cps","value":75,"key":"8"},
    {"name":"Omega Click","desc":"+1K DNA/click","base_cost":2e6,"cost_mult":1.15,"type":"click","value":1000,"key":"9"},
    {"name":"Evolution Core","desc":"+500 DNA/sec","base_cost":5e6,"cost_mult":1.18,"type":"cps","value":500,"key":"0"},
    {"name":"Singularity Tap","desc":"+10K/click","base_cost":5e7,"cost_mult":1.15,"type":"click","value":1e4,"key":""},
    {"name":"Genesis Engine","desc":"+5K DNA/sec","base_cost":1e8,"cost_mult":1.18,"type":"cps","value":5e3,"key":""},
]
BUY_AMOUNTS=[1,10,100,-1]; BUY_LABELS=["x1","x10","x100","MAX"]

# ─────────────── CREATURE RENDERER (compact) ───────────────
# ─────────────── CREATURE RENDERER ───────────────
class CreatureRenderer:
    def __init__(self, genome):
        self.g = genome

    def draw(self, surface, cx, cy, td, t, hover=False):
        g = self.g
        sf = 1.0 + hover * 0.07
        bob = math.sin(t * 2.0) * 6
        color = g.body_color(td, t)
        acc = g.accent_color(td, t)
        bs = g.body_size(td) * sf
        cy_b = cy + bob
        # Shadow
        sw, sh = int(bs * 2.2), max(4, int(bs * 0.3))
        shadow_surf = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 40), (0, 0, sw * 2, sh * 2))
        surface.blit(shadow_surf, (cx - sw, cy + bs * 0.9))
        # Draw layers
        if g.has_aura(td):
            self._draw_aura(surface, cx, cy_b, bs, td, t, color, acc)
        if g.tail_length(td) > 0:
            self._draw_tail(surface, cx, cy_b, bs, td, t, color, acc)
        if g.limb_count(td) > 0:
            self._draw_limbs(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_wings(td):
            self._draw_wings(surface, cx, cy_b, bs, td, t, color, acc)
        self._draw_body(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_pattern(td):
            self._draw_pattern(surface, cx, cy_b, bs, td, t, color, acc)
        if g.spike_count(td) > 0:
            self._draw_spikes(surface, cx, cy_b, bs, td, t, acc)
        hx, hy = cx - bs * 0.6, cy_b - bs * 0.5
        if g.has_ears(td):
            self._draw_ears(surface, hx, hy, bs, td, t, color, acc)
        if g.has_horns(td):
            self._draw_horns(surface, hx, hy, bs, td, t, acc)
        self._draw_eyes(surface, hx, hy, bs, td, t, color)
        self._draw_mouth(surface, hx, hy, bs, td, t, acc)
        # Bioluminescent glow
        bio = g.bioluminescence(td)
        if bio > 0.1:
            gs = pygame.Surface((int(bs * 4), int(bs * 4)), pygame.SRCALPHA)
            pulse = (math.sin(t * 3) + 1) * 0.5
            a = int(bio * (30 + 25 * pulse))
            pygame.draw.circle(gs, (*color, a), (int(bs * 2), int(bs * 2)), int(bs * 1.6))
            surface.blit(gs, (int(cx - bs * 2), int(cy_b - bs * 2)))

    def _draw_body(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        segs = g.body_segments(td)
        if segs <= 1:
            pts = []
            for a in range(360):
                r = math.radians(a)
                w = math.sin(r * 3 + t * 3) * 3 + math.sin(r * 5 + t * 2) * 2
                rx = (bs + w) * g.body_width_ratio
                ry = bs * 0.85 + w * 0.5
                pts.append((cx + math.sin(r) * rx, cy + math.cos(r) * ry))
            pygame.draw.polygon(s, col, pts)
            hl_r = max(3, int(bs * 0.3))
            hl_color = tuple(min(255, c + 60) for c in col)
            pygame.draw.circle(s, hl_color, (int(cx - bs * 0.25), int(cy - bs * 0.3)), hl_r)
        else:
            tl = bs * 2 * segs * 0.6
            sr = bs * 0.65
            for i in range(segs):
                ratio = i / max(segs - 1, 1)
                wave = math.sin(t * 2 + i * 0.8) * 12 * (1 - ratio * 0.3)
                sx = cx - tl / 2 + ratio * tl + wave
                sy = cy + ratio * bs * 0.3
                sri = sr * (1 - ratio * 0.25)
                wb = math.sin(t * 3 + i * 2) * 2
                sp = []
                for a in range(360):
                    rad = math.radians(a)
                    sp.append((sx + math.sin(rad) * (sri + wb), sy + math.cos(rad) * (sri * 0.8 + wb * 0.5)))
                seg_c = tuple(int(c * (1 - ratio * 0.15)) for c in col)
                pygame.draw.polygon(s, seg_c, sp)
                if i == 0:
                    pygame.draw.circle(s, tuple(min(255, c + 50) for c in col),
                                       (int(sx - sri * 0.2), int(sy - sri * 0.3)), max(2, int(sri * 0.3)))

    def _draw_eyes(self, s, hx, hy, bs, td, t, col):
        g = self.g
        count = g.eye_count(td)
        es = g.eye_size(td)
        style = g.eye_style
        if style == "cyclops":
            positions = [(0, 0)]
            es *= 1.8
        elif style == "compound":
            positions = []
            for row in range(min((count + 2) // 3, 3)):
                c_in_row = min(count - row * 3, 3)
                for c_ in range(c_in_row):
                    positions.append((c_ - (c_in_row - 1) / 2, row - 0.5))
            es *= 0.7
        else:
            positions = [(i - (count - 1) / 2, 0) for i in range(count)]
        for px, py in positions:
            ex = hx + px * es * 1.6
            ey = hy + py * es * 1.6 - bs * 0.1
            if style == "slit":
                pygame.draw.ellipse(s, WHITE, (int(ex - es), int(ey - es * 0.7), int(es * 2), int(es * 1.4)))
                pygame.draw.ellipse(s, (20, 20, 40),
                    (int(ex - es * 0.15), int(ey - es * 0.6), int(es * 0.3), int(es * 1.2)))
            elif style == "compound":
                for ci in range(6):
                    angle = ci * math.pi * 2 / 6 + t * 0.5
                    cr = es * 0.6
                    ccx = ex + math.cos(angle) * es * 0.4
                    ccy = ey + math.sin(angle) * es * 0.4
                    pygame.draw.circle(s, (200, 200, 255), (int(ccx), int(ccy)), max(1, int(cr)))
                    pygame.draw.circle(s, (30, 30, 60), (int(ccx), int(ccy)), max(1, int(cr * 0.5)))
            else:
                pygame.draw.circle(s, WHITE, (int(ex), int(ey)), int(es))
                look = math.sin(t * 2) * es * 0.2
                pr = es * 0.5
                pygame.draw.circle(s, (20, 20, 40), (int(ex + look), int(ey)), int(pr))
                pygame.draw.circle(s, WHITE, (int(ex + look - pr * 0.3), int(ey - pr * 0.3)), max(1, int(pr * 0.3)))

    def _draw_mouth(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        comp = g.mouth_complexity(td)
        if comp < 0.1:
            return
        mx_p = hx + bs * 0.3
        my_p = hy + bs * 0.2
        style = g.mouth_style
        if style == "smile" or comp < 0.3:
            mw = bs * 0.5 * comp
            mh = bs * 0.2 * comp
            if mw > 3:
                pygame.draw.arc(s, acc,
                    (int(mx_p - mw), int(my_p - mh), int(mw * 2), int(mh * 2)),
                    math.pi + 0.3, 2 * math.pi - 0.3, max(1, int(2 * comp + 1)))
        if comp > 0.3:
            if style == "teeth":
                tw = bs * 0.4
                for i in range(int(3 + comp * 5)):
                    tx = mx_p - tw / 2 + (i / max(int(3 + comp * 5) - 1, 1)) * tw
                    th = 3 + comp * 5
                    pygame.draw.polygon(s, WHITE, [
                        (int(tx - 2), int(my_p)), (int(tx + 2), int(my_p)), (int(tx), int(my_p + th))])
            elif style == "beak":
                bl = bs * 0.4 * comp
                pygame.draw.polygon(s, (255, 200, 80), [
                    (int(mx_p), int(my_p - 4)), (int(mx_p + bl), int(my_p)), (int(mx_p), int(my_p + 4))])
            elif style == "tentacles":
                for i in range(int(2 + comp * 4)):
                    ba = -0.5 + i * (1.0 / max(int(2 + comp * 4) - 1, 1))
                    pts = [(int(mx_p), int(my_p))]
                    for j in range(1, 6):
                        tr = j / 5
                        w = math.sin(t * 5 + i + j * 0.7) * 8 * tr
                        pts.append((int(mx_p + tr * bs * 0.5 * comp + w),
                                    int(my_p + tr * bs * 0.3 * comp + ba * bs * 0.2 * tr)))
                    if len(pts) > 1:
                        pygame.draw.lines(s, acc, False, pts, max(1, int(2)))
            elif style == "lamprey":
                mr = int(bs * 0.15 * comp)
                if mr > 2:
                    pygame.draw.circle(s, (40, 10, 10), (int(mx_p), int(my_p)), mr)
                    for i in range(int(6 + comp * 10)):
                        a = i * math.pi * 2 / int(6 + comp * 10)
                        pygame.draw.line(s, WHITE,
                            (int(mx_p + math.cos(a) * mr * 0.6), int(my_p + math.sin(a) * mr * 0.6)),
                            (int(mx_p + math.cos(a) * mr), int(my_p + math.sin(a) * mr)), 1)

    def _draw_limbs(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        count = g.limb_count(td)
        length = g.limb_length(td)
        style = g.limb_style
        if count == 0 or length < 3:
            return
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            idx = i // 2
            tp = count // 2
            spread = bs * 1.2
            bx = cx - spread / 2 + (idx / max(tp - 1, 1)) * spread if tp > 1 else cx
            by = cy + bs * 0.6
            anim = math.sin(t * 4 + i * 1.2) * 0.3
            if style == "tentacle":
                pts = [(int(bx + side * bs * 0.4), int(by))]
                for j in range(1, 8):
                    tr = j / 7
                    w = math.sin(t * 5 + i + j * 0.8) * 12 * tr
                    pts.append((int(bx + side * (bs * 0.4 + length * tr) + w),
                                int(by + length * tr * 0.5 + anim * length * tr)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(4)))
            elif style == "crab":
                kx = bx + side * (bs * 0.5 + length * 0.5)
                ky = by + length * 0.3 + anim * 10
                fx = kx + side * length * 0.4
                fy = by + length * 0.8
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(kx), int(ky)), max(2, int(4)))
                pygame.draw.line(s, acc, (int(kx), int(ky)),
                               (int(fx), int(fy)), max(2, int(3)))
                if i < 2:
                    cs = max(2, int(bs * 0.15))
                    pygame.draw.circle(s, col, (int(fx), int(fy)), cs)
            elif style == "spindly":
                px, py = bx + side * bs * 0.3, by
                for j in range(3):
                    tr = (j + 1) / 3
                    nx = px + side * length * 0.35
                    ny = py + length * 0.3 + anim * 8 * tr
                    pygame.draw.line(s, acc, (int(px), int(py)), (int(nx), int(ny)), max(1, int(2)))
                    pygame.draw.circle(s, col, (int(nx), int(ny)), max(1, int(3)))
                    px, py = nx, ny
            else:  # stubby
                fx = bx + side * (bs * 0.5 + length * 0.3)
                fy = by + length * 0.7 + anim * 8
                lw = max(3, int(bs * 0.15))
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(fx), int(fy)), lw)
                pygame.draw.circle(s, col, (int(fx), int(fy)), max(2, int(lw * 0.8)))

    def _draw_wings(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        ws = g.wing_size(td)
        if ws < 3:
            return
        style = g.wing_style
        flap = math.sin(t * 3) * 15
        for side in [-1, 1]:
            if style == "bat":
                pts = [
                    (cx + side * bs * 0.3, cy - bs * 0.3),
                    (cx + side * ws, cy - bs * 0.5 + flap),
                    (cx + side * ws * 0.7, cy - bs * 0.1 + flap * 0.6),
                    (cx + side * ws * 1.1, cy + bs * 0.1 + flap * 0.8),
                    (cx + side * ws * 0.5, cy + bs * 0.2)]
                wc = tuple(max(0, c - 50) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])
                pygame.draw.polygon(s, acc, [(int(p[0]), int(p[1])) for p in pts], 2)
            elif style == "feathered":
                for layer in range(3):
                    off = layer * 8
                    pts = [
                        (cx + side * bs * 0.2, cy - bs * 0.2),
                        (cx + side * (ws - off), cy - bs * (0.6 + layer * 0.2) + flap * (1 - layer * 0.2)),
                        (cx + side * (ws * 0.8 - off), cy + bs * 0.1 + flap * 0.5)]
                    lc = tuple(min(255, c + layer * 20) for c in col)
                    pygame.draw.polygon(s, lc, [(int(p[0]), int(p[1])) for p in pts])
            elif style == "crystal":
                for j in range(4):
                    a = math.radians(-30 + j * 25 + side * 20) + math.sin(t * 2) * 0.1
                    d = ws * (0.6 + j * 0.12)
                    tx = cx + side * math.cos(a) * d
                    ty = cy - abs(math.sin(a)) * d * 0.7 + flap * 0.3
                    pts = [(int(cx + side * bs * 0.3), int(cy - bs * 0.3)),
                           (int(tx), int(ty)),
                           (int(cx + side * 10), int(cy))]
                    als = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    pygame.draw.polygon(als, (*acc, 100), pts)
                    s.blit(als, (0, 0))
                    pygame.draw.polygon(s, acc, pts, 1)
            else:  # insect
                pts = [
                    (cx + side * bs * 0.2, cy - bs * 0.1),
                    (cx + side * ws, cy - bs * 0.8 + flap),
                    (cx + side * ws * 0.9, cy - bs * 0.2 + flap * 0.4),
                    (cx + side * ws * 0.3, cy + bs * 0.3)]
                wc = tuple(max(0, c - 30) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])

    def _draw_tail(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        length = g.tail_length(td)
        if length < 3:
            return
        style = g.tail_style
        segs = max(3, int(length / 10))
        pts = []
        for i in range(segs + 1):
            tr = i / segs
            w = math.sin(t * 3 + tr * 4) * (10 + tr * 15)
            tx = cx + bs * 0.7 + tr * length + w
            ty = cy + tr * bs * 0.3 + math.sin(t * 2 + tr * 3) * 5
            pts.append((tx, ty))
            sr = max(2, int(bs * 0.3 * (1 - tr * 0.7)))
            sc = tuple(int(c * (1 - tr * 0.2)) for c in col)
            pygame.draw.circle(s, sc, (int(tx), int(ty)), sr)
        if style == "spiked":
            for i in range(2, segs, 2):
                tr = i / segs
                px, py = pts[i]
                sh = 8 + tr * 10
                pygame.draw.polygon(s, acc, [(int(px - 3), int(py)),
                                                  (int(px + 3), int(py)),
                                                  (int(px), int(py - sh))])
        elif style == "forked":
            tx, ty = pts[-1]
            fl = length * 0.2
            for d in [-1, 1]:
                pygame.draw.line(s, acc, (int(tx), int(ty)),
                               (int(tx + fl + math.sin(t * 4 + d) * 5), int(ty + d * fl * 0.5)),
                               max(1, int(3)))
        elif style == "flame":
            tx, ty = pts[-1]
            for _ in range(5):
                fc = random.choice([(255, 100, 0), (255, 200, 0), (255, 50, 0)])
                pygame.draw.circle(s, fc,
                                   (int(tx + random.randint(-8, 12)), int(ty + random.randint(-12, 12))),
                                   random.randint(3, int(6 + g.level(td))))
        elif style == "tentacle":
            tx, ty = pts[-1]
            for d in [-1, 1]:
                tent_pts = [(int(tx), int(ty))]
                for j in range(1, 5):
                    tr = j / 4
                    w = math.sin(t * 6 + d + j) * 8
                    tent_pts.append((int(tx + d * tr * 20 + w), int(ty + tr * 15)))
                if len(tent_pts) > 1:
                    pygame.draw.lines(s, acc, False, tent_pts, max(1, int(2)))

    def _draw_spikes(self, s, cx, cy, bs, td, t, acc):
        g = self.g
        count = g.spike_count(td)
        size = g.spike_size(td)
        if count < 1 or size < 2:
            return
        for i in range(count):
            a = (i / count) * math.pi * 2 + 0.5
            if math.sin(a) > 0.2:
                continue
            sx = cx + math.cos(a) * bs * 0.85
            sy = cy + math.sin(a) * bs * 0.85
            pygame.draw.polygon(s, acc, [
                (int(sx - math.sin(a) * 3), int(sy + math.cos(a) * 3)),
                (int(sx + math.sin(a) * 3), int(sy - math.cos(a) * 3)),
                (int(sx + math.cos(a) * size), int(sy + math.sin(a) * size))])

    def _draw_horns(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        count = g.horn_count(td)
        size = g.horn_size(td)
        style = g.horn_style
        if count < 1 or size < 3:
            return
        for i in range(count):
            off = (i - (count - 1) / 2) * 12 if count > 1 else 0
            bx, by = hx + off, hy - bs * 0.4
            if style == "pointed":
                pygame.draw.polygon(s, acc, [(int(bx - 4), int(by)),
                                                  (int(bx + 4), int(by)),
                                                  (int(bx + off * 0.3), int(by - size))])
            elif style == "curved":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.4 + math.sin(tr * math.pi) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
            elif style == "crystal":
                pygame.draw.polygon(s, acc, [(int(bx), int(by - size)),
                                                  (int(bx - 5), int(by)),
                                                  (int(bx + 5), int(by))])
            elif style == "antler":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.5 + math.sin(tr * 3) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
                if len(pts) > 3:
                    bp = pts[2]
                    pygame.draw.line(s, acc, bp,
                                   (int(bp[0] + (15 if off >= 0 else -15)), int(bp[1] - 10)),
                                   max(1, int(2)))

    def _draw_ears(self, s, hx, hy, bs, td, t, col, acc):
        g = self.g
        es = g.ear_size(td)
        if es < 3:
            return
        if g.ear_type == "pointed":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.5
                ey = hy - bs * 0.3
                pygame.draw.polygon(s, col, [(int(ex - 8), int(ey)),
                                                  (int(ex + 8), int(ey)),
                                                  (int(ex + side * 5), int(ey - es))])
                pygame.draw.polygon(s, acc, [(int(ex - 8), int(ey)),
                                                   (int(ex + 8), int(ey)),
                                                   (int(ex + side * 5), int(ey - es))], 1)
        elif g.ear_type == "frilled":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.4
                ey = hy - bs * 0.2
                fp = []
                for j in range(8):
                    a = math.radians(-90 + (j / 7) * 60 * side)
                    r = es * (0.5 + math.sin(j * 1.5) * 0.3)
                    fp.append((int(ex + math.cos(a) * r * side), int(ey + math.sin(a) * r)))
                if len(fp) > 2:
                    pygame.draw.lines(s, acc, False, fp, 2)
        elif g.ear_type == "antenna":
            for side in [-1, 1]:
                bx = hx + side * bs * 0.3
                by = hy - bs * 0.3
                w = math.sin(t * 5 + side) * 5
                tx = bx + side * es * 0.5 + w
                ty = by - es + w
                pygame.draw.line(s, acc, (int(bx), int(by)), (int(tx), int(ty)), 2)
                glow = (math.sin(t * 4 + side * 2) + 1) * 0.5
                gc = tuple(int(min(255, c * (0.5 + 0.5 * glow))) for c in acc)
                pygame.draw.circle(s, gc, (int(tx), int(ty)), max(2, int(4 * glow + 2)))

    def _draw_pattern(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        op = g.pattern_opacity(td)
        pt = g.pattern_type
        if op < 0.05:
            return
        pc = tuple(int(c * op + bg * (1 - op)) for c, bg in zip(acc, col))
        if pt == "spots":
            for i in range(int(5 + g.level(td) * 1.5)):
                a = i * 2.3 + 0.5
                d = bs * (0.2 + (i % 3) * 0.2)
                pygame.draw.circle(s, pc, (int(cx + math.cos(a) * d), int(cy + math.sin(a) * d * 0.7)),
                                   max(2, int(bs * 0.1 * op)))
        elif pt == "stripes":
            for i in range(-3, 4):
                sx = cx + i * bs * 0.25
                sh = int(bs * 1.2)
                pygame.draw.line(s, pc,
                    (int(sx + math.sin(i + t) * 3), int(cy - sh // 2)),
                    (int(sx + math.sin(i + t + 1) * 3), int(cy + sh // 2)),
                    max(1, int(2 * op)))
        elif pt == "rings":
            for i in range(1, 4):
                pygame.draw.circle(s, pc, (int(cx), int(cy)),
                                   int(bs * 0.3 * i * op), max(1, int(2 * op)))
        elif pt == "scales":
            for row in range(-2, 3):
                for c_ in range(-2, 3):
                    sx = cx + c_ * bs * 0.3 + (row % 2) * bs * 0.15
                    sy = cy + row * bs * 0.25
                    if math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2) < bs * 0.8:
                        sr = int(bs * 0.12 * op)
                        pygame.draw.arc(s, pc,
                            (int(sx - sr), int(sy - sr), sr * 2, sr * 2),
                            0, math.pi, max(1, int(1.5 * op)))

    def _draw_aura(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        intensity = g.aura_intensity(td)
        style = g.aura_style
        if intensity < 0.05:
            return
        if style == "glow":
            for layer in range(3):
                r = int(bs * (1.5 + layer * 0.4) * intensity)
                a = int(30 * intensity * (1 - layer * 0.25))
                gs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                p = (math.sin(t * 3 + layer) + 1) * 0.5
                pygame.draw.circle(gs, (*col, int(a * (0.7 + 0.3 * p))),
                                   (r + 2, r + 2), r)
                s.blit(gs, (cx - r - 2, cy - r - 2))
        elif style == "sparks":
            for i in range(int(8 * intensity)):
                a = t * (1.5 + i * 0.3) + i * math.pi * 2 / 8
                d = (bs * 1.2 + math.sin(t * 2 + i) * 15) * intensity
                c = acc if i % 2 else col
                pygame.draw.circle(s, c, (int(cx + math.cos(a) * d),
                                              int(cy + math.sin(a) * d * 0.7)),
                                   max(1, int(3 * intensity)))
        elif style == "rings":
            for i in range(2):
                ra = t * (1 + i * 0.7) + i * 1.5
                rx = int((bs * 1.5 + i * 15) * intensity)
                ry = int((bs * 0.4 + i * 8) * intensity)
                rs = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
                pygame.draw.ellipse(rs, (*acc, int(80 * intensity)), (2, 2, rx * 2, ry * 2),
                                 max(1, int(2 * intensity)))
                rot = pygame.transform.rotate(rs, math.degrees(ra))
                s.blit(rot, (cx - rot.get_width() // 2, cy - rot.get_height() // 2))
        elif style == "dna_helix":
            for i in range(int(20 * intensity)):
                tr = i / max(int(20 * intensity) - 1, 1)
                a = tr * math.pi * 4 + t * 2
                d = bs * 1.3 * intensity
                for strand in [0, math.pi]:
                    sx = cx + math.cos(a + strand) * d * math.sin(tr * math.pi)
                    sy = cy - bs + tr * bs * 2
                    pygame.draw.circle(s, col if strand == 0 else acc, (int(sx), int(sy)),
                                       max(1, int(2 * intensity)))
        elif style == "constellation":
            sp = []
            for i in range(int(10 * intensity)):
                seed = i * 7.3 + 1.2
                a = seed * 2.1 + t * 0.3
                d = bs * (0.8 + (seed % 0.6) * 0.8) * intensity
                sx = cx + math.cos(a) * d
                sy = cy + math.sin(a) * d * 0.7
                sp.append((int(sx), int(sy)))
                tw = (math.sin(t * 3 + i * 2) + 1) * 0.5
                pygame.draw.circle(s, WHITE, (int(sx), int(sy)),
                                   max(1, int((1 + tw) * 2 * intensity)))
            for i in range(len(sp)):
                for j in range(i + 1, len(sp)):
                    dx = sp[i][0] - sp[j][0]
                    dy = sp[i][1] - sp[j][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < bs * 1.5 * intensity:
                        ls = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        al = max(0, min(255, int(40 * intensity * (1 - d / (bs * 1.5 * intensity)))))
                        pygame.draw.line(ls, (*acc, al), sp[i], sp[j], 1)
                        s.blit(ls, (0, 0))

# ─────────────── GAME STATE ───────────────
class Game:
    def __init__(self):
        self.dna=0.0;self.total_dna=0.0;self.total_clicks=0;self.total_crits=0
        self.total_upgrades_bought=0;self.click_power=1;self.cps=0.0
        self.upgrade_counts=[0]*len(UPGRADES)
        self.particles=[];self.float_texts=[];self.toasts=[]
        self.t=0.0;self.creature_hover=False;self.shop_scroll=0;self.max_scroll=0
        self.creature_cx=320;self.creature_cy=360
        self.shake_x=0;self.shake_y=0;self.shake_time=0
        # Prestige
        self.prestige_count=0;self.prestige_mult=1.0
        # Combo
        self.combo=0;self.combo_timer=0;self.combo_decay=1.2;self.max_combo=0
        # Crits
        self.crit_chance=0.05;self.crit_mult=5.0
        # Achievement bonus tracking
        self.ach_bonus_click=0;self.ach_bonus_cps=0;self.ach_bonus_crit=0;self.ach_bonus_prestige=0;self.ach_bonus_crit_mult=0
        # Buy amount
        self.buy_amount_idx=0;self.display_dna=0.0
        # UI panels
        self.show_traits=False;self.show_bestiary=False;self.show_stats=False;self.show_settings=False;self.show_achievements_panel=False
        self.hovered_upgrade=-1;self.panel_scroll=0
        # Background
        self.starfield=Starfield();self.ambient_particles=[AmbientParticle()for _ in range(30)]
        self.sparkline=Sparkline()
        # Achievements
        self.achievements_unlocked=set()
        # Milestones
        self.last_milestone=0;self.milestones=[10,100,1e3,1e4,1e5,1e6,1e7,1e8,1e9,1e10,1e11,1e12]
        # Auto-save
        self.autosave_timer=0;self.save_time=time.time();self.play_time=0.0
        # Boss system
        self.boss=None;self.boss_timer=random.uniform(60,120);self.bosses_defeated=0;self.boss_tier=0
        # Orbs
        self.orbs=[];self.orb_timer=0;self.orbs_collected=0
        # Abilities
        self.ability_cooldowns=[0.0]*len(ABILITIES);self.ability_actives=[0.0]*len(ABILITIES)
        self.abilities_unlocked=[False]*len(ABILITIES)
        # Mutations
        self.active_mutation=None;self.mutation_timer=0;self.mutations_experienced=0;self.mutation_event_timer=random.uniform(45,90)
        # Bestiary
        self.bestiary=[]
        # Settings
        self.sound_on=SOUND_ENABLED;self.particle_quality=2  # 0=low,1=med,2=high
        # Genome
        seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed);self.renderer=CreatureRenderer(self.genome);self.seed_display=seed
        self._try_load()

    def _try_load(self):
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE,'r') as f: data=json.load(f)
            self.dna=data.get("dna",0);self.total_dna=data.get("total_dna",0)
            self.total_clicks=data.get("total_clicks",0);self.total_crits=data.get("total_crits",0)
            self.total_upgrades_bought=data.get("total_upgrades_bought",0)
            self.click_power=data.get("click_power",1);self.cps=data.get("cps",0)
            self.upgrade_counts=data.get("upgrade_counts",[0]*len(UPGRADES))
            self.prestige_count=data.get("prestige_count",0);self.prestige_mult=data.get("prestige_mult",1.0)
            self.max_combo=data.get("max_combo",0);self.achievements_unlocked=set(data.get("achievements",[]))
            self.buy_amount_idx=data.get("buy_amount_idx",0);self.save_time=data.get("save_time",time.time())
            self.play_time=data.get("play_time",0);self.bosses_defeated=data.get("bosses_defeated",0)
            self.boss_tier=data.get("boss_tier",0);self.orbs_collected=data.get("orbs_collected",0)
            self.mutations_experienced=data.get("mutations_experienced",0)
            self.ach_bonus_click=data.get("ach_bonus_click",0);self.ach_bonus_cps=data.get("ach_bonus_cps",0)
            self.ach_bonus_crit=data.get("ach_bonus_crit",0);self.ach_bonus_prestige=data.get("ach_bonus_prestige",0)
            self.ach_bonus_crit_mult=data.get("ach_bonus_crit_mult",0)
            self.bestiary=data.get("bestiary",[]);self.sound_on=data.get("sound_on",SOUND_ENABLED)
            self.particle_quality=data.get("particle_quality",2)
            self.genome=Genome.from_dict(data["genome"]);self.renderer=CreatureRenderer(self.genome);self.seed_display=self.genome.seed
            # Offline progress
            elapsed=time.time()-self.save_time
            if elapsed>5:
                cps_val=self.effective_cps();off_earn=cps_val*elapsed*0.5
                if off_earn>0:
                    self.dna+=off_earn;self.total_dna+=off_earn
                    self.toasts.append(Toast("Welcome Back!",f"Earned {fmt(off_earn)} DNA away ({elapsed/60:.1f}m)",CYAN))
        except Exception as e: print(f"Load failed: {e}")

    def save(self):
        try:
            data={"dna":self.dna,"total_dna":self.total_dna,"total_clicks":self.total_clicks,
                "total_crits":self.total_crits,"total_upgrades_bought":self.total_upgrades_bought,
                "click_power":self.click_power,"cps":self.cps,"upgrade_counts":self.upgrade_counts,
                "prestige_count":self.prestige_count,"prestige_mult":self.prestige_mult,
                "max_combo":self.max_combo,"achievements":list(self.achievements_unlocked),
                "buy_amount_idx":self.buy_amount_idx,"save_time":time.time(),"play_time":self.play_time,
                "bosses_defeated":self.bosses_defeated,"boss_tier":self.boss_tier,
                "orbs_collected":self.orbs_collected,"mutations_experienced":self.mutations_experienced,
                "ach_bonus_click":self.ach_bonus_click,"ach_bonus_cps":self.ach_bonus_cps,
                "ach_bonus_crit":self.ach_bonus_crit,"ach_bonus_prestige":self.ach_bonus_prestige,
                "ach_bonus_crit_mult":self.ach_bonus_crit_mult,
                "bestiary":self.bestiary,"sound_on":self.sound_on,"particle_quality":self.particle_quality,
                "genome":self.genome.to_dict()}
            with open(SAVE_FILE,'w') as f: json.dump(data,f,indent=2)
        except Exception as e: print(f"Save failed: {e}")

    def prestige(self):
        if self.total_dna<1e6:
            return
            bonus=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige

            self.prestige_count+=1;self.prestige_mult+=bonus

            self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),

            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            self.dna=0;self.total_dna=0;self.click_power=1;self.cps=0

            self.upgrade_counts=[0]*len(UPGRADES);self.combo=0;self.combo_timer=0;self.last_milestone=0

            self.total_clicks=0;self.total_crits=0;self.total_upgrades_bought=0;self.sparkline=Sparkline()

            self.boss=None;self.boss_timer=random.uniform(60,120);self.active_mutation=None

            self.toasts.append(Toast("PRESTIGE!",f"+{bonus:.2f}x permanent (now {self.prestige_mult:.2f}x)",GOLD))

            self._play(snd_prestige);self._burst(self.creature_cx,self.creature_cy,80,[GOLD,CYAN,WHITE,PURPLE]);self.save()


    def _trait_summary(self):
        g=self.genome;td=self.total_dna
        return{"limbs":g.limb_style,"wings":g.wing_style,"eyes":g.eye_style,"tail":g.tail_style,
               "horns":g.horn_style,"mouth":g.mouth_style,"aura":g.aura_style,"pattern":g.pattern_type,
               "ears":g.ear_type,"level":f"{g.level(td):.1f}"}

    def upgrade_cost(self,idx):
        upg=UPGRADES[idx];base=upg["base_cost"];cm=upg["cost_mult"];owned=self.upgrade_counts[idx];amt=self.get_buy_amount()
        if amt==-1:
            total=0;count=0
            while True:
                c=int(base*(cm**(owned+count)));total+=c;count+=1
                if self.dna-total<c or count>10000:
                    total-=c;count-=1;break
            return total,count
        else:total=sum(int(base*(cm**(owned+i)))for i in range(amt));return total,amt

    def get_buy_amount(self):return BUY_AMOUNTS[self.buy_amount_idx]

    def effective_click(self):
        m=self.genome.click_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("click"))
        if self.ability_actives[0]>0:
            m*=10  # DNA Storm
            return(self.click_power+self.ach_bonus_click)*m


    def effective_cps(self):
        m=self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("cps"))
        if self.ability_actives[1]>0:
            m*=10  # Time Warp
            return(self.cps+self.ach_bonus_cps)*m


    def effective_crit_chance(self):
        c=self.crit_chance+self.ach_bonus_crit
        if self.ability_actives[2]>0:
            c=1.0  # Crit Surge
            mut=self._get_mutation_mult("crit")

        if mut>0:
            c=max(c,mut/100)
            return min(c,1.0)


    def effective_crit_mult(self):
        return self.crit_mult+self.ach_bonus_crit_mult

    def _get_mutation_mult(self,mtype):
        if not self.active_mutation:
            return 0
        if self.active_mutation["mult_type"]==mtype:
            return self.active_mutation["mult_value"]-1
        if self.active_mutation["mult_type"]=="all"and mtype in("click","cps"):
            return self.active_mutation["mult_value"]-1
            return 0


    def _play(self,snd):
        if snd and self.sound_on:
            try:snd.play()
            except:pass

    def click_creature(self,mx,my):
        self.total_clicks+=1;self.combo+=1;self.combo_timer=self.combo_decay
        # Mutation combo boost
        if self.active_mutation and self.active_mutation["mult_type"]=="combo":
            self.combo=max(self.combo,int(self.active_mutation["mult_value"]))
        if self.combo>self.max_combo:
            self.max_combo=self.combo
            combo_mult=1.0+(self.combo-1)*0.1

            is_crit=random.random()<self.effective_crit_chance()

        if is_crit:
            self.total_crits+=1;combo_mult*=self.effective_crit_mult()
            earned=self.effective_click()*combo_mult

            self.dna+=earned;self.total_dna+=earned;color=self.genome.body_color(self.total_dna,self.t)

            pcount=max(1,self.particle_quality)

            if is_crit:
                for _ in range(random.randint(5,15)*pcount):
                    self.particles.append(Particle(mx,my,random.choice([GOLD,ORANGE,RED,WHITE]),lifetime=random.uniform(0.4,1.0),size=random.randint(3,9)))
                self.float_texts.append(FloatingText(mx,my-30,f"CRIT! +{fmt(earned)}",ORANGE,"lg"))
            self.shake_time=0.15;self._play(snd_crit)
        else:
            for _ in range(random.randint(2,4+min(self.combo,10))*pcount):
                self.particles.append(Particle(mx,my,color,lifetime=random.uniform(0.2,0.6),size=random.randint(2,5)))
            prefix=f"{self.combo}x "if self.combo>1 else""
            self.float_texts.append(FloatingText(mx,my-20,f"{prefix}+{fmt(earned)}",GOLD))
            self._play(snd_click)
        if self.combo>1 and self.combo%5==0:
            self._play(snd_combo)
        # Damage boss if active
        if self.boss and self.boss.alive:
            self.boss.damage(earned)
            self._play(snd_boss_hit)
            if self.boss.hp<=0:
                self.dna+=self.boss.reward;self.total_dna+=self.boss.reward
                self.float_texts.append(FloatingText(self.boss.x,self.boss.y-60,f"BOSS DEFEATED! +{fmt(self.boss.reward)}",GOLD,"lg"))
                self._play(snd_boss_die);self.bosses_defeated+=1;self.boss_tier+=1
                self._burst(self.boss.x,self.boss.y,50,[GOLD,RED,ORANGE]);self.boss=None
        self._check_achievements();self._check_milestones()

    def buy_upgrade(self,idx):
        total_cost,amount=self.upgrade_cost(idx)
        if self.dna>=total_cost and amount>0:
            self.dna-=total_cost;self.upgrade_counts[idx]+=amount;upg=UPGRADES[idx]
            if upg["type"]=="click":
                self.click_power+=upg["value"]*amount
            elif upg["type"]=="cps":self.cps+=upg["value"]*amount
            self.total_upgrades_bought+=amount;self._play(snd_buy);self._check_achievements();return True
        return False

    def activate_ability(self,idx):
        if idx>=len(ABILITIES):
            return
            ab=ABILITIES[idx]

        if not self.abilities_unlocked[idx]:
            return
        if self.ability_cooldowns[idx]>0 or self.ability_actives[idx]>0:
            return
            self.ability_actives[idx]=ab["duration"];self.ability_cooldowns[idx]=ab["cooldown"]

            self.toasts.append(Toast(f"{ab['name']}!",ab["desc"],ab["color"]))

            self._play(snd_ability);self._burst(self.creature_cx,self.creature_cy,20,[ab["color"]])


    def collect_orb(self,orb,mx,my):
        self.dna+=orb.value;self.total_dna+=orb.value;self.orbs_collected+=1;orb.alive=False
        self.float_texts.append(FloatingText(mx,my-15,f"+{fmt(orb.value)} {orb.name}",orb.color))
        for _ in range(8):
            self.particles.append(Particle(mx,my,orb.color,lifetime=0.5,size=3))
            self._play(snd_orb);self._check_achievements()


    def _start_mutation(self):
        mut=random.choice(MUTATIONS)
        self.active_mutation=mut;self.mutation_timer=mut["duration"];self.mutations_experienced+=1
        self.toasts.append(Toast(f"Mutation: {mut['name']}!",mut["desc"],mut["color"]))
        self._play(snd_mutation);self._check_achievements()

    def _grant_achievement_reward(self,ach):
        rt=ach["reward_type"];rv=ach["reward"]
        if rt=="click":
            self.ach_bonus_click+=rv
        elif rt=="cps":self.ach_bonus_cps+=rv
        elif rt=="crit_chance":self.ach_bonus_crit+=rv
        elif rt=="crit_mult":self.ach_bonus_crit_mult+=rv
        elif rt=="prestige_bonus":self.ach_bonus_prestige+=rv

    def _check_achievements(self):
        checks={"first_click":lambda:self.total_clicks>=1,"click_100":lambda:self.total_clicks>=100,
            "click_1k":lambda:self.total_clicks>=1000,"click_10k":lambda:self.total_clicks>=10000,
            "dna_100":lambda:self.total_dna>=100,"dna_10k":lambda:self.total_dna>=1e4,
            "dna_1m":lambda:self.total_dna>=1e6,"dna_1b":lambda:self.total_dna>=1e9,"dna_1t":lambda:self.total_dna>=1e12,
            "combo_5":lambda:self.max_combo>=5,"combo_20":lambda:self.max_combo>=20,"combo_50":lambda:self.max_combo>=50,
            "crit_first":lambda:self.total_crits>=1,"crit_10":lambda:self.total_crits>=10,
            "upgrade_first":lambda:self.total_upgrades_bought>=1,"upgrade_50":lambda:self.total_upgrades_bought>=50,
            "prestige_1":lambda:self.prestige_count>=1,"prestige_5":lambda:self.prestige_count>=5,
            "level_5":lambda:self.genome.level(self.total_dna)>=5,"level_10":lambda:self.genome.level(self.total_dna)>=10,
            "level_15":lambda:self.genome.level(self.total_dna)>=15,
            "cps_100":lambda:self.effective_cps()>=100,"cps_10k":lambda:self.effective_cps()>=1e4,
            "boss_1":lambda:self.bosses_defeated>=1,"boss_10":lambda:self.bosses_defeated>=10,
            "orb_50":lambda:self.orbs_collected>=50,"mutation_5":lambda:self.mutations_experienced>=5}
        for ach in ACHIEVEMENTS:
            if ach["id"]not in self.achievements_unlocked:
                chk=checks.get(ach["id"])
                if chk and chk():
                    self.achievements_unlocked.add(ach["id"]);self._grant_achievement_reward(ach)
                    self.toasts.append(Toast(f"Achievement: {ach['name']}",f"{ach['desc']} (+reward!)",GOLD))
                    self._play(snd_achieve)

    def _check_milestones(self):
        for m in self.milestones:
            if self.total_dna>=m and self.last_milestone<m:
                self.last_milestone=m;self.shake_time=0.1
                self.float_texts.append(FloatingText(self.creature_cx,self.creature_cy-100,f"MILESTONE: {fmt(m)} DNA!",CYAN,"lg"))
                self._burst(self.creature_cx,self.creature_cy,30,[GOLD,CYAN,GREEN,PINK,PURPLE])

    def _burst(self,x,y,n,colors):
        for _ in range(n):
            a=random.uniform(0,2*math.pi);sp=random.uniform(60,200)
            self.particles.append(Particle(x,y,random.choice(colors),math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.6,1.5),random.randint(3,7)))

    def update(self,dt):
        self.t+=dt;self.play_time+=dt
        # Combo decay (unless Frenzy active)
        if self.ability_actives[3]<=0:
            if self.combo_timer>0:
                self.combo_timer-=dt
                if self.combo_timer<=0:
                    self.combo=0
        # Auto DNA
        auto=self.effective_cps()*dt;self.dna+=auto;self.total_dna+=auto
        self._check_achievements();self._check_milestones()
        # Particles
        for p in self.particles:
            p.update(dt)
            self.particles=[p for p in self.particles if p.alive]

        for ft in self.float_texts:
            ft.update(dt)
            self.float_texts=[ft for ft in self.float_texts if ft.alive]

        for t in self.toasts:
            t.update(dt)
            self.toasts=[t for t in self.toasts if t.alive]

        # Shake
        if self.shake_time>0:
            self.shake_time-=dt;i=self.shake_time*40;self.shake_x=random.uniform(-i,i);self.shake_y=random.uniform(-i,i)
        else:self.shake_x=self.shake_y=0
        # Ambient
        for ap in self.ambient_particles:
            ap.update(dt)
            self.sparkline.update(dt,self.effective_cps())

        # Animated DNA
        diff=self.dna-self.display_dna;self.display_dna+=diff*min(1,dt*10)
        if abs(diff)<0.5:
            self.display_dna=self.dna
        # Auto-save
        self.autosave_timer+=dt
        if self.autosave_timer>=30:
            self.autosave_timer=0;self.save()
        # Boss timer
        if not self.boss:
            self.boss_timer-=dt
            if self.boss_timer<=0:
                self.boss=Boss(self.boss_tier,self.total_dna);self.boss_timer=random.uniform(90,180)
        else:self.boss.update(dt)
        # Orb spawning
        self.orb_timer+=dt
        if self.orb_timer>random.uniform(2,5):
            self.orb_timer=0;self.orbs.append(DNAOrb(self.total_dna))
        for orb in self.orbs:
            orb.update(dt)
            self.orbs=[o for o in self.orbs if o.alive]

        # Ability timers
        for i in range(len(ABILITIES)):
            if self.ability_actives[i]>0:
                self.ability_actives[i]=max(0,self.ability_actives[i]-dt)
            if self.ability_cooldowns[i]>0:
                self.ability_cooldowns[i]=max(0,self.ability_cooldowns[i]-dt)
                if not self.abilities_unlocked[i] and self.total_dna>=ABILITIES[i]["unlock_dna"]:
                    self.abilities_unlocked[i]=True
                    self.toasts.append(Toast(f"Ability Unlocked!",f"{ABILITIES[i]['name']} [{ABILITIES[i]['key']}]",ABILITIES[i]["color"]))
        # Mutation timer
        if self.active_mutation:
            self.mutation_timer-=dt
            if self.mutation_timer<=0:
                self.active_mutation=None
        else:
            self.mutation_event_timer-=dt
            if self.mutation_event_timer<=0:
                self._start_mutation();self.mutation_event_timer=random.uniform(60,120)

    def new_creature(self):
        self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),
            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed)

            self.renderer=CreatureRenderer(self.genome);self.seed_display=seed

            self.toasts.append(Toast("New Creature!",f"Seed: {seed}",CYAN))

            self._burst(self.creature_cx,self.creature_cy,40,[CYAN,GREEN,PINK])


    def draw(self,surface):
        mx,my=pygame.mouse.get_pos();evo_lv=self.genome.level(self.total_dna)
        # BG
        for y in range(HEIGHT):
            ratio=y/HEIGHT;ls=min(evo_lv*2,30)
            r=int((BG_TOP[0]+ls*0.3)*(1-ratio)+(BG_BOT[0]+ls*0.5)*ratio)
            g=int((BG_TOP[1]+ls*0.1)*(1-ratio)+(BG_BOT[1]+ls*0.2)*ratio)
            b=int(min(255,(BG_TOP[2]+ls*0.8)*(1-ratio)+(BG_BOT[2]+ls*0.6)*ratio))
            pygame.draw.line(surface,(min(255,r),min(255,g),min(255,b)),(0,y),(WIDTH,y))
        self.starfield.draw(surface,evo_lv,self.t)
        for ap in self.ambient_particles:
            ap.draw(surface,evo_lv)
        # Orbs (behind panels)
        for orb in self.orbs:
            orb.draw(surface)
            so=(int(self.shake_x),int(self.shake_y))

        # ── Left Panel ──
        pygame.draw.rect(surface,PANEL_BG,(15+so[0],15+so[1],620,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(15+so[0],15+so[1],620,750),2,border_radius=15)
        title=font_xl.render("Procedural Creature Clicker",True,CYAN)
        surface.blit(title,(325-title.get_width()//2+so[0],22+so[1]))
        name=self.genome.proc_name(self.total_dna);color=self.genome.body_color(self.total_dna,self.t)
        surface.blit(font_lg.render(name,True,color),(325-font_lg.size(name)[0]//2+so[0],62+so[1]))
        evo_display = evo_lv
        if self.active_mutation and self.active_mutation["mult_type"]=="evo":
            evo_display += self.active_mutation["mult_value"]
        stage_txt=font_sm.render(f"Evo Lv: {evo_display:.1f} | Prestige: {self.prestige_count} ({self.prestige_mult:.2f}x)",True,MUTED)
        surface.blit(stage_txt,(325-stage_txt.get_width()//2+so[0],90+so[1]))
        # Trait tags
        traits=[]
        gd=self.genome
        if gd.limb_count(self.total_dna)>0:
            traits.append(f"{gd.limb_count(self.total_dna)} {gd.limb_style}")
        if gd.has_wings(self.total_dna):
            traits.append(f"{gd.wing_style} wings")
        if gd.eye_count(self.total_dna)>2:
            traits.append(f"{gd.eye_count(self.total_dna)} {gd.eye_style}")
        if gd.has_horns(self.total_dna):
            traits.append(f"{gd.horn_count(self.total_dna)} {gd.horn_style}")
        if gd.tail_length(self.total_dna)>0:
            traits.append(f"{gd.tail_style} tail")
        if gd.has_pattern(self.total_dna):
            traits.append(gd.pattern_type)
        if gd.has_aura(self.total_dna):
            traits.append(f"{gd.aura_style} aura")
        if traits:
            tt=font_xs.render(" | ".join(traits[:6]),True,DIM);surface.blit(tt,(325-tt.get_width()//2+so[0],108+so[1]))
        # Mutation banner
        if self.active_mutation:
            mut=self.active_mutation;flash=(math.sin(self.t*6)+1)*0.5
            mc=tuple(int(min(255,c*(0.6+0.4*flash)))for c in mut["color"])
            mt=font_md.render(f"MUTATION: {mut['name']} ({self.mutation_timer:.0f}s)",True,mc)
            surface.blit(mt,(325-mt.get_width()//2+so[0],125+so[1]))
        # Boss
        if self.boss and self.boss.alive:
            self.boss.draw(surface,self.t)
        else:
            # Creature
            dist=math.sqrt((mx-self.creature_cx)**2+(my-self.creature_cy)**2)
            bsize=self.genome.body_size(self.total_dna)
            self.creature_hover=dist<bsize*1.5 and not self.show_traits and not self.show_bestiary and not self.show_stats and not self.show_settings and not self.show_achievements_panel
            self.renderer.draw(surface,self.creature_cx+so[0],self.creature_cy+so[1],self.total_dna,self.t,self.creature_hover)
            if self.creature_hover:
                hint=font_sm.render("Click me!",True,WHITE);surface.blit(hint,(self.creature_cx-hint.get_width()//2,int(self.creature_cy+bsize+15)))
        for p in self.particles:
            p.draw(surface)
        for ft in self.float_texts:
            ft.draw(surface)
        # DNA + Combo
        dna_txt=font_xl.render(f"{fmt(self.display_dna)}",True,GOLD);surface.blit(dna_txt,(325-dna_txt.get_width()//2,490))
        if self.combo>1:
            cc=ORANGE if self.combo<10 else RED if self.combo<30 else PURPLE
            ct=font_lg.render(f"COMBO x{self.combo}",True,cc);surface.blit(ct,(325-ct.get_width()//2,468))
            bw=min(200,200*(self.combo_timer/self.combo_decay))
            pygame.draw.rect(surface,DARK_PURPLE,(225,493,200,4),border_radius=2)
            if bw>0:
                pygame.draw.rect(surface,cc,(225,493,int(bw),4),border_radius=2)
        surface.blit(font_md.render("DNA Points",True,MUTED),(325-font_md.size("DNA Points")[0]//2,525))
        # Stats line
        sl=f"Click: {fmt(self.effective_click())} | CPS: {fmt(self.effective_cps())} | Crit: {self.effective_crit_chance()*100:.0f}% | Bosses: {self.bosses_defeated}"
        surface.blit(font_xs.render(sl,True,MUTED),(325-font_xs.size(sl)[0]//2,550))
        sl2=f"Total: {fmt(self.total_dna)} | Clicks: {self.total_clicks} | Orbs: {self.orbs_collected} | Mutations: {self.mutations_experienced}"
        surface.blit(font_xs.render(sl2,True,DIM),(325-font_xs.size(sl2)[0]//2,565))
        # Sparkline
        self.sparkline.draw(surface,195,585,260,32,CYAN)
        # Ability bar
        ab_y=625
        surface.blit(font_xs.render("Abilities:",True,MUTED),(30,ab_y+2))
        for i,ab in enumerate(ABILITIES):
            ax=110+i*120;aw=110;ah=36;ar=pygame.Rect(ax,ab_y,aw,ah)
            unlocked=self.abilities_unlocked[i]
            on=self.ability_actives[i]>0;cd=self.ability_cooldowns[i]>0
            if on:
                ac=(40,80,40);bc=GREEN
            elif cd:ac=(30,25,50);bc=DIM
            elif unlocked:ac=(35,50,90);bc=ab["color"]
            else:ac=(20,18,35);bc=(40,35,60)
            pygame.draw.rect(surface,ac,ar,border_radius=6);pygame.draw.rect(surface,bc,ar,1,border_radius=6)
            # Cooldown overlay
            if cd and unlocked:
                cdr=self.ability_cooldowns[i]/ab["cooldown"]
                ch=int(ah*cdr)
                if ch>0:
                    cs=pygame.Surface((aw,ch),pygame.SRCALPHA);cs.fill((0,0,0,100));surface.blit(cs,(ax,ab_y))
                    cd_txt=font_xxs.render(f"{self.ability_cooldowns[i]:.0f}s",True,WHITE);surface.blit(cd_txt,(ax+aw//2-cd_txt.get_width()//2,ab_y+ah//2-cd_txt.get_height()//2))

            elif on:
                on_txt=font_xxs.render(f"{self.ability_actives[i]:.1f}s",True,GREEN);surface.blit(on_txt,(ax+aw//2-on_txt.get_width()//2,ab_y+ah//2-on_txt.get_height()//2))
            tc=WHITE if unlocked else DIM
            nt=font_xs.render(f"[{ab['key']}] {ab['name']}",True,tc);surface.blit(nt,(ax+4,ab_y+3))
            dt_txt=font_xxs.render(ab["desc"] if unlocked else f"Unlock: {fmt(ab['unlock_dna'])} DNA",True,MUTED if unlocked else (50,45,80))
            surface.blit(dt_txt,(ax+4,ab_y+19))
        # Trait detail panel
        if self.show_traits:
            self._draw_trait_panel(surface,so)
        # Other panels
        if self.show_bestiary:
            self._draw_bestiary(surface,so)
        if self.show_stats:
            self._draw_stats(surface,so)
        if self.show_settings:
            self._draw_settings(surface,so)
        if self.show_achievements_panel:
            self._draw_achievements_panel(surface,so)
        # ── Right Panel: Shop ──
        pygame.draw.rect(surface,PANEL_BG,(650,15,435,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(650,15,435,750),2,border_radius=15)
        surface.blit(font_lg.render("Upgrades",True,CYAN),(867-font_lg.size("Upgrades")[0]//2,22))
        surface.blit(font_sm.render(f"DNA: {fmt(self.dna)}",True,GOLD),(665,52))
        # Buy amount
        surface.blit(font_xs.render("Buy:",True,MUTED),(830,55))
        for bi,bl in enumerate(BUY_LABELS):
            bx=865+bi*38;sel=bi==self.buy_amount_idx;bc=GREEN if sel else(40,35,80)
            pygame.draw.rect(surface,bc,(bx,52,34,16),border_radius=4)
            if sel:
                pygame.draw.rect(surface,WHITE,(bx,52,34,16),1,border_radius=4)
                surface.blit(font_xs.render(bl,True,WHITE if sel else DIM),(bx+17-font_xs.size(bl)[0]//2,53))

        # Upgrade list
        clip=pygame.Rect(655,74,425,500);surface.set_clip(clip);self.max_scroll=max(0,len(UPGRADES)*46-490)
        self.hovered_upgrade=-1
        for i,upg in enumerate(UPGRADES):
            tc,am=self.upgrade_cost(i);ca=self.dna>=tc and am>0;by=80+i*46-self.shop_scroll
            if 70<by<575:
                r=pygame.Rect(665,by,405,40);hov=r.collidepoint(mx,my)
                if hov:
                    self.hovered_upgrade=i
                    c=(40,35,90)if ca else(18,16,42)

                if ca and hov:
                    c=(55,48,110)
                    pygame.draw.rect(surface,c,r,border_radius=8);pygame.draw.rect(surface,GREEN if ca else DIM,r,1,border_radius=8)

                    key=upg.get("key","")

                if key:
                    surface.blit(font_xs.render(f"[{key}]",True,DIM),(r.x+5,r.y+4))
                    surface.blit(font_sm.render(f"{upg['name']} (x{self.upgrade_counts[i]})",True,WHITE if ca else DIM),(r.x+30,r.y+2))

                    surface.blit(font_xs.render(upg["desc"],True,MUTED if ca else(50,45,80)),(r.x+30,r.y+21))

                    cs=fmt(tc)

                if am>1:
                    cs+=f" (x{am})"
                    surface.blit(font_sm.render(cs,True,GREEN if ca else RED),(r.right-font_sm.size(cs)[0]-8,r.y+11))

        surface.set_clip(None)
        if self.max_scroll>0:
            sr=self.shop_scroll/self.max_scroll;bh=max(20,int(500*(500/(500+self.max_scroll))))
            pygame.draw.rect(surface,DIM,(1072,82+int(sr*(490-bh)),4,bh),border_radius=2)
        # Progress
        py_=590;next_m=None
        for m in self.milestones:
            if self.total_dna<m:
                next_m=m;break
        if not next_m:
            next_m=self.milestones[-1]*10
            pygame.draw.rect(surface,DARK_PURPLE,(665,py_,410,10),border_radius=5)

            prev_m=self.milestones[max(0,self.milestones.index(next_m)-1)]if next_m in self.milestones else 0

            prog=min(1,max(0,(self.total_dna-prev_m)/(next_m-prev_m)))if next_m>prev_m else 1

            fw=int(410*prog)

            if fw>0:
                for px in range(fw):
                    ratio=px/410;c=(int(60+120*ratio),int(40+180*ratio),int(180+75*ratio))
                pygame.draw.line(surface,c,(665+px,py_),(665+px,py_+9))

        pygame.draw.rect(surface,PANEL_BORDER,(665,py_,410,10),1,border_radius=5)
        surface.blit(font_xxs.render(f"Next: {fmt(next_m)} ({prog*100:.1f}%)",True,MUTED),(667,py_+12))
        # Buttons
        can_prestige=self.total_dna>=1e6
        pb=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige if can_prestige else 0
        pr=pygame.Rect(665,620,130,28);ph=pr.collidepoint(mx,my)
        pygame.draw.rect(surface,(150,30,30)if can_prestige else DARK_RED,pr,border_radius=5)
        pygame.draw.rect(surface,RED if can_prestige else DIM,pr,1,border_radius=5)
        surface.blit(font_sm.render(f"Prestige [P]"if can_prestige else"Prestige (1M)",True,WHITE if can_prestige else DIM),
            (pr.centerx-font_sm.size(f"Prestige [P] +{pb:.1f}x"if can_prestige else"Prestige (1M)")[0]//2,pr.centery-7))
        nr=pygame.Rect(800,620,130,28)
        pygame.draw.rect(surface,(50,80,150)if nr.collidepoint(mx,my)else(35,55,110),nr,border_radius=5)
        pygame.draw.rect(surface,CYAN,nr,1,border_radius=5)
        surface.blit(font_sm.render("New [N]",True,WHITE),(nr.centerx-25,nr.centery-7))
        br=pygame.Rect(935,620,140,28)
        pygame.draw.rect(surface,(50,50,100)if br.collidepoint(mx,my)else(30,28,65),br,border_radius=5)
        pygame.draw.rect(surface,PANEL_BORDER,br,1,border_radius=5)
        surface.blit(font_sm.render("Bestiary [B]",True,WHITE),(br.centerx-38,br.centery-7))
        # Bottom bar
        bb=pygame.Rect(665,660,410,24)
        pygame.draw.rect(surface,(30,28,65),bb,border_radius=4);pygame.draw.rect(surface,PANEL_BORDER,bb,1,border_radius=4)
        bt="[T]raits [D]stats [A]achieve [M]settings [S]save [Tab]buy"
        surface.blit(font_xxs.render(bt,True,MUTED),(bb.centerx-font_xxs.size(bt)[0]//2,bb.centery-5))
        # Bottom info
        info=f"Achievements: {len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)} | Time: {int(self.play_time//3600)}h{int(self.play_time%3600//60)}m | Autosave 30s"
        surface.blit(font_xxs.render(info,True,DIM),(325-font_xxs.size(info)[0]//2,HEIGHT-15))
        # Tooltip
        if self.hovered_upgrade>=0:
            self._draw_tooltip(surface,self.hovered_upgrade,mx,my)
        # Toasts
        for i,toast in enumerate(self.toasts):
            toast.draw(surface,i)

    def _draw_trait_panel(self,s,so):
        px,py,pw,ph=25,150,610,280
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,230),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*PANEL_BORDER,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        gd=self.genome;td=self.total_dna;rows=[
            ("Body Size",f"{gd.body_size(td):.1f}"),("Segments",f"{gd.body_segments(td)}"),
            ("Eyes",f"{gd.eye_count(td)} ({gd.eye_style})"),("Limbs",f"{gd.limb_count(td)} ({gd.limb_style})"),
            ("Wings",f"{gd.wing_size(td):.0f} ({gd.wing_style})"if gd.has_wings(td)else"None"),
            ("Tail",f"{gd.tail_length(td):.0f} ({gd.tail_style})"),
            ("Horns",f"{gd.horn_count(td)} ({gd.horn_style})"if gd.has_horns(td)else"None"),
            ("Pattern",f"{gd.pattern_type}"if gd.has_pattern(td)else"None"),
            ("Aura",f"{gd.aura_style}"if gd.has_aura(td)else"None"),
            ("Click Mult",f"{gd.click_multiplier(td):.2f}x"),("CPS Mult",f"{gd.cps_multiplier(td):.2f}x"),
            ("Prestige",f"{self.prestige_mult:.2f}x"),("Ach Bonus Click",f"+{self.ach_bonus_click}"),
            ("Ach Bonus CPS",f"+{self.ach_bonus_cps}"),("Crit Chance",f"{self.effective_crit_chance()*100:.1f}%"),
            ("Crit Mult",f"{self.effective_crit_mult():.1f}x"),
        ]
        cols=3;cw=pw//cols
        for idx,(label,val)in enumerate(rows):
            col=idx%cols;row=idx//cols;x=px+10+col*cw+so[0];y=py+8+row*17+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+font_xs.size(label+":")[0]+4,y))

    def _draw_bestiary(self,s,so):
        px,py,pw,ph=50,80,560,580
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*CYAN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Bestiary",True,CYAN),(px+pw//2-font_lg.size("Bestiary")[0]//2+so[0],py+10+so[1]))
        if not self.bestiary:
            surface.blit(font_sm.render("No creatures yet! Prestige or press N to add entries.",True,MUTED),(px+20+so[0],py+50+so[1]))
        else:
            for i,entry in enumerate(sorted(self.bestiary,key=lambda e:
                e.get("total_dna",0),reverse=True)):
                if i>15:
                    break;ey=py+45+i*32+so[1];ex=px+15+so[0]
                # Mini creature name
                surface.blit(font_sm.render(f"{entry.get('name','?')}",True,GOLD),(ex,ey))
                tr=entry.get("traits",{})
                parts=[f"{tr.get('limbs','?')} limbs",f"{tr.get('eyes','?')} eyes",f"{tr.get('tail','?')} tail",f"Lv {tr.get('level','?')}"]
                surface.blit(font_xs.render(" | ".join(parts),True,MUTED),(ex,ey+15))
                surface.blit(font_xs.render(f"DNA: {fmt(entry.get('total_dna',0))} | Prestige #{entry.get('prestige','?')}",True,DIM),(ex+350,ey+7))

    def _draw_stats(self,s,so):
        px,py,pw,ph=50,80,560,500
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GREEN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Statistics",True,GREEN),(px+pw//2-font_lg.size("Statistics")[0]//2+so[0],py+10+so[1]))
        hrs=int(self.play_time//3600);mins=int(self.play_time%3600//60);secs=int(self.play_time%60)
        cps_v=self.effective_cps();click_v=self.effective_click()
        rows=[
            ("Play Time",f"{hrs}h {mins}m {secs}s"),("Total DNA Earned",fmt(self.total_dna)),
            ("Current DNA",fmt(self.dna)),("Total Clicks",f"{self.total_clicks:,}"),
            ("Click Rate",f"{self.total_clicks/max(1,self.play_time):.1f}/s" if self.play_time>1 else "N/A"),
            ("Per Click",fmt(click_v)),("Per Second",fmt(cps_v)),
            ("Total Crits",f"{self.total_crits:,} ({self.total_crits/max(1,self.total_clicks)*100:.1f}%)" if self.total_clicks>0 else "0"),
            ("Max Combo",f"{self.max_combo}x"),("Upgrades Bought",f"{self.total_upgrades_bought:,}"),
            ("Prestige Count",f"{self.prestige_count}"),("Prestige Mult",f"{self.prestige_mult:.2f}x"),
            ("Bosses Defeated",f"{self.bosses_defeated}"),("Boss Tier",f"{self.boss_tier}"),
            ("Orbs Collected",f"{self.orbs_collected}"),("Mutations",f"{self.mutations_experienced}"),
            ("Achievement Bonus Click",f"+{self.ach_bonus_click}"),("Achievement Bonus CPS",f"+{self.ach_bonus_cps}"),
            ("Achievement Bonus Crit",f"+{self.ach_bonus_crit*100:.1f}%"),
            ("Creature Seed",self.seed_display),
        ]
        for idx,(label,val)in enumerate(rows):
            col=idx%2;row=idx//2;x=px+15+col*280+so[0];y=py+42+row*21+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+140,y))

    def _draw_settings(self,s,so):
        px,py,pw,ph=200,100,350,350
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*ORANGE,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Settings",True,ORANGE),(px+pw//2-font_lg.size("Settings")[0]//2+so[0],py+10+so[1]))
        mx,my=pygame.mouse.get_pos()
        # Sound toggle
        sr=pygame.Rect(px+20+so[0],py+50+so[1],150,30);sh=sr.collidepoint(mx,my)
        pygame.draw.rect(surface,(40,80,40)if self.sound_on else(80,30,30)if sh else DARK_RED,sr,border_radius=5)
        surface.blit(font_sm.render(f"Sound: {'ON' if self.sound_on else 'OFF'}",True,WHITE),(sr.x+10,sr.y+7))
        # Particle quality
        for qi,ql in enumerate(["Low","Med","High"]):
            qr=pygame.Rect(px+20+qi*105+so[0],py+95+so[1],95,30)
            qs=qi==self.particle_quality;qh=qr.collidepoint(mx,my)
            pygame.draw.rect(surface,(50,50,100)if(qs or qh)else(30,28,60),qr,border_radius=5)
            if qs:
                pygame.draw.rect(surface,WHITE,qr,1,border_radius=5)
                surface.blit(font_sm.render(f"Particles: {ql}",True,WHITE if qs else MUTED),(qr.x+5,qr.y+7))

        # Reset button
        rr=pygame.Rect(px+20+so[0],py+145+so[1],150,30)
        pygame.draw.rect(surface,(120,30,30)if rr.collidepoint(mx,my)else DARK_RED,rr,border_radius=5)
        surface.blit(font_sm.render("Reset Save [X]",True,RED if rr.collidepoint(mx,my)else DIM),(rr.x+10,rr.y+7))
        # Info
        lines=["Controls:","[Q/W/E/R] Activate abilities","[1-0] Buy upgrades",
               "[P] Prestige  [N] New creature","[B] Bestiary  [T] Traits",
               "[D] Stats  [A] Achievements","[M] Settings  [S] Save",
               "[Tab] Cycle buy amount","[X in Settings] Reset save","[ESC] Quit"]
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,MUTED if i>0 else WHITE),(px+20+so[0],py+190+i*16+so[1]))

    def _draw_achievements_panel(self,s,so):
        px,py,pw,ph=30,50,600,620
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GOLD,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})",True,GOLD),
            (px+pw//2-font_lg.size(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})")[0]//2+so[0],py+8+so[1]))
        clip=pygame.Rect(px+5,py+35,pw-10,ph-40);surface.set_clip(clip)
        for i,ach in enumerate(ACHIEVEMENTS):
            unlocked=ach["id"]in self.achievements_unlocked;ay=py+38+i*22
            if ay<py+30 or ay>py+ph-10:
                continue
                c=GOLD if unlocked else(40,35,60)

                icon="*"if unlocked else "o"

                surface.blit(font_xs.render(f"[{icon}] {ach['name']}",True,WHITE if unlocked else DIM),(px+15+so[0],ay+so[1]))

                surface.blit(font_xxs.render(f"{ach['desc']} | Reward: +{ach['reward']} {ach['reward_type']}",True,MUTED if unlocked else(50,45,70)),(px+200+so[0],ay+2+so[1]))

        surface.set_clip(None)

    def _draw_tooltip(self,surface,idx,mx,my):
        upg=UPGRADES[idx];tc,am=self.upgrade_cost(idx);lines=[upg["name"],upg["desc"],
            f"Type: {upg['type'].upper()}",f"Cost mult: x{upg['cost_mult']}/lv",
            f"Owned: {self.upgrade_counts[idx]}",f"Cost ({am}): {fmt(tc)}"]
        if upg["type"]=="click":
            nv=self.effective_click()+upg["value"]*am*self.genome.click_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"Click after: {fmt(nv)}")
        else:
            nv=self.effective_cps()+upg["value"]*am*self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"CPS after: {fmt(nv)}")
        tw=max(font_xs.size(l)[0]for l in lines)+16;th=len(lines)*15+10
        tx=min(mx+15,WIDTH-tw-5);ty=min(my+15,HEIGHT-th-5)
        tip=pygame.Surface((tw,th),pygame.SRCALPHA);pygame.draw.rect(tip,(10,8,30,230),(0,0,tw,th),border_radius=6)
        pygame.draw.rect(tip,(*PANEL_BORDER,200),(0,0,tw,th),1,border_radius=6);surface.blit(tip,(tx,ty))
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,GOLD if i==0 else MUTED),(tx+8,ty+5+i*15))


def fmt(n):
    if n<0:
        return"-"+fmt(-n)
    if n<1000:
        return f"{n:.1f}"if isinstance(n,float)and n!=int(n)else str(int(n))
        sfx=["","K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc"];t=0

    while n>=1000 and t<len(sfx)-1:
        n/=1000;t+=1
        return f"{n:.0f}{sfx[t]}"if n>=100 else f"{n:.1f}{sfx[t]}"if n>=10 else f"{n:.2f}{sfx[t]}"



# ─────────────── MAIN ───────────────
def main():
    game=Game();running=True
    while running:
        dt=clock.tick(60)/1000;dt=min(dt,0.05);mx,my=pygame.mouse.get_pos()
        close_panels=lambda:any([game.show_traits,game.show_bestiary,game.show_stats,game.show_settings,game.show_achievements_panel])
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                game.save();running=False
            elif event.type==pygame.KEYDOWN:
                k=event.key
                if k==pygame.K_ESCAPE:
                    if close_panels():
                        game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                    else:game.save();running=False
                elif k==pygame.K_s:game.save();game.toasts.append(Toast("Saved!","Game saved",GREEN))
                elif k==pygame.K_p:game.prestige()
                elif k==pygame.K_n:game.new_creature()
                elif k==pygame.K_t:game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_b:game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_d:game.show_stats=not game.show_stats;game.show_traits=game.show_bestiary=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_a:game.show_achievements_panel=not game.show_achievements_panel;game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=False
                elif k==pygame.K_m:game.show_settings=not game.show_settings;game.show_traits=game.show_bestiary=game.show_stats=game.show_achievements_panel=False
                elif k==pygame.K_TAB:game.buy_amount_idx=(game.buy_amount_idx+1)%len(BUY_AMOUNTS)
                elif k==pygame.K_q:game.activate_ability(0)
                elif k==pygame.K_w:game.activate_ability(1)
                elif k==pygame.K_e:game.activate_ability(2)
                elif k==pygame.K_r:game.activate_ability(3)
                km={pygame.K_1:0,pygame.K_2:1,pygame.K_3:2,pygame.K_4:3,pygame.K_5:4,pygame.K_6:5,pygame.K_7:6,pygame.K_8:7,pygame.K_9:8,pygame.K_0:9}
                if k in km:
                    game.buy_upgrade(km[k])
            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==1:
                    # Check orbs first
                    for orb in game.orbs:
                        if orb.alive and orb.hit_test(mx,my):
                            game.collect_orb(orb,mx,my);break
                    else:
                        if game.creature_hover and not close_panels():
                            game.click_creature(mx,my)
                            for i in range(len(UPGRADES)):
                                by=80+i*46-game.shop_scroll;r=pygame.Rect(665,by,405,40)
                                if r.collidepoint(mx,my):
                                    game.buy_upgrade(i)
                        for bi in range(len(BUY_LABELS)):
                            if pygame.Rect(865+bi*38,52,34,16).collidepoint(mx,my):
                                game.buy_amount_idx=bi
                        if pygame.Rect(665,620,130,28).collidepoint(mx,my):
                            game.prestige()
                        if pygame.Rect(800,620,130,28).collidepoint(mx,my):
                            game.new_creature()
                        if pygame.Rect(935,620,140,28).collidepoint(mx,my):
                            game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        if pygame.Rect(665,660,410,24).collidepoint(mx,my):
                            game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        # Settings panel clicks
                        if game.show_settings:
                            spx,spy=200+int(game.shake_x),100+int(game.shake_y)
                            if pygame.Rect(spx+20,spy+50,150,30).collidepoint(mx,my):
                                game.sound_on=not game.sound_on
                                for qi in range(3):
for                                f pygame.Rect(spx+20+qi*105,spy+95,95,30).collidepoint(mx,my):

                                    game.particle_quality=qi
                            if pygame.Rect(spx+20,spy+145,150,30).collidepoint(mx,my):
                                if os.path.exists(SAVE_FILE):
                                    os.remove(SAVE_FILE)
                                    game.toasts.append(Toast("Reset!","Save file deleted. Restart to start fresh.",RED))

                        # Ability bar clicks
                        for ai in range(len(ABILITIES)):
                            ar=pygame.Rect(110+ai*120,625,110,36)
                            if ar.collidepoint(mx,my):
                                game.activate_ability(ai)
                elif event.button==4:game.shop_scroll=max(0,game.shop_scroll-40)
                elif event.button==5:game.shop_scroll=min(game.max_scroll,game.shop_scroll+40)
        # Ambient particles
        if game.effective_cps()>0 and random.random()<dt*2*game.particle_quality:
            a=random.uniform(0,2*math.pi);d=random.uniform(40,80)
            c=game.genome.accent_color(game.total_dna,game.t)
            game.particles.append(Particle(game.creature_cx+math.cos(a)*d,game.creature_cy+math.sin(a)*d*0.7,c,random.uniform(-15,15),random.uniform(-35,-10),0.5,random.randint(2,4)))
        game.update(dt);game.draw(screen);pygame.display.flip()
    pygame.quit();sys.exit()

if __name__=="__main__":

    main()


qi in range(3):
for                                f pygame.Rect(spx+20+qi*105,spy+95,95,30).collidepoint(mx,my):

                                    game.particle_quality=qi
                            if pygame.Rect(spx+20,spy+145,150,30).collidepoint(mx,my):
                                if os.path.exists(SAVE_FILE):
                                    os.remove(SAVE_FILE)
                                    game.toasts.append(Toast("Reset!","Save file deleted. Restart to start fresh.",RED))

                        # Ability bar clicks
                        for ai in range(len(ABILITIES)):
                            ar=pygame.Rect(110+ai*120,625,110,36)
                            if ar.collidepoint(mx,my):
                                game.activate_ability(ai)
                elif event.button==4:game.shop_scroll=max(0,game.shop_scroll-40)
                elif event.button==5:game.shop_scroll=min(game.max_scroll,game.shop_scroll+40)
        # Ambient particles
        if game.effective_cps()>0 and random.random()<dt*2*game.particle_quality:
            a=random.uniform(0,2*math.pi);d=random.uniform(40,80)
            c=game.genome.accent_color(game.total_dna,game.t)
            game.particles.append(Particle(game.creature_cx+math.cos(a)*d,game.creature_cy+math.sin(a)*d*0.7,c,random.uniform(-15,15),random.uniform(-35,-10),0.5,random.randint(2,4)))
        game.update(dt);game.draw(screen);pygame.display.flip()
    pygame.quit();sys.exit()

if __name__=="__main__":

    main()

/usr/bin/env python3
"""
Procedural Creature Clicker v3
Boss fights, falling orbs, active abilities, mutations, bestiary, stats, settings, and more!
"""

import pygame, sys, math, random, hashlib, colorsys, json, os, time, array

# ─────────────── INIT ───────────────
pygame.init()
SOUND_ENABLED = False
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    SOUND_ENABLED = True
except Exception:
    pass
WIDTH, HEIGHT = 1100, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Procedural Creature Clicker v3")
clock = pygame.time.Clock()
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "creature_save.json")

# ─────────────── COLORS ───────────────
BG_TOP = (12, 10, 35); BG_BOT = (40, 35, 85); PANEL_BG = (22, 20, 55)
PANEL_BORDER = (75, 65, 150); WHITE = (255, 255, 255); GOLD = (255, 215, 0)
CYAN = (0, 230, 255); GREEN = (80, 255, 120); RED = (255, 80, 80)
ORANGE = (255, 160, 50); PURPLE = (180, 100, 255); PINK = (255, 120, 200)
DARK_PURPLE = (55, 38, 110); MUTED = (155, 150, 195); DIM = (95, 90, 135)
DARK_RED = (120, 20, 20); YELLOW = (255, 255, 80); DARK_GREEN = (20, 80, 30)

# ─────────────── FONTS ───────────────
font_xl = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 36, bold=True)
font_lg = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 24, bold=True)
font_md = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 18)
font_sm = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 14)
font_xs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 11)
font_xxs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 9)

# ─────────────── PROCEDURAL SOUND ───────────────
def make_sound(freq=440, duration=0.08, volume=0.12, wave="sine"):
    try:
        sr = 22050; ns = int(sr * duration); buf = array.array('h')
        for i in range(ns):
            t = i / sr; env = min(1.0, min(i/(sr*0.005), (ns-i)/(sr*0.01)))
            v = math.sin(2*math.pi*freq*t) if wave=="sine" else (1.0 if math.sin(2*math.pi*freq*t)>0 else -1.0) if wave=="square" else random.uniform(-1,1)
            buf.append(max(-32767, min(32767, int(v*volume*env*32767))))
        return pygame.mixer.Sound(buffer=buf)
    except: return None

snd_click = make_sound(520,0.06,0.10,"sine"); snd_crit = make_sound(880,0.15,0.15,"square")
snd_buy = make_sound(660,0.08,0.08,"sine"); snd_achieve = make_sound(1047,0.25,0.12,"sine")
snd_combo = make_sound(700,0.05,0.06,"sine"); snd_prestige = make_sound(440,0.5,0.15,"sine")
snd_orb = make_sound(1200,0.1,0.08,"sine"); snd_ability = make_sound(660,0.3,0.12,"sine")
snd_boss_hit = make_sound(300,0.1,0.10,"square"); snd_boss_die = make_sound(200,0.4,0.15,"noise")
snd_mutation = make_sound(500,0.2,0.10,"sine")

def play(snd):
    if snd:
        try: snd.play()
        except: pass

# ─────────────── SEEDED RNG ───────────────
class SeededRNG:
    def __init__(self, seed_str="default"):
        h = hashlib.sha256(seed_str.encode()).digest()
        self.state = int.from_bytes(h[:8], 'big'); self.pool = []; self._refill()
    def _refill(self):
        for _ in range(256):
            self.state = (self.state*6364136223846793005+1442695040888963407)&0xFFFFFFFFFFFFFFFF
            self.pool.append(((self.state>>16)&0xFFFFFFFF)/0xFFFFFFFF)
    def next(self):
        if not self.pool:
            self._refill()
            return self.pool.pop(0)

    def rand(self,lo,hi): return lo+self.next()*(hi-lo)
    def randint(self,lo,hi): return int(self.next()*(hi-lo+1))+lo
    def choice(self,lst): return lst[self.randint(0,len(lst)-1)]

# ─────────────── GENOME ───────────────
class Genome:
    def __init__(self, seed="creature_1"):
        self.seed=seed; self.rng=SeededRNG(seed)
        self.hue_offset=self.rng.rand(0,1); self.hue_speed=self.rng.rand(0.02,0.08)
        self.body_width_ratio=self.rng.rand(0.85,1.15)
        self.limb_style=self.rng.choice(["stubby","spindly","tentacle","crab"])
        self.wing_style=self.rng.choice(["feathered","bat","crystal","insect"])
        self.tail_style=self.rng.choice(["curved","spiked","forked","flame","tentacle"])
        self.eye_style=self.rng.choice(["round","slit","compound","cyclops"])
        self.pattern_type=self.rng.choice(["spots","stripes","rings","scales","none"])
        self.horn_style=self.rng.choice(["pointed","curved","crystal","antler"])
        self.mouth_style=self.rng.choice(["smile","teeth","beak","tentacles","lamprey"])
        self.aura_style=self.rng.choice(["glow","sparks","rings","dna_helix","constellation"])
        self.ear_type=self.rng.choice(["none","pointed","frilled","antenna"])
        self.leg_count_bias=self.rng.choice([2,4,6,8])
    def level(self,td):
        return 0 if td<=0 else math.log10(td+1)*2.5
    def body_size(self,td): return 30+min(self.level(td),12)*4.2
    def body_segments(self,td): return 1+int(min(self.level(td),10)/2.5)
    def body_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+lv*self.hue_speed+t*0.02)%1.0
        sat=0.5+min(lv,8)*0.05; val=0.6+min(lv,10)*0.03
        r,g,b=colorsys.hsv_to_rgb(hue,min(sat,0.95),min(val,0.95))
        return(int(r*255),int(g*255),int(b*255))
    def accent_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+0.4+lv*self.hue_speed*0.7+t*0.015)%1.0
        r,g,b=colorsys.hsv_to_rgb(hue,0.7,0.8); return(int(r*255),int(g*255),int(b*255))
    def eye_count(self,td): return 1 if self.eye_style=="cyclops" else min(2+int(self.level(td)/3),8)
    def eye_size(self,td): return 5+min(self.level(td),8)*1.2
    def limb_count(self,td):
        lv=self.level(td); return 0 if lv<1.5 else min(self.leg_count_bias,int(lv/1.5)*2)
    def limb_length(self,td): return min(self.level(td),8)*6
    def has_wings(self,td): return self.level(td)>=4.0
    def wing_size(self,td): return 0 if not self.has_wings(td) else min((self.level(td)-4.0)*12,80)
    def tail_length(self,td):
        lv=self.level(td); return 0 if lv<1.0 else min((lv-1.0)*15,120)
    def spike_count(self,td): return int(min(self.level(td),10)*0.8)
    def spike_size(self,td): lv=self.level(td); return 0 if lv<2 else min((lv-2)*3,25)
    def has_pattern(self,td): return self.level(td)>=3.0 and self.pattern_type!="none"
    def pattern_opacity(self,td): return 0 if not self.has_pattern(td) else min((self.level(td)-3.0)/3.0,1.0)
    def has_aura(self,td): return self.level(td)>=5.5
    def aura_intensity(self,td): return 0 if not self.has_aura(td) else min((self.level(td)-5.5)/4.0,1.0)
    def has_horns(self,td): return self.level(td)>=3.5
    def horn_count(self,td): return 0 if not self.has_horns(td) else min(int((self.level(td)-3.5)*1.5)+1,6)
    def horn_size(self,td): return 0 if not self.has_horns(td) else min((self.level(td)-3.5)*5,35)
    def mouth_complexity(self,td): return min(self.level(td)/8.0,1.0)
    def has_ears(self,td): return self.ear_type!="none" and self.level(td)>=2.0
    def ear_size(self,td): return 0 if not self.has_ears(td) else min((self.level(td)-2.0)*5,30)
    def bioluminescence(self,td): return min(self.level(td)/12.0,1.0)
    def proc_name(self,td):
        lv=self.level(td)
        pf=["Proto","Nano","Micro","Alpha","Beta","Gamma","Mega","Giga","Ultra","Hyper","Nova","Cosmic","Elder","Ancient","Omega"]
        bd=["Spore","Cell","Blob","Flop","Wurm","Crawler","Slinker","Lurker","Stalker","Drake","Wyrm","Serpent","Leviathan","Titan","Colossus","Behemoth"]
        sf=["ling","ite","us","ax","on","ix","ar","oth","ius","os","ux","ath","eon","ion","ium","or"]
        return f"{pf[min(int(lv/1.2),len(pf)-1)]}{bd[min(int(lv/1.0),len(bd)-1)]}{sf[min(int(lv/2.0),len(sf)-1)]}"
    def click_multiplier(self,td): return 1+self.level(td)*0.4
    def cps_multiplier(self,td): return 1+self.level(td)*0.3
    def to_dict(self):
        return {k:getattr(self,k) for k in ["seed","hue_offset","hue_speed","body_width_ratio",
            "limb_style","wing_style","tail_style","eye_style","pattern_type","horn_style",
            "mouth_style","aura_style","ear_type","leg_count_bias"]}
    @classmethod
    def from_dict(cls,d):
        g=cls.__new__(cls); g.seed=d["seed"]; g.rng=SeededRNG(g.seed)
        for k in ["hue_offset","hue_speed","body_width_ratio","limb_style","wing_style","tail_style",
                   "eye_style","pattern_type","horn_style","mouth_style","aura_style","ear_type","leg_count_bias"]:
            setattr(g,k,d[k])
        return g
Genome.has_wings_at_level=lambda s,lv:lv>=4.0; Genome.has_horns_at_level=lambda s,lv:lv>=3.5
Genome.has_aura_at_level=lambda s,lv:lv>=5.5; Genome.has_pattern_at_level=lambda s,lv:lv>=3.0

# ─────────────── ACHIEVEMENTS (with rewards) ───────────────
ACHIEVEMENTS = [
    {"id":"first_click","name":"First Contact","desc":"Click the creature","reward_type":"click","reward":1},
    {"id":"click_100","name":"Clicker","desc":"Click 100 times","reward_type":"click","reward":2},
    {"id":"click_1k","name":"Click Master","desc":"Click 1,000 times","reward_type":"click","reward":5},
    {"id":"click_10k","name":"Click Legend","desc":"Click 10,000 times","reward_type":"click","reward":20},
    {"id":"dna_100","name":"DNA Collector","desc":"Earn 100 total DNA","reward_type":"cps","reward":1},
    {"id":"dna_10k","name":"Gene Hoarder","desc":"Earn 10K total DNA","reward_type":"cps","reward":5},
    {"id":"dna_1m","name":"Biotech Baron","desc":"Earn 1M total DNA","reward_type":"click","reward":50},
    {"id":"dna_1b","name":"Genome God","desc":"Earn 1B total DNA","reward_type":"cps","reward":200},
    {"id":"dna_1t","name":"Singularity","desc":"Earn 1T total DNA","reward_type":"click","reward":5000},
    {"id":"combo_5","name":"Combo Starter","desc":"Reach 5x combo","reward_type":"crit_chance","reward":0.01},
    {"id":"combo_20","name":"Combo Frenzy","desc":"Reach 20x combo","reward_type":"crit_chance","reward":0.02},
    {"id":"combo_50","name":"Combo Madness","desc":"Reach 50x combo","reward_type":"crit_mult","reward":1},
    {"id":"crit_first","name":"Lucky Strike","desc":"First critical hit","reward_type":"click","reward":3},
    {"id":"crit_10","name":"Critical Mass","desc":"10 critical hits","reward_type":"crit_chance","reward":0.01},
    {"id":"upgrade_first","name":"Investor","desc":"First upgrade","reward_type":"cps","reward":2},
    {"id":"upgrade_50","name":"Hoarder","desc":"50 total upgrades","reward_type":"cps","reward":20},
    {"id":"prestige_1","name":"Rebirth","desc":"First prestige","reward_type":"click","reward":100},
    {"id":"prestige_5","name":"Transcendence","desc":"Prestige 5 times","reward_type":"prestige_bonus","reward":0.5},
    {"id":"level_5","name":"Evolved","desc":"Reach evo level 5","reward_type":"cps","reward":10},
    {"id":"level_10","name":"Advanced","desc":"Reach evo level 10","reward_type":"click","reward":200},
    {"id":"level_15","name":"Apex","desc":"Reach evo level 15","reward_type":"cps","reward":500},
    {"id":"cps_100","name":"Automation","desc":"Reach 100 DNA/sec","reward_type":"cps","reward":25},
    {"id":"cps_10k","name":"Factory","desc":"Reach 10K DNA/sec","reward_type":"click","reward":500},
    {"id":"boss_1","name":"Boss Slayer","desc":"Defeat first boss","reward_type":"click","reward":50},
    {"id":"boss_10","name":"Boss Hunter","desc":"Defeat 10 bosses","reward_type":"crit_chance","reward":0.03},
    {"id":"orb_50","name":"Orb Catcher","desc":"Collect 50 orbs","reward_type":"cps","reward":15},
    {"id":"mutation_5","name":"Mutant","desc":"Experience 5 mutations","reward_type":"click","reward":30},
]

# ─────────────── ACTIVE ABILITIES ───────────────
ABILITIES = [
    {"id":"storm","name":"DNA Storm","key":"Q","desc":"10x click for 5s","duration":5,"cooldown":30,"unlock_dna":500,"color":CYAN},
    {"id":"warp","name":"Time Warp","key":"W","desc":"10x CPS for 8s","duration":8,"cooldown":45,"unlock_dna":5000,"color":PURPLE},
    {"id":"surge","name":"Crit Surge","key":"E","desc":"100% crit for 6s","duration":6,"cooldown":35,"unlock_dna":50000,"color":RED},
    {"id":"frenzy","name":"Frenzy","key":"R","desc":"No combo decay 10s","duration":10,"cooldown":40,"unlock_dna":500000,"color":GREEN},
]

# ─────────────── MUTATION EVENTS ───────────────
MUTATIONS = [
    {"id":"dna_frenzy","name":"DNA Frenzy","desc":"2x all income!","mult_type":"all","mult_value":2.0,"duration":30,"color":GOLD},
    {"id":"golden_touch","name":"Golden Touch","desc":"3x click power!","mult_type":"click","mult_value":3.0,"duration":25,"color":YELLOW},
    {"id":"slow_meta","name":"Slow Metabolism","desc":"0.5x CPS...","mult_type":"cps","mult_value":0.5,"duration":20,"color":RED},
    {"id":"lucky_stars","name":"Lucky Stars","desc":"25% crit chance!","mult_type":"crit","mult_value":25.0,"duration":20,"color":ORANGE},
    {"id":"evolve_burst","name":"Evolution Burst","desc":"Visual evolution +3!","mult_type":"evo","mult_value":3.0,"duration":35,"color":PINK},
    {"id":"mega_combo","name":"Mega Combo","desc":"Combo starts at 10x!","mult_type":"combo","mult_value":10.0,"duration":15,"color":CYAN},
]

# ─────────────── BOSS DATA ───────────────
BOSS_NAMES = ["Alpha Slime","Crystal Golem","Shadow Wraith","Void Serpent","Storm Titan","Chaos Beast","Dimensional Eye","Cosmic Horror"]
BOSS_COLORS = [(100,200,100),(150,180,255),(120,50,180),(80,0,120),(200,200,50),(200,50,50),(200,100,255),(100,0,200)]

# ─────────────── BACKGROUND ───────────────
class Starfield:
    def __init__(self):
        self.stars=[{"x":random.uniform(0,WIDTH),"y":random.uniform(0,HEIGHT),
            "b":random.uniform(0.2,1),"s":random.uniform(1,4),"sz":random.uniform(0.5,2.5),"al":random.uniform(0,8)} for _ in range(200)]
    def draw(self,surf,lv,t):
        for s in self.stars:
            if lv<s["al"]:
                continue
                a=min(1,(lv-s["al"])*0.5); tw=(math.sin(t*s["s"]+s["x"])+1)*0.5

                br=s["b"]*a*(0.4+0.6*tw); c=int(255*br); sz=max(1,int(s["sz"]*(0.5+a*0.5)))

            if sz<=1:
                surf.set_at((int(s["x"])%WIDTH,int(s["y"])%HEIGHT),(c,c,min(255,int(c*1.1))))
            else: pygame.draw.circle(surf,(c,c,min(255,int(c*1.1))),(int(s["x"])%WIDTH,int(s["y"])%HEIGHT),sz)

class AmbientParticle:
    def __init__(self): self.reset(); self.y=random.uniform(0,HEIGHT)
    def reset(self):
        self.x=random.uniform(0,WIDTH); self.y=-5; self.vy=random.uniform(10,30)
        self.vx=random.uniform(-8,8); self.sz=random.uniform(1,3); self.a=random.uniform(0.1,0.4)
        self.color=random.choice([(100,200,255),(150,100,255),(100,255,150)])
    def update(self,dt):
        self.x+=self.vx*dt; self.y+=self.vy*dt
        if self.y>HEIGHT+10:
            self.reset()
    def draw(self,surf,lv):
        if lv<2:
            return; a=min(1,(lv-2)*0.2)*self.a; c=tuple(int(v*a) for v in self.color)
            pygame.draw.circle(surf,c,(int(self.x),int(self.y)),max(1,int(self.sz)))


# ─────────────── EFFECTS ───────────────
class Particle:
    def __init__(self,x,y,color,vx=None,vy=None,lifetime=1.0,size=4):
        self.x=x;self.y=y;self.color=color;self.vx=vx or random.uniform(-80,80);self.vy=vy or random.uniform(-120,-30)
        self.lifetime=self.max_life=lifetime;self.size=size
    def update(self,dt): self.x+=self.vx*dt;self.y+=self.vy*dt;self.vy+=100*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,self.lifetime/self.max_life);c=tuple(int(v*a) for v in self.color);sz=max(1,int(self.size*a))
        pygame.draw.circle(s,c,(int(self.x),int(self.y)),sz)
    @property
    def alive(self): return self.lifetime>0

class FloatingText:
    def __init__(self,x,y,text,color=GOLD,size="md"):
        self.x=x;self.y=y;self.text=text;self.color=color;self.lifetime=self.max_life=1.4
        self.font={"sm":font_sm,"md":font_md,"lg":font_lg}[size]
    def update(self,dt): self.y-=55*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,min(1,self.lifetime/(self.max_life*0.5)))
        c=tuple(int(v*a+bg*(1-a)) for v,bg in zip(self.color,BG_TOP))
        t=self.font.render(self.text,True,c);s.blit(t,(self.x-t.get_width()//2,int(self.y)))
    @property
    def alive(self): return self.lifetime>0

class Toast:
    def __init__(self,title,desc,icon_color=GOLD):
        self.title=title;self.desc=desc;self.icon_color=icon_color;self.lifetime=self.max_life=4.0;self.slide=0
    def update(self,dt): self.lifetime-=dt;self.slide=min(1,self.slide+dt*5)
    def draw(self,s,idx):
        if self.lifetime<=0:
            return; fade=min(1,self.lifetime/1.0)
            tx=WIDTH-320+(320+10-int(330*self.slide)); y=20+idx*60; w,h=300,52

            ts=pygame.Surface((w,h),pygame.SRCALPHA)

            pygame.draw.rect(ts,(30,25,70,int(220*fade)),(0,0,w,h),border_radius=10)

            pygame.draw.rect(ts,(*self.icon_color,int(200*fade)),(0,0,w,h),2,border_radius=10)

            s.blit(ts,(int(tx),y))

            pygame.draw.circle(s,self.icon_color,(int(tx+18),y+16),8)

            star=font_xs.render("*",True,WHITE);s.blit(star,(int(tx+14),y+9))

            tc=tuple(int(min(255,v*fade)) for v in GOLD);tt=font_sm.render(self.title,True,tc);s.blit(tt,(int(tx+34),y+6))

            dc=tuple(int(min(255,v*fade)) for v in MUTED);dt2=font_xs.render(self.desc,True,dc);s.blit(dt2,(int(tx+34),y+26))

    @property
    def alive(self): return self.lifetime>0

class Sparkline:
    def __init__(self,mp=120): self.data=[];self.max_p=mp;self.timer=0;self.interval=0.5
    def update(self,dt,v):
        self.timer+=dt
        if self.timer>=self.interval:
            self.timer=0;self.data.append(v)
        if len(self.data)>self.max_p:
            self.data.pop(0)
    def draw(self,s,x,y,w,h,color=CYAN):
        if len(self.data)<2:
            return;mv=max(self.data) or 1
            pygame.draw.rect(s,DARK_PURPLE,(x,y,w,h),border_radius=4)

            pygame.draw.rect(s,PANEL_BORDER,(x,y,w,h),1,border_radius=4)

            pts=[(int(x+2+(i/(self.max_p-1))*(w-4)),int(y+h-2-(v/mv)*(h-4))) for i,v in enumerate(self.data)]

        if len(pts)>1:
            pygame.draw.lines(s,color,False,pts,1)
            lbl=font_xxs.render(f"{fmt(self.data[-1])}/s",True,MUTED);s.blit(lbl,(x+3,y+1))


# ─────────────── FALLING ORBS ───────────────
class DNAOrb:
    def __init__(self, total_dna):
        self.x=random.uniform(30,590); self.y=-20; self.vy=random.uniform(30,60)
        self.vx=random.uniform(-10,10); self.alive=True; self.pulse=random.uniform(0,6)
        # Value scales with progression
        scale = max(1, math.log10(total_dna+1))
        r = random.random()
        if r < 0.6:
            self.value=scale*5; self.radius=8; self.color=GREEN; self.name="Small"
        elif r < 0.85: self.value=scale*25; self.radius=12; self.color=CYAN; self.name="Medium"
        elif r < 0.97: self.value=scale*150; self.radius=16; self.color=PURPLE; self.name="Large"
        else: self.value=scale*1000; self.radius=20; self.color=GOLD; self.name="Golden!"
    def update(self,dt):
        self.y+=self.vy*dt; self.x+=self.vx*dt+math.sin(self.y*0.02)*0.5; self.pulse+=dt*4
        if self.y>HEIGHT+30:
            self.alive=False
    def draw(self,s):
        p=0.7+0.3*math.sin(self.pulse); r=int(self.radius*p)
        gs=pygame.Surface((r*4,r*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,40),(r*2,r*2),r*2)
        pygame.draw.circle(gs,(*self.color,120),(r*2,r*2),r)
        pygame.draw.circle(gs,(*WHITE,180),(r*2,r*2),max(2,r//2))
        s.blit(gs,(int(self.x-r*2),int(self.y-r*2)))
    def hit_test(self,mx,my): return math.sqrt((mx-self.x)**2+(my-self.y)**2)<self.radius*1.5

# ─────────────── BOSS ───────────────
class Boss:
    def __init__(self, tier, total_dna):
        self.tier=min(tier, len(BOSS_NAMES)-1)
        self.name=BOSS_NAMES[self.tier]; self.color=BOSS_COLORS[self.tier]
        self.max_hp=int((100+self.tier*300)*(1+math.log10(total_dna+1)*2))
        self.hp=self.max_hp; self.x=310; self.y=300; self.alive=True
        self.reward=int(self.max_hp*5*(1+self.tier*0.5))
        self.timer=45+self.tier*10; self.flash=0; self.shake=0
        self.spawn_anim=1.0
    def update(self,dt):
        self.timer-=dt; self.flash=max(0,self.flash-dt); self.shake=max(0,self.shake-dt)
        self.spawn_anim=max(0,self.spawn_anim-dt*2)
        if self.timer<=0:
            self.alive=False
        if self.hp<=0:
            self.alive=False
    def damage(self,amount):
        self.hp-=amount; self.flash=0.15; self.shake=0.08
    def draw(self,s,t):
        if not self.alive:
            return
            sx=int(self.shake*20*(random.random()*2-1)); sy=int(self.shake*15*(random.random()*2-1))

            cx,cy=self.x+sx,self.y+sy; scale=min(1,self.spawn_anim)*1.0

        # Warning flash
        if self.spawn_anim>0.5:
            ws=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            a=int(60*(self.spawn_anim-0.5)*2*(math.sin(t*15)+1)*0.5)
            ws.fill((*RED,max(0,min(255,a)))); s.blit(ws,(0,0))
        # Body
        bob=math.sin(t*1.5)*8*scale; size=(50+self.tier*10)*scale
        # Aura
        asurf=pygame.Surface((int(size*6),int(size*6)),pygame.SRCALPHA)
        pulse=(math.sin(t*3)+1)*0.5
        pygame.draw.circle(asurf,(*self.color,int(30*(0.5+0.5*pulse))),(int(size*3),int(size*3)),int(size*2.5))
        s.blit(asurf,(int(cx-size*3),int(cy-size*3+bob)))
        # Spiky body
        pts=[]
        for a in range(0,360,15):
            rad=math.radians(a); spike=math.sin(a*3+t*2)*5*scale
            r=size+spike+(15 if a%30<15 else 0)*scale
            pts.append((cx+math.sin(rad)*r,cy+math.cos(rad)*r*0.8+bob))
        body_c=self.color if self.flash<=0 else WHITE
        pygame.draw.polygon(s,body_c,pts)
        pygame.draw.polygon(s,tuple(min(255,c+60) for c in self.color),pts,2)
        # Eyes
        for side in [-1,1]:
            ex=int(cx+side*15*scale); ey=int(cy-10*scale+bob)
            pygame.draw.circle(s,WHITE,(ex,ey),int(8*scale))
            pygame.draw.circle(s,(200,0,0),(ex+int(side*2*scale),ey),int(4*scale))
            pygame.draw.circle(s,WHITE,(ex+int(side*1*scale),ey-int(2*scale)),max(1,int(2*scale)))
        # HP bar
        bw=200; bh=12; bx=cx-bw//2; by=cy-int(size*1.2+bob)
        pygame.draw.rect(s,DARK_RED,(bx,by,bw,bh),border_radius=4)
        hw=int(bw*max(0,self.hp/self.max_hp))
        if hw>0:
            for px in range(hw):
                ratio=px/bw; c=(int(200*(1-ratio)+50*ratio),int(50+150*ratio),50)
                pygame.draw.line(s,c,(bx+px,by),(bx+px,by+bh-1))
        pygame.draw.rect(s,WHITE,(bx,by,bw,bh),1,border_radius=4)
        hp_txt=font_xs.render(f"{max(0,self.hp):.0f}/{self.max_hp}",True,WHITE)
        s.blit(hp_txt,(cx-hp_txt.get_width()//2,by-1))
        # Name & timer
        nt=font_md.render(f"BOSS: {self.name}",True,RED)
        s.blit(nt,(cx-nt.get_width()//2,by-22))
        tc=RED if self.timer<10 else ORANGE if self.timer<20 else MUTED
        tt=font_sm.render(f"Time: {self.timer:.0f}s  |  Reward: {fmt(self.reward)}",True,tc)
        s.blit(tt,(cx-tt.get_width()//2,by+bh+4))

# ─────────────── UPGRADES ───────────────
UPGRADES = [
    {"name":"Click Power","desc":"+1 DNA/click","base_cost":10,"cost_mult":1.15,"type":"click","value":1,"key":"1"},
    {"name":"Auto Cell","desc":"+0.5 DNA/sec","base_cost":25,"cost_mult":1.18,"type":"cps","value":0.5,"key":"2"},
    {"name":"Click Boost","desc":"+3 DNA/click","base_cost":200,"cost_mult":1.15,"type":"click","value":3,"key":"3"},
    {"name":"Amoeba Swarm","desc":"+2 DNA/sec","base_cost":500,"cost_mult":1.18,"type":"cps","value":2,"key":"4"},
    {"name":"Mega Click","desc":"+15 DNA/click","base_cost":5e3,"cost_mult":1.15,"type":"click","value":15,"key":"5"},
    {"name":"Bacteria Colony","desc":"+10 DNA/sec","base_cost":1e4,"cost_mult":1.18,"type":"cps","value":10,"key":"6"},
    {"name":"Hyper Click","desc":"+100 DNA/click","base_cost":1e5,"cost_mult":1.15,"type":"click","value":100,"key":"7"},
    {"name":"Biome Engine","desc":"+75 DNA/sec","base_cost":2e5,"cost_mult":1.18,"type":"cps","value":75,"key":"8"},
    {"name":"Omega Click","desc":"+1K DNA/click","base_cost":2e6,"cost_mult":1.15,"type":"click","value":1000,"key":"9"},
    {"name":"Evolution Core","desc":"+500 DNA/sec","base_cost":5e6,"cost_mult":1.18,"type":"cps","value":500,"key":"0"},
    {"name":"Singularity Tap","desc":"+10K/click","base_cost":5e7,"cost_mult":1.15,"type":"click","value":1e4,"key":""},
    {"name":"Genesis Engine","desc":"+5K DNA/sec","base_cost":1e8,"cost_mult":1.18,"type":"cps","value":5e3,"key":""},
]
BUY_AMOUNTS=[1,10,100,-1]; BUY_LABELS=["x1","x10","x100","MAX"]

# ─────────────── CREATURE RENDERER (compact) ───────────────
# ─────────────── CREATURE RENDERER ───────────────
class CreatureRenderer:
    def __init__(self, genome):
        self.g = genome

    def draw(self, surface, cx, cy, td, t, hover=False):
        g = self.g
        sf = 1.0 + hover * 0.07
        bob = math.sin(t * 2.0) * 6
        color = g.body_color(td, t)
        acc = g.accent_color(td, t)
        bs = g.body_size(td) * sf
        cy_b = cy + bob
        # Shadow
        sw, sh = int(bs * 2.2), max(4, int(bs * 0.3))
        shadow_surf = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 40), (0, 0, sw * 2, sh * 2))
        surface.blit(shadow_surf, (cx - sw, cy + bs * 0.9))
        # Draw layers
        if g.has_aura(td):
            self._draw_aura(surface, cx, cy_b, bs, td, t, color, acc)
        if g.tail_length(td) > 0:
            self._draw_tail(surface, cx, cy_b, bs, td, t, color, acc)
        if g.limb_count(td) > 0:
            self._draw_limbs(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_wings(td):
            self._draw_wings(surface, cx, cy_b, bs, td, t, color, acc)
        self._draw_body(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_pattern(td):
            self._draw_pattern(surface, cx, cy_b, bs, td, t, color, acc)
        if g.spike_count(td) > 0:
            self._draw_spikes(surface, cx, cy_b, bs, td, t, acc)
        hx, hy = cx - bs * 0.6, cy_b - bs * 0.5
        if g.has_ears(td):
            self._draw_ears(surface, hx, hy, bs, td, t, color, acc)
        if g.has_horns(td):
            self._draw_horns(surface, hx, hy, bs, td, t, acc)
        self._draw_eyes(surface, hx, hy, bs, td, t, color)
        self._draw_mouth(surface, hx, hy, bs, td, t, acc)
        # Bioluminescent glow
        bio = g.bioluminescence(td)
        if bio > 0.1:
            gs = pygame.Surface((int(bs * 4), int(bs * 4)), pygame.SRCALPHA)
            pulse = (math.sin(t * 3) + 1) * 0.5
            a = int(bio * (30 + 25 * pulse))
            pygame.draw.circle(gs, (*color, a), (int(bs * 2), int(bs * 2)), int(bs * 1.6))
            surface.blit(gs, (int(cx - bs * 2), int(cy_b - bs * 2)))

    def _draw_body(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        segs = g.body_segments(td)
        if segs <= 1:
            pts = []
            for a in range(360):
                r = math.radians(a)
                w = math.sin(r * 3 + t * 3) * 3 + math.sin(r * 5 + t * 2) * 2
                rx = (bs + w) * g.body_width_ratio
                ry = bs * 0.85 + w * 0.5
                pts.append((cx + math.sin(r) * rx, cy + math.cos(r) * ry))
            pygame.draw.polygon(s, col, pts)
            hl_r = max(3, int(bs * 0.3))
            hl_color = tuple(min(255, c + 60) for c in col)
            pygame.draw.circle(s, hl_color, (int(cx - bs * 0.25), int(cy - bs * 0.3)), hl_r)
        else:
            tl = bs * 2 * segs * 0.6
            sr = bs * 0.65
            for i in range(segs):
                ratio = i / max(segs - 1, 1)
                wave = math.sin(t * 2 + i * 0.8) * 12 * (1 - ratio * 0.3)
                sx = cx - tl / 2 + ratio * tl + wave
                sy = cy + ratio * bs * 0.3
                sri = sr * (1 - ratio * 0.25)
                wb = math.sin(t * 3 + i * 2) * 2
                sp = []
                for a in range(360):
                    rad = math.radians(a)
                    sp.append((sx + math.sin(rad) * (sri + wb), sy + math.cos(rad) * (sri * 0.8 + wb * 0.5)))
                seg_c = tuple(int(c * (1 - ratio * 0.15)) for c in col)
                pygame.draw.polygon(s, seg_c, sp)
                if i == 0:
                    pygame.draw.circle(s, tuple(min(255, c + 50) for c in col),
                                       (int(sx - sri * 0.2), int(sy - sri * 0.3)), max(2, int(sri * 0.3)))

    def _draw_eyes(self, s, hx, hy, bs, td, t, col):
        g = self.g
        count = g.eye_count(td)
        es = g.eye_size(td)
        style = g.eye_style
        if style == "cyclops":
            positions = [(0, 0)]
            es *= 1.8
        elif style == "compound":
            positions = []
            for row in range(min((count + 2) // 3, 3)):
                c_in_row = min(count - row * 3, 3)
                for c_ in range(c_in_row):
                    positions.append((c_ - (c_in_row - 1) / 2, row - 0.5))
            es *= 0.7
        else:
            positions = [(i - (count - 1) / 2, 0) for i in range(count)]
        for px, py in positions:
            ex = hx + px * es * 1.6
            ey = hy + py * es * 1.6 - bs * 0.1
            if style == "slit":
                pygame.draw.ellipse(s, WHITE, (int(ex - es), int(ey - es * 0.7), int(es * 2), int(es * 1.4)))
                pygame.draw.ellipse(s, (20, 20, 40),
                    (int(ex - es * 0.15), int(ey - es * 0.6), int(es * 0.3), int(es * 1.2)))
            elif style == "compound":
                for ci in range(6):
                    angle = ci * math.pi * 2 / 6 + t * 0.5
                    cr = es * 0.6
                    ccx = ex + math.cos(angle) * es * 0.4
                    ccy = ey + math.sin(angle) * es * 0.4
                    pygame.draw.circle(s, (200, 200, 255), (int(ccx), int(ccy)), max(1, int(cr)))
                    pygame.draw.circle(s, (30, 30, 60), (int(ccx), int(ccy)), max(1, int(cr * 0.5)))
            else:
                pygame.draw.circle(s, WHITE, (int(ex), int(ey)), int(es))
                look = math.sin(t * 2) * es * 0.2
                pr = es * 0.5
                pygame.draw.circle(s, (20, 20, 40), (int(ex + look), int(ey)), int(pr))
                pygame.draw.circle(s, WHITE, (int(ex + look - pr * 0.3), int(ey - pr * 0.3)), max(1, int(pr * 0.3)))

    def _draw_mouth(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        comp = g.mouth_complexity(td)
        if comp < 0.1:
            return
        mx_p = hx + bs * 0.3
        my_p = hy + bs * 0.2
        style = g.mouth_style
        if style == "smile" or comp < 0.3:
            mw = bs * 0.5 * comp
            mh = bs * 0.2 * comp
            if mw > 3:
                pygame.draw.arc(s, acc,
                    (int(mx_p - mw), int(my_p - mh), int(mw * 2), int(mh * 2)),
                    math.pi + 0.3, 2 * math.pi - 0.3, max(1, int(2 * comp + 1)))
        if comp > 0.3:
            if style == "teeth":
                tw = bs * 0.4
                for i in range(int(3 + comp * 5)):
                    tx = mx_p - tw / 2 + (i / max(int(3 + comp * 5) - 1, 1)) * tw
                    th = 3 + comp * 5
                    pygame.draw.polygon(s, WHITE, [
                        (int(tx - 2), int(my_p)), (int(tx + 2), int(my_p)), (int(tx), int(my_p + th))])
            elif style == "beak":
                bl = bs * 0.4 * comp
                pygame.draw.polygon(s, (255, 200, 80), [
                    (int(mx_p), int(my_p - 4)), (int(mx_p + bl), int(my_p)), (int(mx_p), int(my_p + 4))])
            elif style == "tentacles":
                for i in range(int(2 + comp * 4)):
                    ba = -0.5 + i * (1.0 / max(int(2 + comp * 4) - 1, 1))
                    pts = [(int(mx_p), int(my_p))]
                    for j in range(1, 6):
                        tr = j / 5
                        w = math.sin(t * 5 + i + j * 0.7) * 8 * tr
                        pts.append((int(mx_p + tr * bs * 0.5 * comp + w),
                                    int(my_p + tr * bs * 0.3 * comp + ba * bs * 0.2 * tr)))
                    if len(pts) > 1:
                        pygame.draw.lines(s, acc, False, pts, max(1, int(2)))
            elif style == "lamprey":
                mr = int(bs * 0.15 * comp)
                if mr > 2:
                    pygame.draw.circle(s, (40, 10, 10), (int(mx_p), int(my_p)), mr)
                    for i in range(int(6 + comp * 10)):
                        a = i * math.pi * 2 / int(6 + comp * 10)
                        pygame.draw.line(s, WHITE,
                            (int(mx_p + math.cos(a) * mr * 0.6), int(my_p + math.sin(a) * mr * 0.6)),
                            (int(mx_p + math.cos(a) * mr), int(my_p + math.sin(a) * mr)), 1)

    def _draw_limbs(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        count = g.limb_count(td)
        length = g.limb_length(td)
        style = g.limb_style
        if count == 0 or length < 3:
            return
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            idx = i // 2
            tp = count // 2
            spread = bs * 1.2
            bx = cx - spread / 2 + (idx / max(tp - 1, 1)) * spread if tp > 1 else cx
            by = cy + bs * 0.6
            anim = math.sin(t * 4 + i * 1.2) * 0.3
            if style == "tentacle":
                pts = [(int(bx + side * bs * 0.4), int(by))]
                for j in range(1, 8):
                    tr = j / 7
                    w = math.sin(t * 5 + i + j * 0.8) * 12 * tr
                    pts.append((int(bx + side * (bs * 0.4 + length * tr) + w),
                                int(by + length * tr * 0.5 + anim * length * tr)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(4)))
            elif style == "crab":
                kx = bx + side * (bs * 0.5 + length * 0.5)
                ky = by + length * 0.3 + anim * 10
                fx = kx + side * length * 0.4
                fy = by + length * 0.8
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(kx), int(ky)), max(2, int(4)))
                pygame.draw.line(s, acc, (int(kx), int(ky)),
                               (int(fx), int(fy)), max(2, int(3)))
                if i < 2:
                    cs = max(2, int(bs * 0.15))
                    pygame.draw.circle(s, col, (int(fx), int(fy)), cs)
            elif style == "spindly":
                px, py = bx + side * bs * 0.3, by
                for j in range(3):
                    tr = (j + 1) / 3
                    nx = px + side * length * 0.35
                    ny = py + length * 0.3 + anim * 8 * tr
                    pygame.draw.line(s, acc, (int(px), int(py)), (int(nx), int(ny)), max(1, int(2)))
                    pygame.draw.circle(s, col, (int(nx), int(ny)), max(1, int(3)))
                    px, py = nx, ny
            else:  # stubby
                fx = bx + side * (bs * 0.5 + length * 0.3)
                fy = by + length * 0.7 + anim * 8
                lw = max(3, int(bs * 0.15))
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(fx), int(fy)), lw)
                pygame.draw.circle(s, col, (int(fx), int(fy)), max(2, int(lw * 0.8)))

    def _draw_wings(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        ws = g.wing_size(td)
        if ws < 3:
            return
        style = g.wing_style
        flap = math.sin(t * 3) * 15
        for side in [-1, 1]:
            if style == "bat":
                pts = [
                    (cx + side * bs * 0.3, cy - bs * 0.3),
                    (cx + side * ws, cy - bs * 0.5 + flap),
                    (cx + side * ws * 0.7, cy - bs * 0.1 + flap * 0.6),
                    (cx + side * ws * 1.1, cy + bs * 0.1 + flap * 0.8),
                    (cx + side * ws * 0.5, cy + bs * 0.2)]
                wc = tuple(max(0, c - 50) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])
                pygame.draw.polygon(s, acc, [(int(p[0]), int(p[1])) for p in pts], 2)
            elif style == "feathered":
                for layer in range(3):
                    off = layer * 8
                    pts = [
                        (cx + side * bs * 0.2, cy - bs * 0.2),
                        (cx + side * (ws - off), cy - bs * (0.6 + layer * 0.2) + flap * (1 - layer * 0.2)),
                        (cx + side * (ws * 0.8 - off), cy + bs * 0.1 + flap * 0.5)]
                    lc = tuple(min(255, c + layer * 20) for c in col)
                    pygame.draw.polygon(s, lc, [(int(p[0]), int(p[1])) for p in pts])
            elif style == "crystal":
                for j in range(4):
                    a = math.radians(-30 + j * 25 + side * 20) + math.sin(t * 2) * 0.1
                    d = ws * (0.6 + j * 0.12)
                    tx = cx + side * math.cos(a) * d
                    ty = cy - abs(math.sin(a)) * d * 0.7 + flap * 0.3
                    pts = [(int(cx + side * bs * 0.3), int(cy - bs * 0.3)),
                           (int(tx), int(ty)),
                           (int(cx + side * 10), int(cy))]
                    als = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    pygame.draw.polygon(als, (*acc, 100), pts)
                    s.blit(als, (0, 0))
                    pygame.draw.polygon(s, acc, pts, 1)
            else:  # insect
                pts = [
                    (cx + side * bs * 0.2, cy - bs * 0.1),
                    (cx + side * ws, cy - bs * 0.8 + flap),
                    (cx + side * ws * 0.9, cy - bs * 0.2 + flap * 0.4),
                    (cx + side * ws * 0.3, cy + bs * 0.3)]
                wc = tuple(max(0, c - 30) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])

    def _draw_tail(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        length = g.tail_length(td)
        if length < 3:
            return
        style = g.tail_style
        segs = max(3, int(length / 10))
        pts = []
        for i in range(segs + 1):
            tr = i / segs
            w = math.sin(t * 3 + tr * 4) * (10 + tr * 15)
            tx = cx + bs * 0.7 + tr * length + w
            ty = cy + tr * bs * 0.3 + math.sin(t * 2 + tr * 3) * 5
            pts.append((tx, ty))
            sr = max(2, int(bs * 0.3 * (1 - tr * 0.7)))
            sc = tuple(int(c * (1 - tr * 0.2)) for c in col)
            pygame.draw.circle(s, sc, (int(tx), int(ty)), sr)
        if style == "spiked":
            for i in range(2, segs, 2):
                tr = i / segs
                px, py = pts[i]
                sh = 8 + tr * 10
                pygame.draw.polygon(s, acc, [(int(px - 3), int(py)),
                                                  (int(px + 3), int(py)),
                                                  (int(px), int(py - sh))])
        elif style == "forked":
            tx, ty = pts[-1]
            fl = length * 0.2
            for d in [-1, 1]:
                pygame.draw.line(s, acc, (int(tx), int(ty)),
                               (int(tx + fl + math.sin(t * 4 + d) * 5), int(ty + d * fl * 0.5)),
                               max(1, int(3)))
        elif style == "flame":
            tx, ty = pts[-1]
            for _ in range(5):
                fc = random.choice([(255, 100, 0), (255, 200, 0), (255, 50, 0)])
                pygame.draw.circle(s, fc,
                                   (int(tx + random.randint(-8, 12)), int(ty + random.randint(-12, 12))),
                                   random.randint(3, int(6 + g.level(td))))
        elif style == "tentacle":
            tx, ty = pts[-1]
            for d in [-1, 1]:
                tent_pts = [(int(tx), int(ty))]
                for j in range(1, 5):
                    tr = j / 4
                    w = math.sin(t * 6 + d + j) * 8
                    tent_pts.append((int(tx + d * tr * 20 + w), int(ty + tr * 15)))
                if len(tent_pts) > 1:
                    pygame.draw.lines(s, acc, False, tent_pts, max(1, int(2)))

    def _draw_spikes(self, s, cx, cy, bs, td, t, acc):
        g = self.g
        count = g.spike_count(td)
        size = g.spike_size(td)
        if count < 1 or size < 2:
            return
        for i in range(count):
            a = (i / count) * math.pi * 2 + 0.5
            if math.sin(a) > 0.2:
                continue
            sx = cx + math.cos(a) * bs * 0.85
            sy = cy + math.sin(a) * bs * 0.85
            pygame.draw.polygon(s, acc, [
                (int(sx - math.sin(a) * 3), int(sy + math.cos(a) * 3)),
                (int(sx + math.sin(a) * 3), int(sy - math.cos(a) * 3)),
                (int(sx + math.cos(a) * size), int(sy + math.sin(a) * size))])

    def _draw_horns(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        count = g.horn_count(td)
        size = g.horn_size(td)
        style = g.horn_style
        if count < 1 or size < 3:
            return
        for i in range(count):
            off = (i - (count - 1) / 2) * 12 if count > 1 else 0
            bx, by = hx + off, hy - bs * 0.4
            if style == "pointed":
                pygame.draw.polygon(s, acc, [(int(bx - 4), int(by)),
                                                  (int(bx + 4), int(by)),
                                                  (int(bx + off * 0.3), int(by - size))])
            elif style == "curved":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.4 + math.sin(tr * math.pi) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
            elif style == "crystal":
                pygame.draw.polygon(s, acc, [(int(bx), int(by - size)),
                                                  (int(bx - 5), int(by)),
                                                  (int(bx + 5), int(by))])
            elif style == "antler":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.5 + math.sin(tr * 3) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
                if len(pts) > 3:
                    bp = pts[2]
                    pygame.draw.line(s, acc, bp,
                                   (int(bp[0] + (15 if off >= 0 else -15)), int(bp[1] - 10)),
                                   max(1, int(2)))

    def _draw_ears(self, s, hx, hy, bs, td, t, col, acc):
        g = self.g
        es = g.ear_size(td)
        if es < 3:
            return
        if g.ear_type == "pointed":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.5
                ey = hy - bs * 0.3
                pygame.draw.polygon(s, col, [(int(ex - 8), int(ey)),
                                                  (int(ex + 8), int(ey)),
                                                  (int(ex + side * 5), int(ey - es))])
                pygame.draw.polygon(s, acc, [(int(ex - 8), int(ey)),
                                                   (int(ex + 8), int(ey)),
                                                   (int(ex + side * 5), int(ey - es))], 1)
        elif g.ear_type == "frilled":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.4
                ey = hy - bs * 0.2
                fp = []
                for j in range(8):
                    a = math.radians(-90 + (j / 7) * 60 * side)
                    r = es * (0.5 + math.sin(j * 1.5) * 0.3)
                    fp.append((int(ex + math.cos(a) * r * side), int(ey + math.sin(a) * r)))
                if len(fp) > 2:
                    pygame.draw.lines(s, acc, False, fp, 2)
        elif g.ear_type == "antenna":
            for side in [-1, 1]:
                bx = hx + side * bs * 0.3
                by = hy - bs * 0.3
                w = math.sin(t * 5 + side) * 5
                tx = bx + side * es * 0.5 + w
                ty = by - es + w
                pygame.draw.line(s, acc, (int(bx), int(by)), (int(tx), int(ty)), 2)
                glow = (math.sin(t * 4 + side * 2) + 1) * 0.5
                gc = tuple(int(min(255, c * (0.5 + 0.5 * glow))) for c in acc)
                pygame.draw.circle(s, gc, (int(tx), int(ty)), max(2, int(4 * glow + 2)))

    def _draw_pattern(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        op = g.pattern_opacity(td)
        pt = g.pattern_type
        if op < 0.05:
            return
        pc = tuple(int(c * op + bg * (1 - op)) for c, bg in zip(acc, col))
        if pt == "spots":
            for i in range(int(5 + g.level(td) * 1.5)):
                a = i * 2.3 + 0.5
                d = bs * (0.2 + (i % 3) * 0.2)
                pygame.draw.circle(s, pc, (int(cx + math.cos(a) * d), int(cy + math.sin(a) * d * 0.7)),
                                   max(2, int(bs * 0.1 * op)))
        elif pt == "stripes":
            for i in range(-3, 4):
                sx = cx + i * bs * 0.25
                sh = int(bs * 1.2)
                pygame.draw.line(s, pc,
                    (int(sx + math.sin(i + t) * 3), int(cy - sh // 2)),
                    (int(sx + math.sin(i + t + 1) * 3), int(cy + sh // 2)),
                    max(1, int(2 * op)))
        elif pt == "rings":
            for i in range(1, 4):
                pygame.draw.circle(s, pc, (int(cx), int(cy)),
                                   int(bs * 0.3 * i * op), max(1, int(2 * op)))
        elif pt == "scales":
            for row in range(-2, 3):
                for c_ in range(-2, 3):
                    sx = cx + c_ * bs * 0.3 + (row % 2) * bs * 0.15
                    sy = cy + row * bs * 0.25
                    if math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2) < bs * 0.8:
                        sr = int(bs * 0.12 * op)
                        pygame.draw.arc(s, pc,
                            (int(sx - sr), int(sy - sr), sr * 2, sr * 2),
                            0, math.pi, max(1, int(1.5 * op)))

    def _draw_aura(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        intensity = g.aura_intensity(td)
        style = g.aura_style
        if intensity < 0.05:
            return
        if style == "glow":
            for layer in range(3):
                r = int(bs * (1.5 + layer * 0.4) * intensity)
                a = int(30 * intensity * (1 - layer * 0.25))
                gs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                p = (math.sin(t * 3 + layer) + 1) * 0.5
                pygame.draw.circle(gs, (*col, int(a * (0.7 + 0.3 * p))),
                                   (r + 2, r + 2), r)
                s.blit(gs, (cx - r - 2, cy - r - 2))
        elif style == "sparks":
            for i in range(int(8 * intensity)):
                a = t * (1.5 + i * 0.3) + i * math.pi * 2 / 8
                d = (bs * 1.2 + math.sin(t * 2 + i) * 15) * intensity
                c = acc if i % 2 else col
                pygame.draw.circle(s, c, (int(cx + math.cos(a) * d),
                                              int(cy + math.sin(a) * d * 0.7)),
                                   max(1, int(3 * intensity)))
        elif style == "rings":
            for i in range(2):
                ra = t * (1 + i * 0.7) + i * 1.5
                rx = int((bs * 1.5 + i * 15) * intensity)
                ry = int((bs * 0.4 + i * 8) * intensity)
                rs = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
                pygame.draw.ellipse(rs, (*acc, int(80 * intensity)), (2, 2, rx * 2, ry * 2),
                                 max(1, int(2 * intensity)))
                rot = pygame.transform.rotate(rs, math.degrees(ra))
                s.blit(rot, (cx - rot.get_width() // 2, cy - rot.get_height() // 2))
        elif style == "dna_helix":
            for i in range(int(20 * intensity)):
                tr = i / max(int(20 * intensity) - 1, 1)
                a = tr * math.pi * 4 + t * 2
                d = bs * 1.3 * intensity
                for strand in [0, math.pi]:
                    sx = cx + math.cos(a + strand) * d * math.sin(tr * math.pi)
                    sy = cy - bs + tr * bs * 2
                    pygame.draw.circle(s, col if strand == 0 else acc, (int(sx), int(sy)),
                                       max(1, int(2 * intensity)))
        elif style == "constellation":
            sp = []
            for i in range(int(10 * intensity)):
                seed = i * 7.3 + 1.2
                a = seed * 2.1 + t * 0.3
                d = bs * (0.8 + (seed % 0.6) * 0.8) * intensity
                sx = cx + math.cos(a) * d
                sy = cy + math.sin(a) * d * 0.7
                sp.append((int(sx), int(sy)))
                tw = (math.sin(t * 3 + i * 2) + 1) * 0.5
                pygame.draw.circle(s, WHITE, (int(sx), int(sy)),
                                   max(1, int((1 + tw) * 2 * intensity)))
            for i in range(len(sp)):
                for j in range(i + 1, len(sp)):
                    dx = sp[i][0] - sp[j][0]
                    dy = sp[i][1] - sp[j][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < bs * 1.5 * intensity:
                        ls = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        al = max(0, min(255, int(40 * intensity * (1 - d / (bs * 1.5 * intensity)))))
                        pygame.draw.line(ls, (*acc, al), sp[i], sp[j], 1)
                        s.blit(ls, (0, 0))

# ─────────────── GAME STATE ───────────────
class Game:
    def __init__(self):
        self.dna=0.0;self.total_dna=0.0;self.total_clicks=0;self.total_crits=0
        self.total_upgrades_bought=0;self.click_power=1;self.cps=0.0
        self.upgrade_counts=[0]*len(UPGRADES)
        self.particles=[];self.float_texts=[];self.toasts=[]
        self.t=0.0;self.creature_hover=False;self.shop_scroll=0;self.max_scroll=0
        self.creature_cx=320;self.creature_cy=360
        self.shake_x=0;self.shake_y=0;self.shake_time=0
        # Prestige
        self.prestige_count=0;self.prestige_mult=1.0
        # Combo
        self.combo=0;self.combo_timer=0;self.combo_decay=1.2;self.max_combo=0
        # Crits
        self.crit_chance=0.05;self.crit_mult=5.0
        # Achievement bonus tracking
        self.ach_bonus_click=0;self.ach_bonus_cps=0;self.ach_bonus_crit=0;self.ach_bonus_prestige=0;self.ach_bonus_crit_mult=0
        # Buy amount
        self.buy_amount_idx=0;self.display_dna=0.0
        # UI panels
        self.show_traits=False;self.show_bestiary=False;self.show_stats=False;self.show_settings=False;self.show_achievements_panel=False
        self.hovered_upgrade=-1;self.panel_scroll=0
        # Background
        self.starfield=Starfield();self.ambient_particles=[AmbientParticle()for _ in range(30)]
        self.sparkline=Sparkline()
        # Achievements
        self.achievements_unlocked=set()
        # Milestones
        self.last_milestone=0;self.milestones=[10,100,1e3,1e4,1e5,1e6,1e7,1e8,1e9,1e10,1e11,1e12]
        # Auto-save
        self.autosave_timer=0;self.save_time=time.time();self.play_time=0.0
        # Boss system
        self.boss=None;self.boss_timer=random.uniform(60,120);self.bosses_defeated=0;self.boss_tier=0
        # Orbs
        self.orbs=[];self.orb_timer=0;self.orbs_collected=0
        # Abilities
        self.ability_cooldowns=[0.0]*len(ABILITIES);self.ability_actives=[0.0]*len(ABILITIES)
        self.abilities_unlocked=[False]*len(ABILITIES)
        # Mutations
        self.active_mutation=None;self.mutation_timer=0;self.mutations_experienced=0;self.mutation_event_timer=random.uniform(45,90)
        # Bestiary
        self.bestiary=[]
        # Settings
        self.sound_on=SOUND_ENABLED;self.particle_quality=2  # 0=low,1=med,2=high
        # Genome
        seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed);self.renderer=CreatureRenderer(self.genome);self.seed_display=seed
        self._try_load()

    def _try_load(self):
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE,'r') as f: data=json.load(f)
            self.dna=data.get("dna",0);self.total_dna=data.get("total_dna",0)
            self.total_clicks=data.get("total_clicks",0);self.total_crits=data.get("total_crits",0)
            self.total_upgrades_bought=data.get("total_upgrades_bought",0)
            self.click_power=data.get("click_power",1);self.cps=data.get("cps",0)
            self.upgrade_counts=data.get("upgrade_counts",[0]*len(UPGRADES))
            self.prestige_count=data.get("prestige_count",0);self.prestige_mult=data.get("prestige_mult",1.0)
            self.max_combo=data.get("max_combo",0);self.achievements_unlocked=set(data.get("achievements",[]))
            self.buy_amount_idx=data.get("buy_amount_idx",0);self.save_time=data.get("save_time",time.time())
            self.play_time=data.get("play_time",0);self.bosses_defeated=data.get("bosses_defeated",0)
            self.boss_tier=data.get("boss_tier",0);self.orbs_collected=data.get("orbs_collected",0)
            self.mutations_experienced=data.get("mutations_experienced",0)
            self.ach_bonus_click=data.get("ach_bonus_click",0);self.ach_bonus_cps=data.get("ach_bonus_cps",0)
            self.ach_bonus_crit=data.get("ach_bonus_crit",0);self.ach_bonus_prestige=data.get("ach_bonus_prestige",0)
            self.ach_bonus_crit_mult=data.get("ach_bonus_crit_mult",0)
            self.bestiary=data.get("bestiary",[]);self.sound_on=data.get("sound_on",SOUND_ENABLED)
            self.particle_quality=data.get("particle_quality",2)
            self.genome=Genome.from_dict(data["genome"]);self.renderer=CreatureRenderer(self.genome);self.seed_display=self.genome.seed
            # Offline progress
            elapsed=time.time()-self.save_time
            if elapsed>5:
                cps_val=self.effective_cps();off_earn=cps_val*elapsed*0.5
                if off_earn>0:
                    self.dna+=off_earn;self.total_dna+=off_earn
                    self.toasts.append(Toast("Welcome Back!",f"Earned {fmt(off_earn)} DNA away ({elapsed/60:.1f}m)",CYAN))
        except Exception as e: print(f"Load failed: {e}")

    def save(self):
        try:
            data={"dna":self.dna,"total_dna":self.total_dna,"total_clicks":self.total_clicks,
                "total_crits":self.total_crits,"total_upgrades_bought":self.total_upgrades_bought,
                "click_power":self.click_power,"cps":self.cps,"upgrade_counts":self.upgrade_counts,
                "prestige_count":self.prestige_count,"prestige_mult":self.prestige_mult,
                "max_combo":self.max_combo,"achievements":list(self.achievements_unlocked),
                "buy_amount_idx":self.buy_amount_idx,"save_time":time.time(),"play_time":self.play_time,
                "bosses_defeated":self.bosses_defeated,"boss_tier":self.boss_tier,
                "orbs_collected":self.orbs_collected,"mutations_experienced":self.mutations_experienced,
                "ach_bonus_click":self.ach_bonus_click,"ach_bonus_cps":self.ach_bonus_cps,
                "ach_bonus_crit":self.ach_bonus_crit,"ach_bonus_prestige":self.ach_bonus_prestige,
                "ach_bonus_crit_mult":self.ach_bonus_crit_mult,
                "bestiary":self.bestiary,"sound_on":self.sound_on,"particle_quality":self.particle_quality,
                "genome":self.genome.to_dict()}
            with open(SAVE_FILE,'w') as f: json.dump(data,f,indent=2)
        except Exception as e: print(f"Save failed: {e}")

    def prestige(self):
        if self.total_dna<1e6:
            return
            bonus=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige

            self.prestige_count+=1;self.prestige_mult+=bonus

            self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),

            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            self.dna=0;self.total_dna=0;self.click_power=1;self.cps=0

            self.upgrade_counts=[0]*len(UPGRADES);self.combo=0;self.combo_timer=0;self.last_milestone=0

            self.total_clicks=0;self.total_crits=0;self.total_upgrades_bought=0;self.sparkline=Sparkline()

            self.boss=None;self.boss_timer=random.uniform(60,120);self.active_mutation=None

            self.toasts.append(Toast("PRESTIGE!",f"+{bonus:.2f}x permanent (now {self.prestige_mult:.2f}x)",GOLD))

            self._play(snd_prestige);self._burst(self.creature_cx,self.creature_cy,80,[GOLD,CYAN,WHITE,PURPLE]);self.save()


    def _trait_summary(self):
        g=self.genome;td=self.total_dna
        return{"limbs":g.limb_style,"wings":g.wing_style,"eyes":g.eye_style,"tail":g.tail_style,
               "horns":g.horn_style,"mouth":g.mouth_style,"aura":g.aura_style,"pattern":g.pattern_type,
               "ears":g.ear_type,"level":f"{g.level(td):.1f}"}

    def upgrade_cost(self,idx):
        upg=UPGRADES[idx];base=upg["base_cost"];cm=upg["cost_mult"];owned=self.upgrade_counts[idx];amt=self.get_buy_amount()
        if amt==-1:
            total=0;count=0
            while True:
                c=int(base*(cm**(owned+count)));total+=c;count+=1
                if self.dna-total<c or count>10000:
                    total-=c;count-=1;break
            return total,count
        else:total=sum(int(base*(cm**(owned+i)))for i in range(amt));return total,amt

    def get_buy_amount(self):return BUY_AMOUNTS[self.buy_amount_idx]

    def effective_click(self):
        m=self.genome.click_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("click"))
        if self.ability_actives[0]>0:
            m*=10  # DNA Storm
            return(self.click_power+self.ach_bonus_click)*m


    def effective_cps(self):
        m=self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("cps"))
        if self.ability_actives[1]>0:
            m*=10  # Time Warp
            return(self.cps+self.ach_bonus_cps)*m


    def effective_crit_chance(self):
        c=self.crit_chance+self.ach_bonus_crit
        if self.ability_actives[2]>0:
            c=1.0  # Crit Surge
            mut=self._get_mutation_mult("crit")

        if mut>0:
            c=max(c,mut/100)
            return min(c,1.0)


    def effective_crit_mult(self):
        return self.crit_mult+self.ach_bonus_crit_mult

    def _get_mutation_mult(self,mtype):
        if not self.active_mutation:
            return 0
        if self.active_mutation["mult_type"]==mtype:
            return self.active_mutation["mult_value"]-1
        if self.active_mutation["mult_type"]=="all"and mtype in("click","cps"):
            return self.active_mutation["mult_value"]-1
            return 0


    def _play(self,snd):
        if snd and self.sound_on:
            try:snd.play()
            except:pass

    def click_creature(self,mx,my):
        self.total_clicks+=1;self.combo+=1;self.combo_timer=self.combo_decay
        # Mutation combo boost
        if self.active_mutation and self.active_mutation["mult_type"]=="combo":
            self.combo=max(self.combo,int(self.active_mutation["mult_value"]))
        if self.combo>self.max_combo:
            self.max_combo=self.combo
            combo_mult=1.0+(self.combo-1)*0.1

            is_crit=random.random()<self.effective_crit_chance()

        if is_crit:
            self.total_crits+=1;combo_mult*=self.effective_crit_mult()
            earned=self.effective_click()*combo_mult

            self.dna+=earned;self.total_dna+=earned;color=self.genome.body_color(self.total_dna,self.t)

            pcount=max(1,self.particle_quality)

            if is_crit:
                for _ in range(random.randint(5,15)*pcount):
                    self.particles.append(Particle(mx,my,random.choice([GOLD,ORANGE,RED,WHITE]),lifetime=random.uniform(0.4,1.0),size=random.randint(3,9)))
                self.float_texts.append(FloatingText(mx,my-30,f"CRIT! +{fmt(earned)}",ORANGE,"lg"))
            self.shake_time=0.15;self._play(snd_crit)
        else:
            for _ in range(random.randint(2,4+min(self.combo,10))*pcount):
                self.particles.append(Particle(mx,my,color,lifetime=random.uniform(0.2,0.6),size=random.randint(2,5)))
            prefix=f"{self.combo}x "if self.combo>1 else""
            self.float_texts.append(FloatingText(mx,my-20,f"{prefix}+{fmt(earned)}",GOLD))
            self._play(snd_click)
        if self.combo>1 and self.combo%5==0:
            self._play(snd_combo)
        # Damage boss if active
        if self.boss and self.boss.alive:
            self.boss.damage(earned)
            self._play(snd_boss_hit)
            if self.boss.hp<=0:
                self.dna+=self.boss.reward;self.total_dna+=self.boss.reward
                self.float_texts.append(FloatingText(self.boss.x,self.boss.y-60,f"BOSS DEFEATED! +{fmt(self.boss.reward)}",GOLD,"lg"))
                self._play(snd_boss_die);self.bosses_defeated+=1;self.boss_tier+=1
                self._burst(self.boss.x,self.boss.y,50,[GOLD,RED,ORANGE]);self.boss=None
        self._check_achievements();self._check_milestones()

    def buy_upgrade(self,idx):
        total_cost,amount=self.upgrade_cost(idx)
        if self.dna>=total_cost and amount>0:
            self.dna-=total_cost;self.upgrade_counts[idx]+=amount;upg=UPGRADES[idx]
            if upg["type"]=="click":
                self.click_power+=upg["value"]*amount
            elif upg["type"]=="cps":self.cps+=upg["value"]*amount
            self.total_upgrades_bought+=amount;self._play(snd_buy);self._check_achievements();return True
        return False

    def activate_ability(self,idx):
        if idx>=len(ABILITIES):
            return
            ab=ABILITIES[idx]

        if not self.abilities_unlocked[idx]:
            return
        if self.ability_cooldowns[idx]>0 or self.ability_actives[idx]>0:
            return
            self.ability_actives[idx]=ab["duration"];self.ability_cooldowns[idx]=ab["cooldown"]

            self.toasts.append(Toast(f"{ab['name']}!",ab["desc"],ab["color"]))

            self._play(snd_ability);self._burst(self.creature_cx,self.creature_cy,20,[ab["color"]])


    def collect_orb(self,orb,mx,my):
        self.dna+=orb.value;self.total_dna+=orb.value;self.orbs_collected+=1;orb.alive=False
        self.float_texts.append(FloatingText(mx,my-15,f"+{fmt(orb.value)} {orb.name}",orb.color))
        for _ in range(8):
            self.particles.append(Particle(mx,my,orb.color,lifetime=0.5,size=3))
            self._play(snd_orb);self._check_achievements()


    def _start_mutation(self):
        mut=random.choice(MUTATIONS)
        self.active_mutation=mut;self.mutation_timer=mut["duration"];self.mutations_experienced+=1
        self.toasts.append(Toast(f"Mutation: {mut['name']}!",mut["desc"],mut["color"]))
        self._play(snd_mutation);self._check_achievements()

    def _grant_achievement_reward(self,ach):
        rt=ach["reward_type"];rv=ach["reward"]
        if rt=="click":
            self.ach_bonus_click+=rv
        elif rt=="cps":self.ach_bonus_cps+=rv
        elif rt=="crit_chance":self.ach_bonus_crit+=rv
        elif rt=="crit_mult":self.ach_bonus_crit_mult+=rv
        elif rt=="prestige_bonus":self.ach_bonus_prestige+=rv

    def _check_achievements(self):
        checks={"first_click":lambda:self.total_clicks>=1,"click_100":lambda:self.total_clicks>=100,
            "click_1k":lambda:self.total_clicks>=1000,"click_10k":lambda:self.total_clicks>=10000,
            "dna_100":lambda:self.total_dna>=100,"dna_10k":lambda:self.total_dna>=1e4,
            "dna_1m":lambda:self.total_dna>=1e6,"dna_1b":lambda:self.total_dna>=1e9,"dna_1t":lambda:self.total_dna>=1e12,
            "combo_5":lambda:self.max_combo>=5,"combo_20":lambda:self.max_combo>=20,"combo_50":lambda:self.max_combo>=50,
            "crit_first":lambda:self.total_crits>=1,"crit_10":lambda:self.total_crits>=10,
            "upgrade_first":lambda:self.total_upgrades_bought>=1,"upgrade_50":lambda:self.total_upgrades_bought>=50,
            "prestige_1":lambda:self.prestige_count>=1,"prestige_5":lambda:self.prestige_count>=5,
            "level_5":lambda:self.genome.level(self.total_dna)>=5,"level_10":lambda:self.genome.level(self.total_dna)>=10,
            "level_15":lambda:self.genome.level(self.total_dna)>=15,
            "cps_100":lambda:self.effective_cps()>=100,"cps_10k":lambda:self.effective_cps()>=1e4,
            "boss_1":lambda:self.bosses_defeated>=1,"boss_10":lambda:self.bosses_defeated>=10,
            "orb_50":lambda:self.orbs_collected>=50,"mutation_5":lambda:self.mutations_experienced>=5}
        for ach in ACHIEVEMENTS:
            if ach["id"]not in self.achievements_unlocked:
                chk=checks.get(ach["id"])
                if chk and chk():
                    self.achievements_unlocked.add(ach["id"]);self._grant_achievement_reward(ach)
                    self.toasts.append(Toast(f"Achievement: {ach['name']}",f"{ach['desc']} (+reward!)",GOLD))
                    self._play(snd_achieve)

    def _check_milestones(self):
        for m in self.milestones:
            if self.total_dna>=m and self.last_milestone<m:
                self.last_milestone=m;self.shake_time=0.1
                self.float_texts.append(FloatingText(self.creature_cx,self.creature_cy-100,f"MILESTONE: {fmt(m)} DNA!",CYAN,"lg"))
                self._burst(self.creature_cx,self.creature_cy,30,[GOLD,CYAN,GREEN,PINK,PURPLE])

    def _burst(self,x,y,n,colors):
        for _ in range(n):
            a=random.uniform(0,2*math.pi);sp=random.uniform(60,200)
            self.particles.append(Particle(x,y,random.choice(colors),math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.6,1.5),random.randint(3,7)))

    def update(self,dt):
        self.t+=dt;self.play_time+=dt
        # Combo decay (unless Frenzy active)
        if self.ability_actives[3]<=0:
            if self.combo_timer>0:
                self.combo_timer-=dt
                if self.combo_timer<=0:
                    self.combo=0
        # Auto DNA
        auto=self.effective_cps()*dt;self.dna+=auto;self.total_dna+=auto
        self._check_achievements();self._check_milestones()
        # Particles
        for p in self.particles:
            p.update(dt)
            self.particles=[p for p in self.particles if p.alive]

        for ft in self.float_texts:
            ft.update(dt)
            self.float_texts=[ft for ft in self.float_texts if ft.alive]

        for t in self.toasts:
            t.update(dt)
            self.toasts=[t for t in self.toasts if t.alive]

        # Shake
        if self.shake_time>0:
            self.shake_time-=dt;i=self.shake_time*40;self.shake_x=random.uniform(-i,i);self.shake_y=random.uniform(-i,i)
        else:self.shake_x=self.shake_y=0
        # Ambient
        for ap in self.ambient_particles:
            ap.update(dt)
            self.sparkline.update(dt,self.effective_cps())

        # Animated DNA
        diff=self.dna-self.display_dna;self.display_dna+=diff*min(1,dt*10)
        if abs(diff)<0.5:
            self.display_dna=self.dna
        # Auto-save
        self.autosave_timer+=dt
        if self.autosave_timer>=30:
            self.autosave_timer=0;self.save()
        # Boss timer
        if not self.boss:
            self.boss_timer-=dt
            if self.boss_timer<=0:
                self.boss=Boss(self.boss_tier,self.total_dna);self.boss_timer=random.uniform(90,180)
        else:self.boss.update(dt)
        # Orb spawning
        self.orb_timer+=dt
        if self.orb_timer>random.uniform(2,5):
            self.orb_timer=0;self.orbs.append(DNAOrb(self.total_dna))
        for orb in self.orbs:
            orb.update(dt)
            self.orbs=[o for o in self.orbs if o.alive]

        # Ability timers
        for i in range(len(ABILITIES)):
            if self.ability_actives[i]>0:
                self.ability_actives[i]=max(0,self.ability_actives[i]-dt)
            if self.ability_cooldowns[i]>0:
                self.ability_cooldowns[i]=max(0,self.ability_cooldowns[i]-dt)
                if not self.abilities_unlocked[i] and self.total_dna>=ABILITIES[i]["unlock_dna"]:
                    self.abilities_unlocked[i]=True
                    self.toasts.append(Toast(f"Ability Unlocked!",f"{ABILITIES[i]['name']} [{ABILITIES[i]['key']}]",ABILITIES[i]["color"]))
        # Mutation timer
        if self.active_mutation:
            self.mutation_timer-=dt
            if self.mutation_timer<=0:
                self.active_mutation=None
        else:
            self.mutation_event_timer-=dt
            if self.mutation_event_timer<=0:
                self._start_mutation();self.mutation_event_timer=random.uniform(60,120)

    def new_creature(self):
        self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),
            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed)

            self.renderer=CreatureRenderer(self.genome);self.seed_display=seed

            self.toasts.append(Toast("New Creature!",f"Seed: {seed}",CYAN))

            self._burst(self.creature_cx,self.creature_cy,40,[CYAN,GREEN,PINK])


    def draw(self,surface):
        mx,my=pygame.mouse.get_pos();evo_lv=self.genome.level(self.total_dna)
        # BG
        for y in range(HEIGHT):
            ratio=y/HEIGHT;ls=min(evo_lv*2,30)
            r=int((BG_TOP[0]+ls*0.3)*(1-ratio)+(BG_BOT[0]+ls*0.5)*ratio)
            g=int((BG_TOP[1]+ls*0.1)*(1-ratio)+(BG_BOT[1]+ls*0.2)*ratio)
            b=int(min(255,(BG_TOP[2]+ls*0.8)*(1-ratio)+(BG_BOT[2]+ls*0.6)*ratio))
            pygame.draw.line(surface,(min(255,r),min(255,g),min(255,b)),(0,y),(WIDTH,y))
        self.starfield.draw(surface,evo_lv,self.t)
        for ap in self.ambient_particles:
            ap.draw(surface,evo_lv)
        # Orbs (behind panels)
        for orb in self.orbs:
            orb.draw(surface)
            so=(int(self.shake_x),int(self.shake_y))

        # ── Left Panel ──
        pygame.draw.rect(surface,PANEL_BG,(15+so[0],15+so[1],620,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(15+so[0],15+so[1],620,750),2,border_radius=15)
        title=font_xl.render("Procedural Creature Clicker",True,CYAN)
        surface.blit(title,(325-title.get_width()//2+so[0],22+so[1]))
        name=self.genome.proc_name(self.total_dna);color=self.genome.body_color(self.total_dna,self.t)
        surface.blit(font_lg.render(name,True,color),(325-font_lg.size(name)[0]//2+so[0],62+so[1]))
        evo_display = evo_lv
        if self.active_mutation and self.active_mutation["mult_type"]=="evo":
            evo_display += self.active_mutation["mult_value"]
        stage_txt=font_sm.render(f"Evo Lv: {evo_display:.1f} | Prestige: {self.prestige_count} ({self.prestige_mult:.2f}x)",True,MUTED)
        surface.blit(stage_txt,(325-stage_txt.get_width()//2+so[0],90+so[1]))
        # Trait tags
        traits=[]
        gd=self.genome
        if gd.limb_count(self.total_dna)>0:
            traits.append(f"{gd.limb_count(self.total_dna)} {gd.limb_style}")
        if gd.has_wings(self.total_dna):
            traits.append(f"{gd.wing_style} wings")
        if gd.eye_count(self.total_dna)>2:
            traits.append(f"{gd.eye_count(self.total_dna)} {gd.eye_style}")
        if gd.has_horns(self.total_dna):
            traits.append(f"{gd.horn_count(self.total_dna)} {gd.horn_style}")
        if gd.tail_length(self.total_dna)>0:
            traits.append(f"{gd.tail_style} tail")
        if gd.has_pattern(self.total_dna):
            traits.append(gd.pattern_type)
        if gd.has_aura(self.total_dna):
            traits.append(f"{gd.aura_style} aura")
        if traits:
            tt=font_xs.render(" | ".join(traits[:6]),True,DIM);surface.blit(tt,(325-tt.get_width()//2+so[0],108+so[1]))
        # Mutation banner
        if self.active_mutation:
            mut=self.active_mutation;flash=(math.sin(self.t*6)+1)*0.5
            mc=tuple(int(min(255,c*(0.6+0.4*flash)))for c in mut["color"])
            mt=font_md.render(f"MUTATION: {mut['name']} ({self.mutation_timer:.0f}s)",True,mc)
            surface.blit(mt,(325-mt.get_width()//2+so[0],125+so[1]))
        # Boss
        if self.boss and self.boss.alive:
            self.boss.draw(surface,self.t)
        else:
            # Creature
            dist=math.sqrt((mx-self.creature_cx)**2+(my-self.creature_cy)**2)
            bsize=self.genome.body_size(self.total_dna)
            self.creature_hover=dist<bsize*1.5 and not self.show_traits and not self.show_bestiary and not self.show_stats and not self.show_settings and not self.show_achievements_panel
            self.renderer.draw(surface,self.creature_cx+so[0],self.creature_cy+so[1],self.total_dna,self.t,self.creature_hover)
            if self.creature_hover:
                hint=font_sm.render("Click me!",True,WHITE);surface.blit(hint,(self.creature_cx-hint.get_width()//2,int(self.creature_cy+bsize+15)))
        for p in self.particles:
            p.draw(surface)
        for ft in self.float_texts:
            ft.draw(surface)
        # DNA + Combo
        dna_txt=font_xl.render(f"{fmt(self.display_dna)}",True,GOLD);surface.blit(dna_txt,(325-dna_txt.get_width()//2,490))
        if self.combo>1:
            cc=ORANGE if self.combo<10 else RED if self.combo<30 else PURPLE
            ct=font_lg.render(f"COMBO x{self.combo}",True,cc);surface.blit(ct,(325-ct.get_width()//2,468))
            bw=min(200,200*(self.combo_timer/self.combo_decay))
            pygame.draw.rect(surface,DARK_PURPLE,(225,493,200,4),border_radius=2)
            if bw>0:
                pygame.draw.rect(surface,cc,(225,493,int(bw),4),border_radius=2)
        surface.blit(font_md.render("DNA Points",True,MUTED),(325-font_md.size("DNA Points")[0]//2,525))
        # Stats line
        sl=f"Click: {fmt(self.effective_click())} | CPS: {fmt(self.effective_cps())} | Crit: {self.effective_crit_chance()*100:.0f}% | Bosses: {self.bosses_defeated}"
        surface.blit(font_xs.render(sl,True,MUTED),(325-font_xs.size(sl)[0]//2,550))
        sl2=f"Total: {fmt(self.total_dna)} | Clicks: {self.total_clicks} | Orbs: {self.orbs_collected} | Mutations: {self.mutations_experienced}"
        surface.blit(font_xs.render(sl2,True,DIM),(325-font_xs.size(sl2)[0]//2,565))
        # Sparkline
        self.sparkline.draw(surface,195,585,260,32,CYAN)
        # Ability bar
        ab_y=625
        surface.blit(font_xs.render("Abilities:",True,MUTED),(30,ab_y+2))
        for i,ab in enumerate(ABILITIES):
            ax=110+i*120;aw=110;ah=36;ar=pygame.Rect(ax,ab_y,aw,ah)
            unlocked=self.abilities_unlocked[i]
            on=self.ability_actives[i]>0;cd=self.ability_cooldowns[i]>0
            if on:
                ac=(40,80,40);bc=GREEN
            elif cd:ac=(30,25,50);bc=DIM
            elif unlocked:ac=(35,50,90);bc=ab["color"]
            else:ac=(20,18,35);bc=(40,35,60)
            pygame.draw.rect(surface,ac,ar,border_radius=6);pygame.draw.rect(surface,bc,ar,1,border_radius=6)
            # Cooldown overlay
            if cd and unlocked:
                cdr=self.ability_cooldowns[i]/ab["cooldown"]
                ch=int(ah*cdr)
                if ch>0:
                    cs=pygame.Surface((aw,ch),pygame.SRCALPHA);cs.fill((0,0,0,100));surface.blit(cs,(ax,ab_y))
                    cd_txt=font_xxs.render(f"{self.ability_cooldowns[i]:.0f}s",True,WHITE);surface.blit(cd_txt,(ax+aw//2-cd_txt.get_width()//2,ab_y+ah//2-cd_txt.get_height()//2))

            elif on:
                on_txt=font_xxs.render(f"{self.ability_actives[i]:.1f}s",True,GREEN);surface.blit(on_txt,(ax+aw//2-on_txt.get_width()//2,ab_y+ah//2-on_txt.get_height()//2))
            tc=WHITE if unlocked else DIM
            nt=font_xs.render(f"[{ab['key']}] {ab['name']}",True,tc);surface.blit(nt,(ax+4,ab_y+3))
            dt_txt=font_xxs.render(ab["desc"] if unlocked else f"Unlock: {fmt(ab['unlock_dna'])} DNA",True,MUTED if unlocked else (50,45,80))
            surface.blit(dt_txt,(ax+4,ab_y+19))
        # Trait detail panel
        if self.show_traits:
            self._draw_trait_panel(surface,so)
        # Other panels
        if self.show_bestiary:
            self._draw_bestiary(surface,so)
        if self.show_stats:
            self._draw_stats(surface,so)
        if self.show_settings:
            self._draw_settings(surface,so)
        if self.show_achievements_panel:
            self._draw_achievements_panel(surface,so)
        # ── Right Panel: Shop ──
        pygame.draw.rect(surface,PANEL_BG,(650,15,435,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(650,15,435,750),2,border_radius=15)
        surface.blit(font_lg.render("Upgrades",True,CYAN),(867-font_lg.size("Upgrades")[0]//2,22))
        surface.blit(font_sm.render(f"DNA: {fmt(self.dna)}",True,GOLD),(665,52))
        # Buy amount
        surface.blit(font_xs.render("Buy:",True,MUTED),(830,55))
        for bi,bl in enumerate(BUY_LABELS):
            bx=865+bi*38;sel=bi==self.buy_amount_idx;bc=GREEN if sel else(40,35,80)
            pygame.draw.rect(surface,bc,(bx,52,34,16),border_radius=4)
            if sel:
                pygame.draw.rect(surface,WHITE,(bx,52,34,16),1,border_radius=4)
                surface.blit(font_xs.render(bl,True,WHITE if sel else DIM),(bx+17-font_xs.size(bl)[0]//2,53))

        # Upgrade list
        clip=pygame.Rect(655,74,425,500);surface.set_clip(clip);self.max_scroll=max(0,len(UPGRADES)*46-490)
        self.hovered_upgrade=-1
        for i,upg in enumerate(UPGRADES):
            tc,am=self.upgrade_cost(i);ca=self.dna>=tc and am>0;by=80+i*46-self.shop_scroll
            if 70<by<575:
                r=pygame.Rect(665,by,405,40);hov=r.collidepoint(mx,my)
                if hov:
                    self.hovered_upgrade=i
                    c=(40,35,90)if ca else(18,16,42)

                if ca and hov:
                    c=(55,48,110)
                    pygame.draw.rect(surface,c,r,border_radius=8);pygame.draw.rect(surface,GREEN if ca else DIM,r,1,border_radius=8)

                    key=upg.get("key","")

                if key:
                    surface.blit(font_xs.render(f"[{key}]",True,DIM),(r.x+5,r.y+4))
                    surface.blit(font_sm.render(f"{upg['name']} (x{self.upgrade_counts[i]})",True,WHITE if ca else DIM),(r.x+30,r.y+2))

                    surface.blit(font_xs.render(upg["desc"],True,MUTED if ca else(50,45,80)),(r.x+30,r.y+21))

                    cs=fmt(tc)

                if am>1:
                    cs+=f" (x{am})"
                    surface.blit(font_sm.render(cs,True,GREEN if ca else RED),(r.right-font_sm.size(cs)[0]-8,r.y+11))

        surface.set_clip(None)
        if self.max_scroll>0:
            sr=self.shop_scroll/self.max_scroll;bh=max(20,int(500*(500/(500+self.max_scroll))))
            pygame.draw.rect(surface,DIM,(1072,82+int(sr*(490-bh)),4,bh),border_radius=2)
        # Progress
        py_=590;next_m=None
        for m in self.milestones:
            if self.total_dna<m:
                next_m=m;break
        if not next_m:
            next_m=self.milestones[-1]*10
            pygame.draw.rect(surface,DARK_PURPLE,(665,py_,410,10),border_radius=5)

            prev_m=self.milestones[max(0,self.milestones.index(next_m)-1)]if next_m in self.milestones else 0

            prog=min(1,max(0,(self.total_dna-prev_m)/(next_m-prev_m)))if next_m>prev_m else 1

            fw=int(410*prog)

            if fw>0:
                for px in range(fw):
                    ratio=px/410;c=(int(60+120*ratio),int(40+180*ratio),int(180+75*ratio))
                pygame.draw.line(surface,c,(665+px,py_),(665+px,py_+9))

        pygame.draw.rect(surface,PANEL_BORDER,(665,py_,410,10),1,border_radius=5)
        surface.blit(font_xxs.render(f"Next: {fmt(next_m)} ({prog*100:.1f}%)",True,MUTED),(667,py_+12))
        # Buttons
        can_prestige=self.total_dna>=1e6
        pb=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige if can_prestige else 0
        pr=pygame.Rect(665,620,130,28);ph=pr.collidepoint(mx,my)
        pygame.draw.rect(surface,(150,30,30)if can_prestige else DARK_RED,pr,border_radius=5)
        pygame.draw.rect(surface,RED if can_prestige else DIM,pr,1,border_radius=5)
        surface.blit(font_sm.render(f"Prestige [P]"if can_prestige else"Prestige (1M)",True,WHITE if can_prestige else DIM),
            (pr.centerx-font_sm.size(f"Prestige [P] +{pb:.1f}x"if can_prestige else"Prestige (1M)")[0]//2,pr.centery-7))
        nr=pygame.Rect(800,620,130,28)
        pygame.draw.rect(surface,(50,80,150)if nr.collidepoint(mx,my)else(35,55,110),nr,border_radius=5)
        pygame.draw.rect(surface,CYAN,nr,1,border_radius=5)
        surface.blit(font_sm.render("New [N]",True,WHITE),(nr.centerx-25,nr.centery-7))
        br=pygame.Rect(935,620,140,28)
        pygame.draw.rect(surface,(50,50,100)if br.collidepoint(mx,my)else(30,28,65),br,border_radius=5)
        pygame.draw.rect(surface,PANEL_BORDER,br,1,border_radius=5)
        surface.blit(font_sm.render("Bestiary [B]",True,WHITE),(br.centerx-38,br.centery-7))
        # Bottom bar
        bb=pygame.Rect(665,660,410,24)
        pygame.draw.rect(surface,(30,28,65),bb,border_radius=4);pygame.draw.rect(surface,PANEL_BORDER,bb,1,border_radius=4)
        bt="[T]raits [D]stats [A]achieve [M]settings [S]save [Tab]buy"
        surface.blit(font_xxs.render(bt,True,MUTED),(bb.centerx-font_xxs.size(bt)[0]//2,bb.centery-5))
        # Bottom info
        info=f"Achievements: {len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)} | Time: {int(self.play_time//3600)}h{int(self.play_time%3600//60)}m | Autosave 30s"
        surface.blit(font_xxs.render(info,True,DIM),(325-font_xxs.size(info)[0]//2,HEIGHT-15))
        # Tooltip
        if self.hovered_upgrade>=0:
            self._draw_tooltip(surface,self.hovered_upgrade,mx,my)
        # Toasts
        for i,toast in enumerate(self.toasts):
            toast.draw(surface,i)

    def _draw_trait_panel(self,s,so):
        px,py,pw,ph=25,150,610,280
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,230),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*PANEL_BORDER,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        gd=self.genome;td=self.total_dna;rows=[
            ("Body Size",f"{gd.body_size(td):.1f}"),("Segments",f"{gd.body_segments(td)}"),
            ("Eyes",f"{gd.eye_count(td)} ({gd.eye_style})"),("Limbs",f"{gd.limb_count(td)} ({gd.limb_style})"),
            ("Wings",f"{gd.wing_size(td):.0f} ({gd.wing_style})"if gd.has_wings(td)else"None"),
            ("Tail",f"{gd.tail_length(td):.0f} ({gd.tail_style})"),
            ("Horns",f"{gd.horn_count(td)} ({gd.horn_style})"if gd.has_horns(td)else"None"),
            ("Pattern",f"{gd.pattern_type}"if gd.has_pattern(td)else"None"),
            ("Aura",f"{gd.aura_style}"if gd.has_aura(td)else"None"),
            ("Click Mult",f"{gd.click_multiplier(td):.2f}x"),("CPS Mult",f"{gd.cps_multiplier(td):.2f}x"),
            ("Prestige",f"{self.prestige_mult:.2f}x"),("Ach Bonus Click",f"+{self.ach_bonus_click}"),
            ("Ach Bonus CPS",f"+{self.ach_bonus_cps}"),("Crit Chance",f"{self.effective_crit_chance()*100:.1f}%"),
            ("Crit Mult",f"{self.effective_crit_mult():.1f}x"),
        ]
        cols=3;cw=pw//cols
        for idx,(label,val)in enumerate(rows):
            col=idx%cols;row=idx//cols;x=px+10+col*cw+so[0];y=py+8+row*17+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+font_xs.size(label+":")[0]+4,y))

    def _draw_bestiary(self,s,so):
        px,py,pw,ph=50,80,560,580
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*CYAN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Bestiary",True,CYAN),(px+pw//2-font_lg.size("Bestiary")[0]//2+so[0],py+10+so[1]))
        if not self.bestiary:
            surface.blit(font_sm.render("No creatures yet! Prestige or press N to add entries.",True,MUTED),(px+20+so[0],py+50+so[1]))
        else:
            for i,entry in enumerate(sorted(self.bestiary,key=lambda e:
                e.get("total_dna",0),reverse=True)):
                if i>15:
                    break;ey=py+45+i*32+so[1];ex=px+15+so[0]
                # Mini creature name
                surface.blit(font_sm.render(f"{entry.get('name','?')}",True,GOLD),(ex,ey))
                tr=entry.get("traits",{})
                parts=[f"{tr.get('limbs','?')} limbs",f"{tr.get('eyes','?')} eyes",f"{tr.get('tail','?')} tail",f"Lv {tr.get('level','?')}"]
                surface.blit(font_xs.render(" | ".join(parts),True,MUTED),(ex,ey+15))
                surface.blit(font_xs.render(f"DNA: {fmt(entry.get('total_dna',0))} | Prestige #{entry.get('prestige','?')}",True,DIM),(ex+350,ey+7))

    def _draw_stats(self,s,so):
        px,py,pw,ph=50,80,560,500
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GREEN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Statistics",True,GREEN),(px+pw//2-font_lg.size("Statistics")[0]//2+so[0],py+10+so[1]))
        hrs=int(self.play_time//3600);mins=int(self.play_time%3600//60);secs=int(self.play_time%60)
        cps_v=self.effective_cps();click_v=self.effective_click()
        rows=[
            ("Play Time",f"{hrs}h {mins}m {secs}s"),("Total DNA Earned",fmt(self.total_dna)),
            ("Current DNA",fmt(self.dna)),("Total Clicks",f"{self.total_clicks:,}"),
            ("Click Rate",f"{self.total_clicks/max(1,self.play_time):.1f}/s" if self.play_time>1 else "N/A"),
            ("Per Click",fmt(click_v)),("Per Second",fmt(cps_v)),
            ("Total Crits",f"{self.total_crits:,} ({self.total_crits/max(1,self.total_clicks)*100:.1f}%)" if self.total_clicks>0 else "0"),
            ("Max Combo",f"{self.max_combo}x"),("Upgrades Bought",f"{self.total_upgrades_bought:,}"),
            ("Prestige Count",f"{self.prestige_count}"),("Prestige Mult",f"{self.prestige_mult:.2f}x"),
            ("Bosses Defeated",f"{self.bosses_defeated}"),("Boss Tier",f"{self.boss_tier}"),
            ("Orbs Collected",f"{self.orbs_collected}"),("Mutations",f"{self.mutations_experienced}"),
            ("Achievement Bonus Click",f"+{self.ach_bonus_click}"),("Achievement Bonus CPS",f"+{self.ach_bonus_cps}"),
            ("Achievement Bonus Crit",f"+{self.ach_bonus_crit*100:.1f}%"),
            ("Creature Seed",self.seed_display),
        ]
        for idx,(label,val)in enumerate(rows):
            col=idx%2;row=idx//2;x=px+15+col*280+so[0];y=py+42+row*21+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+140,y))

    def _draw_settings(self,s,so):
        px,py,pw,ph=200,100,350,350
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*ORANGE,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Settings",True,ORANGE),(px+pw//2-font_lg.size("Settings")[0]//2+so[0],py+10+so[1]))
        mx,my=pygame.mouse.get_pos()
        # Sound toggle
        sr=pygame.Rect(px+20+so[0],py+50+so[1],150,30);sh=sr.collidepoint(mx,my)
        pygame.draw.rect(surface,(40,80,40)if self.sound_on else(80,30,30)if sh else DARK_RED,sr,border_radius=5)
        surface.blit(font_sm.render(f"Sound: {'ON' if self.sound_on else 'OFF'}",True,WHITE),(sr.x+10,sr.y+7))
        # Particle quality
        for qi,ql in enumerate(["Low","Med","High"]):
            qr=pygame.Rect(px+20+qi*105+so[0],py+95+so[1],95,30)
            qs=qi==self.particle_quality;qh=qr.collidepoint(mx,my)
            pygame.draw.rect(surface,(50,50,100)if(qs or qh)else(30,28,60),qr,border_radius=5)
            if qs:
                pygame.draw.rect(surface,WHITE,qr,1,border_radius=5)
                surface.blit(font_sm.render(f"Particles: {ql}",True,WHITE if qs else MUTED),(qr.x+5,qr.y+7))

        # Reset button
        rr=pygame.Rect(px+20+so[0],py+145+so[1],150,30)
        pygame.draw.rect(surface,(120,30,30)if rr.collidepoint(mx,my)else DARK_RED,rr,border_radius=5)
        surface.blit(font_sm.render("Reset Save [X]",True,RED if rr.collidepoint(mx,my)else DIM),(rr.x+10,rr.y+7))
        # Info
        lines=["Controls:","[Q/W/E/R] Activate abilities","[1-0] Buy upgrades",
               "[P] Prestige  [N] New creature","[B] Bestiary  [T] Traits",
               "[D] Stats  [A] Achievements","[M] Settings  [S] Save",
               "[Tab] Cycle buy amount","[X in Settings] Reset save","[ESC] Quit"]
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,MUTED if i>0 else WHITE),(px+20+so[0],py+190+i*16+so[1]))

    def _draw_achievements_panel(self,s,so):
        px,py,pw,ph=30,50,600,620
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GOLD,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})",True,GOLD),
            (px+pw//2-font_lg.size(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})")[0]//2+so[0],py+8+so[1]))
        clip=pygame.Rect(px+5,py+35,pw-10,ph-40);surface.set_clip(clip)
        for i,ach in enumerate(ACHIEVEMENTS):
            unlocked=ach["id"]in self.achievements_unlocked;ay=py+38+i*22
            if ay<py+30 or ay>py+ph-10:
                continue
                c=GOLD if unlocked else(40,35,60)

                icon="*"if unlocked else "o"

                surface.blit(font_xs.render(f"[{icon}] {ach['name']}",True,WHITE if unlocked else DIM),(px+15+so[0],ay+so[1]))

                surface.blit(font_xxs.render(f"{ach['desc']} | Reward: +{ach['reward']} {ach['reward_type']}",True,MUTED if unlocked else(50,45,70)),(px+200+so[0],ay+2+so[1]))

        surface.set_clip(None)

    def _draw_tooltip(self,surface,idx,mx,my):
        upg=UPGRADES[idx];tc,am=self.upgrade_cost(idx);lines=[upg["name"],upg["desc"],
            f"Type: {upg['type'].upper()}",f"Cost mult: x{upg['cost_mult']}/lv",
            f"Owned: {self.upgrade_counts[idx]}",f"Cost ({am}): {fmt(tc)}"]
        if upg["type"]=="click":
            nv=self.effective_click()+upg["value"]*am*self.genome.click_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"Click after: {fmt(nv)}")
        else:
            nv=self.effective_cps()+upg["value"]*am*self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"CPS after: {fmt(nv)}")
        tw=max(font_xs.size(l)[0]for l in lines)+16;th=len(lines)*15+10
        tx=min(mx+15,WIDTH-tw-5);ty=min(my+15,HEIGHT-th-5)
        tip=pygame.Surface((tw,th),pygame.SRCALPHA);pygame.draw.rect(tip,(10,8,30,230),(0,0,tw,th),border_radius=6)
        pygame.draw.rect(tip,(*PANEL_BORDER,200),(0,0,tw,th),1,border_radius=6);surface.blit(tip,(tx,ty))
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,GOLD if i==0 else MUTED),(tx+8,ty+5+i*15))


def fmt(n):
    if n<0:
        return"-"+fmt(-n)
    if n<1000:
        return f"{n:.1f}"if isinstance(n,float)and n!=int(n)else str(int(n))
        sfx=["","K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc"];t=0

    while n>=1000 and t<len(sfx)-1:
        n/=1000;t+=1
        return f"{n:.0f}{sfx[t]}"if n>=100 else f"{n:.1f}{sfx[t]}"if n>=10 else f"{n:.2f}{sfx[t]}"



# ─────────────── MAIN ───────────────
def main():
    game=Game();running=True
    while running:
        dt=clock.tick(60)/1000;dt=min(dt,0.05);mx,my=pygame.mouse.get_pos()
        close_panels=lambda:any([game.show_traits,game.show_bestiary,game.show_stats,game.show_settings,game.show_achievements_panel])
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                game.save();running=False
            elif event.type==pygame.KEYDOWN:
                k=event.key
                if k==pygame.K_ESCAPE:
                    if close_panels():
                        game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                    else:game.save();running=False
                elif k==pygame.K_s:game.save();game.toasts.append(Toast("Saved!","Game saved",GREEN))
                elif k==pygame.K_p:game.prestige()
                elif k==pygame.K_n:game.new_creature()
                elif k==pygame.K_t:game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_b:game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_d:game.show_stats=not game.show_stats;game.show_traits=game.show_bestiary=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_a:game.show_achievements_panel=not game.show_achievements_panel;game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=False
                elif k==pygame.K_m:game.show_settings=not game.show_settings;game.show_traits=game.show_bestiary=game.show_stats=game.show_achievements_panel=False
                elif k==pygame.K_TAB:game.buy_amount_idx=(game.buy_amount_idx+1)%len(BUY_AMOUNTS)
                elif k==pygame.K_q:game.activate_ability(0)
                elif k==pygame.K_w:game.activate_ability(1)
                elif k==pygame.K_e:game.activate_ability(2)
                elif k==pygame.K_r:game.activate_ability(3)
                km={pygame.K_1:0,pygame.K_2:1,pygame.K_3:2,pygame.K_4:3,pygame.K_5:4,pygame.K_6:5,pygame.K_7:6,pygame.K_8:7,pygame.K_9:8,pygame.K_0:9}
                if k in km:
                    game.buy_upgrade(km[k])
            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==1:
                    # Check orbs first
                    for orb in game.orbs:
                        if orb.alive and orb.hit_test(mx,my):
                            game.collect_orb(orb,mx,my);break
                    else:
                        if game.creature_hover and not close_panels():
                            game.click_creature(mx,my)
                            for i in range(len(UPGRADES)):
                                by=80+i*46-game.shop_scroll;r=pygame.Rect(665,by,405,40)
                                if r.collidepoint(mx,my):
                                    game.buy_upgrade(i)
                        for bi in range(len(BUY_LABELS)):
                            if pygame.Rect(865+bi*38,52,34,16).collidepoint(mx,my):
                                game.buy_amount_idx=bi
                        if pygame.Rect(665,620,130,28).collidepoint(mx,my):
                            game.prestige()
                        if pygame.Rect(800,620,130,28).collidepoint(mx,my):
                            game.new_creature()
                        if pygame.Rect(935,620,140,28).collidepoint(mx,my):
                            game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        if pygame.Rect(665,660,410,24).collidepoint(mx,my):
                            game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        # Settings panel clicks
                        if game.show_settings:
                            spx,spy=200+int(game.shake_x),100+int(game.shake_y)
                            if pygame.Rect(spx+20,spy+50,150,30).collidepoint(mx,my):
                                game.sound_on=not game.sound_on
                                for qi in range(3):
for                                f pygame.Rect(spx+20+qi*105,spy+95,95,30).collidepoint(mx,my):

                                    game.particle_quality=qi
                            if pygame.Rect(spx+20,spy+145,150,30).collidepoint(mx,my):
                                if os.path.exists(SAVE_FILE):
                                    os.remove(SAVE_FILE)
                                    game.toasts.append(Toast("Reset!","Save file deleted. Restart to start fresh.",RED))

                        # Ability bar clicks
                        for ai in range(len(ABILITIES)):
                            ar=pygame.Rect(110+ai*120,625,110,36)
                            if ar.collidepoint(mx,my):
                                game.activate_ability(ai)
                elif event.button==4:game.shop_scroll=max(0,game.shop_scroll-40)
                elif event.button==5:game.shop_scroll=min(game.max_scroll,game.shop_scroll+40)
        # Ambient particles
        if game.effective_cps()>0 and random.random()<dt*2*game.particle_quality:
            a=random.uniform(0,2*math.pi);d=random.uniform(40,80)
            c=game.genome.accent_color(game.total_dna,game.t)
            game.particles.append(Particle(game.creature_cx+math.cos(a)*d,game.creature_cy+math.sin(a)*d*0.7,c,random.uniform(-15,15),random.uniform(-35,-10),0.5,random.randint(2,4)))
        game.update(dt);game.draw(screen);pygame.display.flip()
    pygame.quit();sys.exit()

if __name__=="__main__":

    main()

/usr/bin/env python3
"""
Procedural Creature Clicker v3
Boss fights, falling orbs, active abilities, mutations, bestiary, stats, settings, and more!
"""

import pygame, sys, math, random, hashlib, colorsys, json, os, time, array

# ─────────────── INIT ───────────────
pygame.init()
SOUND_ENABLED = False
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    SOUND_ENABLED = True
except Exception:
    pass
WIDTH, HEIGHT = 1100, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Procedural Creature Clicker v3")
clock = pygame.time.Clock()
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "creature_save.json")

# ─────────────── COLORS ───────────────
BG_TOP = (12, 10, 35); BG_BOT = (40, 35, 85); PANEL_BG = (22, 20, 55)
PANEL_BORDER = (75, 65, 150); WHITE = (255, 255, 255); GOLD = (255, 215, 0)
CYAN = (0, 230, 255); GREEN = (80, 255, 120); RED = (255, 80, 80)
ORANGE = (255, 160, 50); PURPLE = (180, 100, 255); PINK = (255, 120, 200)
DARK_PURPLE = (55, 38, 110); MUTED = (155, 150, 195); DIM = (95, 90, 135)
DARK_RED = (120, 20, 20); YELLOW = (255, 255, 80); DARK_GREEN = (20, 80, 30)

# ─────────────── FONTS ───────────────
font_xl = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 36, bold=True)
font_lg = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 24, bold=True)
font_md = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 18)
font_sm = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 14)
font_xs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 11)
font_xxs = pygame.font.SysFont("segoeuisymbol,notosanssc,arial", 9)

# ─────────────── PROCEDURAL SOUND ───────────────
def make_sound(freq=440, duration=0.08, volume=0.12, wave="sine"):
    try:
        sr = 22050; ns = int(sr * duration); buf = array.array('h')
        for i in range(ns):
            t = i / sr; env = min(1.0, min(i/(sr*0.005), (ns-i)/(sr*0.01)))
            v = math.sin(2*math.pi*freq*t) if wave=="sine" else (1.0 if math.sin(2*math.pi*freq*t)>0 else -1.0) if wave=="square" else random.uniform(-1,1)
            buf.append(max(-32767, min(32767, int(v*volume*env*32767))))
        return pygame.mixer.Sound(buffer=buf)
    except: return None

snd_click = make_sound(520,0.06,0.10,"sine"); snd_crit = make_sound(880,0.15,0.15,"square")
snd_buy = make_sound(660,0.08,0.08,"sine"); snd_achieve = make_sound(1047,0.25,0.12,"sine")
snd_combo = make_sound(700,0.05,0.06,"sine"); snd_prestige = make_sound(440,0.5,0.15,"sine")
snd_orb = make_sound(1200,0.1,0.08,"sine"); snd_ability = make_sound(660,0.3,0.12,"sine")
snd_boss_hit = make_sound(300,0.1,0.10,"square"); snd_boss_die = make_sound(200,0.4,0.15,"noise")
snd_mutation = make_sound(500,0.2,0.10,"sine")

def play(snd):
    if snd:
        try: snd.play()
        except: pass

# ─────────────── SEEDED RNG ───────────────
class SeededRNG:
    def __init__(self, seed_str="default"):
        h = hashlib.sha256(seed_str.encode()).digest()
        self.state = int.from_bytes(h[:8], 'big'); self.pool = []; self._refill()
    def _refill(self):
        for _ in range(256):
            self.state = (self.state*6364136223846793005+1442695040888963407)&0xFFFFFFFFFFFFFFFF
            self.pool.append(((self.state>>16)&0xFFFFFFFF)/0xFFFFFFFF)
    def next(self):
        if not self.pool:
            self._refill()
            return self.pool.pop(0)

    def rand(self,lo,hi): return lo+self.next()*(hi-lo)
    def randint(self,lo,hi): return int(self.next()*(hi-lo+1))+lo
    def choice(self,lst): return lst[self.randint(0,len(lst)-1)]

# ─────────────── GENOME ───────────────
class Genome:
    def __init__(self, seed="creature_1"):
        self.seed=seed; self.rng=SeededRNG(seed)
        self.hue_offset=self.rng.rand(0,1); self.hue_speed=self.rng.rand(0.02,0.08)
        self.body_width_ratio=self.rng.rand(0.85,1.15)
        self.limb_style=self.rng.choice(["stubby","spindly","tentacle","crab"])
        self.wing_style=self.rng.choice(["feathered","bat","crystal","insect"])
        self.tail_style=self.rng.choice(["curved","spiked","forked","flame","tentacle"])
        self.eye_style=self.rng.choice(["round","slit","compound","cyclops"])
        self.pattern_type=self.rng.choice(["spots","stripes","rings","scales","none"])
        self.horn_style=self.rng.choice(["pointed","curved","crystal","antler"])
        self.mouth_style=self.rng.choice(["smile","teeth","beak","tentacles","lamprey"])
        self.aura_style=self.rng.choice(["glow","sparks","rings","dna_helix","constellation"])
        self.ear_type=self.rng.choice(["none","pointed","frilled","antenna"])
        self.leg_count_bias=self.rng.choice([2,4,6,8])
    def level(self,td):
        return 0 if td<=0 else math.log10(td+1)*2.5
    def body_size(self,td): return 30+min(self.level(td),12)*4.2
    def body_segments(self,td): return 1+int(min(self.level(td),10)/2.5)
    def body_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+lv*self.hue_speed+t*0.02)%1.0
        sat=0.5+min(lv,8)*0.05; val=0.6+min(lv,10)*0.03
        r,g,b=colorsys.hsv_to_rgb(hue,min(sat,0.95),min(val,0.95))
        return(int(r*255),int(g*255),int(b*255))
    def accent_color(self,td,t):
        lv=self.level(td); hue=(self.hue_offset+0.4+lv*self.hue_speed*0.7+t*0.015)%1.0
        r,g,b=colorsys.hsv_to_rgb(hue,0.7,0.8); return(int(r*255),int(g*255),int(b*255))
    def eye_count(self,td): return 1 if self.eye_style=="cyclops" else min(2+int(self.level(td)/3),8)
    def eye_size(self,td): return 5+min(self.level(td),8)*1.2
    def limb_count(self,td):
        lv=self.level(td); return 0 if lv<1.5 else min(self.leg_count_bias,int(lv/1.5)*2)
    def limb_length(self,td): return min(self.level(td),8)*6
    def has_wings(self,td): return self.level(td)>=4.0
    def wing_size(self,td): return 0 if not self.has_wings(td) else min((self.level(td)-4.0)*12,80)
    def tail_length(self,td):
        lv=self.level(td); return 0 if lv<1.0 else min((lv-1.0)*15,120)
    def spike_count(self,td): return int(min(self.level(td),10)*0.8)
    def spike_size(self,td): lv=self.level(td); return 0 if lv<2 else min((lv-2)*3,25)
    def has_pattern(self,td): return self.level(td)>=3.0 and self.pattern_type!="none"
    def pattern_opacity(self,td): return 0 if not self.has_pattern(td) else min((self.level(td)-3.0)/3.0,1.0)
    def has_aura(self,td): return self.level(td)>=5.5
    def aura_intensity(self,td): return 0 if not self.has_aura(td) else min((self.level(td)-5.5)/4.0,1.0)
    def has_horns(self,td): return self.level(td)>=3.5
    def horn_count(self,td): return 0 if not self.has_horns(td) else min(int((self.level(td)-3.5)*1.5)+1,6)
    def horn_size(self,td): return 0 if not self.has_horns(td) else min((self.level(td)-3.5)*5,35)
    def mouth_complexity(self,td): return min(self.level(td)/8.0,1.0)
    def has_ears(self,td): return self.ear_type!="none" and self.level(td)>=2.0
    def ear_size(self,td): return 0 if not self.has_ears(td) else min((self.level(td)-2.0)*5,30)
    def bioluminescence(self,td): return min(self.level(td)/12.0,1.0)
    def proc_name(self,td):
        lv=self.level(td)
        pf=["Proto","Nano","Micro","Alpha","Beta","Gamma","Mega","Giga","Ultra","Hyper","Nova","Cosmic","Elder","Ancient","Omega"]
        bd=["Spore","Cell","Blob","Flop","Wurm","Crawler","Slinker","Lurker","Stalker","Drake","Wyrm","Serpent","Leviathan","Titan","Colossus","Behemoth"]
        sf=["ling","ite","us","ax","on","ix","ar","oth","ius","os","ux","ath","eon","ion","ium","or"]
        return f"{pf[min(int(lv/1.2),len(pf)-1)]}{bd[min(int(lv/1.0),len(bd)-1)]}{sf[min(int(lv/2.0),len(sf)-1)]}"
    def click_multiplier(self,td): return 1+self.level(td)*0.4
    def cps_multiplier(self,td): return 1+self.level(td)*0.3
    def to_dict(self):
        return {k:getattr(self,k) for k in ["seed","hue_offset","hue_speed","body_width_ratio",
            "limb_style","wing_style","tail_style","eye_style","pattern_type","horn_style",
            "mouth_style","aura_style","ear_type","leg_count_bias"]}
    @classmethod
    def from_dict(cls,d):
        g=cls.__new__(cls); g.seed=d["seed"]; g.rng=SeededRNG(g.seed)
        for k in ["hue_offset","hue_speed","body_width_ratio","limb_style","wing_style","tail_style",
                   "eye_style","pattern_type","horn_style","mouth_style","aura_style","ear_type","leg_count_bias"]:
            setattr(g,k,d[k])
        return g
Genome.has_wings_at_level=lambda s,lv:lv>=4.0; Genome.has_horns_at_level=lambda s,lv:lv>=3.5
Genome.has_aura_at_level=lambda s,lv:lv>=5.5; Genome.has_pattern_at_level=lambda s,lv:lv>=3.0

# ─────────────── ACHIEVEMENTS (with rewards) ───────────────
ACHIEVEMENTS = [
    {"id":"first_click","name":"First Contact","desc":"Click the creature","reward_type":"click","reward":1},
    {"id":"click_100","name":"Clicker","desc":"Click 100 times","reward_type":"click","reward":2},
    {"id":"click_1k","name":"Click Master","desc":"Click 1,000 times","reward_type":"click","reward":5},
    {"id":"click_10k","name":"Click Legend","desc":"Click 10,000 times","reward_type":"click","reward":20},
    {"id":"dna_100","name":"DNA Collector","desc":"Earn 100 total DNA","reward_type":"cps","reward":1},
    {"id":"dna_10k","name":"Gene Hoarder","desc":"Earn 10K total DNA","reward_type":"cps","reward":5},
    {"id":"dna_1m","name":"Biotech Baron","desc":"Earn 1M total DNA","reward_type":"click","reward":50},
    {"id":"dna_1b","name":"Genome God","desc":"Earn 1B total DNA","reward_type":"cps","reward":200},
    {"id":"dna_1t","name":"Singularity","desc":"Earn 1T total DNA","reward_type":"click","reward":5000},
    {"id":"combo_5","name":"Combo Starter","desc":"Reach 5x combo","reward_type":"crit_chance","reward":0.01},
    {"id":"combo_20","name":"Combo Frenzy","desc":"Reach 20x combo","reward_type":"crit_chance","reward":0.02},
    {"id":"combo_50","name":"Combo Madness","desc":"Reach 50x combo","reward_type":"crit_mult","reward":1},
    {"id":"crit_first","name":"Lucky Strike","desc":"First critical hit","reward_type":"click","reward":3},
    {"id":"crit_10","name":"Critical Mass","desc":"10 critical hits","reward_type":"crit_chance","reward":0.01},
    {"id":"upgrade_first","name":"Investor","desc":"First upgrade","reward_type":"cps","reward":2},
    {"id":"upgrade_50","name":"Hoarder","desc":"50 total upgrades","reward_type":"cps","reward":20},
    {"id":"prestige_1","name":"Rebirth","desc":"First prestige","reward_type":"click","reward":100},
    {"id":"prestige_5","name":"Transcendence","desc":"Prestige 5 times","reward_type":"prestige_bonus","reward":0.5},
    {"id":"level_5","name":"Evolved","desc":"Reach evo level 5","reward_type":"cps","reward":10},
    {"id":"level_10","name":"Advanced","desc":"Reach evo level 10","reward_type":"click","reward":200},
    {"id":"level_15","name":"Apex","desc":"Reach evo level 15","reward_type":"cps","reward":500},
    {"id":"cps_100","name":"Automation","desc":"Reach 100 DNA/sec","reward_type":"cps","reward":25},
    {"id":"cps_10k","name":"Factory","desc":"Reach 10K DNA/sec","reward_type":"click","reward":500},
    {"id":"boss_1","name":"Boss Slayer","desc":"Defeat first boss","reward_type":"click","reward":50},
    {"id":"boss_10","name":"Boss Hunter","desc":"Defeat 10 bosses","reward_type":"crit_chance","reward":0.03},
    {"id":"orb_50","name":"Orb Catcher","desc":"Collect 50 orbs","reward_type":"cps","reward":15},
    {"id":"mutation_5","name":"Mutant","desc":"Experience 5 mutations","reward_type":"click","reward":30},
]

# ─────────────── ACTIVE ABILITIES ───────────────
ABILITIES = [
    {"id":"storm","name":"DNA Storm","key":"Q","desc":"10x click for 5s","duration":5,"cooldown":30,"unlock_dna":500,"color":CYAN},
    {"id":"warp","name":"Time Warp","key":"W","desc":"10x CPS for 8s","duration":8,"cooldown":45,"unlock_dna":5000,"color":PURPLE},
    {"id":"surge","name":"Crit Surge","key":"E","desc":"100% crit for 6s","duration":6,"cooldown":35,"unlock_dna":50000,"color":RED},
    {"id":"frenzy","name":"Frenzy","key":"R","desc":"No combo decay 10s","duration":10,"cooldown":40,"unlock_dna":500000,"color":GREEN},
]

# ─────────────── MUTATION EVENTS ───────────────
MUTATIONS = [
    {"id":"dna_frenzy","name":"DNA Frenzy","desc":"2x all income!","mult_type":"all","mult_value":2.0,"duration":30,"color":GOLD},
    {"id":"golden_touch","name":"Golden Touch","desc":"3x click power!","mult_type":"click","mult_value":3.0,"duration":25,"color":YELLOW},
    {"id":"slow_meta","name":"Slow Metabolism","desc":"0.5x CPS...","mult_type":"cps","mult_value":0.5,"duration":20,"color":RED},
    {"id":"lucky_stars","name":"Lucky Stars","desc":"25% crit chance!","mult_type":"crit","mult_value":25.0,"duration":20,"color":ORANGE},
    {"id":"evolve_burst","name":"Evolution Burst","desc":"Visual evolution +3!","mult_type":"evo","mult_value":3.0,"duration":35,"color":PINK},
    {"id":"mega_combo","name":"Mega Combo","desc":"Combo starts at 10x!","mult_type":"combo","mult_value":10.0,"duration":15,"color":CYAN},
]

# ─────────────── BOSS DATA ───────────────
BOSS_NAMES = ["Alpha Slime","Crystal Golem","Shadow Wraith","Void Serpent","Storm Titan","Chaos Beast","Dimensional Eye","Cosmic Horror"]
BOSS_COLORS = [(100,200,100),(150,180,255),(120,50,180),(80,0,120),(200,200,50),(200,50,50),(200,100,255),(100,0,200)]

# ─────────────── BACKGROUND ───────────────
class Starfield:
    def __init__(self):
        self.stars=[{"x":random.uniform(0,WIDTH),"y":random.uniform(0,HEIGHT),
            "b":random.uniform(0.2,1),"s":random.uniform(1,4),"sz":random.uniform(0.5,2.5),"al":random.uniform(0,8)} for _ in range(200)]
    def draw(self,surf,lv,t):
        for s in self.stars:
            if lv<s["al"]:
                continue
                a=min(1,(lv-s["al"])*0.5); tw=(math.sin(t*s["s"]+s["x"])+1)*0.5

                br=s["b"]*a*(0.4+0.6*tw); c=int(255*br); sz=max(1,int(s["sz"]*(0.5+a*0.5)))

            if sz<=1:
                surf.set_at((int(s["x"])%WIDTH,int(s["y"])%HEIGHT),(c,c,min(255,int(c*1.1))))
            else: pygame.draw.circle(surf,(c,c,min(255,int(c*1.1))),(int(s["x"])%WIDTH,int(s["y"])%HEIGHT),sz)

class AmbientParticle:
    def __init__(self): self.reset(); self.y=random.uniform(0,HEIGHT)
    def reset(self):
        self.x=random.uniform(0,WIDTH); self.y=-5; self.vy=random.uniform(10,30)
        self.vx=random.uniform(-8,8); self.sz=random.uniform(1,3); self.a=random.uniform(0.1,0.4)
        self.color=random.choice([(100,200,255),(150,100,255),(100,255,150)])
    def update(self,dt):
        self.x+=self.vx*dt; self.y+=self.vy*dt
        if self.y>HEIGHT+10:
            self.reset()
    def draw(self,surf,lv):
        if lv<2:
            return; a=min(1,(lv-2)*0.2)*self.a; c=tuple(int(v*a) for v in self.color)
            pygame.draw.circle(surf,c,(int(self.x),int(self.y)),max(1,int(self.sz)))


# ─────────────── EFFECTS ───────────────
class Particle:
    def __init__(self,x,y,color,vx=None,vy=None,lifetime=1.0,size=4):
        self.x=x;self.y=y;self.color=color;self.vx=vx or random.uniform(-80,80);self.vy=vy or random.uniform(-120,-30)
        self.lifetime=self.max_life=lifetime;self.size=size
    def update(self,dt): self.x+=self.vx*dt;self.y+=self.vy*dt;self.vy+=100*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,self.lifetime/self.max_life);c=tuple(int(v*a) for v in self.color);sz=max(1,int(self.size*a))
        pygame.draw.circle(s,c,(int(self.x),int(self.y)),sz)
    @property
    def alive(self): return self.lifetime>0

class FloatingText:
    def __init__(self,x,y,text,color=GOLD,size="md"):
        self.x=x;self.y=y;self.text=text;self.color=color;self.lifetime=self.max_life=1.4
        self.font={"sm":font_sm,"md":font_md,"lg":font_lg}[size]
    def update(self,dt): self.y-=55*dt;self.lifetime-=dt
    def draw(self,s):
        a=max(0,min(1,self.lifetime/(self.max_life*0.5)))
        c=tuple(int(v*a+bg*(1-a)) for v,bg in zip(self.color,BG_TOP))
        t=self.font.render(self.text,True,c);s.blit(t,(self.x-t.get_width()//2,int(self.y)))
    @property
    def alive(self): return self.lifetime>0

class Toast:
    def __init__(self,title,desc,icon_color=GOLD):
        self.title=title;self.desc=desc;self.icon_color=icon_color;self.lifetime=self.max_life=4.0;self.slide=0
    def update(self,dt): self.lifetime-=dt;self.slide=min(1,self.slide+dt*5)
    def draw(self,s,idx):
        if self.lifetime<=0:
            return; fade=min(1,self.lifetime/1.0)
            tx=WIDTH-320+(320+10-int(330*self.slide)); y=20+idx*60; w,h=300,52

            ts=pygame.Surface((w,h),pygame.SRCALPHA)

            pygame.draw.rect(ts,(30,25,70,int(220*fade)),(0,0,w,h),border_radius=10)

            pygame.draw.rect(ts,(*self.icon_color,int(200*fade)),(0,0,w,h),2,border_radius=10)

            s.blit(ts,(int(tx),y))

            pygame.draw.circle(s,self.icon_color,(int(tx+18),y+16),8)

            star=font_xs.render("*",True,WHITE);s.blit(star,(int(tx+14),y+9))

            tc=tuple(int(min(255,v*fade)) for v in GOLD);tt=font_sm.render(self.title,True,tc);s.blit(tt,(int(tx+34),y+6))

            dc=tuple(int(min(255,v*fade)) for v in MUTED);dt2=font_xs.render(self.desc,True,dc);s.blit(dt2,(int(tx+34),y+26))

    @property
    def alive(self): return self.lifetime>0

class Sparkline:
    def __init__(self,mp=120): self.data=[];self.max_p=mp;self.timer=0;self.interval=0.5
    def update(self,dt,v):
        self.timer+=dt
        if self.timer>=self.interval:
            self.timer=0;self.data.append(v)
        if len(self.data)>self.max_p:
            self.data.pop(0)
    def draw(self,s,x,y,w,h,color=CYAN):
        if len(self.data)<2:
            return;mv=max(self.data) or 1
            pygame.draw.rect(s,DARK_PURPLE,(x,y,w,h),border_radius=4)

            pygame.draw.rect(s,PANEL_BORDER,(x,y,w,h),1,border_radius=4)

            pts=[(int(x+2+(i/(self.max_p-1))*(w-4)),int(y+h-2-(v/mv)*(h-4))) for i,v in enumerate(self.data)]

        if len(pts)>1:
            pygame.draw.lines(s,color,False,pts,1)
            lbl=font_xxs.render(f"{fmt(self.data[-1])}/s",True,MUTED);s.blit(lbl,(x+3,y+1))


# ─────────────── FALLING ORBS ───────────────
class DNAOrb:
    def __init__(self, total_dna):
        self.x=random.uniform(30,590); self.y=-20; self.vy=random.uniform(30,60)
        self.vx=random.uniform(-10,10); self.alive=True; self.pulse=random.uniform(0,6)
        # Value scales with progression
        scale = max(1, math.log10(total_dna+1))
        r = random.random()
        if r < 0.6:
            self.value=scale*5; self.radius=8; self.color=GREEN; self.name="Small"
        elif r < 0.85: self.value=scale*25; self.radius=12; self.color=CYAN; self.name="Medium"
        elif r < 0.97: self.value=scale*150; self.radius=16; self.color=PURPLE; self.name="Large"
        else: self.value=scale*1000; self.radius=20; self.color=GOLD; self.name="Golden!"
    def update(self,dt):
        self.y+=self.vy*dt; self.x+=self.vx*dt+math.sin(self.y*0.02)*0.5; self.pulse+=dt*4
        if self.y>HEIGHT+30:
            self.alive=False
    def draw(self,s):
        p=0.7+0.3*math.sin(self.pulse); r=int(self.radius*p)
        gs=pygame.Surface((r*4,r*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(*self.color,40),(r*2,r*2),r*2)
        pygame.draw.circle(gs,(*self.color,120),(r*2,r*2),r)
        pygame.draw.circle(gs,(*WHITE,180),(r*2,r*2),max(2,r//2))
        s.blit(gs,(int(self.x-r*2),int(self.y-r*2)))
    def hit_test(self,mx,my): return math.sqrt((mx-self.x)**2+(my-self.y)**2)<self.radius*1.5

# ─────────────── BOSS ───────────────
class Boss:
    def __init__(self, tier, total_dna):
        self.tier=min(tier, len(BOSS_NAMES)-1)
        self.name=BOSS_NAMES[self.tier]; self.color=BOSS_COLORS[self.tier]
        self.max_hp=int((100+self.tier*300)*(1+math.log10(total_dna+1)*2))
        self.hp=self.max_hp; self.x=310; self.y=300; self.alive=True
        self.reward=int(self.max_hp*5*(1+self.tier*0.5))
        self.timer=45+self.tier*10; self.flash=0; self.shake=0
        self.spawn_anim=1.0
    def update(self,dt):
        self.timer-=dt; self.flash=max(0,self.flash-dt); self.shake=max(0,self.shake-dt)
        self.spawn_anim=max(0,self.spawn_anim-dt*2)
        if self.timer<=0:
            self.alive=False
        if self.hp<=0:
            self.alive=False
    def damage(self,amount):
        self.hp-=amount; self.flash=0.15; self.shake=0.08
    def draw(self,s,t):
        if not self.alive:
            return
            sx=int(self.shake*20*(random.random()*2-1)); sy=int(self.shake*15*(random.random()*2-1))

            cx,cy=self.x+sx,self.y+sy; scale=min(1,self.spawn_anim)*1.0

        # Warning flash
        if self.spawn_anim>0.5:
            ws=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            a=int(60*(self.spawn_anim-0.5)*2*(math.sin(t*15)+1)*0.5)
            ws.fill((*RED,max(0,min(255,a)))); s.blit(ws,(0,0))
        # Body
        bob=math.sin(t*1.5)*8*scale; size=(50+self.tier*10)*scale
        # Aura
        asurf=pygame.Surface((int(size*6),int(size*6)),pygame.SRCALPHA)
        pulse=(math.sin(t*3)+1)*0.5
        pygame.draw.circle(asurf,(*self.color,int(30*(0.5+0.5*pulse))),(int(size*3),int(size*3)),int(size*2.5))
        s.blit(asurf,(int(cx-size*3),int(cy-size*3+bob)))
        # Spiky body
        pts=[]
        for a in range(0,360,15):
            rad=math.radians(a); spike=math.sin(a*3+t*2)*5*scale
            r=size+spike+(15 if a%30<15 else 0)*scale
            pts.append((cx+math.sin(rad)*r,cy+math.cos(rad)*r*0.8+bob))
        body_c=self.color if self.flash<=0 else WHITE
        pygame.draw.polygon(s,body_c,pts)
        pygame.draw.polygon(s,tuple(min(255,c+60) for c in self.color),pts,2)
        # Eyes
        for side in [-1,1]:
            ex=int(cx+side*15*scale); ey=int(cy-10*scale+bob)
            pygame.draw.circle(s,WHITE,(ex,ey),int(8*scale))
            pygame.draw.circle(s,(200,0,0),(ex+int(side*2*scale),ey),int(4*scale))
            pygame.draw.circle(s,WHITE,(ex+int(side*1*scale),ey-int(2*scale)),max(1,int(2*scale)))
        # HP bar
        bw=200; bh=12; bx=cx-bw//2; by=cy-int(size*1.2+bob)
        pygame.draw.rect(s,DARK_RED,(bx,by,bw,bh),border_radius=4)
        hw=int(bw*max(0,self.hp/self.max_hp))
        if hw>0:
            for px in range(hw):
                ratio=px/bw; c=(int(200*(1-ratio)+50*ratio),int(50+150*ratio),50)
                pygame.draw.line(s,c,(bx+px,by),(bx+px,by+bh-1))
        pygame.draw.rect(s,WHITE,(bx,by,bw,bh),1,border_radius=4)
        hp_txt=font_xs.render(f"{max(0,self.hp):.0f}/{self.max_hp}",True,WHITE)
        s.blit(hp_txt,(cx-hp_txt.get_width()//2,by-1))
        # Name & timer
        nt=font_md.render(f"BOSS: {self.name}",True,RED)
        s.blit(nt,(cx-nt.get_width()//2,by-22))
        tc=RED if self.timer<10 else ORANGE if self.timer<20 else MUTED
        tt=font_sm.render(f"Time: {self.timer:.0f}s  |  Reward: {fmt(self.reward)}",True,tc)
        s.blit(tt,(cx-tt.get_width()//2,by+bh+4))

# ─────────────── UPGRADES ───────────────
UPGRADES = [
    {"name":"Click Power","desc":"+1 DNA/click","base_cost":10,"cost_mult":1.15,"type":"click","value":1,"key":"1"},
    {"name":"Auto Cell","desc":"+0.5 DNA/sec","base_cost":25,"cost_mult":1.18,"type":"cps","value":0.5,"key":"2"},
    {"name":"Click Boost","desc":"+3 DNA/click","base_cost":200,"cost_mult":1.15,"type":"click","value":3,"key":"3"},
    {"name":"Amoeba Swarm","desc":"+2 DNA/sec","base_cost":500,"cost_mult":1.18,"type":"cps","value":2,"key":"4"},
    {"name":"Mega Click","desc":"+15 DNA/click","base_cost":5e3,"cost_mult":1.15,"type":"click","value":15,"key":"5"},
    {"name":"Bacteria Colony","desc":"+10 DNA/sec","base_cost":1e4,"cost_mult":1.18,"type":"cps","value":10,"key":"6"},
    {"name":"Hyper Click","desc":"+100 DNA/click","base_cost":1e5,"cost_mult":1.15,"type":"click","value":100,"key":"7"},
    {"name":"Biome Engine","desc":"+75 DNA/sec","base_cost":2e5,"cost_mult":1.18,"type":"cps","value":75,"key":"8"},
    {"name":"Omega Click","desc":"+1K DNA/click","base_cost":2e6,"cost_mult":1.15,"type":"click","value":1000,"key":"9"},
    {"name":"Evolution Core","desc":"+500 DNA/sec","base_cost":5e6,"cost_mult":1.18,"type":"cps","value":500,"key":"0"},
    {"name":"Singularity Tap","desc":"+10K/click","base_cost":5e7,"cost_mult":1.15,"type":"click","value":1e4,"key":""},
    {"name":"Genesis Engine","desc":"+5K DNA/sec","base_cost":1e8,"cost_mult":1.18,"type":"cps","value":5e3,"key":""},
]
BUY_AMOUNTS=[1,10,100,-1]; BUY_LABELS=["x1","x10","x100","MAX"]

# ─────────────── CREATURE RENDERER (compact) ───────────────
# ─────────────── CREATURE RENDERER ───────────────
class CreatureRenderer:
    def __init__(self, genome):
        self.g = genome

    def draw(self, surface, cx, cy, td, t, hover=False):
        g = self.g
        sf = 1.0 + hover * 0.07
        bob = math.sin(t * 2.0) * 6
        color = g.body_color(td, t)
        acc = g.accent_color(td, t)
        bs = g.body_size(td) * sf
        cy_b = cy + bob
        # Shadow
        sw, sh = int(bs * 2.2), max(4, int(bs * 0.3))
        shadow_surf = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 40), (0, 0, sw * 2, sh * 2))
        surface.blit(shadow_surf, (cx - sw, cy + bs * 0.9))
        # Draw layers
        if g.has_aura(td):
            self._draw_aura(surface, cx, cy_b, bs, td, t, color, acc)
        if g.tail_length(td) > 0:
            self._draw_tail(surface, cx, cy_b, bs, td, t, color, acc)
        if g.limb_count(td) > 0:
            self._draw_limbs(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_wings(td):
            self._draw_wings(surface, cx, cy_b, bs, td, t, color, acc)
        self._draw_body(surface, cx, cy_b, bs, td, t, color, acc)
        if g.has_pattern(td):
            self._draw_pattern(surface, cx, cy_b, bs, td, t, color, acc)
        if g.spike_count(td) > 0:
            self._draw_spikes(surface, cx, cy_b, bs, td, t, acc)
        hx, hy = cx - bs * 0.6, cy_b - bs * 0.5
        if g.has_ears(td):
            self._draw_ears(surface, hx, hy, bs, td, t, color, acc)
        if g.has_horns(td):
            self._draw_horns(surface, hx, hy, bs, td, t, acc)
        self._draw_eyes(surface, hx, hy, bs, td, t, color)
        self._draw_mouth(surface, hx, hy, bs, td, t, acc)
        # Bioluminescent glow
        bio = g.bioluminescence(td)
        if bio > 0.1:
            gs = pygame.Surface((int(bs * 4), int(bs * 4)), pygame.SRCALPHA)
            pulse = (math.sin(t * 3) + 1) * 0.5
            a = int(bio * (30 + 25 * pulse))
            pygame.draw.circle(gs, (*color, a), (int(bs * 2), int(bs * 2)), int(bs * 1.6))
            surface.blit(gs, (int(cx - bs * 2), int(cy_b - bs * 2)))

    def _draw_body(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        segs = g.body_segments(td)
        if segs <= 1:
            pts = []
            for a in range(360):
                r = math.radians(a)
                w = math.sin(r * 3 + t * 3) * 3 + math.sin(r * 5 + t * 2) * 2
                rx = (bs + w) * g.body_width_ratio
                ry = bs * 0.85 + w * 0.5
                pts.append((cx + math.sin(r) * rx, cy + math.cos(r) * ry))
            pygame.draw.polygon(s, col, pts)
            hl_r = max(3, int(bs * 0.3))
            hl_color = tuple(min(255, c + 60) for c in col)
            pygame.draw.circle(s, hl_color, (int(cx - bs * 0.25), int(cy - bs * 0.3)), hl_r)
        else:
            tl = bs * 2 * segs * 0.6
            sr = bs * 0.65
            for i in range(segs):
                ratio = i / max(segs - 1, 1)
                wave = math.sin(t * 2 + i * 0.8) * 12 * (1 - ratio * 0.3)
                sx = cx - tl / 2 + ratio * tl + wave
                sy = cy + ratio * bs * 0.3
                sri = sr * (1 - ratio * 0.25)
                wb = math.sin(t * 3 + i * 2) * 2
                sp = []
                for a in range(360):
                    rad = math.radians(a)
                    sp.append((sx + math.sin(rad) * (sri + wb), sy + math.cos(rad) * (sri * 0.8 + wb * 0.5)))
                seg_c = tuple(int(c * (1 - ratio * 0.15)) for c in col)
                pygame.draw.polygon(s, seg_c, sp)
                if i == 0:
                    pygame.draw.circle(s, tuple(min(255, c + 50) for c in col),
                                       (int(sx - sri * 0.2), int(sy - sri * 0.3)), max(2, int(sri * 0.3)))

    def _draw_eyes(self, s, hx, hy, bs, td, t, col):
        g = self.g
        count = g.eye_count(td)
        es = g.eye_size(td)
        style = g.eye_style
        if style == "cyclops":
            positions = [(0, 0)]
            es *= 1.8
        elif style == "compound":
            positions = []
            for row in range(min((count + 2) // 3, 3)):
                c_in_row = min(count - row * 3, 3)
                for c_ in range(c_in_row):
                    positions.append((c_ - (c_in_row - 1) / 2, row - 0.5))
            es *= 0.7
        else:
            positions = [(i - (count - 1) / 2, 0) for i in range(count)]
        for px, py in positions:
            ex = hx + px * es * 1.6
            ey = hy + py * es * 1.6 - bs * 0.1
            if style == "slit":
                pygame.draw.ellipse(s, WHITE, (int(ex - es), int(ey - es * 0.7), int(es * 2), int(es * 1.4)))
                pygame.draw.ellipse(s, (20, 20, 40),
                    (int(ex - es * 0.15), int(ey - es * 0.6), int(es * 0.3), int(es * 1.2)))
            elif style == "compound":
                for ci in range(6):
                    angle = ci * math.pi * 2 / 6 + t * 0.5
                    cr = es * 0.6
                    ccx = ex + math.cos(angle) * es * 0.4
                    ccy = ey + math.sin(angle) * es * 0.4
                    pygame.draw.circle(s, (200, 200, 255), (int(ccx), int(ccy)), max(1, int(cr)))
                    pygame.draw.circle(s, (30, 30, 60), (int(ccx), int(ccy)), max(1, int(cr * 0.5)))
            else:
                pygame.draw.circle(s, WHITE, (int(ex), int(ey)), int(es))
                look = math.sin(t * 2) * es * 0.2
                pr = es * 0.5
                pygame.draw.circle(s, (20, 20, 40), (int(ex + look), int(ey)), int(pr))
                pygame.draw.circle(s, WHITE, (int(ex + look - pr * 0.3), int(ey - pr * 0.3)), max(1, int(pr * 0.3)))

    def _draw_mouth(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        comp = g.mouth_complexity(td)
        if comp < 0.1:
            return
        mx_p = hx + bs * 0.3
        my_p = hy + bs * 0.2
        style = g.mouth_style
        if style == "smile" or comp < 0.3:
            mw = bs * 0.5 * comp
            mh = bs * 0.2 * comp
            if mw > 3:
                pygame.draw.arc(s, acc,
                    (int(mx_p - mw), int(my_p - mh), int(mw * 2), int(mh * 2)),
                    math.pi + 0.3, 2 * math.pi - 0.3, max(1, int(2 * comp + 1)))
        if comp > 0.3:
            if style == "teeth":
                tw = bs * 0.4
                for i in range(int(3 + comp * 5)):
                    tx = mx_p - tw / 2 + (i / max(int(3 + comp * 5) - 1, 1)) * tw
                    th = 3 + comp * 5
                    pygame.draw.polygon(s, WHITE, [
                        (int(tx - 2), int(my_p)), (int(tx + 2), int(my_p)), (int(tx), int(my_p + th))])
            elif style == "beak":
                bl = bs * 0.4 * comp
                pygame.draw.polygon(s, (255, 200, 80), [
                    (int(mx_p), int(my_p - 4)), (int(mx_p + bl), int(my_p)), (int(mx_p), int(my_p + 4))])
            elif style == "tentacles":
                for i in range(int(2 + comp * 4)):
                    ba = -0.5 + i * (1.0 / max(int(2 + comp * 4) - 1, 1))
                    pts = [(int(mx_p), int(my_p))]
                    for j in range(1, 6):
                        tr = j / 5
                        w = math.sin(t * 5 + i + j * 0.7) * 8 * tr
                        pts.append((int(mx_p + tr * bs * 0.5 * comp + w),
                                    int(my_p + tr * bs * 0.3 * comp + ba * bs * 0.2 * tr)))
                    if len(pts) > 1:
                        pygame.draw.lines(s, acc, False, pts, max(1, int(2)))
            elif style == "lamprey":
                mr = int(bs * 0.15 * comp)
                if mr > 2:
                    pygame.draw.circle(s, (40, 10, 10), (int(mx_p), int(my_p)), mr)
                    for i in range(int(6 + comp * 10)):
                        a = i * math.pi * 2 / int(6 + comp * 10)
                        pygame.draw.line(s, WHITE,
                            (int(mx_p + math.cos(a) * mr * 0.6), int(my_p + math.sin(a) * mr * 0.6)),
                            (int(mx_p + math.cos(a) * mr), int(my_p + math.sin(a) * mr)), 1)

    def _draw_limbs(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        count = g.limb_count(td)
        length = g.limb_length(td)
        style = g.limb_style
        if count == 0 or length < 3:
            return
        for i in range(count):
            side = 1 if i % 2 == 0 else -1
            idx = i // 2
            tp = count // 2
            spread = bs * 1.2
            bx = cx - spread / 2 + (idx / max(tp - 1, 1)) * spread if tp > 1 else cx
            by = cy + bs * 0.6
            anim = math.sin(t * 4 + i * 1.2) * 0.3
            if style == "tentacle":
                pts = [(int(bx + side * bs * 0.4), int(by))]
                for j in range(1, 8):
                    tr = j / 7
                    w = math.sin(t * 5 + i + j * 0.8) * 12 * tr
                    pts.append((int(bx + side * (bs * 0.4 + length * tr) + w),
                                int(by + length * tr * 0.5 + anim * length * tr)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(4)))
            elif style == "crab":
                kx = bx + side * (bs * 0.5 + length * 0.5)
                ky = by + length * 0.3 + anim * 10
                fx = kx + side * length * 0.4
                fy = by + length * 0.8
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(kx), int(ky)), max(2, int(4)))
                pygame.draw.line(s, acc, (int(kx), int(ky)),
                               (int(fx), int(fy)), max(2, int(3)))
                if i < 2:
                    cs = max(2, int(bs * 0.15))
                    pygame.draw.circle(s, col, (int(fx), int(fy)), cs)
            elif style == "spindly":
                px, py = bx + side * bs * 0.3, by
                for j in range(3):
                    tr = (j + 1) / 3
                    nx = px + side * length * 0.35
                    ny = py + length * 0.3 + anim * 8 * tr
                    pygame.draw.line(s, acc, (int(px), int(py)), (int(nx), int(ny)), max(1, int(2)))
                    pygame.draw.circle(s, col, (int(nx), int(ny)), max(1, int(3)))
                    px, py = nx, ny
            else:  # stubby
                fx = bx + side * (bs * 0.5 + length * 0.3)
                fy = by + length * 0.7 + anim * 8
                lw = max(3, int(bs * 0.15))
                pygame.draw.line(s, acc, (int(bx + side * bs * 0.3), int(by)),
                               (int(fx), int(fy)), lw)
                pygame.draw.circle(s, col, (int(fx), int(fy)), max(2, int(lw * 0.8)))

    def _draw_wings(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        ws = g.wing_size(td)
        if ws < 3:
            return
        style = g.wing_style
        flap = math.sin(t * 3) * 15
        for side in [-1, 1]:
            if style == "bat":
                pts = [
                    (cx + side * bs * 0.3, cy - bs * 0.3),
                    (cx + side * ws, cy - bs * 0.5 + flap),
                    (cx + side * ws * 0.7, cy - bs * 0.1 + flap * 0.6),
                    (cx + side * ws * 1.1, cy + bs * 0.1 + flap * 0.8),
                    (cx + side * ws * 0.5, cy + bs * 0.2)]
                wc = tuple(max(0, c - 50) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])
                pygame.draw.polygon(s, acc, [(int(p[0]), int(p[1])) for p in pts], 2)
            elif style == "feathered":
                for layer in range(3):
                    off = layer * 8
                    pts = [
                        (cx + side * bs * 0.2, cy - bs * 0.2),
                        (cx + side * (ws - off), cy - bs * (0.6 + layer * 0.2) + flap * (1 - layer * 0.2)),
                        (cx + side * (ws * 0.8 - off), cy + bs * 0.1 + flap * 0.5)]
                    lc = tuple(min(255, c + layer * 20) for c in col)
                    pygame.draw.polygon(s, lc, [(int(p[0]), int(p[1])) for p in pts])
            elif style == "crystal":
                for j in range(4):
                    a = math.radians(-30 + j * 25 + side * 20) + math.sin(t * 2) * 0.1
                    d = ws * (0.6 + j * 0.12)
                    tx = cx + side * math.cos(a) * d
                    ty = cy - abs(math.sin(a)) * d * 0.7 + flap * 0.3
                    pts = [(int(cx + side * bs * 0.3), int(cy - bs * 0.3)),
                           (int(tx), int(ty)),
                           (int(cx + side * 10), int(cy))]
                    als = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                    pygame.draw.polygon(als, (*acc, 100), pts)
                    s.blit(als, (0, 0))
                    pygame.draw.polygon(s, acc, pts, 1)
            else:  # insect
                pts = [
                    (cx + side * bs * 0.2, cy - bs * 0.1),
                    (cx + side * ws, cy - bs * 0.8 + flap),
                    (cx + side * ws * 0.9, cy - bs * 0.2 + flap * 0.4),
                    (cx + side * ws * 0.3, cy + bs * 0.3)]
                wc = tuple(max(0, c - 30) for c in col)
                pygame.draw.polygon(s, wc, [(int(p[0]), int(p[1])) for p in pts])

    def _draw_tail(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        length = g.tail_length(td)
        if length < 3:
            return
        style = g.tail_style
        segs = max(3, int(length / 10))
        pts = []
        for i in range(segs + 1):
            tr = i / segs
            w = math.sin(t * 3 + tr * 4) * (10 + tr * 15)
            tx = cx + bs * 0.7 + tr * length + w
            ty = cy + tr * bs * 0.3 + math.sin(t * 2 + tr * 3) * 5
            pts.append((tx, ty))
            sr = max(2, int(bs * 0.3 * (1 - tr * 0.7)))
            sc = tuple(int(c * (1 - tr * 0.2)) for c in col)
            pygame.draw.circle(s, sc, (int(tx), int(ty)), sr)
        if style == "spiked":
            for i in range(2, segs, 2):
                tr = i / segs
                px, py = pts[i]
                sh = 8 + tr * 10
                pygame.draw.polygon(s, acc, [(int(px - 3), int(py)),
                                                  (int(px + 3), int(py)),
                                                  (int(px), int(py - sh))])
        elif style == "forked":
            tx, ty = pts[-1]
            fl = length * 0.2
            for d in [-1, 1]:
                pygame.draw.line(s, acc, (int(tx), int(ty)),
                               (int(tx + fl + math.sin(t * 4 + d) * 5), int(ty + d * fl * 0.5)),
                               max(1, int(3)))
        elif style == "flame":
            tx, ty = pts[-1]
            for _ in range(5):
                fc = random.choice([(255, 100, 0), (255, 200, 0), (255, 50, 0)])
                pygame.draw.circle(s, fc,
                                   (int(tx + random.randint(-8, 12)), int(ty + random.randint(-12, 12))),
                                   random.randint(3, int(6 + g.level(td))))
        elif style == "tentacle":
            tx, ty = pts[-1]
            for d in [-1, 1]:
                tent_pts = [(int(tx), int(ty))]
                for j in range(1, 5):
                    tr = j / 4
                    w = math.sin(t * 6 + d + j) * 8
                    tent_pts.append((int(tx + d * tr * 20 + w), int(ty + tr * 15)))
                if len(tent_pts) > 1:
                    pygame.draw.lines(s, acc, False, tent_pts, max(1, int(2)))

    def _draw_spikes(self, s, cx, cy, bs, td, t, acc):
        g = self.g
        count = g.spike_count(td)
        size = g.spike_size(td)
        if count < 1 or size < 2:
            return
        for i in range(count):
            a = (i / count) * math.pi * 2 + 0.5
            if math.sin(a) > 0.2:
                continue
            sx = cx + math.cos(a) * bs * 0.85
            sy = cy + math.sin(a) * bs * 0.85
            pygame.draw.polygon(s, acc, [
                (int(sx - math.sin(a) * 3), int(sy + math.cos(a) * 3)),
                (int(sx + math.sin(a) * 3), int(sy - math.cos(a) * 3)),
                (int(sx + math.cos(a) * size), int(sy + math.sin(a) * size))])

    def _draw_horns(self, s, hx, hy, bs, td, t, acc):
        g = self.g
        count = g.horn_count(td)
        size = g.horn_size(td)
        style = g.horn_style
        if count < 1 or size < 3:
            return
        for i in range(count):
            off = (i - (count - 1) / 2) * 12 if count > 1 else 0
            bx, by = hx + off, hy - bs * 0.4
            if style == "pointed":
                pygame.draw.polygon(s, acc, [(int(bx - 4), int(by)),
                                                  (int(bx + 4), int(by)),
                                                  (int(bx + off * 0.3), int(by - size))])
            elif style == "curved":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.4 + math.sin(tr * math.pi) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
            elif style == "crystal":
                pygame.draw.polygon(s, acc, [(int(bx), int(by - size)),
                                                  (int(bx - 5), int(by)),
                                                  (int(bx + 5), int(by))])
            elif style == "antler":
                pts = [(int(bx), int(by))]
                for j in range(1, 6):
                    tr = j / 5
                    pts.append((int(bx + tr * off * 0.5 + math.sin(tr * 3) * 3),
                                int(by - tr * size)))
                if len(pts) > 1:
                    pygame.draw.lines(s, acc, False, pts, max(2, int(3)))
                if len(pts) > 3:
                    bp = pts[2]
                    pygame.draw.line(s, acc, bp,
                                   (int(bp[0] + (15 if off >= 0 else -15)), int(bp[1] - 10)),
                                   max(1, int(2)))

    def _draw_ears(self, s, hx, hy, bs, td, t, col, acc):
        g = self.g
        es = g.ear_size(td)
        if es < 3:
            return
        if g.ear_type == "pointed":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.5
                ey = hy - bs * 0.3
                pygame.draw.polygon(s, col, [(int(ex - 8), int(ey)),
                                                  (int(ex + 8), int(ey)),
                                                  (int(ex + side * 5), int(ey - es))])
                pygame.draw.polygon(s, acc, [(int(ex - 8), int(ey)),
                                                   (int(ex + 8), int(ey)),
                                                   (int(ex + side * 5), int(ey - es))], 1)
        elif g.ear_type == "frilled":
            for side in [-1, 1]:
                ex = hx + side * bs * 0.4
                ey = hy - bs * 0.2
                fp = []
                for j in range(8):
                    a = math.radians(-90 + (j / 7) * 60 * side)
                    r = es * (0.5 + math.sin(j * 1.5) * 0.3)
                    fp.append((int(ex + math.cos(a) * r * side), int(ey + math.sin(a) * r)))
                if len(fp) > 2:
                    pygame.draw.lines(s, acc, False, fp, 2)
        elif g.ear_type == "antenna":
            for side in [-1, 1]:
                bx = hx + side * bs * 0.3
                by = hy - bs * 0.3
                w = math.sin(t * 5 + side) * 5
                tx = bx + side * es * 0.5 + w
                ty = by - es + w
                pygame.draw.line(s, acc, (int(bx), int(by)), (int(tx), int(ty)), 2)
                glow = (math.sin(t * 4 + side * 2) + 1) * 0.5
                gc = tuple(int(min(255, c * (0.5 + 0.5 * glow))) for c in acc)
                pygame.draw.circle(s, gc, (int(tx), int(ty)), max(2, int(4 * glow + 2)))

    def _draw_pattern(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        op = g.pattern_opacity(td)
        pt = g.pattern_type
        if op < 0.05:
            return
        pc = tuple(int(c * op + bg * (1 - op)) for c, bg in zip(acc, col))
        if pt == "spots":
            for i in range(int(5 + g.level(td) * 1.5)):
                a = i * 2.3 + 0.5
                d = bs * (0.2 + (i % 3) * 0.2)
                pygame.draw.circle(s, pc, (int(cx + math.cos(a) * d), int(cy + math.sin(a) * d * 0.7)),
                                   max(2, int(bs * 0.1 * op)))
        elif pt == "stripes":
            for i in range(-3, 4):
                sx = cx + i * bs * 0.25
                sh = int(bs * 1.2)
                pygame.draw.line(s, pc,
                    (int(sx + math.sin(i + t) * 3), int(cy - sh // 2)),
                    (int(sx + math.sin(i + t + 1) * 3), int(cy + sh // 2)),
                    max(1, int(2 * op)))
        elif pt == "rings":
            for i in range(1, 4):
                pygame.draw.circle(s, pc, (int(cx), int(cy)),
                                   int(bs * 0.3 * i * op), max(1, int(2 * op)))
        elif pt == "scales":
            for row in range(-2, 3):
                for c_ in range(-2, 3):
                    sx = cx + c_ * bs * 0.3 + (row % 2) * bs * 0.15
                    sy = cy + row * bs * 0.25
                    if math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2) < bs * 0.8:
                        sr = int(bs * 0.12 * op)
                        pygame.draw.arc(s, pc,
                            (int(sx - sr), int(sy - sr), sr * 2, sr * 2),
                            0, math.pi, max(1, int(1.5 * op)))

    def _draw_aura(self, s, cx, cy, bs, td, t, col, acc):
        g = self.g
        intensity = g.aura_intensity(td)
        style = g.aura_style
        if intensity < 0.05:
            return
        if style == "glow":
            for layer in range(3):
                r = int(bs * (1.5 + layer * 0.4) * intensity)
                a = int(30 * intensity * (1 - layer * 0.25))
                gs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                p = (math.sin(t * 3 + layer) + 1) * 0.5
                pygame.draw.circle(gs, (*col, int(a * (0.7 + 0.3 * p))),
                                   (r + 2, r + 2), r)
                s.blit(gs, (cx - r - 2, cy - r - 2))
        elif style == "sparks":
            for i in range(int(8 * intensity)):
                a = t * (1.5 + i * 0.3) + i * math.pi * 2 / 8
                d = (bs * 1.2 + math.sin(t * 2 + i) * 15) * intensity
                c = acc if i % 2 else col
                pygame.draw.circle(s, c, (int(cx + math.cos(a) * d),
                                              int(cy + math.sin(a) * d * 0.7)),
                                   max(1, int(3 * intensity)))
        elif style == "rings":
            for i in range(2):
                ra = t * (1 + i * 0.7) + i * 1.5
                rx = int((bs * 1.5 + i * 15) * intensity)
                ry = int((bs * 0.4 + i * 8) * intensity)
                rs = pygame.Surface((rx * 2 + 4, ry * 2 + 4), pygame.SRCALPHA)
                pygame.draw.ellipse(rs, (*acc, int(80 * intensity)), (2, 2, rx * 2, ry * 2),
                                 max(1, int(2 * intensity)))
                rot = pygame.transform.rotate(rs, math.degrees(ra))
                s.blit(rot, (cx - rot.get_width() // 2, cy - rot.get_height() // 2))
        elif style == "dna_helix":
            for i in range(int(20 * intensity)):
                tr = i / max(int(20 * intensity) - 1, 1)
                a = tr * math.pi * 4 + t * 2
                d = bs * 1.3 * intensity
                for strand in [0, math.pi]:
                    sx = cx + math.cos(a + strand) * d * math.sin(tr * math.pi)
                    sy = cy - bs + tr * bs * 2
                    pygame.draw.circle(s, col if strand == 0 else acc, (int(sx), int(sy)),
                                       max(1, int(2 * intensity)))
        elif style == "constellation":
            sp = []
            for i in range(int(10 * intensity)):
                seed = i * 7.3 + 1.2
                a = seed * 2.1 + t * 0.3
                d = bs * (0.8 + (seed % 0.6) * 0.8) * intensity
                sx = cx + math.cos(a) * d
                sy = cy + math.sin(a) * d * 0.7
                sp.append((int(sx), int(sy)))
                tw = (math.sin(t * 3 + i * 2) + 1) * 0.5
                pygame.draw.circle(s, WHITE, (int(sx), int(sy)),
                                   max(1, int((1 + tw) * 2 * intensity)))
            for i in range(len(sp)):
                for j in range(i + 1, len(sp)):
                    dx = sp[i][0] - sp[j][0]
                    dy = sp[i][1] - sp[j][1]
                    d = math.sqrt(dx * dx + dy * dy)
                    if d < bs * 1.5 * intensity:
                        ls = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        al = max(0, min(255, int(40 * intensity * (1 - d / (bs * 1.5 * intensity)))))
                        pygame.draw.line(ls, (*acc, al), sp[i], sp[j], 1)
                        s.blit(ls, (0, 0))

# ─────────────── GAME STATE ───────────────
class Game:
    def __init__(self):
        self.dna=0.0;self.total_dna=0.0;self.total_clicks=0;self.total_crits=0
        self.total_upgrades_bought=0;self.click_power=1;self.cps=0.0
        self.upgrade_counts=[0]*len(UPGRADES)
        self.particles=[];self.float_texts=[];self.toasts=[]
        self.t=0.0;self.creature_hover=False;self.shop_scroll=0;self.max_scroll=0
        self.creature_cx=320;self.creature_cy=360
        self.shake_x=0;self.shake_y=0;self.shake_time=0
        # Prestige
        self.prestige_count=0;self.prestige_mult=1.0
        # Combo
        self.combo=0;self.combo_timer=0;self.combo_decay=1.2;self.max_combo=0
        # Crits
        self.crit_chance=0.05;self.crit_mult=5.0
        # Achievement bonus tracking
        self.ach_bonus_click=0;self.ach_bonus_cps=0;self.ach_bonus_crit=0;self.ach_bonus_prestige=0;self.ach_bonus_crit_mult=0
        # Buy amount
        self.buy_amount_idx=0;self.display_dna=0.0
        # UI panels
        self.show_traits=False;self.show_bestiary=False;self.show_stats=False;self.show_settings=False;self.show_achievements_panel=False
        self.hovered_upgrade=-1;self.panel_scroll=0
        # Background
        self.starfield=Starfield();self.ambient_particles=[AmbientParticle()for _ in range(30)]
        self.sparkline=Sparkline()
        # Achievements
        self.achievements_unlocked=set()
        # Milestones
        self.last_milestone=0;self.milestones=[10,100,1e3,1e4,1e5,1e6,1e7,1e8,1e9,1e10,1e11,1e12]
        # Auto-save
        self.autosave_timer=0;self.save_time=time.time();self.play_time=0.0
        # Boss system
        self.boss=None;self.boss_timer=random.uniform(60,120);self.bosses_defeated=0;self.boss_tier=0
        # Orbs
        self.orbs=[];self.orb_timer=0;self.orbs_collected=0
        # Abilities
        self.ability_cooldowns=[0.0]*len(ABILITIES);self.ability_actives=[0.0]*len(ABILITIES)
        self.abilities_unlocked=[False]*len(ABILITIES)
        # Mutations
        self.active_mutation=None;self.mutation_timer=0;self.mutations_experienced=0;self.mutation_event_timer=random.uniform(45,90)
        # Bestiary
        self.bestiary=[]
        # Settings
        self.sound_on=SOUND_ENABLED;self.particle_quality=2  # 0=low,1=med,2=high
        # Genome
        seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed);self.renderer=CreatureRenderer(self.genome);self.seed_display=seed
        self._try_load()

    def _try_load(self):
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE,'r') as f: data=json.load(f)
            self.dna=data.get("dna",0);self.total_dna=data.get("total_dna",0)
            self.total_clicks=data.get("total_clicks",0);self.total_crits=data.get("total_crits",0)
            self.total_upgrades_bought=data.get("total_upgrades_bought",0)
            self.click_power=data.get("click_power",1);self.cps=data.get("cps",0)
            self.upgrade_counts=data.get("upgrade_counts",[0]*len(UPGRADES))
            self.prestige_count=data.get("prestige_count",0);self.prestige_mult=data.get("prestige_mult",1.0)
            self.max_combo=data.get("max_combo",0);self.achievements_unlocked=set(data.get("achievements",[]))
            self.buy_amount_idx=data.get("buy_amount_idx",0);self.save_time=data.get("save_time",time.time())
            self.play_time=data.get("play_time",0);self.bosses_defeated=data.get("bosses_defeated",0)
            self.boss_tier=data.get("boss_tier",0);self.orbs_collected=data.get("orbs_collected",0)
            self.mutations_experienced=data.get("mutations_experienced",0)
            self.ach_bonus_click=data.get("ach_bonus_click",0);self.ach_bonus_cps=data.get("ach_bonus_cps",0)
            self.ach_bonus_crit=data.get("ach_bonus_crit",0);self.ach_bonus_prestige=data.get("ach_bonus_prestige",0)
            self.ach_bonus_crit_mult=data.get("ach_bonus_crit_mult",0)
            self.bestiary=data.get("bestiary",[]);self.sound_on=data.get("sound_on",SOUND_ENABLED)
            self.particle_quality=data.get("particle_quality",2)
            self.genome=Genome.from_dict(data["genome"]);self.renderer=CreatureRenderer(self.genome);self.seed_display=self.genome.seed
            # Offline progress
            elapsed=time.time()-self.save_time
            if elapsed>5:
                cps_val=self.effective_cps();off_earn=cps_val*elapsed*0.5
                if off_earn>0:
                    self.dna+=off_earn;self.total_dna+=off_earn
                    self.toasts.append(Toast("Welcome Back!",f"Earned {fmt(off_earn)} DNA away ({elapsed/60:.1f}m)",CYAN))
        except Exception as e: print(f"Load failed: {e}")

    def save(self):
        try:
            data={"dna":self.dna,"total_dna":self.total_dna,"total_clicks":self.total_clicks,
                "total_crits":self.total_crits,"total_upgrades_bought":self.total_upgrades_bought,
                "click_power":self.click_power,"cps":self.cps,"upgrade_counts":self.upgrade_counts,
                "prestige_count":self.prestige_count,"prestige_mult":self.prestige_mult,
                "max_combo":self.max_combo,"achievements":list(self.achievements_unlocked),
                "buy_amount_idx":self.buy_amount_idx,"save_time":time.time(),"play_time":self.play_time,
                "bosses_defeated":self.bosses_defeated,"boss_tier":self.boss_tier,
                "orbs_collected":self.orbs_collected,"mutations_experienced":self.mutations_experienced,
                "ach_bonus_click":self.ach_bonus_click,"ach_bonus_cps":self.ach_bonus_cps,
                "ach_bonus_crit":self.ach_bonus_crit,"ach_bonus_prestige":self.ach_bonus_prestige,
                "ach_bonus_crit_mult":self.ach_bonus_crit_mult,
                "bestiary":self.bestiary,"sound_on":self.sound_on,"particle_quality":self.particle_quality,
                "genome":self.genome.to_dict()}
            with open(SAVE_FILE,'w') as f: json.dump(data,f,indent=2)
        except Exception as e: print(f"Save failed: {e}")

    def prestige(self):
        if self.total_dna<1e6:
            return
            bonus=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige

            self.prestige_count+=1;self.prestige_mult+=bonus

            self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),

            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            self.dna=0;self.total_dna=0;self.click_power=1;self.cps=0

            self.upgrade_counts=[0]*len(UPGRADES);self.combo=0;self.combo_timer=0;self.last_milestone=0

            self.total_clicks=0;self.total_crits=0;self.total_upgrades_bought=0;self.sparkline=Sparkline()

            self.boss=None;self.boss_timer=random.uniform(60,120);self.active_mutation=None

            self.toasts.append(Toast("PRESTIGE!",f"+{bonus:.2f}x permanent (now {self.prestige_mult:.2f}x)",GOLD))

            self._play(snd_prestige);self._burst(self.creature_cx,self.creature_cy,80,[GOLD,CYAN,WHITE,PURPLE]);self.save()


    def _trait_summary(self):
        g=self.genome;td=self.total_dna
        return{"limbs":g.limb_style,"wings":g.wing_style,"eyes":g.eye_style,"tail":g.tail_style,
               "horns":g.horn_style,"mouth":g.mouth_style,"aura":g.aura_style,"pattern":g.pattern_type,
               "ears":g.ear_type,"level":f"{g.level(td):.1f}"}

    def upgrade_cost(self,idx):
        upg=UPGRADES[idx];base=upg["base_cost"];cm=upg["cost_mult"];owned=self.upgrade_counts[idx];amt=self.get_buy_amount()
        if amt==-1:
            total=0;count=0
            while True:
                c=int(base*(cm**(owned+count)));total+=c;count+=1
                if self.dna-total<c or count>10000:
                    total-=c;count-=1;break
            return total,count
        else:total=sum(int(base*(cm**(owned+i)))for i in range(amt));return total,amt

    def get_buy_amount(self):return BUY_AMOUNTS[self.buy_amount_idx]

    def effective_click(self):
        m=self.genome.click_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("click"))
        if self.ability_actives[0]>0:
            m*=10  # DNA Storm
            return(self.click_power+self.ach_bonus_click)*m


    def effective_cps(self):
        m=self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
        m*=(1+self._get_mutation_mult("cps"))
        if self.ability_actives[1]>0:
            m*=10  # Time Warp
            return(self.cps+self.ach_bonus_cps)*m


    def effective_crit_chance(self):
        c=self.crit_chance+self.ach_bonus_crit
        if self.ability_actives[2]>0:
            c=1.0  # Crit Surge
            mut=self._get_mutation_mult("crit")

        if mut>0:
            c=max(c,mut/100)
            return min(c,1.0)


    def effective_crit_mult(self):
        return self.crit_mult+self.ach_bonus_crit_mult

    def _get_mutation_mult(self,mtype):
        if not self.active_mutation:
            return 0
        if self.active_mutation["mult_type"]==mtype:
            return self.active_mutation["mult_value"]-1
        if self.active_mutation["mult_type"]=="all"and mtype in("click","cps"):
            return self.active_mutation["mult_value"]-1
            return 0


    def _play(self,snd):
        if snd and self.sound_on:
            try:snd.play()
            except:pass

    def click_creature(self,mx,my):
        self.total_clicks+=1;self.combo+=1;self.combo_timer=self.combo_decay
        # Mutation combo boost
        if self.active_mutation and self.active_mutation["mult_type"]=="combo":
            self.combo=max(self.combo,int(self.active_mutation["mult_value"]))
        if self.combo>self.max_combo:
            self.max_combo=self.combo
            combo_mult=1.0+(self.combo-1)*0.1

            is_crit=random.random()<self.effective_crit_chance()

        if is_crit:
            self.total_crits+=1;combo_mult*=self.effective_crit_mult()
            earned=self.effective_click()*combo_mult

            self.dna+=earned;self.total_dna+=earned;color=self.genome.body_color(self.total_dna,self.t)

            pcount=max(1,self.particle_quality)

            if is_crit:
                for _ in range(random.randint(5,15)*pcount):
                    self.particles.append(Particle(mx,my,random.choice([GOLD,ORANGE,RED,WHITE]),lifetime=random.uniform(0.4,1.0),size=random.randint(3,9)))
                self.float_texts.append(FloatingText(mx,my-30,f"CRIT! +{fmt(earned)}",ORANGE,"lg"))
            self.shake_time=0.15;self._play(snd_crit)
        else:
            for _ in range(random.randint(2,4+min(self.combo,10))*pcount):
                self.particles.append(Particle(mx,my,color,lifetime=random.uniform(0.2,0.6),size=random.randint(2,5)))
            prefix=f"{self.combo}x "if self.combo>1 else""
            self.float_texts.append(FloatingText(mx,my-20,f"{prefix}+{fmt(earned)}",GOLD))
            self._play(snd_click)
        if self.combo>1 and self.combo%5==0:
            self._play(snd_combo)
        # Damage boss if active
        if self.boss and self.boss.alive:
            self.boss.damage(earned)
            self._play(snd_boss_hit)
            if self.boss.hp<=0:
                self.dna+=self.boss.reward;self.total_dna+=self.boss.reward
                self.float_texts.append(FloatingText(self.boss.x,self.boss.y-60,f"BOSS DEFEATED! +{fmt(self.boss.reward)}",GOLD,"lg"))
                self._play(snd_boss_die);self.bosses_defeated+=1;self.boss_tier+=1
                self._burst(self.boss.x,self.boss.y,50,[GOLD,RED,ORANGE]);self.boss=None
        self._check_achievements();self._check_milestones()

    def buy_upgrade(self,idx):
        total_cost,amount=self.upgrade_cost(idx)
        if self.dna>=total_cost and amount>0:
            self.dna-=total_cost;self.upgrade_counts[idx]+=amount;upg=UPGRADES[idx]
            if upg["type"]=="click":
                self.click_power+=upg["value"]*amount
            elif upg["type"]=="cps":self.cps+=upg["value"]*amount
            self.total_upgrades_bought+=amount;self._play(snd_buy);self._check_achievements();return True
        return False

    def activate_ability(self,idx):
        if idx>=len(ABILITIES):
            return
            ab=ABILITIES[idx]

        if not self.abilities_unlocked[idx]:
            return
        if self.ability_cooldowns[idx]>0 or self.ability_actives[idx]>0:
            return
            self.ability_actives[idx]=ab["duration"];self.ability_cooldowns[idx]=ab["cooldown"]

            self.toasts.append(Toast(f"{ab['name']}!",ab["desc"],ab["color"]))

            self._play(snd_ability);self._burst(self.creature_cx,self.creature_cy,20,[ab["color"]])


    def collect_orb(self,orb,mx,my):
        self.dna+=orb.value;self.total_dna+=orb.value;self.orbs_collected+=1;orb.alive=False
        self.float_texts.append(FloatingText(mx,my-15,f"+{fmt(orb.value)} {orb.name}",orb.color))
        for _ in range(8):
            self.particles.append(Particle(mx,my,orb.color,lifetime=0.5,size=3))
            self._play(snd_orb);self._check_achievements()


    def _start_mutation(self):
        mut=random.choice(MUTATIONS)
        self.active_mutation=mut;self.mutation_timer=mut["duration"];self.mutations_experienced+=1
        self.toasts.append(Toast(f"Mutation: {mut['name']}!",mut["desc"],mut["color"]))
        self._play(snd_mutation);self._check_achievements()

    def _grant_achievement_reward(self,ach):
        rt=ach["reward_type"];rv=ach["reward"]
        if rt=="click":
            self.ach_bonus_click+=rv
        elif rt=="cps":self.ach_bonus_cps+=rv
        elif rt=="crit_chance":self.ach_bonus_crit+=rv
        elif rt=="crit_mult":self.ach_bonus_crit_mult+=rv
        elif rt=="prestige_bonus":self.ach_bonus_prestige+=rv

    def _check_achievements(self):
        checks={"first_click":lambda:self.total_clicks>=1,"click_100":lambda:self.total_clicks>=100,
            "click_1k":lambda:self.total_clicks>=1000,"click_10k":lambda:self.total_clicks>=10000,
            "dna_100":lambda:self.total_dna>=100,"dna_10k":lambda:self.total_dna>=1e4,
            "dna_1m":lambda:self.total_dna>=1e6,"dna_1b":lambda:self.total_dna>=1e9,"dna_1t":lambda:self.total_dna>=1e12,
            "combo_5":lambda:self.max_combo>=5,"combo_20":lambda:self.max_combo>=20,"combo_50":lambda:self.max_combo>=50,
            "crit_first":lambda:self.total_crits>=1,"crit_10":lambda:self.total_crits>=10,
            "upgrade_first":lambda:self.total_upgrades_bought>=1,"upgrade_50":lambda:self.total_upgrades_bought>=50,
            "prestige_1":lambda:self.prestige_count>=1,"prestige_5":lambda:self.prestige_count>=5,
            "level_5":lambda:self.genome.level(self.total_dna)>=5,"level_10":lambda:self.genome.level(self.total_dna)>=10,
            "level_15":lambda:self.genome.level(self.total_dna)>=15,
            "cps_100":lambda:self.effective_cps()>=100,"cps_10k":lambda:self.effective_cps()>=1e4,
            "boss_1":lambda:self.bosses_defeated>=1,"boss_10":lambda:self.bosses_defeated>=10,
            "orb_50":lambda:self.orbs_collected>=50,"mutation_5":lambda:self.mutations_experienced>=5}
        for ach in ACHIEVEMENTS:
            if ach["id"]not in self.achievements_unlocked:
                chk=checks.get(ach["id"])
                if chk and chk():
                    self.achievements_unlocked.add(ach["id"]);self._grant_achievement_reward(ach)
                    self.toasts.append(Toast(f"Achievement: {ach['name']}",f"{ach['desc']} (+reward!)",GOLD))
                    self._play(snd_achieve)

    def _check_milestones(self):
        for m in self.milestones:
            if self.total_dna>=m and self.last_milestone<m:
                self.last_milestone=m;self.shake_time=0.1
                self.float_texts.append(FloatingText(self.creature_cx,self.creature_cy-100,f"MILESTONE: {fmt(m)} DNA!",CYAN,"lg"))
                self._burst(self.creature_cx,self.creature_cy,30,[GOLD,CYAN,GREEN,PINK,PURPLE])

    def _burst(self,x,y,n,colors):
        for _ in range(n):
            a=random.uniform(0,2*math.pi);sp=random.uniform(60,200)
            self.particles.append(Particle(x,y,random.choice(colors),math.cos(a)*sp,math.sin(a)*sp,random.uniform(0.6,1.5),random.randint(3,7)))

    def update(self,dt):
        self.t+=dt;self.play_time+=dt
        # Combo decay (unless Frenzy active)
        if self.ability_actives[3]<=0:
            if self.combo_timer>0:
                self.combo_timer-=dt
                if self.combo_timer<=0:
                    self.combo=0
        # Auto DNA
        auto=self.effective_cps()*dt;self.dna+=auto;self.total_dna+=auto
        self._check_achievements();self._check_milestones()
        # Particles
        for p in self.particles:
            p.update(dt)
            self.particles=[p for p in self.particles if p.alive]

        for ft in self.float_texts:
            ft.update(dt)
            self.float_texts=[ft for ft in self.float_texts if ft.alive]

        for t in self.toasts:
            t.update(dt)
            self.toasts=[t for t in self.toasts if t.alive]

        # Shake
        if self.shake_time>0:
            self.shake_time-=dt;i=self.shake_time*40;self.shake_x=random.uniform(-i,i);self.shake_y=random.uniform(-i,i)
        else:self.shake_x=self.shake_y=0
        # Ambient
        for ap in self.ambient_particles:
            ap.update(dt)
            self.sparkline.update(dt,self.effective_cps())

        # Animated DNA
        diff=self.dna-self.display_dna;self.display_dna+=diff*min(1,dt*10)
        if abs(diff)<0.5:
            self.display_dna=self.dna
        # Auto-save
        self.autosave_timer+=dt
        if self.autosave_timer>=30:
            self.autosave_timer=0;self.save()
        # Boss timer
        if not self.boss:
            self.boss_timer-=dt
            if self.boss_timer<=0:
                self.boss=Boss(self.boss_tier,self.total_dna);self.boss_timer=random.uniform(90,180)
        else:self.boss.update(dt)
        # Orb spawning
        self.orb_timer+=dt
        if self.orb_timer>random.uniform(2,5):
            self.orb_timer=0;self.orbs.append(DNAOrb(self.total_dna))
        for orb in self.orbs:
            orb.update(dt)
            self.orbs=[o for o in self.orbs if o.alive]

        # Ability timers
        for i in range(len(ABILITIES)):
            if self.ability_actives[i]>0:
                self.ability_actives[i]=max(0,self.ability_actives[i]-dt)
            if self.ability_cooldowns[i]>0:
                self.ability_cooldowns[i]=max(0,self.ability_cooldowns[i]-dt)
                if not self.abilities_unlocked[i] and self.total_dna>=ABILITIES[i]["unlock_dna"]:
                    self.abilities_unlocked[i]=True
                    self.toasts.append(Toast(f"Ability Unlocked!",f"{ABILITIES[i]['name']} [{ABILITIES[i]['key']}]",ABILITIES[i]["color"]))
        # Mutation timer
        if self.active_mutation:
            self.mutation_timer-=dt
            if self.mutation_timer<=0:
                self.active_mutation=None
        else:
            self.mutation_event_timer-=dt
            if self.mutation_event_timer<=0:
                self._start_mutation();self.mutation_event_timer=random.uniform(60,120)

    def new_creature(self):
        self.bestiary.append({"seed":self.genome.seed,"name":self.genome.proc_name(self.total_dna),
            "total_dna":self.total_dna,"prestige":self.prestige_count,"traits":self._trait_summary()})
        if len(self.bestiary)>20:
            self.bestiary=self.bestiary[-20:]
            seed=f"creature_{random.randint(1,999999)}";self.genome=Genome(seed)

            self.renderer=CreatureRenderer(self.genome);self.seed_display=seed

            self.toasts.append(Toast("New Creature!",f"Seed: {seed}",CYAN))

            self._burst(self.creature_cx,self.creature_cy,40,[CYAN,GREEN,PINK])


    def draw(self,surface):
        mx,my=pygame.mouse.get_pos();evo_lv=self.genome.level(self.total_dna)
        # BG
        for y in range(HEIGHT):
            ratio=y/HEIGHT;ls=min(evo_lv*2,30)
            r=int((BG_TOP[0]+ls*0.3)*(1-ratio)+(BG_BOT[0]+ls*0.5)*ratio)
            g=int((BG_TOP[1]+ls*0.1)*(1-ratio)+(BG_BOT[1]+ls*0.2)*ratio)
            b=int(min(255,(BG_TOP[2]+ls*0.8)*(1-ratio)+(BG_BOT[2]+ls*0.6)*ratio))
            pygame.draw.line(surface,(min(255,r),min(255,g),min(255,b)),(0,y),(WIDTH,y))
        self.starfield.draw(surface,evo_lv,self.t)
        for ap in self.ambient_particles:
            ap.draw(surface,evo_lv)
        # Orbs (behind panels)
        for orb in self.orbs:
            orb.draw(surface)
            so=(int(self.shake_x),int(self.shake_y))

        # ── Left Panel ──
        pygame.draw.rect(surface,PANEL_BG,(15+so[0],15+so[1],620,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(15+so[0],15+so[1],620,750),2,border_radius=15)
        title=font_xl.render("Procedural Creature Clicker",True,CYAN)
        surface.blit(title,(325-title.get_width()//2+so[0],22+so[1]))
        name=self.genome.proc_name(self.total_dna);color=self.genome.body_color(self.total_dna,self.t)
        surface.blit(font_lg.render(name,True,color),(325-font_lg.size(name)[0]//2+so[0],62+so[1]))
        evo_display = evo_lv
        if self.active_mutation and self.active_mutation["mult_type"]=="evo":
            evo_display += self.active_mutation["mult_value"]
        stage_txt=font_sm.render(f"Evo Lv: {evo_display:.1f} | Prestige: {self.prestige_count} ({self.prestige_mult:.2f}x)",True,MUTED)
        surface.blit(stage_txt,(325-stage_txt.get_width()//2+so[0],90+so[1]))
        # Trait tags
        traits=[]
        gd=self.genome
        if gd.limb_count(self.total_dna)>0:
            traits.append(f"{gd.limb_count(self.total_dna)} {gd.limb_style}")
        if gd.has_wings(self.total_dna):
            traits.append(f"{gd.wing_style} wings")
        if gd.eye_count(self.total_dna)>2:
            traits.append(f"{gd.eye_count(self.total_dna)} {gd.eye_style}")
        if gd.has_horns(self.total_dna):
            traits.append(f"{gd.horn_count(self.total_dna)} {gd.horn_style}")
        if gd.tail_length(self.total_dna)>0:
            traits.append(f"{gd.tail_style} tail")
        if gd.has_pattern(self.total_dna):
            traits.append(gd.pattern_type)
        if gd.has_aura(self.total_dna):
            traits.append(f"{gd.aura_style} aura")
        if traits:
            tt=font_xs.render(" | ".join(traits[:6]),True,DIM);surface.blit(tt,(325-tt.get_width()//2+so[0],108+so[1]))
        # Mutation banner
        if self.active_mutation:
            mut=self.active_mutation;flash=(math.sin(self.t*6)+1)*0.5
            mc=tuple(int(min(255,c*(0.6+0.4*flash)))for c in mut["color"])
            mt=font_md.render(f"MUTATION: {mut['name']} ({self.mutation_timer:.0f}s)",True,mc)
            surface.blit(mt,(325-mt.get_width()//2+so[0],125+so[1]))
        # Boss
        if self.boss and self.boss.alive:
            self.boss.draw(surface,self.t)
        else:
            # Creature
            dist=math.sqrt((mx-self.creature_cx)**2+(my-self.creature_cy)**2)
            bsize=self.genome.body_size(self.total_dna)
            self.creature_hover=dist<bsize*1.5 and not self.show_traits and not self.show_bestiary and not self.show_stats and not self.show_settings and not self.show_achievements_panel
            self.renderer.draw(surface,self.creature_cx+so[0],self.creature_cy+so[1],self.total_dna,self.t,self.creature_hover)
            if self.creature_hover:
                hint=font_sm.render("Click me!",True,WHITE);surface.blit(hint,(self.creature_cx-hint.get_width()//2,int(self.creature_cy+bsize+15)))
        for p in self.particles:
            p.draw(surface)
        for ft in self.float_texts:
            ft.draw(surface)
        # DNA + Combo
        dna_txt=font_xl.render(f"{fmt(self.display_dna)}",True,GOLD);surface.blit(dna_txt,(325-dna_txt.get_width()//2,490))
        if self.combo>1:
            cc=ORANGE if self.combo<10 else RED if self.combo<30 else PURPLE
            ct=font_lg.render(f"COMBO x{self.combo}",True,cc);surface.blit(ct,(325-ct.get_width()//2,468))
            bw=min(200,200*(self.combo_timer/self.combo_decay))
            pygame.draw.rect(surface,DARK_PURPLE,(225,493,200,4),border_radius=2)
            if bw>0:
                pygame.draw.rect(surface,cc,(225,493,int(bw),4),border_radius=2)
        surface.blit(font_md.render("DNA Points",True,MUTED),(325-font_md.size("DNA Points")[0]//2,525))
        # Stats line
        sl=f"Click: {fmt(self.effective_click())} | CPS: {fmt(self.effective_cps())} | Crit: {self.effective_crit_chance()*100:.0f}% | Bosses: {self.bosses_defeated}"
        surface.blit(font_xs.render(sl,True,MUTED),(325-font_xs.size(sl)[0]//2,550))
        sl2=f"Total: {fmt(self.total_dna)} | Clicks: {self.total_clicks} | Orbs: {self.orbs_collected} | Mutations: {self.mutations_experienced}"
        surface.blit(font_xs.render(sl2,True,DIM),(325-font_xs.size(sl2)[0]//2,565))
        # Sparkline
        self.sparkline.draw(surface,195,585,260,32,CYAN)
        # Ability bar
        ab_y=625
        surface.blit(font_xs.render("Abilities:",True,MUTED),(30,ab_y+2))
        for i,ab in enumerate(ABILITIES):
            ax=110+i*120;aw=110;ah=36;ar=pygame.Rect(ax,ab_y,aw,ah)
            unlocked=self.abilities_unlocked[i]
            on=self.ability_actives[i]>0;cd=self.ability_cooldowns[i]>0
            if on:
                ac=(40,80,40);bc=GREEN
            elif cd:ac=(30,25,50);bc=DIM
            elif unlocked:ac=(35,50,90);bc=ab["color"]
            else:ac=(20,18,35);bc=(40,35,60)
            pygame.draw.rect(surface,ac,ar,border_radius=6);pygame.draw.rect(surface,bc,ar,1,border_radius=6)
            # Cooldown overlay
            if cd and unlocked:
                cdr=self.ability_cooldowns[i]/ab["cooldown"]
                ch=int(ah*cdr)
                if ch>0:
                    cs=pygame.Surface((aw,ch),pygame.SRCALPHA);cs.fill((0,0,0,100));surface.blit(cs,(ax,ab_y))
                    cd_txt=font_xxs.render(f"{self.ability_cooldowns[i]:.0f}s",True,WHITE);surface.blit(cd_txt,(ax+aw//2-cd_txt.get_width()//2,ab_y+ah//2-cd_txt.get_height()//2))

            elif on:
                on_txt=font_xxs.render(f"{self.ability_actives[i]:.1f}s",True,GREEN);surface.blit(on_txt,(ax+aw//2-on_txt.get_width()//2,ab_y+ah//2-on_txt.get_height()//2))
            tc=WHITE if unlocked else DIM
            nt=font_xs.render(f"[{ab['key']}] {ab['name']}",True,tc);surface.blit(nt,(ax+4,ab_y+3))
            dt_txt=font_xxs.render(ab["desc"] if unlocked else f"Unlock: {fmt(ab['unlock_dna'])} DNA",True,MUTED if unlocked else (50,45,80))
            surface.blit(dt_txt,(ax+4,ab_y+19))
        # Trait detail panel
        if self.show_traits:
            self._draw_trait_panel(surface,so)
        # Other panels
        if self.show_bestiary:
            self._draw_bestiary(surface,so)
        if self.show_stats:
            self._draw_stats(surface,so)
        if self.show_settings:
            self._draw_settings(surface,so)
        if self.show_achievements_panel:
            self._draw_achievements_panel(surface,so)
        # ── Right Panel: Shop ──
        pygame.draw.rect(surface,PANEL_BG,(650,15,435,750),border_radius=15)
        pygame.draw.rect(surface,PANEL_BORDER,(650,15,435,750),2,border_radius=15)
        surface.blit(font_lg.render("Upgrades",True,CYAN),(867-font_lg.size("Upgrades")[0]//2,22))
        surface.blit(font_sm.render(f"DNA: {fmt(self.dna)}",True,GOLD),(665,52))
        # Buy amount
        surface.blit(font_xs.render("Buy:",True,MUTED),(830,55))
        for bi,bl in enumerate(BUY_LABELS):
            bx=865+bi*38;sel=bi==self.buy_amount_idx;bc=GREEN if sel else(40,35,80)
            pygame.draw.rect(surface,bc,(bx,52,34,16),border_radius=4)
            if sel:
                pygame.draw.rect(surface,WHITE,(bx,52,34,16),1,border_radius=4)
                surface.blit(font_xs.render(bl,True,WHITE if sel else DIM),(bx+17-font_xs.size(bl)[0]//2,53))

        # Upgrade list
        clip=pygame.Rect(655,74,425,500);surface.set_clip(clip);self.max_scroll=max(0,len(UPGRADES)*46-490)
        self.hovered_upgrade=-1
        for i,upg in enumerate(UPGRADES):
            tc,am=self.upgrade_cost(i);ca=self.dna>=tc and am>0;by=80+i*46-self.shop_scroll
            if 70<by<575:
                r=pygame.Rect(665,by,405,40);hov=r.collidepoint(mx,my)
                if hov:
                    self.hovered_upgrade=i
                    c=(40,35,90)if ca else(18,16,42)

                if ca and hov:
                    c=(55,48,110)
                    pygame.draw.rect(surface,c,r,border_radius=8);pygame.draw.rect(surface,GREEN if ca else DIM,r,1,border_radius=8)

                    key=upg.get("key","")

                if key:
                    surface.blit(font_xs.render(f"[{key}]",True,DIM),(r.x+5,r.y+4))
                    surface.blit(font_sm.render(f"{upg['name']} (x{self.upgrade_counts[i]})",True,WHITE if ca else DIM),(r.x+30,r.y+2))

                    surface.blit(font_xs.render(upg["desc"],True,MUTED if ca else(50,45,80)),(r.x+30,r.y+21))

                    cs=fmt(tc)

                if am>1:
                    cs+=f" (x{am})"
                    surface.blit(font_sm.render(cs,True,GREEN if ca else RED),(r.right-font_sm.size(cs)[0]-8,r.y+11))

        surface.set_clip(None)
        if self.max_scroll>0:
            sr=self.shop_scroll/self.max_scroll;bh=max(20,int(500*(500/(500+self.max_scroll))))
            pygame.draw.rect(surface,DIM,(1072,82+int(sr*(490-bh)),4,bh),border_radius=2)
        # Progress
        py_=590;next_m=None
        for m in self.milestones:
            if self.total_dna<m:
                next_m=m;break
        if not next_m:
            next_m=self.milestones[-1]*10
            pygame.draw.rect(surface,DARK_PURPLE,(665,py_,410,10),border_radius=5)

            prev_m=self.milestones[max(0,self.milestones.index(next_m)-1)]if next_m in self.milestones else 0

            prog=min(1,max(0,(self.total_dna-prev_m)/(next_m-prev_m)))if next_m>prev_m else 1

            fw=int(410*prog)

            if fw>0:
                for px in range(fw):
                    ratio=px/410;c=(int(60+120*ratio),int(40+180*ratio),int(180+75*ratio))
                pygame.draw.line(surface,c,(665+px,py_),(665+px,py_+9))

        pygame.draw.rect(surface,PANEL_BORDER,(665,py_,410,10),1,border_radius=5)
        surface.blit(font_xxs.render(f"Next: {fmt(next_m)} ({prog*100:.1f}%)",True,MUTED),(667,py_+12))
        # Buttons
        can_prestige=self.total_dna>=1e6
        pb=1.0+math.log10(self.total_dna/1e6)*0.5+self.ach_bonus_prestige if can_prestige else 0
        pr=pygame.Rect(665,620,130,28);ph=pr.collidepoint(mx,my)
        pygame.draw.rect(surface,(150,30,30)if can_prestige else DARK_RED,pr,border_radius=5)
        pygame.draw.rect(surface,RED if can_prestige else DIM,pr,1,border_radius=5)
        surface.blit(font_sm.render(f"Prestige [P]"if can_prestige else"Prestige (1M)",True,WHITE if can_prestige else DIM),
            (pr.centerx-font_sm.size(f"Prestige [P] +{pb:.1f}x"if can_prestige else"Prestige (1M)")[0]//2,pr.centery-7))
        nr=pygame.Rect(800,620,130,28)
        pygame.draw.rect(surface,(50,80,150)if nr.collidepoint(mx,my)else(35,55,110),nr,border_radius=5)
        pygame.draw.rect(surface,CYAN,nr,1,border_radius=5)
        surface.blit(font_sm.render("New [N]",True,WHITE),(nr.centerx-25,nr.centery-7))
        br=pygame.Rect(935,620,140,28)
        pygame.draw.rect(surface,(50,50,100)if br.collidepoint(mx,my)else(30,28,65),br,border_radius=5)
        pygame.draw.rect(surface,PANEL_BORDER,br,1,border_radius=5)
        surface.blit(font_sm.render("Bestiary [B]",True,WHITE),(br.centerx-38,br.centery-7))
        # Bottom bar
        bb=pygame.Rect(665,660,410,24)
        pygame.draw.rect(surface,(30,28,65),bb,border_radius=4);pygame.draw.rect(surface,PANEL_BORDER,bb,1,border_radius=4)
        bt="[T]raits [D]stats [A]achieve [M]settings [S]save [Tab]buy"
        surface.blit(font_xxs.render(bt,True,MUTED),(bb.centerx-font_xxs.size(bt)[0]//2,bb.centery-5))
        # Bottom info
        info=f"Achievements: {len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)} | Time: {int(self.play_time//3600)}h{int(self.play_time%3600//60)}m | Autosave 30s"
        surface.blit(font_xxs.render(info,True,DIM),(325-font_xxs.size(info)[0]//2,HEIGHT-15))
        # Tooltip
        if self.hovered_upgrade>=0:
            self._draw_tooltip(surface,self.hovered_upgrade,mx,my)
        # Toasts
        for i,toast in enumerate(self.toasts):
            toast.draw(surface,i)

    def _draw_trait_panel(self,s,so):
        px,py,pw,ph=25,150,610,280
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,230),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*PANEL_BORDER,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        gd=self.genome;td=self.total_dna;rows=[
            ("Body Size",f"{gd.body_size(td):.1f}"),("Segments",f"{gd.body_segments(td)}"),
            ("Eyes",f"{gd.eye_count(td)} ({gd.eye_style})"),("Limbs",f"{gd.limb_count(td)} ({gd.limb_style})"),
            ("Wings",f"{gd.wing_size(td):.0f} ({gd.wing_style})"if gd.has_wings(td)else"None"),
            ("Tail",f"{gd.tail_length(td):.0f} ({gd.tail_style})"),
            ("Horns",f"{gd.horn_count(td)} ({gd.horn_style})"if gd.has_horns(td)else"None"),
            ("Pattern",f"{gd.pattern_type}"if gd.has_pattern(td)else"None"),
            ("Aura",f"{gd.aura_style}"if gd.has_aura(td)else"None"),
            ("Click Mult",f"{gd.click_multiplier(td):.2f}x"),("CPS Mult",f"{gd.cps_multiplier(td):.2f}x"),
            ("Prestige",f"{self.prestige_mult:.2f}x"),("Ach Bonus Click",f"+{self.ach_bonus_click}"),
            ("Ach Bonus CPS",f"+{self.ach_bonus_cps}"),("Crit Chance",f"{self.effective_crit_chance()*100:.1f}%"),
            ("Crit Mult",f"{self.effective_crit_mult():.1f}x"),
        ]
        cols=3;cw=pw//cols
        for idx,(label,val)in enumerate(rows):
            col=idx%cols;row=idx//cols;x=px+10+col*cw+so[0];y=py+8+row*17+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+font_xs.size(label+":")[0]+4,y))

    def _draw_bestiary(self,s,so):
        px,py,pw,ph=50,80,560,580
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*CYAN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Bestiary",True,CYAN),(px+pw//2-font_lg.size("Bestiary")[0]//2+so[0],py+10+so[1]))
        if not self.bestiary:
            surface.blit(font_sm.render("No creatures yet! Prestige or press N to add entries.",True,MUTED),(px+20+so[0],py+50+so[1]))
        else:
            for i,entry in enumerate(sorted(self.bestiary,key=lambda e:
                e.get("total_dna",0),reverse=True)):
                if i>15:
                    break;ey=py+45+i*32+so[1];ex=px+15+so[0]
                # Mini creature name
                surface.blit(font_sm.render(f"{entry.get('name','?')}",True,GOLD),(ex,ey))
                tr=entry.get("traits",{})
                parts=[f"{tr.get('limbs','?')} limbs",f"{tr.get('eyes','?')} eyes",f"{tr.get('tail','?')} tail",f"Lv {tr.get('level','?')}"]
                surface.blit(font_xs.render(" | ".join(parts),True,MUTED),(ex,ey+15))
                surface.blit(font_xs.render(f"DNA: {fmt(entry.get('total_dna',0))} | Prestige #{entry.get('prestige','?')}",True,DIM),(ex+350,ey+7))

    def _draw_stats(self,s,so):
        px,py,pw,ph=50,80,560,500
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GREEN,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Statistics",True,GREEN),(px+pw//2-font_lg.size("Statistics")[0]//2+so[0],py+10+so[1]))
        hrs=int(self.play_time//3600);mins=int(self.play_time%3600//60);secs=int(self.play_time%60)
        cps_v=self.effective_cps();click_v=self.effective_click()
        rows=[
            ("Play Time",f"{hrs}h {mins}m {secs}s"),("Total DNA Earned",fmt(self.total_dna)),
            ("Current DNA",fmt(self.dna)),("Total Clicks",f"{self.total_clicks:,}"),
            ("Click Rate",f"{self.total_clicks/max(1,self.play_time):.1f}/s" if self.play_time>1 else "N/A"),
            ("Per Click",fmt(click_v)),("Per Second",fmt(cps_v)),
            ("Total Crits",f"{self.total_crits:,} ({self.total_crits/max(1,self.total_clicks)*100:.1f}%)" if self.total_clicks>0 else "0"),
            ("Max Combo",f"{self.max_combo}x"),("Upgrades Bought",f"{self.total_upgrades_bought:,}"),
            ("Prestige Count",f"{self.prestige_count}"),("Prestige Mult",f"{self.prestige_mult:.2f}x"),
            ("Bosses Defeated",f"{self.bosses_defeated}"),("Boss Tier",f"{self.boss_tier}"),
            ("Orbs Collected",f"{self.orbs_collected}"),("Mutations",f"{self.mutations_experienced}"),
            ("Achievement Bonus Click",f"+{self.ach_bonus_click}"),("Achievement Bonus CPS",f"+{self.ach_bonus_cps}"),
            ("Achievement Bonus Crit",f"+{self.ach_bonus_crit*100:.1f}%"),
            ("Creature Seed",self.seed_display),
        ]
        for idx,(label,val)in enumerate(rows):
            col=idx%2;row=idx//2;x=px+15+col*280+so[0];y=py+42+row*21+so[1]
            surface.blit(font_xs.render(f"{label}:",True,DIM),(x,y));surface.blit(font_xs.render(val,True,MUTED),(x+140,y))

    def _draw_settings(self,s,so):
        px,py,pw,ph=200,100,350,350
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*ORANGE,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render("Settings",True,ORANGE),(px+pw//2-font_lg.size("Settings")[0]//2+so[0],py+10+so[1]))
        mx,my=pygame.mouse.get_pos()
        # Sound toggle
        sr=pygame.Rect(px+20+so[0],py+50+so[1],150,30);sh=sr.collidepoint(mx,my)
        pygame.draw.rect(surface,(40,80,40)if self.sound_on else(80,30,30)if sh else DARK_RED,sr,border_radius=5)
        surface.blit(font_sm.render(f"Sound: {'ON' if self.sound_on else 'OFF'}",True,WHITE),(sr.x+10,sr.y+7))
        # Particle quality
        for qi,ql in enumerate(["Low","Med","High"]):
            qr=pygame.Rect(px+20+qi*105+so[0],py+95+so[1],95,30)
            qs=qi==self.particle_quality;qh=qr.collidepoint(mx,my)
            pygame.draw.rect(surface,(50,50,100)if(qs or qh)else(30,28,60),qr,border_radius=5)
            if qs:
                pygame.draw.rect(surface,WHITE,qr,1,border_radius=5)
                surface.blit(font_sm.render(f"Particles: {ql}",True,WHITE if qs else MUTED),(qr.x+5,qr.y+7))

        # Reset button
        rr=pygame.Rect(px+20+so[0],py+145+so[1],150,30)
        pygame.draw.rect(surface,(120,30,30)if rr.collidepoint(mx,my)else DARK_RED,rr,border_radius=5)
        surface.blit(font_sm.render("Reset Save [X]",True,RED if rr.collidepoint(mx,my)else DIM),(rr.x+10,rr.y+7))
        # Info
        lines=["Controls:","[Q/W/E/R] Activate abilities","[1-0] Buy upgrades",
               "[P] Prestige  [N] New creature","[B] Bestiary  [T] Traits",
               "[D] Stats  [A] Achievements","[M] Settings  [S] Save",
               "[Tab] Cycle buy amount","[X in Settings] Reset save","[ESC] Quit"]
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,MUTED if i>0 else WHITE),(px+20+so[0],py+190+i*16+so[1]))

    def _draw_achievements_panel(self,s,so):
        px,py,pw,ph=30,50,600,620
        ps=pygame.Surface((pw,ph),pygame.SRCALPHA);pygame.draw.rect(ps,(15,12,45,240),(0,0,pw,ph),border_radius=10)
        pygame.draw.rect(ps,(*GOLD,200),(0,0,pw,ph),2,border_radius=10);s.blit(ps,(px+so[0],py+so[1]))
        surface.blit(font_lg.render(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})",True,GOLD),
            (px+pw//2-font_lg.size(f"Achievements ({len(self.achievements_unlocked)}/{len(ACHIEVEMENTS)})")[0]//2+so[0],py+8+so[1]))
        clip=pygame.Rect(px+5,py+35,pw-10,ph-40);surface.set_clip(clip)
        for i,ach in enumerate(ACHIEVEMENTS):
            unlocked=ach["id"]in self.achievements_unlocked;ay=py+38+i*22
            if ay<py+30 or ay>py+ph-10:
                continue
                c=GOLD if unlocked else(40,35,60)

                icon="*"if unlocked else "o"

                surface.blit(font_xs.render(f"[{icon}] {ach['name']}",True,WHITE if unlocked else DIM),(px+15+so[0],ay+so[1]))

                surface.blit(font_xxs.render(f"{ach['desc']} | Reward: +{ach['reward']} {ach['reward_type']}",True,MUTED if unlocked else(50,45,70)),(px+200+so[0],ay+2+so[1]))

        surface.set_clip(None)

    def _draw_tooltip(self,surface,idx,mx,my):
        upg=UPGRADES[idx];tc,am=self.upgrade_cost(idx);lines=[upg["name"],upg["desc"],
            f"Type: {upg['type'].upper()}",f"Cost mult: x{upg['cost_mult']}/lv",
            f"Owned: {self.upgrade_counts[idx]}",f"Cost ({am}): {fmt(tc)}"]
        if upg["type"]=="click":
            nv=self.effective_click()+upg["value"]*am*self.genome.click_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"Click after: {fmt(nv)}")
        else:
            nv=self.effective_cps()+upg["value"]*am*self.genome.cps_multiplier(self.total_dna)*self.prestige_mult
            lines.append(f"CPS after: {fmt(nv)}")
        tw=max(font_xs.size(l)[0]for l in lines)+16;th=len(lines)*15+10
        tx=min(mx+15,WIDTH-tw-5);ty=min(my+15,HEIGHT-th-5)
        tip=pygame.Surface((tw,th),pygame.SRCALPHA);pygame.draw.rect(tip,(10,8,30,230),(0,0,tw,th),border_radius=6)
        pygame.draw.rect(tip,(*PANEL_BORDER,200),(0,0,tw,th),1,border_radius=6);surface.blit(tip,(tx,ty))
        for i,line in enumerate(lines):
            surface.blit(font_xs.render(line,True,GOLD if i==0 else MUTED),(tx+8,ty+5+i*15))


def fmt(n):
    if n<0:
        return"-"+fmt(-n)
    if n<1000:
        return f"{n:.1f}"if isinstance(n,float)and n!=int(n)else str(int(n))
        sfx=["","K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc"];t=0

    while n>=1000 and t<len(sfx)-1:
        n/=1000;t+=1
        return f"{n:.0f}{sfx[t]}"if n>=100 else f"{n:.1f}{sfx[t]}"if n>=10 else f"{n:.2f}{sfx[t]}"



# ─────────────── MAIN ───────────────
def main():
    game=Game();running=True
    while running:
        dt=clock.tick(60)/1000;dt=min(dt,0.05);mx,my=pygame.mouse.get_pos()
        close_panels=lambda:any([game.show_traits,game.show_bestiary,game.show_stats,game.show_settings,game.show_achievements_panel])
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                game.save();running=False
            elif event.type==pygame.KEYDOWN:
                k=event.key
                if k==pygame.K_ESCAPE:
                    if close_panels():
                        game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                    else:game.save();running=False
                elif k==pygame.K_s:game.save();game.toasts.append(Toast("Saved!","Game saved",GREEN))
                elif k==pygame.K_p:game.prestige()
                elif k==pygame.K_n:game.new_creature()
                elif k==pygame.K_t:game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_b:game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_d:game.show_stats=not game.show_stats;game.show_traits=game.show_bestiary=game.show_settings=game.show_achievements_panel=False
                elif k==pygame.K_a:game.show_achievements_panel=not game.show_achievements_panel;game.show_traits=game.show_bestiary=game.show_stats=game.show_settings=False
                elif k==pygame.K_m:game.show_settings=not game.show_settings;game.show_traits=game.show_bestiary=game.show_stats=game.show_achievements_panel=False
                elif k==pygame.K_TAB:game.buy_amount_idx=(game.buy_amount_idx+1)%len(BUY_AMOUNTS)
                elif k==pygame.K_q:game.activate_ability(0)
                elif k==pygame.K_w:game.activate_ability(1)
                elif k==pygame.K_e:game.activate_ability(2)
                elif k==pygame.K_r:game.activate_ability(3)
                km={pygame.K_1:0,pygame.K_2:1,pygame.K_3:2,pygame.K_4:3,pygame.K_5:4,pygame.K_6:5,pygame.K_7:6,pygame.K_8:7,pygame.K_9:8,pygame.K_0:9}
                if k in km:
                    game.buy_upgrade(km[k])
            elif event.type==pygame.MOUSEBUTTONDOWN:
                if event.button==1:
                    # Check orbs first
                    for orb in game.orbs:
                        if orb.alive and orb.hit_test(mx,my):
                            game.collect_orb(orb,mx,my);break
                    else:
                        if game.creature_hover and not close_panels():
                            game.click_creature(mx,my)
                            for i in range(len(UPGRADES)):
                                by=80+i*46-game.shop_scroll;r=pygame.Rect(665,by,405,40)
                                if r.collidepoint(mx,my):
                                    game.buy_upgrade(i)
                        for bi in range(len(BUY_LABELS)):
                            if pygame.Rect(865+bi*38,52,34,16).collidepoint(mx,my):
                                game.buy_amount_idx=bi
                        if pygame.Rect(665,620,130,28).collidepoint(mx,my):
                            game.prestige()
                        if pygame.Rect(800,620,130,28).collidepoint(mx,my):
                            game.new_creature()
                        if pygame.Rect(935,620,140,28).collidepoint(mx,my):
                            game.show_bestiary=not game.show_bestiary;game.show_traits=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        if pygame.Rect(665,660,410,24).collidepoint(mx,my):
                            game.show_traits=not game.show_traits;game.show_bestiary=game.show_stats=game.show_settings=game.show_achievements_panel=False
                        # Settings panel clicks
                        if game.show_settings:
                            spx,spy=200+int(game.shake_x),100+int(game.shake_y)
                            if pygame.Rect(spx+20,spy+50,150,30).collidepoint(mx,my):
                                game.sound_on=not game.sound_on
                                for qi in range(3):
for                                f pygame.Rect(spx+20+qi*105,spy+95,95,30).collidepoint(mx,my):

                                    game.particle_quality=qi
                            if pygame.Rect(spx+20,spy+145,150,30).collidepoint(mx,my):
                                if os.path.exists(SAVE_FILE):
                                    os.remove(SAVE_FILE)
                                    game.toasts.append(Toast("Reset!","Save file deleted. Restart to start fresh.",RED))

                        # Ability bar clicks
                        for ai in range(len(ABILITIES)):
                            ar=pygame.Rect(110+ai*120,625,110,36)
                            if ar.collidepoint(mx,my):
                                game.activate_ability(ai)
                elif event.button==4:game.shop_scroll=max(0,game.shop_scroll-40)
                elif event.button==5:game.shop_scroll=min(game.max_scroll,game.shop_scroll+40)
        # Ambient particles
        if game.effective_cps()>0 and random.random()<dt*2*game.particle_quality:
            a=random.uniform(0,2*math.pi);d=random.uniform(40,80)
            c=game.genome.accent_color(game.total_dna,game.t)
            game.particles.append(Particle(game.creature_cx+math.cos(a)*d,game.creature_cy+math.sin(a)*d*0.7,c,random.uniform(-15,15),random.uniform(-35,-10),0.5,random.randint(2,4)))
        game.update(dt);game.draw(screen);pygame.display.flip()
    pygame.quit();sys.exit()

if __name__=="__main__":

    main()


qi in range(3):
for                                f pygame.Rect(spx+20+qi*105,spy+95,95,30).collidepoint(mx,my):

                                    game.particle_quality=qi
                            if pygame.Rect(spx+20,spy+145,150,30).collidepoint(mx,my):
                                if os.path.exists(SAVE_FILE):
                                    os.remove(SAVE_FILE)
                                    game.toasts.append(Toast("Reset!","Save file deleted. Restart to start fresh.",RED))

                        # Ability bar clicks
                        for ai in range(len(ABILITIES)):
                            ar=pygame.Rect(110+ai*120,625,110,36)
                            if ar.collidepoint(mx,my):
                                game.activate_ability(ai)
                elif event.button==4:game.shop_scroll=max(0,game.shop_scroll-40)
                elif event.button==5:game.shop_scroll=min(game.max_scroll,game.shop_scroll+40)
        # Ambient particles
        if game.effective_cps()>0 and random.random()<dt*2*game.particle_quality:
            a=random.uniform(0,2*math.pi);d=random.uniform(40,80)
            c=game.genome.accent_color(game.total_dna,game.t)
            game.particles.append(Particle(game.creature_cx+math.cos(a)*d,game.creature_cy+math.sin(a)*d*0.7,c,random.uniform(-15,15),random.uniform(-35,-10),0.5,random.randint(2,4)))
        game.update(dt);game.draw(screen);pygame.display.flip()
    pygame.quit();sys.exit()

if __name__=="__main__":

    main()


