#!/usr/bin/python
# coding=utf-8
from game import Game
import random
import cv2
import time 

if __name__ == "__main__":
	cv2.startWindowThread()
	game = Game(robot=False, render_mode="rgb")
	game.play()
