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

##DATABSE STRUCTURE:
#{
#"id": "2406124091",
#"type: "node",
#"visible":"true",
#"created": {
          #"version":"2",
          #"changeset":"17206049",
          #"timestamp":"2013-08-03T16:43:42Z",
          #"user":"linuxUser16",
          #"uid":"1219059"
        #},
#"pos": [41.9757030, -87.6921867],
#"address": {
          #"housenumber": "5157",
          #"postcode": "60625",
          #"street": "North Lincoln Ave"
        #},
#"amenity": "restaurant",
#"cuisine": "mexican",
#"name": "La Cabana De Don Luis",
#"phone": "1 (773)-271-5176",
#"node_refs": ["305896090", "1719825889"],
#}

#Open the xml file (sample file or the complete file)
_file='madrid_spain.osm'

#Expected names for streets, avenues ... (in spanish)
#I audited a couple of times the xml and added new types to expected
expected = ['calle', 'avenida', 'plaza', 'parque', 'glorieta', 'paseo', 'ronda',
            'camino', 'carretera', 'bulevar', 'cuesta','pasaje', 'travesia', 'urbanizacion', 'autovia',
            'barrio', 'ciudad', 'sector', 'via', 'cuesta', 'bajada', 'puerta', 'rinconada', 'callejon', 'poligono', 'senda',
            'costanilla']
# In spanish the type of street appears first, so I have to match the start of a string (ex: Calle Maria de Molina)
street_types_re = re.compile(r'^\b\S+\.?', re.IGNORECASE)

#Regular expression to match highway codes. These always start with a letter - number (ex: A-1, M-30, l-91...)
roads_re=re.compile(r'(([a-z]|[A-Z])\-[0-9]+)')

#These are corrections of street types, some are abbreviation corrections, others are conversion of unicode(accents) to words with
#no accents.
corrections ={'av': 'avenida', 'av.': 'avenida', 'call': 'calle', 'ctra': 'carretera', 'ctra.':'carretera', 'ctra,':'carretera',
            'crta':'carretera', 'crta.': 'carretera', 'carrterera':'carretera', 'pasage':'pasaje', 'avda.':'avenida', 'avda':'avenida',
            u'travesía': 'travesia', u'callejón':'callejon', 'rcda':'rinconada', 'corredera':'calle',
            'carrera':'calle', u'urbanización':'urbanizacion', u'autovía':'autovia', 'urb.':'urbanizacion', u'vía':'via',
            u'pol\xef\xbf\xbd\xef\xbf\xbdgono':'poligono', u'calleja/callej\xef\xbf\xbd\xef\xbf\xbdn':'callejon',
            u'prolongación': 'calle', 'cr': 'carretera', 'gran': 'calle'}

#These are modifications to street types. Some streets did not have a street type (they just had a name)
#so I manually introduced their street type.
modifications = {'santa':'calle', 'virgen':'calle', 'san':'calle', 'ermita':'calle', 'daoiz':'calle', 'francisco': 'calle',
                'salvador': 'calle', u'josé':'calle', u'fermín':'calle', 'antonio':'calle', 'rafaela':'calle',
                'camilo': 'calle', 'fuencarral': 'calle', 'goya': 'calle', 'ventura': 'calle', 'sierra':'calle',
                'tenerife':'calle', u'constitución':'calle', 'ginebra': 'paseo', 'lina':'calle', 'real': 'calle',
                'campezo': 'calle', 'veredilla': 'calle', 'aguado': 'calle', 'venezuela':'calle', 'bucarmanga':'avenida',
                'fundidores': 'calle', 'paloma': 'calle', u'amnistía':'calle'}

#Postcodes in spain are 5digit codes. The first two digits are province codes. For madrid the province code is 28
#Hence all madrid postocodes need to start with 28 and be followed by 3 numbers.
postcode_re = re.compile(r'^[2][8][0-9]{3}\b')

#I audited it once and saw that some postocdes were prefaced with the letter E, indicdating Espana(spain). So
#those postcodes are good but need to be corrected so that they only have the 5digit code.
correct_postcode_re = re.compile(r'^[E][2][8][0-9]{3}\b')

#create a function to stop the iterparse function to commit the complete tree to memory.

#create a function to stop the iterparse function to commit the complete tree to memory.
def get_element(osm_file):
    """ Reference:
    http://stackoverflow.com/questions/3095434/inserting-newlines-in-xml-file-generated-via-xml-etree-elementtree-in-python
    """
    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end':
            yield elem
            root.clear()

CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
cordinates =["lat","lon"]

