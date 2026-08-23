schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "RM1" "schematic" "schematic" "w")
schName = "RM1"
xcoord = 1
ycoord = 0
        
myA = schCreatePin( sch inputOutputPinMaster "A" "inputOutput" nil 0:0 "R0" )
myTermA = (setof pin sch->terminals (pcreMatchp "A" pin->name))
myprebBoxA = car(car(myA~>master~>terminals~>pins)~>fig~>bBox)
mybBoxA = dbTransformBBox(myprebBoxA myA~>transform)
            
myB = schCreatePin( sch inputOutputPinMaster "B" "inputOutput" nil 0:0.2 "R0" )
myTermB = (setof pin sch->terminals (pcreMatchp "B" pin->name))
myprebBoxB = car(car(myB~>master~>terminals~>pins)~>fig~>bBox)
mybBoxB = dbTransformBBox(myprebBoxB myB~>transform)
            
        syb =  ddGetObj("cpdk" "RM1" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "RM1" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        

        ;;-------------------------------------------------------------------
        ;; Create Metal capacitor (two metal resistors) R1
        ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType(techLib "devices__res" "symbol")

        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1

        schInst=dbCreateInst(sch schLib "R1_a_0" xcoord:ycoord "0")


    
        dbReplaceProp(schInst "l" 'string "0.06u")
dbReplaceProp(schInst "w" 'string "0.06u")

        (CCSinvokeInstCdfCallbacks schInst ?order list("l" "w"))
            deviceportn = (setof sig schLib~>signals (member "P" sig~>sigNames))
            bBoxDport = car(car(deviceportn~>pins)~>fig)~>bBox
            pinDport=dbTransformBBox(bBoxDport schInst~>transform)
            wireId = schCreateWire( sch "draw" "full" list(centerBox(pinDport) rodAddToX(centerBox(pinDport) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pinDport) 0.125)  "A" "lowerLeft" "R0" "stick" 0.0625 nil )
            
            deviceportn = (setof sig schLib~>signals (member "M" sig~>sigNames))
            bBoxDport = car(car(deviceportn~>pins)~>fig)~>bBox
            pinDport=dbTransformBBox(bBoxDport schInst~>transform)
            wireId = schCreateWire( sch "draw" "full" list(centerBox(pinDport) rodAddToX(centerBox(pinDport) 0.05) )  0.0625 0.0625 0.0 )
            schCreateWireLabel( sch car(wireId) rodAddToX(centerBox(pinDport) 0.125)  "B" "lowerLeft" "R0" "stick" 0.0625 nil )
            
schCheck(sch)
dbSave(sch)
