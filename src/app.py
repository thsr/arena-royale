from datetime import datetime
from flask import Flask, jsonify, request
import json
import math
from py2neo import Graph
import requests




# const
# =====
# CHANNELS_TO_TEST = [142063, 419718, 422143, 422144, 411952    159627]
API_TOKEN = "c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"
CHANNELS_TO_TEST = [142063, 419718, 422143, 422144, 411952]




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
@app.route('/c', methods=['GET'])
def route_c():
    if request.method == 'GET':
        b = Backup()
        b.reset_logfile()
        b.reset_db()
        res = b.go_for_it()
        return jsonify(res)




# modules
# =======
class Backup:
    def __init__(self):
        pass

    def reset_logfile(self):
        open('./app.log', 'w').close()

    def reset_db(self):
        g.run("MATCH (n) DETACH DELETE n")

    def redo_user(self):
        u = User(user_id=33234)
        u.merge_in_db()

    def go_for_it(self):
        logging.warning("starting backup, starting at user node, user_id " + str(33234))

        u = User(user_id=33234)

        u.merge_in_db()

        u.backup_channels(test_mode=True)
        return "ok"




class User:
    def __init__(self, user=None, user_id=33234):
        if user is None:
            assert user_id is not None
            res = self.fetch_one_from_api(user_id)
            user = res
        self._user = user
        self.id = user['id'] if 'id' in user else None
        self.slug = user['slug'] if 'slug' in user else None
        self._channels_from_db = []
        self._channels_from_api = []
        self._channel_relationships_to_create = []


    @property
    def channel_ids_from_db(self):
        return [ o['id'] for o in self._channels_from_db ]


    @property
    def backup_props(self):
        props = self._user
        if 'contents' in props:
            del props['contents']
        return flatten(props)


    @staticmethod
    def fetch_one_from_api(user_id):
        logging.warning(f"Fetching API: user id {str(user_id)}")
        response = requests.request(
            "GET",
            "https://api.are.na/v2/users/" + str(user_id),
            timeout=60,
            headers={"Authorization": "Bearer " + API_TOKEN},
        )
        r = response.json()
        return r


    def log(self, message):
        logging.warning(f"User {str(self.id)} {str(self.slug).ljust(10)[0:10]}: {message}")


    def merge_in_db(self):
        self.log("merging user in db")
        g.run(
            """MERGE (c:User {id: {id}})
            SET c += {props}
            """,
            id=self.id,
            props=self.backup_props
        )


    def __create_user_channel_relationships(self):
        self.log("creating all user-channel rels")
        res = g.run(
            """MATCH (u:User {id: {user_id}}), (c:Channel)
            WHERE c.id in {list}
            MERGE (u)-[r:OWNS]->(c)
            RETURN count(r) as cnt""",
            user_id=self.id,
            list=self._channel_relationships_to_create,
        ).data()
        self.log(f"done created {str(res[0]['cnt'])} rels")


    def __delete_user_channel_relationships(self):
        self.log("deleting all user-channel rels")
        res = g.run(
            """MATCH (:User {id: {user_id}})-[r:OWNS]->(:Channel)
            DELETE r
            RETURN count(r) as cnt""",
            user_id=self.id,
        ).data()
        self.log(f"done deleted {str(res[0]['cnt'])} rels")


    def backup_channels(self, test_mode=False):
        self.log("starting backup of channels, test_mode " + ("On" if test_mode else "Off"))

        channels_from_api = Channel.fetch_all_from_api(user_id=self.id)

        self.__delete_user_channel_relationships()
        self._channel_relationships_to_create = []
        _, all_ids_from_db, all_dates_from_db = Channel.all_datetimes_from_db(return_raw=False, return_ids=True, return_dates=True)

        for channel in channels_from_api:
            c = Channel(channel)
            self._channel_relationships_to_create.append(c.id)

            # test mode
            if test_mode:
                to_test=CHANNELS_TO_TEST
                if c.id not in to_test:
                    c.log("skipping bcus testing")
                    continue

            # skip channel if not newly updated or added to
            if (c.id in all_ids_from_db):
                old_updated_at = all_dates_from_db[c.id]['updated_at']
                old_added_to_at = all_dates_from_db[c.id]['addded_to_at']
                new_updated_at = c.updated_at
                new_added_to_at = c.added_to_at

                if ((old_updated_at == new_updated_at) and (old_added_to_at == new_added_to_at)):
                    c.log("nothing to update or add")
                    continue

            # merge channel
            c.merge_in_db()

            # go thru channel's blocks if they're not too old
            if (c.length != 0):
                if (c.id in all_ids_from_db):
                    cutoff_date = min(all_dates_from_db[c.id]['updated_at'], all_dates_from_db[c.id]['addded_to_at'])
                else:
                    cutoff_date = datetime(1,1,1)

                c.backup_blocks(cutoff_date=cutoff_date)

        self.__create_user_channel_relationships()

        return "ok"




