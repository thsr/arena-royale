from datetime import datetime
from flask import Flask, jsonify
import json
import math
from py2neo import Graph
import requests

# utils
# =====
import logging
logging.basicConfig(filename='./app.log',level=logging.WARNING)

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
    open('./app.log', 'w').close()
    g.run("match (n)-[r]-() delete r, n")
    g.run("match (n) delete n")
    pass_through_channels()
    return "ok"

@app.route('/a')
def route_a():
    open('./app.log', 'w').close()
    pass_through_channels()
    return "ok"

@app.route('/b')
def route_b():
    pass_through_blocks(length=1)
    return "ok"

# funcs
# =====
def pass_through_channels(user_id=33234, channel_test=None):
    per = 100
    current_page = 0
    total_pages = 1
    
    while (current_page < total_pages):
        response = requests.request(
            "GET",
            "https://api.are.na/v2/users/" + str(user_id) + "/channels",
            timeout=60,
            headers={"Authorization": "Bearer c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"},
            params={"per": per, "page": current_page + 1},
        )
        r = response.json()
        
        db_channels = g.run(
            "MATCH (a:Channel) RETURN a.id as id, a.updated_at as updated_at, a.added_to_at as added_to_at"
        ).data()
        db_channels_ids = [ o['id'] for o in db_channels ]

        for channel in r['channels']:

            # test mode
            to_test=[142063, 419718, 422143, 422144, 420907, 420906]
            if channel['id'] not in to_test:
                logging.warning("Channel skipped in testing {} {}".format(str(channel['id']), str(channel['title'])))
                continue

            if channel['id'] not in db_channels_ids:
                # create channel in db
                data = channel
                del data['contents']
                del data['user']
                res = g.run(
                    "CREATE (a:Channel {data}) RETURN id(a) as id",
                    data=data
                ).data()
                logging.warning("Channel created {} {} - neo4j id {}".format(str(channel['id']), str(channel['title']), str(res[0]['id'])))

                # create/add/update blocks in channel
                pass_through_blocks(channel['id'], channel['length'])

                continue
            
            if channel['id'] in db_channels_ids:
                # collect update information
                db_updated_at = [ o['updated_at'] for o in db_channels if o['id'] == channel['id'] ][0]
                db_updated_at = datetime.strptime(db_updated_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                db_added_to_at = [ o['added_to_at'] for o in db_channels if o['id'] == channel['id'] ][0]
                db_added_to_at = datetime.strptime(db_added_to_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                updated_at = datetime.strptime(channel['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                added_to_at = datetime.strptime(channel['added_to_at'], '%Y-%m-%dT%H:%M:%S.%fZ')

                if ((updated_at>db_updated_at) or (added_to_at>db_added_to_at)):
                    # update channel props
                    data = channel
                    del data['contents']
                    del data['user']
                    res = g.run(
                        "MATCH (a:Channel {id: {id}}) SET a+={data} RETURN id(a) as id",
                        id=channel['id'],
                        data=data
                    ).data()
                    logging.warning("Channel info updated {} {} - neo4j id {}".format(str(channel['id']), str(channel['title']), str(res[0]['id'])))

                    # create/add/update blocks in channel
                    pass_through_blocks(channel['id'], channel['length'])
                    logging.warning("Channel blocks updated {} {}".format(str(channel['id']), str(channel['title']), str(res[0]['id'])))
                    continue

            logging.warning("Channel nothing to do {} {}".format(str(channel['id']), str(channel['title'])))

        current_page = r['current_page']
        total_pages = r['total_pages']

def pass_through_blocks(channel_id=142063, length=None):
    per = 100
    current_page = 0
    total_pages = math.ceil(length / per)
    
    while (current_page < total_pages):
        # get channel contents
        response = requests.request(
            "GET",
            "http://api.are.na/v2/channels/" + str(channel_id) + "/contents",
            timeout=60,
            headers={"Authorization": "Bearer c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"},
            params={"per": per, "page": current_page + 1},
        )
        r = response.json()

        # get blocks already in db
        db_blocks = g.run(
            """MATCH (a:Block), (a)-[b:CONNECTS_TO]-(:Channel {id: {channel_id}})
            RETURN a.id as id, a.updated_at as updated_at, b.id as connection_id""",
            channel_id=channel_id
            ).data()
        db_blocks_ids = [ o['id'] for o in db_blocks ]
        db_connection_ids = [ o['connection_id'] for o in db_blocks ]

        for block in r['contents']:
            
            if block['id'] not in db_blocks_ids:
                # create block
                data = block
                # del data['user']
                data = flatten(data)
                res = g.run(
                    "CREATE (a:Block {data}) RETURN id(a) as id", 
                    data=data
                ).data()
                logging.warning("\tBlock created {} {} - neo4j id {}".format(str(block['id']), str(block['title']), str(res[0]['id'])))

            if block['connection_id'] not in db_connection_ids:
                # create connection
                data = {
                    'id': block['connection_id'],
                    'connected_at': block['connected_at'],
                }
                res = g.run(
                    """MATCH (b:Block {id: {block_id}}), (c:Channel {id: {channel_id}})
                    CREATE (b)-[r:CONNECTS_TO {data}]->(c)
                    RETURN id(r) as id""",
                    data=data,
                    block_id=block['id'],
                    channel_id=channel_id,
                ).data()
                logging.warning("\t\tConnection created block{} channel{} - neo4j id {}".format(str(block['id']), str(channel_id), str(res[0]['id'])))

            if block['id'] in db_blocks_ids:
                # collect update information
                db_updated_at = [ o['updated_at'] for o in db_blocks if o['id'] == block['id'] ][0]
                db_updated_at = datetime.strptime(db_updated_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                updated_at = datetime.strptime(block['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')

                if (updated_at>db_updated_at):
                    # update block props
                    data = block
                    # del data['user']
                    data = flatten(data)
                    res = g.run(
                        "MATCH (a:Block {id: {id}}) SET a+={data} RETURN id(a) as id",
                        id=block['id'],
                        data=data
                    ).data()
                    logging.warning("\tBlock info updated {} {} - neo4j id {}".format(str(block['id']), str(block['title']), str(res[0]['id'])))

        current_page += 1

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)