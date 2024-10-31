from oscopilot.utils import setup_config, setup_pre_run
from oscopilot.modules.base_module import BaseModule
import re
import os
import json
import base64
import time
from rich.console import Console
from rich.markdown import Markdown

from desktop_env.desktop_env import DesktopEnv

from oscopilot.prompts.osworld_pt import prompt_image

console = Console()

def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')

def rich_print(markdown_text):
    md = Markdown(markdown_text)
    console.print(md)


def send_chat_prompts(message, llm):
    return llm.chat(message)

    
def extract_code(input_string):
    pattern = r"```(\w+)?\s*(.*?)```"  # 匹配代码块，语言名称是可选项
    matches = re.findall(pattern, input_string, re.DOTALL)

    if matches:
        language, code = matches[0]

        # 如果没有语言信息，尝试从代码内容中检测
        if not language:
            if re.search("python", code.lower()) or re.search(r"import\s+\w+", code):
                language = "python"
            elif re.search("bash", code.lower()) or re.search(r"echo", code):
                language = "bash"

        if language == 'bash':
            code = code.strip()
            code = code.replace('"', '\\"')
            code = code.replace('\n', ' && ')
            code = "pyautogui.typewrite(\"{0}\", interval=0.05)\npyautogui.press('enter')\ntime.sleep(2)".format(code)
            if re.search("sudo", code.lower()):
                code += "\npyautogui.typewrite('password', interval=0.05)\npyautogui.press('enter')\ntime.sleep(1)"
        elif language == 'python':

            # save code
            with open('tmp.py', 'w') as f:
                f.write(code)

            code = "pyautogui.typewrite(\"python main.py\", interval=0.05)\npyautogui.press('enter')\ntime.sleep(2)"
            
        else:
            print(language)
            raise language

        return code, language
    else:
        return None, None

class ImageAgent(BaseModule):

    def __init__(self, args, config, env):
        super().__init__()
        self.args = args

        self.environment = env
        

        self.task_name = config['instruction']

        try:
            path = config['evaluator']['result']['path']
            self.task_name = self.task_name + " export path is " + path
            print(self.task_name)
        except:
            pass

        self.reply = None

        domain = config['snapshot']
        example_id = config['id']

        result_dir = 'D:\jcy\OS-Copilot\\results'
        self.example_result_dir = os.path.join(
                result_dir,
                domain,
                example_id
            )

        os.makedirs(self.example_result_dir, exist_ok=True)


    
    def execute_tool(self, code, lang):
        if lang == 'python':
            file = [{
                "local_path": 'tmp.py',
                "path": '/home/user/main.py'
              }]
            self.environment.setup_controller._upload_file_setup(file)
        obs, reward, done, info = self.environment.step(code)  # node_type
        
        reply = self.environment.controller.get_terminal_output()
        # update reply
        if self.reply and reply:
            message_terminal = reply.replace(self.reply, "")
        else:
            message_terminal = reply
        self.reply = reply

        base64_image = encode_image(obs['screenshot'])
        print("message_terminal", message_terminal)
        if 'gpt' in self.llm.model_name:
            message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "After executing the command, the terminal output is {0}. the screenshot as below.".format(message_terminal)
                        }
                        # {
                        #     "type": "image_url",
                        #     "image_url": {
                        #         "url": f"data:image/png;base64,{base64_image}",
                        #         "detail": "high"
                        #     }
                        # }
                    ]
            }
        else:
            message = {
                    "role": "user",
                    "content": "After executing the command, the terminal output is {0}. the screenshot as below.".format(message_terminal)
            }
        return message
# When a user refers to a file opened， you can use the provided screenshot to find the filepath.
    def run(self):

        while not self.environment.controller.get_terminal_output():
            self.environment.step("pyautogui.click()")
            self.environment.step("pyautogui.hotkey('ctrl', 'alt', 't')")
            print(self.environment.controller.get_terminal_output())

        light_planner_sys_prompt = prompt_image['SYS_PROMPT_IN_CLI_IMAGE']
        
        
         #  Try to use `print` or `echo` to output information needed for the subsequent tasks, or the next step might not get the required information.
        light_planner_user_prompt = '''
        User's information are as follows:
        System Version: Ubuntu
        Task Name: {task_name}
        '''.format(task_name=self.task_name)
        
        message = [
            {"role": "system", "content": light_planner_sys_prompt},
            {"role": "user", "content": light_planner_user_prompt},
        ]
        self.example_result_dir
        step_idx = 0
        while step_idx < 12:
            print("send_chat_prompts...")
            response = send_chat_prompts(message, self.llm)
            print(response)
            message.append({"role": "assistant", "content": response})
            code, lang = extract_code(response)

            import datetime
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")

            with open(os.path.join(self.example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "response": response,
                    "code": code,
                    "lang": lang
                }))

            if code:
                result = self.execute_tool(code, lang)
            else:
                result = ''

            if result != '':
                message.append(result)
            else:
                message.append({"role": "user", "content": "Please continue. If all tasks have been completed, reply with 'TASK DONE'. If you believe subsequent tasks cannot continue, or you find that the task is problematic, or beyond your ability, reply with 'TASK FAIL'. Including the reasons why the tasks cannot proceed, and provide the user with some possible solutions."})
            
            if 'TASK DONE' in response or 'TASK FAIL' in response:
                if 'TASK FAIL' in response:
                    self.environment.step("FAIL")
                break
            else:
                step_idx += 1   

        return response


def replace_path(obj,old_path,new_path):
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = replace_path(value,old_path,new_path)
    elif isinstance(obj, list):
        obj = [replace_path(item,old_path,new_path) for item in obj]
    elif isinstance(obj, str):
        obj = obj.replace(old_path, new_path)
    return obj


if __name__ == '__main__':


    environment = DesktopEnv(
            path_to_vm=r"D:/jcy/OSWorld_new/vmware_vm_data/Ubuntu0/Ubuntu0.vmx",
            action_space="pyautogui",
            require_a11y_tree=False,
        )

    test_all_meta_path = "D:\\jcy\\OSWorld_new\\evaluation_examples/test_all.json"
    example_path = "D:\\jcy\\OSWorld_new\\evaluation_examples"

    with open(test_all_meta_path, "r", encoding="utf-8") as f:
        test_all_meta = json.load(f)

    domain = 'gimp'
    tasks = test_all_meta[domain]

    # run_list_file_path = r'D:\jcy\OS-Copilot\run_list.txt'
    # run_list = []

    # with open(run_list_file_path, 'r') as file:
    #     for line in file:
    #         run_list.append(line.strip())

    for example_id in tasks[25:]:
        print(example_id)
        config_file = os.path.join(example_path, f"examples/{domain}/{example_id}.json")
        with open(config_file, "r", encoding="utf-8") as f:
            example = json.load(f)
        task_name = example['instruction']
        
        print('task_name:', task_name)
        example = replace_path(example, 'evaluation_examples/settings', 'D:\\jcy\\OSWorld_new\\evaluation_examples\\settings')
        
        previous_obs = environment.reset(task_config=example)
        args = setup_config()
        
        excel_agent = ImageAgent(args, example, environment)
        excel_agent.run()
        input()
        
        # 判定内容
        print("evaluate.......")
        print(environment.evaluate())   
        break    