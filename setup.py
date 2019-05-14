from setuptools import setup
from setuptools import find_packages

setup(name='dl1_data_handler',
      version='0.7.4',
      description='dl1 HDF5 data writer + reader + processor',
      url='http://github.com/cta-observatory/dl1-data-handler',
      license='MIT',
      packages=['dl1_data_handler'],
      install_requires=[
          'numpy>=1.15.0',
          'tables>=3.4.4',
          'ctapipe>=0.6.2',
          'ctapipe-extra >=0.2.17'],
      dependency_links=[],
      zip_safe=True)
