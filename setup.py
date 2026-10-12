from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="api-shield",
    version="2.4.0",
    author="API Shield Team",
    author_email="security@api-shield.dev",
    description="Enterprise-grade Autonomous Rate Limiting & Zero-Trust Defense Gateway for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Yuvaraj-sudo-max/API-SHIELD",
    py_modules=[
        "shield",
        "redis_store",
        "limiter",
        "policy",
        "blocking",
        "identity",
        "metrics",
        "logging_utils",
        "ai_service",
        "routes",
        "config",
        "app",
        "cli",
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask>=3.0.0",
        "redis>=5.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "test": [
            "pytest>=8.0.0",
            "fakeredis>=2.20.0",
        ],
        "prod": [
            "gunicorn>=21.2.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "api-shield=cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
    ],
    python_requires=">=3.9",
)
