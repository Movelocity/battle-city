import numpy as np
import os
from game import Game
from model import CatEnv
import matplotlib.pyplot as plt

import random
from collections import namedtuple, deque

import torch
import torch.nn.functional as F
from model import QNetwork


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"using device: {device}")

class ReplayBuffer():
    def __init__(self, buffer_size, batch_size):
        self.buffer_size = int(buffer_size)
        self.batch_size = batch_size
        self.buffer = deque(maxlen=self.buffer_size)
    
    def add(self, state, action, reward, next_state, done):
        transition = (state, action, reward, next_state, 1-done)
        self.buffer.append(transition)

    def sample(self):
        indices = random.choices(range(len(self.buffer)), k=self.batch_size)
        transitions = [self.buffer[i] for i in indices]
        return transitions
    
    def __len__(self):
        return len(self.buffer)


class Agent():
    def __init__(
        self, 
        state_size, 
        action_size, 
        batch_size=128, 
        gamma=0.99, 
        tau=1e-3, 
        buffer_size=2e4, 
        update_interval=4
    ):
        self.action_size, self.batch_size = action_size, batch_size
        self.gamma = gamma  # discount factor
        self.tau = tau      # 副模型更新时保留的量
        self.update_interval = update_interval  # 模型更新间隔
        
        self.qnet_local = QNetwork(state_size, action_size).to(device)
        self.qnet_target = QNetwork(state_size, action_size).to(device)
        self.qnet_target.eval()
        self.optimizer = torch.optim.Adam(self.qnet_local.parameters(), lr=5e-4)
        self.scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=1000, gamma=0.9)
        self.memory = ReplayBuffer(buffer_size, batch_size)
        self.t_step = 0

    def step(self, state, action, reward, next_state, done):
        self.memory.add(state, action, reward, next_state, done)
        self.t_step = (self.t_step + 1) % self.update_interval
        if self.t_step == 0 and len(self.memory) > self.batch_size:
            self.learn()

    def act(self, state, eps=0.):
        state = torch.FloatTensor(state).unsqueeze(0).to(device)
        # Epsilon-greedy action selection
        if random.random() > eps:
            self.qnet_local.eval()
            with torch.no_grad():
                action_qvalues = self.qnet_local(state)
            return action_qvalues.argmax(dim=-1)[0].item()
        else:
            return random.choice(np.arange(self.action_size))

    def learn(self):
        transitions = self.memory.sample()
        states, actions, rewards, next_states, masks = zip(*transitions)
        
        states = torch.FloatTensor(np.array(states)).to(device)
        actions = torch.LongTensor(np.array(actions)).to(device)
        rewards = torch.FloatTensor(np.array(rewards)).to(device)
        next_states = torch.FloatTensor(np.array(next_states)).to(device)
        masks = torch.ByteTensor(np.array(masks)).to(device)
        
        # Compute Q-values and target values(discounted cumulated rewards)
        with torch.no_grad():
            next_q_values = self.qnet_target(next_states)
            next_q_values = next_q_values.max(1)[0]
            target_qvalues = rewards + masks * self.gamma * next_q_values
        
        self.qnet_local.train()
        pred_qvalues = self.qnet_local(states)
        pred_qvalues = pred_qvalues.gather(1, actions.unsqueeze(1)).squeeze(1)

        loss = F.l1_loss(pred_qvalues, target_qvalues)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        self.scheduler.step()

        if random.random() > 0.6: # 减少更新频率，但是不想写跟踪变量
            self.soft_update()

    def soft_update(self):
        # θ_target = τ*θ_local + (1 - τ)*θ_target
        for target_param, local_param in zip(self.qnet_target.parameters(), self.qnet_local.parameters()):
            target_param.data.copy_(
                self.tau*local_param.data + (1.0-self.tau)*target_param.data)


def train_dqn(
    agent, env,
    n_episodes=2000, 
    log_interval=100,
    max_t=1000,
    eps_start=1.0, 
    eps_end=0.001,
    eps_decay=0.995, 
    start_at=1
):
    scores_window = deque(maxlen=log_interval)  # last 100 scores
    steps_window = deque(maxlen=log_interval)
    eps = eps_start                    # initialize epsilon
    for i_episode in range(start_at, n_episodes+1):
        state, info = env.reset()
        score = 0
        for t in range(max_t):
            action = agent.act(state, eps)
            next_state, reward, done, truncated, info = env.step(action)
            if truncated: 
                next_state, info = env.reset()
            agent.step(state, action, reward, next_state, done)
            state = next_state
            score += reward
            if done: break
        scores_window.append(score)
        scores.append(score)              # for ploting
        eps = max(eps_end, eps_decay*eps) # decrease epsilon

        if i_episode % log_interval == 0:
            print(f'Episode {i_episode}\tAvg Score: {np.mean(scores_window):.2f}')
    torch.save(agent.qnet_local.state_dict(), f'/kaggle/working/tank{i_episode}.pth')


import argparse
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="The random seed")
    parser.add_argument("--episodes", type=int, default=6000, help="How many games to play")
    parser.add_argument("--batch_size", type=int, default=256, help="How many data to use together")
    parser.add_argument("--buffer_size", type=int, default=5e3, help="Replay memory buffer size")
    parser.add_argument("--update_interval", type=int, default=12, help="how many steps will cause an update")
    return parser.parse_args()

# python train.py --seed=1230 --episodes=4000 --batch_size=256

if __name__ == "__main__":
    os.environ['SDL_AUDIODRIVER'] = 'dsp'

    args = get_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    _env = Game(render_mode='grid')
    env = CatEnv(_env)
    
    scores = []  # 记录历史奖励
    agent = Agent(
        state_size=1377,
        action_size=6,
        batch_size=args.batch_size,
        buffer_size=args.buffer_size,
        update_interval=args.update_interval
    )

    train_dqn(agent, env, n_episodes=args.episodes)

    plt.figure(figsize=(8,3))
    plt.title(f"DQN - seed={args.seed}")
    plt.scatter(range(len(scores)), scores, s=3)
    plt.savefig(f"log-{args.episodes}.png")

# state, info = env.reset()
# print(state.shape)
# next_state, reward, done, done, info = env.step(5)
# print(next_state.shape)