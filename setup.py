from setuptools import setup, find_packages

setup(
    name='bcpc-build',
    version='0.1',
    py_modules=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        bcpc-build-unit=bcpc_build.cmd.bcpc_build_unit:cli
        bcpc-build=bcpc_build.cmd.bcpc_build:cli
    ''',
)
