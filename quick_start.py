import argparse
import datetime
import json
import logging
import os
import sys

from tqdm import tqdm

from desktop_env.desktop_env import DesktopEnv

# agents
from agentstore import ChromeGUIAgent
from agentstore import WordAgent,PptxAgent,ExcelAgent
from agentstore import ImageAgent,OSAgent,VScodeAgent
# to be updated more



agent_dict = {
    "ChromeAgent": ChromeGUIAgent,

    "SlideAgent":PptxAgent,
    "SheetAgent": ExcelAgent,
    "WordAgent": WordAgent,

    "ImageAgent": ImageAgent,
    "VSAgent": VScodeAgent,
    "OSAgent": OSAgent,
    "OSAgent": OSAgent,
    "OSAgent": OSAgent,
    # Add more agents here
}

def replace_path(obj,old_path,new_path):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_path(value,old_path,new_path)
    elif isinstance(obj, list):
        obj = [replace_path(item,old_path,new_path) for item in obj]
    elif isinstance(obj, str):
        obj = obj.replace(old_path, new_path)
    return obj

def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run end-to-end evaluation on the benchmark"
    )

    # AgentStore config
    parser.add_argument(
        "--agent_type",
        choices=["gui", "cli"],
        default="gui",
    )
    parser.add_argument("--agent_name", type=str, default='ChromeAgent')

    # OSworld path and task config
    parser.add_argument("--osworld_path", type=str, default='./OSworld/')
    parser.add_argument("--domain", type=str, default='chrome')
    parser.add_argument("--example_id", type=str, default='bb5e4c0d-f964-439c-97b6-bdb9747de3f4')
    

    # OSworld environment config
    parser.add_argument("--path_to_vm", type=str, default=None)
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless machine"
    )
    parser.add_argument(
        "--action_space", type=str, default="pyautogui", help="Action type"
    )
    parser.add_argument(
        "--observation_type",
        choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"],
        default="screenshot_a11y_tree",
        help="Observation type",
    )
    parser.add_argument("--screen_width", type=int, default=1920)
    parser.add_argument("--screen_height", type=int, default=1080)
    parser.add_argument("--sleep_after_execution", type=float, default=0.0)
    parser.add_argument("--max_steps", type=int, default=15)

    # agent config
    parser.add_argument("--max_trajectory_length", type=int, default=3)
    parser.add_argument(
        "--test_config_base_dir", type=str, default="evaluation_examples"
    )

    # lm config
    parser.add_argument("--model", type=str, default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top_p", type=float, default=0.9)
    parser.add_argument("--max_tokens", type=int, default=1500)
    parser.add_argument("--stop_token", type=str, default=None)

    # logging related
    parser.add_argument("--result_dir", type=str, default="./results")
    args = parser.parse_args()

    return args

def initialize_agent(agent_name, *args, **kwargs):
    if agent_name not in agent_dict:
        raise ValueError(f"Agent '{agent_name}' is not recognized. Available agents: {list(agent_dict.keys())}")
    AgentClass = agent_dict[agent_name]
    return AgentClass(*args, **kwargs)


def main():
    args = config()
    environment = DesktopEnv(
            path_to_vm=args.path_to_vm,
            action_space=args.action_space,
            require_a11y_tree=True,
        )

    # test_all_meta_path = "D:\\jcy\\OSWorld_new\\evaluation_examples/test_all.json"
    # example_path = "D:\\jcy\\OSWorld\\evaluation_examples"

    # with open(test_all_meta_path, "r", encoding="utf-8") as f:
    #     test_all_meta = json.load(f)

    # run_list_file_path = r'D:\jcy\OS-Copilot\run_list.txt'
    # run_list = []

    # with open(run_list_file_path, 'r') as file:
    #     for line in file:
    #         run_list.append(line.strip())

    # change path and tasks or run all tasks using loop
    osworld_path = args.osworld_path
    domain = args.domain
    example_id = args.example_id
    config_file = os.path.join(osworld_path, f"evaluation_examples/examples/{domain}/{example_id}.json")
    with open(config_file, "r", encoding="utf-8") as f:
        example = json.load(f)
    task_name = example['instruction']
    
    print('task_name:', task_name)
    setting_path = os.path.join(osworld_path, f"evaluation_examples/settings")
    example = replace_path(example, 'evaluation_examples/settings', setting_path)
    
    previous_obs = environment.reset(task_config=example)

    action_space = args.action_space 
    observation_type = args.observation_type
    max_trajectory_length = args.max_trajectory_length
    max_steps = args.max_steps

    if args.agent_type == 'gui':
        agent = initialize_agent(
        args.agent_name,
        args,
        example,
        environment,
        action_space,
        observation_type,
        max_trajectory_length,
        max_steps=max_steps
        )
    elif args.agent_type == 'cli':
        agent = initialize_agent(args.agent_name, args, example, environment,obs=previous_obs)
    else:
        raise ValueError(f"Agent Type '{args.agent_type}' is not recognized.")
    
    agent.run()
    print("evaluate.......")
    print(environment.evaluate())

if __name__ == '__main__':
    main()
