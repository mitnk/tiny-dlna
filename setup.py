import os.path
from setuptools import setup

DESC = """
Home Page: https://github.com/mitnk/tiny-dlna

A tiny DLNA sender & receiver.

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
can also use `tiny-cli` to play local videos (like in your RaspberryPi) on it.

Note: mpv needs to be installed on your system.

::

    $ tiny-cli list

List available DLNA devices.

::

    $ tiny-cli play ~/Movies/foo/bar.mp4 -q 'TV'

Play a video on the DLNA device having "TV" in its name.
"""
version_file = os.path.join(os.path.dirname(__file__), 'tiny_dlna', 'version')
with open(version_file, 'r') as f:
    version = f.read().strip()


setup(
    name='tiny-dlna',
    version=version,
    description='a tiny DLNA sender & receiver',
    long_description=DESC,
    url='https://github.com/mitnk/tiny-dlna',
    author='mitnk',
    license='MIT',
    keywords='dlna',
    packages=['tiny_dlna'],
    package_data={'': ['version']},
    package_dir={'tiny_dlna': 'tiny_dlna'},
    entry_points={
        'console_scripts': [
            'tiny-render=tiny_dlna.tiny_render:main',
            'tiny-cli=tiny_dlna.tiny_cli:main',
        ],
    },
    install_requires=[
        'flask>=3.0.0',
        'psutil>=6.0.0',
    ],
)
