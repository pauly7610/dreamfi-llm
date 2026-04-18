"""
setup.py - DreamFi package configuration.

Defines dependencies and package metadata for pip install.
"""

from setuptools import setup, find_packages

setup(
    name='dreamfi',
    version='0.1.0',
    description='Product operations platform with locked evaluation infrastructure',
    author='Paul DreamFi',
    author_email='paul@dreamfi.dev',
    url='https://github.com/pauly7610/dreamfi-llm',
    packages=find_packages(exclude=['tests', 'docs']),
    python_requires='>=3.9',
    install_requires=[
        'psycopg2-binary>=2.9.0',
        'pytest>=7.0.0',
        'pytest-asyncio>=0.21.0',
        'python-dotenv>=0.21.0',
    ],
    extras_require={
        'dev': [
            'pytest-cov>=4.0.0',
            'pytest-xdist>=3.0.0',
            'pytest-timeout>=2.1.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
