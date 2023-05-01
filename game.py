import pygame
import os, sys, random
import numpy as np

from label import Label
from castle import Castle
from tank import Tank
from enemy import Enemy
from player import Player
from level import Level

from utils import Timer


class Game():
	# direction constants
	(DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT) = range(4)
	TILE_SIZE = 16

	def __init__(self, robot=True, full_screen=False):
		self.play_sounds = False
		self.sprites = None
		self.timer_pool = Timer()
		self.robot = robot

		# center window
		os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'

		if self.play_sounds:
			pygame.mixer.pre_init(44100, -16, 1, 512)

		pygame.init()
		pygame.display.set_caption("Battle City")

		# size = width, height = 480, 416
		size = width, height = 416, 416

		if self.robot:
			self.screen = pygame.Surface(size)
		else:
			if full_screen:
				self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
			else:
				self.screen = pygame.display.set_mode(size)
		self.screen_buffer = np.zeros((width, height, 3), dtype=np.uint8)
		# self.screen_buffer = np.array([[[0, 0, 0] for _ in range(height)] for _ in range(width)])
		self.clock = pygame.time.Clock()

		# load sprites (funky version)
		#sprites = pygame.transform.scale2x(pygame.image.load("images/sprites.gif"))
		# load sprites (pixely version)
		# sprite = 贴图
		self.sprites = pygame.transform.scale(pygame.image.load("images/sprites.png"), [192, 224]) # tanks, effects
		#screen.set_colorkey((0,138,104))

		pygame.display.set_icon(self.sprites.subsurface(0, 0, 13*2, 13*2))  # Yellow Tank

		self.sounds = {}
		if self.play_sounds:
			pygame.mixer.init(44100, -16, 1, 512)
			self.sounds["start"] = pygame.mixer.Sound("sounds/gamestart.ogg")
			self.sounds["end"] = pygame.mixer.Sound("sounds/gameover.ogg")
			self.sounds["score"] = pygame.mixer.Sound("sounds/score.ogg")
			self.sounds["bg"] = pygame.mixer.Sound("sounds/background.ogg")
			self.sounds["fire"] = pygame.mixer.Sound("sounds/fire.ogg")
			self.sounds["bonus"] = pygame.mixer.Sound("sounds/bonus.ogg")
			self.sounds["explosion"] = pygame.mixer.Sound("sounds/explosion.ogg")
			self.sounds["brick"] = pygame.mixer.Sound("sounds/brick.ogg")
			self.sounds["steel"] = pygame.mixer.Sound("sounds/steel.ogg")

		# 裁剪贴图
		self.enemy_life_image = self.sprites.subsurface(81*2, 57*2, 7*2, 7*2)
		self.player_life_image = self.sprites.subsurface(89*2, 56*2, 7*2, 8*2)
		self.flag_image = self.sprites.subsurface(64*2, 49*2, 16*2, 15*2)

		# this is used in intro screen
		self.player_image = pygame.transform.rotate(self.sprites.subsurface(0, 0, 13*2, 13*2), 270)

		# if true, no new enemies will be spawn during this time
		# 时停使得新敌人暂时不生成
		self.timefreeze = False

		# load custom font
		self.font = pygame.font.Font("fonts/prstart.ttf", 16)

		# pre-render game-over text
		self.im_game_over = pygame.Surface((64, 40))
		self.im_game_over.set_colorkey((0,0,0))
		self.im_game_over.blit(self.font.render("GAME", False, (127, 64, 64)), [0, 0])
		self.im_game_over.blit(self.font.render("OVER", False, (127, 64, 64)), [0, 20])
		self.game_over_y = 416+40

		# number of players. here is defined preselected menu value
		self.nr_of_players = 1

		self.players = []
		self.enemies = []
		self.bullets = []
		self.bonuses = []
		self.labels = []
		self.castle = Castle(game=self)

	def triggerBonus(self, bonus, player):
		""" Execute bonus powers 捡到地图上的奖励 """
		if self.play_sounds:
			self.sounds["bonus"].play()

		player.trophies["bonus"] += 1
		player.score += 500  # 直接加分

		if bonus.bonus == bonus.BONUS_GRENADE:   # 捡到手雷
			for enemy in self.enemies:
				enemy.explode()
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

	def gameOver(self):
		""" End game and return to menu, 玩家没命或碉堡爆炸立即触发, 3秒后触发得分板界面 """
		print("Game Over")
		if self.play_sounds:
			for sound in self.sounds:
				self.sounds[sound].stop()
			self.sounds["end"].play()

		self.game_over_y = 416+40

		self.game_over = True
		self.timer_pool.add(3000, self.showScores, 1)

	def gameOverScreen(self):
		""" Show game over screen. Called in showScore() """
		# stop game main loop (if any)
		self.running = False

		self.screen.fill([0, 0, 0])

		self.writeInBricks("game", [125, 140])
		self.writeInBricks("over", [125, 220])
		pygame.display.flip()

		while 1:
			time_passed = self.clock.tick(50)
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_RETURN:
						self.showMenu()
						return

	def showMenu(self):
		""" Show game menu
		Redraw screen only when up or down key is pressed. When enter is pressed,
		exit from this screen and start the game with selected number of players
		"""
		self.running = False   # stop game main loop (if any)
		del self.timer_pool.timers[:]   # clear all timers
		del self.players[:]
		self.stage = 0         # set current stage to 0
		self.animateIntroScreen()

		main_loop = True
		while main_loop:
			time_passed = self.clock.tick(50)

			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					quit()
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_q:
						quit()
					elif event.key == pygame.K_UP:  # 选择玩家个数
						if self.nr_of_players == 2:
							self.nr_of_players = 1
							self.drawIntroScreen()  # 刷新界面
					elif event.key == pygame.K_DOWN:
						if self.nr_of_players == 1:
							self.nr_of_players = 2
							self.drawIntroScreen()
					elif event.key == pygame.K_RETURN:
						main_loop = False
		self.nextLevel()

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

			# second player
			if self.nr_of_players == 2:
				x = 16 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 26) / 2
				y = 24 * self.TILE_SIZE + (self.TILE_SIZE * 2 - 26) / 2
				player = Player(
					game=self, 
					level=self.level,
					position=[x, y], 
					direction=self.DIR_UP, 
					filename=(16*2, 0, 13*2, 13*2)
				)
				player.controls = [102, 119, 100, 115, 97]
				self.players.append(player)

		for player in self.players:
			player.level = self.level
			self.respawnPlayer(player, True)

	def showScores(self):
		""" Show level scores, 游戏结束，计算得分 """
		# stop game main loop (if any)
		self.running = False

		# clear all timers
		del self.timer_pool.timers[:]

		if self.play_sounds:
			for sound in self.sounds:
				self.sounds[sound].stop()

		hiscore = self.loadHiscore()

		# update hiscore if needed
		if self.players[0].score > hiscore:
			hiscore = self.players[0].score
			self.saveHiscore(hiscore)
		if self.nr_of_players == 2 and self.players[1].score > hiscore:
			hiscore =self.players[1].score
			self.saveHiscore(hiscore)

		img_tanks = [
			self.sprites.subsurface(32*2, 0, 13*2, 15*2),
			self.sprites.subsurface(48*2, 0, 13*2, 15*2),
			self.sprites.subsurface(64*2, 0, 13*2, 15*2),
			self.sprites.subsurface(80*2, 0, 13*2, 15*2)
		]

		img_arrows = [
			self.sprites.subsurface(81*2, 48*2, 7*2, 7*2),
			self.sprites.subsurface(88*2, 48*2, 7*2, 7*2)
		]

		self.screen.fill([0, 0, 0])

		# colors
		black = pygame.Color("black")
		white = pygame.Color("white")
		purple = pygame.Color(127, 64, 64)
		pink = pygame.Color(191, 160, 128)

		self.screen.blit(self.font.render("HI-SCORE", False, purple), [105, 35])
		self.screen.blit(self.font.render(str(hiscore), False, pink), [295, 35])
		self.screen.blit(self.font.render("STAGE"+str(self.stage).rjust(3), False, white), [170, 65])
		self.screen.blit(self.font.render("I-PLAYER", False, purple), [25, 95])

		#player 1 global score
		self.screen.blit(self.font.render(str(self.players[0].score).rjust(8), False, pink), [25, 125])

		if self.nr_of_players == 2:
			self.screen.blit(self.font.render("II-PLAYER", False, purple), [310, 95])

			#player 2 global score
			self.screen.blit(self.font.render(str(self.players[1].score).rjust(8), False, pink), [325, 125])

		# tanks and arrows
		for i in range(4):
			self.screen.blit(img_tanks[i], [226, 160+(i*45)])
			self.screen.blit(img_arrows[0], [206, 168+(i*45)])
			if self.nr_of_players == 2:
				self.screen.blit(img_arrows[1], [258, 168+(i*45)])

		self.screen.blit(self.font.render("TOTAL", False, white), [70, 335])

		# total underline
		pygame.draw.line(self.screen, white, [170, 330], [307, 330], 4)
		pygame.display.flip()

		self.clock.tick(2)
		interval = 5

		# points and kills
		for i in range(4):
			# total specific tanks
			tanks = self.players[0].trophies["enemy"+str(i)]

			for n in range(tanks+1):
				if n > 0 and self.play_sounds:
					self.sounds["score"].play()

				# erase previous text
				self.screen.blit(self.font.render(str(n-1).rjust(2), False, black), [170, 168+(i*45)])
				# print new number of enemies
				self.screen.blit(self.font.render(str(n).rjust(2), False, white), [170, 168+(i*45)])
				# erase previous text
				self.screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [25, 168+(i*45)])
				# print new total points per enemy
				self.screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [25, 168+(i*45)])
				pygame.display.flip()
				self.clock.tick(interval)

			if self.nr_of_players == 2:
				tanks = self.players[1].trophies["enemy"+str(i)]

				for n in range(tanks+1):

					if n > 0 and self.play_sounds:
						self.game.sounds["score"].play()

					self.screen.blit(self.font.render(str(n-1).rjust(2), False, black), [277, 168+(i*45)])
					self.screen.blit(self.font.render(str(n).rjust(2), False, white), [277, 168+(i*45)])

					self.screen.blit(self.font.render(str((n-1) * (i+1) * 100).rjust(4)+" PTS", False, black), [325, 168+(i*45)])
					self.screen.blit(self.font.render(str(n * (i+1) * 100).rjust(4)+" PTS", False, white), [325, 168+(i*45)])

					pygame.display.flip()
					self.clock.tick(interval)

			self.clock.tick(interval)

		# total tanks
		tanks = sum([i for i in self.players[0].trophies.values()]) - self.players[0].trophies["bonus"]
		self.screen.blit(self.font.render(str(tanks).rjust(2), False, white), [170, 335])
		if self.nr_of_players == 2:
			tanks = sum([i for i in self.players[1].trophies.values()]) - self.players[1].trophies["bonus"]
			self.screen.blit(self.font.render(str(tanks).rjust(2), False, white), [277, 335])

		pygame.display.flip()

		# do nothing for 2 seconds
		self.clock.tick(1)
		self.clock.tick(1)

		if self.game_over:
			self.gameOverScreen()
		else:
			self.nextLevel()


	def draw(self):
		self.screen.fill([0, 0, 0])
		self.level.draw([self.level.TILE_EMPTY, self.level.TILE_BRICK, self.level.TILE_STEEL, self.level.TILE_FROZE, self.level.TILE_WATER])
		self.castle.draw()

		for obj in self.enemies + self.labels + self.players + self.bullets + self.bonuses:
			obj.draw()

		self.level.draw([self.level.TILE_GRASS])

		if self.game_over:
			if self.game_over_y > 188:
				self.game_over_y -= 4
			self.screen.blit(self.im_game_over, [176, self.game_over_y]) # 176=(416-64)/2

		# self.drawSidebar()

		if not self.robot:
			pygame.display.flip()  # Update the full display Surface to the screen

	def drawSidebar(self):
		x = 416
		y = 0
		self.screen.fill([100, 100, 100], pygame.Rect([416, 0], [64, 416]))

		xpos = x + 16
		ypos = y + 16

		# draw enemy lives
		for n in range(len(self.level.enemies_left) + len(self.enemies)):
			self.screen.blit(self.enemy_life_image, [xpos, ypos])
			if n % 2 == 1:
				xpos = x + 16
				ypos+= 17
			else:
				xpos += 17

		# players' lives
		if pygame.font.get_init():
			text_color = pygame.Color('black')
			for n in range(len(self.players)):
				if n == 0:
					self.screen.blit(self.font.render(str(n+1)+"P", False, text_color), [x+16, y+200])
					self.screen.blit(self.font.render(str(self.players[n].lives), False, text_color), [x+31, y+215])
					self.screen.blit(self.player_life_image, [x+17, y+215])
				else:
					self.screen.blit(self.font.render(str(n+1)+"P", False, text_color), [x+16, y+240])
					self.screen.blit(self.font.render(str(self.players[n].lives), False, text_color), [x+31, y+255])
					self.screen.blit(self.player_life_image, [x+17, y+255])

			self.screen.blit(self.flag_image, [x+17, y+280])
			self.screen.blit(self.font.render(str(self.stage), False, text_color), [x+17, y+312])


	def drawIntroScreen(self, put_on_surface=True):
		""" Draw intro (menu) screen 开始界面
		@param boolean put_on_surface If True, flip display after drawing
		@return None
		"""
		self.screen.fill([0, 0, 0])

		if pygame.font.get_init():  # 只用绘制一次
			hiscore = self.loadHiscore()
			self.screen.blit(self.font.render("HI- "+str(hiscore), True, pygame.Color('white')), [170, 35])
			self.screen.blit(self.font.render("1 PLAYER", True, pygame.Color('white')), [165, 250])
			self.screen.blit(self.font.render("2 PLAYERS", True, pygame.Color('white')), [165, 275])
			self.screen.blit(self.font.render("(c) 1980 1985 NAMCO LTD.", True, pygame.Color('white')), [50, 350])
			self.screen.blit(self.font.render("ALL RIGHTS RESERVED", True, pygame.Color('white')), [85, 380])

		if self.nr_of_players == 1:
			self.screen.blit(self.player_image, [125, 245])
		elif self.nr_of_players == 2:
			self.screen.blit(self.player_image, [125, 270])

		self.writeInBricks("battle", [65, 80])
		self.writeInBricks("city", [129, 160])

		if put_on_surface:
			pygame.display.flip()

	def animateIntroScreen(self):
		""" Slide intro (menu) screen from bottom to top
		If Enter key is pressed, finish animation immediately
		@return None
		"""
		self.drawIntroScreen(False)
		screen_cp = self.screen.copy()
		self.screen.fill([0, 0, 0])

		y = 416
		while (y > 0):
			time_passed = self.clock.tick(50)
			for event in pygame.event.get():
				if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
					y = 0  # 按下回车结束入场动画
					break
			self.screen.blit(screen_cp, [0, y])
			pygame.display.flip()
			y -= 5

		self.screen.blit(screen_cp, [0, 0])
		pygame.display.flip()  #  更新整个待显示的  Surface 对象到屏幕上


	def chunks(self, l, n):
		""" Split text string in chunks of specified size, 把输入字符按n个一组切分
		@param string l Input string
		@param int n Size (number of characters) of each chunk
		@return list
		"""
		return [l[i:i+n] for i in range(0, len(l), n)]

	def writeInBricks(self, text, pos):
		""" Write specified text in "brick font" 用砖块贴图写字
		Only those letters are available that form words "Battle City" and "Game Over"
		Both lowercase and uppercase are valid input, but output is always uppercase
		Each letter consists of 7x7 bricks which is converted into 49 character long string
		of 1's and 0's which in turn is then converted into hex to save some bytes
		@return None
		"""
		bricks = self.sprites.subsurface(56*2, 64*2, 8*2, 8*2)
		brick1 = bricks.subsurface((0, 0, 8, 8))
		brick2 = bricks.subsurface((8, 0, 8, 8))
		brick3 = bricks.subsurface((8, 8, 8, 8))
		brick4 = bricks.subsurface((0, 8, 8, 8))

		alphabet = {
			"a" : "0071b63c7ff1e3",
			"b" : "01fb1e3fd8f1fe",
			"c" : "00799e0c18199e",
			"e" : "01fb060f98307e",
			"g" : "007d860cf8d99f",
			"i" : "01f8c183060c7e",
			"l" : "0183060c18307e",
			"m" : "018fbffffaf1e3",
			"o" : "00fb1e3c78f1be",
			"r" : "01fb1e3cff3767",
			"t" : "01f8c183060c18",
			"v" : "018f1e3eef8e08",
			"y" : "019b3667860c18"
		}

		abs_x, abs_y = pos

		for letter in text.lower():
			binstr = ""
			for h in self.chunks(alphabet[letter], 2):
				binstr += str(bin(int(h, 16)))[2:].rjust(8, "0")
			binstr = binstr[7:]

			x, y = 0, 0
			letter_w = 0
			surf_letter = pygame.Surface((56, 56))
			for j, row in enumerate(self.chunks(binstr, 7)):
				for i, bit in enumerate(row):
					if bit == "1":
						if i%2 == 0 and j%2 == 0:
							surf_letter.blit(brick1, [x, y])
						elif i%2 == 1 and j%2 == 0:
							surf_letter.blit(brick2, [x, y])
						elif i%2 == 1 and j%2 == 1:
							surf_letter.blit(brick3, [x, y])
						elif i%2 == 0 and j%2 == 1:
							surf_letter.blit(brick4, [x, y])
						if x > letter_w:
							letter_w = x
					x += 8
				x = 0
				y += 8
			self.screen.blit(surf_letter, [abs_x, abs_y])
			abs_x += letter_w + 16

	def toggleEnemyFreeze(self, freeze=True):
		""" Freeze/defreeze all enemies """
		for enemy in self.enemies:
			enemy.paused = freeze
		self.timefreeze = freeze

	def loadHiscore(self):
		""" Load hiscore
		Really primitive version =] If for some reason hiscore cannot be loaded, return 20000
		@return int
		"""
		filename = ".hiscore"
		if (not os.path.isfile(filename)):
			return 20000

		f = open(filename, "r")
		hiscore = int(f.read())

		if hiscore > 19999 and hiscore < 1000000:
			return hiscore
		else:
			print("cheater =[")
			return 20000

	def saveHiscore(self, hiscore):
		""" Save hiscore 保存历史记录
		@return boolean
		"""
		try:
			f = open(".hiscore", "w")
		except:
			print("Can't save hi-score")
			return False
		f.write(str(hiscore))
		f.close()
		return True


	def finishLevel(self):
		""" Finish current level
		Show earned scores and advance to the next stage
		"""
		if self.play_sounds:
			self.sounds["bg"].stop()

		self.active = False
		self.timer_pool.add(3000, self.showScores, 1)

		print("Stage "+str(self.stage)+" completed")

	def reset(self):
		""" Start next level. 下面会进入while循环 """
		del self.bullets[:]
		del self.enemies[:]
		del self.bonuses[:]
		self.castle.rebuild()
		del self.timer_pool.timers[:]

		# load level
		self.stage = random.randint(1,35)
		self.level = Level(game=self, level_nr=self.stage)
		self.timefreeze = False

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
		enemies_l = levels_enemies[self.stage - 1]

		self.level.enemies_left = [0]*enemies_l[0] + [1]*enemies_l[1] + [2]*enemies_l[2] + [3]*enemies_l[3]
		random.shuffle(self.level.enemies_left)

		self.reloadPlayers()

		self.timer_pool.add(3000, self.spawnEnemy) 

		self.game_over = False  # if True, start "game over" animation
		self.running = True     # if False, game will end w/o "game over" bussiness
		self.active = True      # if False, players won't be able to do anything
		self.draw()

		pygame.pixelcopy.surface_to_array(self.screen_buffer, self.screen)
		return self.screen_buffer.transpose((1,0,2))


	def step(self, action:int):
		assert 0<=action<=5, f"action 值 {action} 不在有效范围"
		# 0: fire, 1~4: move, 5: idle

		reward = -1
		player = self.players[0]
		if player.state == player.STATE_ALIVE:
			if action == 0:
				player.fire()
			elif action < 5:
				player.pressed[action-1] = True

		# 1/3 秒执行一次动作
		for _ in range(10):
			time_passed = 33  # framerate=30
			if player.state == player.STATE_ALIVE and not self.game_over and self.active:
				if player.pressed[0] == True:
					player.move(self.DIR_UP)
				elif player.pressed[1] == True:
					player.move(self.DIR_RIGHT)
				elif player.pressed[2] == True:
					player.move(self.DIR_DOWN)
				elif player.pressed[3] == True:
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
				for player in self.players:
					if player.state == player.STATE_ALIVE:
						if player.bonus != None and player.side == player.SIDE_PLAYER:
							self.triggerBonus(bonus, player)  # 有奖励的话现在就给，然后划掉
							player.bonus = None
					elif player.state == player.STATE_DEAD:
						self.superpowers = 0
						player.lives -= 1
						reward -= 30
						if player.lives > 0:
							self.respawnPlayer(player)  # 还有命就复活，没命就结束游戏
						else:
							self.game_over = True

			for bullet in self.bullets:  # 移除被标记为 REMOVED 的子弹
				if bullet.state == bullet.STATE_REMOVED:
					self.bullets.remove(bullet)
				else:
					if bullet.update():
						reward += 20
					
			for bonus in self.bonuses:  # 移除超时的奖励
				if bonus.active == False:
					self.bonuses.remove(bonus)

			for label in self.labels:  # 移除超时的文字
				if not label.active:
					self.labels.remove(label)

			if not self.game_over:
				if not self.castle.active:  # 碉堡破了，游戏结束
					self.game_over = True
					reward -= 50

			self.timer_pool.update(time_passed)  # 计时器心跳

		player.pressed = [False] * 4
		self.draw()
		pygame.pixelcopy.surface_to_array(self.screen_buffer, self.screen)
		done = self.game_over or not self.active
		# print(self.screen_buffer.shape)
		# print(self.screen_buffer.dtype)
		return self.screen_buffer.transpose((1,0,2)), reward, done

	def nextLevel(self):
		""" Start next level. 下面会进入while循环 """
		del self.bullets[:]
		del self.enemies[:]
		del self.bonuses[:]
		self.castle.rebuild()
		del self.timer_pool.timers[:]

		# load level
		self.stage = self.stage%35 + 1
		self.level = Level(game=self, level_nr=self.stage)
		self.timefreeze = False

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

		if self.stage <= 35:
			enemies_l = levels_enemies[self.stage - 1]
		else:
			enemies_l = levels_enemies[34]
		self.level.enemies_left = [0]*enemies_l[0] + [1]*enemies_l[1] + [2]*enemies_l[2] + [3]*enemies_l[3]
		random.shuffle(self.level.enemies_left)

		if self.play_sounds:
			self.sounds["start"].play()
			self.timer_pool.add(4330, lambda :sounds["bg"].play(-1), 1)

		self.reloadPlayers()

		self.timer_pool.add(3000, self.spawnEnemy) 
		print("enemy spawning timer added")
		self.game_over = False  # if True, start "game over" animation
		self.running = True     # if False, game will end w/o "game over" bussiness
		self.active = True      # if False, players won't be able to do anything

		self.draw()

		while self.running:  # 游戏主线程
			time_passed = self.clock.tick(50)  # framerate=50

			for event in pygame.event.get():
				if event.type == pygame.MOUSEBUTTONDOWN:
					pass
				elif event.type == pygame.QUIT:  # 来自 pygame 的 quit 信号？
					quit()
				elif event.type == pygame.KEYDOWN and not self.game_over and self.active:

					if event.key == pygame.K_q:  # 按 Q 退出
						quit()
					
					elif event.key == pygame.K_m:  # toggle sounds 设置或取消静音
						self.play_sounds = not self.play_sounds
						if not self.play_sounds:
							pygame.mixer.stop()
						else:
							self.sounds["bg"].play(-1)

					for player in self.players:
						if player.state == player.STATE_ALIVE:
							try:  # 从 Tank 类 controls 列表中获取按键序号
								index = player.controls.index(event.key)
							except:
								pass
							else:  # 根据按下按键序号设置标志
								if index == 0:
									if player.fire() and self.play_sounds:
										self.sounds["fire"].play()
								elif index == 1:
									player.pressed[0] = True
								elif index == 2:
									player.pressed[1] = True
								elif index == 3:
									player.pressed[2] = True
								elif index == 4:
									player.pressed[3] = True

				elif event.type == pygame.KEYUP and not self.game_over and self.active:
					for player in self.players:
						if player.state == player.STATE_ALIVE:
							try:
								index = player.controls.index(event.key)
							except:
								pass
							else:  # 根据抬起按键序号取消标志
								if index == 1:
									player.pressed[0] = False
								elif index == 2:
									player.pressed[1] = False
								elif index == 3:
									player.pressed[2] = False
								elif index == 4:
									player.pressed[3] = False

			for player in self.players:
				if player.state == player.STATE_ALIVE and not self.game_over and self.active:
					if player.pressed[0] == True:
						player.move(self.DIR_UP)
					elif player.pressed[1] == True:
						player.move(self.DIR_RIGHT)
					elif player.pressed[2] == True:
						player.move(self.DIR_DOWN)
					elif player.pressed[3] == True:
						player.move(self.DIR_LEFT)
				player.update(time_passed)

			for enemy in self.enemies:
				if enemy.state == enemy.STATE_DEAD and not self.game_over and self.active:
					self.enemies.remove(enemy)
					if len(self.level.enemies_left) == 0 and len(self.enemies) == 0:
						self.finishLevel()
				else:
					enemy.update(time_passed)

			if not self.game_over and self.active:
				for player in self.players:
					if player.state == player.STATE_ALIVE:
						if player.bonus != None and player.side == player.SIDE_PLAYER:
							self.triggerBonus(bonus, player)  # 有奖励的话现在就给，然后划掉
							player.bonus = None
					elif player.state == player.STATE_DEAD:
						self.superpowers = 0
						player.lives -= 1
						if player.lives > 0:
							self.respawnPlayer(player)  # 还有命就复活，没命就结束游戏
						else:
							self.gameOver()

			for bullet in self.bullets:  # 移除被标记为 REMOVED 的子弹
				if bullet.state == bullet.STATE_REMOVED:
					self.bullets.remove(bullet)
				else:
					bullet.update()

			for bonus in self.bonuses:  # 移除不再 ACTIVE 的奖励
				if bonus.active == False:
					self.bonuses.remove(bonus)

			for label in self.labels:  # 移除不再 ACTIVE 的奖励
				if not label.active:
					self.labels.remove(label)

			if not self.game_over:     
				if not self.castle.active:  # 碉堡破了，游戏结束
					self.gameOver()

			self.timer_pool.update(time_passed)  # 计时器心跳
			self.draw()