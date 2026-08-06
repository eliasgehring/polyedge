from setuptools import (
    find_packages,
    setup,
)


setup(
    name="polyedge",
    version="0.1.0",
    description=(
        "Prediction-market research engine with explicit "
        "probability semantics and settlement-aware accounting."
    ),
    packages=find_packages(
        where="src"
    ),
    package_dir={
        "": "src",
    },
    python_requires=">=3.9",
    extras_require={
        "dashboard": [
            "streamlit==1.50.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "polyedge=polyedge.cli:main",
        ],
    },
)
