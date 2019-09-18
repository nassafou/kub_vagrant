#!/usr/bin/python
# -*- coding: Utf-8 -*-

from flask import Flask, render_template

app = Flask(__name__)


@app.route('/')
def index():
    
		# dictionnaire de data
    data = {'user': 'Xavki', 'machine': 'lubuntu-18.04'}

    # affichage
    return render_template('index.html', title='Home', data=data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


