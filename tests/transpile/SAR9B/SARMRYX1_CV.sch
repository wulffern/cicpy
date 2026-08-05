v {xschem version=3.0.0 file_version=1.2 }
G {}
K {}
V {}
S {}
E {}
C {devices/iopin.sym} 0 0 0 0 {name=p0 lab=CMP_OP}
C {devices/iopin.sym} 0 20 0 0 {name=p1 lab=CMP_ON}
C {devices/iopin.sym} 0 40 0 0 {name=p2 lab=EN}
C {devices/iopin.sym} 0 60 0 0 {name=p3 lab=RST_N}
C {devices/iopin.sym} 0 80 0 0 {name=p4 lab=ENO}
C {devices/iopin.sym} 0 100 0 0 {name=p5 lab=CHL_OP}
C {devices/iopin.sym} 0 120 0 0 {name=p6 lab=CHL_ON}
C {devices/iopin.sym} 0 140 0 0 {name=p7 lab=AVDD}
C {devices/iopin.sym} 0 160 0 0 {name=p8 lab=AVSS}
C {SAR9B/TAPCELL_CV.sym} 400 0 0 0 {name=XXA0}
N 360.0 0.0 380.0 0.0 {lab=AVSS}
C {devices/lab_pin.sym} 360.0 0.0 0 0 {name=l0 sig_type=std_logic lab=AVSS }
C {SAR9B/SAREMX1_CV.sym} 400 120.0 0 0 {name=XXA1}
N 360.0 120.0 380.0 120.0 {lab=CMP_OP}
C {devices/lab_pin.sym} 360.0 120.0 0 0 {name=l1 sig_type=std_logic lab=CMP_OP }
N 360.0 140.0 380.0 140.0 {lab=CMP_ON}
C {devices/lab_pin.sym} 360.0 140.0 0 0 {name=l2 sig_type=std_logic lab=CMP_ON }
N 360.0 160.0 380.0 160.0 {lab=EN}
C {devices/lab_pin.sym} 360.0 160.0 0 0 {name=l3 sig_type=std_logic lab=EN }
N 360.0 180.0 380.0 180.0 {lab=ENO}
C {devices/lab_pin.sym} 360.0 180.0 0 0 {name=l4 sig_type=std_logic lab=ENO }
N 360.0 200.0 380.0 200.0 {lab=RST_N}
C {devices/lab_pin.sym} 360.0 200.0 0 0 {name=l5 sig_type=std_logic lab=RST_N }
N 360.0 220.0 380.0 220.0 {lab=AVDD}
C {devices/lab_pin.sym} 360.0 220.0 0 0 {name=l6 sig_type=std_logic lab=AVDD }
N 360.0 240.0 380.0 240.0 {lab=AVSS}
C {devices/lab_pin.sym} 360.0 240.0 0 0 {name=l7 sig_type=std_logic lab=AVSS }
C {SAR9B/IVX1_CV.sym} 400 360.0 0 0 {name=XXA2}
N 360.0 360.0 380.0 360.0 {lab=ENO}
C {devices/lab_pin.sym} 360.0 360.0 0 0 {name=l8 sig_type=std_logic lab=ENO }
N 360.0 380.0 380.0 380.0 {lab=LCK_N}
C {devices/lab_pin.sym} 360.0 380.0 0 0 {name=l9 sig_type=std_logic lab=LCK_N }
N 360.0 400.0 380.0 400.0 {lab=AVDD}
C {devices/lab_pin.sym} 360.0 400.0 0 0 {name=l10 sig_type=std_logic lab=AVDD }
N 360.0 420.0 380.0 420.0 {lab=AVSS}
C {devices/lab_pin.sym} 360.0 420.0 0 0 {name=l11 sig_type=std_logic lab=AVSS }
C {SAR9B/SARLTX1_CV.sym} 400 540.0 0 0 {name=XXA4}
N 360.0 540.0 380.0 540.0 {lab=CMP_OP}
C {devices/lab_pin.sym} 360.0 540.0 0 0 {name=l12 sig_type=std_logic lab=CMP_OP }
N 360.0 560.0 380.0 560.0 {lab=CHL_OP}
C {devices/lab_pin.sym} 360.0 560.0 0 0 {name=l13 sig_type=std_logic lab=CHL_OP }
N 360.0 580.0 380.0 580.0 {lab=RST_N}
C {devices/lab_pin.sym} 360.0 580.0 0 0 {name=l14 sig_type=std_logic lab=RST_N }
N 360.0 600.0 380.0 600.0 {lab=EN}
C {devices/lab_pin.sym} 360.0 600.0 0 0 {name=l15 sig_type=std_logic lab=EN }
N 360.0 620.0 380.0 620.0 {lab=LCK_N}
C {devices/lab_pin.sym} 360.0 620.0 0 0 {name=l16 sig_type=std_logic lab=LCK_N }
N 360.0 640.0 380.0 640.0 {lab=AVDD}
C {devices/lab_pin.sym} 360.0 640.0 0 0 {name=l17 sig_type=std_logic lab=AVDD }
N 360.0 660.0 380.0 660.0 {lab=AVSS}
C {devices/lab_pin.sym} 360.0 660.0 0 0 {name=l18 sig_type=std_logic lab=AVSS }
C {SAR9B/SARLTX1_CV.sym} 400 780.0 0 0 {name=XXA5}
N 360.0 780.0 380.0 780.0 {lab=CMP_ON}
C {devices/lab_pin.sym} 360.0 780.0 0 0 {name=l19 sig_type=std_logic lab=CMP_ON }
N 360.0 800.0 380.0 800.0 {lab=CHL_ON}
C {devices/lab_pin.sym} 360.0 800.0 0 0 {name=l20 sig_type=std_logic lab=CHL_ON }
N 360.0 820.0 380.0 820.0 {lab=RST_N}
C {devices/lab_pin.sym} 360.0 820.0 0 0 {name=l21 sig_type=std_logic lab=RST_N }
N 360.0 840.0 380.0 840.0 {lab=EN}
C {devices/lab_pin.sym} 360.0 840.0 0 0 {name=l22 sig_type=std_logic lab=EN }
N 360.0 860.0 380.0 860.0 {lab=LCK_N}
C {devices/lab_pin.sym} 360.0 860.0 0 0 {name=l23 sig_type=std_logic lab=LCK_N }
N 360.0 880.0 380.0 880.0 {lab=AVDD}
C {devices/lab_pin.sym} 360.0 880.0 0 0 {name=l24 sig_type=std_logic lab=AVDD }
N 360.0 900.0 380.0 900.0 {lab=AVSS}
C {devices/lab_pin.sym} 360.0 900.0 0 0 {name=l25 sig_type=std_logic lab=AVSS }
