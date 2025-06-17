import pygame
import math
import random
import time
from enum import Enum

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)

class GameState(Enum):
    PLAYING = 1
    SLOW_MOTION = 2
    GAME_OVER = 3

class Particle:
    def __init__(self, x, y, color, velocity, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.velocity = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        
    def update(self, dt):
        self.x += self.velocity[0] * dt
        self.y += self.velocity[1] * dt
        self.lifetime -= dt
        
    def draw(self, screen):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            color_with_alpha = (*self.color, alpha)
            size = max(1, int(4 * (self.lifetime / self.max_lifetime)))
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)

class Bullet:
    def __init__(self, x, y, target_x, target_y):
        self.x = x
        self.y = y
        self.speed = 800
        
        # Calculate direction to target
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            self.velocity_x = (dx / distance) * self.speed
            self.velocity_y = (dy / distance) * self.speed
        else:
            self.velocity_x = 0
            self.velocity_y = -self.speed
            
        self.active = True
        
    def update(self, dt):
        if self.active:
            self.x += self.velocity_x * dt
            self.y += self.velocity_y * dt
            
            # Remove bullet if it goes off screen
            if (self.x < 0 or self.x > SCREEN_WIDTH or 
                self.y < 0 or self.y > SCREEN_HEIGHT):
                self.active = False
                
    def draw(self, screen):
        if self.active:
            pygame.draw.circle(screen, CYAN, (int(self.x), int(self.y)), 3)
            # Add glow effect
            pygame.draw.circle(screen, (0, 100, 100), (int(self.x), int(self.y)), 6, 1)

class Enemy:
    def __init__(self, x, y, enemy_type="normal"):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.health = 3 if enemy_type == "special" else 1
        self.max_health = self.health
        self.size = 25 if enemy_type == "special" else 15
        self.speed = 50 if enemy_type == "special" else 100
        self.active = True
        self.hit_flash = 0
        
        # Movement pattern
        self.angle = random.uniform(0, 2 * math.pi)
        self.movement_timer = 0
        
    def update(self, dt, corridor_speed):
        if self.active:
            # Move towards player (simulating corridor movement)
            self.y += corridor_speed * dt
            
            # Add some side-to-side movement
            self.movement_timer += dt
            self.x += math.sin(self.movement_timer * 2) * self.speed * dt * 0.5
            
            # Keep enemy on screen horizontally
            self.x = max(self.size, min(SCREEN_WIDTH - self.size, self.x))
            
            # Remove if off screen
            if self.y > SCREEN_HEIGHT + 50:
                self.active = False
                
            # Update hit flash
            if self.hit_flash > 0:
                self.hit_flash -= dt
                
    def take_damage(self):
        self.health -= 1
        self.hit_flash = 0.2
        if self.health <= 0:
            self.active = False
            return True
        return False
        
    def draw(self, screen):
        if self.active:
            color = RED if self.type == "normal" else PURPLE
            if self.hit_flash > 0:
                color = WHITE
                
            # Draw enemy body
            pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.size)
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.size, 2)
            
            # Draw health bar for special enemies
            if self.type == "special" and self.health < self.max_health:
                bar_width = 40
                bar_height = 6
                bar_x = self.x - bar_width // 2
                bar_y = self.y - self.size - 15
                
                pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
                health_width = (self.health / self.max_health) * bar_width
                pygame.draw.rect(screen, GREEN, (bar_x, bar_y, health_width, bar_height))

class PowerUp:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 12
        self.active = True
        self.pulse_timer = 0
        
    def update(self, dt, corridor_speed):
        if self.active:
            self.y += corridor_speed * dt
            self.pulse_timer += dt
            
            if self.y > SCREEN_HEIGHT + 50:
                self.active = False
                
    def draw(self, screen):
        if self.active:
            pulse = math.sin(self.pulse_timer * 8) * 0.3 + 0.7
            size = int(self.size * pulse)
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), size)
            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), size, 2)
            
            # Draw inner star
            points = []
            for i in range(8):
                angle = i * math.pi / 4
                if i % 2 == 0:
                    r = size * 0.6
                else:
                    r = size * 0.3
                px = self.x + math.cos(angle) * r
                py = self.y + math.sin(angle) * r
                points.append((px, py))
            pygame.draw.polygon(screen, YELLOW, points)

