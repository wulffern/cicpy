######################################################################
##        Copyright (c) 2020 Carsten Wulff Software, Norway 
## ###################################################################
## Created       : wulff at 2020-3-13
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
import sys
import os
import json
import re
from .layer import Layer

class Rules:

    rules = None
    instance = None


    def getInstance():
        return Rules.instance
    
    def __init__(self,filename=None):

        self.alias = dict()
        self.layers = dict()
        if(filename is not None):
            with open(filename,"r") as f:
                Rules.rules = json.load(f)
                self._unspoolInherit()
                Rules.instance = self
                if("layers" in Rules.rules):
                    for layer in Rules.rules["layers"]:
                        l = Layer()
                        l.name = layer
                        l.fromJson(Rules.rules["layers"][layer])
                        self.alias[l.alias] = l
                        self.layers[layer] = l


        if(Rules.rules is not None):
            self.gamma = self.getValue("technology","gamma")
            self.grid = self.getValue("technology","grid")
            self.spiceunit = self.getValue("technology","spiceunit")

        #if(Rules.rules is None):
        #    raise Exception("Rules: No rules loaded!")

    def hasRules(self):
        return (Rules.rules is not None)

    def _inherit(self,obj):
        if(type(obj) is not dict):
            return
        for key in obj:
            o = obj[key]
            if(type(o) is not dict):
                continue
            if("inherit" in o):
                inheritfrom = o["inherit"]
                if(inheritfrom in obj):
                    b = obj[inheritfrom]
                    for field in b:
                        if(field not in o):
                            o[field] = b[field]

    def _unspoolInherit(self):
        for category in Rules.rules:
            obj = Rules.rules[category]
            if(type(obj) is not dict):
                continue
            self._inherit(obj)
            for key in obj:
                if(type(obj) is not dict):
                    continue
                o = obj[key]
                self._inherit(o)




    def getField(self,category, key, field):
        if(category in Rules.rules):
            obj = Rules.rules[category]
            if(key in obj):
                lay = obj[key]
                if(field in lay):
                    return lay[field]
                else:
                    import logging
                    log = logging.getLogger("Rules")
                    log.error(f"RuleError: {category}->{key} does not contain field '{field}'")
                    raise Exception(f"RuleError: {category}->{key} does not contain {field}")
            else:
                import logging
                log = logging.getLogger("Rules")
                log.error(f"RuleError: {category} does not contain key '{key}'")
                raise Exception(f"RuleError: {category} does not contain {key}")
        else:
            import logging
            log = logging.getLogger("Rules")
            log.error(f"RuleError: Rulefile does not have category '{category}'")
            raise Exception(f"RuleError: Rulefile does not have category {category}")

    def getValue(self,category, key ):

        if(category in Rules.rules):
            obj = Rules.rules[category]
            if(key in obj):
                val = obj[key]
                return val
            else:
                import logging
                log = logging.getLogger("Rules")
                log.error(f"RuleError: {category} does not contain key '{key}'")
                raise Exception(f"RuleError: {category} does not contain {key}")
        else:
            import logging
            log = logging.getLogger("Rules")
            log.error(f"RuleError: Rulefile does not have category '{category}'")
            raise Exception(f"RuleError: Rulefile does not have category {category}")

    def get(self,layer,key):
        obj = self.getValue("rules",layer)
        #print(obj)
        if(key in obj):
            #print(obj)
            #print(obj[key])
            return obj[key]*self.gamma
        else:
            raise Exception(f"RuleError: Coult not find rule {key} on layer {layer}")



    def colorTranslate(self,color):
        colors = {
            "gray" : "rgb(1,1,1)",
            "lightgray" : "rgb(104,104,104)",
            "active" : "rgb(102,255,153)",
            "poly" : "rgb(255,128,128)",
            "cut" : "rgb(233,233,0)",
            "mOne" : "rgb(92,92,255)",
            "mTwo" : "rgb(167,167,0)",
            "mThree" : "rgb(77,255,255)",
            "mFour" : "rgb(0,53,0)",
            "mFive" : "brown",
            "mSix" : "teal"
        }

        if(color in colors):
            return colors[color]
        else:
            return color
        
    def layerToNumber(self,layer):
        return self.getField("layers",layer,"number")

    def layerToAlias(self,layer):
        return self.getField("layers",layer,"alias")

    #def
    #
    def getLayer(self,layer):

        if(layer in self.layers):
            return self.layers[layer]
        else:
            return self.layers["PR"]
    
    def getNextLayer(self, layer):
        """Get the next layer in the stack"""
        if layer in self.layers:
            return getattr(self.layers[layer], 'next', "")
        else:
            import logging
            logging.getLogger("Rules").warning(f"Error: Could not find next layer for {layer}")
            return ""
    
    def getPreviousLayer(self, layer):
        """Get the previous layer in the stack"""
        if layer in self.layers:
            return getattr(self.layers[layer], 'previous', "")
        else:
            import logging
            logging.getLogger("Rules").warning(f"Error: Could not find previous layer for {layer}")
            return ""
    
    def isLayerBeforeLayer(self, layer1, layer2):
        """Check if layer1 comes before layer2 in the stack"""
        if layer1 not in self.layers or layer2 not in self.layers:
            return False
        # Walk through the stack from layer1
        current = layer1
        counter = 100
        while current and counter > 0:
            if current == layer2:
                return True
            current = self.getNextLayer(current)
            counter -= 1
        return False
    
    def getConnectStack(self, layer1, layer2):
        """Get the list of layers needed to connect layer1 to layer2"""
        stack = []
        start = None
        stop = None
        
        if self.isLayerBeforeLayer(layer1, layer2):
            start = layer1
            stop = layer2
        elif self.isLayerBeforeLayer(layer2, layer1):
            start = layer2
            stop = layer1
        elif layer1 == "OD":
            start = layer1
            stop = layer2
        elif layer2 == "OD":
            start = layer2
            stop = layer1
        else:
            import logging
            logging.getLogger("Rules").debug(f"No connect rules that tie {layer1} to {layer2}")
            return stack
        
        current = start
        counter = 100
        while current != stop and counter > 0:
            stack.append(self.getLayer(current))
            current = self.getNextLayer(current)
            counter -= 1
            if counter <= 0:
                break
        
        stack.append(self.getLayer(stop))
        return stack
    
    def aliasToLayer(self,alias):
        if(alias in self.alias):
            return self.alias[alias]
        elif(re.search(r"m\d",alias)):
            alias =  alias.replace("m","metal")
            if(alias in self.alias):
                return self.alias[alias]


    def layerToDataType(self,layer):
        return self.getField("layers",layer,"datatype")

    def layerToColor(self,layer):
        return self.getField("layers",layer,"color")

    def layerToFill(self,layer):
        return self.getField("layers",layer,"fill")

    def layerToColorWithTranslate(self,layer):
        color = self.getField("layers",layer,"color")
        return self.colorTranslate(color)

    def hasLayer(self,layer):
        return True if("layers" in Rules.rules and layer in Rules.rules["layers"]) else False


    def device(self,name):
        o = self.getField("technology","devices",name)
        return o

    @property
    def symbol_lib(self):
        o = self.getValue("technology","symbol_lib")
        return o

    @property
    def techlib(self):
        o = self.getValue("technology","techlib")
        return o

    @property
    def symbol_libs(self):
        o = self.getValue("technology","symbol_libs")
        return o
