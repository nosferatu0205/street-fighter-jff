import pygame
import sys
import random
import math
from pygame.locals import *

# Initialize pygame
pygame.init()

# Game Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
GRAVITY = 0.6
JUMP_STRENGTH = -12
FLOOR_HEIGHT = SCREEN_HEIGHT - 100

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)

# Game States
MENU = 0
CHARACTER_SELECT = 1
FIGHTING = 2
GAME_OVER = 3

# Create screen and clock
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Python Street Fighter")
clock = pygame.time.Clock()

# Load fonts
title_font = pygame.font.SysFont('Impact', 64)
menu_font = pygame.font.SysFont('Arial', 36)
hud_font = pygame.font.SysFont('Arial', 24)

# Sound effects
try:
    pygame.mixer.init()
    punch_sound = pygame.mixer.Sound('punch.wav')
    kick_sound = pygame.mixer.Sound('kick.wav')
    special_sound = pygame.mixer.Sound('special.wav')
except:
    print("Sound files not found. Using silent placeholders.")
    punch_sound = kick_sound = special_sound = pygame.mixer.Sound(bytes(0))

# Simple particle system for special effects
class Particle:
    def __init__(self, x, y, color, vel_x, vel_y, size, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.size = size
        self.lifetime = lifetime
        self.age = 0
    
    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y += GRAVITY * 0.1
        self.age += 1
        # Shrink particle as it ages
        self.size = max(1, self.size * 0.95)
        return self.age < self.lifetime
    
    def draw(self, surface):
        alpha = int(255 * (1 - self.age / self.lifetime))
        particle_color = (*self.color, alpha)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, particle_color, (self.size, self.size), self.size)
        surface.blit(s, (self.x - self.size, self.y - self.size))

