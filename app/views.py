import json
import os
import requests
from flask import render_template, redirect, request, send_file
from werkzeug.utils import secure_filename
from app import app
from timeit import default_timer as timer
from learn import PLR, Segment
import numpy as np
import math
from random import sample

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
M = 1000000


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
        if len(request_tx) > 0:
            # 先默认大于10000个文件
            request_tx = sample(request_tx, 10000)


@app.route("/learn")
def learned_index():
    global learn
    global segs
    plr = PLR(err)
    if len(files) == 0:
        return "No files to learn!"

    size = len(files)
    segs = plr.train(np.array(files)[:, 0])
    if len(segs) == 0:
        return "No Segments!"
    segs.append(Segment(int(files[size - 1][0]), 0, size - 1, 0))
    learn = True
    return "Finish learning!"


@app.route("/switch")
def unlearned_index():
    global learn
    learn = not learn
    if learn and segs != []:
        return "enable learn"
    else:
        return "Disable learning!"


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


@app.route("/batch_load")
def batch_load():
    user = 'test_user'
    for idx in range(0, 20000):
        filename = str(idx)
        filename = filename.zfill(10)
        # add the file to the list to create a download link
        # print('submit file: ', up_file.filename)
        files.append([filename, 'C:/Users/Jiananyuan/Downloads/Uploads/' + filename])
        # determines the size of the file uploaded in bytes
        file_states = 4
        # create a transaction object
        post_object = {
            "user": user,  # user name
            "v_file": filename,  # filename
            "file_data": 'test',  # file data
            "file_size": file_states  # file size
        }
        # Submit a new transaction
        address = "{0}/new_transaction".format(ADDR)
        requests.post(address, json=post_object)
    # for filename in os.listdir(r'C:\Users\Jiananyuan\Downloads\origin2'):
    #     rf = open(r'C:\Users\Jiananyuan\Downloads\origin2' + '\\' + filename)
    #     wf = open(os.path.join('app/static/Uploads/', secure_filename(filename)), 'w')
    #     # save the uploaded file in destination
    #     rf_content = rf.readline()
    #     wf.write(rf_content)
    #     wf.close()
    #     rf.close()
    #     # add the file to the list to create a download link
    #     # print('submit file: ', up_file.filename)
    #     files.append([filename, os.path.join(app.root_path, "static", "Uploads", filename)])
    #     # determines the size of the file uploaded in bytes
    #     file_states = os.stat(os.path.join(app.root_path, "static", "Uploads", filename)).st_size
    #     # create a transaction object
    #     post_object = {
    #         "user": user,  # user name
    #         "v_file": filename,  # filename
    #         "file_data": rf_content,  # file data
    #         "file_size": file_states  # file size
    #     }
    #     # Submit a new transaction
    #     address = "{0}/new_transaction".format(ADDR)
    #     requests.post(address, json=post_object)
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
    wf = open('C:/Users/Jiananyuan/Downloads/Uploads/' + variable.zfill(10), 'w')
    wf.write('test')
    wf.close()
    st = timer()
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
                en = timer()
                print('lookup time using learn model:', en - st)
                return send_file(files[l][1], as_attachment=True)
            else:
                return 'files[l][0] != variable'
        else:
            return 'segs[l].x > variable'
    else:
        # l = 0
        # r = len(files)
        # while l < r:
        #     m = (r + l) // 2
        #     if variable <= files[m][0]:
        #         r = m
        #     else:
        #         l = m + 1
        # if files[l][0] != variable:
        #     return 'files[l][0] != variable'
        m = 0
        for i in range(0, len(files)):
            if files[i][0] == variable:
                m = i
                break
        en = timer()
        print('lookup time using binary search:', en - st)
        return send_file(files[m][1], as_attachment=True)
