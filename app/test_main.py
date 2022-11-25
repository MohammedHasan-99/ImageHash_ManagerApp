
# from ast import Num
# from curses import flash
# from itertools import chain
from dbm import dumb
import random
# import time
# from tkinter.messagebox import NO
# from unittest.mock import patch
# from flask import render_template, url_for
# from app import webapp, memcache
from flask import *
# from flask import Flask, redirect, render_template, request, url_for
import pymysql
import os
import threading
from collections import OrderedDict
import base64




global memcache

webapp = Flask(__name__)
memcache = {}


def connection():
    # Connect to database
    conn = pymysql.connect(host='localhost',
                           user='root',
                           password='',
                           database='hash_image')
    return conn






class Cache:
    
    def __init__(self):
        self.cache = OrderedDict()
        self.capacity = (1000) * 1024 * 1024
        self.size = (1000) * 1024 * 1024
        self.hit_count = 0
        self.miss_count = 0
        self.replacment_policy = 0
        self.number_of_items = 0
        self.number_of_requests_served = 0

        self.refreshConfiguration()
        # threading.Timer(5.0, self.storeStatistics).start()

    def get(self, key: str) -> str:
        self.number_of_requests_served = self.number_of_requests_served + 1

        # If key exists in cache
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hit_count = self.hit_count + 1
            return self.cache[key]["image"]
        else:
            self.miss_count = self.miss_count + 1

            # Connect to database
            conn = connection()

            # Check if hash exists
            cursor = conn.cursor()
            sql = f"SELECT count(*) FROM `images` WHERE `key`='{key}'"
            cursor.execute(sql)

            if cursor.fetchone()[0] == 0:
                # If hash does not exist return empty string
                return ""
            else:
                sql = f"SELECT `key`,`name` FROM `images` WHERE `key`='{key}'"
                cursor.execute(sql)

                row = cursor.fetchone()

                hash = row[0]
                path = f"app/static/hashedImages/{row[1]}"

                print(path)

                return self.put(hash, path)

    def put(self, key: str, path: str) -> None:
        if key not in self.cache:
            # If image exists
            if os.path.exists(path):
                # Get image size in Bytes
                fileSize = os.path.getsize(path)
                if fileSize > self.size:
                    return
                # If cache has no free space replace
                while self.capacity - fileSize < 0:
                    
                    self.replace()
                with open(path, 'rb') as file:
                    data = file.read()
                # data = f"data:{file.content_type};base64,{base64.b64encode(data).decode('utf-8')}"
                data = f"data:jpeg;base64,{base64.b64encode(data).decode('utf-8')}"
                self.cache[key] = {
                    "image": data,
                    "size": fileSize
                }
                self.capacity = self.capacity - fileSize
                return data
        return None

    def replace(self, ) -> None:
        if len(self.cache) > 0:
            # LRU
            if self.replacment_policy == 1:
                # key = min(self.cache.keys(),
                #     key=(lambda k: self.cache[k]["LastTimeUsed"]))
                item = self.cache.popitem(last=False)

                fileSize = item[1]["size"]
                # Free space
                self.capacity = self.capacity + fileSize
                # Delete the item
                
            # Random
            else:
                # Get random key
                key = random.choice(list(self.cache.keys()))

                # Delete the item
                self.invalidateKey(key)

    def invalidateKey(self, key: str) -> None:
        if key in self.cache:
            # Get file size in Bytes
            fileSize = os.path.getsize(self.cache[key]["path"])

            # Free space
            self.capacity = self.capacity + fileSize

            # Delete item from cache
            self.cache.pop(key)

    def setReplacment(self, policy: int) -> None:
        if 0 <= policy <= 1:
            self.replacment_policy = policy

    def setSize(self, size: int) -> None:
        size = size * 1024 * 1024

        self.capacity = self.capacity - self.size + size

        self.size = size

        while self.capacity < 0:
            self.replace()

    def getSize(self, ) -> int:
        return int(self.size) / 1024 / 1024

    def getFullSpace(self, ) -> int:
        return (self.size - self.capacity) / 1024 / 1024

    def getFreeSpace(self, ) -> int:
        return (self.size - (self.size - self.capacity)) / 1024 / 1024

    def getNumberOfItems(self, ) -> int:
        return len(self.cache)

    def getReplacePolicy(self, ) -> int:
        return self.replacment_policy

    def scheduler(self, ):
        # Push statistics every 5 sec
        threading.Timer(5.0, self.storeStatistics).start()

    def storeStatistics(self, ) -> None:
        if self.hit_count > 0 or self.miss_count > 0 or self.number_of_items != len(
                self.cache):
            # Connect to database
            conn = connection()

            cursor = conn.cursor()
            sql = f"INSERT INTO `statistics`(`Hit Rate`, `Miss Rate`, `Number Of Items`, `Size`, `Number Of Requests Served`, `Free Space`) VALUES ({self.hit_count},{self.miss_count},{len(self.cache)},{self.getFullSpace()},{self.number_of_requests_served}, {self.getFreeSpace()})"
            cursor.execute(sql)
            conn.commit()
            conn.close()

            # Clear old values
            self.hit_count = 0
            self.miss_count = 0
            self.number_of_items = len(self.cache)
            self.number_of_requests_served = 0

        self.scheduler()

    def clear(slef, ):
        slef.cache.clear()
        slef.capacity = slef.size

    def state(self, ):
        print(f"Number of items: {self.getNumberOfItems()}")
        print(f"Size: {self.size}")
        print(f"Capacity: {self.capacity}")
        print(f"Hit: {self.hit_count}")
        print(f"Miss: {self.miss_count}")
        print(
            "============================================================================================================================"
        )

    def refreshConfiguration(self, ):
        # Connect to database
        conn = connection()

        cursor = conn.cursor()
        sql = f"SELECT count(*) FROM `caches`"
        cursor.execute(sql)

        if cursor.fetchone()[0] != 0:
            sql = f"SELECT size, policies_id FROM `caches` where created_at = (SELECT MAX(created_at) FROM caches)"
            cursor.execute(sql)

            row = cursor.fetchone()

            self.capacity = row[0] * 1024 * 1024
            self.size = row[0] * 1024 * 1024
            
            self.replacment_policy = row[1]


