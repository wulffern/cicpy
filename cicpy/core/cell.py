from .rect import Rect

class Cell(Rect): 

        def __init__ (self,name=""):
            super().__init__()
            self.subckt = None
            self.boundaryIgnoreRouting = False
            self.physicalOnly = False
            self.children  = list()

        # Find the first rectangle in this cell that uses layer
        def getRect(self,layer):
            raise Exception("Not implemented")
            pass
        
        # Add a rectangle to the cell, hooks updated() of the child to updateBoundingRect
        def add(self, child):
            if(child == None):
                raise Exception("Null rectangle added")
            
            #TODO: What did I use children_by_type for?

            #TODO: I handle Ports specially

            #TODO: I handled Routes specially

            if(not child in self.children):
                child.parent = self
                self.children.append(child)
                child.connect(self.updateBoundingRect)

        
        # Move this cell, and all children by dx and dy
        def translate( dx, dy):
            raise Exception("Not implemented")
            pass

        # Mirror this cell, and all children around ax
        def mirrorX(ax):
            raise Exception("Not implemented")
            pass

        # Mirror this cell, and all children around ay
        def mirrorY(ay):
            raise Exception("Not implemented")
            pass

        # Move this cell, and all children to ax and ay
        def moveTo(ax, ay):
            raise Exception("Not implemented")
            pass

        # Center this cell, and all children on ax and ay
        def moveCenter(ax, ay):
            raise Exception("Not implemented")
            pass

        # Shortcut for adding ports
        def addPort(name, rect):
            raise Exception("Not implemented")
            pass
            
        # Mirror this cell, and all children around horizontal center point (basically flip horizontal)
        def mirrorCenterX(self):
            self.mirrorX(self.centerY)
            pass
            
            
        def mirrorCenterY():
            self.mirrorY(self.centerX)
            pass

        def updateBoundingRect(self):
            pass

        # Calculate the extent of this cell. Should be overriden by children
        def calcBoundingRect():
            raise Exception("Not implemented")
            pass

        def isEmpty():
            raise Exception("Not implemented")
            pass
        

        #- Abstract methods
        def paint():
            pass

        def route():
            pass

        def place():
            pass


        def fromJson(self,jobj):
            super().fromJson(jobj)
            self.name = jobj["name"]
            self.has_pr = jobj["has_pr"]


        

    #     Port * getPort(QString name);
    #     Port * getCellPort(QString name);

    #     //! Get all ports on this cell
    #     QList<Port *>  ports();
    #     QMap<QString,QList<Port*>> allports();
    #     QList<QString> allPortNames();

    #     //! Update rectangle of port, if port does not exist a new one
    #     //! is created
    #     Port * updatePort(QString name,Rect* r);

    #     //! Spice subcircuit object
    #     cIcSpice::Subckt * subckt(){return _subckt;}
    #     cIcSpice::Subckt * setSubckt(cIcSpice::Subckt * val){ _subckt = val; return _subckt;}


    #     //! Get list of all children
    #     QList<Rect*> children(){return _children;}

    #     bool isASpicePort(QString name);
        

    #     //! Place children
    #     virtual void place();

    #     //! Route children
    #     virtual void route();

    #     //! Paint children, useful with a method after route
    #     virtual void paint();

    #     //! Automatically add remaing ports
    #     virtual void addAllPorts();

    #     //! Check if this cell contains a cell with name cell
    #     static bool hasCell(QString cell){
    #         return Cell::_allcells.contains(cell);
    #     }

    #     //! Get a named cell, returns empty cell if it does not exist, so you should check
    #     //! that the cell exists in this cell first
    #     static Cell* getCell(QString cell){
    #         if(Cell::_allcells.contains(cell)){
    #             return Cell::_allcells[cell];
    #         }else{
    #             Cell * c = new Cell();
    #             return c;
    #         }
    #     }

    #     //! Get a list of all cells in this design
    #     static QList<Cell*> getAllCells(){
    #         QList<Cell*> cells;
    #         foreach(Cell * cell,_allcells){
    #             cells.append(cell);
    #         }
    #         return cells;
    #     }

    #     //! Add a cell to the list of all cells
    #     static Cell* addCell(QString cell,Cell * c){
    #         Cell::_allcells[cell] = c;
    #         return c;
    #     }

    #     //! Add a cell, and use the cell->name() as key
    #     static Cell* addCell(Cell *c){
    #         Cell::_allcells[c->name()] = c;
    #         return c;
    #     }

  

    #     //! Find all rectangles by regular expression
    #     virtual QList<Rect *> findRectanglesByRegex(QString regex,QString layer);
    #     virtual void findRectangles(QList<Rect*> &rects,QString name,QString layer);
    #     virtual QList<Rect *> findAllRectangles(QString regex, QString layer);

    #     QJsonObject toJson();
    #     void fromJson(QJsonObject o);
    #     QList<Rect*> getChildren(QString type);
        
    #     void addEnclosingLayers(QList<QString> layers);
        

    # protected:
    #     QList<Rect*> routes_;
    #     //! List of all cells
    #     static QMap<QString,Cell*> _allcells;

    #     //! Ports in this cell
    #     QMap<QString,Port*> ports_;

    #     QList<QString> allPortNames_;
        
    #     QMap<QString,QList<Port*>> allports_;

    #     //! Named Rects in this cell
    #     QMap<QString,Rect*> named_rects_;

    #     //! SPICE subcircuit related to this cell
    #     cIcSpice::Subckt * _subckt;

    #     //! Find bottom left rectangle in the cell
    #     Rect* getBottomLeftRect();
    #     //! Find top left rectangle in the cell
    #     Rect* getTopLeftRect();

    #     //! Children of this cell
    #     QList<Rect*> _children;
    #     QMap<QString,QList<Rect*>> children_by_type;
        

    # protected:
    #     QString instanceName_;
    #     bool boundaryIgnoreRouting_;
    #     bool _has_pr;        

    # private:
    #     //! Cell name
    #     QString _name;
    #     bool _physicalOnly;



    # signals:

    # public slots:
    #     void updateBoundingRect();
