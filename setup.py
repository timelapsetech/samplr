from setuptools import setup, find_packages

setup(
    name="samplr",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Pillow>=9.0.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ],
        "gui": [
            "PyQt6>=6.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "samplr=samplr.cli:main",
        ],
    },
    author="Dave Klee",
    author_email="dave@timelapsetech.com",
    description="A tool for sampling images based on various criteria",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/timelapsetech/samplr",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
) 