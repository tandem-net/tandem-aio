from flask import Flask, render_template

import json

app = Flask(__name__)

@app.route('/')
def index():
    return 'index'



@app.route('/start', methods=['POST'])
def start():
    pass

@app.route('/stop', methods=['POST'])
def stop():
    pass

@app.route('/new', methods=['POST'])
def new():
    pass

@app.route('/deploy', methods=['POST'])
def deploy():
    pass



app.run('0.0.0.0', port=6767)