#!/usr/bin/python
# coding=utf-8
from game import Game
import random
import cv2
import time 
import random

random.seed(666)

if __name__ == "__main__":
	cv2.startWindowThread()
	game = Game(robot=False)
	# game.showMenu()
	game.play()
	# game.reset()
	# for i in range(9999):
	# 	action = random.randint(0,5)
	# 	for _ in range(6):
	# 		state, reward, done, truncated = game.step(action)
	# 	cv2.imshow('game', cv2.cvtColor(state, cv2.COLOR_RGB2BGR))

	# 	print(f"action: {action}, reward:{reward}, done: {done}, lives: {game.players[0].lives}")
	# 	if done: break
		
	# 	c = cv2.waitKey(33*6)
	# 	if c==ord('q') or c==ord('c'):
	# 		print('break')
	# 		cv2.destroyAllWindows()
	# 		break