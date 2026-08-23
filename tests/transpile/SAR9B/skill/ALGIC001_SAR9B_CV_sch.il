schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "ALGIC001_SAR9B_CV" "schematic" "schematic" "w")
schName = "ALGIC001_SAR9B_CV"
xcoord = 1
ycoord = 0
        
mySAR_IP = schCreatePin( sch inputOutputPinMaster "SAR_IP" "inputOutput" nil 0:0 "R0" )
myTermSAR_IP = (setof pin sch->terminals (pcreMatchp "SAR_IP" pin->name))
myprebBoxSAR_IP = car(car(mySAR_IP~>master~>terminals~>pins)~>fig~>bBox)
mybBoxSAR_IP = dbTransformBBox(myprebBoxSAR_IP mySAR_IP~>transform)
            
mySAR_IN = schCreatePin( sch inputOutputPinMaster "SAR_IN" "inputOutput" nil 0:0.2 "R0" )
myTermSAR_IN = (setof pin sch->terminals (pcreMatchp "SAR_IN" pin->name))
myprebBoxSAR_IN = car(car(mySAR_IN~>master~>terminals~>pins)~>fig~>bBox)
mybBoxSAR_IN = dbTransformBBox(myprebBoxSAR_IN mySAR_IN~>transform)
            
mySARN = schCreatePin( sch inputOutputPinMaster "SARN" "inputOutput" nil 0:0.4 "R0" )
myTermSARN = (setof pin sch->terminals (pcreMatchp "SARN" pin->name))
myprebBoxSARN = car(car(mySARN~>master~>terminals~>pins)~>fig~>bBox)
mybBoxSARN = dbTransformBBox(myprebBoxSARN mySARN~>transform)
            
mySARP = schCreatePin( sch inputOutputPinMaster "SARP" "inputOutput" nil 0:0.6000000000000001 "R0" )
myTermSARP = (setof pin sch->terminals (pcreMatchp "SARP" pin->name))
myprebBoxSARP = car(car(mySARP~>master~>terminals~>pins)~>fig~>bBox)
mybBoxSARP = dbTransformBBox(myprebBoxSARP mySARP~>transform)
            
myDONE = schCreatePin( sch inputOutputPinMaster "DONE" "inputOutput" nil 0:0.8 "R0" )
myTermDONE = (setof pin sch->terminals (pcreMatchp "DONE" pin->name))
myprebBoxDONE = car(car(myDONE~>master~>terminals~>pins)~>fig~>bBox)
mybBoxDONE = dbTransformBBox(myprebBoxDONE myDONE~>transform)
            