# Cache
cache = Cache()






@webapp.route('/')
def main():
    return render_template("main.html")


@webapp.route('/config',methods=['POST','GET'])
def config():
    if request.method == 'POST':
        size = request.form["size"]
        policy = request.form["policy"]
        clear = request.form["clear"]
        print(clear)
        if clear == "on":
            cache.clear()
        conn = connection()
        cursor = conn.cursor()
        
        insert = f"INSERT INTO `caches` (`size`, `policies_id`) VALUES ({size}, {policy})"
        cursor.execute(insert)
        conn.commit()
        conn.close()
        cache.refreshConfiguration()
        return render_template("config.html", message="Cache set successfully")
    if request.method == 'GET':   
        return render_template("config.html")

@webapp.route('/list')
def listItems():
    conn = connection()
    cursor = conn.cursor()
        
    select = f"SELECT * FROM `images`"

    cursor.execute(select)
    images = cursor.fetchall()
    conn.close()
    return render_template("list.html", images=images)

@webapp.route('/addImage',methods=['POST','GET'])
def addImage():
    
    if request.method == 'POST':

        id = request.form["id"]
        path = request.files["image"]
        print(f"static/hashedImages/{path.filename}")
        # print(os.path.join(os.getcwd(), f"static/x/{path.filename}"))

        path.save(f"app/static/hashedImages/{path.filename}")
        conn = connection()
        cursor = conn.cursor()
        
        select = f"SELECT count(*) FROM `images` WHERE `key`='{id}'"
        cursor.execute(select)
        if cursor.fetchone()[0] == 0:
            insert = f"INSERT INTO `images` (`key`, `name`) VALUES ('{id}', '{path.filename}')"
            cursor.execute(insert)
            conn.commit()
            conn.close()
        else:
            update = f"UPDATE `images` SET `name` ='{path.filename}' WHERE `key`='{id}'"
            cursor.execute(update)
            conn.commit()
            conn.close()
        return redirect(url_for("addImage"))

    if request.method == 'GET':
        return render_template("addImage.html")

@webapp.route('/requestImage',methods=['GET'])
def requestImage():
    return render_template("requestImage.html")


@webapp.route('/getImage',methods=['POST'])
def getImage():
    id = request.form["id"]
    img = cache.get(id)

    if img == "":
        return render_template("requestImage.html", message="No Image found")
    else:
        # select = f"SELECT name FROM `images` WHERE `key`='{id}'"
        # cursor.execute(select)
        # conn.commit()
        # conn.close()
        # path = f'static/hashedImages/{cursor.fetchone()[0]}'
        return render_template("requestImage.html",image=img)


@webapp.route('/statistics')
def statistics():
    conn = connection()
    cursor = conn.cursor()

    sql = "SELECT count(*) from `statistics` where `created_at` >= date_sub(now(), interval 10 minute)"
    cursor.execute(sql)

    hitRate = 0
    missRate = 0

    if cursor.fetchone()[0] != 0:
        sql = "SELECT SUM(`hit Rate`), SUM(`miss Rate`) from `statistics` where created_at >= date_sub(now(), interval 10 minute);"
        # sql = f"SELECT size, policies_id FROM `statistics` where created_at = (SELECT MAX(created_at) FROM caches)"
        cursor.execute(sql)
        
        row = cursor.fetchone()

        hitCount = row[0]
        MissCount = row[1]
        if hitCount == 0 and MissCount == 0: 
            hitRate = 0
            missRate = 0
        else:
            hitRate = (hitCount/(hitCount+MissCount))*100
            missRate = 100 - hitRate
    
    sql = "SELECT sum(`Number Of Requests Served`) from `statistics` where `created_at` >= date_sub(now(), interval 10 minute)"
    cursor.execute(sql)
    numOfRequestServed = cursor.fetchone()[0]
    numOfItems = cache.getNumberOfItems()
    size = cache.getSize()
    freeSpace = cache.getFreeSpace()
    return render_template("statistics.html",hitRate=hitRate,missRate=missRate,numOfRequestServed=numOfRequestServed ,numOfItems=numOfItems,size=size,freeSpace=freeSpace )

