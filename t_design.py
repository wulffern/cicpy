
import os, sys
sys.path.append(os.path.dirname(sys.argv[0]))



import cicpy as cic


d = cic.Design()
d.fromJsonFile("/Users/wulff/pro/analogicus/work/gf130n/SAR9B_CV.cic")

s = cic.SkillLayPrinter("test")

s.print(d)
