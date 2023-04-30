import pygame
import random

class Bonus():
	""" Various power-ups
	When bonus is spawned, it begins flashing and after some time dissapears

	Available bonusses:
		grenade	: Picking up the grenade power up instantly wipes out ever enemy presently on the screen, including Armor Tanks regardless of how many times you've hit them. You do not, however, get credit for destroying them during the end-stage bonus points.
		helmet	: The helmet power up grants you a temporary force field that makes you invulnerable to enemy shots, just like the one you begin every stage with.
		shovel	: The shovel power up turns the walls around your fortress from brick to stone. This makes it impossible for the enemy to penetrate the wall and destroy your fortress, ending the game prematurely. The effect, however, is only temporary, and will wear off eventually.
		star	: The star power up grants your tank with new offensive power each time you pick one up, up to three times. The first star allows you to fire your bullets as fast as the power tanks can. The second star allows you to fire up to two bullets on the screen at one time. And the third star allows your bullets to destroy the otherwise unbreakable steel walls. You carry this power with you to each new stage until you lose a life.
		tank	: The tank power up grants you one extra life. The only other way to get an extra life is to score 20000 points.
		timer	: The timer power up temporarily freezes time, allowing you to harmlessly approach every tank and destroy them until the time freeze wears off.
	"""

	# bonus types
	(BONUS_GRENADE, BONUS_HELMET, BONUS_SHOVEL, BONUS_STAR, BONUS_TANK, BONUS_TIMER) = range(6)

	def __init__(self, game, level):
		self.game = game
		self.level = level   # to know where to place
		self.active = True   # bonus lives only for a limited period of time
		self.visible = True  # blinking state
		self.rect = pygame.Rect(random.randint(0, 416-32), random.randint(0, 416-32), 32, 32)

		self.bonus = random.choice([
			self.BONUS_GRENADE,
			self.BONUS_HELMET,
			self.BONUS_SHOVEL,
			self.BONUS_STAR,
			self.BONUS_TANK,
			self.BONUS_TIMER
		])

		self.image = self.game.sprites.subsurface(16*2*self.bonus, 32*2, 16*2, 15*2)

	def draw(self):
		""" draw bonus """
		if self.visible:
			self.game.screen.blit(self.image, self.rect.topleft)

	def toggleVisibility(self):
		""" Toggle bonus visibility """
		self.visible = not self.visible