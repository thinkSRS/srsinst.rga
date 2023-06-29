
GUI application
==================

After the full installation, you can start ``srsinst.rga`` application
by typing one of the following commands from the command prompt.
If you installed it with a virtual environment, activate the virtual environment
before stating ``srsinst.rga``.

.. code-block::

    # If python/script directory is in PATH setting,
    rga

    # If not,
    python -m srsinst.rga

The initial window looks like the :ref:`image <top-of-initial-screen-capture>`
in the previous page, if ``srsinst.rga`` is started with the default rga project.

``srsinst.rga`` GUI application is simply the ``srsgui`` application running
with a configuration file including
:class:`RGA100 <srsinst.rga.instruments.rga100.rga.RGA100>` class
and supporting RGA tasks. The `application section of srsgui <srsgui_application_>`_
gives general description on how to use the application.

Following are ``srsinst.rga`` related descriptions.

Opening a configuration file
-------------------------------

Srsinst.rga starts with the last configuration file it used when closed.
Note that the configuration file name is printed in the console dock window,
when the application starts. Unless you loaded another configuration file
after installation, it is the default configuration file, *rga.taskconfig*
in the default Pyhon library directory\\site-packages\\srsinst\\rga
for Windows computers.

If you want to use a different configuration, you can change a configuration file
by select one from the menu/File/Open Config.

Connection to an RGA
-----------------------

You can connect to an RGA by selecting one of the instrument names from the menu/Connect.

If the RGA is connected, it will pop up a dialog box asking if you want to disconnect.
If the RGA is disconnected, it will pop up a dialog box for connection.
The connection dialog box is simply a GUI wrapper for the connection method of the Instrument class shown in
:ref:`Connection section in the instrument driver <top_of_connecting_rga>`

Once an RGA is connected, the Instrument Info panel will be populated with the instrument status info,
which displays the return string of  rga.get_info() method.

Terminal
---------

Once an RGA is connected, you can query and send commands from the terminal.
If you do not see the terminal window, you can bring it up to the top by selecting
the menu/Docks/Terminal.

From the terminal, you can use both the raw remote commands of an RGA and the commands in Rga100 class.
When you type "help" from the terminal, it displays details on how to use commands in the terminal.
Following shows interaction with an RGA from the terminal window.

.. code-block::

    # type the first part of each line into the terminal input and press "Send" button

    # using RGA raw command
    id?   ==>   SRSRGA200VER0.01SN01008
    mi?   ==>   1
    mi2
    mi?   ==>   2

    # with instrument specifier incase you use multiple instrument2
    rga:mi?   ==>   2
    rga2:id?   ==>   SRSRGA100VER0.01SN01023

    # RGA100 instrument class command

    rga.status.id_string   ==>   SRSRGA320VER0.01SN01008
    rga.scan.initial_mass   ==>   2
    rga.scan.initial_mass=1
    rga.scan.initial_mass   ==>   1

You can run all the code blocks shown in :ref:`navigating through RGA100 class <top_of_navigating_rga>`
from the terminal (well, no pprint. Only attributes and methods of the instrument
defined in the configuration file).

.. code-block:: python

    rga.scan.get_parameters()   ==>   (2, 65, 3, 10)
    rga.scan.initial_mass = 1
    rga.scan.final_mass = 100
    rga.scan.get_parameters()   ==>   (1, 100, 3, 10)

Capture dock widget
--------------------
Another way to interact with an RGA is through the capture dock widget. You can open or bring
the capture dock widget to the top by select the **rga-Capture** menu item from the menu/Docks.
Pressing the Capture button will query all the commands in the class, and update the display them
in the tree structure. Double-clicking on a value allow you to change the value.

Enabling *Show method* option will display class methods associated with the components.
Some simple methods without a return value can have the run button.
Pressing the run button the methods can run from the capture dock widget.

    ..  figure:: ./_static/image/rga-capture-dock-screenshot.png
        :align: center
        :scale: 75 %

        Screenshot of the capture dock widget


.. note::

    - The capture dock widget is a convenient way to look through command values of the instrument at a glance.
      However, its continuous update generates a lot of communication with the instrument.

    - The item values does **NOT** get updated or changed reliably while a scan is running in a task.


Tasks
--------

A simple function of an instrument are implemented as a command or a method in a component.
It can be run from the terminal widget or capture dock widget. A Bigger and complex task, however,
may need hundreds of lines of code with combination of multiple
commands and methods of multiple components of multiple instruments.
Such a task can be implemented as a subclass of
`Task`_ class and included as a separate item in the menu/Tasks.

The default task configuration file, rga.taskconfig, contains the following tasks for basic RGA operations.

    * :class:`Search for RGAs on the local area network (LAN)<srsinst.rga.tasks.searchlan.SearchLanTask>`
    * :class:`Filament control <srsinst.rga.tasks.filamentcontroltask.FilamentControlTask>`
    * :class:`CEM control <srsinst.rga.tasks.cemcontroltask.CEMControlTask>`
    * :class:`CEM gain tuning <srsinst.rga.tasks.cemgaintask.CEMGainTask>`
    * :class:`Analog scan <srsinst.rga.tasks.analogscantask.AnalogScanTask>`
    * :class:`Histogram scan <srsinst.rga.tasks.histogramscantask.HistogramScanTask>`
    * :class:`Pressure vs. time scan <srsinst.rga.tasks.pvstscantask.PvsTScanTask>`
    * :class:`Derived P vs. T scan <srsinst.rga.tasks.derivedpvstscantask.DerivedPvsTScanTask>`
    * :class:`Composition analysis scan <srsinst.rga.tasks.compositionanalysistask.CompositionAnalysisTask>`

Select a task from the Tasks menu, adjust parameters, and press the green arrow *Run* button.
It will start the selected task.

.. _srsgui_application: https://thinksrs.github.io/srsgui/application.html
.. _task: https://thinksrs.github.io/srsgui/srsgui.task.html
