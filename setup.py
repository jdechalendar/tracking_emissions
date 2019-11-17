from setuptools import setup, find_packages

setup(
    name='tracking_emissions',
    packages=[],
    version='0.0.1',
    python_requires='>=3.5',
    install_requires=['pandas>=0.25', 'numpy>=1.17', 'matplotlib', 'xlrd',
                      'joblib', 'cmocean'],
    scripts=[]
)
