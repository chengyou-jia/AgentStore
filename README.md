<h1 align="center">
AgentStore: Scalable Integration of Heterogeneous Agents As Specialized Generalist Computer Assistant
</h1>

<p align="center">
  <a href="https://chengyou-jia.github.io/AgentStore-Home/"><b>[🌐 Website]</b></a> •
  <a href="https://arxiv.org/abs/2410.18603"><b>[📜 Paper]</b></a> •
  <a href="#"><b>[🤗 HF Models]</b></a> •  
</p>

<p align="center">
Repo for "<a href="https://arxiv.org/abs/2410.18603" target="_blank">AgentStore: Scalable Integration of Heterogeneous Agents As Specialized Generalist Computer Assistant</a>"
</p>


## 🔥 News

- _2024.10_: 🎉 We release the initial code of AgentStore; due to the CVPR deadline, more refined code will be rapidly organized and released shortly after.

## What is AgentStore

AgentStore is a flexible and scalable platform for dynamically integrating various heterogeneous agents to independently or collaboratively automate OS tasks. It allows users to quickly integrate their own specialized agents into the platform, similar to the functionality of the App store. This scalable integration allows the framework to dynamically adapt itself to the evolving OS, providing the multi-dimensional capabilities needed for open-ended tasks.

## 💾 Installation

###  Preparing the OSworld Environment
Agents in AgentStore operate within the OSworld environment; thus, a complete setup of the OSworld is required. For detailed setup instructions, please refer to the [OSworld](#https://github.com/xlang-ai/OSWorld) documentation. We provide a quick step-by-step installation guide for setting up the necessary environment.

1. First, clone this repository and `cd` into it. Then, install the dependencies listed in `requirements.txt`. 
```bash
# Clone the OSWorld repository
git clone https://github.com/xlang-ai/OSWorld

# Change directory into the cloned repository
cd OSWorld

# Optional: Create a Conda environment for OSWorld
# conda create -n osworld python=3.9
# conda activate osworld

# Install required dependencies
pip install -r requirements.txt
```

2. Install [VMware Workstation Pro](https://www.vmware.com/products/workstation-pro/workstation-pro-evaluation.html) (for systems with Apple Chips, you should install [VMware Fusion](https://support.broadcom.com/group/ecx/productdownloads?subfamily=VMware+Fusion)) and configure the `vmrun` command.  The installation process can refer to [How to install VMware Worksation Pro](desktop_env/providers/vmware/INSTALL_VMWARE.md). Verify the successful installation by running the following:
```bash
vmrun -T ws list
```
If the installation along with the environment variable set is successful, you will see the message showing the current running virtual machines.

All set! The setup script will automatically download the necessary virtual machines and configure the environment for you.

### Install AgentStore


1. **Clone the GitHub Repository:**

   ```
   git clone git@github.com:chengyou-jia/AgentStore.git
   ```

2. **Set Up Python Environment and Install Dependencies:**

   ```
   conda create -n agentstore_env python=3.10 -y
   conda activate agentstore_env

   cd AgentStore
   pip install -e .
   ```

3. **Set OpenAI API Key:** Configure your OpenAI API key in [.env](.env).

   ```
   cp .env_template .env
   ```

### ⚡️ Quickstart 

1. **Run agents in AgentStore:**
   
   ```
   python quick_start.py --agent_name ""
   ```

### Others
We are working on supporting more 👷. Please hold tight!

## Citation
If you find it helpful, please kindly cite the paper.
```
@article{jia2024agentstore,
      title={AgentStore: Scalable Integration of Heterogeneous Agents As Specialized Generalist Computer Assistant},
      author={Jia, Chengyou and Luo, Minnan and Dang, Zhuohang and Sun, Qiushi and Xu, Fangzhi and Hu, Junlin and Xie, Tianbao and Wu, Zhiyong},
      journal={arXiv preprint arXiv:2410.18603},
      year={2024}
    }
```

## 📬 Contact

If you have any inquiries, suggestions, or wish to contact us for any reason, we warmly invite you to email us at cp3jia@stu.xjtu.edu.cn.
