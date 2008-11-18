"""
Basic items.
"""

__version__ = "$Revision$"
# $HeadURL$

from math import atan2
from weakref import WeakKeyDictionary

from matrix import Matrix
from geometry import distance_line_point, distance_rectangle_point
from gaphas.connector import Handle, LinePort
from solver import solvable, WEAK, NORMAL, STRONG, VERY_STRONG
from constraint import EqualsConstraint, LessThanConstraint, LineConstraint, LineAlignConstraint
from state import observed, reversible_method, reversible_pair, reversible_property, disable_dispatching

class Item(object):
    """
    Base class (or interface) for items on a canvas.Canvas.

    Attributes:

    - matrix: item's transformation matrix
    - canvas: canvas, which owns an item
    - constraints: list ofitem constraints, automatically registered
      when the item is added to a canvas; may be extended in subclasses

    Private:

    - _canvas:      canvas, which owns an item
    - _handles:     list of handles owned by an item
    - _ports:       list of ports, connectable areas of an item
    - _matrix_i2c:  item to canvas coordinates matrix
    - _matrix_c2i:  canvas to item coordinates matrix
    - _matrix_i2v:  item to view coordinates matrices
    - _matrix_v2i:  view to item coordinates matrices
    - _sort_key:  used to sort items
    """

    def __init__(self):
        self._canvas = None
        self._matrix = Matrix()
        self._handles = []
        self._constraints = []
        self._ports = []

        # used by gaphas.canvas.Canvas to hold conversion matrices
        self._matrix_i2c = None
        self._matrix_c2i = None

        # used by gaphas.view.GtkView to hold item 2 view matrices (view=key)
        self._matrix_i2v = WeakKeyDictionary()
        self._matrix_v2i = WeakKeyDictionary()


    # _set_canvas() is not observed, since this operation is initialized by
    # Canvas.add() and Canvas.remove()
    #@observed
    def _set_canvas(self, canvas):
        """
        Set the canvas. Should only be called from Canvas.add and
        Canvas.remove().
        """
        assert not canvas or not self._canvas or self._canvas is canvas
        if self._canvas:
            self.teardown_canvas()
        self._canvas = canvas
        if canvas:
            self.setup_canvas()

    canvas = reversible_property(lambda s: s._canvas,
                doc="Canvas owning this item")

    constraints = property(lambda s: s._constraints,
                doc="Item constraints")

    def setup_canvas(self):
        """
        Called when the canvas is set for the item.
        This method can be used to create constraints.
        """
        add = self.canvas.solver.add_constraint
        for c in self._constraints:
            add(c)


    def teardown_canvas(self):
        """
        Called when the canvas is unset for the item.
        This method can be used to dispose constraints.
        """
        for h in self.handles():
            h.disconnect()

        remove = self.canvas.solver.remove_constraint
        for c in self._constraints:
            remove(c)


    @observed
    def _set_matrix(self, matrix):
        """
        Set the conversion matrix (parent -> item)
        """
        if not isinstance(matrix, Matrix):
            matrix = Matrix(*matrix)
        self._matrix = matrix

    matrix = reversible_property(lambda s: s._matrix, _set_matrix)


    def request_update(self, update=True, matrix=True):
        if self._canvas:
            self._canvas.request_update(self, update=update, matrix=matrix)


    def pre_update(self, context):
        """
        Perform any changes before item update here, for example:

        - change matrix
        - move handles

        Gaphas does not guarantee that any canvas invariant is valid at
        this point (i.e. constraints are not solved, first handle is not in
        position (0, 0), etc).
        """
        pass


    def post_update(self, context):
        """
        Method called after item update.

        If some variables should be used during drawing or in another
        update, then they should be calculated in post method.

        Changing matrix or moving handles programmatically is really not
        advised to be performed here.

        All canvas invariants are true.
        """
        pass

    def draw(self, context):
        """
        Render the item to a canvas view.
        Context contains the following attributes:

        - cairo: the Cairo Context use this one to draw
        - view: the view that is to be rendered to
        - selected, focused, hovered, dropzone: view state of items (True/False)
        - draw_all: a request to draw everything, for bounding box calculations
        """
        pass

    
    def constraint(self, handle, horizontal=None, vertical=None, line=None, delta=0.0, align=None):
        """
        Utility method to create item's constraint.
        """
        constraint = None
        if horizontal:
            pass
        elif vertical:
            pass
        elif len(line) == 2:
            point = handle.pos
            line = line[0].pos, line[1].pos
            if align is None:
                constraint = LineConstraint(line=line, point=point)
            else:
                constraint = LineAlignConstraint(line=line, point=point, align=align, delta=delta)
        else:
            raise ValueError('Constraint incorrectly specified')
        assert constraint is not None
        self._constraints.append(constraint)
        return constraint


    def handles(self):
        """
        Return a list of handles owned by the item.
        """
        return self._handles


    def ports(self):
        """
        Return list of ports.
        """
        return self._ports


    def point(self, pos):
        """
        Get the distance from a point (``x``, ``y``) to the item.
        ``x`` and ``y`` are in item coordinates.
        """
        pass


    def __getstate__(self):
        """
        Persist all, but calculated values (``_matrix_?2?``).
        """
        d = dict(self.__dict__)
        for n in ('_matrix_i2c', '_matrix_c2i', '_matrix_i2v', '_matrix_v2i'):
            try:
                del d[n]
            except KeyError:
                pass
        return d


    def __setstate__(self, state):
        """
        Set state. No ``__init__()`` is called.
        """
        for n in ('_matrix_i2c', '_matrix_c2i'):
            setattr(self, n, None)
        for n in ('_matrix_i2v', '_matrix_v2i'):
            setattr(self, n, WeakKeyDictionary())
        self.__dict__.update(state)