class RailShooter:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rail Shooter - Corridor Run")
        self.clock = pygame.time.Clock()
        
        # Game state
        self.state = GameState.PLAYING
        self.score = 0
        self.shield = 100
        self.max_shield = 100
        self.shield_regen_rate = 20  # per second
        self.last_damage_time = 0
        
        # Slow motion system
        self.slow_motion_charge = 0
        self.max_slow_motion = 100
        self.slow_motion_active = False
        self.slow_motion_duration = 3.0
        self.slow_motion_timer = 0
        self.time_scale = 1.0
        
        # Ship position (moves automatically along path)
        self.ship_path_progress = 0
        self.ship_x = SCREEN_WIDTH // 2
        self.ship_y = SCREEN_HEIGHT - 100
        
        # Corridor effect
        self.corridor_speed = 200
        self.corridor_lines = []
        self.init_corridor()
        
        # Game objects
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.power_ups = []
        
        # Spawn timers
        self.enemy_spawn_timer = 0
        self.enemy_spawn_interval = 2.0
        self.power_up_spawn_timer = 0
        self.power_up_spawn_interval = 8.0
        
        # Mouse
        self.crosshair_x = SCREEN_WIDTH // 2
        self.crosshair_y = SCREEN_HEIGHT // 2
        
        # Font
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
    def init_corridor(self):
        # Create initial corridor lines for 3D effect
        for i in range(20):
            y = i * 50
            self.corridor_lines.append(y)
            
    def update_ship_position(self, dt):
        # Automatic ship movement along a curved path
        self.ship_path_progress += dt * 0.5
        
        # Create a figure-8 like path
        path_x = SCREEN_WIDTH // 2 + math.sin(self.ship_path_progress) * 200
        path_y = SCREEN_HEIGHT - 100 + math.sin(self.ship_path_progress * 0.7) * 30
        
        # Smooth movement towards path position
        self.ship_x += (path_x - self.ship_x) * dt * 3
        self.ship_y += (path_y - self.ship_y) * dt * 3
        
    def spawn_enemy(self):
        x = random.randint(50, SCREEN_WIDTH - 50)
        y = -50
        
        # 20% chance for special enemy
        enemy_type = "special" if random.random() < 0.2 else "normal"
        self.enemies.append(Enemy(x, y, enemy_type))
        
    def spawn_power_up(self):
        x = random.randint(50, SCREEN_WIDTH - 50)
        y = -50
        self.power_ups.append(PowerUp(x, y))
        
    def create_explosion(self, x, y, color=ORANGE):
        # Create explosion particles
        for _ in range(15):
            velocity = (random.uniform(-200, 200), random.uniform(-200, 200))
            lifetime = random.uniform(0.5, 1.5)
            self.particles.append(Particle(x, y, color, velocity, lifetime))
            
    def handle_collision(self, bullet, enemy):
        # Check collision between bullet and enemy
        dx = bullet.x - enemy.x
        dy = bullet.y - enemy.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        return distance < enemy.size
        
    def handle_power_up_collision(self, power_up):
        # Check collision between ship and power up
        dx = self.ship_x - power_up.x
        dy = self.ship_y - power_up.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        return distance < 30
        
    def update_slow_motion(self, dt):
        if self.slow_motion_active:
            self.slow_motion_timer -= dt
            self.time_scale = 0.3
            
            if self.slow_motion_timer <= 0:
                self.slow_motion_active = False
                self.time_scale = 1.0
        else:
            self.time_scale = 1.0
            
    def activate_slow_motion(self):
        if self.slow_motion_charge >= self.max_slow_motion:
            self.slow_motion_active = True
            self.slow_motion_timer = self.slow_motion_duration
            self.slow_motion_charge = 0
            
    def update(self, dt):
        # Apply time scale for slow motion
        scaled_dt = dt * self.time_scale
        
        # Update slow motion system
        self.update_slow_motion(dt)
        
        # Update ship position
        self.update_ship_position(scaled_dt)
        
        # Shield regeneration (only if not recently damaged)
        current_time = time.time()
        if current_time - self.last_damage_time > 2.0:  # 2 second delay
            self.shield = min(self.max_shield, self.shield + self.shield_regen_rate * dt)
            
        # Update corridor effect
        for i in range(len(self.corridor_lines)):
            self.corridor_lines[i] += self.corridor_speed * scaled_dt
            if self.corridor_lines[i] > SCREEN_HEIGHT:
                self.corridor_lines[i] = -50
                
        # Spawn enemies
        self.enemy_spawn_timer += scaled_dt
        if self.enemy_spawn_timer >= self.enemy_spawn_interval:
            self.spawn_enemy()
            self.enemy_spawn_timer = 0
            # Gradually increase spawn rate
            self.enemy_spawn_interval = max(0.8, self.enemy_spawn_interval - 0.01)
            
        # Spawn power ups
        self.power_up_spawn_timer += scaled_dt
        if self.power_up_spawn_timer >= self.power_up_spawn_interval:
            self.spawn_power_up()
            self.power_up_spawn_timer = 0
            
        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(scaled_dt)
            if not bullet.active:
                self.bullets.remove(bullet)
                
        # Update enemies
        for enemy in self.enemies[:]:
            enemy.update(scaled_dt, self.corridor_speed)
            if not enemy.active:
                self.enemies.remove(enemy)
                
        # Update power ups
        for power_up in self.power_ups[:]:
            power_up.update(scaled_dt, self.corridor_speed)
            if not power_up.active:
                self.power_ups.remove(power_up)
            elif self.handle_power_up_collision(power_up):
                power_up.active = False
                self.power_ups.remove(power_up)
                self.slow_motion_charge = min(self.max_slow_motion, self.slow_motion_charge + 25)
                self.create_explosion(power_up.x, power_up.y, YELLOW)
                
        # Update particles
        for particle in self.particles[:]:
            particle.update(scaled_dt)
            if particle.lifetime <= 0:
                self.particles.remove(particle)
                
        # Check bullet-enemy collisions
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if bullet.active and enemy.active and self.handle_collision(bullet, enemy):
                    bullet.active = False
                    self.bullets.remove(bullet)
                    
                    if enemy.take_damage():
                        # Enemy destroyed
                        points = 100 if enemy.type == "special" else 50
                        self.score += points
                        
                        # Special enemies give slow motion charge
                        if enemy.type == "special":
                            self.slow_motion_charge = min(self.max_slow_motion, 
                                                        self.slow_motion_charge + 15)
                            
                        self.create_explosion(enemy.x, enemy.y)
                        self.enemies.remove(enemy)
                    break
                    
        # Check enemy-ship collisions (damage shield)
        for enemy in self.enemies[:]:
            dx = self.ship_x - enemy.x
            dy = self.ship_y - enemy.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < 40:  # Ship collision radius
                self.shield -= 20
                self.last_damage_time = time.time()
                self.create_explosion(enemy.x, enemy.y, RED)
                enemy.active = False
                self.enemies.remove(enemy)
                
                if self.shield <= 0:
                    self.state = GameState.GAME_OVER
                    
    def shoot(self, target_x, target_y):
        bullet = Bullet(self.ship_x, self.ship_y - 20, target_x, target_y)
        self.bullets.append(bullet)
        
    def draw_corridor(self):
        # Draw 3D-like corridor effect
        for i, y in enumerate(self.corridor_lines):
            if 0 <= y <= SCREEN_HEIGHT:
                # Calculate perspective scaling
                scale = (y + 100) / (SCREEN_HEIGHT + 100)
                width = int(SCREEN_WIDTH * scale)
                
                # Draw corridor walls
                left_x = (SCREEN_WIDTH - width) // 2
                right_x = left_x + width
                
                color_intensity = int(100 * scale)
                color = (color_intensity, color_intensity, color_intensity)
                
                if i % 2 == 0:  # Grid lines
                    pygame.draw.line(self.screen, color, (left_x, y), (right_x, y), 2)
                    
                # Side walls
                if i > 0 and i < len(self.corridor_lines) - 1:
                    prev_y = self.corridor_lines[i-1]
                    if 0 <= prev_y <= SCREEN_HEIGHT:
                        prev_scale = (prev_y + 100) / (SCREEN_HEIGHT + 100)
                        prev_width = int(SCREEN_WIDTH * prev_scale)
                        prev_left = (SCREEN_WIDTH - prev_width) // 2
                        prev_right = prev_left + prev_width
                        
                        pygame.draw.line(self.screen, color, (left_x, y), (prev_left, prev_y), 1)
                        pygame.draw.line(self.screen, color, (right_x, y), (prev_right, prev_y), 1)
                        
    def draw_ui(self):
        # Shield bar
        shield_width = 200
        shield_height = 20
        shield_x = 20
        shield_y = 20
        
        pygame.draw.rect(self.screen, DARK_GRAY, (shield_x, shield_y, shield_width, shield_height))
        shield_fill = (self.shield / self.max_shield) * shield_width
        shield_color = GREEN if self.shield > 50 else ORANGE if self.shield > 25 else RED
        pygame.draw.rect(self.screen, shield_color, (shield_x, shield_y, shield_fill, shield_height))
        pygame.draw.rect(self.screen, WHITE, (shield_x, shield_y, shield_width, shield_height), 2)
        
        shield_text = self.small_font.render(f"Shield: {int(self.shield)}", True, WHITE)
        self.screen.blit(shield_text, (shield_x, shield_y + 25))
        
        # Slow motion charge bar
        sm_width = 150
        sm_height = 15
        sm_x = 20
        sm_y = 70
        
        pygame.draw.rect(self.screen, DARK_GRAY, (sm_x, sm_y, sm_width, sm_height))
        sm_fill = (self.slow_motion_charge / self.max_slow_motion) * sm_width
        sm_color = CYAN if self.slow_motion_charge >= self.max_slow_motion else BLUE
        pygame.draw.rect(self.screen, sm_color, (sm_x, sm_y, sm_fill, sm_height))
        pygame.draw.rect(self.screen, WHITE, (sm_x, sm_y, sm_width, sm_height), 2)
        
        sm_text = self.small_font.render("Slow Motion", True, WHITE)
        self.screen.blit(sm_text, (sm_x, sm_y + 20))
        
        # Score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (SCREEN_WIDTH - 200, 20))
        
        # Slow motion indicator
        if self.slow_motion_active:
            sm_indicator = self.font.render("SLOW MOTION", True, CYAN)
            text_rect = sm_indicator.get_rect(center=(SCREEN_WIDTH//2, 100))
            self.screen.blit(sm_indicator, text_rect)
            
    def draw_crosshair(self):
        # Draw crosshair at mouse position
        size = 20
        pygame.draw.line(self.screen, WHITE, 
                        (self.crosshair_x - size, self.crosshair_y), 
                        (self.crosshair_x + size, self.crosshair_y), 2)
        pygame.draw.line(self.screen, WHITE, 
                        (self.crosshair_x, self.crosshair_y - size), 
                        (self.crosshair_x, self.crosshair_y + size), 2)
        pygame.draw.circle(self.screen, WHITE, (self.crosshair_x, self.crosshair_y), size, 2)
        
    def draw_ship(self):
        # Draw player ship
        ship_points = [
            (self.ship_x, self.ship_y - 20),
            (self.ship_x - 15, self.ship_y + 10),
            (self.ship_x, self.ship_y + 5),
            (self.ship_x + 15, self.ship_y + 10)
        ]
        pygame.draw.polygon(self.screen, CYAN, ship_points)
        pygame.draw.polygon(self.screen, WHITE, ship_points, 2)
        
        # Engine glow
        glow_points = [
            (self.ship_x - 8, self.ship_y + 10),
            (self.ship_x, self.ship_y + 20),
            (self.ship_x + 8, self.ship_y + 10)
        ]
        pygame.draw.polygon(self.screen, ORANGE, glow_points)
        
    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw corridor
        self.draw_corridor()
        
        # Draw particles (behind everything)
        for particle in self.particles:
            particle.draw(self.screen)
            
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(self.screen)
            
        # Draw power ups
        for power_up in self.power_ups:
            power_up.draw(self.screen)
            
        # Draw bullets
        for bullet in self.bullets:
            bullet.draw(self.screen)
            
        # Draw ship
        self.draw_ship()
        
        # Draw UI
        self.draw_ui()
        
        # Draw crosshair
        self.draw_crosshair()
        
        if self.state == GameState.GAME_OVER:
            # Game over screen
            game_over_text = self.font.render("GAME OVER", True, RED)
            score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            restart_text = self.small_font.render("Press R to restart or ESC to quit", True, WHITE)
            
            game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
            score_rect = score_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
            
            self.screen.blit(game_over_text, game_over_rect)
            self.screen.blit(score_text, score_rect)
            self.screen.blit(restart_text, restart_rect)
            
        pygame.display.flip()
        
    def reset_game(self):
        self.state = GameState.PLAYING
        self.score = 0
        self.shield = 100
        self.slow_motion_charge = 0
        self.slow_motion_active = False
        self.slow_motion_timer = 0
        self.time_scale = 1.0
        self.ship_path_progress = 0
        self.enemy_spawn_timer = 0
        self.enemy_spawn_interval = 2.0
        self.power_up_spawn_timer = 0
        
        # Clear all game objects
        self.bullets.clear()
        self.enemies.clear()
        self.particles.clear()
        self.power_ups.clear()
        
    def run(self):
        running = True
        
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.MOUSEMOTION:
                    self.crosshair_x, self.crosshair_y = event.pos
                    
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if self.state == GameState.PLAYING:
                            self.shoot(self.crosshair_x, self.crosshair_y)
                            
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.state == GameState.PLAYING:
                            self.activate_slow_motion()
                    elif event.key == pygame.K_r:
                        if self.state == GameState.GAME_OVER:
                            self.reset_game()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                        
            # Update game
            if self.state in [GameState.PLAYING, GameState.SLOW_MOTION]:
                self.update(dt)
                
            # Draw everything
            self.draw()
            
        pygame.quit()

if __name__ == "__main__":
    game = RailShooter()
    game.run()
