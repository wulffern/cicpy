
import os, sys
sys.path.append("../")

import cicpy as cic


d = cic.Design()
d.fromJsonFile("/Users/wulff/pro/cic/ciccreator/lay/SAR_ESSCIRC16_28N.cic")

for c in d.children:
    print(c.name)
