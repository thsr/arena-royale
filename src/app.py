from flask import Flask, jsonify, request, Response, render_template




import const
from utils import flatten, logging
from db import g
from models import Backup, User, Channel, Block
from gc_stuff import gc_stuff




app = Flask(__name__)




# routes
# ======
@app.route('/all')
def route_all():
    if request.args.get('channel'):
        res = g.run("""MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel {id: {channel_id}})
            RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
            ORDER BY b.connected_at DESC
            LIMIT 200""",
            channel_id=int(request.args.get('channel')),
        ).data()
    else:
        res = g.run("""MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel)
            RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
            ORDER BY b.connected_at DESC
            LIMIT 200"""
        ).data()
    return render_template('jj.html', blocks=res)


@app.route('/c', methods=['POST'])
def route_c():
    if request.method == 'POST':
        b = Backup()
        b.clear_logfile()
        b.clear_db()
        res = b.go_for_it()
        return jsonify(res)


@app.route('/d', methods=['POST'])
def route_d():
    if request.method == 'POST':
        b = Backup()
        res = b.go_for_it()
        return jsonify(res)


@app.route('/e', methods=['POST'])
def route_e():
    if request.method == 'POST':
        blob_name = "dir/file.webm"
        url = "http://example.com/file.webm"
        res = gc_stuff.upload_to_gcs(blob_name, url)
        return jsonify(res)


@app.route('/f', methods=['POST'])
def route_f():
    if request.method == 'POST':
        b = Backup()
        b.clear_logfile()
        b.clear_db()
        res = b.go_for_it(test_mode=False)
        return jsonify(res)


# @app.route('/g', methods=['POST'])
# def route_g():
#     if request.method == 'POST':
#         logging.warning("here is my result k")


@app.route('/h', methods=['POST'])
def route_h():
    if request.method == 'POST':
        b = Backup()
        res = b.go_for_it(test_mode=False)
        return jsonify(res)
        return "ok"


@app.route('/i', methods=['POST'])
def route_i():
    if request.method == 'POST':
        b = Backup()
        b.clear_logfile()
        b.clear_db()
        block = Block.from_api(1276942)
        block.save()
        return "ok"


query_1 = """MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel)
        //WHERE c.id in [418567, 419718]
        //WHERE b.class = "Media"
        WHERE b.id in [4399660, 3565547, 576903, 4399661, 4467723] //high connected
        RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
        ORDER BY b.connected_at DESC
        LIMIT 200"""


@app.route('/j')
def route_j():
    res = g.run(query_1).data()
    return render_template('j.html', blocks=res)


@app.route('/jj')
def route_jj():
    res = g.run(query_1).data()
    return render_template('jj.html', blocks=res)


@app.route('/k')
def route_k():
    res = g.run(query_1).data()
    return jsonify(res)


@app.route('/l', methods=['POST'])
def route_l():
    if request.method == 'POST':
        file="arena_royale_archive/453466.jpg"
        res = gc_stuff.check_if_file_exists(file)
        if res:
            return str("its there")
        else:
            return gc_stuff.get_public_url(file)


@app.route('/m', methods=['POST'])
def route_m():
    if request.method == 'POST':
        a = {'a': 1, 'c': {'a': 2, 'b': {'x': 5, 'y' : 10}}, 'd': [{'1':1, '2':2, '3':3}, {'1':1, '2':2, '3':3}], 'e': None}
        a = flatten(a)
        return jsonify(a)




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)