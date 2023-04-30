import pygame
import random
from explosion import Explosion
from bullet import Bullet
from label import Label

class Tank:
	"""坦克父类, 可以派生出玩家和敌方坦克"""
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)  # possible directions
	(STATE_SPAWNING, STATE_DEAD, STATE_ALIVE, STATE_EXPLODING) = range(4)  # states
	(SIDE_PLAYER, SIDE_ENEMY) = range(2)  # sides

	def __init__(self, game, level, side, position=None, direction=None, filename=None):
		self.game = game  # 与上层资源交互
		self.level = level

		self.health = 100            # health. 0 health means dead
		self.paralised = False       # tank can't move but can rotate and shoot
		self.paused = False          # tank can't do anything
		self.shielded = False        # tank is protected from bullets
		self.speed = 2               # px per move
		self.max_active_bullets = 1  # how many bullets can tank fire simultaneously
		self.side = side             # friend or foe
		self.flash = 0               # flashing state. 0-off, 1-on
		self.bonus = None            # each tank can pick up 1 bonus

		# 0 - no superpowers
		# 1 - faster bullets
		# 2 - can fire 2 bullets
		# 3 - can destroy steel
		self.superpowers = 0

		# navigation keys: fire, up, right, down, left
		self.controls = [pygame.K_SPACE, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT]
		self.pressed = [False] * 4  # currently pressed buttons (navigation only)

		self.shield_images = [
			self.game.sprites.subsurface(0, 48*2, 16*2, 16*2),
			self.game.sprites.subsurface(16*2, 48*2, 16*2, 16*2)
		]
		self.shield_image = self.shield_images[0]
		self.shield_index = 0
		self.spawn_images = [
			self.game.sprites.subsurface(32*2, 48*2, 16*2, 16*2),
			self.game.sprites.subsurface(48*2, 48*2, 16*2, 16*2)
		]
		self.spawn_image = self.spawn_images[0]
		self.spawn_index = 0
		

		if position != None:
			self.rect = pygame.Rect(position, (26, 26))
		else:
			self.rect = pygame.Rect(0, 0, 26, 26)

		if direction == None:
			self.direction = random.choice([self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT])
		else:
			self.direction = direction

		self.state = self.STATE_SPAWNING
		self.timer_uuid_spawn = self.game.timer_pool.add(100, self.toggleSpawnImage)  # spawning animation
		self.timer_uuid_spawn_end = self.game.timer_pool.add(1000, self.endSpawning)  # duration of spawning

	def endSpawning(self):
		""" End spawning
		Player becomes operational
		"""
		self.state = self.STATE_ALIVE
		self.game.timer_pool.destroy(self.timer_uuid_spawn_end)

	def toggleSpawnImage(self):
		""" advance to the next spawn image """
		if self.state != self.STATE_SPAWNING:
			self.game.timer_pool.destroy(self.timer_uuid_spawn)
			return
		self.spawn_index += 1
		if self.spawn_index >= len(self.spawn_images):
			self.spawn_index = 0
		self.spawn_image = self.spawn_images[self.spawn_index]

	def toggleShieldImage(self):
		""" advance to the next shield image """
		if self.state != self.STATE_ALIVE:
			self.game.timer_pool.destroy(self.timer_uuid_shield)
			return
		if self.shielded:
			self.shield_index += 1
			if self.shield_index >= len(self.shield_images):
				self.shield_index = 0
			self.shield_image = self.shield_images[self.shield_index]

	def draw(self):
		""" draw tank """
		if self.state == self.STATE_ALIVE:
			self.game.screen.blit(self.image, self.rect.topleft)
			if self.shielded:
				self.game.screen.blit(self.shield_image, [self.rect.left-3, self.rect.top-3])
		elif self.state == self.STATE_EXPLODING:
			self.explosion.draw()
		elif self.state == self.STATE_SPAWNING:
			self.game.screen.blit(self.spawn_image, self.rect.topleft)

	def explode(self):
		""" start tanks's explosion """
		if self.state != self.STATE_DEAD:
			self.state = self.STATE_EXPLODING
			self.explosion = Explosion(self.game, self.rect.topleft)

			if self.bonus:
				self.spawnBonus()

	def fire(self, forced=False):
		""" Shoot a bullet 创建一个子弹
		@param boolean forced.(是否强制发射子弹) If false, check whether tank has exceeded his bullet quota. Default: False
		@return boolean True if bullet was fired, false otherwise
		"""
		if self.state != self.STATE_ALIVE:
			self.game.timer_pool.destroy(self.timer_uuid_fire)
			return False

		if self.paused:
			return False

		if not forced:
			active_bullets = 0
			for bullet in self.game.bullets:
				if bullet.owner == self and bullet.state == bullet.STATE_ACTIVE:
					active_bullets += 1
			if active_bullets >= self.max_active_bullets:
				return False

		bullet = Bullet(game=self.game, level=self.level, owner=self, position=self.rect.topleft, direction=self.direction)

		if self.superpowers > 0:  # if superpower level is at least 1
			bullet.speed = 8

		if self.superpowers > 2:  # if superpower level is at least 3
			bullet.power = 2

		if self.side == self.SIDE_ENEMY:
			self.bullet_queued = False

		self.game.bullets.append(bullet)
		return True

	def rotate(self, direction, fix_position=True):
		""" Rotate tank
		rotate, update image and correct position
		"""
		self.direction = direction

		if direction == self.DIR_UP:
			self.image = self.image_up
		elif direction == self.DIR_RIGHT:
			self.image = self.image_right
		elif direction == self.DIR_DOWN:
			self.image = self.image_down
		elif direction == self.DIR_LEFT:
			self.image = self.image_left

		if fix_position:
			new_x = self.nearest(self.rect.left, 8) + 3
			new_y = self.nearest(self.rect.top, 8) + 3

			if (abs(self.rect.left - new_x) < 5):
				self.rect.left = new_x

			if (abs(self.rect.top - new_y) < 5):
				self.rect.top = new_y

	def turnAround(self):
		""" Turn tank into opposite direction """
		if self.direction in (self.DIR_UP, self.DIR_RIGHT):
			self.rotate(self.direction + 2, False)
		else:
			self.rotate(self.direction - 2, False)

	def update(self, time_passed):
		""" Update timer and explosion (if any) """
		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DEAD
				del self.explosion

	def nearest(self, num, base):
		""" Round number to nearest divisible """
		return int(round(num / (base * 1.0)) * base)


	def bulletImpact(self, friendly_fire=False, damage=100, tank=None):
		""" Bullet impact
		Return True if bullet should be destroyed on impact. 
		Only enemy friendly-fire doesn't trigger bullet explosion
		敌方子弹不引起爆炸特效
		friendly_fire: 子弹发射方和击中方是否属于同一阵营
		tank: owner of bullet
		"""
		if self.shielded:
			return True

		if not friendly_fire:  # 不是友方子弹
			self.health -= damage
			if self.health < 1:  # 死亡
				if self.side == self.SIDE_ENEMY:
					tank.trophies["enemy"+str(self.type)] += 1
					points = (self.type+1) * 100
					tank.score += points
					if self.game.play_sounds:
						self.game.sounds["explosion"].play()

					self.game.labels.append(Label(self.game, self.rect.topleft, str(points), 500))

				self.explode()
			return True

		if self.side == self.SIDE_ENEMY:  # 敌人击中敌人
			return True
		elif self.side == self.SIDE_PLAYER: # 玩家击中玩家
			if not self.paralised:
				self.setParalised()  # 瘫痪
				self.timer_uuid_paralise = self.game.timer_pool.add(10000, self.resetParalised, 1)
			return True

	def setParalised(self):
		""" 
		set tank paralise state
		cancel state with resetParalised()
		"""
		if self.state != self.STATE_ALIVE:  # 已经死了
			self.game.timer_pool.destroy(self.timer_uuid_paralise)
			return
		self.paralised = True

	def resetParalised(self):
		if self.state != self.STATE_ALIVE:
			self.game.timer_pool.destroy(self.timer_uuid_paralise)
			return
		self.paralised = False