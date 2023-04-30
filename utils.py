
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


