from datetime import datetime
from flask import Flask, jsonify
import json
import math
from py2neo import Graph
import requests




# utils
# =====
import logging
logging.basicConfig(filename='./app.log',level=logging.WARNING,format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')

import collections
def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)



# app and db
# ==========
app = Flask(__name__)

g = Graph("bolt://neo4j:7687", auth=('neo4j', 'pass'))




# routes
# ======
@app.route('/del')
def route_del():
    # open('./app.log', 'w').close()
    g.run("match (n)-[r]-() delete r, n")
    g.run("match (n) delete n")
    do_user_channels()
    return "ok"

@app.route('/a')
def route_a():
    # open('./app.log', 'w').close()
    do_user_channels()
    return "ok"

@app.route('/b')
def route_b():
    do_channel_blocks(length=1)
    return "ok"




# funcs
# =====
def do_user_channels(user_id=33234):
    per = 100
    current_page = 0
    total_pages = 1
    
    db_channels = g.run(
        """MATCH (c:Channel)
        RETURN c.id as id, c.updated_at as updated_at, c.added_to_at as added_to_at
        """
    ).data()
    db_channel_ids =  [o['id'] for o in db_channels ]

    while (current_page < total_pages):
        # fetch API for user
        logging.warning("User {}: to fetch all channels API: page {}/{}".format(str(user_id), str(current_page + 1), str(total_pages)))
        response = requests.request(
            "GET",
            "https://api.are.na/v2/users/" + str(user_id) + "/channels",
            timeout=60,
            headers={"Authorization": "Bearer c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"},
            params={"per": per, "page": current_page + 1},
        )
        r = response.json()

        for channel in r['channels']:

            # test mode
            if True:
                to_test=[142063, 419718, 422143, 422144]
                if channel['id'] not in to_test:
                    logging.warning("Channel {} {}: to skip in testing".format(str(channel['id']), str(channel['title'])))
                    continue

            # skip channel if not newly updated or added to
            if (channel['id'] in db_channel_ids):
                old_updated_at = [ o['updated_at'] for o in db_channels if o['id'] == channel['id'] ][0]
                old_updated_at = datetime.strptime(old_updated_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                old_added_to_at = [ o['added_to_at'] for o in db_channels if o['id'] == channel['id'] ][0]
                old_added_to_at = datetime.strptime(old_added_to_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                new_updated_at = datetime.strptime(channel['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                new_added_to_at = datetime.strptime(channel['added_to_at'], '%Y-%m-%dT%H:%M:%S.%fZ')

                if ((old_updated_at == new_updated_at) and (old_added_to_at == new_added_to_at)):
                    logging.warning("Channel {} {}: nothing to update or add".format(str(channel['id']), str(channel['title'])))
                    continue

            # merge channel
            logging.warning("Channel {} {}: to merge ".format(str(channel['id']), str(channel['title'])))
            props = channel
            if 'contents' in props:
                del props['contents']
            props = flatten(props)
            res = g.run(
                """MERGE (c:Channel {id: {id}})
                SET c += {props}
                """,
                id=channel['id'],
                props=props
            ).stats()

            # go thru channel's blocks
            if (channel['length'] != 0):
                logging.warning("Channel {} {}: to start going through all blocks".format(str(channel['id']), str(channel['title'])))
                do_channel_blocks(channel['id'], channel['title'], channel['length'])
        
        current_page = r['current_page']
        total_pages = r['total_pages']




def do_channel_blocks(channel_id=142063, channel_title="testmode", length=None):
    assert length is not None
    per = 100
    current_page = 0
    total_pages = math.ceil(length / per)

    # connections: reset all in this channel
    logging.warning("Channel {} {}: to delete all block-channel rels".format(str(channel_id), str(channel_title)))
    res = g.run(
        """MATCH (:Block)-[r:CONNECTS_TO]->(c:Channel {id: {channel_id}})
        DELETE r
        RETURN count(r) as cnt""",
        channel_id=channel_id,
    ).data()
    logging.warning("Done: deleted {} rels".format(str(res[0]['cnt'])))

    while (current_page < total_pages):
        # fetch API channel contents
        logging.warning("Channel {} {}: to fetch API: page {}/{} ({})".format(str(channel_id), str(channel_title), str(current_page + 1), str(total_pages), str(length)))
        response = requests.request(
            "GET",
            "http://api.are.na/v2/channels/" + str(channel_id) + "/contents",
            timeout=60,
            headers={"Authorization": "Bearer c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"},
            params={"per": per, "page": current_page + 1},
        )
        r = response.json()

        for block in r['contents']:

            # merge block
            logging.warning("Channel {} {}: Block {} {}: to merge".format(str(channel_id), str(channel_title), str(block['class']), str(block['id'])))
            props = block
            if 'contents' in props:
                del props['contents']
            props = flatten(props)
            res = g.run(
                """MERGE (b:Block {id: {id}})
                SET b += {props}
                """,
                id=block['id'],
                props=props
            ).stats()

            # create connection
            logging.warning("Channel {} {}: Block {} {}: to create block-channel rel {})".format(str(channel_id), str(channel_title), str(block['class']), str(block['id']), str(block['connection_id'])))
            props = {
                'id': block['connection_id'],
                'connected_at': block['connected_at'],
            }
            res = g.run(
                """MATCH (b:Block {id: {block_id}}), (c:Channel {id: {channel_id}})
                CREATE (b)-[r:CONNECTS_TO {props}]->(c)
                RETURN id(r) as id""",
                props=props,
                block_id=block['id'],
                channel_id=channel_id,
            ).data()
            logging.warning("Done: rel id {}".format(str(res[0]['id'])))

        current_page += 1




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)