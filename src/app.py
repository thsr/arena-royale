from flask import Flask, jsonify, request, Response, render_template


import const
from utils import flatten, logging
from db import g
from models import Backup, User, Channel, Block
from gc_stuff import gc_stuff




app = Flask(__name__)




# routes
# ======
@app.route('/backup/reset', methods=['POST'])
def backup_reset():
    if request.method == 'POST':
        b = Backup()
        b.clear_logfile()
        b.clear_db()
        res = b.go_for_it(test_mode=False)
        return jsonify(res)


@app.route('/backup', methods=['POST'])
def backup():
    if request.method == 'POST':
        b = Backup()
        res = b.go_for_it(test_mode=False)
        return jsonify(res)
        return "ok"


@app.route('/all')
def route_all():
    limit = request.args.get('limit') or 50
    limit = int(limit)
    skip = request.args.get('skip') or 0
    skip = int(skip)
    
    if request.args.get('channel'):
        res = g.run("""MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel {id: {channel_id}})
            RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
            ORDER BY b.connected_at DESC
            SKIP {skip}
            LIMIT {limit}""",
            channel_id=int(request.args.get('channel')),
            skip=skip,
            limit=limit,
        ).data()
    else:
        res = g.run("""MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel)
            RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
            ORDER BY b.connected_at DESC
            SKIP {skip}
            LIMIT {limit}""",
            skip=skip,
            limit=limit,
        ).data()

    return render_template('jj.html', blocks=res)





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)