import os

import pygame
from utils import myRect

class Level():
	# tile constants
	(TILE_EMPTY, TILE_BRICK, TILE_STEEL, TILE_WATER, TILE_GRASS, TILE_FROZE) = range(6)
	TILE_SIZE = 16  # tile width/height in px
	char2tile = {
		"#": TILE_BRICK,
		"@": TILE_STEEL,
		"~": TILE_WATER,
		"%": TILE_GRASS,
		"-": TILE_FROZE
	}

	def __init__(self, game, level_nr):
		""" There are total 35 different levels. If level_nr is larger than 35, loop over
		to next according level so, for example, if level_nr ir 37, then load level 2 """
		self.game = game
		self.level_nr = level_nr
		# max number of enemies simultaneously  being on map
		self.max_active_enemies = 4

		self.current_water = 0
		self.tile_water1 = game.sprites.subsurface(64*2, 64*2, 8*2, 8*2)
		self.tile_water2 = game.sprites.subsurface(72*2, 64*2, 8*2, 8*2)

		self.tiles = {
			self.TILE_EMPTY: pygame.Surface((8*2, 8*2)),
			self.TILE_BRICK: game.sprites.subsurface(48*2, 64*2, 8*2, 8*2),
			self.TILE_STEEL: game.sprites.subsurface(48*2, 72*2, 8*2, 8*2),
			self.TILE_GRASS: game.sprites.subsurface(56*2, 72*2, 8*2, 8*2),
			self.TILE_WATER: self.tile_water1,
			self.TILE_FROZE: game.sprites.subsurface(64*2, 72*2, 8*2, 8*2)
		}

		self.loadLevel(level_nr)
		self.obstacle_rects = []    # tiles' rects on map, tanks cannot move over
		self.updateObstacleRects()  # update these tiles

		# self.game.timer_pool.add(400, lambda :self.toggleWaves())  暂时取消河流动效，后面要再加回来

	def hitTile(self, pos, power=1, sound=False):
		"""
			如果子弹停下, 返回 True。否则返回 False, 表示遇到河流、草块等非碰撞方块
			@param: pos Tile's x, y in px, 子弹等级, 是否播放音效
			@return: True if bullet was stopped, False otherwise
		"""
		for tile in self.mapr:
			if tile.topleft == pos:
				if tile.type == self.TILE_BRICK:
					if self.game.play_sounds and sound:
						self.game.sounds["brick"].play()
					self.mapr.remove(tile)
					self.updateObstacleRects()
					return True
				elif tile.type == self.TILE_STEEL:
					if self.game.play_sounds and sound:
						self.game.sounds["steel"].play()
					if power == 2:  # 强子弹击穿铁块
						self.mapr.remove(tile)
						self.updateObstacleRects()
					return True
				else:
					return False

	def toggleWaves(self):
		""" Toggle water image 水波效果 """
		if self.current_water == 0:
			self.tiles[self.TILE_WATER] = self.tile_water2
			self.current_water = 1
		else:
			self.tiles[self.TILE_WATER] = self.tile_water1
			self.current_water = 0


	def loadLevel(self, level_nr = 1):
		""" Load specified level 根据配置文件加载地图
		@return boolean Whether level was loaded
		"""
		filename = "levels/"+str(level_nr)
		if (not os.path.isfile(filename)):
			return False
		level = []
		f = open(filename, "r")
		data = f.read().split("\n")
		self.mapr = []
		x, y = 0, 0
		for row in data:
			for ch in row:
				if ch in self.char2tile.keys():
					self.mapr.append(myRect(x, y, self.TILE_SIZE, self.TILE_SIZE, self.char2tile[ch]))
				x += self.TILE_SIZE
			x = 0
			y += self.TILE_SIZE
		return True

	def draw(self, tiles=None):
		""" Draw specified map on top of existing surface """
		for tile in self.mapr:
			if tile.type in self.tiles.keys():
				self.game.screen.blit(self.tiles[tile.type], tile.topleft)

	def updateObstacleRects(self):
		""" Set self.obstacle_rects to all tiles' rects that players can destroy
		with bullets """
		self.obstacle_rects = [self.game.castle.rect]

		for tile in self.mapr:
			if tile.type in (self.TILE_BRICK, self.TILE_STEEL, self.TILE_WATER):
				self.obstacle_rects.append(tile)

	def buildFortress(self, tile):
		""" Build walls around castle made from tile """
		positions = [
			(11*self.TILE_SIZE, 23*self.TILE_SIZE),
			(11*self.TILE_SIZE, 24*self.TILE_SIZE),
			(11*self.TILE_SIZE, 25*self.TILE_SIZE),
			(14*self.TILE_SIZE, 23*self.TILE_SIZE),
			(14*self.TILE_SIZE, 24*self.TILE_SIZE),
			(14*self.TILE_SIZE, 25*self.TILE_SIZE),
			(12*self.TILE_SIZE, 23*self.TILE_SIZE),
			(13*self.TILE_SIZE, 23*self.TILE_SIZE)
		]

		for i, rect in enumerate(self.mapr):
			if rect.topleft in positions:
				self.mapr.remove(rect)  # remove obsolete blocks

		for pos in positions:
			self.mapr.append(myRect(pos[0], pos[1], self.TILE_SIZE, self.TILE_SIZE, tile))

		self.updateObstacleRects()