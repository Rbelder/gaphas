"""
Test all the tools provided by gaphas.
"""

import unittest

from gaphas.tool import ConnectHandleTool, LineSegmentTool
from gaphas.canvas import Canvas
from gaphas.examples import Box
from gaphas.item import Item, Element, Line
from gaphas.view import View, GtkView
from gaphas.constraint import LineConstraint
from gaphas.canvas import Context
from gaphas import state

Event = Context

undo_list = []
redo_list = []


def undo_handler(event):
    undo_list.append(event)


def undo():
    apply_me = list(undo_list)
    del undo_list[:]
    apply_me.reverse()
    for e in apply_me:
        state.saveapply(*e)
    redo_list[:] = undo_list[:]
    del undo_list[:]


def simple_canvas(self):
    """
    This decorator adds view, canvas and handle connection tool to a test
    case. Two boxes and a line are added to the canvas as well.
    """
    self.canvas = Canvas()

    self.box1 = Box()
    self.canvas.add(self.box1)
    self.box1.matrix.translate(100, 50)
    self.box1.width = 40 
    self.box1.height = 40 
    self.box1.request_update()

    self.box2 = Box()
    self.canvas.add(self.box2)
    self.box2.matrix.translate(100, 150)
    self.box2.width = 50 
    self.box2.height = 50 
    self.box2.request_update()

    self.line = Line()
    self.head = self.line.handles()[0]
    self.tail = self.line.handles()[-1]
    self.tail.pos = 100, 100
    self.canvas.add(self.line)

    self.canvas.update_now()
    self.view = GtkView()
    self.view.canvas = self.canvas
    import gtk
    win = gtk.Window()
    win.add(self.view)
    self.view.show()
    self.view.update()
    win.show()

    self.tool = ConnectHandleTool()



class TestCaseBase(unittest.TestCase):
    """
    Abstract test case class with undo support.
    """
    def setUp(self):
        state.observers.add(state.revert_handler)
        state.subscribers.add(undo_handler)

    def tearDown(self):
        state.observers.remove(state.revert_handler)
        state.subscribers.remove(undo_handler)



class ConnectHandleToolGlueTestCase(unittest.TestCase):
    """
    Test handle connection tool glue method.
    """

    def setUp(self):
        simple_canvas(self)


    def test_item_and_port_glue(self):
        """Test glue operation to an item and its ports"""

        ports = self.box1.ports()

        # glue to port nw-ne
        item, port = self.tool.glue(self.view, self.line, self.head, (120, 50))
        self.assertEquals(item, self.box1)
        self.assertEquals(ports[0], port)

        # glue to port ne-se
        item, port = self.tool.glue(self.view, self.line, self.head, (140, 70))
        self.assertEquals(item, self.box1)
        self.assertEquals(ports[1], port)

        # glue to port se-sw
        item, port = self.tool.glue(self.view, self.line, self.head, (120, 90))
        self.assertEquals(item, self.box1)
        self.assertEquals(ports[2], port)

        # glue to port sw-nw
        item, port = self.tool.glue(self.view, self.line, self.head, (100, 70))
        self.assertEquals(item, self.box1)
        self.assertEquals(ports[3], port)
        

    def test_failed_glue(self):
        """Test glue from too far distance"""
        item, port = self.tool.glue(self.view, self.line, self.head, (90, 50))
        self.assertTrue(item is None)
        self.assertTrue(port is None)


    def test_glue_call_can_glue_once(self):
        """Test if glue method calls can glue once only

        Box has 4 ports. Every port is examined once per
        ConnectHandleTool.glue method call. The purpose of this test is to
        assure that ConnectHandleTool.can_glue is called once (for the
        found port), it cannot be called four times (once for every port).
        """

        # count ConnectHandleTool.can_glue calls
        class Tool(ConnectHandleTool):
            def __init__(self, *args):
                super(Tool, self).__init__(*args)
                self._calls = 0
                
            def can_glue(self, *args):
                self._calls += 1
                return True

        tool = Tool()
        item, port = tool.glue(self.view, self.line, self.head, (120, 50))
        assert item and port
        self.assertEquals(1, tool._calls)


    def test_glue_cannot_glue(self):
        """Test if glue method respects ConnectHandleTool.can_glue method"""

        class Tool(ConnectHandleTool):
            def can_glue(self, *args):
                return False

        tool = Tool()
        item, port = tool.glue(self.view, self.line, self.head, (120, 50))
        self.assertTrue(item is None)
        self.assertTrue(port is None)


    def test_glue_no_port_no_can_glue(self):
        """Test if glue method does not call ConnectHandleTool.can_glue method when port is not found"""

        class Tool(ConnectHandleTool):
            def __init__(self, *args):
                super(Tool, self).__init__(*args)
                self._calls = 0

            def can_glue(self, *args):
                self._calls += 1

        tool = Tool()
        # at 300, 50 there should be no item
        item, port = tool.glue(self.view, self.line, self.head, (300, 50))
        assert item is None and port is None
        self.assertEquals(0, tool._calls)



