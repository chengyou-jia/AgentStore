from setuptools import setup, find_packages


with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="agentstore",
    version="0.1.0",
    author="Chengyou Jia, Minnan Luo, Zhuohang Dang, Qiushi Sun, Fangzhi Xu, Junlin Hu, Tianbao Xie, Zhiyong Wu",
    author_email="cp3jia@stu.xjtu.edu.cn",
    description="A flexible and scalable platform for dynamically integrating various heterogeneous agents to independently or collaboratively automate OS tasks. ",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chengyou-jia/AgentStore",
    license="MIT",

    packages=find_packages(exclude=("docs", "temp", "pic", "log")),

    install_requires=requirements,

    entry_points={
        "console_scripts": [
            "friday=quick_start:main",
        ],
    },

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="AI, LLMs, Large Language Models, Agent, OS, Operating System",

    python_requires='>=3.10',
)
