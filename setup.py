
import os
from distutils.core import setup

setup(
    name="chatgpt-telegram",
    version="0.1.2",
    description="ChatGPT Bot For telegram",
    author='learnforpractice',
    license="Apache 2.0",
    url="https://github.com/learnforpractice/chatgpt-telegram",
    packages=['chatgpt_telegram'],
    package_dir={'chatgpt_telegram': 'src'},
    package_data={},
    setup_requires=['wheel']
)
