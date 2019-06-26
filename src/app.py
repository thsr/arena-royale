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
@app.route('/classdel')
def route_classdel():
    open('./app.log', 'w').close()
    g.run("MATCH (n) DETACH DELETE n")
    u = User()
    u.backup_channels(test_mode=True)
    return "ok"

@app.route('/classa')
def route_classa():
    u = User()
    u.backup_channels(test_mode=True)
    return "ok"




# modules
# =======
class User:
    def __init__(self, user_id=33234):
        self.id = user_id
        self._channels_from_db = []
        self._channels_from_api = []


    @property
    def channel_ids_from_db(self):
        return [ o['id'] for o in self._channels_from_db ]


    def __old_updated_at(self, channel_id):
        res = [ o['updated_at'] for o in self._channels_from_db if o['id'] == channel_id ][0]
        return datetime.strptime(res, '%Y-%m-%dT%H:%M:%S.%fZ')


    def __old_added_to_at(self, channel_id):
        res = [ o['added_to_at'] for o in self._channels_from_db if o['id'] == channel_id ][0]
        return datetime.strptime(res, '%Y-%m-%dT%H:%M:%S.%fZ')


    def __cutoff_date(self, channel_id):
        return min(self.__old_updated_at(channel_id), self.__old_added_to_at(channel_id))


    def log(self, message):
        logging.warning(f"User {str(self.id)}: " + message)


    def __fetch_channels_from_db(self):
        self._channels_from_db = []
        self.log(f"fetching all channels in db")
        res = g.run(
            """MATCH (c:Channel)
            RETURN c.id as id, c.updated_at as updated_at, c.added_to_at as added_to_at
            """
        ).data()
        self._channels_from_db = res


    def __fetch_channels_from_api(self):
        self._channels_from_api = []
        per = 100
        current_page = 0
        total_pages = 1

        while (current_page < total_pages):
            # fetch API for user
            self.log(f"fetching all channels API: page {str(current_page + 1)}/{str(total_pages)}")
            response = requests.request(
                "GET",
                "https://api.are.na/v2/users/" + str(self.id) + "/channels",
                timeout=60,
                headers={"Authorization": "Bearer c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"},
                params={"per": per, "page": current_page + 1},
            )
            r = response.json()
            
            self._channels_from_api += r['channels']
        
            current_page = r['current_page']
            total_pages = r['total_pages']


    def backup_channels(self, test_mode=False):
        self.log("starting backup of channels, test_mode " + ("On" if test_mode else "Off"))
        self.__fetch_channels_from_db()
        self.__fetch_channels_from_api()

        for channel in self._channels_from_api:
            c = Channel(channel)

            # test mode
            if test_mode:
                to_test=[142063, 419718, 422143, 422144,      159627]
                if c.id not in to_test:
                    c.log("skipping bcus testing")
                    continue

            # skip channel if not newly updated or added to
            if (c.id in self.channel_ids_from_db):
                old_updated_at = self.__old_updated_at(channel['id'])
                old_added_to_at = self.__old_added_to_at(channel['id'])
                new_updated_at = c.updated_at
                new_added_to_at = c.added_to_at

                if ((old_updated_at == new_updated_at) and (old_added_to_at == new_added_to_at)):
                    c.log("nothing to update or add")
                    continue

            # merge channel
            c.backup_merge()

            # go thru channel's blocks if they're not too old
            if (c.length != 0):
                if (c.id in self.channel_ids_from_db):
                    cutoff_date = self.__cutoff_date(c.id)
                else:
                    cutoff_date = datetime(1,1,1)

                c.backup_blocks(cutoff_date=cutoff_date)

        return "ok"




class Channel:
    def __init__(self, channel):
        self._channel = channel
        self.id = channel['id']
        self.title = channel['title']
        self.length = channel['length']
        self.updated_at = datetime.strptime(channel['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.added_to_at = datetime.strptime(channel['added_to_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        self._blocks_from_db = []
        self._blocks_from_api = []
        self._block_relationships_to_create = []


    @property
    def block_ids_from_api(self):
        return [ o['id'] for o in self._blocks_from_api ]


    @property
    def backup_props(self):
        props = self._channel
        if 'contents' in props:
            del props['contents']
        return flatten(props)


    def log(self, message):
        logging.warning(f"Channel {str(self.id)} {str(self.title).ljust(10)[0:10]}: " + message)


    def backup_merge(self):
        self.log("merging")
        g.run(
            """MERGE (c:Channel {id: {id}})
            SET c += {props}
            """,
            id=self.id,
            props=self.backup_props
        )


    def __create_block_relationships_to_channel(self):
        self.log("creating all block-channel rels")
        res = g.run(
            """MATCH (b:Block), (c:Channel {id: {channel_id}})
            WHERE b.id in {list}
            MERGE (b)-[r:CONNECTS_TO]->(c)
            RETURN count(r) as cnt""",
            channel_id=self.id,
            list=self._block_relationships_to_create,
        ).data()
        self.log(f"done created {str(res[0]['cnt'])} rels")


    def __delete_block_relationships_to_channel(self):
        self.log("deleting all block-channel rels")
        res = g.run(
            """MATCH (:Block)-[r:CONNECTS_TO]->(c:Channel {id: {channel_id}})
            DELETE r
            RETURN count(r) as cnt""",
            channel_id=self.id,
        ).data()
        self.log(f"done deleted {str(res[0]['cnt'])} rels")


    def __fetch_blocks_from_api(self):
        self._blocks_from_api = []
        per = 100
        current_page = 0
        total_pages = math.ceil(self.length / per)

        while (current_page < total_pages):
            self.log(f"fetching API: page {str(current_page + 1)}/{str(total_pages)} ({str(self.length)})")
        
            response = requests.request(
                "GET",
                "http://api.are.na/v2/channels/" + str(self.id),# + "/contents",
                timeout=60,
                headers={"Authorization": "Bearer c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"},
                params={"per": per, "page": current_page + 1},
            )
            r = response.json()

            self._blocks_from_api += r['contents']

            current_page += 1

        assert len(self._blocks_from_api) == r['length']


    def backup_blocks(self, cutoff_date=None):
        self.log("starting backup of blocks")
        self.__fetch_blocks_from_api()
        self.__delete_block_relationships_to_channel()
        self._block_relationships_to_create = []

        for block in self._blocks_from_api:
            b = Block(block)

            if (b.cutoff_date < cutoff_date):
                b.log("old block nothing to do")
            else:
                b.backup_merge()

            self._block_relationships_to_create.append(b.id)

        self.__create_block_relationships_to_channel()

        return "ok"




class Block:
    def __init__(self, block):
        self._block = block
        self.id = block['id']
        self.class_ = block['class']
        self.created_at = datetime.strptime(block['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        self.updated_at = datetime.strptime(block['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
    
    @property
    def backup_props(self):
        props = self._block
        if 'contents' in props:
            del props['contents']
        return flatten(props)
    
    @property
    def cutoff_date(self):
        return max(self.created_at, self.updated_at)


    def log(self, message):
        logging.warning(f"Block {str(self.class_).ljust(5)[0:5]} {str(self.id)}: " + message)


    def backup_merge(self):
        self.log("merging")
        g.run(
            """MERGE (b:Block {id: {id}})
            SET b += {props}
            """,
            id=self.id,
            props=self.backup_props
        )




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)