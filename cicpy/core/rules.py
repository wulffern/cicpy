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




class Rules:

    rules = False
    
    def __init__(self,filename):

        if(not Rules.rules):
            with open(filename,"r") as f:
                Rules.rules = json.load(f)


    def getField(self,category, key, field):
        if(category in Rules.rules):
            obj = Rules.rules[category]
            if(key in obj):
                lay = obj[key]
                if(field in lay):
                    return lay[field]
                else:
                    raise Exception(f"RuleError: {category}->{key} does not contain {field}")
            else:
                raise Exception(f"RuleError: {category} does not contain {key}")
        else:
            raise Exception(f"RuleError: Rulefile does not have category {category}")
    

        
    def layerToNumber(self,layer):
        return self.getField("layers",layer,"number")

    def layerToDataType(self,layer):
        return self.getField("layers",layer,"datatype")
    
                
        
        
        
