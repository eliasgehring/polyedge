from setuptools import setup, find_packages

setup(
    name="polyedge",
    version="0.1.0",
    description="Prediction-market backtesting engine with explicit probability semantics and settlement-aware accounting.",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "polyedge=polyedge.cli:main",
        ],
    },
)
