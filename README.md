# maglimit

![](https://img.shields.io/github/license/iamstarstuff/maglimit)
![](https://img.shields.io/pypi/v/maglimit)
[![DOI](https://zenodo.org/badge/506751105.svg)](https://zenodo.org/badge/latestdoi/506751105)
[![Documentation Status](https://readthedocs.org/projects/maglimit/badge/?version=latest)](https://maglimit.readthedocs.io/en/latest/?badge=latest)

A package to determine observability of an astronomical object using it's magnitude and telescope's limiting magnitude.
The limiting magnitude of a telescope depends only on the aperture of mirror / lens.  


$$L_{mag} = 2 + 5\log{D_0}$$
Where $D_0$ is the aperture.  



## Installation

### Using `pip`
The package is installable on Python 3.x. To install the package,

```python
pip install maglimit
```

### Using `GitHub`
Otherwise, clone this repo, and follow the below specified commands

```python
git clone 'https://github.com/iamstarstuff/maglimit'
cd maglimit
pip install -e .
```
A list of dependencies is available in requirements.txt

 ## Tutorials
 You can find the tutorial here: ['maglimit/docs/Tutorials/limiting_magnitude.ipynb'](https://github.com/iamstarstuff/maglimit/blob/main/docs/Tutorial/limiting_magnitude.ipynb)


 ## Future Goals:
 - We use [astroquery.ipac.ned](https://astroquery.readthedocs.io/en/latest/ipac/ned/ned.html) catalogue to query the object by Messier and NGC name. 
    Further we plan to add cross-catalogue query feature.