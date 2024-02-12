from setuptools import setup

setup(
    name="iraircon",
    version="0.2.9",
    description="A Python package to control the IR Air Con",
    url="https://github.com/shuds13/pyexample",
    author="Nathan Clark",
    author_email="nclarknz@gmail.com",
    license="BSD 2-clause",
    packages=["iraircon"],
    install_requires=[
        "tinytuya>=0.1",
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
    ],
)
