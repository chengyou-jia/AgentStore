<h1 align="center">
AgentStore: Scalable Integration of Heterogeneous Agents As Specialized Generalist Computer Assistant
</h1>

<p align="center">
  <a href=""><b>[🌐 Website]</b></a> •
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

## ⚡️ Quickstart

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

4. **Now you are ready to have fun:**
   ```
   python quick_start.py
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
