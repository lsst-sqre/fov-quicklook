Welcome to hscmap's documentation!
==================================

.. Note::
   You can try out this package interactively in a live Jupyter notebook environment here:
   
   https://hscmap.mtk.nao.ac.jp/hscMap5/jupyter/lab/?path=tutorial.ipynb

   (Please note that it may take a few seconds to load the environment.)

This is the documentation for the `hscmap` package.
`hscMap` is a web application designed for displaying wide-field observation data. 
The accompanying Python package, named `hscmap`, facilitates the operation of the `hscMap` web application directly from Python environments. 
It's primarily utilized within JupyterLab, offering an integrated experience for data visualization and analysis. 

The package extends a variety of functionalities for enhanced interactivity and control over the data visualization process. 
Key features include:

- **Camera Control**:
   This function allows users to manipulate the viewer's display area, providing capabilities to both retrieve and set the visible region.

- **Manipulation of Displayed Data Sets**:
   The package offers the flexibility to add or remove data sets displayed on the viewer, including the ability to display or hide HiPS (Hierarchical Progressive Surveys) data.

- **Catlog Overlay**:
   This feature enables the overlaying of a catalog—a list of coordinates—onto the viewer. 
   Users can interact with the markers corresponding to these coordinates, with the ability to select them directly through the viewer. 
   Moreover, the selection state of these markers can be managed and retrieved from Python.

- **Region Annotation**:
   Users can annotate the viewer with various shapes such as circles, rectangles, texts, and custom arbitrary shapes, facilitating detailed visualization and analysis of specific areas.

- **Monitoring the Viewer State**:
   The "Monitoring the Viewer State" feature lets Python detect and respond to changes in the `hscMap` viewer caused by user interactions. By registering callback functions.

Installation
============

The `hscmap` package can be installed via pip:

.. code-block:: bash

   pip install jupyterlab # if you haven't installed JupyterLab yet
   pip install https://hscmap.mtk.nao.ac.jp/hscMap5/python/dist/hscmap-0.0.0.tar.gz
   pip install https://hscmap.mtk.nao.ac.jp/hscMap5/python/dist/stellar_globe_jupyterlab_extension-0.0.0.tar.gz

Tutorial
========

You can try out this package interactively in a live Jupyter notebook environment here:

https://hscmap.mtk.nao.ac.jp/hscMap5/jupyter/lab/?path=tutorial.ipynb

(Please note that it may take a few seconds to load the environment.)


API Reference
=============

This is an API reference in alphabetical order.
We recommend that you first read the tutorial and then refer to it as needed.

.. toctree::
   :maxdepth: 3

   autodoc/hscmap

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
