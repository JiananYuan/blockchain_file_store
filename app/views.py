import json
import os
import requests
from flask import render_template, redirect, request,send_file
from werkzeug.utils import secure_filename
from app import app
from timeit import default_timer as timer

# Stores all the post transaction in the node
request_tx = []
#store filename
files = []
#destiantion for upload files
UPLOAD_FOLDER = "app/static/Uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# store  address
ADDR = "http://127.0.0.1:8800"


#create a list of requests that peers has send to upload files
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
        request_tx = sorted(content,key=lambda k: k["hash"],reverse=True)


# Loads and runs the home page
@app.route("/")
def index():
    get_tx_req()
    return render_template("index.html",title="FileStorage",subtitle = "A Decentralized Network for File Storage/Sharing",node_address = ADDR,request_tx = request_tx)


@app.route("/submit", methods=["POST"])
# When new transaction is created it is processed and added to transaction
def submit():
    start = timer()
    user = request.form["user"]
    up_file = request.files["v_file"]
    
    #save the uploaded file in destination
    up_file.save(os.path.join("app/static/Uploads/",secure_filename(up_file.filename)))
    #add the file to the list to create a download link
    files.append([up_file.filename, os.path.join(app.root_path, "static" , "Uploads", up_file.filename)])
    #determines the size of the file uploaded in bytes 
    file_states = os.stat(os.path.join(app.root_path, "static" , "Uploads", up_file.filename)).st_size 
    #create a transaction object
    post_object = {
        "user": user, #user name
        "v_file" : up_file.filename, #filename
        "file_data" : str(up_file.stream.read()), #file data
        "file_size" : file_states   #file size
    }
   
    # Submit a new transaction
    address = "{0}/new_transaction".format(ADDR)
    requests.post(address, json=post_object)
    end = timer()
    print(end - start)
    return redirect("/")

#creates a download link for the file
@app.route("/submit/<string:variable>",methods = ["GET"])
def download_file(variable):
    # p = files[variable]
    # 查询id转化为数字型id
    # dot_id = 0
    # while dot_id < len(variable) and variable[dot_id] != '.':
    #     dot_id += 1
    # file_v_id = int(variable[0:dot_id])
    l = 0
    r = len(files)
    while l < r:
        m = (r + l) >> 1
        if variable >= files[m][0]:
            r = m
        else:
            l = m + 1
    if files[l][0] != variable:
        return
    return send_file(files[l][1],as_attachment=True)
