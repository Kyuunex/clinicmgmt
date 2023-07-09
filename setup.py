from distutils.core import setup

setup(
    name='clinicmgmt',
    packages=[
        'clinicmgmt',
        'clinicmgmt.blueprints',
        'clinicmgmt.classes',
        'clinicmgmt.reusables'
    ],
    include_package_data=True,
    package_data={'clinicmgmt': ['static/*', 'templates/*']},
    version="0.1.0",
    install_requires=[
        'Flask==2.3.2',
    ],
)