class ConnectHandleToolConnectTestCase(unittest.TestCase):

    def setUp(self):
        simple_canvas(self)


    def _get_line(self):
        line = Line()
        head = self.line.handles()[0]
        self.canvas.add(line)
        return line, head


    def test_connect(self):
        """Test connection to an item"""
        line, head = self._get_line()
        self.tool.connect(self.view, line, head, (120, 50))
        self.assertEquals(self.box1, head.connected_to)
        self.assertTrue(head.connection_data is not None)
        self.assertTrue(isinstance(head.connection_data, LineConstraint))
        self.assertTrue(head.disconnect is not None)

        line, head = self._get_line()
        self.tool.connect(self.view, line, head, (90, 50))
        self.assertTrue(head.connected_to is None)
        self.assertTrue(head.connection_data is None)


    def test_disconnect(self):
        """Test disconnection from an item"""
        line, head = self._get_line()
        self.tool.connect(self.view, line, head, (120, 50))
        assert head.connected_to is not None

        self.tool.disconnect(self.view, line, head)
        self.assertTrue(head.connected_to is None)
        self.assertTrue(head.connection_data is None)


    def test_reconnect_another(self):
        """Test reconnection to another item"""
        line, head = self._get_line()
        self.tool.connect(self.view, line, head, (120, 50))
        assert head.connected_to is not None
        item = head.connected_to
        constraint = head.connection_data

        assert item == self.box1
        assert item != self.box2

        # connect to box2, handle's connected item and connection data
        # should differ
        self.tool.connect(self.view, line, head, (120, 150))
        assert head.connected_to is not None
        self.assertEqual(self.box2, head.connected_to)
        self.assertNotEqual(item, head.connected_to)
        self.assertNotEqual(constraint, head.connection_data)


    def test_reconnect_same(self):
        """Test reconnection to same item"""
        line, head = self._get_line()
        self.tool.connect(self.view, line, head, (120, 50))
        assert head.connected_to is not None
        item = head.connected_to
        constraint = head.connection_data

        assert item == self.box1
        assert item != self.box2

        # connect to box1 again, handle's connected item should be the same
        # but connection constraint will differ
        connected = self.tool.connect(self.view, line, head, (120, 50))
        assert head.connected_to is not None
        self.assertEqual(self.box1, head.connected_to)
        self.assertNotEqual(constraint, head.connection_data)


    def test_find_port(self):
        """Test finding a port
        """
        line, head = self._get_line()
        p1, p2, p3, p4 = self.box1.ports()

        head.pos = 110, 50
        port = self.tool.find_port(line, head, self.box1)
        self.assertEquals(p1, port)

        head.pos = 140, 60
        port = self.tool.find_port(line, head, self.box1)
        self.assertEquals(p2, port)

        head.pos = 110, 95
        port = self.tool.find_port(line, head, self.box1)
        self.assertEquals(p3, port)

        head.pos = 100, 55
        port = self.tool.find_port(line, head, self.box1)
        self.assertEquals(p4, port)