##function to clean the street names and types using the dictionaries that were manually producef after iterativel running audit.py
def clean_street(tag):
    street_name = tag.attrib['v']
    what_street_type = street_types_re.search(street_name)
    if what_street_type:
        street_type=what_street_type.group().lower()
        if street_type in corrections.keys():
            street_type = corrections[street_type]
            return street_type, street_name
        elif street_type in modifications.keys():
            #because street type is missing i want to concanate the street type to the street name
            street_name = modifications[street_type] + ' ' + street_name
            street_type = modifications[street_type]
            return street_type, street_name
        #highways need their own street type
        elif roads_re.search(street_type):
            street_type='highway'
            return street_type, street_name
        elif street_type in expected:
            return street_type, street_name
        else:
            return None, None
    else:
        return None, None

#function to clean the postcodes, using the regex.
def clean_postcode(tag):
    postcode = tag.attrib['v']
    if postcode_re.search(postcode):
        return postcode
    elif correct_postcode_re.search(postcode):
        postcode=postcode[1:]
        return postcode
    else:
        return None

#function to clean phone numbers. This is making sure that numbers are made of 9 digits without prefix or 12 digits with a + at the
# start. Then it returns phone numbers in one of those formats.
def clean_phone(phone_number):
    num_string = phone_number.replace(' ','')
    if len(num_string)==9:
        try:
            int(num_string)
            return num_string
        except:
            pass
    elif num_string.startswith('+') and len(num_string)==12:
        try:
            int(num_string[1:])
            return num_string
        except:
            pass
    elif num_string.startswith('+00') and len(num_string)==14:
        try:
            int(num_string[3:])
            return num_string[0] + num_string[3:]
        except:
            pass
    elif num_string.startswith('0034') and len(num_string)==13:
        try:
            int(num_string[2:])
            return '+' + num_string[2:]
        except:
            pass
    ## numbers made of two different numbers need to call the two_phonenumbers function first to split.
    elif len(num_string.split('/'))>1:
        try:
            two_phonenumbers(num_string, '/')
        except:
            pass
    ## numbers made of two different numbers need to call the two_phonenumbers function first to split.
    elif len(num_string.split(','))>1:
        try:
            two_phonenumbers(num_string, ',')
        except:
            pass
    else:
        return None

#function splits phone numbers that are made up of two numbers and then passes each of those number to clean_phone function
def two_phonenumbers(num_string, parameter):
    num_list = num_string.split(parameter)
    for num in num_list:
        clean_phone(num)

## for each element it examines the data, cleans it and creates a list of dictinaries of key value pairs
def shape_element(element):
    node = {}
    ## Some postcodes are not from Madrid, so elements that contain a postcode not from madrid need to be ignored entirely.
    if element.tag == "node" or element.tag == "way":
        for tags in element.iter('tag'):
            if tags.attrib['k']=='addr:postcode':
                if postcode_re.search(tags.attrib['v'])==None and correct_postcode_re.search(tags.attrib['v'])==None:
                    return None
        ## nested documents
        node['id']=element.attrib['id']
        node['type']=element.tag
        node['created']=dict()
        node['pos']=list()
        node['address']=dict()
        node['node_refs']=list()
        node['phone']=list()
        ## visible is not always there, hence try.
        try:
            node['visible']=element.attrib['visible']
        except:
            pass
        for attributes in element.attrib.keys():
            if attributes in CREATED:
                node['created'][attributes]=element.attrib[attributes]
            elif attributes =='lat':
                node['pos'].append(element.attrib[attributes])
            elif attributes =='lon':
                node['pos'].append(element.attrib[attributes])
        for tag in element.iter('tag'):
            if tag.attrib['k'].startswith('addr:'):
                    if tag.attrib['k']=='addr:street':
                        node['address'][clean_street(tag)[0]]=clean_street(tag)[1]
                    elif tag.attrib['k']=='addr:postcode':
                        node['address']['postcode']=clean_postcode(tag)
            elif tag.attrib['k']=='amenity':
                node['amenity']=tag.attrib['v']
            elif tag.attrib['k']=='cuisine':
                node['cuisine']=tag.attrib['v']
            elif tag.attrib['k']=='name':
                node['name']=tag.attrib['v']
            elif tag.attrib['k']=='contact:phone' or tag.attrib['k']=='phone':
                node['phone'].append(clean_phone(tag.attrib['v']))
        for ref in element.iter('nd'):
            node['node_refs'].append(ref.attrib['ref'])
        ## Remove empty values from the dictionary
        nodee = {k:v for k,v in node.items() if v}
        return nodee
    else:
        return None

##function to write the json file. Calls the shape_element funnction one element at a time
def process_map(file_in, pretty = False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for element in get_element(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data

if __name__ == '__main__':
    process_map(_file, pretty = False)
