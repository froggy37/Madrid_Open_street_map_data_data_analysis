#!/usr/bin/env python
# -*- coding: utf-8 -*-#

#Import the libraries needed for the project
import re
import json
import xml.etree.cElementTree as ET
import pprint
import codecs
from pymongo import MongoClient
from collections import defaultdict
print 'Libraries imported'

data_json = 'madrid_spain.osm.json'

#connect to MongoDB database
client = MongoClient("localhost:27017")
db = client.test
print 'connected'

#size of collection
print db.command('dbstats')

#most popular cuisine
def cuisine_pipeline():
    pipeline = [{'$match':{'cuisine':{'$exists':1}}}, {'$group':{'_id':'$cuisine', 'count':{'$sum':1}}}, {'$sort':{'count':-1}},{'$limit':5}]
    return pipeline

#number of single contributing users
def single_contributions():
    pipeline=[{'$group':{'_id':'$created.user', 'count':{'$sum':1}}},
            {'$group':{'_id':'$count', 'contributions':{'$sum':1}}}, {'$sort':{'contributions':1}}, {'$limit':1}]
    return pipeline

#rarest amenities
def rarest_amenities():
    pipeline = [{'$match':{'amenity':{'$exists':1}}}, {'$group':{'_id':'$amenity', 'count':{'$sum':1}}},
                {'$sort':{'count':1}}, {'$limit':5}]
    return pipeline

#number of unique users
print 'number of unique users', len(db.Madrid.distinct('created.user'))

#number of nodes
print 'number of nodes:', db.Madrid.find({'type':'node'}).count()

#number of ways
print 'number of ways:', db.Madrid.find({'type':'way'}).count()

#number of shops
print 'number of shops:', db.Madrid.find({'amenity':'shop'}).count()

#most popular cuisine
print 'most popular cuisines:'
for i in db.Madrid.aggregate(cuisine_pipeline()):
    print i

#largest contributors
print '10 greatest contributors:'
for i in db.Madrid.aggregate([{'$group':{'_id':'$created.user', 'count':{'$sum':1}}}, {'$sort':{'count':-1}},{'$limit':10}]):
    print i

#number of single contributing users
print 'number of single contributing users:'
for i in db.Madrid.aggregate(single_contributions()):
    print i

#rarest amenities
print '5  rarest amenities:'
for i in db.Madrid.aggregate(rarest_amenities()):
    print i
