# jcell

`jcell` extracts one cell from a `.cic` file and prints the JSON for that cell.

```bash
make test && wc -l NCHDL.json
```

```bash
cicpy jcell ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech  NCHDL > NCHDL.json
     415 NCHDL.json

```


Command under test:

```bash
cicpy jcell ../transpile/SAR9B_CV.cic.gz ../transpile/demo.tech NCHDL > NCHDL.json
```

Excerpt from the extracted cell JSON:

NCHDL.json:
```json
{
    "abstract": false,
    "boundaryIgnoreRouting": false,
    "cellused": false,
    "children": [
        {
            "class": "Rect",
            "layer": "OD",
            "net": "",
            "x1": -1720,
            "x2": 1720,
            "y1": -430,
            "y2": 430
        },
        {
            "class": "Rect",
            "layer": "OD",
            "net": "",
            "x1": -1720,
            "x2": 1720,
            "y1": 430,
            "y2": 1290
        },
        {
            "class": "Rect",
            "layer": "CO",
            "net": "",
            "x1": -1060,
            "x2": -660,
            "y1": 660,
            "y2": 1060
        },
        {
            "class": "Rect",
            "layer": "CO",
            "net": "",
            "x1": 660,
            "x2": 1060,
            "y1": 660,
            "y2": 1060
        },
        {
            "class": "Rect",
            "layer": "OD",
            "net": "",
            "x1": 11180,
            "x2": 13760,
            "y1": 430,
            "y2": 1290
        },
        {
            "class": "Rect",
            "layer": "CO",
            "net": "",
            "x1": 11840,
            "x2": 12240,
            "y1": 660,
            "y2": 1060
        },
        {
            "class": "Rect",
            "layer": "CO",
            "net": "",
            "x1": 12840,
            "x2": 13240,
            "y1": 660,
            "y2": 1060
        },
        {
            "class": "Rect",
            "layer": "OD",
            "net": "",
            "x1": -1720,
            "x2": 1720,
            "y1": 1290,
            "y2": 2150
        },
        {
            "class": "Rect",
            "layer": "OD",

```

