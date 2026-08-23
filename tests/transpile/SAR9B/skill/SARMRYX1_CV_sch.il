schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "SARMRYX1_CV" "schematic" "schematic" "w")
schName = "SARMRYX1_CV"
xcoord = 1
ycoord = 0
        
myCMP_OP = schCreatePin( sch inputOutputPinMaster "CMP_OP" "inputOutput" nil 0:0 "R0" )
myTermCMP_OP = (setof pin sch->terminals (pcreMatchp "CMP_OP" pin->name))
myprebBoxCMP_OP = car(car(myCMP_OP~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCMP_OP = dbTransformBBox(myprebBoxCMP_OP myCMP_OP~>transform)
            
myCMP_ON = schCreatePin( sch inputOutputPinMaster "CMP_ON" "inputOutput" nil 0:0.2 "R0" )
myTermCMP_ON = (setof pin sch->terminals (pcreMatchp "CMP_ON" pin->name))
myprebBoxCMP_ON = car(car(myCMP_ON~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCMP_ON = dbTransformBBox(myprebBoxCMP_ON myCMP_ON~>transform)
            
myEN = schCreatePin( sch inputOutputPinMaster "EN" "inputOutput" nil 0:0.4 "R0" )
myTermEN = (setof pin sch->terminals (pcreMatchp "EN" pin->name))
myprebBoxEN = car(car(myEN~>master~>terminals~>pins)~>fig~>bBox)
mybBoxEN = dbTransformBBox(myprebBoxEN myEN~>transform)
            
myRST_N = schCreatePin( sch inputOutputPinMaster "RST_N" "inputOutput" nil 0:0.6000000000000001 "R0" )
myTermRST_N = (setof pin sch->terminals (pcreMatchp "RST_N" pin->name))
myprebBoxRST_N = car(car(myRST_N~>master~>terminals~>pins)~>fig~>bBox)
mybBoxRST_N = dbTransformBBox(myprebBoxRST_N myRST_N~>transform)
            
myENO = schCreatePin( sch inputOutputPinMaster "ENO" "inputOutput" nil 0:0.8 "R0" )
myTermENO = (setof pin sch->terminals (pcreMatchp "ENO" pin->name))
myprebBoxENO = car(car(myENO~>master~>terminals~>pins)~>fig~>bBox)
mybBoxENO = dbTransformBBox(myprebBoxENO myENO~>transform)
            
myCHL_OP = schCreatePin( sch inputOutputPinMaster "CHL_OP" "inputOutput" nil 0:1.0 "R0" )
myTermCHL_OP = (setof pin sch->terminals (pcreMatchp "CHL_OP" pin->name))
myprebBoxCHL_OP = car(car(myCHL_OP~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCHL_OP = dbTransformBBox(myprebBoxCHL_OP myCHL_OP~>transform)
            
myCHL_ON = schCreatePin( sch inputOutputPinMaster "CHL_ON" "inputOutput" nil 0:1.2 "R0" )
myTermCHL_ON = (setof pin sch->terminals (pcreMatchp "CHL_ON" pin->name))
myprebBoxCHL_ON = car(car(myCHL_ON~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCHL_ON = dbTransformBBox(myprebBoxCHL_ON myCHL_ON~>transform)
            
myAVDD = schCreatePin( sch inputOutputPinMaster "AVDD" "inputOutput" nil 0:1.4 "R0" )
myTermAVDD = (setof pin sch->terminals (pcreMatchp "AVDD" pin->name))
myprebBoxAVDD = car(car(myAVDD~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVDD = dbTransformBBox(myprebBoxAVDD myAVDD~>transform)
            
myAVSS = schCreatePin( sch inputOutputPinMaster "AVSS" "inputOutput" nil 0:1.5999999999999999 "R0" )
myTermAVSS = (setof pin sch->terminals (pcreMatchp "AVSS" pin->name))
myprebBoxAVSS = car(car(myAVSS~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVSS = dbTransformBBox(myprebBoxAVSS myAVSS~>transform)
            
        syb =  ddGetObj("cpdk" "SARMRY" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "SARMRY" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        
    ;;-------------------------------------------------------------------
    ;; Create instance XA0
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "TAPCELL_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA0" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "TAP" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XA1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "SAREMX1_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA1" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "ENO" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "RST_N" "lowerLeft" "R0" "stick" 0.0625 nil )
            
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
        schLib = dbOpenCellViewByType("SAR9B" "IVX1_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA2" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "ENO" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "Y" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "LCK_N" "lowerLeft" "R0" "stick" 0.0625 nil )
            
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
        schLib = dbOpenCellViewByType("SAR9B" "SARLTX1_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA4" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CHL" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CHL_OP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "RST_N" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "LCK_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "LCK_N" "lowerLeft" "R0" "stick" 0.0625 nil )
            
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
        schLib = dbOpenCellViewByType("SAR9B" "SARLTX1_CV" "symbol")
        schInst=dbCreateInst(sch schLib "XA5" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CMP_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "CHL" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "CHL_ON" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "RST_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "RST_N" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "EN" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "EN" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "LCK_N" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "LCK_N" "lowerLeft" "R0" "stick" 0.0625 nil )
            
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
