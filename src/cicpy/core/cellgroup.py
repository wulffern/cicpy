#!/usr/bin/env python3

import re

from .cell import Cell


class _PhysicalInst:
    def __init__(self, name, subckt_name):
        self.name = name
        self.subcktName = subckt_name


class StackGroup(Cell):
    def __init__(self, layout, name):
        super().__init__(name)
        self.layout = layout
        self.instances = []
        self.tap_instances = []

    def _members(self):
        members = []
        seen = set()
        for obj in self.instances + self.tap_instances:
            if obj is None:
                continue
            oid = id(obj)
            if oid in seen:
                continue
            seen.add(oid)
            members.append(obj)
        return members

    def translate(self, dx, dy):
        for obj in self._members():
            obj.translate(dx, dy)
        self.updateBoundingRect()
        self.emit_updated()

    def addInstance(self, inst):
        if inst not in self.instances:
            self.instances.append(inst)
        self.add(inst)
        self.updateBoundingRect()
        return inst

    def addInstances(self, instances):
        for inst in instances:
            self.addInstance(inst)
        self.updateBoundingRect()
        return self

    def sort(self):
        self.instances = sorted(self.instances, key=lambda inst: (inst.y1, inst.x1, inst.instanceName))
        self.updateBoundingRect()
        return self

    def calcBoundingRect(self):
        members = self._members()
        if not members:
            return super().calcBoundingRect()
        return Cell.calcBoundingRectFromList(members, False)

    def height(self):
        if not self.instances:
            return 0
        self.sort()
        return self.instances[-1].y2 - self.instances[0].y1

    def width(self):
        if not self.instances:
            return 0
        self.sort()
        return max(inst.width() for inst in self.instances)

    def left(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.x1

    def bottom(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.y1

    def top(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.y2

    def stack(self, x=None, y=None, ygap=0):
        if not self.instances:
            return self
        self.sort()
        if x is None:
            x = self.left()
        if y is None:
            y = self.bottom()
        ypos = int(y)
        for inst in self.instances:
            inst.moveTo(int(x), ypos)
            ypos = int(inst.y2 + ygap)
        self.updateBoundingRect()
        return self

    def right(self):
        if not self._members():
            return 0
        self.updateBoundingRect()
        return self.x2

    def abutBottom(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.left() - self.left())
        dy = int(other.bottom() - space - self.top())
        self.translate(dx, dy)
        return self

    def abutTop(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.left() - self.left())
        dy = int(other.top() + space - self.bottom())
        self.translate(dx, dy)
        return self

    def abutLeft(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.left() - space - self.right())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    def abutRight(self, other, space=0):
        if not self._members():
            return self
        dx = int(other.right() + space - self.left())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    # Compatibility aliases
    def moveBelow(self, other, ygap=0):
        return self.abutBottom(other, ygap)

    def moveAbove(self, other, ygap=0):
        return self.abutTop(other, ygap)

    def _tap_name(self, cell_name, suffix):
        return re.sub(r"C\d+F\d+$", suffix, cell_name)

    def addTaps(self, prefix=None):
        if not self.instances:
            return self
        self.sort()
        base = self.instances[0]
        bot_cell = self._tap_name(base.cell, "CTAPBOT")
        top_cell = self._tap_name(base.cell, "CTAPTOP")
        if bot_cell == base.cell or top_cell == base.cell:
            return self
        name = prefix or self.name
        bot = self.layout.addPhysicalInstance(bot_cell, f"xstack_{name}_bot", int(base.x1), int(base.y1 - 24000))
        top = self.layout.addPhysicalInstance(top_cell, f"xstack_{name}_top", int(base.x1), int(self.instances[-1].y2))
        if bot is not None and bot not in self.tap_instances:
            self.tap_instances.append(bot)
            self.add(bot)
        if top is not None and top not in self.tap_instances:
            self.tap_instances.append(top)
            self.add(top)
        self.updateBoundingRect()
        return self

    def fillDummyTransistors(self, target_height):
        if not self.instances:
            return self
        self.sort()
        current_height = self.height()
        if current_height >= target_height:
            return self
        base = self.instances[0]
        dummy_index = 0
        ypos = int(self.top())
        while current_height < target_height:
            dname = f"xfill_{self.name}_{dummy_index}"
            dummy = self.layout.addPhysicalInstance(base.cell, dname, int(base.x1), ypos)
            if dummy is None:
                break
            self.addInstance(dummy)
            ypos = int(dummy.y2)
            current_height = self.height()
            dummy_index += 1
        self.sort()
        self.updateBoundingRect()
        return self


class CellGroup(Cell):
    def __init__(self, layout, name):
        super().__init__(name)
        self.layout = layout
        self.stacks = []

    def addStack(self, name, instances):
        stack = StackGroup(self.layout, name)
        stack.addInstances(instances)
        self.stacks.append(stack)
        self.add(stack)
        self.updateBoundingRect()
        return stack

    def calcBoundingRect(self):
        if not self.stacks:
            return super().calcBoundingRect()
        active = [stack for stack in self.stacks if stack.instances]
        if not active:
            return super().calcBoundingRect()
        return Cell.calcBoundingRectFromList(active, False)

    def left(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.x1

    def right(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.x2

    def bottom(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.y1

    def top(self):
        if not self.stacks:
            return 0
        self.updateBoundingRect()
        return self.y2

    def abutTop(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.left() - self.left())
        dy = int(other.top() + space - self.bottom())
        self.translate(dx, dy)
        return self

    def abutBottom(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.left() - self.left())
        dy = int(other.bottom() - space - self.top())
        self.translate(dx, dy)
        return self

    def abutLeft(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.left() - space - self.right())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    def abutRight(self, other, space=0):
        if not self.stacks:
            return self
        dx = int(other.right() + space - self.left())
        dy = int(other.bottom() - self.bottom())
        self.translate(dx, dy)
        return self

    # Compatibility aliases
    def moveAbove(self, other, ygap=0):
        return self.abutTop(other, ygap)

    def moveBelow(self, other, ygap=0):
        return self.abutBottom(other, ygap)

    def fillDummyTransistors(self):
        if not self.stacks:
            return self
        target_height = max(stack.height() for stack in self.stacks)
        for stack in self.stacks:
            stack.fillDummyTransistors(target_height)
        self.updateBoundingRect()
        return self
