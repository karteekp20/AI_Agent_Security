"""
Setup script for Sentinel Agentic Framework
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

setup(
    name="sentinel-agentic-framework",
    version="0.1.0",
    author="Sentinel Security Team",
    author_email="security@sentinel.ai",
    description="Zero-Trust AI Security Control Plane for LLM Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/sentinel-agentic-framework",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "pydantic>=2.0.0",
        "langgraph>=0.0.20",
        "langchain>=0.1.0",
        "cryptography>=41.0.0",
        "python-jose>=3.3.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "nlp": [
            "spacy>=3.7.0",
            "transformers>=4.35.0",
            "sentence-transformers>=2.2.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
        ],
        "all": [
            "spacy>=3.7.0",
            "transformers>=4.35.0",
            "sentence-transformers>=2.2.0",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sentinel=sentinel.cli:main",  # Future CLI tool
        ],
    },
)
