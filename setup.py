from setuptools import setup, find_packages

setup(
    name='video_scraper',
    version='1.0.0',
    description='A web scraper that collects video data and uploads to a database with real-time logging and progress',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4',
        'tqdm',
        'sqlite3',
        'flask'
    ],
    entry_points={
        'console_scripts': [
            'video_scraper = src.main:run',  # Entry point to run your scraper
        ],
    },
    python_requires='>=3.6',
)
