.. SRS RGA documentation master file, created by
   sphinx-quickstart on Sun Oct  9 16:07:41 2022.

.. _overview:

``srsinst.rga`` documentation
===================================

``srsinst.rga`` is a `Python package <package_>`_ to control and acquire data from
a `Stanford Research Systems (SRS) Residual Gas Analyzer (RGA) <rga100_>`_,
using the `srsgui`_  package as a base instrument driver as well as a graphic user interface (GUI)
application.

    ..  figure:: ./_static/image/comp-analysis-screenshot.png
        :align: center
        :scale: 50 %

        Screenshot of srsinst.rga application

You can use ``srsinst.rga`` with `SRS RGAs <rga100_>`_ in various ways, depending on your need:

    * :class:`RGA100<srsinst.rga.instruments.rga100.rga.RGA100>` class in
      ``srsinst.rga`` provides attributes and methods
      to configure, control and acquire data from an SRS RGA. You can use
      :class:`RGA100<srsinst.rga.instruments.rga100.rga.RGA100>` class
      directly from Python interpreter console, simple text-based scripts, or Jupyter notebook.

    * If you want to control RGAs interactively (using the terminal and the capture widget) and
      run predefined basic RGA tasks (analog scan, histogram scan, P vs. T scan, etc.)
      from GUI environment, you can use `srsgui`_ application loaded with the default RGA
      configuration file.

    * If you want to run your own tasks specific to your system, you can modify existing tasks
      or `write your own task scripts <create_task_>`_ based on Task_ class in srsgui_.
      Adding those tasks to a `configuration file <config_file_>`_, and opening
      the configuration file from the srsgui application
      let you run your tasks as a part of the application.

.. toctree::
   :maxdepth: 4

   installation
   instrument_driver
   gui_application
   custom_tasks
   srsinst.rga

Indices and tables
-------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _srsgui: https://thinksrs.github.io/srsgui/
.. _task: https://thinksrs.github.io/srsgui/srsgui.task.html
.. _create_task: https://thinksrs.github.io/srsgui/create-task.html
.. _config_file: https://thinksrs.github.io/srsgui/create-project.html#populating-the-taskconfig-file
.. _package: https://docs.python.org/3/tutorial/modules.html#packages
.. _rga100: https://thinksrs.com/products/rga.html
.. _rga: https://en.wikipedia.org/wiki/Residual_gas_analyzer
.. _qmf: https://en.wikipedia.org/wiki/Quadrupole_mass_analyzer
.. _manual: https://thinksrs.com/downloads/pdfs/manuals/RGAm.pdf 
