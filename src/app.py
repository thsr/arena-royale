from flask import Flask, jsonify
from py2neo import Graph

app = Flask(__name__)

g = Graph("bolt://neo4j:7687", auth=('neo4j', 'pass'))

@app.route('/testinsert/<username>')
def testinsert(username):
    try:
        props = {
            'name':username, 
            'foo':'bar', 
            'fuzz':'buzz',
            'test':'and now',
        }
        res = g.run("CREATE (a:Testuser {props}) RETURN a", props=props).data()
        return jsonify(res)
    except Exception as e:
        return jsonify(e), 500

@app.route('/testfind')
def testfind():
    try:
        res = g.run("MATCH (a) RETURN labels(a) as labels, a").data()
        return jsonify(res)
    except Exception as e:
        return jsonify(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)