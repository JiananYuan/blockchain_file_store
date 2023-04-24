import json
import os
import requests
from flask import render_template, redirect, request, send_file
from werkzeug.utils import secure_filename
from app import app
from timeit import default_timer as timer
# from learn import PLR, Segment
import numpy as np
import math


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


# Stores all the post transaction in the node
request_tx = []
# store filename
files = []
# destiantion for upload files
UPLOAD_FOLDER = "app/static/Uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# store  address
ADDR = "http://127.0.0.1:8800"
learn = False
segs = []
err = 8


# create a list of requests that peers has send to upload files
def get_tx_req():
    global request_tx
    chain_addr = "{0}/chain".format(ADDR)
    resp = requests.get(chain_addr)
    if resp.status_code == 200:
        content = []
        chain = json.loads(resp.content.decode())
        for block in chain["chain"]:
            for trans in block["transactions"]:
                trans["index"] = block["index"]
                trans["hash"] = block["prev_hash"]
                content.append(trans)
        request_tx = sorted(content, key=lambda k: k["hash"], reverse=True)


@app.route("/learn")
def learned_index():
    global learn
    global segs
    plr = PLR(err)
    if len(files) == 0:
        return "No files to learn!"

    size = len(files)
    temp = int(files[size - 1][0])
    segs = plr.train(np.array(files)[:, 0])
    if len(segs) == 0:
        return "No Segments!"
    segs.append(Segment(temp, 0, 0, 0))
    learn = True
    return "Finish learning!"

# Loads and runs the home page
@app.route("/")
def index():
    get_tx_req()
    return render_template("index.html", title="FileStorage",
                           subtitle="A Decentralized Network for File Storage/Sharing", node_address=ADDR,
                           request_tx=request_tx)


@app.route("/submit", methods=["POST"])
# When new transaction is created it is processed and added to transaction
def submit():
    start = timer()
    user = request.form["user"]
    if user == '':
        user = 'test_user'
    up_file = request.files["v_file"]

    # save the uploaded file in destination
    up_file.save(os.path.join("app/static/Uploads/", secure_filename(up_file.filename)))
    # add the file to the list to create a download link
    # print('submit file: ', up_file.filename)
    files.append([up_file.filename, os.path.join(app.root_path, "static", "Uploads", up_file.filename)])
    # determines the size of the file uploaded in bytes
    file_states = os.stat(os.path.join(app.root_path, "static", "Uploads", up_file.filename)).st_size
    # create a transaction object
    post_object = {
        "user": user,  # user name
        "v_file": up_file.filename,  # filename
        "file_data": str(up_file.stream.read()),  # file data
        "file_size": file_states  # file size
    }

    # Submit a new transaction
    address = "{0}/new_transaction".format(ADDR)
    requests.post(address, json=post_object)
    end = timer()
    print(end - start)
    return redirect("/")


# creates a download link for the file
@app.route("/submit/<string:variable>", methods=["GET"])
def download_file(variable):
    # p = files[variable]
    # 查询id转化为数字型id
    # dot_id = 0
    # while dot_id < len(variable) and variable[dot_id] != '.':
    #     dot_id += 1
    # file_v_id = int(variable[0:dot_id])
    if learn:
        l = 0
        r = len(segs)
        while l < r:
            m = (r + l) // 2
            if int(variable) <= segs[m].x:
                r = m
            else:
                l = m + 1
        if segs[l].x > int(variable) and l > 0:
            l -= 1
        if segs[l].x <= int(variable):
            pos = segs[l].k * float(variable) + segs[l].b
            low_bound = max(math.floor(pos - err), 0)
            up_bound = min(math.ceil(pos + err), len(files) - 1)
            l = int(low_bound)
            r = int(up_bound)
            while l < r:
                m = (r + l) // 2
                if variable <= files[m][0]:
                    r = m
                else:
                    l = m + 1
            if files[l][0] == variable:
                return send_file(files[l][1], as_attachment=True)
            else:
                return 'files[l][0] != variable'
        else:
            return 'segs[l].x > variable'
    else:
        l = 0
        r = len(files)
        while l < r:
            m = (r + l) // 2
            if variable <= files[m][0]:
                r = m
            else:
                l = m + 1
        if files[l][0] != variable:
            return 'files[l][0] != variable'
        return send_file(files[l][1], as_attachment=True)
