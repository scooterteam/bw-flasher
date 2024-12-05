import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()
ABOUT = {}
with open((HERE / "bwflasher" / "version.py")) as f:
    exec(f.read(), ABOUT)

setup(
    name="bwflasher",
    version=ABOUT['__version__'],
    description="Flashing Brightway controllers using the UART.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="ScooterTeam",
    url="https://github.com/scooterteam/bw-flasher",
    python_requires=">=3.10, <4",
    license="AGPL-3.0",
    packages=["bwflasher"],
    keywords=["Xiaomi", "Brightway", "ScooterTeam", "Scooter", "BWFlasher"],
    entry_points={"console_scripts": ["bwflasher=bwflasher.__main__:main"]}
)
