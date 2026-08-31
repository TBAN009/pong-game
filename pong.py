import pygame
import sys
import math
import random

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 1580
SCREEN_HEIGHT = 900
FPS = 90

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)

# Paddle dimensions
PADDLE_WIDTH = 15
PADDLE_HEIGHT = 100
PADDLE_SPEED = 6

# Ball dimensions
BALL_SIZE = 20
BALL_SPEED = 5

# Game setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pong Game")
clock = pygame.time.Clock()
font_score = pygame.font.Font(None, 74)
font_info = pygame.font.Font(None, 36)


class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = PADDLE_SPEED

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect)

    def move_up(self):
        if self.rect.top > 0:
            self.rect.y -= self.speed

    def move_down(self):
        if self.rect.bottom < SCREEN_HEIGHT:
            self.rect.y += self.speed

    def set_position(self, y):
        """Set paddle position with boundaries"""
        self.rect.y = max(0, min(y, SCREEN_HEIGHT - PADDLE_HEIGHT))


class Ball:
    def __init__(self):
        self.rect = pygame.Rect(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, BALL_SIZE, BALL_SIZE)
        self.velocity_x = BALL_SPEED * random.choice([-1, 1])
        self.velocity_y = BALL_SPEED * random.choice([-1, 1])

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect)

    def update(self):
        self.rect.x += self.velocity_x
        self.rect.y += self.velocity_y

        # Bounce off top and bottom walls
        if self.rect.top <= 0 or self.rect.bottom >= SCREEN_HEIGHT:
            self.velocity_y *= -1
            self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - BALL_SIZE))

    def reset(self):
        """Reset ball to center"""
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.centery = SCREEN_HEIGHT // 2
        self.velocity_x = BALL_SPEED * random.choice([-1, 1])
        self.velocity_y = BALL_SPEED * random.choice([-1, 1]) * 0.5

    def check_paddle_collision(self, paddle):
        """Check collision with paddle and adjust velocity"""
        if self.rect.colliderect(paddle.rect):
            # Determine collision side
            if self.velocity_x > 0:  # Ball moving right
                self.rect.right = paddle.rect.left
                self.velocity_x *= -1
            else:  # Ball moving left
                self.rect.left = paddle.rect.right
                self.velocity_x *= -1

            # Add spin based on where ball hits paddle
            hit_pos = (self.rect.centery - paddle.rect.centery) / (PADDLE_HEIGHT / 2)
            hit_pos = max(-1, min(1, hit_pos))  # Clamp between -1 and 1
            self.velocity_y += hit_pos * 3

            return True
        return False


class Game:
    def __init__(self):
        self.player_paddle = Paddle(20, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2)
        self.computer_paddle = Paddle(SCREEN_WIDTH - PADDLE_WIDTH - 20, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2)
        self.ball = Ball()
        self.player_score = 0
        self.computer_score = 0

    def handle_input(self):
        """Handle player input"""
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Mouse control for left paddle
        self.player_paddle.set_position(mouse_y - PADDLE_HEIGHT // 2)

        # Arrow key control (alternative)
        if keys[pygame.K_UP]:
            self.player_paddle.move_up()
        if keys[pygame.K_DOWN]:
            self.player_paddle.move_down()

    def update_ai(self):
        """Update computer paddle AI"""
        paddle_center = self.computer_paddle.rect.centery
        ball_center = self.ball.rect.centery
        ai_speed = PADDLE_SPEED * 0.75  # Slightly slower than player

        # AI tries to follow the ball
        if paddle_center < ball_center - 35:
            self.computer_paddle.rect.y += ai_speed
        elif paddle_center > ball_center + 35:
            self.computer_paddle.rect.y -= ai_speed

        # Keep paddle in bounds
        self.computer_paddle.rect.y = max(0, min(self.computer_paddle.rect.y, SCREEN_HEIGHT - PADDLE_HEIGHT))

    def update(self):
        """Update game state"""
        self.ball.update()

        # Check paddle collisions
        self.ball.check_paddle_collision(self.player_paddle)
        self.ball.check_paddle_collision(self.computer_paddle)

        # Check if ball is out of bounds
        if self.ball.rect.left < 0:
            self.computer_score += 1
            self.ball.reset()
        elif self.ball.rect.right > SCREEN_WIDTH:
            self.player_score += 1
            self.ball.reset()

        self.update_ai()

    def draw(self):
        """Draw all game elements"""
        screen.fill(BLACK)

        # Draw center line
        for y in range(0, SCREEN_HEIGHT, 20):
            pygame.draw.line(screen, GRAY, (SCREEN_WIDTH // 2, y), (SCREEN_WIDTH // 2, y + 10), 2)

        # Draw paddles and ball
        self.player_paddle.draw(screen)
        self.computer_paddle.draw(screen)
        self.ball.draw(screen)

        # Draw scores
        player_text = font_score.render(str(self.player_score), True, WHITE)
        computer_text = font_score.render(str(self.computer_score), True, WHITE)
        screen.blit(player_text, (SCREEN_WIDTH // 4, 50))
        screen.blit(computer_text, (3 * SCREEN_WIDTH // 4 - 50, 50))

        # Draw controls info
        info_text = font_info.render("Mouse or Arrow Keys to Control Left Paddle", True, WHITE)
        screen.blit(info_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT - 40))

        pygame.display.flip()

    def run(self):
        """Main game loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.handle_input()
            self.update()
            self.draw()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
