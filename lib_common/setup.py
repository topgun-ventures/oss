from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

requirements.append(
    "muttlib @ git+https://gitlab.com/mutt_data/muttlib.git#egg=muttlib[postgres]"
)


setup(
    name="lib_common",
    version="0.1.0",
    description="Shared resources",
    packages=find_packages(),
    zip_safe=False,
    install_requires=requirements,
)
