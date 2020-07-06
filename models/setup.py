from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="models",
    version="0.1.0",
    description="Database models",
    packages=find_packages(),
    zip_safe=False,
    install_requires=requirements,
)