[ NW,
  NE,
  SE,
  SW ] = xrange(4)

class Element(Item):
    """
    An Element has 4 handles (for a start)::

     NW +---+ NE
        |   |
     SW +---+ SE
    """

    def __init__(self, width=10, height=10):
        super(Element, self).__init__()
        self._handles = [ h(strength=VERY_STRONG) for h in [Handle]*4 ]

        eq = EqualsConstraint
        lt = LessThanConstraint
        handles = self._handles
        h_nw = handles[NW]
        h_ne = handles[NE]
        h_sw = handles[SW]
        h_se = handles[SE]

        # edge of element define default element ports
        self._ports = [
            LinePort(h_nw.pos, h_ne.pos),
            LinePort(h_ne.pos, h_se.pos), 
            LinePort(h_se.pos, h_sw.pos), 
            LinePort(h_sw.pos, h_nw.pos)
        ]

        # create minimal size constraints
        self._c_min_w = LessThanConstraint(smaller=h_nw.x, bigger=h_se.x, delta=10)
        self._c_min_h = LessThanConstraint(smaller=h_nw.y, bigger=h_se.y, delta=10)

        # setup constraints
        self.constraints.extend([
            eq(a=h_nw.y, b=h_ne.y),
            eq(a=h_nw.x, b=h_sw.x),
            eq(a=h_se.y, b=h_sw.y),
            eq(a=h_se.x, b=h_ne.x),
            # set h_nw < h_se constraints
            # with minimal size functionality
            self._c_min_w,
            self._c_min_h,
        ])

        # set width/height when minimal size constraints exist
        self.width = width
        self.height = height

    def setup_canvas(self):
        super(Element, self).setup_canvas()

        # Set width/height explicitly, so the element will maintain it
        self.width = self.width
        self.height = self.height

    def _set_width(self, width):
        """
        >>> b=Element()
        >>> b.width = 20
        >>> b.width
        20.0
        >>> b._handles[NW].x
        Variable(0, 40)
        >>> b._handles[SE].x
        Variable(20, 40)
        """
        if width < self.min_width:
            width = self.min_width
        h = self._handles
        h[SE].x = h[NW].x + width


    def _get_width(self):
        """
        Width of the box, calculated as the distance from the left and
        right handle.
        """
        h = self._handles
        return float(h[SE].x) - float(h[NW].x)

    width = property(_get_width, _set_width)

    def _set_height(self, height):
        """
        >>> b=Element()
        >>> b.height = 20
        >>> b.height
        20.0
        >>> b.height = 2
        >>> b.height
        10.0
        >>> b._handles[NW].y
        Variable(0, 40)
        >>> b._handles[SE].y
        Variable(10, 40)
        """
        if height < self.min_height:
            height = self.min_height
        h = self._handles
        h[SE].y = h[NW].y + height

    def _get_height(self):
        """
        Height.
        """
        h = self._handles
        return float(h[SE].y) - float(h[NW].y)

    height = property(_get_height, _set_height)

    @observed
    def _set_min_width(self, min_width):
        """
        Set minimal width.
        """
        if min_width < 0:
            raise ValueError, 'Minimal width cannot be less than 0'

        self._c_min_w.delta = min_width
        if self.canvas:
            self.canvas.solver.request_resolve_constraint(self._c_min_w)

    min_width = reversible_property(lambda s: s._c_min_w.delta, _set_min_width)

    @observed
    def _set_min_height(self, min_height):
        """
        Set minimal height.
        """
        if min_height < 0:
            raise ValueError, 'Minimal height cannot be less than 0'

        self._c_min_h.delta = min_height
        if self.canvas:
            self.canvas.solver.request_resolve_constraint(self._c_min_h)

    min_height = reversible_property(lambda s: s._c_min_h.delta, _set_min_height)

        
    def point(self, pos):
        """
        Distance from the point (x, y) to the item.
        """
        h = self._handles
        hnw, hse = h[NW], h[SE]
        return distance_rectangle_point(map(float, (hnw.x, hnw.y, hse.x, hse.y)), pos)


