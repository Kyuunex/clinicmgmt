from distutils.core import setup

setup(
    name='clinicmgmt',
    packages=[
        'clinicmgmt',
        'clinicmgmt.blueprints',
        'clinicmgmt.classes',
        'clinicmgmt.localization',
        'clinicmgmt.reusables'
    ],
    include_package_data=True,
    package_data={'clinicmgmt': ['static/*', 'templates/*']},
    version="2023.10.29",
    install_requires=[
        'Flask==3.0.0',
    ],
)
