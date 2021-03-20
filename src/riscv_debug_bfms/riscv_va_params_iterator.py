'''
Created on Feb 21, 2021

@author: mballance
'''
import hvlrpc

class RiscvVaParamsIterator(hvlrpc.va_list):
    """Implements the variadic-argument iterator for RISC-V"""
    
    def __init__(self, bfm, addr):
        self.bfm = bfm
        self.addr = addr
        
    def int8(self) -> int:
        """Returns the next 8-bit parameter"""
        ret = self.bfm.mm.read8(self.addr)
        self.addr += 1
        
        ret &= 0xFF
        if (ret & 0x80) != 0:
            ret = -((~ret & 0xFF) + 1)
            
        return ret
    
    def uint8(self) -> int:
        """Returns the next 8-bit parameter"""
        ret = self.bfm.mm.read8(self.addr)
        self.addr += 1
        
        ret &= 0xFF
        return ret
    
    def int16(self) -> int:
        """Returns the next 16-bit parameter"""
        ret = self.bfm.mm.read16(self.addr)
        self.addr += 2
        
        ret &= 0xFFFF
        
        if (ret & 0x8000) != 0:
            ret = -((~ret & 0xFFFF) + 1)
            
        return ret
    
    def uint16(self) -> int:
        """Returns the next 16-bit parameter"""
        ret = self.bfm.mm.read16(self.addr)
        self.addr += 2
        
        ret &= 0xFFFF
        
        return ret
    
    def int32(self) -> int:
        """Returns the next 32-bit parameter"""
        ret = self.bfm.mm.read32(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFF
        if (ret & 0x80000000) != 0:
            ret = -((~ret & 0xFFFFFFFF) + 1)

        return ret
    
    def uint32(self) -> int:
        """Returns the next 32-bit parameter"""
        
        ret = self.bfm.mm.read32(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFF
        
        return ret
    
    def int64(self) -> int:
        """Returns the next 64-bit parameter"""
        ret = self.bfm.mm.read64(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFFFFFFFFFF
        if (ret & 0x8000000000000000) != 0:
            ret = -((~ret & 0xFFFFFFFFFFFFFFFF) + 1)

        return ret
    
    def uint64(self) -> int:
        """Returns the next 64-bit parameter"""
        ret = self.bfm.mm.read64(self.addr)
        self.addr += 4
        
        ret &= 0xFFFFFFFFFFFFFFFF

        return ret
    
    def ptr(self) -> int:
        """Returns the next pointer parameter"""
        if self.bfm.addr_width == 32:
            return self.uint32()
        else:
            return self.uint64()
    
    def str(self) -> str:
        """Returns the next string-type (const char *) parameter"""
        addr = self.ptr()
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
    
    def va(self) -> 'ParamsIterator':
        """Returns the an iterator for variadic params"""
        raise NotImplementedError("nextva not implemented")        