myD_9_ = schCreatePin( sch inputOutputPinMaster "D<9>" "inputOutput" nil 0:1.0 "R0" )
myTermD_9_ = (setof pin sch->terminals (pcreMatchp "D<9>" pin->name))
myprebBoxD_9_ = car(car(myD_9_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_9_ = dbTransformBBox(myprebBoxD_9_ myD_9_~>transform)
            
myD_8_ = schCreatePin( sch inputOutputPinMaster "D<8>" "inputOutput" nil 0:1.2 "R0" )
myTermD_8_ = (setof pin sch->terminals (pcreMatchp "D<8>" pin->name))
myprebBoxD_8_ = car(car(myD_8_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_8_ = dbTransformBBox(myprebBoxD_8_ myD_8_~>transform)
            
myD_7_ = schCreatePin( sch inputOutputPinMaster "D<7>" "inputOutput" nil 0:1.4 "R0" )
myTermD_7_ = (setof pin sch->terminals (pcreMatchp "D<7>" pin->name))
myprebBoxD_7_ = car(car(myD_7_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_7_ = dbTransformBBox(myprebBoxD_7_ myD_7_~>transform)
            
myD_6_ = schCreatePin( sch inputOutputPinMaster "D<6>" "inputOutput" nil 0:1.5999999999999999 "R0" )
myTermD_6_ = (setof pin sch->terminals (pcreMatchp "D<6>" pin->name))
myprebBoxD_6_ = car(car(myD_6_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_6_ = dbTransformBBox(myprebBoxD_6_ myD_6_~>transform)
            
myD_5_ = schCreatePin( sch inputOutputPinMaster "D<5>" "inputOutput" nil 0:1.7999999999999998 "R0" )
myTermD_5_ = (setof pin sch->terminals (pcreMatchp "D<5>" pin->name))
myprebBoxD_5_ = car(car(myD_5_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_5_ = dbTransformBBox(myprebBoxD_5_ myD_5_~>transform)
            
myD_4_ = schCreatePin( sch inputOutputPinMaster "D<4>" "inputOutput" nil 0:1.9999999999999998 "R0" )
myTermD_4_ = (setof pin sch->terminals (pcreMatchp "D<4>" pin->name))
myprebBoxD_4_ = car(car(myD_4_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_4_ = dbTransformBBox(myprebBoxD_4_ myD_4_~>transform)
            
myD_3_ = schCreatePin( sch inputOutputPinMaster "D<3>" "inputOutput" nil 0:2.1999999999999997 "R0" )
myTermD_3_ = (setof pin sch->terminals (pcreMatchp "D<3>" pin->name))
myprebBoxD_3_ = car(car(myD_3_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_3_ = dbTransformBBox(myprebBoxD_3_ myD_3_~>transform)
            
myD_2_ = schCreatePin( sch inputOutputPinMaster "D<2>" "inputOutput" nil 0:2.4 "R0" )
myTermD_2_ = (setof pin sch->terminals (pcreMatchp "D<2>" pin->name))
myprebBoxD_2_ = car(car(myD_2_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_2_ = dbTransformBBox(myprebBoxD_2_ myD_2_~>transform)
            
myD_1_ = schCreatePin( sch inputOutputPinMaster "D<1>" "inputOutput" nil 0:2.6 "R0" )
myTermD_1_ = (setof pin sch->terminals (pcreMatchp "D<1>" pin->name))
myprebBoxD_1_ = car(car(myD_1_~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD_1_ = dbTransformBBox(myprebBoxD_1_ myD_1_~>transform)
            
myEN = schCreatePin( sch inputOutputPinMaster "EN" "inputOutput" nil 0:2.8000000000000003 "R0" )
myTermEN = (setof pin sch->terminals (pcreMatchp "EN" pin->name))
myprebBoxEN = car(car(myEN~>master~>terminals~>pins)~>fig~>bBox)
mybBoxEN = dbTransformBBox(myprebBoxEN myEN~>transform)
            
myCK_SAMPLE = schCreatePin( sch inputOutputPinMaster "CK_SAMPLE" "inputOutput" nil 0:3.0000000000000004 "R0" )
myTermCK_SAMPLE = (setof pin sch->terminals (pcreMatchp "CK_SAMPLE" pin->name))
myprebBoxCK_SAMPLE = car(car(myCK_SAMPLE~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCK_SAMPLE = dbTransformBBox(myprebBoxCK_SAMPLE myCK_SAMPLE~>transform)
            
myCK_SAMPLE_BSSW = schCreatePin( sch inputOutputPinMaster "CK_SAMPLE_BSSW" "inputOutput" nil 0:3.2000000000000006 "R0" )
myTermCK_SAMPLE_BSSW = (setof pin sch->terminals (pcreMatchp "CK_SAMPLE_BSSW" pin->name))
myprebBoxCK_SAMPLE_BSSW = car(car(myCK_SAMPLE_BSSW~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCK_SAMPLE_BSSW = dbTransformBBox(myprebBoxCK_SAMPLE_BSSW myCK_SAMPLE_BSSW~>transform)
            
myVREF = schCreatePin( sch inputOutputPinMaster "VREF" "inputOutput" nil 0:3.400000000000001 "R0" )
myTermVREF = (setof pin sch->terminals (pcreMatchp "VREF" pin->name))
myprebBoxVREF = car(car(myVREF~>master~>terminals~>pins)~>fig~>bBox)
mybBoxVREF = dbTransformBBox(myprebBoxVREF myVREF~>transform)
            
myAVDD = schCreatePin( sch inputOutputPinMaster "AVDD" "inputOutput" nil 0:3.600000000000001 "R0" )
myTermAVDD = (setof pin sch->terminals (pcreMatchp "AVDD" pin->name))
myprebBoxAVDD = car(car(myAVDD~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVDD = dbTransformBBox(myprebBoxAVDD myAVDD~>transform)
            
myAVSS = schCreatePin( sch inputOutputPinMaster "AVSS" "inputOutput" nil 0:3.800000000000001 "R0" )
myTermAVSS = (setof pin sch->terminals (pcreMatchp "AVSS" pin->name))
myprebBoxAVSS = car(car(myAVSS~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVSS = dbTransformBBox(myprebBoxAVSS myAVSS~>transform)
            
        syb =  ddGetObj("cpdk" "ALGIC001_SAR9B" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "ALGIC001_SAR9B" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        
    ;;-------------------------------------------------------------------
    ;; Create instance XB1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARBSSW_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XB1" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "VI" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SAR_IP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CK" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE_BSSW" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NCCA" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "TIE_L" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEIN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VO1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VO2" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XB2
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARBSSW_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XB2" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "VI" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SAR_IN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CK" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE_BSSW" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NCCB" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "TIE_L" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEIN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VO1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VO2" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XDAC1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "CDAC9_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XDAC1" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CP<13>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<13>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<12>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<12>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<11>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<8>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<10>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<10>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<9>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<7>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<8>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<8>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<7>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<6>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<6>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<6>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<5>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<5>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<4>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<4>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<3>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<4>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<2>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<3>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<1>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<2>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<0>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<1>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CTOP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XDAC2
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "CDAC9_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XDAC2" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CP<13>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<9>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<12>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<12>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<11>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<11>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<10>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<10>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<9>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<9>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<8>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<8>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<7>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<7>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<6>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<6>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<5>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<5>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<4>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<4>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<3>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<3>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<2>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<2>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<1>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<1>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP<0>" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<0>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CTOP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA0
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA0" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO0" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE0" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<12>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<13>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<12>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<9>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEIN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO0" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA1" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO0" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO1" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE1" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<10>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<8>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<10>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<11>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO0" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO1" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA2
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA2" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO1" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<8>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<7>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<8>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<9>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO1" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA3
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA3" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO3" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE3" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<6>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<6>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<6>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<7>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO3" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA4
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA4" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO3" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CP<4>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<5>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<4>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<5>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO3" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA5
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA5" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO5" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE5" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC3A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<4>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<3>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC3B" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO5" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA6
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA6" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO5" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO6" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE6" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC4A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<3>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<2>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC4B" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO5" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO6" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA7
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA7" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO6" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO7" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE7" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC5A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<2>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<1>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC5B" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO6" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO7" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA8
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARDIGEX4_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA8" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CMP_OP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CMP_ON" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO7" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO8" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC6A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CP1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "D<1>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN0" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CN<0>" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CN1" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC6B" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEIN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CEO7" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CEO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_CMP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CKS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "VREF" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "VREF" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA20
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SARCMPX1_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA20" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "CPI" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CNI" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "SARN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CPO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CNO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CK_CMP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_CMP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CK_SAMPLE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CK_SAMPLE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "DONE" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "DONE" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVDD" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "AVSS" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
schCheck(sch)
dbSave(sch)
