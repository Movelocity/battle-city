import pygame
import os, sys, random
import numpy as np
from label import Label
from castle import Castle
from tank import Tank
from enemy import Enemy
from player import Player
from level import Level
from bullet import Bullet
import utils

class Game():
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)
	TILE_SIZE = 16
	# set number of enemies by types (basic, fast, power, armor) according to level
	# 不同关卡的敌人类型数量
	levels_enemies = (
		(18,2,0,0), (14,4,0,2), (14,4,0,2), (2,5,10,3), (8,5,5,2),
		(9,2,7,2), (7,4,6,3), (7,4,7,2), (6,4,7,3), (12,2,4,2),
		(5,5,4,6), (0,6,8,6), (0,8,8,4), (0,4,10,6), (0,2,10,8),
		(16,2,0,2), (8,2,8,2), (2,8,6,4), (4,4,4,8), (2,8,2,8),
		(6,2,8,4), (6,8,2,4), (0,10,4,6), (10,4,4,2), (0,8,2,10),
		(4,6,4,6), (2,8,2,8), (15,2,2,1), (0,4,10,6), (4,8,4,4),
		(3,8,3,6), (6,4,2,8), (4,4,4,8), (0,10,4,6), (0,6,4,10)
	)

	def __init__(self, robot=True, full_screen=False, render_mode="rgb"):
		# render_mode: rgb, grid, feature
		self.sprites = None
		self.timer_pool = utils.Timer()
		self.robot = robot
		self.render_mode = render_mode
		size = width, height = 416, 416
		self.size = size

		pygame.init()

		self.sprites = pygame.transform.scale(pygame.image.load("images/sprites.png"), [192, 224]) # tanks, effects

		if self.robot:
			self.screen = pygame.Surface(size)
		else:  # human mode
			# size = width, height = 480, 416
			os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'  # center window
			pygame.display.set_caption("Battle City")
			# self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)  # FULL SCREEN mode if needed
			self.screen = pygame.display.set_mode(size)
			pygame.display.set_icon(self.sprites.subsurface(0, 0, 13*2, 13*2))  # Yellow Tank

		self.screen_buffer = np.zeros((width, height, 3), dtype=np.uint8)
		self.clock = pygame.time.Clock()

		# 裁剪贴图
		self.enemy_life_image = self.sprites.subsurface(81*2, 57*2, 7*2, 7*2)
		self.player_life_image = self.sprites.subsurface(89*2, 56*2, 7*2, 8*2)
		self.flag_image = self.sprites.subsurface(64*2, 49*2, 16*2, 15*2)

		# if true, no new enemies will be spawn during this time
		# 时停使得新敌人暂时不生成
		self.timefreeze = False

		# load custom font
		self.font = pygame.font.Font("fonts/prstart.ttf", 16)

		self.players = []
		self.enemies = []
		self.bullets = []
		self.bonuses = []
		self.labels = []
		self.castle = Castle(game=self)

	def triggerBonus(self, bonus, player, reward=None):
		""" Execute bonus powers 捡到地图上的奖励 """
		player.trophies["bonus"] += 1
		player.score += 500  # 直接加分
		if reward:
			reward[0] += 100
		if bonus.bonus == bonus.BONUS_GRENADE:   # 捡到手雷
			for enemy in self.enemies:
				enemy.explode()
				if reward:
					reward[0] += 60
		elif bonus.bonus == bonus.BONUS_HELMET:  # 护甲
			self.shieldPlayer(player, True, 10000)
		elif bonus.bonus == bonus.BONUS_SHOVEL:  # 铲子
			self.level.buildFortress(self.level.TILE_STEEL)
			self.timer_pool.add(
				interval=10000, 
				callback=lambda :self.level.buildFortress(self.level.TILE_BRICK), 
				repeat=1)
		elif bonus.bonus == bonus.BONUS_STAR:    # 五角星
			player.superpowers += 1
			if player.superpowers == 2:
				player.max_active_bullets = 2
		elif bonus.bonus == bonus.BONUS_TANK:    # 加命
			player.lives += 1
		elif bonus.bonus == bonus.BONUS_TIMER:   # 时停
			self.toggleEnemyFreeze(True)
			self.timer_pool.add(
				interval=10000, 
				callback=lambda :self.toggleEnemyFreeze(False), 
				repeat=1)
		self.bonuses.remove(bonus)  # 从列表中移出处理完的奖励

		self.labels.append(
			Label(game=self, position=bonus.rect.topleft, text="500", duration=500))  # 在地图上显示加分信息

	def remove_bonus(self, bonus):
		""" 给 enemy 在生成 bonus 的时候制作计时器用 """
		if bonus in self.bonuses:
			self.bonuses.remove(bonus)

	def shieldPlayer(self, player, shield=True, duration=None):
		""" Add/remove shield
		player: player (not enemy)
		shield: true/false
		duration: in ms. if none, do not remove shield automatically
		"""
		player.shielded = shield
		if shield:
			player.timer_uuid_shield = self.timer_pool.add(100, callback=player.toggleShieldImage)
			if duration != None:
				self.timer_pool.add(duration, lambda :self.shieldPlayer(player, False), 1)
		else:
			self.timer_pool.destroy(player.timer_uuid_shield)

	def spawnEnemy(self):
		""" Spawn new enemy if needed
		Only add enemy if:
			- there are at least one in queue
			- map capacity hasn't exceeded its quota
			- now isn't timefreeze
		"""
		if len(self.enemies) >= self.level.max_active_enemies:
			return False
		if len(self.level.enemies_left) < 1 or self.timefreeze:
			return False
		enemy = Enemy(game=self, level=self.level)
		self.enemies.append(enemy)
		return True

	def respawnPlayer(self, player, clear_scores=False):
		""" Respawn player """
		player.reset()
		if clear_scores:
			player.trophies = {
				"bonus" : 0, "enemy0" : 0, "enemy1" : 0, "enemy2" : 0, "enemy3" : 0
			}
		self.shieldPlayer(player, True, 4000)  # 提供4秒护盾

	def reloadPlayers(self):
		""" Init players 用于关卡开始时对玩家初始化
		If players already exist, just reset them
		"""
		if len(self.players) == 0:
			# first player
			x = 8 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 26) / 2
			y = 24 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 26) / 2

			player = Player(
				game=self, 
				level=self.level,
				position=[x, y], 
				direction=self.DIR_UP, 
				filename=(0, 0, 13*2, 13*2)
			)
			self.players.append(player)

		for player in self.players:
			player.level = self.level
			player.lives = 3
			self.respawnPlayer(player, True)

	def draw(self):
		self.screen.fill([0, 0, 0])
		self.level.draw([self.level.TILE_EMPTY, self.level.TILE_BRICK, self.level.TILE_STEEL, self.level.TILE_FROZE, self.level.TILE_WATER])
		self.castle.draw()

		for obj in self.enemies + self.labels + self.players + self.bullets + self.bonuses:
			obj.draw()

		self.level.draw([self.level.TILE_GRASS])

		# self.drawSidebar()
		if not self.robot:
			pygame.display.flip()  # Update the full display Surface to the screen

	def safe_update(self, screen, x, y, value):
		x, y = max(x, 0), max(y, 0)
		x, y = min(x, 25), min(y, 25)
		screen[x, y] = value

	def draw_tank_tile(self, screen, tank, fill=1):
		# for simple render mode
		x, y = tank.rect.topleft
		col, row = int(round(x/16)), int(round(y/16))
		if tank.direction == tank.DIR_UP:
			a, b, c, d = fill+1, fill+1, fill, fill
		elif tank.direction == tank.DIR_RIGHT:
			a, b, c, d = fill, fill+1, fill, fill+1
		elif tank.direction == tank.DIR_DOWN:
			a, b, c, d = fill, fill, fill+1, fill+1
		elif tank.direction == tank.DIR_LEFT:
			a, b, c, d = fill+1, fill, fill+1, fill
		screen[row, col], screen[row, col+1] = a, b
		screen[row+1, col], screen[row+1, col+1] = c, d

	def simple_render(self):
		"""简化版绘图26*26(一维), 用于加速验证RL算法"""
		# GROUND = 0
		PLAYER_HEAD, ENEMY_HEAD = 120, 90
		# type: value, 砖: 5, 铁: 6, 水: 7
		BRICK, STEEL, WATER = 21, 26, 30
		PLAYER_BULLET_1, PLAYER_BULLET_2 = 244, 245
		ENEMY_BULLET_1, ENEMY_BULLET_2 = 254, 255
		# MAX = 255

		screen = np.zeros((26, 26), dtype=np.uint8)
		for tile in self.level.mapr:
			x, y = tile.topleft
			# 方块以16像素为单位
			col, row = int(round(x/16)), int(round(y/16))
			if tile.type == self.level.TILE_BRICK:
				screen[row, col] = BRICK
			elif tile.type == self.level.TILE_STEEL:
				screen[row, col] = STEEL
			elif tile.type == self.level.TILE_WATER:
				screen[row, col] = WATER

		for e in self.enemies:
			self.draw_tank_tile(screen, e, fill=ENEMY_HEAD)

		for p in self.players:
			self.draw_tank_tile(screen, p, fill=PLAYER_HEAD)

		for b in self.bullets:  # 子弹动的比较多，坐标容易跑出去
			x, y = b.rect.topleft
			if b.owner_side == Bullet.OWNER_PLAYER:
				t1, t2 = PLAYER_BULLET_1, PLAYER_BULLET_2
			else:
				t1, t2 = ENEMY_BULLET_1, ENEMY_BULLET_2
			col, row = int(round(x/16)), int(round(y/16))
			if b.direction == b.DIR_UP:
				self.safe_update(screen, row, col, t1)
				self.safe_update(screen, row, col+1, t2)
			elif b.direction == b.DIR_RIGHT:
				self.safe_update(screen, row, col, t1)
				self.safe_update(screen, row+1, col, t2)
			elif b.direction == b.DIR_DOWN:
				self.safe_update(screen, row, col, t1)
				self.safe_update(screen, row, col+1, t2)
			elif b.direction == b.DIR_LEFT:
				self.safe_update(screen, row, col, t2)
				self.safe_update(screen, row+1, col, t1)
		return screen

	def render(self):
		self.draw()
		pygame.pixelcopy.surface_to_array(self.screen_buffer, self.screen)
		return self.screen_buffer.transpose((1,0,2)) # "rgb"

	def feature(self):
		player = self.players[0]
		direction = [0] *4
		direction[player.direction] = 1
		p_bullet_pos = [[0, 0]]
		can_fire = True
		e_bullets = []
		for b in self.bullets:
			if b.owner_side == Bullet.OWNER_ENEMY:
				e_bullets.append(b)
			elif b.owner == player and b.state == Bullet.STATE_ACTIVE:
				can_fire = False
				p_bullet_pos = utils.get_relative_polar_coordinates(
					player.rect.topleft, [b.rect.topleft])

		enemy_polars = utils.get_relative_polar_coordinates(
			player.rect.topleft, [e.rect.topleft for e in self.enemies], required_size=4)
		e_bullet_polars = utils.get_relative_polar_coordinates(
			player.rect.topleft, [b.rect.topleft for b in e_bullets], required_size=4)
		castle_ploar = utils.get_relative_polar_coordinates(
			player.rect.topleft, [self.castle.rect.topleft])

		result = [can_fire] + direction + p_bullet_pos[0] +\
			[p[0] for p in enemy_polars] + [p[0] for p in e_bullet_polars] + \
			[p[1] for p in enemy_polars] + [p[1] for p in e_bullet_polars] + castle_ploar[0]
		return np.array(result)

	def toggleEnemyFreeze(self, freeze=True):
		""" Freeze/defreeze all enemies """
		for enemy in self.enemies:
			enemy.paused = freeze
		self.timefreeze = freeze

	def reset(self, stage=1):
		""" Start next level. 下面会进入while循环 """
		self.castle.rebuild()
		del self.bullets[:]
		del self.enemies[:]
		del self.bonuses[:]
		del self.labels[:]
		del self.timer_pool.timers[:]

		# load level
		if stage == -1:
			self.stage = random.randint(1,35)
		else:
			self.stage = stage
		self.level = Level(game=self, level_nr=self.stage)

		enemies_l = self.levels_enemies[self.stage - 1]
		self.level.enemies_left = [0]*enemies_l[0] + [1]*enemies_l[1] + [2]*enemies_l[2] + [3]*enemies_l[3]
		random.shuffle(self.level.enemies_left)

		self.reloadPlayers()
		self.timer_pool.add(3000, self.spawnEnemy) 

		self.timefreeze = False
		self.game_over = False
		self.running = True     # if False, game will end w/o "game over" bussiness
		self.active = True      # if False, players won't be able to do anything

		if self.render_mode == "grid":
			return self.simple_render(), {}
		elif self.render_mode == "feature":
			return self.feature(), {}
		else:
			return self.render(), {}

	def step(self, action:int, time_passed=33):
		assert 0<=action<=5, f"action 值 {action} 不在有效范围"
		# 0: fire, 1~4: move, 5: idle
		# framerate=30

		reward = -0.1
		player = self.players[0]
		if player.state == player.STATE_ALIVE and not self.game_over and self.active:
			if action == 0:
				player.fire()
			elif action == 1:
				player.move(self.DIR_UP)
			elif action == 2:
				player.move(self.DIR_RIGHT)
			elif action == 3:
				player.move(self.DIR_DOWN)
			elif action == 4:
				player.move(self.DIR_LEFT)
		player.update(time_passed)

		for enemy in self.enemies:
			if enemy.state == enemy.STATE_DEAD and not self.game_over and self.active:
				self.enemies.remove(enemy)
				if len(self.level.enemies_left) == 0 and len(self.enemies) == 0:
					self.active = False
					print("Stage "+str(self.stage)+" completed")
			else:
				enemy.update(time_passed)

		if not self.game_over and self.active:
			if player.state == player.STATE_ALIVE:
				if player.bonus != None:
					reward_buffer = [0]
					self.triggerBonus(player.bonus, player, reward_buffer)  # 有奖励的话现在就给，然后划掉
					player.bonus = None
					reward += reward_buffer[0]
			elif player.state == player.STATE_DEAD:
				self.superpowers = 0
				player.lives -= 1
				reward -= 60
				if player.lives > 0:
					self.respawnPlayer(player)  # 还有命就复活，没命就结束游戏
				else:
					self.game_over = True

		for bullet in self.bullets:  # 移除被标记为 REMOVED 的子弹
			if bullet.state == bullet.STATE_REMOVED:
				self.bullets.remove(bullet)
			else:
				if bullet.update():
					reward += 100
				
		for bonus in self.bonuses:  # 移除超时的奖励
			if bonus.active == False:
				self.bonuses.remove(bonus)

		for label in self.labels:  # 移除超时的文字
			if not label.active:
				self.labels.remove(label)

		if not self.game_over:
			if not self.castle.active:  # 碉堡破了，游戏结束
				self.game_over = True
				reward -= 100

		self.timer_pool.update(time_passed)  # 计时器心跳

		# self.draw()
		# pygame.pixelcopy.surface_to_array(self.screen_buffer, self.screen)
		done = self.game_over 
		truncated = not self.active
		# return self.screen_buffer.transpose((1,0,2)), reward, done
		if self.render_mode == "grid":
			return self.simple_render(), reward, done, truncated, {}
		elif self.render_mode == "feature":
			return self.feature(), reward, done, truncated, {}
		else:
			return self.render(), reward, done, truncated, {}

	def save_record(self, stage, states, actions):
		import h5py
		assert len(states) == len(actions), f"length of data does not match: {len(states)}, {len(actions)}"
		filename = f"./game_cache/tank-{stage}-{len(states)}.h5"
		with h5py.File(filename, 'w') as f:
			f.create_dataset('states', data=np.array(states, dtype=np.uint8), compression='gzip')
			f.create_dataset('actions', data=np.array(actions, dtype=np.uint8), compression='gzip')
		print(f"{len(states)} states saved to {filename}")
	
	def load_record(self, dirname="./game_cache", prefix="tank-"):
		filenames = [f for f in os.listdir(dirname) if f.startswith(prefix)]
		states, actions = [], []
		for filename in filenames:
			with h5py.File(filename, 'r') as f:
				states_ = np.array(f['states'], dtype=np.uint8)
				actions_ = np.array(f['actions'])
			states.append(states_)
			actions.append(actions_)
		return states, actions

	def play(self):
		assert self.robot == False, "user_mode requires an Game object with robot=False"

		states, actions = [], []
		self.reset()  # 第一帧丢弃
		self.draw()
		active = True
		fire = False
		player = self.players[0]
		while active:
			time_passed = self.clock.tick(30)
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_q:  # 按 Q 退出
						active = False
					try:
						index = player.controls.index(event.key)
						if index == 0:
							fire = True
						elif index >0:
							player.pressed[index-1] = True
					except:
						pass
				elif event.type == pygame.KEYUP:
					try:
						index = player.controls.index(event.key)
						if index > 0:
							player.pressed[index-1] = False
					except:
						pass
			if fire:
				action = 0
				fire = False
			elif player.pressed[0] == True:
				action = 1
			elif player.pressed[1] == True:
				action = 2
			elif player.pressed[2] == True:
				action = 3
			elif player.pressed[3] == True:
				action = 4
			else:
				action = 5

			state, reward, done, truncated, info = self.step(action, time_passed=time_passed)
			if not self.active:
				self.reset()
			states.append(state)
			actions.append(action)
			self.draw()
		self.save_record(self.stage, states, actions)


