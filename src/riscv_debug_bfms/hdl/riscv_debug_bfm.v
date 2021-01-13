/****************************************************************************
 * riscv_debug_bfm.v
 ****************************************************************************/

module riscv_debug_bfm #(
		parameter MSG_SZ = 32 		// Maximum characters in the message fields
		) (
        input				clock,
        input				reset,
		input 				valid,
		input[31:0] 		instr,
		input				trap,
		input 				halt,
		input				intr,
		input[1:0]			mode,
		input[1:0]			ixl,
		input[4:0] 			rd_addr,
		input[31:0] 		rd_wdata,
		input[31:0]			pc,
		input[31:0]			mem_addr,
		input[3:0]			mem_wmask,
		input[31:0]			mem_wdata
        );
	
	riscv_debug_bfm_ctrl_m	_ctrl();
	riscv_debug_bfm_ctxt_m  #(MSG_SZ) ctxt();
    
    always @(posedge clock or posedge reset) begin
        if (reset) begin
            _ctrl.in_reset <= 1;
            _ctrl.reg_written <= 32'h0;
        end else begin
            if (_ctrl.in_reset) begin
                _reset();
                _ctrl.in_reset <= 1'b0;
            end
            
            if (valid) begin
            	_ctrl.last_instr <= instr;
            	_ctrl.instr_count = _ctrl.instr_count + 1;
            	ctxt.pc <= pc;
            	ctxt.instr <= instr;
            	
            	// Update register value on write
            	if (|rd_addr) begin
            		case (rd_addr) 
            			1: ctxt.regs.x1 <= rd_wdata;
            			2: ctxt.regs.x2 <= rd_wdata;
            			3: ctxt.regs.x3 <= rd_wdata;
            			4: ctxt.regs.x4 <= rd_wdata;
            			5: ctxt.regs.x5 <= rd_wdata;
            			6: ctxt.regs.x6 <= rd_wdata;
            			7: ctxt.regs.x7 <= rd_wdata;
            			8: ctxt.regs.x8 <= rd_wdata;
            			9: ctxt.regs.x9 <= rd_wdata;
            			10: ctxt.regs.x10 <= rd_wdata;
            			11: ctxt.regs.x11 <= rd_wdata;
            			12: ctxt.regs.x12 <= rd_wdata;
            			13: ctxt.regs.x13 <= rd_wdata;
            			14: ctxt.regs.x14 <= rd_wdata;
            			15: ctxt.regs.x15 <= rd_wdata;
            			16: ctxt.regs.x16 <= rd_wdata;
            			17: ctxt.regs.x17 <= rd_wdata;
            			18: ctxt.regs.x18 <= rd_wdata;
            			19: ctxt.regs.x19 <= rd_wdata;
            			20: ctxt.regs.x20 <= rd_wdata;
            			30: ctxt.regs.x30 <= rd_wdata;
            			31: ctxt.regs.x31 <= rd_wdata;
            		endcase
            	end
            	
            	if (_ctrl.trace_instr_all 
            			|| (_ctrl.trace_instr_jump && (
            				_ctrl.last_instr[6:0] == 7'b1101111 || // jal
            				_ctrl.last_instr[6:0] == 7'b1100111))  // jalr
            			|| (_ctrl.trace_instr_call && (
            				_ctrl.last_instr[6:0] == 7'b1101111 ||
            				_ctrl.last_instr[6:0] == 7'b1100111) /*&& _ctrl.last_instr[11:7] != 5'b0*/)
            			|| _ctrl.hw_breakpoint 
            			|| _ctrl.instr_limit_count == 1
            			|| _ctrl.trace_mem_writes && |mem_wmask) begin
            		// For jumps and calls, we signal the target instruction
            		// instead of the source
            	
            		// First, update register information changed 
            		// since the last instruction we signaled to the Python side
//            		for (i=0; i<32; i++) begin
//            			if (reg_written[i]) begin
//            				_write_reg(i, regs[i]);
//            			end
//            		end
            		_ctrl.reg_written <= 32'h0;
            
            		// Send the current-instruction's write (if any)
            		if (|rd_addr) begin
           				_write_reg(rd_addr, rd_wdata);
            		end
            		
            		// Finally, signal the instruction execution
            		_instr_exec(
            				pc, 
            				instr, 
            				mem_addr,
            				mem_wdata,
            				mem_wmask,
            				_ctrl.instr_count);
            	end else begin
            		// Cache the registers updated while we're 
            		// not notifying the Python environment
            		if (|rd_addr) begin
            			_ctrl.reg_written[rd_addr] <= 1;
            		end
            	end
            	
            	if (_ctrl.instr_limit_count > 0) begin
            		_ctrl.instr_limit_count = _ctrl.instr_limit_count - 1;
            	end
            end
        end
    end
        
    task init;
    begin
        $display("riscv_debug_bfm: %m");
        _set_parameters(MSG_SZ);
    end
    endtask
    
    task _set_func_c(input reg[7:0] idx, input reg[7:0] ch);
   	begin
   		// Must invert the actual index
   		idx = MSG_SZ-idx-1;
   		ctxt.symbol &= ~('hFF << 8*idx);
   		ctxt.symbol |= (ch << 8*idx);
   	end
    endtask
    
    task _set_disasm_c(input reg[7:0] idx, input reg[7:0] ch);
   	begin
   		// Must invert the actual index
   		idx = MSG_SZ-idx-1;
   		ctxt.disasm &= ~('hFF << 8*idx);
   		ctxt.disasm |= (ch << 8*idx);
   	end
    endtask
    
    task _set_instr_limit(input reg[31:0] limit);
    	_ctrl.instr_limit_count = limit;
    endtask
    
    task _set_trace_level(input reg[31:0] level);
   	begin
   		case (level)
   			0: begin //
   				_ctrl.trace_instr_all = 0;
   				_ctrl.trace_instr_jump = 0;
   				_ctrl.trace_instr_call = 1;
   			end
   			1: begin //
   				_ctrl.trace_instr_all = 0;
   				_ctrl.trace_instr_jump = 1;
   				_ctrl.trace_instr_call = 0;
   			end
   			2: begin //
   				_ctrl.trace_instr_all = 1;
   				_ctrl.trace_instr_jump = 0;
   				_ctrl.trace_instr_call = 0;
   			end
   			default: begin
   				$display("%m Error: unknown trace level %0d", level);
   				$finish();
   			end
   		endcase
   	end
    endtask
	
    // Auto-generated code to implement the BFM API
`ifdef PYBFMS_GEN
${pybfms_api_impl}
`endif

endmodule

module riscv_debug_bfm_ctxt_m #(
		parameter MSG_SZ=32
		) ();
	reg[8*MSG_SZ-1:0]		disasm = {MSG_SZ{8'h00}};
	reg[31:0]				instr;
	reg[31:0]				pc;
	riscv_debug_bfm_regs_m	regs();
	reg[8*MSG_SZ-1:0]		symbol = {MSG_SZ{8'h00}};
endmodule

// Registers traced by the debug BFM
module riscv_debug_bfm_regs_m();
	reg[31:0]				x1 = {32{1'b0}};
	reg[31:0]				x2 = {32{1'b0}};
	reg[31:0]				x3 = {32{1'b0}};
	reg[31:0]				x4 = {32{1'b0}};
	reg[31:0]				x5 = {32{1'b0}};
	reg[31:0]				x6 = {32{1'b0}};
	reg[31:0]				x7 = {32{1'b0}};
	reg[31:0]				x8 = {32{1'b0}};
	reg[31:0]				x9 = {32{1'b0}};
	reg[31:0]				x10 = {32{1'b0}};
	reg[31:0]				x11 = {32{1'b0}};
	reg[31:0]				x12 = {32{1'b0}};
	reg[31:0]				x13 = {32{1'b0}};
	reg[31:0]				x14 = {32{1'b0}};
	reg[31:0]				x15 = {32{1'b0}};
	reg[31:0]				x16 = {32{1'b0}};
	reg[31:0]				x17 = {32{1'b0}};
	reg[31:0]				x18 = {32{1'b0}};
	reg[31:0]				x19 = {32{1'b0}};
	reg[31:0]				x20 = {32{1'b0}};
	reg[31:0]				x21 = {32{1'b0}};
	reg[31:0]				x22 = {32{1'b0}};
	reg[31:0]				x23 = {32{1'b0}};
	reg[31:0]				x24 = {32{1'b0}};
	reg[31:0]				x25 = {32{1'b0}};
	reg[31:0]				x26 = {32{1'b0}};
	reg[31:0]				x27 = {32{1'b0}};
	reg[31:0]				x28 = {32{1'b0}};
	reg[31:0]				x29 = {32{1'b0}};
	reg[31:0]				x30 = {32{1'b0}};
	reg[31:0]				x31 = {32{1'b0}};
	wire[31:0]				ra = x1;
	wire[31:0]				sp = x2;
	wire[31:0]				gp = x3;
	wire[31:0]				tp = x4;
	wire[31:0]				t0 = x5;
	wire[31:0]				t1 = x6;
	wire[31:0]				t2 = x7;
	wire[31:0]				s0 = x8;
	wire[31:0]				s1 = x9;
	wire[31:0]				a0 = x10;
	wire[31:0]				a1 = x11;
	wire[31:0]				a2 = x12;
	wire[31:0]				a3 = x13;
	wire[31:0]				a4 = x14;
	wire[31:0]				a5 = x14;
	wire[31:0]				a6 = x15;
	wire[31:0]				a7 = x17;
	wire[31:0]				s2 = x18;
	wire[31:0]				s3 = x19;
	wire[31:0]				s4 = x20;
	wire[31:0]				s5 = x21;
	wire[31:0]				s6 = x22;
	wire[31:0]				s7 = x23;
	wire[31:0]				s8 = x24;
	wire[31:0]				s9 = x25;
	wire[31:0]				s10 = x26;
	wire[31:0]				s11 = x27;
	wire[31:0]				t3 = x28;
	wire[31:0]				t4 = x29;
	wire[31:0]				t5 = x30;
	wire[31:0]				t6 = x31;
endmodule

// Internal control variables used by the BFM
module riscv_debug_bfm_ctrl_m();
	reg[31:0]				reg_written = 32'h0;
	reg						trace_instr_all   = 1;
	reg						trace_instr_jump  = 1;
	reg						trace_instr_call  = 1;
	reg						trace_reg_writes  = 1;
	reg						trace_mem_writes  = 1;
	reg[31:0]				instr_limit_count = 0;
	reg[31:0]				instr_count = 0;
	
	reg[31:0]				n_hw_breakpoint = 0;
//	reg[31:0]				hw_breakpoint[31:0];
	
    reg            			in_reset = 0;
    
    reg						hw_breakpoint = 0;
    reg[31:0]				last_instr;
endmodule
