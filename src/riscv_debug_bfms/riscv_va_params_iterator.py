'''
Created on Feb 21, 2021

@author: mballance
'''
from core_debug_common.params_iterator import ParamsIterator

class RiscvVaParamsIterator(ParamsIterator):
    """Implements the variadic-argument iterator for RISC-V"""
    
    def __init__(self, bfm, addr):
        self.bfm = bfm
        self.addr = addr
        
    def next8(self) -> int:
        """Returns the next 8-bit parameter"""
        ret = self.bfm.mm.read8(self.addr)
        self.addr += 1
        
        ret &= 0xFF
        if (ret & 0x80) != 0:
            ret = -((~ret & 0xFF) + 1)
            
        return ret
    
    def nextu8(self) -> int:
        """Returns the next 8-bit parameter"""
        ret = self.bfm.mm.read8(self.addr)
        self.addr += 1
        
        ret &= 0xFF
        return ret
    
    def next16(self) -> int:
        """Returns the next 16-bit parameter"""
        ret = self.bfm.mm.read16(self.addr)
        self.addr += 2
        
        ret &= 0xFFFF
        
        if (ret & 0x8000) != 0:
            ret = -((~ret & 0xFFFF) + 1)
            
        return ret
    
    def nextu16(self) -> int:
        """Returns the next 16-bit parameter"""
        ret = self.bfm.mm.read16(self.addr)
        self.addr += 2
        
        ret &= 0xFFFF
        
        return ret
    
    def next32(self) -> int:
        """Returns the next 32-bit parameter"""
        ret = self.bfm.mm.read32(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFF
        if (ret & 0x80000000) != 0:
            ret = -((~ret & 0xFFFFFFFF) + 1)

        return ret
    
    def nextu32(self) -> int:
        """Returns the next 32-bit parameter"""
        
        ret = self.bfm.mm.read32(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFF
        
        return ret
    
    def next64(self) -> int:
        """Returns the next 64-bit parameter"""
        ret = self.bfm.mm.read64(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFFFFFFFFFF
        if (ret & 0x8000000000000000) != 0:
            ret = -((~ret & 0xFFFFFFFFFFFFFFFF) + 1)

        return ret
    
    def nextu64(self) -> int:
        """Returns the next 64-bit parameter"""
        ret = self.bfm.mm.read64(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFFFFFFFFFF

        return ret
    
    def nextptr(self) -> int:
        """Returns the next pointer parameter"""
        if self.bfm.addr_width == 32:
            return self.nextu32()
        else:
            return self.nextu64()
    
    def nextstr(self) -> str:
        """Returns the next string-type (const char *) parameter"""
        addr = self.nextptr()
        mm = self.bfm.mm
        ret = ""

        # Artificially limit strings to 1k
        for i in range(1024):
            ch = mm.read8(addr)
            
            if ch == 0:
                break
            else:
                ret += "%c" % (ch,)
                
            addr += 1
            
        return ret
    
    def nextva(self) -> 'ParamsIterator':
        """Returns the an iterator for variadic params"""
        raise NotImplementedError("nextva not implemented")        
