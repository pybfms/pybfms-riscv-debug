'''
Created on Feb 21, 2021

@author: mballance
'''
from core_debug_common import ParamsIterator
from riscv_debug_bfms.riscv_va_params_iterator import RiscvVaParamsIterator

class RiscvParamsIterator(ParamsIterator):
    
    def __init__(self, bfm):
        super().__init__()
        self.bfm = bfm
        self.param_n = 0
        
        # Capture the SP for later use
        self.sp = bfm.reg(2)
        
        
    def int8(self) -> int:
        """Returns the next 8-bit parameter"""
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        self.param_n += 1
        
        # Handle negative values
        if (ret & 0x80) != 0:
            ret = -((~ret & 0xFF) + 1)
            return ret
        else:
            return (ret & 0xFF)

    def uint8(self) -> int:
        """Returns the next 8-bit parameter"""
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        self.param_n += 1
        
        return (ret & 0xFF)
            
    def int16(self) -> int:
        """Returns the next 16-bit parameter"""
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        
        self.param_n += 1
        
        if (ret & 0x8000) != 0:
            ret = -((~ret & 0xFFFF) + 1) 
            
        return ret
    
    def uint16(self) -> int:
        """Returns the next 16-bit parameter"""
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        
        self.param_n += 1
        
        return ret    
    
    def int32(self) -> int:
        """Returns the next 32-bit parameter"""
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        
        self.param_n += 1

        if (ret & 0x80000000) != 0:
            ret = -((~ret & 0xFFFFFFFF) + 1)
            
        return ret
    
    def uint32(self) -> int:
        """Returns the next 32-bit parameter"""
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        
        self.param_n += 1

        return ret
    
    def int64(self) -> int:
        """Returns the next 64-bit parameter"""
        # TODO:
        raise NotImplementedError("next64 not implemented")
    
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        
        self.param_n += 1
        
        if (ret & 0x8000000000000000) != 0:
            ret = -((~ret & 0xFFFFFFFFFFFFFFFF) + 1)

        return ret

    def uint64(self) -> int:
        """Returns the next 64-bit parameter"""
        # TODO:
        raise NotImplementedError("next64 not implemented")
    
        if self.param_n < 8:
            # Return register value
            ret = self.bfm.reg(self.param_n+10)
        else:
            # Read memory on stack
            raise NotImplementedError("mem-read not implemented")
        
        self.param_n += 1
        
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
        return RiscvVaParamsIterator(self.bfm, self.ptr())


