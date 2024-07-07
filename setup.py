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

"""

setup(
    name='tiny-dlna',
    version='0.3.0',
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
