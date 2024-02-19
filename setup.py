from setuptools import setup

setup(
    name='OctoPrint-NozzleFilamentValidator',
    version='0.1.0',
    packages=['octoprint_nfv'],
    url='https://github.com/yourusername/NozzleFilamentValidator',
    license='MIT',
    author='Your Name',
    author_email='your.email@example.com',
    description='OctoPrint plugin for validating nozzle size and filament type',
    install_requires=[
        'OctoPrint>=1.3.10',

    ],
    entry_points={
        'octoprint.plugin': [
            'NozzleFilamentValidator = octoprint_nfv.plugin:NozzleFilamentValidatorPlugin'
        ]
    },
)
