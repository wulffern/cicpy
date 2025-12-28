#!/usr/bin/env python3

from enum import Enum

class Material(Enum):
    DIFFUSION = 0
    METAL = 1
    POLY = 2
    CUT = 3
    METALRES = 4
    MARKER = 5
    IMPLANT = 6
    OTHER = 7


class Layer:
    def __init__(self):
        self.name = "M1"
        self.alias = "metal1"
        self.number = 0
        self.datatype = 0
        self.material = Material.DIFFUSION
        self.previous = "CO"
        self.next = "VIA1"
        self.pin = "M1_pin"
        self.res = "M1_res"
        self.color = ""
        self.nofill = False
        self.visible = True

    def fromJson(self,obj):

        fields = dir(self)
        for f in fields:
            if(f in obj):
                if(f == "material"):
                    self.material = Material[obj["material"].upper()]
                else:
                    setattr(self,f,obj[f])
