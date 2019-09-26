#!/usr/bin/python
# coding:utf-8

from flask import Flask
from flask import request

app = Flask(__name__)


@app.route('/datas', methods=['PUT'])
def upload():
    machine = request.args['machine']
    type = request.args['type']
    with open('/var/central/'+machine+'_'+type+'_file.csv', 'wb') as f:
        f.write(request.data)

    return machine


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)