class Channel:
    def __init__(self, channel):
        self._channel = channel
        self.id = channel['id'] if 'id' in channel else None
        self.title = channel['title'] if 'title' in channel else None
        self.length = channel['length'] if 'length' in channel else None
        self.updated_at = datetime.strptime(channel['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'updated_at' in channel else None
        self.added_to_at = datetime.strptime(channel['added_to_at'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'added_to_at' in channel else None
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


    @staticmethod
    def fetch_all_from_db(return_raw=True, return_ids=False, return_dates=False):
        logging.warning(f"Fetching DB: all channels")

        res_raw = g.run(
            """MATCH (c:Channel)
            RETURN c.id as id, c.updated_at as updated_at, c.added_to_at as added_to_at
            """
        ).data()

        res_ids = [ o['id'] for o in res_raw ] if return_ids else None

        res_dates = { 
            o['id']: {
                'updated_at': datetime.strptime(o['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                'added_to_at': datetime.strptime(o['added_to_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
            }
            for o in res
        }
        res_dates = res_dates if return_dates else None

        return res_raw, res_ids, res_dates


    @staticmethod
    def fetch_all_from_api(user_id):
        res = []
        per = 100
        current_page = 0
        total_pages = 1

        while (current_page < total_pages):
            logging.warning(f"Fetching API: all channels for user {user_id}: page {str(current_page + 1)}/{str(total_pages)}")
            response = requests.request(
                "GET",
                "https://api.are.na/v2/users/" + str(user_id) + "/channels",
                timeout=60,
                headers={"Authorization": "Bearer " + API_TOKEN},
                params={"per": per, "page": current_page + 1},
            )
            r = response.json()
            
            res += r['channels']
        
            current_page = r['current_page']
            total_pages = r['total_pages']

        return res


    def log(self, message):
        logging.warning(f"Channel {str(self.id)} {str(self.title).ljust(10)[0:10]}: {message}")


    def merge_in_db(self):
        self.log("merging")
        g.run(
            """MERGE (c:Channel {id: {id}})
            SET c += {props}
            """,
            id=self.id,
            props=self.backup_props
        )


    def __create_block_channel_relationships(self):
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


    def __delete_block_channel_relationships(self):
        self.log("deleting all block-channel rels")
        res = g.run(
            """MATCH (:Block)-[r:CONNECTS_TO]->(c:Channel {id: {channel_id}})
            DELETE r
            RETURN count(r) as cnt""",
            channel_id=self.id,
        ).data()
        self.log(f"done deleted {str(res[0]['cnt'])} rels")


    def backup_blocks(self, cutoff_date=None):
        self.log("starting backup of blocks")
        
        self._blocks_from_api = Block.fetch_all_from_api(channel_id=self.id)

        self.__delete_block_channel_relationships()
        self._block_relationships_to_create = []

        for block in self._blocks_from_api:
            b = Block(block)
            self._block_relationships_to_create.append(b.id)

            if (b.cutoff_date < cutoff_date):
                b.log("old block nothing to do")
            else:
                b.merge_in_db()

        self.__create_block_channel_relationships()

        return "ok"




class Block:
    def __init__(self, block=None, block_id=None):
        if block is None:
            assert block_id is not None
            res = self.fetch_one_from_api(block_id)
            block = res
        self._block = block
        self.id = block['id'] if 'id' in block else None
        self.class_ = block['class'] if 'class' in block else None
        self.created_at = datetime.strptime(block['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'created_at' in block else None
        self.updated_at = datetime.strptime(block['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'updated_at' in block else None
        self._other_backup_props = {}
    
    def dotest(self):
        self._other_backup_props['aaaaaasthsth'] = "mydoodee"
        self._other_backup_props['aaaaaaqweqwe'] = 123123
    
    @property
    def backup_props(self):
        props = self._block
        if 'contents' in props:
            del props['contents']
        if 'connections' in props:
            del props['connections']
        return {**flatten(props), **self._other_backup_props}

    @property
    def cutoff_date(self):
        return max(self.created_at, self.updated_at)


    @staticmethod
    def fetch_one_from_api(block_id):
        logging.warning(f"Fetching API: block id {str(block_id)}")
        response = requests.request(
            "GET",
            "https://api.are.na/v2/blocks/" + str(block_id),
            timeout=60,
            headers={"Authorization": "Bearer " + API_TOKEN},
        )
        r = response.json()
        return r


    @staticmethod
    def fetch_all_from_api(channel_id):
        res = []
        per = 100
        current_page = 0
        total_pages = 1

        while (current_page < total_pages):
            logging.warning(f"Fetching API: all blocks for channel {channel_id}: page {str(current_page + 1)}/{str(total_pages)}")
        
            response = requests.request(
                "GET",
                "http://api.are.na/v2/channels/" + str(channel_id),
                timeout=60,
                headers={"Authorization": "Bearer " + API_TOKEN},
                params={"per": per, "page": current_page + 1},
            )
            r = response.json()

            res += r['contents']

            current_page += 1
            total_pages = math.ceil(r['length'] / per)

        assert len(res) == r['length']
        logging.warning(f"Done fetching API: {str(len(res))} blocks")

        return res


    def log(self, message):
        logging.warning(f"Block {str(self.class_).ljust(5)[0:5]} {str(self.id)}: {message}")


    def merge_in_db(self):
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