# Character base class
class Fighter:
    def __init__(self, name, x, y, width, height, color, hp, speed, jump_strength):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.max_hp = hp
        self.hp = hp
        self.speed = speed
        self.jump_strength = jump_strength
        self.vel_x = 0
        self.vel_y = 0
        self.facing_right = True
        self.is_jumping = False
        self.is_attacking = False
        self.is_blocking = False
        self.attack_cooldown = 0
        self.special_cooldown = 0
        self.hit_cooldown = 0
        self.combo_counter = 0
        self.combo_timer = 0
        self.particles = []
        
        # Animation states
        self.frame = 0
        self.animation_speed = 0.2
        self.state = "idle"  # idle, walk, jump, attack, special, hit, block
        
        # Attack properties
        self.attack_damage = 10
        self.attack_range = 60
        self.attack_duration = 20

    def update(self, opponent):
        # Apply gravity
        self.vel_y += GRAVITY
        
        # Apply velocity
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Floor collision
        if self.y + self.height > FLOOR_HEIGHT:
            self.y = FLOOR_HEIGHT - self.height
            self.vel_y = 0
            self.is_jumping = False
        
        # Screen boundaries
        if self.x < 0:
            self.x = 0
        if self.x + self.width > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.width
        
        # Cooldowns
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown == 0:
                self.is_attacking = False
        
        if self.special_cooldown > 0:
            self.special_cooldown -= 1
        
        if self.hit_cooldown > 0:
            self.hit_cooldown -= 1
        
        # Combo system
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo_counter = 0
        
        # Update particles
        self.particles = [p for p in self.particles if p.update()]
        
        # Animation
        self.frame += self.animation_speed
        if self.frame >= 4:  # 4 frames per animation
            self.frame = 0
        
        # Determine facing direction based on opponent position
        if opponent:
            if self.x + self.width/2 < opponent.x + opponent.width/2:
                self.facing_right = True
            else:
                self.facing_right = False
                
    def move(self, direction):
        if not self.is_attacking and not self.is_blocking:
            self.vel_x = self.speed * direction
            if direction != 0:
                self.state = "walk"
            else:
                self.state = "idle"
    
    def jump(self):
        if not self.is_jumping and not self.is_attacking and not self.is_blocking:
            self.vel_y = self.jump_strength
            self.is_jumping = True
            self.state = "jump"
    
    def attack(self):
        if not self.is_attacking and not self.is_blocking and self.attack_cooldown == 0:
            self.is_attacking = True
            self.attack_cooldown = self.attack_duration
            self.state = "attack"
            self.vel_x = 0  # Stop movement during attack
            punch_sound.play()
            return True
        return False
    
    def special_attack(self):
        if not self.is_attacking and not self.is_blocking and self.special_cooldown == 0:
            self.is_attacking = True
            self.attack_cooldown = self.attack_duration * 1.5
            self.special_cooldown = 120  # 2 second cooldown
            self.state = "special"
            self.vel_x = 0
            special_sound.play()
            return True
        return False
    
    def block(self, is_blocking):
        if not self.is_attacking:
            self.is_blocking = is_blocking
            if is_blocking:
                self.state = "block"
                self.vel_x = 0
            else:
                self.state = "idle"
    
    def take_damage(self, damage, knockback=0):
        if self.hit_cooldown == 0:
            if self.is_blocking:
                damage = damage * 0.3  # 70% damage reduction when blocking
            
            self.hp -= damage
            self.hit_cooldown = 15  # Brief invincibility
            self.state = "hit"
            
            # Apply knockback
            direction = -1 if self.facing_right else 1
            self.vel_x = knockback * direction
            
            # Create hit particles
            for _ in range(10):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(1, 3)
                self.particles.append(
                    Particle(
                        self.x + self.width/2, 
                        self.y + self.height/2,
                        (255, 0, 0),
                        math.cos(angle) * speed,
                        math.sin(angle) * speed,
                        random.uniform(2, 5),
                        random.randint(20, 30)
                    )
                )
            
            return True
        return False
    
    def check_hit(self, opponent):
        if self.is_attacking and self.attack_cooldown > self.attack_duration / 2:
            # Attack hitbox depends on facing direction
            if self.facing_right:
                attack_x = self.x + self.width
                attack_width = self.attack_range
            else:
                attack_x = self.x - self.attack_range
                attack_width = self.attack_range
                
            # Check collision with opponent
            if (attack_x < opponent.x + opponent.width and 
                attack_x + attack_width > opponent.x and
                self.y < opponent.y + opponent.height and
                self.y + self.height > opponent.y):
                
                # Calculate damage based on current action
                damage = self.attack_damage
                knockback = 5
                
                if self.state == "special":
                    damage *= 2
                    knockback = 10
                
                # Apply combo system
                if self.combo_counter > 0:
                    damage *= (1 + self.combo_counter * 0.1)  # 10% more damage per combo hit
                
                if opponent.take_damage(damage, knockback):
                    self.combo_counter += 1
                    self.combo_timer = 90  # 1.5 seconds to continue combo
                
                return True
        return False
    
    def draw(self, surface):
        # Draw fighter
        frame_int = int(self.frame)
        
        # Base fighter shape
        fighter_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # Different visual based on state
        if self.state == "idle":
            # Just the base character with subtle breathing animation
            y_offset = math.sin(self.frame * 0.5) * 2
            fighter_rect.y += y_offset
            
        elif self.state == "walk":
            # Walking animation - shift position slightly
            x_offset = math.sin(self.frame * math.pi) * 3
            if not self.facing_right:
                x_offset *= -1
            fighter_rect.x += x_offset
            
        elif self.state == "jump":
            # Jump animation - stretch vertically
            stretch = max(0, 1 - abs(self.vel_y) / self.jump_strength)
            fighter_rect.height = self.height * (1 - stretch * 0.2)
            fighter_rect.width = self.width * (1 + stretch * 0.1)
            
        elif self.state == "attack":
            # Attack animation - extend in attack direction
            attack_extend = (self.attack_duration - self.attack_cooldown) / self.attack_duration
            attack_extend = 1 - abs(2 * attack_extend - 1)  # Make it go out and back
            
            if self.facing_right:
                fighter_rect.width = self.width * (1 + attack_extend * 0.3)
            else:
                width_extend = self.width * attack_extend * 0.3
                fighter_rect.x -= width_extend
                fighter_rect.width = self.width + width_extend
                
        elif self.state == "special":
            # Special attack animation - pulsate
            scale = 1 + 0.2 * math.sin(self.frame * math.pi)
            center_x = fighter_rect.x + fighter_rect.width / 2
            center_y = fighter_rect.y + fighter_rect.height / 2
            
            fighter_rect.width = self.width * scale
            fighter_rect.height = self.height * scale
            fighter_rect.x = center_x - fighter_rect.width / 2
            fighter_rect.y = center_y - fighter_rect.height / 2
            
            # Add energy particles
            if random.random() < 0.3:
                for _ in range(3):
                    angle = random.uniform(0, math.pi * 2)
                    self.particles.append(
                        Particle(
                            center_x, 
                            center_y,
                            self.color,
                            math.cos(angle) * random.uniform(1, 3),
                            math.sin(angle) * random.uniform(1, 3),
                            random.uniform(3, 7),
                            random.randint(20, 40)
                        )
                    )
                
        elif self.state == "hit":
            # Hit animation - compress slightly
            fighter_rect.width = self.width * 0.9
            fighter_rect.height = self.height * 0.9
            fighter_rect.x += self.width * 0.05
            fighter_rect.y += self.height * 0.05
            
        elif self.state == "block":
            # Block animation - shift arms (indicated by color change)
            block_rect = fighter_rect.copy()
            if self.facing_right:
                block_rect.width = self.width * 0.2
                pygame.draw.rect(surface, (100, 100, 100), block_rect)
                fighter_rect.x += self.width * 0.2
                fighter_rect.width = self.width * 0.8
            else:
                block_rect.x = fighter_rect.right - self.width * 0.2
                block_rect.width = self.width * 0.2
                pygame.draw.rect(surface, (100, 100, 100), block_rect)
                fighter_rect.width = self.width * 0.8
        
        # Draw the character
        pygame.draw.rect(surface, self.color, fighter_rect)
        
        # Draw eyes to indicate facing direction
        eye_x = fighter_rect.x + fighter_rect.width * (0.7 if self.facing_right else 0.3)
        eye_y = fighter_rect.y + fighter_rect.height * 0.3
        eye_radius = max(3, min(fighter_rect.width, fighter_rect.height) * 0.1)
        pygame.draw.circle(surface, BLACK, (eye_x, eye_y), eye_radius)
        
        # Draw particles
        for particle in self.particles:
            particle.draw(surface)
        
        # Draw health bar
        health_width = 100
        health_height = 10
        health_x = self.x + (self.width - health_width) / 2
        health_y = self.y - 20
        
        # Background
        pygame.draw.rect(surface, BLACK, (health_x - 2, health_y - 2, health_width + 4, health_height + 4))
        # Health
        health_percent = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surface, RED, (health_x, health_y, health_width * health_percent, health_height))
        
        # Draw special attack cooldown
        if self.special_cooldown > 0:
            cooldown_width = 80
            cooldown_height = 5
            cooldown_x = self.x + (self.width - cooldown_width) / 2
            cooldown_y = self.y - 30
            
            cooldown_percent = self.special_cooldown / 120
            pygame.draw.rect(surface, BLACK, (cooldown_x, cooldown_y, cooldown_width, cooldown_height))
            pygame.draw.rect(surface, YELLOW, 
                            (cooldown_x, cooldown_y, cooldown_width * (1 - cooldown_percent), cooldown_height))
        
        # Draw name
        name_text = hud_font.render(self.name, True, WHITE)
        surface.blit(name_text, (self.x + self.width/2 - name_text.get_width()/2, self.y - 45))
        
        # Draw combo counter if active
        if self.combo_counter > 1:
            combo_text = hud_font.render(f"{self.combo_counter}x Combo!", True, YELLOW)
            surface.blit(combo_text, (self.x + self.width/2 - combo_text.get_width()/2, self.y - 70))

        # Debug - draw attack hitbox
        if self.is_attacking:
            if self.facing_right:
                attack_rect = pygame.Rect(self.x + self.width, self.y, self.attack_range, self.height)
            else:
                attack_rect = pygame.Rect(self.x - self.attack_range, self.y, self.attack_range, self.height)
            pygame.draw.rect(surface, (255, 0, 0, 128), attack_rect, 1)

