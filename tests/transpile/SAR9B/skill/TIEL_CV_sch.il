schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "TIEL_CV" "schematic" "schematic" "w")
schName = "TIEL_CV"
xcoord = 1
ycoord = 0
        
myY = schCreatePin( sch inputOutputPinMaster "Y" "inputOutput" nil 0:0 "R0" )
myTermY = (setof pin sch->terminals (pcreMatchp "Y" pin->name))
myprebBoxY = car(car(myY~>master~>terminals~>pins)~>fig~>bBox)
mybBoxY = dbTransformBBox(myprebBoxY myY~>transform)
            
myAVDD = schCreatePin( sch inputOutputPinMaster "AVDD" "inputOutput" nil 0:0.2 "R0" )
myTermAVDD = (setof pin sch->terminals (pcreMatchp "AVDD" pin->name))
myprebBoxAVDD = car(car(myAVDD~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVDD = dbTransformBBox(myprebBoxAVDD myAVDD~>transform)
            
myAVSS = schCreatePin( sch inputOutputPinMaster "AVSS" "inputOutput" nil 0:0.4 "R0" )
myTermAVSS = (setof pin sch->terminals (pcreMatchp "AVSS" pin->name))
myprebBoxAVSS = car(car(myAVSS~>master~>terminals~>pins)~>fig~>bBox)
mybBoxAVSS = dbTransformBBox(myprebBoxAVSS myAVSS~>transform)
            
        syb =  ddGetObj("cpdk" "TIEL" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "TIEL" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        
    ;;-------------------------------------------------------------------
    ;; Create instance MN0
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "NCHDL" "symbol")
        schInst=dbCreateInst(sch schLib "MN0" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "D" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "Y" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "G" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "S" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance MP0
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "PCHDL" "symbol")
        schInst=dbCreateInst(sch schLib "MP0" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "D" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "G" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "S" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVDD" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "AVSS" "lowerLeft" "R0" "stick" 0.0625 nil )
            
schCheck(sch)
dbSave(sch)
