import random

from flask import Flask, request

app = Flask(__name__)


@app.route('/demo/endpoint')
def test1():
    if random.randrange(0, 10000) in range(4000, 5000):
        raise Exception()
    else:
        return request.args.get('user')


@app.route('/demo/morereliableendpoint')
def test2():
    if random.randrange(0, 10000) in range(4000, 4100):
        raise Exception()
    else:
        return request.args.get('user')


if __name__ == '__main__':
    app.run()
