import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='updownserver',
    version='1.0.3',
    author='Harry (Original by Densaugeo)',
    author_email='harry18456@gmail.com',
    description='A lightweight HTTP server with unified upload/download interface',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/harry18456/updownserver',
    packages=['updownserver'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
    extras_require={
        'qr': ['qrcode'],
    },
    entry_points = {
        'console_scripts': ['updownserver=updownserver:main'],
    }
)
