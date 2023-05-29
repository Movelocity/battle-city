import pygame
from explosion import Explosion

class Castle:
	""" Player's castle/fortress """
	(STATE_STANDING, STATE_DESTROYED, STATE_EXPLODING) = range(3)

	def __init__(self, game):
		self.game = game
		# images
		self.img_undamaged = self.game.sprites.subsurface(0, 15*2, 16*2, 16*2)
		self.img_destroyed = self.game.sprites.subsurface(16*2, 15*2, 16*2, 16*2)
		self.rect = pygame.Rect(12*16, 24*16, 32, 32)  # init position
		self.rebuild()  # start with undamaged and shiny castle

	def draw(self):
		""" Draw castle """
		self.game.screen.blit(self.image, self.rect.topleft)

		if self.state == self.STATE_EXPLODING:
			if not self.explosion.active:
				self.state = self.STATE_DESTROYED
				del self.explosion
			else:
				self.explosion.draw()

	def rebuild(self):
		""" Reset castle """
		self.state = self.STATE_STANDING
		self.image = self.img_undamaged
		self.active = True

	def destroy(self):
		""" Destroy castle """
		self.state = self.STATE_EXPLODING
		self.explosion = Explosion(self.game, self.rect.topleft)
		self.image = self.img_destroyed
		self.active = False