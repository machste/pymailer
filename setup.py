from setuptools import setup, find_packages

setup(
    name="pymailer",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "pandoc>=2.3",
        "premailer>=3.10.0",
    ],
    entry_points={
        "console_scripts": [
            "pymailer = pymailer.mailer:main"
        ]
    }
)