# Define unique fighters
class NinjaFighter(Fighter):
    def __init__(self, x, y):
        super().__init__("Shadow Ninja", x, y, 40, 80, BLACK, 100, 5, JUMP_STRENGTH - 2)
        self.attack_damage = 8  # Less damage
        self.attack_range = 50  # Less range
        self.dash_cooldown = 0
        self.can_double_jump = True
        self.has_double_jumped = False
    
    def update(self, opponent):
        super().update(opponent)
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
            
        # Reset double jump when landing
        if not self.is_jumping:
            self.has_double_jumped = False
    
    def jump(self):
        if not self.is_jumping:
            super().jump()
        elif self.can_double_jump and not self.has_double_jumped:
            self.vel_y = self.jump_strength * 0.8
            self.has_double_jumped = True
            self.state = "jump"
            
            # Create jump effect
            for _ in range(5):
                self.particles.append(
                    Particle(
                        self.x + self.width/2, 
                        self.y + self.height,
                        (100, 100, 100),
                        random.uniform(-1, 1),
                        random.uniform(1, 3),
                        random.uniform(3, 5),
                        random.randint(10, 20)
                    )
                )
    
    def dash(self, direction):
        if self.dash_cooldown == 0 and not self.is_attacking:
            self.vel_x = direction * 15
            self.dash_cooldown = 45
            
            # Create dash effect
            for _ in range(10):
                self.particles.append(
                    Particle(
                        self.x + (0 if direction > 0 else self.width), 
                        self.y + random.uniform(0, self.height),
                        (50, 50, 50),
                        -direction * random.uniform(2, 4),
                        random.uniform(-1, 1),
                        random.uniform(2, 4),
                        random.randint(10, 20)
                    )
                )
            return True
        return False
    
    def special_attack(self):
        if super().special_attack():
            # Teleport behind opponent and attack
            return True
        return False
    
    def check_hit(self, opponent):
        # If in special attack and we're in the right frame, teleport behind opponent
        if self.state == "special" and self.attack_cooldown == int(self.attack_duration * 0.75):
            # Determine which side to teleport to
            teleport_x = opponent.x + opponent.width + 10
            if teleport_x + self.width > SCREEN_WIDTH:
                teleport_x = opponent.x - self.width - 10
                
            # Create smoke effect at current position
            for _ in range(15):
                self.particles.append(
                    Particle(
                        self.x + self.width/2, 
                        self.y + self.height/2,
                        (100, 100, 100),
                        random.uniform(-2, 2),
                        random.uniform(-2, 2),
                        random.uniform(3, 6),
                        random.randint(20, 40)
                    )
                )
                
            # Teleport
            self.x = teleport_x
            
            # Create smoke effect at new position
            for _ in range(15):
                self.particles.append(
                    Particle(
                        self.x + self.width/2, 
                        self.y + self.height/2,
                        (100, 100, 100),
                        random.uniform(-2, 2),
                        random.uniform(-2, 2),
                        random.uniform(3, 6),
                        random.randint(20, 40)
                    )
                )
        
        return super().check_hit(opponent)

