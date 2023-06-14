
import pygame
import uuid


class myRect(pygame.Rect):
	""" Add type property """
	def __init__(self, left, top, width, height, type):
		pygame.Rect.__init__(self, left, top, width, height)
		self.type = type


class Timer(object):
	def __init__(self):
		self.timers = []  # [dict, dict, ...]

	def add(self, interval, callback, repeat=-1):
		# 增加一个计时器
		options = {
			"interval": interval,
			"callback": callback,
			"repeat": repeat,
			"times": 0,
			"time": 0,
			"uuid": uuid.uuid4()
		}
		self.timers.append(options)

		return options["uuid"]  # 返回定时器的id，用于将来外部调用摧毁

	def destroy(self, uuid_nr):
		""" 依据 id 删除对应的计时器 """
		for timer in self.timers:
			if timer["uuid"] == uuid_nr:
				self.timers.remove(timer)
				break

	def update(self, time_passed):
		""" 更新一遍计时器 """
		for timer in self.timers:
			timer["time"] += time_passed
			if timer["time"] <= timer["interval"]:
				continue
			# 该计时器积累了一个固定周期

			timer["time"] -= timer["interval"]
			timer["times"] += 1  # 触发次数加一
			if timer["repeat"] > -1 and timer["times"] == timer["repeat"]:
				# 记录完指定次数，移除计时器
				self.timers.remove(timer)
			#try:
			timer["callback"]()
			# except:
			# 	try: # 一旦 callback 出错，移除对应的计时器
			# 		self.timers.remove(timer)
			# 	except:
			# 		pass


import cmath

def cartesian_to_polar(x, y):
	"""Convert cartesian coordinates to polar coordinates."""
	r = abs(complex(x, y))
	phi = cmath.phase(complex(x, y))
	return r, phi

def get_relative_polar_coordinates(a, b, required_size=None, normalize=True):
	"""Calculate the relative polar coordinates of b with respect to a."""
	width, height = 416, 416
	polar_coordinates = []
	for point in b:
		x, y = point[0], point[1]
		dx, dy = x-a[0], y-a[1]
		if normalize:
			dx /= width
			dy /= height
		r, phi = cartesian_to_polar(dx, dy)
		polar_coordinates.append([r, phi])
	if required_size is not None:
		while len(polar_coordinates)<required_size:
			polar_coordinates.append([0, 0])
		if len(polar_coordinates)>required_size:
			polar_coordinates = polar_coordinates[:required_size]
	return polar_coordinates