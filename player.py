import pygame
from tank import Tank

class Player(Tank):
	def __init__(self, game, level, position=None, direction=None, filename=None):
		super().__init__(game, level, side=0, position=None, direction=None, filename=None)
		self.start_position = position
		self.start_direction = direction
		self.lives = 3
		self.score = 0  # total score

		# store how many bonuses in this stage this player has collected 计分板
		self.trophies = {
			"bonus"  : 0,
			"enemy0" : 0,
			"enemy1" : 0,
			"enemy2" : 0,
			"enemy3" : 0
		}
		
		if filename == None:
			filename = (0, 0, 16*2, 16*2)
		self.image = self.game.sprites.subsurface(filename)
		self.image_up = self.image
		self.image_left = pygame.transform.rotate(self.image, 90)
		self.image_down = pygame.transform.rotate(self.image, 180)
		self.image_right = pygame.transform.rotate(self.image, 270)

		if direction == None:
			self.rotate(self.DIR_UP, False)
		else:
			self.rotate(direction, False)

	def move(self, direction):
		""" move player if possible """
		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DEAD
				del self.explosion

		if self.state != self.STATE_ALIVE:
			return

		if self.direction != direction:  # rotate player
			self.rotate(direction)

		if self.paralised:  # 瘫痪
			return

		# speed: px per move, default is 2
		if direction == self.DIR_UP:     # move player
			new_position = [self.rect.left, self.rect.top - self.speed]
			if new_position[1] < 0:
				return
		elif direction == self.DIR_RIGHT:
			new_position = [self.rect.left + self.speed, self.rect.top]
			if new_position[0] > (416 - 26):
				return
		elif direction == self.DIR_DOWN:
			new_position = [self.rect.left, self.rect.top + self.speed]
			if new_position[1] > (416 - 26):
				return
		elif direction == self.DIR_LEFT:
			new_position = [self.rect.left - self.speed, self.rect.top]
			if new_position[0] < 0:
				return

		player_rect = pygame.Rect(new_position, [26, 26])

		# collisions with tiles
		if player_rect.collidelist(self.level.obstacle_rects) != -1:
			return  # ignore update

		# collisions with other players
		for player in self.game.players:
			if player != self and player.state == player.STATE_ALIVE and player_rect.colliderect(player.rect) == True:
				return  # ignore update

		# collisions with enemies
		for enemy in self.game.enemies:
			if player_rect.colliderect(enemy.rect) == True:
				return  # ignore update

		# collisions with bonuses
		for bonus in self.game.bonuses:
			if player_rect.colliderect(bonus.rect) == True:
				self.bonus = bonus

		#if no collision, move player
		self.rect.topleft = (new_position[0], new_position[1])

	def reset(self):
		""" reset player """
		self.rotate(self.start_direction, False)
		self.rect.topleft = self.start_position
		self.superpowers = 0
		self.max_active_bullets = 1
		self.health = 100
		self.paralised = False
		self.paused = False
		self.pressed = [False] * 4
		self.state = self.STATE_ALIVE