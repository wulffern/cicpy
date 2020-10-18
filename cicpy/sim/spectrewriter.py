######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway
## ###################################################################
## Created       : wulff at 2020-10-16
## ###################################################################
##  The MIT License (MIT)
##
##  Permission is hereby granted, free of charge, to any person obtaining a copy
##  of this software and associated documentation files (the "Software"), to deal
##  in the Software without restriction, including without limitation the rights
##  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##  copies of the Software, and to permit persons to whom the Software is
##  furnished to do so, subject to the following conditions:
##
##  The above copyright notice and this permission notice shall be included in all
##  copies or substantial portions of the Software.
##
##  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##  SOFTWARE.
##
######################################################################

import os

class SpectreWriter:

    def __init__(self,simconf):
        self.simconf = simconf
        self.simdir = None
        self.simfile = None

    def run(self):
        os.system(f"""cd {self.simdir};spectre {self.simfile}  +escchars +log spectre.out -raw psf -format psfascii""")

    def write(self,spicefile,cfgfile):

        dr = cfgfile.replace(".cfg","")
        self.simdir = dr

        if(not os.path.exists(dr)):
            os.makedirs(dr)

        name = dr + os.path.sep + cfgfile.replace(".cfg",".scs")
        self.simfile = cfgfile.replace(".cfg",".scs")
        with open(name,"w") as fo:
            fo.write(f"Generated {self.simfile} \n")
            fo.write(f"// Config Version : {self.simconf.version}\n\n")

            self.fo = fo

            self.addHeader("OPTIONS")

            fo.write("""
global 0

simulatorOptions options reltol=1e-6 vabstol=1e-6 save=selected \\
iabstol=1e-12 gmin=1e-15 redefinedparams=warning digits=7 cols=80 \\
pivrel=1e-3 sensfile="psf/sens.output" checklimitdest=both
            
            """)



            self.addHeader("INCLUDES")

            self.addInclude(spicefile)

            self.addHeader("DEVICE UNDER TEST")

            self.simconf.writeSubckt(self)

            self.simconf.writePorts(self)

    def addParam(self,key,val):
        self.fo.write(f"parameters {key}={val}\n")


    def addInclude(self,spicefile):
        self.fo.write(f"include \"{spicefile}\"\n")


    def addComment(self,ss):
        self.fo.write(f"// {ss}\n")

    def addHeader(self,name):
        self.fo.write(f"""
//-----------------------------------------------------------------
// {name}
//-----------------------------------------------------------------
""")

    def addLine(self):
        self.fo.write("\n")

    def addForce(self,ftype,name,val):
        if(ftype == "vdc"):
            self.fo.write(f"v{name.lower()} ({name} 0) vsource type=dc dc={val} \n")
        if(ftype == "idc"):
            self.fo.write(f"i{name.lower()} (0 {name}) isource type=dc dc={val} \n")
        if(ftype == "resistance"):
            self.fo.write(f"r{name.lower()} ({name} 0) resistor r={val} \n")
        if(ftype == "capacitance"):
            self.fo.write(f"c{name.lower()} ({name} 0) resistor c={val} \n")

        #self.fo.write("\n")

    def addMeasurement(self,mtype,name):

        if(mtype == "current"):
            self.fo.write(f"""save {name} xdut:{name}\n""")

        if(mtype == "impedance"):
            self.fo.write(f"""

// Measure impedance of {name}
vz{name} (0 {name}) vsource mag=1
save xdut:{name}

            """)

    def addSubckt(self,subckt,nodes):
        self.fo.write("xdut (" +" ".join(nodes) +  f") {subckt}\n")
