
objs = geGetSelectedSet()
(foreach o objs
        
        if(rexMatchp("X1" o~>name) then
            dbMoveFig(o nil list(0.0:0.0 "R0"))

        )

        
        if(rexMatchp("X2" o~>name) then
            dbMoveFig(o nil list(0.0:0.344 "R0"))

        )

        
        if(rexMatchp("X3" o~>name) then
            dbMoveFig(o nil list(0.0:0.688 "R0"))

        )

        
        if(rexMatchp("X4" o~>name) then
            dbMoveFig(o nil list(0.0:1.032 "R0"))

        )

        
        if(rexMatchp("X5" o~>name) then
            dbMoveFig(o nil list(0.0:1.376 "R0"))

        )

        
        if(rexMatchp("X6" o~>name) then
            dbMoveFig(o nil list(0.0:1.7199999999999998 "R0"))

        )

        )