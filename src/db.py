from py2neo import Graph
import os



g = Graph("bolt://neo4j:7687", auth=(os.environ.get('NEO4J_USER'), os.environ.get('NEO4J_PASSWORD')))