class ElectricFighter(Fighter):
    def __init__(self, x, y):
        super().__init__("Volt Striker", x, y, 50, 90, BLUE, 90, 4, JUMP_STRENGTH)
        self.attack_damage = 12
        self.charge_level = 0
        self.max_charge = 100
    
    def update(self, opponent):
        super().update(opponent)
        
        # Slowly build charge when on ground
        if not self.is_jumping and not self.is_attacking:
            self.charge_level = min(self.max_charge, self.charge_level + 0.2)
        
        # Electric particles based on charge
        if random.random() < self.charge_level / 500:  # Higher chance with more charge
            self.particles.append(
                Particle(
                    self.x + random.uniform(0, self.width), 
                    self.y + random.uniform(0, self.height),
                    (0, 200, 255),
                    random.uniform(-1, 1),
                    random.uniform(-3, -1),
                    random.uniform(1, 3),
                    random.randint(10, 20)
                )
            )
    
    def attack(self):
        if super().attack():
            # Standard attack uses some charge
            if self.charge_level > 10:
                self.attack_damage = 12 + int(self.charge_level / 20)
                self.charge_level -= 10
            else:
                self.attack_damage = 12
            return True
        return False
    
    def special_attack(self):
        if self.charge_level >= 50 and super().special_attack():
            # Lightning strike attack
            self.charge_level -= 50
            
            # Create lightning effect
            for _ in range(30):
                height_position = random.uniform(0, 1)
                self.particles.append(
                    Particle(
                        self.x + self.width/2 + random.uniform(-50, 50), 
                        self.y * height_position,
                        (0, 200, 255),
                        random.uniform(-1, 1),
                        random.uniform(5, 15),
                        random.uniform(2, 5),
                        random.randint(10, 30)
                    )
                )
            return True
        return False
    
    def draw(self, surface):
        super().draw(surface)
        
        # Draw charge meter
        charge_width = 80
        charge_height = 5
        charge_x = self.x + (self.width - charge_width) / 2
        charge_y = self.y - 35
        
        pygame.draw.rect(surface, BLACK, (charge_x, charge_y, charge_width, charge_height))
        pygame.draw.rect(surface, CYAN, 
                        (charge_x, charge_y, charge_width * (self.charge_level / self.max_charge), charge_height))

