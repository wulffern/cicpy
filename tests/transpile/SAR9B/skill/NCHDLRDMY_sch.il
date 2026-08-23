schLibName = "SAR9B"
    techLib = "tech"
    inputPinMaster=dbOpenCellView("basic" "ipin" "symbol" nil "r")
    outputPinMaster=dbOpenCellView("basic" "opin" "symbol" nil "r")
    inputOutputPinMaster=dbOpenCellView("basic" "iopin" "symbol" nil "r")

;Create cell
sch = dbOpenCellViewByType(schLibName "NCHDLRDMY" "schematic" "schematic" "w")
schName = "NCHDLRDMY"
xcoord = 1
ycoord = 0
        
myD = schCreatePin( sch inputOutputPinMaster "D" "inputOutput" nil 0:0 "R0" )
myTermD = (setof pin sch->terminals (pcreMatchp "D" pin->name))
myprebBoxD = car(car(myD~>master~>terminals~>pins)~>fig~>bBox)
mybBoxD = dbTransformBBox(myprebBoxD myD~>transform)
            
myG = schCreatePin( sch inputOutputPinMaster "G" "inputOutput" nil 0:0.2 "R0" )
myTermG = (setof pin sch->terminals (pcreMatchp "G" pin->name))
myprebBoxG = car(car(myG~>master~>terminals~>pins)~>fig~>bBox)
mybBoxG = dbTransformBBox(myprebBoxG myG~>transform)
            
myS = schCreatePin( sch inputOutputPinMaster "S" "inputOutput" nil 0:0.4 "R0" )
myTermS = (setof pin sch->terminals (pcreMatchp "S" pin->name))
myprebBoxS = car(car(myS~>master~>terminals~>pins)~>fig~>bBox)
mybBoxS = dbTransformBBox(myprebBoxS myS~>transform)
            
myB = schCreatePin( sch inputOutputPinMaster "B" "inputOutput" nil 0:0.6000000000000001 "R0" )
myTermB = (setof pin sch->terminals (pcreMatchp "B" pin->name))
myprebBoxB = car(car(myB~>master~>terminals~>pins)~>fig~>bBox)
mybBoxB = dbTransformBBox(myprebBoxB myB~>transform)
            
        syb =  ddGetObj("cpdk" "NCH" "symbol")
        if( syb then
          syb_dd = dbOpenCellViewByType("cpdk" "NCH" "symbol")
          dbCopyCellView(syb_dd schLibName schName "symbol" ?g_overwrite t)
        )


unless( ddGetObj(schLibName schName "symbol")
        schViewToView( schLibName schName schLibName schName "schematic" "symbol" "schSchemToPinList" "schPinListToSymbol" )
)
        
    ;;-------------------------------------------------------------------
    ;; Create transistor M1
    ;;-------------------------------------------------------------------
        schLib = dbOpenCellViewByType(techLib "devices__nmos4" "symbol")
        xcoord = xcoord  + rightEdge(schLib->bBox) - leftEdge(schLib->bBox) + 1
        ndrain = (setof sig schLib~>signals (member "d" sig~>sigNames))
        ngate  = (setof sig schLib~>signals (member "g" sig~>sigNames))
        nsource = (setof sig schLib~>signals (member "s" sig~>sigNames))
        nbulk = (setof sig schLib~>signals (member "b" sig~>sigNames))

        bBoxDrain = car(car(ndrain~>pins)~>fig)~>bBox
        bBoxSource = car(car(nsource~>pins)~>fig)~>bBox
        bBoxBulk = car(car(nbulk~>pins)~>fig)~>bBox
        bBoxGate = car(car(ngate~>pins)~>fig)~>bBox

        schInst=dbCreateInst(sch schLib "M1_0" xcoord:ycoord "0")
        dbReplaceProp(schInst "l" 'string "0.03*1u")
dbReplaceProp(schInst "nf" 'string "1")
dbReplaceProp(schInst "m" 'string "1")
dbReplaceProp(schInst "totalW" 'string "0.258*1u")
dbReplaceProp(schInst "fingerW" 'string "0.258*1u")

        (CCSinvokeInstCdfCallbacks schInst ?order list("l" "nf" "m" "totalW" "fingerW"))

        ;;- Create wires
        pinDrain=dbTransformBBox(bBoxDrain schInst~>transform)
        pinSource=dbTransformBBox(bBoxSource schInst~>transform)
        pinGate=dbTransformBBox(bBoxGate schInst~>transform)
        pinBulk=dbTransformBBox(bBoxBulk schInst~>transform)

        bDestD = mybBoxD
bDestG = mybBoxG
bDestS = mybBoxS
bDestB = mybBoxB

        schCreateWire( sch "route" "flight" list(centerBox(pinDrain) centerBox(bDestD)) 0.0625 0.0625 0.0 )
        schCreateWire( sch "route" "flight" list(centerBox(pinSource) centerBox(bDestS)) 0.0625 0.0625 0.0 )
        schCreateWire( sch "route" "flight" list(centerBox(pinGate) centerBox(bDestG)) 0.0625 0.0625 0.0 )
        schCreateWire( sch "route" "flight" list(centerBox(pinBulk) centerBox(bDestB)) 0.0625 0.0625 0.0 )
        
schCheck(sch)
dbSave(sch)
