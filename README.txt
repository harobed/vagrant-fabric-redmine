=========================
Vagrant + faric + redmine
=========================

`vagrant-faric-redmine <https://github.com/harobed/vagrant-fabric-redmine>`_ is a tool to install automatically
`Redmine <http://www.redmine.org/>`_ application in `Vagrant <http://www.vagrantup.com/>`_ VM or directly 
on your Debian physical server.



Prerequisites
=============

On Ubuntu 12.10
---------------

Prerequisites :

.. code-block:: sh

    $ sudo apt-get install virtualbox rubygem1.8


On Mac OS X
-----------

Prerequisites :

* Download `Virtualbox <https://www.virtualbox.org/wiki/Downloads>`_.



Quickstart
==========

Clone `vagrant-fabric-redmine <https://github.com/harobed/vagrant-fabric-redmine>`_ project :

.. code-block:: sh

    $ git clone https://github.com/harobed/vagrant-fabric-redmine.git

Install Python dependencies (`fabric <http://docs.fabfile.org/>`_…) and `Vagrant <http://www.vagrantup.com/>`_ 
with *buildout* :

.. code-block:: sh

    $ python bootstrap.py
    $ bin/buildout


Download and start *vagrant* VM :

.. code-block:: sh

    $ vagrant up


Execute *Redmine* installation
==============================


.. code-block:: sh

    $ bin/fab vagrant install


To test your installion, go to `http://redmine.example.com <http://redmine.example.com>`_.


More info : contact me at `contact@stephane-klein.info <mailto:contact@stephane-klein.info>`_
