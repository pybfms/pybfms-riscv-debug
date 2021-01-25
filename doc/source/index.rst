###########################
PyBFMS RISC-V Debug Library
###########################

The PyBFMs RISC-V Debug Library provides support for tracing and debugging
RISC-V processor cores.

************
Installation
************

The RISC-V Debug BFMs library can be installed from PyPi.org or 
directly from GitHub.

Installing from PyPi::

% pip install pybfms_riscv_debug

Installing from GitHub::

% pip install https://github.com/pybfms/pybfms_riscv_debug


*****************
Provided BFMs
*****************

The RISC-V Debug Library currently provides a single BFM.


RISC-V Debug BFM
================

The RISC-V

Debug Trace Features
--------------------

Instruction Disassembly
^^^^^^^^^^^^^^^^^^^^^^^

Register Values
^^^^^^^^^^^^^^^

Call Stack
^^^^^^^^^^

Python API Features
-------------------

Instruction-execution Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Function Enter/Exit Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Wait for Function Enter/Exit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^



Signal-level Interface
----------------------

.. code-block:: sv

  module riscv_debug_bfm #(
        parameter MSG_SZ = 32         // Maximum characters in the message fields
        ) (
        input                clock,
        input                reset,
        input                valid,
        input[31:0]          instr,
        input                trap,
        input                halt,
        input                intr,
        input[1:0]           mode,
        input[1:0]           ixl,
        input[4:0]           rd_addr,
        input[31:0]          rd_wdata,
        input[31:0]          pc,
        input[31:0]          mem_addr,
        input[3:0]           mem_wmask,
        input[31:0]          mem_wdata
        );

Connecting the HDL BFM
^^^^^^^^^^^^^^^^^^^^^^
The HDL BFM requires access to information about executed instructions 
and memory writes. The information is a subset of that provided to the
RISC-V Formal Interface (RVFI) used by the riscv-formal package. Many
RISC-V cores have implemented this interface already, so if your core
has then the required information is already available.

https://github.com/SymbioticEDA/riscv-formal/blob/master/docs/rvfi.md

The following table lists the signals monitored by the RISC-V debug
BFM and the corresponding RVFI signals.

================  ===========
Debug BFM Signal  RVFI Signal
================  ===========
valid             rvfi_valid
N/A               rvfi_order
instr             rvfi_insn
trap              rvfi_trap
halt              rvfi_halt
intr              rvfi_intr
mode              rvfi_mode
ixl               rvfi_ixl
N/A               rvfi_rs1_addr
N/A               rvfi_rs2_addr
N/A               rvfi_rs1_rdata
N/A               rvfi_rs2_rdata
rd_addr           rvfi_rd_addr
rd_wdata          rvfi_rd_wdata
pc                rvfi_pc_rdata
N/A               rvfi_pc_wdata
mem_addr          rvfi_mem_addr
N/A               rvfi_mem_rmask
mem_wmask         rvfi_mem_wmask
N/A               rvfi_mem_rdata
mem_wdata         rvfi_mem_wdata


Python API
----------------------

.. autoclass:: riscv_debug_bfms.riscv_debug_bfm.RiscvDebugBfm
    :members:
    :member-order: bysource
    :undoc-members:

