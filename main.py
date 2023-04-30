#!/usr/bin/python
# coding=utf-8
from game import Game
import random
import cv2

if __name__ == "__main__":
	cv2.startWindowThread()
	game = Game(robot=True)
	# game.showMenu()

	game.reset()
	for i in range(9999):
		action = random.randint(0,5)
		state, reward, done = game.step(action)
		cv2.imshow('game', cv2.cvtColor(state, cv2.COLOR_RGB2BGR))
		print(f"action: {action}, reward:{reward}")
		if done: break
		c = cv2.waitKey(1)
		if c==ord('q') or c==ord('c'):
			print('break')
			cv2.destroyAllWindows()
			break