from datetime import datetime
from flask import Flask, jsonify, request
import json
import math
from py2neo import Graph
import requests




# const
# =====
API_TOKEN = "c3e339b184646e3fc8c6ee102c801b03a7d77282bd07d28112250b1cdf9d46d9"
# CHANNELS_TO_TEST = [142063, 419718, 422143, 422144, 411952    159627]
DEFAULT_USER_ID=33234
CHANNELS_TO_TEST = [142063, 419718, 422143, 422144, 411952]

GCS_PROJECT="thsr-project"
GCS_BUCKET="thsr-bucket"
GCS_CRED_FILE="./here.json"



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

def generate_epoch_filename(ext="jpg"):
    return str(int(datetime.now().timestamp()*1000)) + "." + ext




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
        b.clear_logfile()
        b.clear_db()
        res = b.go_for_it()
        return jsonify(res)

@app.route('/d', methods=['GET'])
def route_d():
    if request.method == 'GET':
        b = Backup()
        res = b.go_for_it()
        return jsonify(res)

@app.route('/e', methods=['GET'])
def route_e():
    if request.method == 'GET':
        blob_name = "arenaroyale/1561442550136.webm"#+generate_epoch_filename()
        url = "http://is2.4chan.org/gif/1561442550136.webm"
        res = gc_stuff.upload_to_gcs(blob_name, url)
        return jsonify(res)

@app.route('/f', methods=['GET'])
def route_f():
    if request.method == 'GET':
        b = Backup()
        b.clear_logfile()
        b.clear_db()
        res = b.go_for_it(test_mode=False)
        return jsonify(res)




# google cloud stuff
# ==================
from google.cloud import storage

class GCStuff:
    def __init__(self):
        self.cred_file = GCS_CRED_FILE
        self.storage_client = storage.Client.from_service_account_json(self.cred_file)
        self.bucket = self.storage_client.get_bucket(GCS_BUCKET)

    def upload_to_gcs(self, blob_name, url):
        blob = self.bucket.blob(blob_name)
        f = requests.get(url)
        blob.upload_from_string(data=f.content, content_type=f.headers['Content-Type'])
        blob.make_public()
        return str(blob.public_url)

gc_stuff = GCStuff()




# modules
# =======
class Backup:
    def __init__(self):
        pass

    def clear_logfile(self):
        open('./app.log', 'w').close()

    def clear_db(self):
        g.run("MATCH (n) DETACH DELETE n")

    def redo_user(self):
        u = User.from_api(user_id=DEFAULT_USER_ID)
        u.merge_in_db()

    def go_for_it(self, test_mode=True):
        logging.warning("starting backup, starting at user node, user_id " + str(DEFAULT_USER_ID))

        u = User.from_api(user_id=DEFAULT_USER_ID)

        u.merge_in_db()

        u.backup_channels(test_mode=test_mode)
        return "ok"




class User:
    def __init__(self, user):
        self._user = user
        self.id = user['id'] if 'id' in user else None
        self.slug = user['slug'] if 'slug' in user else None
        self._channels_from_db = []
        self._channels_from_api = []
        self._channel_relationships_to_create = []


    @classmethod
    def from_api(cls, user_id):
        res = self.fetch_one_from_api(user_id)
        return cls(res)


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
        _, all_channel_ids_from_db, all_channel_dates_from_db = Channel.fetch_all_from_db(return_raw=False, return_ids=True, return_dates=True)

        self.__delete_user_channel_relationships()
        self._channel_relationships_to_create = []

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
            if (c.id in all_channel_ids_from_db):
                old_updated_at = all_channel_dates_from_db[c.id]['updated_at']
                old_added_to_at = all_channel_dates_from_db[c.id]['added_to_at']
                new_updated_at = c.updated_at
                new_added_to_at = c.added_to_at

                if ((old_updated_at == new_updated_at) and (old_added_to_at == new_added_to_at)):
                    c.log("nothing to update or add")
                    continue

            # merge channel
            c.merge_in_db()

            # go thru channel's blocks if they're not too old
            if (c.length != 0):
                if (c.id in all_channel_ids_from_db):
                    cutoff_date = min(all_channel_dates_from_db[c.id]['updated_at'], all_channel_dates_from_db[c.id]['added_to_at'])
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

        if return_dates:
            res_dates = {
                o['id']: {
                    'updated_at': datetime.strptime(o['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                    'added_to_at': datetime.strptime(o['added_to_at'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                } for o in res_raw }
        else:
            res_dates = None

        if not return_raw:
            res_raw = None

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
        
        blocks_from_api = Block.fetch_all_from_api(channel_id=self.id)
        _, all_block_ids_from_db = Block.fetch_all_from_db(return_raw=False, return_ids=True)

        self.__delete_block_channel_relationships()
        self._block_relationships_to_create = []

        for block in blocks_from_api:
            b = Block(block)
            self._block_relationships_to_create.append(b.id)

            if (b.id not in all_block_ids_from_db):
                b.merge_in_db()

        self.__create_block_channel_relationships()

        return "ok"




class Block:
    def __init__(self, block):
        self._block = block
        self.id = block['id'] if 'id' in block else None
        self.class_ = block['class'] if 'class' in block else None
        self.created_at = datetime.strptime(block['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'created_at' in block else None
        self.updated_at = datetime.strptime(block['updated_at'], '%Y-%m-%dT%H:%M:%S.%fZ') if 'updated_at' in block else None
        self._other_backup_props = {}


    @classmethod
    def from_api(cls, block_id):
        res = self.fetch_one_from_api(block_id)
        return cls(res)


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
    def fetch_all_from_db(return_raw=True, return_ids=False):
        logging.warning(f"Fetching DB: all blocks")

        res_raw = g.run(
            """MATCH (c:Block)
            RETURN c.id as id
            """
        ).data()

        res_ids = [ o['id'] for o in res_raw ] if return_ids else None

        if not return_raw:
            res_raw = None

        return res_raw, res_ids


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

        logging.warning(f"Done fetching API: {str(len(res))} blocks")
        if len(res) != r['length']:
            logging.warning(f"Promised {str(r['length'])} blocks but gotten {str(len(res))}")

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