class FireFighter(Fighter):
    def __init__(self, x, y):
        super().__init__("Flame Master", x, y, 55, 85, RED, 110, 3.5, JUMP_STRENGTH + 1)
        self.attack_damage = 15
        self.heat_level = 0
        self.max_heat = 100
        self.overheated = False
        self.fireball_cooldown = 0
    
    def update(self, opponent):
        super().update(opponent)
        
        # Heat management
        if self.overheated:
            self.heat_level -= 0.5
            if self.heat_level <= 0:
                self.heat_level = 0
                self.overheated = False
        
        # Fire particles
        if not self.overheated and random.random() < 0.1 + (self.heat_level / 200):
            self.particles.append(
                Particle(
                    self.x + random.uniform(0, self.width), 
                    self.y + random.uniform(self.height * 0.7, self.height),
                    (255, random.randint(100, 200), 0),
                    random.uniform(-1, 1),
                    random.uniform(-4, -2),
                    random.uniform(2, 4),
                    random.randint(15, 25)
                )
            )
        
        if self.fireball_cooldown > 0:
            self.fireball_cooldown -= 1
    
    def attack(self):
        if not self.overheated and super().attack():
            # Attacks generate heat
            self.heat_level = min(self.max_heat, self.heat_level + 15)
            
            # More damage with more heat
            heat_bonus = int(self.heat_level / 20)
            self.attack_damage = 15 + heat_bonus
            
            # Check for overheat
            if self.heat_level >= self.max_heat:
                self.overheated = True
            
            return True
        return False
    
    def special_attack(self):
        if not self.overheated and self.heat_level >= 40 and self.fireball_cooldown == 0:
            if super().special_attack():
                # Fireball attack
                self.heat_level -= 40
                self.fireball_cooldown = 90
                return True
        return False
    
    def check_hit(self, opponent):
        # For special, create fireball projectile effect
        if self.state == "special" and self.attack_cooldown == int(self.attack_duration * 0.8):
            # Create fireball effect moving forward
            direction = 1 if self.facing_right else -1
            for _ in range(20):
                speed_x = direction * random.uniform(5, 8)
                self.particles.append(
                    Particle(
                        self.x + (self.width if direction > 0 else 0), 
                        self.y + self.height/2,
                        (255, random.randint(100, 200), 0),
                        speed_x,
                        random.uniform(-2, 2),
                        random.uniform(3, 7),
                        random.randint(30, 50)
                    )
                )
                
            # Extend attack range for fireball
            old_range = self.attack_range
            self.attack_range = 150
            hit = super().check_hit(opponent)
            self.attack_range = old_range
            return hit
        
        return super().check_hit(opponent)
    
    def draw(self, surface):
        super().draw(surface)
        
        # Draw heat meter
        heat_width = 80
        heat_height = 5
        heat_x = self.x + (self.width - heat_width) / 2
        heat_y = self.y - 35
        
        pygame.draw.rect(surface, BLACK, (heat_x, heat_y, heat_width, heat_height))
        heat_color = RED if self.overheated else ORANGE
        pygame.draw.rect(surface, heat_color, 
                        (heat_x, heat_y, heat_width * (self.heat_level / self.max_heat), heat_height))

