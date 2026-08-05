
objs = geGetSelectedSet()
(foreach o objs
        
        if(rexMatchp("X1" o~>name) then
            dbMoveFig(o nil list(0.0:0.0 "R0"))

        )

        
        if(rexMatchp("X2" o~>name) then
            dbMoveFig(o nil list(3.44:0.0 "R0"))

        )

        
        if(rexMatchp("X3" o~>name) then
            dbMoveFig(o nil list(6.88:0.0 "R0"))

        )

        
        if(rexMatchp("X4" o~>name) then
            dbMoveFig(o nil list(10.32:0.0 "R0"))

        )

        
        if(rexMatchp("X5" o~>name) then
            dbMoveFig(o nil list(13.76:0.0 "R0"))

        )

        
        if(rexMatchp("X6" o~>name) then
            dbMoveFig(o nil list(17.2:0.0 "R0"))

        )

        )