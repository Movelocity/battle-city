

class Explosion():
	def __init__(self, game, position, interval=None, images=None):
		self.game = game
		self.position = [position[0]-16, position[1]-16]
		self.active = True

		if interval == None:
			interval = 100

		if images == None:
			images = [
				game.sprites.subsurface(0, 80*2, 32*2, 32*2),
				game.sprites.subsurface(32*2, 80*2, 32*2, 32*2),
				game.sprites.subsurface(64*2, 80*2, 32*2, 32*2)
			]
		
		images.reverse()
		self.images = [] + images
		self.image = self.images.pop()
		self.game.timer_pool.add(interval, self.update, len(self.images) + 1)

	def draw(self):
		""" draw current explosion frame """
		self.game.screen.blit(self.image, self.position)

	def update(self):
		""" Advace to the next image """
		if len(self.images) > 0:
			self.image = self.images.pop()
		else:
			self.active = False