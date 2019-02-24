from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name="siebel-crash-report",
    version="0.0.1",
    author="Alceu Rodrigues de Freitas Junior",
    author_email="glasswalk3r@yahoo.com.br",
    url="https://github.com/glasswalk3r/siebel-crash-report",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'simplejson>=3.13.2',
        'pyyaml>=3.13'
    ],
    description='Searchs and aggregates Siebel component crashes information \
into a nice report.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    scripts=['bin/crash_reporter'],
    keywords="Siebel crash core dump component",
    classifiers=[
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 3',
        "Operating System :: POSIX :: Linux",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
