from setuptools import setup

DESC = """
Home Page: https://github.com/mitnk/tiny-dlna

A tiny DLNA receiver.

Install
-------

::

    $ pip install tiny-dlna

Usages
------

::

    $ tiny-render

This will activate a DLNA receiver named "Tiny Render", which can stream videos
from apps like 虎牙直播, Bilibili, and other video platforms. Additionally, you
can also use `nano-dlna` to play local videos (like in your RaspberryPi) on it.

Note: mpv needs to be installed on your system.
"""

setup(
    name='tiny-dlna',
    version='0.4.1',
    description='a tiny DLNA receiver',
    long_description=DESC,
    url='https://github.com/mitnk/tiny-dlna',
    author='mitnk',
    license='MIT',
    keywords='dlna',
    py_modules=["tiny_render", "ssdp"],
    entry_points={
        'console_scripts': [
            'tiny-render=tiny_render:main',
        ],
    },
    install_requires=[
        'flask>=3.0.0',
    ],
)