class EarthFighter(Fighter):
    def __init__(self, x, y):
        super().__init__("Stone Titan", x, y, 60, 95, (139, 69, 19), 140, 2.5, JUMP_STRENGTH + 3)  # Brown color
        self.attack_damage = 20
        self.attack_range = 50
        self.stone_armor = 30
        self.max_stone_armor = 30
        self.armor_regen_rate = 0.1
    
    def update(self, opponent):
        super().update(opponent)
        
        # Regenerate stone armor slowly
        if self.stone_armor < self.max_stone_armor:
            self.stone_armor = min(self.max_stone_armor, self.stone_armor + self.armor_regen_rate)
    
    def take_damage(self, damage, knockback=0):
        # Stone armor absorbs damage first
        if self.stone_armor > 0:
            absorbed = min(self.stone_armor, damage)
            self.stone_armor -= absorbed
            damage -= absorbed
            
            # Create stone particle effect
            for _ in range(int(absorbed / 2)):
                self.particles.append(
                    Particle(
                        self.x + random.uniform(0, self.width), 
                        self.y + random.uniform(0, self.height),
                        (139, 69, 19),
                        random.uniform(-3, 3),
                        random.uniform(-3, 0),
                        random.uniform(2, 5),
                        random.randint(20, 40)
                    )
                )
        
        # Reduced knockback
        return super().take_damage(damage, knockback * 0.7)
    
    def special_attack(self):
        if super().special_attack():
            # Ground slam - fully regenerate armor but slow afterward
            self.stone_armor = self.max_stone_armor
            self.speed *= 0.8  # Temporary speed decrease
            
            # Stone eruption effect
            for _ in range(30):
                distance = random.uniform(20, 150)
                angle = random.uniform(0, math.pi)
                if not self.facing_right:
                    angle = math.pi - angle
                    
                self.particles.append(
                    Particle(
                        self.x + self.width/2 + math.cos(angle) * distance, 
                        FLOOR_HEIGHT - random.uniform(10, 30),
                        (139, 69, 19),
                        random.uniform(-1, 1),
                        random.uniform(-10, -5),
                        random.uniform(5, 10),
                        random.randint(30, 60)
                    )
                )
            
            return True
        return False
    
    def draw(self, surface):
        super().draw(surface)
        
        # Draw armor meter
        armor_width = 80
        armor_height = 5
        armor_x = self.x + (self.width - armor_width) / 2
        armor_y = self.y - 35
        
        pygame.draw.rect(surface, BLACK, (armor_x, armor_y, armor_width, armor_height))
        pygame.draw.rect(surface, (139, 69, 19), 
                        (armor_x, armor_y, armor_width * (self.stone_armor / self.max_stone_armor), armor_height))

