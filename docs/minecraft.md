# minecraft

`minecraft` converts a layout cell into a stream of Minecraft `screen` commands.

```bash
make test && ls -1 NCHDL.mc
```

```bash
cicpy minecraft ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech  NCHDL --x 0 --y 0
NCHDL.mc

```


Excerpt from the generated script:

NCHDL.mc:
```bash
screen -x minecraft -X stuff '/fill -2920 5 -1630 16680 20 5070 air replace
'
screen -x minecraft -X stuff '/forceload add -2920 -1630 16679 5069
'
screen -x minecraft -X stuff '/fill -1720 27 -430 1719 27 429 green replace
/fill -1720 28 -430 1719 28 429 redstone_wire replace
'
screen -x minecraft -X stuff '/fill -1720 27 430 1719 27 1289 green replace
/fill -1720 28 430 1719 28 1289 redstone_wire replace
'
screen -x minecraft -X stuff '/fill 11180 27 430 13759 27 1289 green replace
/fill 11180 28 430 13759 28 1289 redstone_wire replace
'
screen -x minecraft -X stuff '/fill -1720 27 1290 1719 27 2149 green replace
/fill -1720 28 1290 1719 28 2149 redstone_wire replace
'
screen -x minecraft -X stuff '/fill 11180 27 1290 13759 27 2149 green replace
/fill 11180 28 1290 13759 28 2149 redstone_wire replace
'
screen -x minecraft -X stuff '/fill -1720 27 2150 1719 27 3009 green replace
/fill -1720 28 2150 1719 28 3009 redstone_wire replace
'
screen -x minecraft -X stuff '/fill 11180 27 2150 13759 27 3009 green replace
/fill 11180 28 2150 13759 28 3009 redstone_wire replace

```