class LineSegmentToolTestCase(unittest.TestCase):
    """
    Line segment tool tests.
    """
    def setUp(self):
        simple_canvas(self)

    def test_split(self):
        """Test splitting line
        """
        tool = LineSegmentTool()
        def dummy_grab(): pass

        context = Context(view=self.view,
                grab=dummy_grab,
                ungrab=dummy_grab)

        head, tail = self.line.handles()

        self.view.hovered_item = self.line
        self.view.focused_item = self.line
        tool.on_button_press(context, Event(x=50, y=50, state=0))
        self.assertEquals(3, len(self.line.handles()))
        self.assertEquals(self.head, head)
        self.assertEquals(self.tail, tail)

        #tool.on_motion_notify(context, Event(x=200, y=200, state=0xffff))
        #tool.on_button_release(context, Event(x=200, y=200, state=0))


    def test_constraints_after_split(self):
        """Test if constraints are recreated after line split
        """
        tool = LineSegmentTool()
        def dummy_grab(): pass

        context = Context(view=self.view,
                grab=dummy_grab,
                ungrab=dummy_grab)

        # connect line2 to self.line
        line2 = Line()
        self.canvas.add(line2)
        head = line2.handles()[0]
        self.tool.connect(self.view, line2, head, (25, 25))
        self.assertEquals(self.line, head.connected_to)

        self.view.hovered_item = self.line
        self.view.focused_item = self.line
        tool.on_button_press(context, Event(x=50, y=50, state=0))
        assert len(self.line.handles()) == 3
        h1, h2, h3 = self.line.handles()

        # connection shall be reconstrained between 1st and 2nd handle
        c1 = head.connection_data
        self.assertEquals(c1._line[0]._point, h1.pos)
        self.assertEquals(c1._line[1]._point, h2.pos)


    def test_merge(self):
        """Test line merging
        """
        tool = LineSegmentTool()
        def dummy_grab(): pass

        context = Context(view=self.view,
                grab=dummy_grab,
                ungrab=dummy_grab)

        self.view.hovered_item = self.line
        self.view.focused_item = self.line
        tool.on_button_press(context, Event(x=50, y=50, state=0))
        # start with 2 segments
        assert len(self.line.handles()) == 3

        # try to merge, now
        tool.on_button_release(context, Event(x=0, y=0, state=0))
        self.assertEquals(2, len(self.line.handles()))


    def test_constraints_after_merge(self):
        """Test if constraints are recreated after line merge
        """
        tool = LineSegmentTool()
        def dummy_grab(): pass

        context = Context(view=self.view,
                grab=dummy_grab,
                ungrab=dummy_grab)

        # connect line2 to self.line
        line2 = Line()
        self.canvas.add(line2)
        head = line2.handles()[0]
        self.tool.connect(self.view, line2, head, (25, 25))
        self.assertEquals(self.line, head.connected_to)

        self.view.hovered_item = self.line
        self.view.focused_item = self.line
        tool.on_button_press(context, Event(x=50, y=50, state=0))
        assert len(self.line.handles()) == 3
        c1 = head.connection_data

        tool.on_button_release(context, Event(x=0, y=0, state=0))
        assert len(self.line.handles()) == 2

        h1, h2 = self.line.handles()
        # connection shall be reconstrained between 1st and 2nd handle
        c2 = head.connection_data
        self.assertEquals(c2._line[0]._point, h1.pos)
        self.assertEquals(c2._line[1]._point, h2.pos)
        self.assertFalse(c1 == c2)


    def test_merged_segment(self):
        """Test if proper segment is merged
        """
        tool = LineSegmentTool()
        def dummy_grab(): pass

        context = Context(view=self.view,
                grab=dummy_grab,
                ungrab=dummy_grab)

        self.view.hovered_item = self.line
        self.view.focused_item = self.line
        tool.on_button_press(context, Event(x=50, y=50, state=0))
        tool.on_button_press(context, Event(x=75, y=75, state=0))
        # start with 3 segments
        assert len(self.line.handles()) == 4

        # ports to be removed
        port1 = self.line.ports()[0]
        port2 = self.line.ports()[1]

        # try to merge, now
        tool.grab_handle(self.line, self.line.handles()[1])
        tool.on_button_release(context, Event(x=0, y=0, state=0))
        # check if line merging was performed
        assert len(self.line.handles()) == 3
        
        # check if proper segments were merged
        self.assertFalse(port1 in self.line.ports())
        self.assertFalse(port2 in self.line.ports())



