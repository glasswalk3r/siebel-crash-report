from setuptools import setup, find_packages

with open('README.md', 'r') as fh:
    long_description = fh.read()

requirements = ['PyYAML>=5.4', 'simplejson>=3.17.2']

setup(
    name="siebel-crash-report",
    version="0.0.2",
    author="Alceu Rodrigues de Freitas Junior",
    author_email="arfreitas@cpan.org",
    url="https://github.com/glasswalk3r/siebel-crash-report",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'simplejson>=3.17.2',
        'pyyaml>=5.4'
    ],
    description='Searchs and aggregates Siebel component crashes information \
into a nice report.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    scripts=['bin/crash_reporter'],
    keywords="Siebel crash core dump component",
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        "Operating System :: POSIX :: Linux",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
)
