from .designprinter import DesignPrinter
import re


class SpicePrinter(DesignPrinter):
    def __init__(self,filename,rules):
        super().__init__(filename,rules)
        self.cell = None
        self.allcells = dict()
        self.current_cell = None
        self.lastname = ".spice"
        self.ngspice = True

    def startLib(self,name):
        self.openFile(name + self.lastname)

    def endLib(self):
        self.closeFile()

    def skipCell(self,cell):

        #if(cell.isCell()):
        #    return True

        if(cell.ckt is None):
            return True

        if(cell.abstract):
            return True

        if(cell.physicalOnly):
            return True


        #if(cell.meta is None):
        #    return True

        return False

    def startCell(self,cell):


        self.current_cell = cell

        self.allcells[cell.name] = 1

        self.cell = cell
        nodes = self.translateNodes(cell.ckt.nodes)
        strports = " ".join(nodes)
        self.f.write(f"""
*-------------------------------------------------------------
* {cell.name} {cell.__class__}
*-------------------------------------------------------------
.SUBCKT {cell.name} {strports}
""")


    def printCell(self,c):
        if(self.skipCell(c)):
            return


        self.startCell(c)


        if(self.ngspice and c.meta is not None and "spice" in c.meta):
            spice = c.meta["spice"]
            if(type(spice) is list):
                self.f.write( "\n".join(spice) + "\n")
            else:
                self.f.write(spice + "\n")
        else:
            try:
                for o in c.ckt.devices:
                    self.printDevice(o)

                for o in c.ckt.instances:
                    self.printInstance(o)

            except Exception as e:
                c.printToJson()
                raise(e)
        self.endCell(c)

    def endCell(self,cell):

        self.current_cell = None
        self.f.write(".ENDS\n")

    def printRect(self,rect):
        pass

    def printPort(self,port):
        return

    def printText(self,text):
        pass

    def printDevice(self,o):

        if("Mosfet" in o.classname):
            self.printMosfet(o)
        elif("Resistor" in o.classname):
             #- NF means in series for highres
            if("nf" in o.properties):
                nf = o.properties["nf"]

                n = o.nodes[0]
                p = o.nodes[1]
                b = o.nodes[2]

                myname = o.name

                for i in range(0,nf):
                    mynodes = [n,p,b]
                    if(i >= 0 and i < nf-1):
                        mynodes[1] = "INT_" + str(i)

                    if(i > 0 and i < nf):
                        mynodes[0] = "INT_" + str(i-1)

                    o.nodes = mynodes
                    o.name = myname + "_" + str(i)
                    self.printResistor(o)
                o.name = myname
                o.nodes = [n,p,b]

            else:
                self.printResistor(o)

        else:
            print(self.o)

        pass

    def printResistor(self,o):

        if(o.deviceName == "mres"):
                odev = self.rules.device(o.deviceName + o.properties["layer"] )
        else:
            odev = self.rules.device(o.deviceName )
        typename = odev["name"]


        propss = self.spiceProperties(odev,o)

        devicetype = odev["devicetype"]

        self.f.write(f"{devicetype}{o.name} " + " ".join(self.translateNodes(o.nodes)) + f" {typename} {propss} \n")

        pass

    def translateNodes(self,nodes):

        if(not self.ngspice):
            return nodes

        new_nodes = list()
        for i in range(0,len(nodes)):
            n = nodes[i]
            if(re.search("<|>",nodes[i])):
                n = n.replace("<","_").replace(">","")
            new_nodes.append(n)


        return new_nodes

    def printMosfet(self,o):

        odev = self.rules.device(o.deviceName)
        typename = odev["name"]

        propss = self.spiceProperties(odev,o)

        devicetype = odev["devicetype"]

        self.f.write(f"{devicetype}{o.name} " + " ".join(self.translateNodes(o.nodes)) + f" {typename} {propss} \n")

        pass

    def spiceProperties(self,odev,o):

        propss = ""
        props = list()
        if("propertymap" in odev):
            ddict = dict()

            #- Go through propertymap and find all parameters
            for key in odev["propertymap"]:
                ddict[key] = dict()
                ddict[key]["val"] = o.properties[odev["propertymap"][key]["name"]]
                ddict[key]["str"] = odev["propertymap"][key]["str"]

            #- If a parameter is used in a string, then replace it
            for key in ddict:
                m = re.search("({\w+})",ddict[key]["str"])

                if(m):
                    for mg in m.groups():
                        rkey = re.sub("{|}","",mg)
                        if(rkey in ddict):
                            ddict[key]["str"] = re.sub(mg,str(ddict[rkey]["val"]),ddict[key]["str"])


            #- Write the properties
            for key in odev["propertymap"]:
                val = str(ddict[key]["val"]) + ddict[key]["str"]
                propss += f" {key}={val} "
        return propss

    def printInstance(self,o):


        instname = o.name
        if(instname.startswith("M")):
            instname = "X" + instname

        if(o.subcktName not in self.allcells):
            print(f"Warning: Could not find cell {o.subcktName}")
        else:
            self.f.write(f"{instname} " + " ".join(self.translateNodes(o.nodes)) + f" {o.subcktName}\n")
        pass
