from .designprinter import DesignPrinter


patterns = {
    "^TIEH" : """
   output logic Y;
   assign Y = 1'b1;
""",
    "^TIEL" : """
   output logic Y;
   assign Y = 1'b0;
""",
    "^IVX\d+" : """
   input logic A;
   output logic Y;
   assign Y = ~A;
""",
    "^BFX\d+" : """
   input logic A;
   output logic Y;
   assign Y = A;
""",
    "^NRX\d+" : """
   input logic A;
   input logic B;
   output logic Y;
   assign Y = ~(A|B);
""",
    "^NDX\d+" : """
   input logic A;
   input logic B;
   output logic Y;
   assign Y = ~(A&B);
""",
    "^ORX\d+" : """
   input logic A;
   input logic B;
   output logic Y;
   assign Y = A|B;
""",
   "^ANX\d+" : """
   input logic A;
   input logic B;
   output logic Y;
   assign Y = A&B;
""",
   "^DFRNQNX\d+" : """
   input logic D;
   input logic CK;
   output logic Q;
   output logic QN;
   input logic  RN;

   always_ff @(posedge CK or negedge RN) begin
      if(~RN) begin
         Q <= 1'b0;
         QN <= 1'b1;
      end
      else begin
         Q <= D;
         QN <= ~D;
      end
   end
"""



}

class VerilogPrinter(DesignPrinter):



    def __init__(self,filename,rules):
        super().__init__(filename,rules)

    def startLib(self,name):
        self.openFile(name + ".v")
        if(self.info is None):
            raise Exception("Error: Info file not loaded, can't write verilog")

    def endLib(self):
        self.closeFile()

    def startCell(self,cell):
        if(cell.name not in self.info):
            return

        cinfo = self.info[cell.name]
        ports = list()
        for pname in cinfo["portorder"]:
            port = cinfo["ports"][pname]
            if(port["type"] in ["analog","digital"]):
                ports.append(pname)

        strports = ",".join(ports)
        self.f.write(f"""
//-------------------------------------------------------------
// {cell.name}
//-------------------------------------------------------------
module {cell.name}({strports});
""")

        inputs = list()
        outputs= list()

        for pname in cinfo["portorder"]:
            port = cinfo["ports"][pname]
            if(port["type"] in ["analog","digital"]):
                if(port["direction"] == "input"):
                    inputs.append(pname)
                elif(port["direction"] == "output"):
                    outputs.append(pname)

                self.f.write("  " + port["direction"] + " logic " + pname + ";\n")

        func = cinfo["function"]
        if(func == "NOT"):
            if(len(inputs) == 1 and len(outputs) ==1):
                self.f.write(f"  assign {outputs[0]} = ~{inputs[0]};\n")
            else:
                raise Exception("More than 1 input or output for NOT " + ",".join(inputs) + " " + ",".join(outputs))
        elif(func == "BUF"):
            if(len(inputs) == 1 and len(outputs) ==1):
                self.f.write(f"assign {outputs[0]} = {inputs[0]};\n")
            else:
                raise Exception("More than 1 input or output for BUT " + ",".join(inputs) + " " + ",".join(outputs))
        elif(func == "OR"):
            if(len(outputs) ==1):
                self.f.write(f"assign {outputs[0]} = %s;\n" %("|".join(inputs)))
            else:
                raise Exception("More than 1 output for OR " + ",".join(inputs) + " " + ",".join(outputs))
        elif(func == "AND"):
            if(len(outputs) ==1):
                self.f.write(f"assign {outputs[0]} = %s;\n" %("&".join(inputs)))
            else:
                raise Exception("More than 1 output for AND" + ",".join(inputs) + " " + ",".join(outputs))
        elif(func == "NAND"):
            if(len(outputs) ==1):
                self.f.write(f"assign {outputs[0]} = ~(%s);\n" %("&".join(inputs)))
            else:
                raise Exception("More than 1 output for NAND " + ",".join(inputs) + " " + ",".join(outputs))
            pass
        elif(func == "NOR"):
            if(len(outputs) ==1):
                self.f.write(f"assign {outputs[0]} = ~(%s);\n" %("|".join(inputs)))
            else:
                raise Exception("More than 1 output for NOR " + ",".join(inputs) + " " + ",".join(outputs))
        elif(func == "TIEH"):
            for o in outputs:
                self.f.write(f"assign {o} = 1'b1;\n")
        elif(func == "TIEL"):
            for o in outputs:
                self.f.write(f"assign {o} = 1'b0;\n")
        elif(func == "DFFRN"):
            #- Assume port names
            self.f.write("""
  always @(posedge CK or negedge RN) begin
    if(~RN) begin
        Q <= 1'b0;
        QN <= 1'b1;
    end
    else begin
        Q <= D;
        QN <= ~D;
    end
  end
""")

            pass

    def endCell(self,cell):

        if(cell.name not in self.info):
            return
        self.f.write("endmodule\n")

    def printRect(self,rect):
        pass

    def printPort(self,port):
        pass

    def printText(self,text):
        pass
    def printReference(self,inst):
        pass
