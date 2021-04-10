#****************************************************************************
#* riscv_debug_bfm.py
#*
#****************************************************************************
from enum import Enum, auto, IntEnum

import core_debug_common as cdbgc
from core_debug_common.stack_frame import StackFrame
import pybfms
from riscv_debug_bfms.riscv_params_iterator import RiscvParamsIterator
from core_debug_common.callframe_window_mgr import CallframeWindowMgr


class RiscvDebugTraceLevel(IntEnum):
    Call = 0
    Jump = 1
    All = 2
    
@pybfms.bfm(hdl={
    pybfms.BfmType.Verilog : pybfms.bfm_hdl_path(__file__, "hdl/riscv_debug_bfm.v"),
    pybfms.BfmType.SystemVerilog : pybfms.bfm_hdl_path(__file__, "hdl/riscv_debug_bfm.v"),
    }, has_init=True)
class RiscvDebugBfm(cdbgc.BfmBase):

    def __init__(self):
        super().__init__(32, 32, True)
        self.busy = pybfms.lock()
        self.is_reset = False
        self.reset_ev = pybfms.event()
        
        self.en_disasm = True
        
        self.window_mgr = CallframeWindowMgr(
            8,
            self._set_func_s,
            self._clr_func,
            lambda t : self._set_tid_s(t.tid))
        
        self.regs = [0]*32
        
        self.last_instr = 0
        
        self.sp_l = set()
        self.last_sp = 0x00000000
        
        self.last_limit = 0

        self.trace_level : RiscvDebugTraceLevel = RiscvDebugTraceLevel.All
        
    def set_trace_level(self, l : RiscvDebugTraceLevel):
        if self.trace_level != l:
            self.trace_level = l
            self._set_trace_level(int(l))
            
            if l != RiscvDebugTraceLevel.All:
                self._set_disasm_s("")
                
    def param_iter(self) -> RiscvParamsIterator:
        """Returns a parameter iterator based on current state"""
        return RiscvParamsIterator(self)
    
    def reg(self, addr):
        """Gets the value of the specified register"""
        return self.regs[addr]
    
    def _set_disasm_s(self, v):
        self._clr_disasm()

        if len(v) > self.msg_sz:
            v = v[:-3]
            v += "..."
            
        for i,c in enumerate(v.encode()):
            self._set_disasm_c(i, c)
        
    def _set_tid_s(self, v):
        self._clr_tid()
        if len(v) > self.msg_sz:
            v = v[:-3]
            v += "..."
        
        for i,c in enumerate(v.encode()):
            self._set_tid_c(i, c)
            
    @pybfms.import_task(pybfms.uint8_t, pybfms.uint8_t)
    def _set_tid_c(self, i, v):
        pass
            
    @pybfms.import_task()
    def _clr_tid(self):
        pass
        
        
    def _set_func_s(self, frame, v):
        self._clr_func(frame)
        
        #
        if len(v) > self.msg_sz:
            v = v[:-3]
            v += "..."

        for i,c in enumerate(v.encode()):
            self._set_func_c(frame, i, c)

    @pybfms.import_task(pybfms.uint8_t)
    def _clr_func(self, frame):
        pass

        
    @pybfms.export_task(pybfms.uint32_t)
    def _set_parameters(self, msg_sz):
        self.msg_sz = msg_sz

    @pybfms.export_task(pybfms.uint32_t,pybfms.uint32_t,pybfms.uint32_t,pybfms.uint32_t,pybfms.uint8_t,pybfms.uint32_t,pybfms.uint32_t,pybfms.uint8_t,pybfms.uint32_t)
    def _instr_exec(self, 
                    last_pc,
                    last_instr,
                    pc,
                    instr,
                    intr,
                    mem_waddr,
                    mem_wdata,
                    mem_wmask,
                    count):
#        if mem_wmask:
#            print("Write: " + hex(mem_waddr) + " = " + hex(mem_wmask))

        if intr:
            print("Intr:")
            
#        if mem_wmask: # and mem_waddr == 0x80009298:
#            print("Write: " + hex(mem_waddr) + " " + hex(mem_wdata))
            
