schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "CAP32C_CV" "schematic" "schematic" "w")
schName = "CAP32C_CV"
xcoord = 1
ycoord = 0
        
myC1A = schCreatePin( sch inputOutputPinMaster "C1A" "inputOutput" nil 0:0 "R0" )
myTermC1A = (setof pin sch->terminals (pcreMatchp "C1A" pin->name))
myprebBoxC1A = car(car(myC1A~>master~>terminals~>pins)~>fig~>bBox)
mybBoxC1A = dbTransformBBox(myprebBoxC1A myC1A~>transform)
            
myC1B = schCreatePin( sch inputOutputPinMaster "C1B" "inputOutput" nil 0:0.2 "R0" )
myTermC1B = (setof pin sch->terminals (pcreMatchp "C1B" pin->name))
myprebBoxC1B = car(car(myC1B~>master~>terminals~>pins)~>fig~>bBox)
mybBoxC1B = dbTransformBBox(myprebBoxC1B myC1B~>transform)
            
myC2 = schCreatePin( sch inputOutputPinMaster "C2" "inputOutput" nil 0:0.4 "R0" )
myTermC2 = (setof pin sch->terminals (pcreMatchp "C2" pin->name))
myprebBoxC2 = car(car(myC2~>master~>terminals~>pins)~>fig~>bBox)
mybBoxC2 = dbTransformBBox(myprebBoxC2 myC2~>transform)
            
myC4 = schCreatePin( sch inputOutputPinMaster "C4" "inputOutput" nil 0:0.6000000000000001 "R0" )
myTermC4 = (setof pin sch->terminals (pcreMatchp "C4" pin->name))
myprebBoxC4 = car(car(myC4~>master~>terminals~>pins)~>fig~>bBox)
mybBoxC4 = dbTransformBBox(myprebBoxC4 myC4~>transform)
            
myC8 = schCreatePin( sch inputOutputPinMaster "C8" "inputOutput" nil 0:0.8 "R0" )
myTermC8 = (setof pin sch->terminals (pcreMatchp "C8" pin->name))
myprebBoxC8 = car(car(myC8~>master~>terminals~>pins)~>fig~>bBox)
mybBoxC8 = dbTransformBBox(myprebBoxC8 myC8~>transform)
            
myC16 = schCreatePin( sch inputOutputPinMaster "C16" "inputOutput" nil 0:1.0 "R0" )
myTermC16 = (setof pin sch->terminals (pcreMatchp "C16" pin->name))
myprebBoxC16 = car(car(myC16~>master~>terminals~>pins)~>fig~>bBox)
mybBoxC16 = dbTransformBBox(myprebBoxC16 myC16~>transform)
            
myCTOP = schCreatePin( sch inputOutputPinMaster "CTOP" "inputOutput" nil 0:1.2 "R0" )
myTermCTOP = (setof pin sch->terminals (pcreMatchp "CTOP" pin->name))
myprebBoxCTOP = car(car(myCTOP~>master~>terminals~>pins)~>fig~>bBox)
mybBoxCTOP = dbTransformBBox(myprebBoxCTOP myCTOP~>transform)
            
myAVSS = schCreatePin( sch inputOutputPinMaster "AVSS" "inputOutput" nil 0:1.4 "R0" )
myTermAVSS = (setof pin sch->terminals (pcreMatchp "AVSS" pin->name))
myprebBoxAVSS = car(car(myAVSS~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVSS = dbTransformBBox(myprebBoxAVSS myAVSS~>transform)
            
        syb =  ddGetObj("cpdk" "CAP32C" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "CAP32C" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        
    ;;-------------------------------------------------------------------
    ;; Create instance XRES1A
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "RM1" "symbol")
        schInst=dbCreateInst(sch schLib "XRES1A" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "C1A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC1" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XRES1B
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "RM1" "symbol")
        schInst=dbCreateInst(sch schLib "XRES1B" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "C1B" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XRES2
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "RM1" "symbol")
        schInst=dbCreateInst(sch schLib "XRES2" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "C2" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC3" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XRES4
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "RM1" "symbol")
        schInst=dbCreateInst(sch schLib "XRES4" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "C4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC4" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XRES8
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "RM1" "symbol")
        schInst=dbCreateInst(sch schLib "XRES8" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "C8" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC5" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance XRES16
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "RM1" "symbol")
        schInst=dbCreateInst(sch schLib "XRES16" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "A" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "C16" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "NC6" "lowerLeft" "R0" "stick" 0.0625 nil )
            
schCheck(sch)
dbSave(sch)
