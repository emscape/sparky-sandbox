from setuptools import setup, find_packages

setup(
    name="sparky-ai-memory",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "openai",
        "supabase",
        "aiohttp",
        "python-dotenv",
        "tiktoken",
        "watchdog",
    ],
    python_requires=">=3.11",
)