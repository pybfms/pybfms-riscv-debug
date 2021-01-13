PyBFMS RISC-V Debug
===================

####################
RISC-V Debug BFMs
####################

The Bus Functional Models (BFMs) provided by this package enable debug
interaction with RISC-V cores via a Python testbench. 

Primary Features
================


Using the RISC-V BFMs
=====================

Connecting the HDL BFM
----------------------

The HDL BFM requires access to information about executed instructions 
and memory writes. The information is a subset of that provided to the
RISC-V Formal Interface (RVFI) used by the riscv-formal package. Many
RISC-V cores have implemented this interface already, so if your core
has then the required information is likely already available.

The following table summarizes

####################
Python API
####################