class Line(Item):
    """
    A Line item.

    Properties:
     - fuzziness (0.0..n): an extra margin that should be taken into account
         when calculating the distance from the line (using point()).
     - orthogonal (bool): wherther or not the line should be orthogonal
         (only straight angles)
     - horizontal: first line segment is horizontal
     - line_width: width of the line to be drawn

    This line also supports arrow heads on both the begin and end of the
    line. These are drawn with the methods draw_head(context) and
    draw_tail(context). The coordinate system is altered so the methods do
    not have to know about the angle of the line segment (e.g. drawing a line
    from (10, 10) via (0, 0) to (10, -10) will draw an arrow point).
    """

    def __init__(self):
        super(Line, self).__init__()
        self._handles = [Handle(connectable=True), Handle((10, 10), connectable=True)]
        self._ports = []
        self._update_ports()

        self._line_width = 2
        self._fuzziness = 0
        self._orthogonal_constraints = []
        self._horizontal = False
        self._head_angle = self._tail_angle = 0

    @observed
    def _set_line_width(self, line_width):
        self._line_width = line_width

    line_width = reversible_property(lambda s: s._line_width, _set_line_width)

    @observed
    def _set_fuzziness(self, fuzziness):
        self._fuzziness = fuzziness

    fuzziness = reversible_property(lambda s: s._fuzziness, _set_fuzziness)

    def _update_orthogonal_constraints(self, orthogonal):
        """
        Update the constraints required to maintain the orthogonal line.
        The actual constraints attribute (``_orthogonal_constraints``) is
        observed, so the undo system will update the contents properly
        """
        if not self.canvas:
            self._orthogonal_constraints = orthogonal and [ None ] or []
            return

        for c in self._orthogonal_constraints:
            self.canvas.solver.remove_constraint(c)

        if not orthogonal:
            return

        h = self._handles
        if len(h) < 3:
            self.split_segment(0)
        eq = EqualsConstraint #lambda a, b: a - b
        add = self.canvas.solver.add_constraint
        cons = []
        rest = self._horizontal and 1 or 0
        for pos, (h0, h1) in enumerate(zip(h, h[1:])):
            if pos % 2 == rest: # odd
                cons.append(add(eq(a=h0.x, b=h1.x)))
            else:
                cons.append(add(eq(a=h0.y, b=h1.y)))
            self.canvas.solver.request_resolve(h1.x)
            self.canvas.solver.request_resolve(h1.y)
        self._set_orthogonal_constraints(cons)
        self.request_update()

    @observed
    def _set_orthogonal_constraints(self, orthogonal_constraints):
        """
        Setter for the constraints maintained. Required for the undo system.
        """
        self._orthogonal_constraints = orthogonal_constraints

    reversible_property(lambda s: s._orthogonal_constraints, _set_orthogonal_constraints)

    @observed
    def _set_orthogonal(self, orthogonal):
        """
        >>> a = Line()
        >>> a.orthogonal
        False
        """
        self._update_orthogonal_constraints(orthogonal)

    orthogonal = reversible_property(lambda s: bool(s._orthogonal_constraints), _set_orthogonal)

    @observed
    def _inner_set_horizontal(self, horizontal):
        self._horizontal = horizontal

    reversible_method(_inner_set_horizontal, _inner_set_horizontal,
                      {'horizontal': lambda horizontal: not horizontal })

    def _set_horizontal(self, horizontal):
        """
        >>> line = Line()
        >>> line.horizontal
        False
        >>> line.horizontal = False
        >>> line.horizontal
        False
        """
        self._inner_set_horizontal(horizontal)
        self._update_orthogonal_constraints(self._orthogonal_constraints)

    horizontal = reversible_property(lambda s: s._horizontal, _set_horizontal)

    def setup_canvas(self):
        """
        Setup constraints. In this case orthogonal.
        """
        super(Line, self).setup_canvas()
        self._update_orthogonal_constraints(self.orthogonal)

    def teardown_canvas(self):
        """
        Remove constraints created in setup_canvas().
        """
        super(Line, self).teardown_canvas()
        for c in self._orthogonal_constraints:
            self.canvas.solver.remove_constraint(c)

    @observed
    def _reversible_insert_handle(self, index, handle):
        self._handles.insert(index, handle)

    @observed
    def _reversible_remove_handle(self, handle):
        self._handles.remove(handle)

    reversible_pair(_reversible_insert_handle, _reversible_remove_handle, \
            bind1={'index': lambda self, handle: self._handles.index(handle)})

    @observed
    def _reversible_insert_port(self, index, port):
        self._ports.insert(index, port)

    @observed
    def _reversible_remove_port(self, port):
        self._ports.remove(port)

    reversible_pair(_reversible_insert_port, _reversible_remove_port, \
            bind1={'index': lambda self, port: self._ports.index(port)})


    def split_segment(self, segment, parts=2):
        """
        Split one segment in the Line in ``parts`` equal pieces.
        ``segment`` 0 is the first segment (between handles 0 and 1).
        The minimum number of parts is 2.

        A list of new handles is returned.

        Note that ``split_segment`` is not able to reconnect constraints that
        are connected to the segment. 
        """
        if segment < 0 or segment >= len(self._ports):
            raise ValueError('Incorrect segment')
        if parts < 2:
            raise ValueError('Incorrect count of parts')

        def do_split(segment, parts):
            h0 = self._handles[segment]
            h1 = self._handles[segment + 1]
            dx, dy = h1.x - h0.x, h1.y - h0.y
            new_h = Handle((h0.x + dx / parts, h0.y + dy / parts), strength=WEAK)
            self._reversible_insert_handle(segment + 1, new_h)

            p0 = LinePort(h0.pos, new_h.pos)
            p1 = LinePort(new_h.pos, h1.pos)
            self._reversible_remove_port(self._ports[segment])
            self._reversible_insert_port(segment, p0)
            self._reversible_insert_port(segment, p1)

            if parts > 2:
                do_split(segment + 1, parts - 1)
        do_split(segment, parts)
        # Force orthogonal constraints to be recreated
        self._update_orthogonal_constraints(self.orthogonal)
        handles = self._handles[segment + 1:segment + parts]
        ports = self._ports[segment:segment + parts - 1]
        return handles, ports


    def merge_segment(self, segment, parts=2):
        """
        Merge two line segments starting from ``segment``.
        The parts parameter indicates how many segments should be merged.

        Tuple of two lists is returned, list of deleted handles and list of
        deleted ports.
        """
        if len(self._ports) < 2:
            raise ValueError('Cannot merge line with one segment')
        if segment < 0 or segment >= len(self._ports):
            raise ValueError('Incorrect segment')
        if parts < 2:
            raise ValueError('Incorrect count of parts')

        if segment + parts >= len(self._ports):
            segment = len(self._ports) - parts
            assert segment >= 0

        # remove handle and ports which share position with handle
        deleted_handles = self._handles[segment + 1:segment + parts]
        deleted_ports = self._ports[segment:segment + parts]
        for h in deleted_handles:
            self._reversible_remove_handle(h)
        for p in deleted_ports:
            self._reversible_remove_port(p)

        # create new port, which replaces old ports destroyed due to
        # deleted handle
        h1 = self._handles[segment]
        h2 = self._handles[segment + 1]
        port = LinePort(h1.pos, h2.pos)
        self._reversible_insert_port(segment, port)

        # force orthogonal constraints to be recreated
        self._update_orthogonal_constraints(self.orthogonal)
        return deleted_handles, deleted_ports


    def _update_ports(self):
        """
        Update line ports.
        """
        assert len(self._handles) >= 2, 'Not enough segments'
        self._ports = []
        handles = self._handles
        for h1, h2 in zip(handles[:-1], handles[1:]):
            self._ports.append(LinePort(h1.pos, h2.pos))


    def opposite(self, handle):
        """
        Given the handle of one end of the line, return the other end.
        """
        handles = self._handles
        if handle is handles[0]:
            return handles[-1]
        elif handle is handles[-1]:
            return handles[0]
        else:
            raise KeyError('Handle is not an end handle')

    def post_update(self, context):
        """
        """
        super(Line, self).post_update(context)
        h0, h1 = self._handles[:2]
        self._head_angle = atan2(h1.y - h0.y, h1.x - h0.x)
        h1, h0 = self._handles[-2:]
        self._tail_angle = atan2(h1.y - h0.y, h1.x - h0.x)

    def closest_segment(self, pos):
        """
        Obtain a tuple (distance, point_on_line, segment).
        Distance is the distance from point to the closest line segment 
        Point_on_line is the reflection of the point on the line.
        Segment is the line segment closest to (x, y)

        >>> a = Line()
        >>> a.closest_segment((4, 5))
        (0.70710678118654757, (4.5, 4.5), 0)
        """
        h = self._handles

        # create a list of (distance, point_on_line) tuples:
        distances = map(distance_line_point, h[:-1], h[1:], [pos] * (len(h) - 1))
        distances, pols = zip(*distances)
        return reduce(min, zip(distances, pols, range(len(distances))))

    def point(self, pos):
        """
        >>> a = Line()
        >>> a.handles()[1].pos = 30, 30
        >>> a.split_segment(0)
        [<Handle object on (15, 15)>]
        >>> a.handles()[1].pos = 25, 5
        >>> a.point((-1, 0))
        1.0
        >>> '%.3f' % a.point((5, 4))
        '2.942'
        >>> '%.3f' % a.point((29, 29))
        '0.784'
        """
        h = self._handles
        distance, point, segment = self.closest_segment(pos)
        return max(0, distance - self.fuzziness)

    def draw_head(self, context):
        """
        Default head drawer: move cursor to the first handle.
        """
        context.cairo.move_to(0, 0)

    def draw_tail(self, context):
        """
        Default tail drawer: draw line to the last handle.
        """
        context.cairo.line_to(0, 0)


    def draw(self, context):
        """
        Draw the line itself.
        See Item.draw(context).
        """
        def draw_line_end(handle, angle, draw):
            cr = context.cairo
            cr.save()
            try:
                cr.translate(handle.x, handle.y)
                cr.rotate(angle)
                draw(context)
            finally:
                cr.restore()

        cr = context.cairo
        cr.set_line_width(self.line_width)
        draw_line_end(self._handles[0], self._head_angle, self.draw_head)
        for h in self._handles[1:-1]:
            cr.line_to(h.x, h.y)
        h0, h1 = self._handles[-2:]
        draw_line_end(self._handles[-1], self._tail_angle, self.draw_tail)
        cr.stroke()


__test__ = {
    'Line._set_orthogonal': Line._set_orthogonal,
    }


# vim: sw=4:et:ai
