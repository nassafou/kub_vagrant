#!/usr/bin/python
from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def home():
  concaten = ""
  liste = []
  for parent, dnames, fnames in os.walk("files/"):
    for fname in fnames:
      filename = os.path.join(parent, fname)
      liste.append(filename)   
  return render_template('machines.html', liste=liste)

@app.route('/<path:path>')
def machines(path):
  contenu = []
  with open(path) as f:
    for line in f:
      contenu.append(line)
  return render_template('contenu.html', contenu=contenu) 


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)