class LineSplitTestCase(TestCaseBase):
    """
    Tests for line splitting.
    """
    def test_split_single(self):
        """Test single line splitting
        """
        line = Line()
        line.handles()[1].pos = (20, 0)

        # we start with two handles and one port, after split 3 handles are
        # expected and 2 ports
        assert len(line.handles()) == 2
        assert len(line.ports()) == 1

        old_port = line.ports()[0]

        tool = LineSegmentTool()
        
        handles, ports = tool.split_segment(line, 0)
        handle = handles[0]
        self.assertEquals(1, len(handles))
        self.assertEquals((10, 0), handle.pos)
        self.assertEquals(3, len(line.handles()))
        self.assertEquals(2, len(line.ports()))

        # new handle is between old handles
        self.assertEquals(handle, line.handles()[1])
        # and old port is deleted
        self.assertTrue(old_port not in line.ports())

        # check ports order
        p1, p2 = line.ports()
        h1, h2, h3 = line.handles()
        self.assertEquals(h1.pos, p1.start)
        self.assertEquals(h2.pos, p1.end)
        self.assertEquals(h2.pos, p2.start)
        self.assertEquals(h3.pos, p2.end)


    def test_split_multiple(self):
        """Test multiple line splitting
        """
        line = Line()
        line.handles()[1].pos = (20, 16)
        handles = line.handles()
        old_ports = line.ports()[:]

        # start with two handles, split into 4 segments - 3 new handles to
        # be expected
        assert len(handles) == 2
        assert len(old_ports) == 1

        tool = LineSegmentTool()

        handles, ports = tool.split_segment(line, 0, count=4)
        self.assertEquals(3, len(handles))
        h1, h2, h3 = handles
        self.assertEquals((5, 4), h1.pos)
        self.assertEquals((10, 8), h2.pos)
        self.assertEquals((15, 12), h3.pos)

        # new handles between old handles
        self.assertEquals(5, len(line.handles()))
        self.assertEquals(h1, line.handles()[1])
        self.assertEquals(h2, line.handles()[2])
        self.assertEquals(h3, line.handles()[3])

        self.assertEquals(4, len(line.ports()))

        # and old port is deleted
        self.assertTrue(old_ports[0] not in line.ports())

        # check ports order
        p1, p2, p3, p4 = line.ports()
        h1, h2, h3, h4, h5 = line.handles()
        self.assertEquals(h1.pos, p1.start)
        self.assertEquals(h2.pos, p1.end)
        self.assertEquals(h2.pos, p2.start)
        self.assertEquals(h3.pos, p2.end)
        self.assertEquals(h3.pos, p3.start)
        self.assertEquals(h4.pos, p3.end)
        self.assertEquals(h4.pos, p4.start)
        self.assertEquals(h5.pos, p4.end)


    def test_ports_after_split(self):
        """Test ports removal after split
        """
        line = Line()
        line.handles()[1].pos = (20, 16)

        tool = LineSegmentTool()

        tool.split_segment(line, 0)
        handles = line.handles()
        old_ports = line.ports()[:]

        # start with 3 handles and two ports
        assert len(handles) == 3
        assert len(old_ports) == 2

        # do split of first segment again
        # first port should be deleted, but 2nd one should remain untouched
        tool.split_segment(line, 0)
        self.assertFalse(old_ports[0] in line.ports())
        self.assertEquals(old_ports[1], line.ports()[2])


    def test_split_undo(self):
        """Test line splitting undo
        """
        line = Line()
        line.handles()[1].pos = (20, 0)

        # we start with two handles and one port, after split 3 handles and
        # 2 ports are expected
        assert len(line.handles()) == 2
        assert len(line.ports()) == 1

        tool = LineSegmentTool()
        tool.split_segment(line, 0)
        assert len(line.handles()) == 3
        assert len(line.ports()) == 2

        # after undo, 2 handles and 1 port are expected again
        undo()
        self.assertEquals(2, len(line.handles()))
        self.assertEquals(1, len(line.ports()))


    def test_orthogonal_line_split(self):
        """Test orthogonal line splitting
        """
        canvas = Canvas()
        line = Line()
        line.handles()[-1].pos = 100, 100
        canvas.add(line)

        # start with no orthogonal constraints
        assert len(canvas.solver._constraints) == 0

        line.orthogonal = True

        # check orthogonal constraints
        assert len(canvas.solver._constraints) == 2
        assert len(line.handles()) == 3

        line.split_segment(0)

        # 4 handles and 3 ports are expected
        # 3 constraints keep the line orthogonal
        self.assertEquals(3, len(canvas.solver._constraints))
        self.assertEquals(4, len(line.handles()))
        self.assertEquals(3, len(line.ports()))


    def test_params_errors(self):
        """Test parameter error exceptions
        """
        tool = LineSegmentTool()

        # there is only 1 segment
        line = Line()
        self.assertRaises(ValueError, tool.split_segment, line, -1)

        line = Line()
        self.assertRaises(ValueError, tool.split_segment, line, 1)

        line = Line()
        # can't split into one or less segment :)
        self.assertRaises(ValueError, tool.split_segment, line, 0, 1)



