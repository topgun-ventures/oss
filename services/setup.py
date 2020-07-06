from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="services",
    version="0.1.0",
    description="Goose Services",
    packages=find_packages(),
    zip_safe=False,
    install_requires=requirements,
)
