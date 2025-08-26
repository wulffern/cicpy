
import numpy as np

def placeArray(xorg,yorg,columns,instances,xspace,yspace):

    x = xorg
    y = yorg
    next_x = 0
    next_y = 0
    count = 0
    N = len(instances)
    M = np.floor(N/columns)
    array = list()
    array.append(list())
    row = 0
    for i in instances:
        i.moveTo(x,y)
        array[row].append(i)

        next_x = i.x2 + xspace
        next_y = i.y2 + xspace

        count +=1

        if(count % columns == 0):
            x = xorg
            y = next_y
            row += 1
            array.append(list())
        else:
            x = next_x
    return array