# Background elements
class Background:
    def __init__(self, theme="dojo"):
        self.theme = theme
        self.elements = []
        
        if theme == "dojo":
            # Wooden floor
            self.floor_color = (139, 69, 19)
            # Background elements - windows, wall decorations
            for i in range(5):
                self.elements.append({
                    'type': 'window',
                    'x': 100 + i * 150,
                    'y': 100,
                    'width': 80,
                    'height': 120
                })
                
        elif theme == "street":
            # Concrete floor
            self.floor_color = (100, 100, 100)
            # Street elements - buildings, cars, etc.
            for i in range(3):
                self.elements.append({
                    'type': 'building',
                    'x': i * 250,
                    'y': 50,
                    'width': 200,
                    'height': 250
                })
            
        elif theme == "arena":
            # Arena floor
            self.floor_color = (200, 180, 100)
            # Arena elements - crowd, banners, etc.
            for i in range(8):
                self.elements.append({
                    'type': 'crowd',
                    'x': i * 100,
                    'y': 150,
                    'width': 80,
                    'height': 30
                })
    
    def draw(self, surface):
        # Draw sky/background
        if self.theme == "dojo":
            pygame.draw.rect(surface, (150, 120, 90), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        elif self.theme == "street":
            pygame.draw.rect(surface, (100, 150, 200), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        elif self.theme == "arena":
            pygame.draw.rect(surface, (50, 50, 80), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Draw background elements
        for element in self.elements:
            if element['type'] == 'window':
                pygame.draw.rect(surface, (200, 200, 255), 
                               (element['x'], element['y'], element['width'], element['height']))
                pygame.draw.rect(surface, (100, 100, 100), 
                               (element['x'], element['y'], element['width'], element['height']), 3)
                
            elif element['type'] == 'building':
                pygame.draw.rect(surface, (80, 80, 80), 
                               (element['x'], element['y'], element['width'], element['height']))
                
                # Windows
                for wy in range(4):
                    for wx in range(3):
                        window_x = element['x'] + 20 + wx * 60
                        window_y = element['y'] + 30 + wy * 50
                        pygame.draw.rect(surface, (255, 255, 200), 
                                       (window_x, window_y, 40, 30))
                
            elif element['type'] == 'crowd':
                # Random crowd color
                for p in range(10):
                    person_color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                    pygame.draw.circle(surface, person_color, 
                                    (element['x'] + random.randint(0, element['width']), 
                                     element['y'] + random.randint(0, element['height'])), 
                                    random.randint(5, 10))
        
        # Draw floor
        pygame.draw.rect(surface, self.floor_color, (0, FLOOR_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_HEIGHT))
        
        # Draw floor details
        if self.theme == "dojo":
            # Wood grain
            for i in range(5):
                pygame.draw.line(surface, (100, 50, 0), 
                               (0, FLOOR_HEIGHT + 20 + i * 15), 
                               (SCREEN_WIDTH, FLOOR_HEIGHT + 20 + i * 15), 2)
                
        elif self.theme == "street":
            # Street markings
            pygame.draw.rect(surface, (255, 255, 255), 
                           (50, FLOOR_HEIGHT + 30, 100, 20))
            pygame.draw.rect(surface, (255, 255, 255), 
                           (250, FLOOR_HEIGHT + 30, 100, 20))
            pygame.draw.rect(surface, (255, 255, 255), 
                           (450, FLOOR_HEIGHT + 30, 100, 20))
            pygame.draw.rect(surface, (255, 255, 255), 
                           (650, FLOOR_HEIGHT + 30, 100, 20))
            
        elif self.theme == "arena":
            # Arena circle
            pygame.draw.circle(surface, (255, 255, 255), 
                             (SCREEN_WIDTH // 2, FLOOR_HEIGHT + 50), 150, 5)

# Main game functions
def draw_menu(screen):
    screen.fill(BLACK)
    
    # Title
    title_text = title_font.render("PYTHON STREET FIGHTER", True, RED)
    screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, 100))
    
    # Menu options
    start_text = menu_font.render("PRESS ENTER TO START", True, WHITE)
    screen.blit(start_text, (SCREEN_WIDTH//2 - start_text.get_width()//2, 300))
    
    controls_text = menu_font.render("Player 1: WASD + F/G    Player 2: Arrows + K/L", True, WHITE)
    screen.blit(controls_text, (SCREEN_WIDTH//2 - controls_text.get_width()//2, 400))
    
    pygame.display.flip()

def draw_character_select(screen, p1_selection, p2_selection, characters):
    screen.fill(BLACK)
    
    # Title
    title_text = title_font.render("SELECT YOUR FIGHTER", True, RED)
    screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, 50))
    
    # Character selection boxes
    box_width = 150
    box_height = 200
    spacing = 30
    total_width = len(characters) * box_width + (len(characters) - 1) * spacing
    start_x = (SCREEN_WIDTH - total_width) // 2
    
    for i, (name, color, _) in enumerate(characters):
        x = start_x + i * (box_width + spacing)
        y = 150
        
        # Box background
        pygame.draw.rect(screen, color, (x, y, box_width, box_height))
        
        # Character name
        name_text = menu_font.render(name, True, WHITE)
        screen.blit(name_text, (x + box_width//2 - name_text.get_width()//2, y + box_height + 20))
        
        # Selection indicators
        if p1_selection == i:
            pygame.draw.rect(screen, RED, (x, y, box_width, box_height), 5)
            p1_text = menu_font.render("P1", True, RED)
            screen.blit(p1_text, (x + 10, y + 10))
            
        if p2_selection == i:
            pygame.draw.rect(screen, BLUE, (x, y, box_width, box_height), 5)
            p2_text = menu_font.render("P2", True, BLUE)
            screen.blit(p2_text, (x + box_width - 40, y + 10))
    
    # Instructions
    instructions_text = menu_font.render("PRESS ENTER TO FIGHT", True, WHITE)
    screen.blit(instructions_text, (SCREEN_WIDTH//2 - instructions_text.get_width()//2, 500))
    
    pygame.display.flip()

def draw_fighting(screen, p1, p2, background):
    screen.fill(BLACK)
    
    # Draw background
    background.draw(screen)
    
    # Draw fighters
    p1.draw(screen)
    p2.draw(screen)
    
    # Draw timer
    timer_text = hud_font.render(f"FIGHT!", True, WHITE)
    screen.blit(timer_text, (SCREEN_WIDTH//2 - timer_text.get_width()//2, 30))
    
    pygame.display.flip()

def draw_game_over(screen, winner, loser):
    screen.fill(BLACK)
    
    # Winner text
    winner_text = title_font.render(f"{winner.name} WINS!", True, winner.color)
    screen.blit(winner_text, (SCREEN_WIDTH//2 - winner_text.get_width()//2, 200))
    
    # Restart text
    restart_text = menu_font.render("PRESS ENTER TO PLAY AGAIN", True, WHITE)
    screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, 350))
    
    pygame.display.flip()

# Main game loop
def main():
    game_state = MENU
    running = True
    
    # Character definitions
    characters = [
        ("Shadow Ninja", BLACK, NinjaFighter),
        ("Volt Striker", BLUE, ElectricFighter),
        ("Flame Master", RED, FireFighter),
        ("Stone Titan", (139, 69, 19), EarthFighter)
    ]
    
    # Select random stage
    stage_themes = ["dojo", "street", "arena"]
    background = Background(random.choice(stage_themes))
    
    # Character selection state
    p1_selection = 0
    p2_selection = 1
    
    # Initialize fighters (will be properly set after character selection)
    p1 = None
    p2 = None
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
                
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                    
                if game_state == MENU and event.key == K_RETURN:
                    game_state = CHARACTER_SELECT
                    
                elif game_state == CHARACTER_SELECT:
                    if event.key == K_a:
                        p1_selection = (p1_selection - 1) % len(characters)
                    elif event.key == K_d:
                        p1_selection = (p1_selection + 1) % len(characters)
                    elif event.key == K_LEFT:
                        p2_selection = (p2_selection - 1) % len(characters)
                    elif event.key == K_RIGHT:
                        p2_selection = (p2_selection + 1) % len(characters)
                    elif event.key == K_RETURN:
                        # Create fighters based on selection
                        p1_class = characters[p1_selection][2]
                        p2_class = characters[p2_selection][2]
                        
                        p1 = p1_class(150, FLOOR_HEIGHT - 100)
                        p2 = p2_class(SCREEN_WIDTH - 200, FLOOR_HEIGHT - 100)
                        p1.facing_right = True
                        p2.facing_right = False
                        
                        game_state = FIGHTING
                        
                elif game_state == GAME_OVER and event.key == K_RETURN:
                    game_state = CHARACTER_SELECT
        
        # Game state updates
        if game_state == MENU:
            draw_menu(screen)
            
        elif game_state == CHARACTER_SELECT:
            draw_character_select(screen, p1_selection, p2_selection, characters)
            
        elif game_state == FIGHTING:
            # Get keyboard state
            keys = pygame.key.get_pressed()
            
            # Player 1 controls
            x_direction1 = 0
            if keys[K_a]:
                x_direction1 = -1
            elif keys[K_d]:
                x_direction1 = 1
            p1.move(x_direction1)
            
            if keys[K_w]:
                p1.jump()
                
            if keys[K_s]:
                if isinstance(p1, NinjaFighter) and x_direction1 != 0:
                    p1.dash(x_direction1)
                
            p1.block(keys[K_c])
            
            # Player 1 attack controls (handled as events to avoid key repeat)
            if keys[K_f] and not p1.is_attacking:
                p1.attack()
            if keys[K_g] and not p1.is_attacking:
                p1.special_attack()
            
            # Player 2 controls
            x_direction2 = 0
            if keys[K_LEFT]:
                x_direction2 = -1
            elif keys[K_RIGHT]:
                x_direction2 = 1
            p2.move(x_direction2)
            
            if keys[K_UP]:
                p2.jump()
                
            if keys[K_DOWN]:
                if isinstance(p2, NinjaFighter) and x_direction2 != 0:
                    p2.dash(x_direction2)
                
            p2.block(keys[K_l])
            
            # Player 2 attack controls
            if keys[K_k] and not p2.is_attacking:
                p2.attack()
            if keys[K_j] and not p2.is_attacking:
                p2.special_attack()
            
            # Update fighters
            p1.update(p2)
            p2.update(p1)
            
            # Check for hits
            p1.check_hit(p2)
            p2.check_hit(p1)
            
            # Check for game over
            if p1.hp <= 0 or p2.hp <= 0:
                game_state = GAME_OVER
                if p1.hp <= 0 and p2.hp <= 0:
                    # In case of a draw, player with higher HP percentage wins
                    if p1.hp / p1.max_hp > p2.hp / p2.max_hp:
                        winner, loser = p1, p2
                    else:
                        winner, loser = p2, p1
                elif p1.hp <= 0:
                    winner, loser = p2, p1
                else:
                    winner, loser = p1, p2
            
            # Draw game
            draw_fighting(screen, p1, p2, background)
            
        elif game_state == GAME_OVER:
            draw_game_over(screen, winner, loser)
        
        # Cap the frame rate
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()