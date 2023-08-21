from setuptools import find_packages, setup

setup(
    name="func-cache",
    packages=find_packages(include=["func_cache"]),
    version="0.1.0",
    description="A simple function cache decorator",
    author="ctudoudou@foxmail.com",
    license="MIT",
    extras_require={
        "interactive": ["redis"],
    },
    Entry_points={"console_scripts": ["func-cache=func_cache.command:main"]},
    install_requires=[],
    setup_requires=["pytest-runner"],
    tests_require=["pytest==4.4.1"],
    test_suite="tests",
)