#        print("instr_exec: " + hex(pc))
#        instr_exec_f_copy = self.instr_exec_f.copy()
#        for f in instr_exec_f_copy:
#            f(pc, instr)

        if mem_wmask != 0:
            # Update the mirror memory
            self.memwrite(mem_waddr, mem_wdata, mem_wmask)

        # Handle disassembly            
        if self.trace_level == RiscvDebugTraceLevel.All:
            self._set_disasm_s(self.disasm(pc, instr))

        (last_is_push,last_is_pop,npc) = self.is_pushpop(last_instr, 0)
        
        if last_is_push:
            # Last was the push, so 'pc' is the target
            retaddr = last_pc + 4 if (instr & 0x3) == 3 else last_pc + 2
            super().execute(pc, retaddr, instr, cdbgc.ExecEvent.Call)
        elif last_is_pop:
            super().execute(pc, last_pc, instr, cdbgc.ExecEvent.Ret)
        elif last_is_push and last_is_pop:
            print("TODO: both push/pop")
        else:
            # TODO: If this is a branch instruction, check
            # to see if we've landed on a symbol
            pass
                
        self.last_instr = instr
        
    def is_pushpop(self, instr, pc):
        is_push = False 
        is_pop = False
        npc = pc
        
        if (instr & 0x7f) == 0x67:
            # jalr
            rs1 = (instr >> 15) & 0x1f
            rd = (instr >> 7) & 0x1f
            
            rs1_islink = rs1 in [1,5]
            rd_islink = rd in [1,5]
            
            if not rd_islink and rs1_islink:
                is_pop = True
            elif rd_islink and not rs1_islink:
                is_push = True
            elif rd_islink and rs1_islink:
                if rd != rs1:
                    is_push = True
                    is_pop = True
                else:
                    is_push = True
            if is_push:
                npc = pc+4
        elif (instr & 0x7f) == 0x6f:
            # jal
            rd = (instr >> 7) & 0x1f
            is_push = rd in [1,5]
            
            if is_push:
                npc = pc+4
        elif (instr & 0x3) == 2 and ((instr >> 13) & 0x7) == 4:
            # c.jal
            rd = (instr >> 7) & 0x1f
            is_push = rd in [1,5]
            
            if is_push:
                npc = pc+2
        elif (instr & 0x3) == 2 and ((instr >> 13) & 0x7) == 8:
            print("TODO: c.jalr")
        elif (instr & 0x3) == 1 and ((instr >> 13) & 0x7) == 1:
            print("TODO: c.jal")
        
        return (is_push,is_pop,npc)

    def enter(self):
        self.window_mgr.enter(self.active_thread)
                
    def exit(self, frame : StackFrame):
        self.window_mgr.exit(self.active_thread)
 
    @pybfms.export_task(pybfms.uint32_t,pybfms.uint32_t)
    def _write_reg(self, addr, data):
        self.regs[addr] = data
    
    @pybfms.import_task(pybfms.uint8_t,pybfms.uint8_t,pybfms.uint8_t)
    def _set_func_c(self, frame, idx, ch):
        pass
    
    @pybfms.import_task()
    def _clr_disasm(self):
        pass
    
    @pybfms.import_task(pybfms.uint8_t,pybfms.uint8_t)
    def _set_disasm_c(self, idx, ch):
        pass
    
    @pybfms.import_task(pybfms.uint32_t)
    def _set_instr_limit(self, count):
        pass
        
    @pybfms.export_task()
    def _reset(self):
        self.is_reset = True
        self.reset_ev.set()

    @pybfms.import_task(pybfms.uint32_t)
    def _set_trace_level(self, l):
        pass
    
    def disasm(self, pc, instr):
        """Disassembles a single RISC-V instruction"""
        if (instr & 0x3) == 0x3:
            return self.disasm_32(pc, instr)
        else:
            return self.disasm_16(pc, instr)
        
    def get_sp(self) -> int:
        return self.regs[2]
        
    def disasm_32(self, pc, instr):
        ret = ""
        
        rd = ((instr >> 7) & 0x1F)
        rs1 = ((instr >> 15) & 0x1F)
        rs2 = ((instr >> 20) & 0x1F)
        
        rnm = [
            "zero", "ra", "sp", "gp", "tp",
            "t0", "t1", "t2", "s0", "s1",
            "a0", "a1", "a2", "a3", "a4",
            "a5", "a6", "a7", "s2", "s3",
            "s4", "s5", "s6", "s7", "s8",
            "s9", "s10", "s11", "t3", "t4",
            "t5", "t6"
            ]
        
        if (instr & 0x7F) == 0x37:
            ret = "lui %s,0x%05x" % (rnm[rd], (instr >> 12) & 0xFFFFF)
        elif (instr & 0x7F) == 0x17:
            imm = (instr & 0xFFFFF000)
            
            if (imm & 0x80000000) != 0:
                imm = -(~imm + 1)
                
            ret = "auipc %s,0x%08x" % (rnm[rd],(pc+imm))
        elif (instr & 0x7F) == 0x6f:
            imm = 0
            imm |= (((instr >> 31) & 1) << 20)
            imm |= (((instr >> 21) & 0x3FF) << 1)
            imm |= (((instr >> 20) & 1) << 11)
            imm |= (((instr >> 12) & 0xFF) << 12)
                    
            if (imm & (1 << 20)) != 0:
                imm = -(~imm + 1)

            if rd == 0:
                ret = "j 0x%08x" % (pc+imm)
            else:
                ret = "jal %s,0x%08x" % (rnm[rd],(pc+imm))
        elif (instr & 0x7F) == 0x67 and ((instr & 0x7000) == 0):
            imm = (instr >> 20) & 0xFFF
            rs1_v = self.regs[rs1]
            
            if imm & 0x800:
                imm = -((~imm&0xFFF)+1)
                
            target = pc + imm
            
            if rd != 0:
                if imm == 0:
                    ret = "jalr %s,(%s)" % (rnm[rd], rnm[rs1])
                else:
                    ret = "jalr %s,%d(%s)" % (rnm[rd], imm, rnm[rs1])
            else:
                if imm == 0:
                    ret = "jalr (%s)" % (rnm[rs1],)
                else:
                    ret = "jalr %d(%s)" % (imm,rnm[rs1])
        elif (instr & 0x7F) == 0x63:
            op = [
                "beq", "bne", "ill", "ill",
                "blt", "bge", "bltu", "bgeu"
                ][(instr >> 12) & 0x7]
            imm = 0
            imm |= ((instr >> 8) & 0xF) << 1
            imm |= ((instr >> 25) & 0x3F) << 5
            imm |= ((instr >> 7) & 0x1) << 11
            imm |= ((instr >> 31) & 0x1) << 12
            
            if (imm & 0x1000) != 0:
                imm = -((~imm&0x1FFF) + 1)
                
            ret = "%s %s,%s,0x%04x" % (op, rnm[rs1], rnm[rs2], (pc+imm))
        elif (instr & 0x7F) == 0x03:
            op = ["lb", "lh", "lw", "ill"
                  "lbu", "lhb", "ill", "ill"][(instr >> 12) & 0x3]
            imm = (instr >> 20) & 0xFFF
            if imm & 0x800:
                # Actually a signed number
                imm = -((~imm&0xFFF) + 1)
            ret = "%s %s,%d(%s)" % (op,rnm[rd],imm,rnm[rs1])
        elif (instr & 0x7F) == 0x23:
            op = ["sb", "sh", "sw", "ill"][(instr >> 12) & 0x3]
            imm = (((instr >> 25) & 0x7F) << 5) | ((instr >> 7) & 0x1F)
            if imm & 0x800:
                # Actually a signed number
                imm = -((~imm&0xFFF) + 1)
                
            ret = "%s %s,%d(%s)" % (op, rnm[rs2], imm,rnm[rs1])
        elif (instr & 0x7F) == 0x13:
            f3 = (instr >> 12) & 0x7
            op = ["addi", "slli", "slti", "sltiu", 
                      "xori", "srli", "ori", "andi"][f3]
            imm = (instr >> 20) & 0xFFF
            
            if imm & 0x800 and f3 in [0, 2]: # addi, slti
                # Actually a signed number
                imm = -((~imm&0xFFF) + 1)

            if f3 == 0 and rs1 == 0:
                if rd == 0:
                    # nop
                    ret = "nop"
                else:
                    # Synthetic li
                    ret = "li %s,%d" % (rnm[rd],imm)
            else:                                
                ret = "%s %s,%s,%d" % (op,rnm[rd],rnm[rs1],imm)
        elif (instr & 0x7F) == 0x33:
            op = "ill"
            if (instr & 0x40000000) == 0:
                op = ["add", "sll", "slt", "sltu", 
                      "xor", "srl", "or", "and"][(instr >> 12) & 0x3]
            else:
                op = ["sub", "ill", "ill", "ill", 
                      "ill", "sra", "ill", "ill"][(instr >> 12) & 0x3]
                
            ret = "%s %s,%s,%s" % (op, rnm[rd], rnm[rs1], rnm[rs2])
        elif (instr & 0x7F) == 0x1F:
            ret = "fence" if (instr & 0x1000) == 0 else "fence.i"
        elif (instr & 0x73) == 0x1F:
            if ((instr >> 12) & 0x7) == 0:
                ret = "ecall" if (instr & 0x100000) == 0 else "ebreak"
            else:
                op = ["ill", "csrrw", "csrrs", "csrrc",
                      "ill", "csrrwi", "csrrsi", "csrrci"][(instr >> 12) & 0x7]
                # TODO: CSR number
                ret = "%s %s,%s" % (op, rnm[rd], rnm[rs1])
        else:
            ret = "ill "
            
        return ret
    
    def disasm_16(self, pc, instr):
        ret = "ill"
        
        rnm = [
            "zero", "ra", "sp", "gp", "tp",
            "t0", "t1", "t2", "s0", "s1",
            "a0", "a1", "a2", "a3", "a4",
            "a5", "a6", "a7", "s2", "s3",
            "s4", "s5", "s6", "s7", "s8",
            "s9", "s10", "s11", "t3", "t4",
            "t5", "t6"
            ]
        
        if (instr & 0x3) == 0:
            pass
        elif (instr & 0x3) == 1:
            op = (instr >> 13) & 0x7
            rd = (instr >> 7) & 0x1f
            imm = (instr >> 2) & 0x1f
            imm |= ((instr >> 12) & 1) << 5
            
            if op == 0:
                if rd == 0:
                    ret = "c.nop"
                else:
                    ret = "c.addi %s,%d" % (rnm[rd], imm)
            elif op == 1:
                pass
            elif op == 2:
                
                ret = "c.li %s,%d" % (rnm[rd], imm)
        elif (instr & 0x3) == 2:
            pass
        
        return ret;
        
