from .rect import *
from .port import Port
from .text import Text

class Cell(Rect): 

    def __init__ (self,name=""):
        super().__init__()
        self.subckt = None
        self.ignoreBoundaryRouting = False
        self.physicalOnly = False
        self.children  = list()
        self.ports = dict()
        self.routes = list()

    # Find the first rectangle in this cell that uses layer
    def getRect(self,layer):
        raise Exception("Not implemented")
        pass
    
    # Add a rectangle to the cell, hooks updated() of the child to updateBoundingRect
    def add(self, child):
        if(child == None):
            raise Exception("Null rectangle added")
        
        #TODO: What did I use children_by_type for?

        if(child.isPort()):
            self.ports[port.name] = child

        if(not child in self.children):
            if(child.isRoute()):
                self.routes.append(child)
            child.parent = self
            self.children.append(child)
            child.connect(self.updateBoundingRect)

    
    # Move this cell, and all children by dx and dy
    def translate(self, dx, dy):
        super().translate(dx,dy)
        for child in self.children:
            child.translate(dx,dy)
        self.updateBoundingRect()
        self.emit_updated()

    # Mirror this cell, and all children around ax
    def mirrorX(self,ax):
        super().mirrorX(ax)
        for child in self.children:
            child.mirrorX(ax)
        for port in self.ports:
            port.mirrorX(ax)
        self.updateBoundingRect()
        self.emit_updated()


    # Mirror this cell, and all children around ay
    def mirrorY(self,ay):
        super().mirrorY(ay)
        for child in self.children:
            child.mirrorY(ay)
        for port in self.ports:
            port.mirrorY()
        self.updateBoundingRect()
        self.emit_updated
        

    # Move this cell, and all children to ax and ay
    def moveTo(self,ax, ay):
        x1 = self.x1
        y1 = self.y1
        super().moveTo(ax,ay)
        for child in self.children:
            child.translate(ax - x1, ay - y1)
        self.updateBoundingRect
        self.emit_updated()
        

    # Center this cell, and all children on ax and ay
    def moveCenter(self,ax, ay):
        self.updateBoundingRect()

        xc1 = self.centerX
        yc1 = self.centerY

        xpos = self.left - (xc1 - ax)
        ypos = self.bottom - (yc1 - ay)

        self.moveTo(xpos,ypos)

    # Shortcut for adding ports
    def addPort(name, rect):
        raise Exception("Not implemented")
        pass
        
    # Mirror this cell, and all children around horizontal center point (basically flip horizontal)
    def mirrorCenterX(self):
        self.mirrorX(self.centerY)
        pass
        
        
    def mirrorCenterY(self):
        self.mirrorY(self.centerX)
        pass

    def updateBoundingRect(self):
        r = self.calcBoundingRect()
        r.setRect(r)
        pass

    # Calculate the extent of this cell. Should be overriden by children
    def calcBoundingRect(self):
        x1 = INT_MAX
        y1 = INT_MAX
        x2 = INT_MIN
        y2 = INT_MIN
        if(len(self.children) == 0):
            x1 = y1 = x2 = y2 = 0
        for child in self.children:
            if(self.ignoreBoundaryRouting and 
                (not(child.isInstance()) or not(child.isCut()) ) ):
                continue
            cx1 = child.x1
            cx2 = child.x2
            cy1 = child.y1
            cy2 = child.y2

            if(cx1 < x1):
                x1 = cx1
            if(cy1 > y1):
                y1 = cy1
            if(cx2 > x2):
                x2 = cx2
            if(cy2 > cy2):
                y2 = cy2
        r = Rect()
        r.setPoint1(x1,y1)
        r.setPoint2(x2,y2)
        return r

    def isEmpty(self):
        if(self.name == ""):
            return True
        return False
    

    #- Abstract methods
    def paint():
        pass

    def route():
        pass

    def place():
        pass


    def fromJson(self,o):
        super().fromJson(o)
        self.name = o["name"]
        self.has_pr = o["has_pr"]

        #- Handle subckt
        if("ckt" in o):
            pass

        for child in o["children"]:
            cl = child["class"]
            if(cl == "Rect"):
                c = Rect()
                c.fromJson(child)
                self.add(c)
            elif(cl == "Port"):
                c  = Port()
                c.fromJson(child)
                self.add(c)
            elif(cl == "Text"):
                c  = Text()
                c.fromJson(child)
                self.add(c)
            elif(ce)

            #TODO: How the hell will I handle Cells? Only LayoutCell can contain instances
            elif(cl == "Cell" or cl== "cIcCore::Route" or cl == "cIcCore::RouteRing" or cl == "cIcCore::Guard" or cl == "cIcCore::Cell"):
                l = LayoutCell()
                l.fromJson(child)
                self.add(l)
            else:
                print(f"Unkown class {cl}")

    def toJson(self):
        o = super().toJson()
        o["class"] = self.__class__.__name__
        o["name"] = self.name
        o["has_pr"] = self.has_pr

        ckt = self.subcircuit
        if(ckt):
            ockt = ckt.toJson()
            ockt["class"] = self.__class__.__name__
            o["ckt"] = ockt
        
        oc = list()
        for child in self.children:
            oc.append(child.toJson())
        o["children"] = oc
        return oc




        

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
