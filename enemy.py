import pygame
import random
from tank import Tank
from bonus import Bonus

class Enemy(Tank):
	(TYPE_BASIC, TYPE_FAST, TYPE_POWER, TYPE_ARMOR) = range(4)

	def __init__(self, game, level, position=None, direction=None, filename=None):
		super().__init__(game, level, side=1, position=None, direction=None, filename=None)
		self.bullet_queued = False  # if true, do not fire
		self.game = game
		# chose type on random
		if len(level.enemies_left) > 0:  # 当前关卡配置里拿出一个坦克型号
			self.type = level.enemies_left.pop()+0
		else:
			self.state = self.STATE_DEAD
			return

		if self.type == self.TYPE_BASIC:
			self.speed = 1
		elif self.type == self.TYPE_FAST:
			self.speed = 3
		elif self.type == self.TYPE_POWER:
			self.superpowers = 1
		elif self.type == self.TYPE_ARMOR:
			self.health = 400

		# 1 in 5 chance this will be bonus carrier, but only if no other tank is
		# 携带奖励的闪烁坦克死亡后，地图上会刷出奖励
		if random.randint(1, 5) == 1:
			self.bonus = True
			for enemy in self.game.enemies:
				if enemy.bonus:
					self.bonus = False
					break

		image_rects = [
			(32*2, 0, 13*2, 15*2),
			(48*2, 0, 13*2, 15*2),
			(64*2, 0, 13*2, 15*2),
			(80*2, 0, 13*2, 15*2),
			(32*2, 16*2, 13*2, 15*2),
			(48*2, 16*2, 13*2, 15*2),
			(64*2, 16*2, 13*2, 15*2),
			(80*2, 16*2, 13*2, 15*2)
		]
		# game.sprites.subsurface
		image = game.sprites.subsurface(image_rects[self.type])
		self.image_up = image
		self.image_left = pygame.transform.rotate(image, 90)
		self.image_down = pygame.transform.rotate(image, 180)
		self.image_right = pygame.transform.rotate(image, 270)

		if self.bonus:  # 闪烁的敌人附带奖励
			self.image1_up = self.image_up
			self.image1_left = self.image_left
			self.image1_down = self.image_down
			self.image1_right = self.image_right

			image2 = game.sprites.subsurface(image_rects[self.type+4])
			self.image2_up = image2
			self.image2_left = pygame.transform.rotate(image2, 90)
			self.image2_down = pygame.transform.rotate(image2, 180)
			self.image2_right = pygame.transform.rotate(image2, 270)

		self.rotate(self.direction, False)

		if position == None:  # 若未指定生成位置，随机获取一个OK的位置
			self.rect.topleft = self.getFreeSpawningPosition()
			if not self.rect.topleft:
				self.state = self.STATE_DEAD
				return

		# list of map coords where tank should go next
		self.path = self.generatePath(self.direction)

		# 1000 (1s) is duration between shots 自动射击间隔
		self.timer_uuid_fire = self.game.timer_pool.add(1000, self.fire)

		# turn on flashing
		if self.bonus:
			self.timer_uuid_flash = self.game.timer_pool.add(200, self.toggleFlash)

	def toggleFlash(self):
		""" Toggle flash state """
		if self.state not in (self.STATE_ALIVE, self.STATE_SPAWNING):
			self.game.timer_pool.destroy(self.timer_uuid_flash)
			return
		self.flash = not self.flash
		if self.flash:
			self.image_up = self.image2_up
			self.image_right = self.image2_right
			self.image_down = self.image2_down
			self.image_left = self.image2_left
		else:
			self.image_up = self.image1_up
			self.image_right = self.image1_right
			self.image_down = self.image1_down
			self.image_left = self.image1_left
		self.rotate(self.direction, fix_position=False)

	def spawnBonus(self):
		""" Create new bonus if tank dead"""
		if len(self.game.bonuses) > 0:
			return
		bonus = Bonus(game=self.game, level=self.level)
		self.game.bonuses.append(bonus)
		self.game.timer_pool.add(500, bonus.toggleVisibility)
		self.game.timer_pool.add(10000, lambda :self.game.remove_bonus(bonus), 1)

	def getFreeSpawningPosition(self):
		""" 在左上，中上，右上三个地点随机选择空位, 若无空位则返回 False """
		vertical_offset = (self.level.TILE_SIZE * 2 - self.rect.width) / 2
		horizontal_offset = (self.level.TILE_SIZE * 2 - self.rect.height) / 2

		available_positions = [
			[vertical_offset, horizontal_offset],
			[12 * self.level.TILE_SIZE + vertical_offset, horizontal_offset],
			[24 * self.level.TILE_SIZE + vertical_offset,  horizontal_offset]
		]
		# [[0*16+3,3], [12*16+3, 3], [24*16+3, 3]]
		random.shuffle(available_positions)

		for pos in available_positions:
			enemy_rect = pygame.Rect(pos, [26, 26])

			# collisions with other enemies
			collision = False
			for enemy in self.game.enemies:
				if enemy_rect.colliderect(enemy.rect):
					collision = True
					break
			if collision:
				continue  # 放弃这个位置

			# collisions with players
			collision = False
			for player in self.game.players:
				if enemy_rect.colliderect(player.rect):
					collision = True
					break
			if collision:
				continue

			return pos
		return False

	def move(self):
		""" move enemy if possible """
		if self.state != self.STATE_ALIVE or self.paused or self.paralised:
			return

		if self.path == []:
			self.path = self.generatePath(None, True)

		new_position = self.path.pop(0)

		# 越界检测
		if self.direction == self.DIR_UP:
			if new_position[1] < 0:  # up, but y<0
				self.path = self.generatePath(self.direction, True)
				return
		elif self.direction == self.DIR_RIGHT:  # right, but x reaches max
			if new_position[0] > (416 - 26):
				self.path = self.generatePath(self.direction, True)
				return
		elif self.direction == self.DIR_DOWN:
			if new_position[1] > (416 - 26):
				self.path = self.generatePath(self.direction, True)
				return
		elif self.direction == self.DIR_LEFT:
			if new_position[0] < 0:
				self.path = self.generatePath(self.direction, True)
				return

		new_rect = pygame.Rect(new_position, [26, 26])

		# collisions with tiles
		if new_rect.collidelist(self.level.obstacle_rects) != -1:
			self.path = self.generatePath(self.direction, True)
			return

		# collisions with other enemies
		for enemy in self.game.enemies:
			if enemy != self and new_rect.colliderect(enemy.rect):
				self.turnAround()
				self.path = self.generatePath(self.direction)
				return

		# collisions with players
		for player in self.game.players:
			if new_rect.colliderect(player.rect):
				self.turnAround()
				self.path = self.generatePath(self.direction)
				return

		# collisions with bonuses
		for bonus in self.game.bonuses:
			if new_rect.colliderect(bonus.rect):
				self.game.bonuses.remove(bonus)

		# if no collision, move enemy
		self.rect.topleft = new_rect.topleft


	def update(self, time_passed):
		Tank.update(self, time_passed)
		if self.state == self.STATE_ALIVE and not self.paused:
			self.move()

	def generatePath(self, direction=None, fix_direction=False):
		""" If direction is specified, try continue that way, otherwise choose at random
		fis_direction: 是否允许方向修正
		"""
		all_directions = [self.DIR_UP, self.DIR_RIGHT, self.DIR_DOWN, self.DIR_LEFT]

		opposite_direction = (self.direction + 2) % 4 if direction is None else (direction + 2) % 4

		directions = all_directions[:]
		directions.remove(opposite_direction)

		random.shuffle(directions)

		if direction is not None:
			directions.remove(direction)
			directions.insert(0, direction)  # if direction given, make it the first

		directions.append(opposite_direction)  # make opposite_direction the last

		# at first, work with general units (steps) not px
		x = int(round(self.rect.left / 16))
		y = int(round(self.rect.top / 16))

		new_direction = None

		# 按照设定好的方向优先级序列逐个判断是否可行。 
		# x,y是所在格子坐标, rect.move()以像素为单位
		for direction in directions:
			if direction == self.DIR_UP and y > 1:
				new_pos_rect = self.rect.move(0, -8)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					new_direction = direction
					break
			elif direction == self.DIR_RIGHT and x < 24:
				new_pos_rect = self.rect.move(8, 0)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					new_direction = direction
					break
			elif direction == self.DIR_DOWN and y < 24:
				new_pos_rect = self.rect.move(0, 8)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					new_direction = direction
					break
			elif direction == self.DIR_LEFT and x > 1:
				new_pos_rect = self.rect.move(-8, 0)
				if new_pos_rect.collidelist(self.level.obstacle_rects) == -1:
					new_direction = direction
					break

		# if we can go anywhere else, turn around
		if new_direction == None:
			new_direction = opposite_direction
			# print("nav izejas. griezhamies") # Latvian for "No exit. Turn around"

		# fix tanks position
		if fix_direction and new_direction == self.direction:
			fix_direction = False  # no need to fix

		self.rotate(new_direction, fix_position=fix_direction)

		positions = []

		x = self.rect.left
		y = self.rect.top

		if new_direction in (self.DIR_RIGHT, self.DIR_LEFT):
			axis_fix = self.nearest(y, 16) - y
		else:
			axis_fix = self.nearest(x, 16) - x
		axis_fix = 0

		# 以32像素的大格为单位, 随机走1~12步, 12步是地图宽度
		# 加上 axis_fix, 3 修正偏移位置 (很难恰好被单位宽32整除)
		pixels = self.nearest(random.randint(1, 12) * 32, 32) + axis_fix + 3

		if new_direction == self.DIR_UP:  # 生成直线路径序列
			for px in range(0, pixels, self.speed):
				positions.append([x, y-px])
		elif new_direction == self.DIR_RIGHT:
			for px in range(0, pixels, self.speed):
				positions.append([x+px, y])
		elif new_direction == self.DIR_DOWN:
			for px in range(0, pixels, self.speed):
				positions.append([x, y+px])
		elif new_direction == self.DIR_LEFT:
			for px in range(0, pixels, self.speed):
				positions.append([x-px, y])

		return positions