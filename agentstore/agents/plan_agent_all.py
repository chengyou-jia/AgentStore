from agentstore.utils import setup_config, setup_pre_run
from agentstore.modules.base_module import BaseModule
import re
import os
import json
import base64
import time
from rich.console import Console
from rich.markdown import Markdown
import contextlib

from desktop_env.envs.desktop_env import DesktopEnv

console = Console()

def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')

def rich_print(markdown_text):
    md = Markdown(markdown_text)
    console.print(md)

def extract_code(input_string):
    pattern = r"```(\w+)?\s*(.*?)```"  # 匹配代码块，语言名称是可选项
    matches = re.findall(pattern, input_string, re.DOTALL)
    info = matches[0][1]
    return info


def send_chat_prompts(message, llm):
    return llm.chat(message)

class PlanAgent(BaseModule):
    def __init__(self, args, task_name, agent_info_list):
        super().__init__()
        self.args = args
        self.task_name = task_name

        agents_name = [agent_info["name"] for agent_info in agent_info_list]
        agents_name = ", ".join(agents_name[:-1]) + ", and " + agents_name[-1]
        agent_description = f''
        for agent_info in agent_info_list:
            name = agent_info["name"]
            can = agent_info['can do']
            cannot = agent_info['can\'t do']
            agent_description += f"### {name}:\n"
            agent_description += f"**Can do:** {can}\n"
            agent_description += f"**Can't do:** {cannot}\n"
        print(agent_description)
        

        self.light_planner_sys_prompt = '''You are the MasterAgent, a strategic coordinator responsible for delegating tasks among a team of specialized agents to complete OS-related tasks efficiently. 
        You will receive a high-level task along with a current system screenshot and determine the best approach for completing the task.
        Your team consists of {0}, each with unique capabilities and cann't do:
        {1}
    Your task is to:

    1. Analyze the given high-level task.
    2. Review the provided system screenshot to understand the current state and context.
    3. Determine which agent ({2}) is best suited to handle the task.
    4. Determine whether the task requires cooperation between different agents, and if so, break down the task into steps that specify which agent should perform each part.
    4. Provide a detailed description of the task, including any relevant information such as file paths, URLs, and steps to complete the task.
    You will only provide the next agent, detailing which agent should perform the task, the task description, and whether any information is needed.
    Follow the next format for Next:
    ```markdown
    Agent: CLIAgent
    Task Description: Check if Python is installed by running the command python --version.
```
'''.format(agents_name, agent_description,agents_name)

        print(self.light_planner_sys_prompt)

        self.light_planner_user_prompt = '''
        OS Task: {task}. Current System Screenshot  as below.
        '''.format(task=self.task_name)

        self.message_pool = None

    def run(self,obs):
        screenshot = obs['screenshot']
        base64_image = encode_image(screenshot)

        if self.message_pool == None:
            message = [
                {"role": "system", "content": self.light_planner_sys_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.light_planner_user_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            self.message_pool = message
        else:
            pass
            # self.message_pool.append(new_message)
            # message = self.message_pool

        print("send_chat_prompts...")
        response = send_chat_prompts(message, self.llm)
        rich_print(response)

        self.message_pool.append({"role": "assistant", "content": response})
        info = extract_code(response)
        print(info)
        return info

def replace_path(obj,old_path,new_path):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_path(value,old_path,new_path)
    elif isinstance(obj, list):
        obj = [replace_path(item,old_path,new_path) for item in obj]
    elif isinstance(obj, str):
        obj = obj.replace(old_path, new_path)
    return obj


from cli_agent import CLIAgent
from gui_agent import GUIAgent
from word_agent import WordAgent
from pptx_agent import PptxAgent
from excel_agent import ExcelAgent
from image_agent import ImageAgent

agent_info_list = [CLIAgent.info, GUIAgent.info, WordAgent.info, PptxAgent.info, ExcelAgent.info]


if __name__ == '__main__':


    environment = DesktopEnv(
            path_to_vm=r"D:/jcy/OSWorld/vm_data/Ubuntu0/Ubuntu0/Ubuntu0.vmx",
            action_space="pyautogui",
            require_a11y_tree=True,
        )


    test_all_meta_path = "D:\\jcy\\OSWorld\\evaluation_examples/test_all.json"
    example_path = "D:\\jcy\\OSWorld\\evaluation_examples"

    with open(test_all_meta_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)

    domain = 'gimp'
    tasks = test_all_meta[domain]

    # run_list_file_path = r'D:\jcy\OS-Copilot\run_list.txt'
    # run_list = []

    # with open(run_list_file_path, 'r') as file:
    #     for line in file:
    #         run_list.append(line.strip())

    for example_id in tasks:
        try:
            print(example_id)
            config_file = os.path.join(example_path, f"examples/{domain}/{example_id}.json")
            with open(config_file, "r", encoding="utf-8") as f:
                example = json.load(f)
            task_name = example['instruction']
            
            log_file_path = os.path.join("cache",example_id, f"{example_id}.log")
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            
            with open(log_file_path, 'w', encoding="utf-8") as log_file:
                with contextlib.redirect_stdout(log_file):
                    print('task_name:', task_name)
                    example = replace_path(example, 'evaluation_examples/settings', 'D:\\jcy\\OSWorld\\evaluation_examples\\settings')
                    
                    previous_obs = environment.reset(task_config=example)
                    args = setup_config()
                    
                    # plan_agent = PlanAgent(args, task_name, agent_info_list)
                    # info = plan_agent.run(previous_obs)

                    info = 'ImageAgent'
                    
                    if 'CLIAgent' in info:
                        cli_agent = CLIAgent(args, task_name, environment)
                        cli_agent.run(info)
                    
                    elif 'GUIAgent' in info:
                        action_space = 'pyautogui'
                        observation_type = 'screenshot_a11y_tree'
                        max_trajectory_length = 3
                        gui_agent = GUIAgent(args, example, environment, action_space, observation_type, max_trajectory_length)
                        gui_agent.run()
                    
                    elif 'WordAgent' in info:
                        word_agent = WordAgent(args, task_name, environment)
                        word_agent.run()
                    
                    elif 'PptxAgent' in info:
                        pptx_agent = PptxAgent(args, task_name, environment)
                        pptx_agent.run()
                    
                    elif 'ExcelAgent' in info:
                        excel_agent = ExcelAgent(args, task_name, environment)
                        excel_agent.run()
                    elif 'ImageAgent' in info:
                        excel_agent = ImageAgent(args, task_name, environment)
                        excel_agent.run()
                    else:
                        # replan 
                        # to be update
                        pass
                    
                    # 判定内容
                    print("evaluate.......")
                    print(environment.evaluate())
        except Exception as e:
            error_log_path = os.path.join("cache",example_id, f"{example_id}_error.log")
            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
            with open(error_log_path, 'w', encoding="utf-8") as error_log:
                error_log.write(str(e))
            print(e)



