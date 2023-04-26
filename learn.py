class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Line:
    def __init__(self, a, b):
        self.a = a
        self.b = b


class Segment:
    def __init__(self, x, k, b, x2):
        self.x = x
        self.k = k
        self.b = b
        self.x2 = x2


def get_slope(p1: Point, p2: Point) -> float:
    return (p2.y - p1.y) / (p2.x - p1.x)


def get_line(p1: Point, p2: Point) -> Line:
    a = get_slope(p1, p2)
    b = -a * p1.x + p1.y
    return Line(a=a, b=b)


def get_intersection(l1: Line, l2: Line) -> Point:
    a, b, c, d = l1.a, l2.a, l1.b, l2.b
    x = (d - c) / (a - b)
    y = (a * d - b * c) / (a - b)
    return Point(x=x, y=y)


def is_above(pt: Point, l: Line) -> bool:
    return pt.y > l.a * pt.x + l.b


def is_below(pt: Point, l: Line) -> bool:
    return pt.y < l.a * pt.x + l.b


def get_upper_bound(pt: Point, gamma: float) -> Point:
    return Point(x=pt.x, y=pt.y + gamma)


def get_lower_bound(pt: Point, gamma: float) -> Point:
    return Point(x=pt.x, y=pt.y - gamma)


class GreedyPLR:
    def __init__(self, gamma: float):
        self.state = "need2"
        self.gamma = gamma
        self.s0 = None
        self.s1 = None
        self.rho_lower = None
        self.rho_upper = None
        self.sint = None
        self.last_pt = None

    def process(self, pt):
        self.last_pt = pt
        if self.state == "need2":
            self.s0 = pt
            self.state = "need1"
        elif self.state == "need1":
            self.s1 = pt
            self.setup()
            self.state = "ready"
        elif self.state == "ready":
            return self.process__(pt)
        else:
            # impossible
            print("ERROR in process")
        s = Segment(0, 0, 0, 0)
        return s

    def setup(self):
        self.rho_lower = get_line(get_upper_bound(self.s0, self.gamma),
                                  get_lower_bound(self.s1, self.gamma))
        self.rho_upper = get_line(get_lower_bound(self.s0, self.gamma),
                                  get_upper_bound(self.s1, self.gamma))
        self.sint = get_intersection(self.rho_upper, self.rho_lower)

    def current_segment(self):
        segment_start = self.s0.x
        avg_slope = (self.rho_lower.a + self.rho_upper.a) / 2.0
        intercept = -avg_slope * self.sint.x + self.sint.y
        s = Segment(segment_start, avg_slope, intercept, int(self.last_pt.x))
        return s

    def process__(self, pt):
        if not (is_above(pt, self.rho_lower) and is_below(pt, self.rho_upper)):
            prev_segment = self.current_segment()
            self.s0 = pt
            self.state = "need1"
            return prev_segment

        s_upper = get_upper_bound(pt, self.gamma)
        s_lower = get_lower_bound(pt, self.gamma)
        if is_below(s_upper, self.rho_upper):
            self.rho_upper = get_line(self.sint, s_upper)
        if is_above(s_lower, self.rho_lower):
            self.rho_lower = get_line(self.sint, s_lower)
        s = Segment(0, 0, 0, 0)
        return s

    def finish(self):
        s = Segment(0, 0, 0, 0)
        if self.state == "need2":
            self.state = "finished"
            return s
        elif self.state == "need1":
            self.state = "finished"
            s.x = self.s0.x
            s.k = 0
            s.b = self.s0.y
            s.x2 = self.last_pt.x
            return s
        elif self.state == "ready":
            self.state = "finished"
            return self.current_segment()
        else:
            print("ERROR in finish")
            return s


class PLR:
    def __init__(self, gamma):
        self.gamma = gamma
        self.segments = []

    def train(self, keys):
        plr = GreedyPLR(self.gamma)
        size = len(keys)
        for i in range(size):
            seg = plr.process(Point(float(keys[i]), i))
            if seg.x != 0 or seg.k != 0 or seg.b != 0:
                self.segments.append(seg)

        last = plr.finish()
        if last.x != 0 or last.k != 0 or last.b != 0:
            self.segments.append(last)
        return self.segments

