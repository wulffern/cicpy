gdssLibName = "SAR9B"
 pdkLib = "SAR9B"
;- Create cell cut_M4M5_1x2
(let (layout net fig )
 layout = dbOpenCellViewByType(gdssLibName "cut_M4M5_1x2" "layout" "maskLayout" "w")
fig = dbCreateRect(layout list(46 -1) list(0.0:0.0 0.05:0.33))
fig = dbCreateRect(layout list(41 -1) list(0.0:0.075 0.05:0.125))
fig = dbCreateRect(layout list(41 -1) list(0.0:0.205 0.05:0.255))
fig = dbCreateRect(layout list(81 -1) list(0.0:0.0 0.05:0.33))
 dbSave(layout) )
