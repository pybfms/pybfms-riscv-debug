#****************************************************************************
#* riscv_debug_bfm.py
#*
#****************************************************************************
from enum import Enum, auto, IntEnum

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
import pybfms


class RiscvDebugTraceLevel(IntEnum):
    Call = 0
    Jump = 1
    All = 2
    
@pybfms.bfm(hdl={
    pybfms.BfmType.Verilog : pybfms.bfm_hdl_path(__file__, "hdl/riscv_debug_bfm.v"),
    pybfms.BfmType.SystemVerilog : pybfms.bfm_hdl_path(__file__, "hdl/riscv_debug_bfm.v"),
    }, has_init=True)
class RiscvDebugBfm():

    def __init__(self):
        self.busy = pybfms.lock()
        self.is_reset = False
        self.reset_ev = pybfms.event()
        
        self.en_disasm = True
        
        # Track the current values of the strings
        self.disasm_s = ""
        self.func_s = ""
        
        self.regs = [0]*32
        
        self.addr2sym_m = {}
        self.sym2addr_m = {}
        
        self.instr_exec_f = set()
        self.elffile = None
        self.elffile_fp = None
        self.symtab = None
        
        self.callstack = []
        self.frame_idx = 0
        self.last_instr = 0
        
        self.last_limit = 0

        self.entry_exit_addr2cb_m = {}
        self.entry_exit_cb2addr_m = {}
        
        self.memwrite_cb = set()
        
        self.trace_level : RiscvDebugTraceLevel = RiscvDebugTraceLevel.All
        
    async def on_entry(self, sym_or_addr):
        """ Waits for a function identified by name or symbol to be entered"""
        target_addr_s = set()
        if isinstance(sym_or_addr, str):
            # It's a symbol
            if sym_or_addr in self.sym2addr_m.keys():
                target_addr_s.add(self.sym2addr_m[sym_or_addr])
            else:
                raise Exception("Symbol \"" + sym_or_addr + "\" not found")
        elif isinstance(sym_or_addr, list):
            for e in sym_or_addr:
                if isinstance(e, str):
                    # It's a symbol
                    if e in self.sym2addr_m.keys():
                        target_addr_s.add(self.sym2addr_m[e])
                    else:
                        raise Exception("Symbol \"" + e + "\" not found")
        else:
            # It's an address
            target_addr_s.add(sym_or_addr)
            
        ev = pybfms.event()
        
        def waiter(pc, sym, is_entry):
            if is_entry and pc in target_addr_s:
                ev.set()

        for a in target_addr_s:                
            if a in self.entry_exit_addr2cb_m.keys():
                self.entry_exit_addr2cb_m[a].append(waiter)
            else:
                self.entry_exit_addr2cb_m[a] = [waiter]

        await ev.wait()
        
        for a in target_addr_s:                
            self.entry_exit_addr2cb_m[a].remove(waiter)
        
    async def on_exit(self, sym_or_addr):
        """ Waits for a function identified by name or symbol to be entered"""
        target_addr_s = set()
        if isinstance(sym_or_addr, str):
            # It's a symbol
            if sym_or_addr in self.sym2addr_m.keys():
                target_addr_s.add(self.sym2addr_m[sym_or_addr])
            else:
                raise Exception("Symbol \"" + sym_or_addr + "\" not found")
        elif isinstance(sym_or_addr, list):
            for e in sym_or_addr:
                if isinstance(e, str):
                    # It's a symbol
                    if e in self.sym2addr_m.keys():
                        target_addr_s.add(self.sym2addr_m[e])
                    else:
                        raise Exception("Symbol \"" + e + "\" not found")
        else:
            # It's an address
            target_addr_s.add(sym_or_addr)
            
        ev = pybfms.event()
        
        def waiter(pc, sym, is_entry):
            if is_entry and pc in target_addr_s:
                ev.set()

        for a in target_addr_s:                
            if a in self.entry_exit_addr2cb_m.keys():
                self.entry_exit_addr2cb_m[a].append(waiter)
            else:
                self.entry_exit_addr2cb_m[a] = [waiter]

        await ev.wait()
        
        for a in target_addr_s:                
            self.entry_exit_addr2cb_m[a].remove(waiter)        
    
    def set_trace_level(self, l : RiscvDebugTraceLevel):
        if self.trace_level != l:
            self.trace_level = l
            self._set_trace_level(int(l))
            
            if l != RiscvDebugTraceLevel.All:
                self._set_disasm_s("")
    
    def load_elf(self, elf_path):
        """
        Specifies the software image running on the core 
        this BFM monitors
        """
        
        # Load ELF and extract symbols
        self.elffile_fp = open(elf_path, "rb")
        self.elffile = ELFFile(self.elffile_fp)
        self.symtab = self.elffile.get_section_by_name('.symtab')
            
        for i in range(self.symtab.num_symbols()):
            sym = self.symtab.get_symbol(i)
            if sym.name != "":
                self.addr2sym_m[sym["st_value"]] = sym.name
                self.sym2addr_m[sym.name] = sym["st_value"]
    
    def add_sym_cb(self, name, f):
        if self.elffile is None:
            raise Exception("No ELF file loaded. Cannot set symbol callback")

        sym = self.symtab.get_symbol_by_name(name)
        
        if sym is None:
            raise Exception("Symbol \"" + name + "\" does not exist");
        
        pass
    
    def add_enter_exit_cb(self, f):
        self.enter_exit_cb.append(f)
        
    
    def add_instr_exec_cb(self, f):
        self.instr_exec_f.add(f)
        
    def del_instr_exec_cb(self, f):
        self.instr_exec_f.remove(f)
        
    def add_memwrite_cb(self, f):
        self.memwrite_cb.add(f)
        
    def del_memwrite_cb(self, f):
        self.memwrite_cb.remove(f)
        
    def reg(self, addr):
        """Gets the value of the specified register"""
        return self.regs[addr]
    
    async def wait_exec(self, addrs, max):
        """
        Wait until one of a set of addresses is executed 
        or a maximum number of instructions have been executed
        """
        ev = pybfms.event()
        result = []

        addr_v = []
        
        for a in addrs:
            if isinstance(a, str):
                if self.elffile is None:
                    raise Exception("No ELF file loaded")
                sym = self.symtab.get_symbol_by_name(a)
                
                if sym is None:
                    raise Exception("No symbol named \"" + a + "\"")
                
                addr_v.append(sym[0]["st_value"])
            else:
                addr_v.append(a)
                
        def exec_f(pc, instr):
            if pc in addr_v:
                result.append(pc)
                ev.set()
                
        self.add_instr_exec_cb(exec_f)
        
        await ev.wait()
        
