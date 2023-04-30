import pygame
from explosion import Explosion

class Bullet():
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)         # direction constants
	(STATE_REMOVED, STATE_ACTIVE, STATE_EXPLODING) = range(3)  # bullet's stated
	(OWNER_PLAYER, OWNER_ENEMY) = range(2)

	def __init__(self, game, level, owner, position, direction, damage=100, speed=5):
		self.game = game
		self.level = level
		self.direction = direction
		self.damage = damage
		self.owner = owner
		self.owner_side = owner.side

		# 1-regular everyday normal bullet
		# 2-can destroy steel
		self.power = 1
		self.image = self.game.sprites.subsurface(75*2, 74*2, 3*2, 4*2)

		# position is player's top left corner, so we'll need to
		# recalculate a bit. also rotate image itself.
		if direction == self.DIR_UP:
			self.rect = pygame.Rect(position[0] + 11, position[1] - 8, 6, 8)
		elif direction == self.DIR_RIGHT:
			self.image = pygame.transform.rotate(self.image, 270)
			self.rect = pygame.Rect(position[0] + 26, position[1] + 11, 8, 6)
		elif direction == self.DIR_DOWN:
			self.image = pygame.transform.rotate(self.image, 180)
			self.rect = pygame.Rect(position[0] + 11, position[1] + 26, 6, 8)
		elif direction == self.DIR_LEFT:
			self.image = pygame.transform.rotate(self.image, 90)
			self.rect = pygame.Rect(position[0] - 8 , position[1] + 11, 8, 6)

		self.explosion_images = [
			self.game.sprites.subsurface(0, 80*2, 32*2, 32*2),
			self.game.sprites.subsurface(32*2, 80*2, 32*2, 32*2),
		]

		self.speed = speed
		self.state = self.STATE_ACTIVE

	def draw(self):
		""" draw bullet """
		if self.state == self.STATE_ACTIVE:
			self.game.screen.blit(self.image, self.rect.topleft)
		elif self.state == self.STATE_EXPLODING:
			self.explosion.draw()

	def update(self):
		""" return True if player hits enemy, return False otherwise """
		if self.state == self.STATE_EXPLODING:  # 子弹出界会被设置为 exploding, 但不会被立刻清除
			if not self.explosion.active:
				self.destroy()
				del self.explosion

		if self.state != self.STATE_ACTIVE:  # 只有 ACTIVE 的子弹可以移动，EXPLODING 和 REMOVED 都不用继续判断
			return False

		""" move bullet and detect border collisions """
		if self.direction == self.DIR_UP:
			self.rect.topleft = [self.rect.left, self.rect.top - self.speed]
			if self.rect.top < 0:
				if self.game.play_sounds and self.owner_side == self.OWNER_PLAYER:
					self.game.sounds["steel"].play()
				self.explode()  # 仅播放动画, 没有其它效果
				return False
		elif self.direction == self.DIR_RIGHT:
			self.rect.topleft = [self.rect.left + self.speed, self.rect.top]
			if self.rect.left > (416 - self.rect.width):
				if self.game.play_sounds and self.owner_side == self.OWNER_PLAYER:
					self.game.sounds["steel"].play()
				self.explode()
				return False
		elif self.direction == self.DIR_DOWN:
			self.rect.topleft = [self.rect.left, self.rect.top + self.speed]
			if self.rect.top > (416 - self.rect.height):
				if self.game.play_sounds and self.owner_side == self.OWNER_PLAYER:
					self.game.sounds["steel"].play()
				self.explode()
				return False
		elif self.direction == self.DIR_LEFT:
			self.rect.topleft = [self.rect.left - self.speed, self.rect.top]
			if self.rect.left < 0:
				if self.game.play_sounds and self.owner == self.OWNER_PLAYER:
					self.game.sounds["steel"].play()
				self.explode()  
				return False

		has_collided = False

		# check for collisions with walls. one bullet can destroy several (1 or 2)
		# tiles but explosion remains 1
		rects = self.level.obstacle_rects
		collisions = self.rect.collidelistall(rects)
		if collisions != []:
			for i in collisions:
				if self.level.hitTile(rects[i].topleft, self.power, self.owner_side==self.OWNER_PLAYER):
					has_collided = True
		if has_collided:
			self.explode()
			return False

		# check for collisions with other bullets
		for bullet in self.game.bullets:
			if self.state == self.STATE_ACTIVE and bullet.owner_side!=self.owner_side and bullet != self and self.rect.colliderect(bullet.rect):
				self.destroy()
				self.explode()
				return False

		# check for collisions with players
		for player in self.game.players:
			if player.state == player.STATE_ALIVE and self.rect.colliderect(player.rect):
				if player.bulletImpact(self.owner_side==self.OWNER_PLAYER, self.damage, self.owner):
					self.destroy()
					return False

		# check for collisions with enemies
		for enemy in self.game.enemies:
			if enemy.state == enemy.STATE_ALIVE and self.rect.colliderect(enemy.rect):
				friendly_fire = self.owner_side==self.OWNER_ENEMY
				if enemy.bulletImpact(friendly_fire, self.damage, self.owner):
					self.destroy()
					return True if not friendly_fire else False

		# check for collision with castle
		if self.game.castle.active and self.rect.colliderect(self.game.castle.rect):
			self.game.castle.destroy()
			self.destroy()
			return False

	def explode(self):
		""" start bullets's explosion """
		if self.state != self.STATE_REMOVED:
			self.state = self.STATE_EXPLODING
			self.explosion = Explosion(game=self.game, position=[self.rect.left-13, self.rect.top-13])

	def destroy(self):
		self.state = self.STATE_REMOVED  # 设置为 STATE_REMOVED 的子弹对象会在下一帧被清除
