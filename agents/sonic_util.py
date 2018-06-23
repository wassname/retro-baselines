"""
Environments and wrappers for Sonic training.
"""

import gym
import numpy as np

from baselines.common.atari_wrappers import WarpFrame, FrameStack
from retro_contest.local import make

def make_env(stack=True, scale_rew=True):
    """
    Create an environment with some standard wrappers.
    """
    env = make("SonicTheHedgehog2-Genesis", state="EmeraldHillZone.Act2")
    env = SonicDiscretizer(env)
    env = AllowBacktracking(env)
    env = RandomGameReset(env)
    if scale_rew:
        env = RewardScaler(env)
    env = WarpFrame(env)
    if stack:
        env = FrameStack(env, 4)
    return env

class SonicDiscretizer(gym.ActionWrapper):
    """
    Wrap a gym-retro environment and make it use discrete
    actions for the Sonic game.
    """
    def __init__(self, env):
        super(SonicDiscretizer, self).__init__(env)
        buttons = ["B", "A", "MODE", "START", "UP", "DOWN", "LEFT", "RIGHT", "C", "Y", "X", "Z"]
        actions = [['LEFT'], ['RIGHT'], ['LEFT', 'DOWN'], ['RIGHT', 'DOWN'], ['DOWN'],
                   ['DOWN', 'B'], ['B']]
        self._actions = []
        for action in actions:
            arr = np.array([False] * 12)
            for button in action:
                arr[buttons.index(button)] = True
            self._actions.append(arr)
        self.action_space = gym.spaces.Discrete(len(self._actions))

    def action(self, a): # pylint: disable=W0221
        return self._actions[a].copy()

class RewardScaler(gym.RewardWrapper):
    """
    Bring rewards to a reasonable scale for PPO.

    This is incredibly important and effects performance
    drastically.
    """
    def reward(self, reward):
        return reward * 0.01

class AllowBacktracking(gym.Wrapper):
    """
    Use deltas in max(X) as the reward, rather than deltas
    in X. This way, agents are not discouraged too heavily
    from exploring backwards if there is no way to advance
    head-on in the level.
    """
    def __init__(self, env):
        super(AllowBacktracking, self).__init__(env)
        self._cur_x = 0
        self._max_x = 0

    def reset(self, **kwargs): # pylint: disable=E0202
        self._cur_x = 0
        self._max_x = 0
        return self.env.reset(**kwargs)

    def step(self, action): # pylint: disable=E0202
        obs, rew, done, info = self.env.step(action)
        self._cur_x += rew
        rew = max(0, self._cur_x - self._max_x)
        self._max_x = max(self._max_x, self._cur_x)
        return obs, rew, done, info

class RandomGameReset(gym.Wrapper):
    def __init__(self, env, state=None):
        """Reset game to a random level."""
        super().__init__(env)
        self.state = state

    def step(self, action):
        return self.env.step(action)

    def reset(self):
        # Reset to a random level (but don't change the game)
        try:
            game = self.env.unwrapped.gamename
        except AttributeError:
            logger.warning('no game name')
            pass
        else:
            game_path = retro.get_game_path(game)

            # pick a random state that's in the same game
            game_states = train_states[train_states.game == game]
            if self.state:
                game_states = game_states[game_states.state.str.contains(self.state)]

            # Load
            choice = game_states.sample().iloc[0]
            state = choice.state + '.state'
            logger.info('reseting to', game, state)
            with gzip.open(os.path.join(game_path, state), 'rb') as fh:
                self.env.unwrapped.initial_state = fh.read()

        return self.env.reset()