@webapp.route('/get',methods=['POST'])
def get():
    key = request.form.get('key')

    if key in memcache:
        value = memcache[key]
        response = webapp.response_class(
            response=json.dumps(value),
            status=200,
            mimetype='application/json'
        )
    else:
        response = webapp.response_class(
            response=json.dumps("Unknown key"),
            status=400,
            mimetype='application/json'
        )

    return response

@webapp.route('/put',methods=['POST'])
def put():
    key = request.form.get('key')
    value = request.form.get('value')
    memcache[key] = value

    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )

    return response




conn = connection()
cursor = conn.cursor()

# Check if their is any hit or miss count the past 10 min
sql = "SELECT count(*) from statistics where created_at >= date_sub(now(), interval 10 minute)"
cursor.execute(sql)


webapp.run('0.0.0.0',5001,debug=True)













import pytest
# import sys
# import io
# sys.path.append('../backend')
# from main import *
# import main
# from main import webapp
import io

@pytest.fixture()
def app():
    webapp.config.update({
        "TESTING": True,
    })
    yield webapp


@pytest.fixture()
def client(app):
    return  webapp.test_client()


@pytest.fixture()
def runner(app):
    print(app)
    return  webapp.test_cli_runner()


# Test home page
def test_render_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


# Test list page
def test_render_list_page(client):
    response = client.get("/list")
    assert response.status_code == 200

# Test config page
def test_render_config_page(client):
    response = client.get("/config")
    assert response.status_code == 200

# Test get page
def test_render_get_page(client):
    response = client.get("/requestImage")
    assert response.status_code == 200


def test_render_statistics(client):
    response = client.get("/statistics")
    assert response.status_code == 200

def test_render_add_page(client):
    response = client.get("/addImage")
    assert response.status_code == 200


def test_post_config(client):
    response = client.post("/config", data={
        "size": 50,
        "policy": 0,
        "clear":"on"
    })
    assert response.status_code == 200
    assert int(cache.getSize()) == 50
    assert cache.getReplacePolicy() == 0



def test_add_image(client):
    response = client.post("/addImage", data={
        "id": "hashkey",
        "image": (io.BytesIO(b"some initial text data"), 'test-img.jpeg')
    }, content_type='multipart/form-data')
    assert response.status_code == 302



def test_get_image(client):
    response = client.post("/getImage" , data={
        "id":"test"
    })
    assert response.status_code == 200





# Test home page
def test_render_home_page2(client):
    response = client.get("/")
    assert response.status_code == 200


# Test list page
def test_render_list_page2(client):
    response = client.get("/list")
    assert response.status_code == 200

# Test config page
def test_render_config_page2(client):
    response = client.get("/config")
    assert response.status_code == 200

# Test get page
def test_render_get_page2(client):
    response = client.get("/requestImage")
    assert response.status_code == 200


def test_render_statistics2(client):
    response = client.get("/statistics")
    assert response.status_code == 200

def test_render_add_page2(client):
    response = client.get("/addImage")
    assert response.status_code == 200


def test_post_config2(client):
    response = client.post("/config", data={
        "size": 50,
        "policy": 0,
        "clear":"on"
    })
    assert response.status_code == 200
    assert int(cache.getSize()) == 50
    assert cache.getReplacePolicy() == 0



def test_add_imag2(client):
    response = client.post("/addImage", data={
        "id": "hashkey",
        "image": (io.BytesIO(b"some initial text data"), 'test-img.jpeg')
    }, content_type='multipart/form-data')
    assert response.status_code == 302



def test_get_image2(client):
    response = client.post("/getImage" , data={
        "id":"test"
    })
    assert response.status_code == 200





# Test home page
def test_render_home_page1(client):
    response = client.get("/")
    assert response.status_code == 200


# Test list page
def test_render_list_page(client):
    response = client.get("/list")
    assert response.status_code == 200

# Test config page
def test_render_config_page1(client):
    response = client.get("/config")
    assert response.status_code == 200

# Test get page
def test_render_get_page1(client):
    response = client.get("/requestImage")
    assert response.status_code == 200


def test_render_statistics1(client):
    response = client.get("/statistics")
    assert response.status_code == 200

def test_render_add_page1(client):
    response = client.get("/addImage")
    assert response.status_code == 200


def test_post_config1(client):
    response = client.post("/config", data={
        "size": 50,
        "policy": 0,
        "clear":"on"
    })
    assert response.status_code == 200
    assert int(cache.getSize()) == 50
    assert cache.getReplacePolicy() == 0



def test_add_image1(client):
    response = client.post("/addImage", data={
        "id": "hashkey",
        "image": (io.BytesIO(b"some initial text data"), 'test-img.jpeg')
    }, content_type='multipart/form-data')
    assert response.status_code == 302



def test_get_image1(client):
    response = client.post("/getImage" , data={
        "id":"test"
    })
    assert response.status_code == 200



