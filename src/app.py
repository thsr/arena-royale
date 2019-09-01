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

@app.route('/blocks')
@app.route('/blocks/<int:page>')
def route_all(page=1):
    per = request.args.get('per') or 500
    try:
        limit = int(per)
    except ValueError:
        limit = 500
    
    skip = (page - 1) * limit
    
    if request.args.get('channel'):
        blocks = g.run("""MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel {id: {channel_id}})
            RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
            ORDER BY b.connected_at DESC
            SKIP {skip}
            LIMIT {limit}""",
            channel_id=int(request.args.get('channel')),
            skip=skip,
            limit=limit,
        ).data()

        this_channel = g.run("""MATCH (c:Channel {id: {channel_id}})
            RETURN c.title as title, c.slug as slug, c.user_slug as user_slug
            LIMIT 1""",
            channel_id=int(request.args.get('channel')),
        ).data()[0]
    else:
        blocks = g.run("""MATCH (b:Block), (b)-[:CONNECTS_TO]-(c:Channel)
            RETURN b as data, collect({id: c.id, title: c.title, slug: c.slug, user_slug: c.user_slug, status: c.status}) as channels
            ORDER BY b.connected_at DESC
            SKIP {skip}
            LIMIT {limit}""",
            skip=skip,
            limit=limit,
        ).data()

        this_channel = None

    channels = g.run("""MATCH (c:Channel)
        RETURN c.id as id, c.title as title, c.status as status
        ORDER BY c.added_to_at DESC""",
    ).data()

    return render_template('blocks.html', blocks=blocks, channels=channels, this_channel=this_channel)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)