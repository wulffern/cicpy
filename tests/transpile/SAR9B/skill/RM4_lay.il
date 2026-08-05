gdssLibName = "SAR9B"
 pdkLib = "SAR9B"
;- Create cell RM4
(let (layout net fig )
 layout = dbOpenCellViewByType(gdssLibName "RM4" "layout" "maskLayout" "w")
fig = dbCreateRect(layout list(46 -1) list(0.0:0.0 0.06:0.06))
net = dbCreateNet(layout "A")
dbCreateTerm( net "A" "inputOutput")
dbCreatePin(net fig)
dbCreateLabel(layout list(46 237) 0.0:0.0 "A" "centerLeft" "R0" "stick" 0.1)
fig = dbCreateRect(layout list(46 -1) list(0.0:0.0 0.06:0.06))
fig = dbCreateRect(layout list(46 -1) list(0.06:0.0 0.18:0.06))
fig = dbCreateRect(layout list(110 14) list(0.06:0.0 0.12:0.06))
fig = dbCreateRect(layout list(46 -1) list(0.06:0.0 0.18:0.06))
net = dbCreateNet(layout "B")
dbCreateTerm( net "B" "inputOutput")
dbCreatePin(net fig)
dbCreateLabel(layout list(46 237) 0.06:0.0 "B" "centerLeft" "R0" "stick" 0.1)
 dbSave(layout) )
