"""Adapted from https://github.com/ysymyth/ReAct/blob/master/alfworld.ipynb"""

import os
import sys
import json
import yaml
import openai
import importlib
import alfworld
import alfworld.agents.environment
from env_history import EnvironmentHistory

from typing import List, Dict, Any, Tuple

openai.api_key = os.environ["OPENAI_API_KEY"]
FOLDER = './prompts'
PROMPT_FILE = 'alfworld_3prompts.json'
with open(os.path.join(FOLDER, PROMPT_FILE), 'r') as f:
    d = json.load(f)
with open('./reflexion_few_shot_examples.txt', 'r') as f:
    challenge_examples = f.read()

def llm(prompt, stop=["\n"]):
    try:
        cur_try = 0
        while cur_try < 6:
            response = openai.Completion.create(
              model="text-davinci-002",
              prompt=prompt,
              temperature=cur_try * 0.2,
              max_tokens=100,
              top_p=1,
              frequency_penalty=0.0,
              presence_penalty=0.0,
              stop=stop
            )
            text = response["choices"][0]["text"]
            # dumb way to do this
            if len(text.strip()) >= 5:
                return response["choices"][0]["text"]
            cur_try += 1
        return ""
    except Exception as e:
        print(prompt)
        print(e)
        import sys
        sys.exit(1)

def process_ob(ob):
    if ob.startswith('You arrive at loc '):
        ob = ob[ob.find('. ')+2:]    
    return ob

def alfworld_run(env, base_prompt, memory: List[str], to_print=True, ob='') -> Tuple[EnvironmentHistory, bool]:
    if len(memory) > 3:
        env_history = EnvironmentHistory(base_prompt, ob, memory[-3:], [])
    else:
        env_history = EnvironmentHistory(base_prompt, ob, memory, [])
    env_history.reset()
    # init_prompt = prompt + ob + '\n>'
    # prompt = ''
    if to_print:
        print(ob)
        sys.stdout.flush()
    cur_step = 0
    while cur_step < 50:
        # action = llm(init_prompt + prompt, stop=['\n']).strip()
        action = llm(str(env_history) + ">", stop=['\n']).strip()
        env_history.add("action", action)
        observation, reward, done, info = env.step([action])
        observation, reward, done = process_ob(observation[0]), info['won'][0], done[0]
        if action.startswith('think:'):
            observation = 'OK.'
        env_history.add("observation", observation)
        if to_print:
            print(f'> {action}\n{observation}')
            sys.stdout.flush()
        # prompt += f' {action}\n{observation}\n>'
        if done:
            return env_history, True
        elif env_history.check_is_exhausted():
            return env_history, False
        cur_step += 1
    return env_history, False

PREFIXES = {
    'pick_and_place': 'put',
    'pick_clean_then_place': 'clean',
    'pick_heat_then_place': 'heat',
    'pick_cool_then_place': 'cool',
    'look_at_obj': 'examine',
    'pick_two_obj': 'puttwo'
}

def run_trial(
        trial_log_path: str,
        world_log_path: str,
        trial_idx: int,
        env_configs: List[Dict[str, Any]],
        use_memory: bool
    ) -> List[Dict[str, Any]]:
    importlib.reload(alfworld)
    importlib.reload(alfworld.agents.environment)

    with open('base_config.yaml') as reader:
        config = yaml.safe_load(reader)
    split = "eval_out_of_distribution"

    env = getattr(alfworld.agents.environment, config["env"]["type"])(config, train_eval=split)
    env = env.init_env(batch_size=1)

    num_successes: int = 0
    num_additional_successes: int = 0
    num_envs: int = len(env_configs)

    for z, env_config in enumerate(env_configs):
        ob, info = env.reset()
        ob = '\n'.join(ob[0].split('\n\n')[1:])
        name = '/'.join(info['extra.gamefile'][0].split('/')[-3:-1])

        print(f"using {name}")

        if env_config["is_success"]:
            num_successes += 1

            # log to world log
            with open(world_log_path, 'a') as wf:
                wf.write(f'Environment #{z} Trial #{trial_idx}: SUCCESS\n')
            with open(trial_log_path, 'a') as wf:
                wf.write(f'\n#####\n\nEnvironment #{z}: Success\n\n#####\n')
            continue

        for i, (k, v) in enumerate(PREFIXES.items()):
            if name.startswith(k):
                base_prompt = 'Interact with a household to solve a task. Here are two examples.\n' + d[f'react_{v}_1'] + d[f'react_{v}_0']
                final_env_history, is_success = alfworld_run(env, base_prompt, env_config["memory"] if use_memory else [], to_print=True, ob=ob)

                # update env config
                if is_success:
                    status_str: str = f'Environment #{z} Trial #{trial_idx}: SUCCESS'
                    env_configs[z]['is_success'] = True
                    num_successes += 1
                    num_additional_successes += 1
                else:
                    status_str: str = f'Environment #{z} Trial #{trial_idx}: FAIL'

                # log to world log
                with open(world_log_path, 'a') as f:
                    f.write(status_str + '\n')

                # log env results to trial log
                with open(trial_log_path, 'a') as wf:
                    wf.write(f'\n#####\n\nEnvironment #{z}:\n{str(final_env_history)}\n\nSTATUS: {"OK" if is_success else "FAIL"}\n\n#####\n')

    # close environment object
    env.close()

    # log trial results to trial and world logs
    log_str: str = f"""
-----
SUCCESS: {num_successes}
ADDITIONAL SUCCESS: {num_additional_successes}
FAIL: {num_envs - num_successes}
TOTAL: {num_envs}
ACCURACY: {round(num_successes / num_envs, 2)}
-----"""
    with open(trial_log_path, 'a') as wf:
        wf.write(log_str)
    with open(world_log_path, 'a') as wf:
        wf.write(log_str + '\n')

    return env_configs
