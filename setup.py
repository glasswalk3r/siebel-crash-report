from setuptools import setup

setup(
    name="siebel-crash-report",
    version="0.0.1",
    author="Alceu Rodrigues de Freitas Junior",
    author_email="arfreitas@cpan.org",
    description="Python script that search and aggregates Siebel component \
crashes information into a nice report",
    url="https://github.com/glasswalk3r/siebel-crash-report",
    package_dir={'': 'src'},
    install_requires=[
        'simplejson>=3.16.0',
        'iniparse>=0.4'
    ],
    scripts=['bin/crash_reporter'],
    keywords="Siebel crash core dump component",
    classifiers=[
        "Programming Language :: Python :: 2",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
