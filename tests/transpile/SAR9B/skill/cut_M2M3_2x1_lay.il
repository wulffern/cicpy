gdssLibName = "SAR9B"
 pdkLib = "SAR9B"
;- Create cell cut_M2M3_2x1
(let (layout net fig )
 layout = dbOpenCellViewByType(gdssLibName "cut_M2M3_2x1" "layout" "maskLayout" "w")
fig = dbCreateRect(layout list(36 -1) list(0.0:0.0 0.33:0.05))
fig = dbCreateRect(layout list(38 -1) list(0.075:0.0 0.125:0.05))
fig = dbCreateRect(layout list(38 -1) list(0.205:0.0 0.255:0.05))
fig = dbCreateRect(layout list(42 -1) list(0.0:0.0 0.33:0.05))
 dbSave(layout) )
