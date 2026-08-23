schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "TAPCELL_CV" "schematic" "schematic" "w")
schName = "TAPCELL_CV"
xcoord = 1
ycoord = 0
        
myTAP = schCreatePin( sch inputOutputPinMaster "TAP" "inputOutput" nil 0:0 "R0" )
myTermTAP = (setof pin sch->terminals (pcreMatchp "TAP" pin->name))
myprebBoxTAP = car(car(myTAP~>master~>terminals~>pins)~>fig~>bBox)
mybBoxTAP = dbTransformBBox(myprebBoxTAP myTAP~>transform)
            
        syb =  ddGetObj("cpdk" "TAPCELL" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "TAPCELL" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        
    ;;-------------------------------------------------------------------
    ;; Create instance MN1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "NCHDL" "symbol")
        schInst=dbCreateInst(sch schLib "MN1" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "D" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "G" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "S" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
    ;;-------------------------------------------------------------------
    ;; Create instance MP1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType("SAR9B" "PCHDL" "symbol")
        schInst=dbCreateInst(sch schLib "MP1" xcoord:ycoord "R180")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        if(xcoord > 15 then
                    xcoord = 2
                    ycoord = ycoord +  topEdge(schLib->bBox) - bottomEdge(schLib->bBox) + 1
        )

        
            signal = (setof sig schLib~>signals (member "D" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "G" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "S" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            signal = (setof sig schLib~>signals (member "B" sig~>sigNames))
            bBox = car(car(signal~>pins)~>fig)~>bBox
            pin =dbTransformBBox(bBox schInst~>transform)

            wireId = schCreateWire( sch "draw" "full" list(centerBox(pin) rodAddToX(centerBox(pin) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pin) 0.125)  "TAP" "lowerLeft" "R0" "stick" 0.0625 nil )
            
schCheck(sch)
dbSave(sch)