class LineMergeTestCase(TestCaseBase):
    """
    Tests for line merging.
    """
    def test_merge_first_single(self):
        """Test single line merging starting from 1st segment
        """
        tool = LineSegmentTool()
        line = Line()
        line.handles()[1].pos = (20, 0)
        tool.split_segment(line, 0)

        # we start with 3 handles and 2 ports, after merging 2 handles and
        # 1 port are expected
        assert len(line.handles()) == 3
        assert len(line.ports()) == 2
        old_ports = line.ports()[:]

        handles, ports = tool.merge_segment(line, 0)
        # deleted handles and ports
        self.assertEquals(1, len(handles))
        self.assertEquals(2, len(ports))
        # handles and ports left after segment merging
        self.assertEquals(2, len(line.handles()))
        self.assertEquals(1, len(line.ports()))

        self.assertTrue(handles[0] not in line.handles())
        self.assertTrue(ports[0] not in line.ports())
        self.assertTrue(ports[1] not in line.ports())

        # old ports are completely removed as they are replaced by new one
        # port
        self.assertEquals(old_ports, ports)

        # finally, created port shall span between first and last handle
        port = line.ports()[0]
        self.assertEquals((0, 0), port.start)
        self.assertEquals((20, 0), port.end)


    def test_merge_multiple(self):
        """Test multiple line merge
        """
        tool = LineSegmentTool()
        line = Line()
        line.handles()[1].pos = (20, 16)
        tool.split_segment(line, 0, count=3)
 
        # start with 4 handles and 3 ports, merge 3 segments
        assert len(line.handles()) == 4
        assert len(line.ports()) == 3
 
        print line.handles()
        handles, ports = tool.merge_segment(line, 0, count=3)
        self.assertEquals(2, len(handles))
        self.assertEquals(3, len(ports))
        self.assertEquals(2, len(line.handles()))
        self.assertEquals(1, len(line.ports()))

        self.assertTrue(set(handles).isdisjoint(set(line.handles())))
        self.assertTrue(set(ports).isdisjoint(set(line.ports())))

        # finally, created port shall span between first and last handle
        port = line.ports()[0]
        self.assertEquals((0, 0), port.start)
        self.assertEquals((20, 16), port.end)

 
    def test_merge_undo(self):
        """Test line merging undo
        """
        tool = LineSegmentTool()

        line = Line()
        line.handles()[1].pos = (20, 0)

        # split for merging
        tool.split_segment(line, 0)
        assert len(line.handles()) == 3
        assert len(line.ports()) == 2

        # clear undo stack before merging
        del undo_list[:]
 
        # merge with empty undo stack
        tool.merge_segment(line, 0)
        assert len(line.handles()) == 2
        assert len(line.ports()) == 1
 
        # after merge undo, 3 handles and 2 ports are expected again
        undo()
        self.assertEquals(3, len(line.handles()))
        self.assertEquals(2, len(line.ports()))
 
 
    def test_orthogonal_line_merge(self):
        """Test orthogonal line merging
        """
        tool = LineSegmentTool()
        canvas = Canvas()
        line = Line()
        line.handles()[-1].pos = 100, 100
        canvas.add(line)

        # prepare the line for merging
        line.orthogonal = True
        tool.split_segment(line, 0)

        assert len(canvas.solver._constraints) == 3
        assert len(line.handles()) == 4 
        assert len(line.ports()) == 3 

        # test the merging
        line.merge_segment(0)

        self.assertEquals(2, len(canvas.solver._constraints))
        self.assertEquals(3, len(line.handles()))
        self.assertEquals(2, len(line.ports()))

 
    def test_params_errors(self):
        """Test parameter error exceptions
        """
        tool = LineSegmentTool()

        line = Line()
        tool.split_segment(line, 0)
        # no segment -1
        self.assertRaises(ValueError, tool.merge_segment, line, -1)
 
        line = Line()
        tool.split_segment(line, 0)
        # no segment no 2
        self.assertRaises(ValueError, tool.merge_segment, line, 2)
 
        line = Line()
        tool.split_segment(line, 0)
        # can't merge one or less segments :)
        self.assertRaises(ValueError, tool.merge_segment, line, 0, 1)
 
        line = Line()
        # can't merge line with one segment
        self.assertRaises(ValueError, tool.merge_segment, line, 0)

        line = Line()
        tool.split_segment(line, 0)
        # 2 segments: no 0 and 1. cannot merge as there are no segments
        # after segment no 1
        self.assertRaises(ValueError, tool.merge_segment, line, 1)

        line = Line()
        tool.split_segment(line, 0)
        # 2 segments: no 0 and 1. cannot merge 3 segments as there are no 3
        # segments
        self.assertRaises(ValueError, tool.merge_segment, line, 0, 3)


# vim: sw=4:et:ai
