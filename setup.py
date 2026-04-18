#!/usr/bin/env python3
"""Eski pip/setuptools sürümleri için; asıl yapılandırma pyproject.toml."""

from setuptools import setup

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

setup(
    name="mechkeys-macos",
    version="1.0.0",
    description="macOS menü çubuğunda Cherry MX Blue tarzı tuş sesleri",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="MIT",
    python_requires=">=3.9",
    packages=["mechkeys"],
    install_requires=[
        "rumps>=0.4.0",
        "pynput>=1.7.6",
        "pygame>=2.5.0",
    ],
    entry_points={
        "console_scripts": [
            "mechkeys=mechkeys.app:main",
            "mechkeys-download-sounds=mechkeys.download_sounds:main",
        ],
    },
)
