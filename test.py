from model import QNetwork, CatEnv
import cv2
import glob
import os
import torch
import shutil
import random
import numpy as np
from game import Game


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"using device: {device}")


class TestAgent():
    def __init__(
        self, 
        state_size, 
        action_size,
        ckpt,
        batch_size=None, 
        gamma=None, 
        tau=None, 
        buffer_size=None, 
        update_interval=None
    ):
        self.action_size, self.batch_size = action_size, batch_size
        self.qnet_local = QNetwork(state_size, action_size).to(device)
        self.qnet_local.load_state_dict(torch.load(ckpt, map_location="cpu"))
        self.qnet_local.eval()
        self.t_step = 0

    def act(self, state, eps=None):
        state = torch.FloatTensor(state).unsqueeze(0).to(device)
        # Epsilon-greedy action selection

        self.qnet_local.eval()
        with torch.no_grad():
            action_qvalues = self.qnet_local(state)
        return action_qvalues.argmax(dim=-1)[0].item()


def test_game(env, agent):
    state, info = env.reset()
    actions, score = [], 0

    # clear last output
    folder_path = "outputs"
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

    for t in range(1000):
        action = agent.act(state, eps=0)
        next_state, reward, done, truncated, info = env.step(action, render=True)  # 保存渲染结果
        if truncated: 
            next_state, info = env.reset()
        state = next_state
        score += reward
        actions.append(action)
        if done:
            break

    categories, a_counts = np.unique(actions, return_counts=True)
    print(f"score: {score}, actions: {categories}, {a_counts}")


def gen_video():
    imgfiles = glob.glob("outputs/*.jpg")
    imgfiles.sort(key=lambda f: int("".join(filter(str.isdigit, f))))
    print(len(imgfiles))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fps = 30

    img = cv2.imread(imgfiles[0])
    out = cv2.VideoWriter('tank-stage1.mp4', fourcc, fps, (img.shape[1], img.shape[0]))

    for f in imgfiles:
        img = cv2.imread(f)
        out.write(img)
    out.release()

import argparse
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", type=str, help="model .pth file path")
    parser.add_argument("--seed", type=int, default=42, help="The random seed")
    return parser.parse_args()

if __name__ == "__main__":
    os.environ['SDL_AUDIODRIVER'] = 'dsp'
    
    args = get_args()
    print(f"args: {args}")
    random.seed(args.seed)

    _env = Game(render_mode='grid')

    env = CatEnv(_env)
    state, info = env.reset()

    agent = TestAgent(
        state_size=1377,
        action_size=6,
        ckpt=args.ckpt
    )

    test_game(env, agent)
    gen_video()

