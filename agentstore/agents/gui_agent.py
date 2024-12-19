from agentstore.agents.base_agent import BaseAgent
from agentstore.utils import check_os_version
from agentstore.utils import setup_config, setup_pre_run
import json
import logging
import os
import sys
from agentstore.prompts.osworld_pt import prompt
from agentstore.utils import TaskStatusCode, InnerMonologue, ExecutionState, JudgementResult, RepairingResult

from agentstore.utils.osworld_parse import parse_actions_from_string, parse_code_from_string, parse_code_from_som_string

from agentstore.utils.llms import OpenAI, LLAMA
from dotenv import load_dotenv

from agentstore.utils.parse_obs import parse_obs

import contextlib
from desktop_env.desktop_env import DesktopEnv

load_dotenv(override=True)
MODEL_TYPE = os.getenv('MODEL_TYPE')

class GUIAgent(BaseAgent):
    def __init__(self, args, config, env, action_space, observation_type, max_trajectory_length, max_steps=10):
        super().__init__()
        try:
            check_os_version(self.system_version)
        except ValueError as e:
            print(e)

        self.environment = env
        self.task_name = config['instruction']

        domain = config['snapshot']
        example_id = config['id']

        self.action_space = action_space
        self.observation_type = observation_type
        self._get_system_message(self.observation_type, self.action_space)
        self.a11y_tree_max_tokens = 2000
        self.max_trajectory_length = max_trajectory_length
        self.max_steps = max_steps
        self.sleep_after_execution = 0.0
        result_dir = 'D:\jcy\OS-Copilot\\results'
        self.example_result_dir = os.path.join(
            result_dir,
            self.action_space,
            self.observation_type,
            domain,
            example_id
        )

        os.makedirs(self.example_result_dir, exist_ok=True)

        if MODEL_TYPE == "OpenAI":
            self.llm = OpenAI()
        elif MODEL_TYPE == "LLAMA":
            self.llm = LLAMA()

        self.reset()

    def run(self):
        step_idx = 0
        obs, reward, done, info = self.environment.step("")
        self.environment.controller.start_recording()

        while not done and step_idx < self.max_steps:
            obs = parse_obs(obs, self.observation_type)
            response, actions = self.predict(obs)
            for action in actions:
                import datetime
                action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
                obs, reward, done, info = self.environment.step(action, self.sleep_after_execution)
                print("Done: %s", done)
                with open(os.path.join(self.example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"), "wb") as _f:
                    _f.write(obs['screenshot'])

                with open(os.path.join(self.example_result_dir, "traj.jsonl"), "a") as f:
                    f.write(json.dumps({
                        "step_num": step_idx + 1,
                        "action_timestamp": action_timestamp,
                        "action": action,
                        "reward": reward,
                        "done": done,
                        "info": info,
                        "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                    }))
                    f.write("\n")
                if done:
                    print("The episode is done.")
                    break
            step_idx += 1

    def predict(self, obs):
        messages = self._get_message(self.task_name, obs)
        print("Generating content with GPT model:")
        response = self.llm.chat(messages)
        print("RESPONSE: %s", response)

        try:
            actions = self.parse_actions(response)
            self.thoughts.append(response)
        except ValueError as e:
            print("Failed to parse action from response", e)
            actions = None
            self.thoughts.append("")
        return response, actions

    def parse_actions(self, response: str, masks=None):
        if self.observation_type in ["screenshot", "a11y_tree", "screenshot_a11y_tree"]:
            if self.action_space == "computer_13":
                actions = parse_actions_from_string(response)
            elif self.action_space == "pyautogui":
                actions = parse_code_from_string(response)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)
            return actions
        elif self.observation_type in ["som"]:
            if self.action_space == "computer_13":
                raise ValueError("Invalid action space: " + self.action_space)
            elif self.action_space == "pyautogui":
                actions = parse_code_from_som_string(response, masks)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)
            return actions

    def reset(self):
        self.thoughts = []
        self.actions = []
        self.observations = []

    def _get_message(self, task, obs):
        system_message = self.system_message + "\nYou are asked to complete the following task: {}".format(task)

        messages = []
        messages.append({
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": system_message
                },
            ]
        })
        assert len(self.observations) == len(self.actions) and len(self.actions) == len(self.thoughts), "The number of observations and actions should be the same."

        if len(self.observations) > self.max_trajectory_length:
            if self.max_trajectory_length == 0:
                _observations = []
                _actions = []
                _thoughts = []
            else:
                _observations = self.observations[-self.max_trajectory_length:]
                _actions = self.actions[-self.max_trajectory_length:]
                _thoughts = self.thoughts[-self.max_trajectory_length:]
        else:
            _observations = self.observations
            _actions = self.actions
            _thoughts = self.thoughts

        for previous_obs, previous_action, previous_thought in zip(_observations, _actions, _thoughts):
            if self.observation_type == "screenshot_a11y_tree":
                _screenshot = previous_obs["screenshot"]
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(_linearized_accessibility_tree)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type in ["som"]:
                _screenshot = previous_obs["screenshot"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the tagged screenshot as below. What's the next step that you will do to help with the task?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type == "screenshot":
                _screenshot = previous_obs["screenshot"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the screenshot as below. What's the next step that you will do to help with the task?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{_screenshot}",
                                "detail": "high"
                            }
                        }
                    ]
                })
            elif self.observation_type == "a11y_tree":
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(_linearized_accessibility_tree)
                        }
                    ]
                })
            else:
                raise ValueError("Invalid observation_type type: " + self.observation_type)

            messages.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": previous_thought.strip() if len(previous_thought) > 0 else "No valid action"
                    },
                ]
            })

        if self.observation_type in ["screenshot", "screenshot_a11y_tree"]:
            if self.observation_type == "screenshot_a11y_tree":
                self.observations.append({
                    "screenshot": obs["base64_image"],
                    "accessibility_tree": obs["linearized_accessibility_tree"]
                })
            else:
                self.observations.append({
                    "screenshot": obs["base64_image"],
                    "accessibility_tree": None
                })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Given the screenshot as below. What's the next step that you will do to help with the task?"
                        if self.observation_type == "screenshot"
                        else "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(obs["linearized_accessibility_tree"])
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"""data:image/png;base64,{obs["base64_image"]}""",
                            "detail": "high"
                        }
                    }
                ]
            })
        elif self.observation_type == "a11y_tree":
            self.observations.append({
                "screenshot": None,
                "accessibility_tree": obs["linearized_accessibility_tree"]
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(obs["linearized_accessibility_tree"])
                    }
                ]
            })
        elif self.observation_type == "som":
            self.observations.append({
                "screenshot": obs["base64_image"],
                "accessibility_tree": obs["linearized_accessibility_tree"]
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Given the tagged screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(obs["linearized_accessibility_tree"])
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"""data:image/png;base64,{obs["base64_image"]}""",
                            "detail": "high"
                        }
                    }
                ]
            })
        else:
            raise ValueError("Invalid observation_type type: " + self.observation_type)

        return messages

    def _get_system_message(self, observation_type, action_space):
        raise NotImplementedError

class ChromeAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_CHROME"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class GimpAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_GIMP"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class VlcAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_VLC"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class ThunderbirdAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_THU"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class VscodeAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_VSCODE"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class OsGUIAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_OS"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class CalcAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_CACL"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class ImpressAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_IMPRESS"]
            else:
                raise ValueError("Invalid action space: " + action_space)

class WriterAgent(GUIAgent):
    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE_WORD"]
            else:
                raise ValueError("Invalid action space: " + action_space)

def replace_path(obj, old_path, new_path):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_path(value, old_path, new_path)
    elif isinstance(obj, list):
        obj = [replace_path(item, old_path, new_path) for item in obj]
    elif isinstance(obj, str):
        obj = obj.replace(old_path, new_path)
    return obj

if __name__ == '__main__':
    environment = DesktopEnv(
        path_to_vm=r"D:/jcy/OSWorld_new/vmware_vm_data/Ubuntu0/Ubuntu0.vmx",
        action_space="pyautogui",
        require_a11y_tree=True,
    )

    test_all_meta_path = "D:\\jcy\\OSWorld_new\\evaluation_examples/test_all.json"
    example_path = "D:\\jcy\\OSWorld_new\\evaluation_examples"

    with open(test_all_meta_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)

    domain = 'libreoffice_writer'
    tasks = test_all_meta[domain]

    for example_id in tasks[0:]:
        example_id = "6ada715d-3aae-4a32-a6a7-429b2e43fb93"
        config_file = os.path.join(example_path, f"examples/{domain}/{example_id}.json")
        with open(config_file, "r", encoding="utf-8") as f:
            example = json.load(f)
        task_name = example['instruction']
        
        print('task_name:', task_name)
        example = replace_path(example, 'evaluation_examples/settings', 'D:\\jcy\\OSWorld_new\\evaluation_examples\\settings')
        
        previous_obs = environment.reset(task_config=example)
        args = setup_config()
        action_space = 'pyautogui'
        observation_type = 'screenshot_a11y_tree'
        max_trajectory_length = 3
        gui_agent = ChromeAgent(args, example, environment, action_space, observation_type, max_trajectory_length, max_steps=10)
        gui_agent.run()

        input()
        print("evaluate.......")
        print(environment.evaluate())
        break
