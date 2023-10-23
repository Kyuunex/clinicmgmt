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
    version="2023.08.24",
    install_requires=[
        'Flask==2.3.3',
    ],
)