#        self.del_instr_exec_cb(exec_f)
        
        if len(result) > 0:
            return result[0]
        else:
            return -1
        
    
    def _set_disasm_s(self, v):

        if len(v) > self.msg_sz:
            v = v[:-3]
            v += "..."
            
        for i,c in enumerate(v.encode()):
            self._set_disasm_c(i, c)

        # If the new string is shorter than the old string,
        # null out the leftover characters
        if len(self.disasm_s) > len(v):
            i=len(v)
            while i < len(self.disasm_s):
                self._set_disasm_c(i, 0)
                i+=1
        self.disasm_s = v
        
    def _set_func_s(self, frame, v):
        self._clr_func(frame)
        
        #
        if len(v) > self.msg_sz:
            v = v[:-3]
            v += "..."
        
        for i,c in enumerate(v.encode()):
            self._set_func_c(frame, i, c)

        # If the new string is shorter than the old string,
        # null out the leftover characters
#        if len(self.func_s) > len(v):
#            i=len(v)
#            while i < len(self.func_s):
#                self._set_func_c(frame, i, 0)
#                i+=1
#        self.func_s = v

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
            
#        print("instr_exec: " + hex(pc))
        for f in self.instr_exec_f:
            f(pc, instr)

        if mem_wmask != 0:
            for f in self.memwrite_cb:
                f(mem_waddr, mem_wdata, mem_wmask)

        # Handle disassembly            
        if self.trace_level == RiscvDebugTraceLevel.All:
            self._set_disasm_s(self.disasm(pc, instr))

        (last_is_push,last_is_pop,npc) = self.is_pushpop(last_instr, 0)
        
        if last_is_push:
            # Last was the push, so 'pc' is the target
            self.do_call(pc)
        elif last_is_pop:
            self.do_ret(pc)
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
    
    def do_call(self, pc):
        if pc in self.addr2sym_m.keys():
            sym = self.addr2sym_m[pc]
        else:
            sym = "<unknown " + hex(pc) + ">"
            
        self.callstack.append((pc,sym))

        if pc in self.entry_exit_addr2cb_m.keys():
            # Ensure we don't get stuck modifying the list in-flight
            for cb in self.entry_exit_addr2cb_m[pc]:
                cb(pc, sym, True)
                
        self._set_func_s(self.frame_idx, sym)
        self.frame_idx += 1
    
    def do_ret(self, pc):
        if len(self.callstack) > 0:
            (pc,sym) = self.callstack.pop()
        else:
            sym = "<unknown " + hex(pc) + ">"
            
        if pc in self.entry_exit_addr2cb_m.keys():
            # Ensure we don't get stuck modifying the list in-flight
            for cb in self.entry_exit_addr2cb_m[pc]:
                cb(pc, sym, False)

        # TODO: handle swapping windows

        if self.frame_idx > 0:
            self._clr_func(self.frame_idx)
            self.frame_idx -= 1
        else:
            self._clr_func(0)
        
            
    @pybfms.export_task(pybfms.uint32_t,pybfms.uint32_t)
    def _write_reg(self, addr, data):
        self.regs[addr] = data
    
    @pybfms.import_task(pybfms.uint8_t,pybfms.uint8_t,pybfms.uint8_t)
    def _set_func_c(self, frame, idx, ch):
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
        if (instr & 0x3) == 0x3:
            return self.disasm_32(pc, instr)
        else:
            return self.disasm_16(pc, instr)
        
        
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
        
