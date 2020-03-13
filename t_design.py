
import os, sys

sys.path.append(os.path.dirname(sys.argv[0]))

import cicpy as cic


d = cic.Design()
d.fromJsonFile("/Users/wulff/pro/analogicus/work/gf130n/SAR9B_CV.cic")

r = cic.Rules("/Users/wulff/pro/analogicus/tech/gf130n/common/gf_130bcdlite.tech")

s = cic.SkillLayPrinter("test",r)
s.print(d)

