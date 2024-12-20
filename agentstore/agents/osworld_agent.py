from agentstore.agents.base_agent import BaseAgent
from agentstore.utils import check_os_version
import json
import logging
import os
import sys
from agentstore.prompts.osworld_pt import prompt
from agentstore.utils import TaskStatusCode, InnerMonologue, ExecutionState, JudgementResult, RepairingResult

from agentstore.utils.osworld_parse import parse_actions_from_string,parse_code_from_string,parse_code_from_som_string

from agentstore.utils.llms import OpenAI,LLAMA
from dotenv import load_dotenv

load_dotenv(override=True)
MODEL_TYPE = os.getenv('MODEL_TYPE')

class OSworldAgent(BaseAgent):
    """
    A FridayAgent orchestrates the execution of tasks by integrating planning, retrieving, and executing strategies.
    
    This agent is designed to process tasks, manage errors, and refine strategies as necessary to ensure successful task completion. It supports dynamic task planning, information retrieval, execution strategy application, and employs a mechanism for self-refinement in case of execution failures.
    """

    def __init__(self, action_space,observation_type,max_trajectory_length):
        """
        Initializes the FridayAgent with specified planning, retrieving, and executing strategies, alongside configuration settings.

        Args:
            planner (callable): A strategy for planning the execution of tasks.
            retriever (callable): A strategy for retrieving necessary information or tools related to the tasks.
            executor (callable): A strategy for executing planned tasks.
            Tool_Manager (callable): A tool manager for handling tool-related operations.
            config (object): Configuration settings for the agent.

        Raises:
            ValueError: If the OS version check fails.
        """
        super().__init__()
        try:
            check_os_version(self.system_version)
        except ValueError as e:
            print(e)        

        self.action_space= action_space # "pyautogui" # computer_13
        self.observation_type=observation_type # observation_type can be in ["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"]
        self._get_system_message(self.observation_type, self.action_space)
        self.a11y_tree_max_tokens = 2000
        self.max_trajectory_length = max_trajectory_length
        self.max_steps = 10

        if MODEL_TYPE == "OpenAI":
            self.llm = OpenAI()
        elif MODEL_TYPE == "LLAMA":
            self.llm = LLAMA()

    def run(self, task, obs):
        """
        Executes the given task by planning, executing, and refining as needed until the task is completed or fails.

        Args:
            query (object): The high-level task to be executed.

        No explicit return value, but the method controls the flow of task execution and may exit the process in case of irreparable failures.
        """

        messages = self._get_message(task,obs)
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
        return response,actions 


    def parse_actions(self, response: str, masks=None):

        if self.observation_type in ["screenshot", "a11y_tree", "screenshot_a11y_tree"]:
            # parse from the response
            if self.action_space == "computer_13":
                actions = parse_actions_from_string(response)
            elif self.action_space == "pyautogui":
                actions = parse_code_from_string(response)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)

            return actions
        elif self.observation_type in ["som"]:
            # parse from the response
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

        assert len(self.observations) == len(self.actions) and len(self.actions) == len(self.thoughts) \
            , "The number of observations and actions should be the same."

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
            # {{{1
            if self.observation_type == "screenshot_a11y_tree":
                _screenshot = previous_obs["screenshot"]
                _linearized_accessibility_tree = previous_obs["accessibility_tree"]

                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                                _linearized_accessibility_tree)
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
                            "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                                _linearized_accessibility_tree)
                        }
                    ]
                })
            else:
                raise ValueError("Invalid observation_type type: " + self.observation_type)  # 1}}}

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
                    else "Given the screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                        obs["linearized_accessibility_tree"])
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
                        "text": "Given the info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            obs["linearized_accessibility_tree"])
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
                        "text": "Given the tagged screenshot and info from accessibility tree as below:\n{}\nWhat's the next step that you will do to help with the task?".format(
                            obs["linearized_accessibility_tree"])
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
            raise ValueError("Invalid observation_type type: " + self.observation_type)  # 1}}}
        
        return messages


    def _get_system_message(self, observation_type, action_space):
        if observation_type == "screenshot":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_SCREENSHOT_OUT_CODE"]
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_A11Y_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_A11Y_OUT_CODE"]
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_ACTION"]
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_BOTH_OUT_CODE"]
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "som":
            if action_space == "computer_13":
                raise ValueError("Invalid action space: " + action_space)
            elif action_space == "pyautogui":
                self.system_message = prompt["SYS_PROMPT_IN_SOM_OUT_TAG"]
            else:
                raise ValueError("Invalid action space: " + action_space)
        else:
            raise ValueError("Invalid experiment type: " + observation_type)

