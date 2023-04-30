import pygame


class Label():
	def __init__(self, game, position, text="", duration=None):
		self.game = game
		self.position = position
		self.active = True
		self.text = text
		self.font = pygame.font.SysFont("Arial", 13)

		if duration != None:  # 定时消失
			self.game.timer_pool.add(duration, self.destroy, 1)

	def draw(self):
		""" draw label """
		self.game.screen.blit(
			self.font.render(
				self.text, False, (200,200,200)   # text, antialias, color
			), 
			[self.position[0]+4, self.position[1]+8]
		)

	def destroy(self):
		self.active = False


