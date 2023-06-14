import numpy as np

from PIL import Image
import os
import torch
import torch.nn as nn
import torch.nn.functional as F

class CatEnv():  # 用来接管环境，一次返回两帧，中间忽略一些帧
    def __init__(self, env, skips=3):
        self.env = env
        self.skips = skips
        folder_path = "outputs"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"'{folder_path}' folder created.")

    def reset(self, id=1):
        self.count = 0
        state, info = self.env.reset()
        states = [state.flatten()]*2
        states.append(self.env.feature())  # 加上25个手工构造的特征，包含自身方向，敌军相对方位
        states = np.concatenate(states)
        return states, info

    def step(self, action=5, render=False):
        states = []
        next_state, reward, done, truncated, info = self.env.step(action)
        if render:
            self.count += 1
            screen = self.env.render()
            Image.fromarray(screen).save(f"outputs/{self.count:0>4}.jpg")
        rewards = reward
        states.append(next_state.flatten())
        for _ in range(self.skips):
            if done or truncated:
                break
            next_state, reward, done, truncated, info = self.env.step(action)
            if render:
                self.count += 1
                screen = self.env.render()
                Image.fromarray(screen).save(f"outputs/{self.count:0>4}.jpg")
            rewards += reward
        states.append(next_state.flatten())
        states.append(self.env.feature())
        states = np.concatenate(states)
        return states, rewards, done, truncated, info


class ResBlock(nn.Module):
    def __init__(self, in_dim, hid_dim, hid_layers=2):
        super(ResBlock, self).__init__()
        self.layers = nn.ModuleList()
        self.layers.append(nn.Linear(in_dim, hid_dim))
        for _ in range(hid_layers):
            self.layers.append(nn.Linear(hid_dim, hid_dim))
        self.layers.append(nn.Linear(hid_dim, in_dim))
    
    def forward(self, x):
        res = x
        for layer in self.layers:
            res = F.relu(layer(res))
        return x + res

class QNetwork(nn.Module):
    def __init__(self, state_size, action_size):
        super(QNetwork, self).__init__()

        self.mlp = nn.Sequential(
            nn.Linear(state_size, 512),
            nn.ReLU(),
            ResBlock(512, 256),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            ResBlock(256, 256),
            nn.Dropout(0.2),
            ResBlock(256, 256),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            ResBlock(128, 128, hid_layers=4),
            ResBlock(128, 128, hid_layers=4),
            nn.ReLU(),
            nn.Linear(128, action_size),
        )

    def forward(self, state):
        out = self.mlp(state)
        return out


class QNetwork_(nn.Module):
    def __init__(self, state_size, action_size):
        super(QNetwork, self).__init__()

        self.mlp = nn.Sequential(
            nn.Linear(state_size, 512),
            nn.ReLU(),
            ResBlock(512, 256),
            nn.Linear(512, 256),
            nn.ReLU(),
            ResBlock(256, 256),
            nn.Dropout(0.2),
            ResBlock(256, 256),
            nn.Linear(256, 128),
            nn.ReLU(),
            ResBlock(128, 128, hid_layers=4),
            ResBlock(128, 128, hid_layers=4),
            nn.ReLU(),
            nn.Linear(128, action_size),
        )

    def forward(self, state):
        out = self.mlp(state)
        return out