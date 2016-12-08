!/usr/bin/env python
# -*- coding: utf-8 -*-

#Import the libraries needed for the project
import re
import json
import xml.etree.cElementTree as ET
import pprint
from pymongo import MongoClient
from collections import defaultdict
print 'Libraries imported'


#Open the xml file (sample file or the complete file)
_file='sample.osm'

#Expected names for streets, avenues ... (in spanish)
#I audited a couple of times the xml and added new types to expected
expected = ['calle', 'avenida', 'plaza', 'parque', 'glorieta', 'paseo', 'ronda',
            'camino', 'carretera', 'bulevar', 'cuesta','pasaje', 'travesia', 'urbanizacion', 'autovia',
            'barrio', 'ciudad', 'sector', 'via', 'cuesta', 'bajada', 'puerta', 'rinconada', 'callejon', 'poligono', 'senda',
            'costanilla']
street_types =defaultdict(set)
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
                'tenerife':'calle', u'constitución':'calle', 'ginebra': 'Paseo', 'lina':'calle', 'real': 'calle',
                'campezo': 'calle', 'veredilla': 'calle', 'aguado': 'calle', 'venezuela':'calle', 'bucarmanga':'avenida',
                'fundidores': 'calle', 'paloma': 'calle', u'amnistía':'calle'}

#Postcodes in spain are 5digit codes. The first two digits are province codes. For madrid the province code is 28
#Hence all madrid postocodes need to start with 28 and be followed by 3 numbers.
postcode_re = re.compile(r'^[2][8][0-9]{3}\b')

#I audited it once and saw that some postocdes were prefaced with the letter E, indicdating Espana(spain). So
#those postcodes are good but need to be corrected so that they only have the 5digit code.
correct_postcode_re = re.compile(r'^[E][2][8][0-9]{3}\b')

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

# Function to check if the street name is a highway
def is_highway(street_name):
    return roads_re.search(street_name)

#function to check the different problems with street_names and its type.
def audit_street_type(street_types, street_name):
    what_street_type = street_types_re.search(street_name)
    if what_street_type:
        street_type=what_street_type.group().lower() ##make sure all in lower case to avoid duplicates
        if street_type not in expected and street_type not in corrections.keys()\
        and street_type not in modifications.keys() and is_highway(street_name)==None:
                street_types[street_type].add(street_name) ##return the weird ones

#function to check that postcodes are correct and print the problematic ones to see whats going on
def audit_postcode(postcode):
    valid_postcode = postcode_re.search(postcode)
    correctible_postcode = correct_postcode_re.search(postcode)
    if valid_postcode ==None and correctible_postcode==None:
        print postcode ##return the weird ones

#function to check that phone numbers are correct and the print the problematic ones
def audit_phonenumbers(phonenumber):
    num_string = phonenumber.replace(' ','')
    if len(num_string)<9:
        print num_string
    elif num_string.startswith('+') and len(num_string)!=12:
        print num_string ##return the weird ones


#audit function. I can specify exactly what I want to audit (phone numbers, street types, postcodes)
def audit(filename, what_to_audit):
    if what_to_audit == 'streets':
        for elem in get_element(filename):
            if elem.tag=='way' or elem.tag=='node':
                for tags in elem.iter('tag'):
                    if tags.attrib['k']=='addr:street':
                        audit_street_type(street_types, tags.attrib['v'])
    elif what_to_audit == 'postcodes':
        for elem in get_element(filename):
            if elem.tag=='way' or elem.tag=='node':
                for tags in elem.iter('tag'):
                    if tags.attrib['k']=='addr:postcode':
                        audit_postcode(tags.attrib['v'])
    elif what_to_audit == 'phones':
        for elem in get_element(filename):
            if elem.tag=='way' or elem.tag=='node':
                for tags in elem.iter('tag'):
                    if tags.attrib['k']=='contact:phone' or tags.attrib['k']=='phone':
                        audit_phonenumbers(tags.attrib['v'])



if __name__ == '__main__':
    ## I ran audit several times, checking phones, streets and postcodes.
    audit(_file, 'phones')
