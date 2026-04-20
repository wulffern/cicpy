# transpile

`transpile` fans a `.cic` design out into multiple downstream formats.

```bash
make test && find SAR9B -maxdepth 1 -type f | wc -l && find SAR9B -maxdepth 1 -type f | sed 's#^#/#' | sort | head -n 12
```

```bash
cicpy transpile SAR9B_CV.cic.gz demo.tech SAR9B --layskill --schskill --verilog --xschem --spice --winfo --rinfo demo.txt --magic
     167
/SAR9B/ALGIC001_SAR9B_CV.mag
/SAR9B/ALGIC001_SAR9B_CV.net
/SAR9B/ALGIC001_SAR9B_CV.sch
/SAR9B/ALGIC001_SAR9B_CV.sym
/SAR9B/ALGIC001_SAR9B_CV_NOROUTE.mag
/SAR9B/ALGIC001_SAR9B_CV_NOROUTE.net
/SAR9B/ALGIC001_SAR9B_CV_NOROUTE.sch
/SAR9B/ALGIC001_SAR9B_CV_NOROUTE.sym
/SAR9B/CAP.mag
/SAR9B/CAP.sch
/SAR9B/CAP.sym
/SAR9B/CAP32C_CV.mag

```


Magic output excerpt:

SAR9B/ALGIC001_SAR9B_CV.mag:
```text
magic
tech tech
magscale 1 2
timestamp 1776117600
<< checkpaint >>
rect -459 -437 7201 16412
<< po >>
rect 2600 11014 6758 11026
rect 2600 11120 6758 11132
rect 4132 10867 4144 11024
rect 2600 10867 2612 11130
rect 6656 11120 6668 11172
rect 6656 11172 6668 13310
rect 6739 11014 6751 11172
rect 6739 11172 6751 14824
rect 20 11238 32 13999
rect 20 11238 32 13999
rect 3950 10855 3962 11226
rect 20 11226 3962 11238
rect 2772 11291 2784 13999

```


Xschem output excerpt:

SAR9B/ALGIC001_SAR9B_CV.sch:
```text
v {xschem version=3.0.0 file_version=1.2 }
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} 0 0 0 0 {name=p0 lab=SAR_IP}
C {devices/iopin.sym} 0 20 0 0 {name=p1 lab=SAR_IN}
C {devices/iopin.sym} 0 40 0 0 {name=p2 lab=SARN}
C {devices/iopin.sym} 0 60 0 0 {name=p3 lab=SARP}
C {devices/iopin.sym} 0 80 0 0 {name=p4 lab=DONE}
C {devices/iopin.sym} 0 100 0 0 {name=p5 lab=D<9>}
C {devices/iopin.sym} 0 120 0 0 {name=p6 lab=D<8>}
C {devices/iopin.sym} 0 140 0 0 {name=p7 lab=D<7>}
C {devices/iopin.sym} 0 160 0 0 {name=p8 lab=D<6>}
C {devices/iopin.sym} 0 180 0 0 {name=p9 lab=D<5>}
C {devices/iopin.sym} 0 200 0 0 {name=p10 lab=D<4>}
C {devices/iopin.sym} 0 220 0 0 {name=p11 lab=D<3>}
C {devices/iopin.sym} 0 240 0 0 {name=p12 lab=D<2>}
C {devices/iopin.sym} 0 260 0 0 {name=p13 lab=D<1>}

```

