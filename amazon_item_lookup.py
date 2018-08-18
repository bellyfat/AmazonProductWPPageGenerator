# -*- coding: utf-8 -*-
"""
Amazon Product Advertising API Item Lookup Request Generator & Response Parser
API Docs: https://docs.aws.amazon.com/AWSECommerceService/latest/DG/ItemLookup.html

Request generation built with permission from:
https://github.com/brunodea/sdsoap/blob/e5407046bf543886151c1c51f4e4cccd29e8a4a8/exemplos/awsUrlBuilder.py

Created on Sun Jun 24 13:01:10 2018

@author: Daniel Koohmarey
"""
import xmltodict
import base64
import hashlib
import hmac
import time
import os
import urllib
import requests

class AmazonItemLookup():
    """ Class used to access parsed data from an Amazon Product Advertising API Item Lookup Request. """
    
    def __init__(self, aws_access_key, aws_secret_key, associate_tag):
        self.aws_access_key = aws_access_key
        self.aws_secret_key= aws_secret_key
        self.associate_tag = associate_tag

    def gen_item_lookup_request_url(self, item_id):
        """ Generates a signed item lookup request url as per amazon rest api requirements.
            Request signature spec: https://docs.aws.amazon.com/AWSECommerceService/latest/DG/rest-signature.html
            Signed requests can be verified at http://associates-amazon.s3.amazonaws.com/signed-requests/helper/index.html"""
    
        url_params = {
            'Service' : 'AWSECommerceService', 
            'Operation' : 'ItemLookup',
            'AWSAccessKeyId' : self.aws_access_key,
            'ResponseGroup' : 'EditorialReview,Images,ItemAttributes,OfferSummary,SalesRank',
            'ItemId' : item_id,
            'AssociateTag' : self.associate_tag,
            'Version' : '2013-08-01'
        }
    
        # Build the Signed a Request
        # 1. Enter the time stamp.
        url_params['Timestamp'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
     
        # 3./4. Sort the URL parameter / value pairs by byte value
        keys = url_params.keys()
        keys.sort()
        values = map(url_params.get, keys)
    
        # 2./5. Join the sorted param
        canonical_string = urllib.urlencode(zip(keys,values))
    
        # 6. Prepend the following string before the canonical string 
        string_to_sign = "GET\nwebservices.amazon.com\n/onca/xml\n%s" % canonical_string
    
        # 7./8. Calculate HMAC with SHA256 using the string to sign
        signature = hmac.new(
            key=self.aws_secret_key,
            msg=string_to_sign,
            digestmod=hashlib.sha256).digest()
        signature = base64.encodestring(signature).strip()
    
        # 9. URL encode the signature
        urlencoded_signature = urllib.quote_plus(signature)
        
        # 10. Add the signature to the request
        canonical_string += "&Signature=%s" % urlencoded_signature
    
        return "http://webservices.amazon.com/onca/xml?" + canonical_string

    def parse_item_response(self, response):
        """ Parses the xml response. Expected output (fields populated if available):
        {
            'item_attributes' : {
                'title' : '',
                'manufacturer' : '',
                'item_dimensions' : {
                    'height' : '',
                    'length' : '',
                    'weight' : '',
                    'width' : ''
                },
                'size' : '',
                'warranty' : '',
                'features' : []
            },
            'url' : '',
            'images' : {
                'small': {
                    'height': '',
                    'width': ''
                },
                'medium' : {
                    'height': '',
                    'width': ''        
                },
                'large' : {
                    'height': '',
                    'width': ''            
                }
            },
            'sales_rank' : '',
            'price' : '',
            'description' : ''
        }
        """
        result = xmltodict.parse(response)
        
        if result['ItemLookupResponse']['Items']['Request']['IsValid'] == 'False':
            try:
                print result['ItemLookupResponse']['Items']['Request']['Errors']['Error']['Message']
            except KeyError:
                print 'Error: Invalid lookup!'
            return  {}
            
        item = result['ItemLookupResponse']['Items']['Item']
        
        # Create default structure to hold parsed data
        parsed = {
            'item_attributes' : {
                'title' : '',
                'manufacturer' : '',
                'item_dimensions' : {
                    'height' : '',
                    'length' : '',
                    'weight' : '',
                    'width' : ''
                },
                'size' : '',
                'warranty' : '',
                'features' : []
            },
            'url' : '',
            'images' : {
                'small': {
                    'height': '',
                    'width': '',
                    'url': ''
                },
                'medium' : {
                    'height': '',
                    'width': '',
                    'url': ''
                },
                'large' : {
                    'height': '',
                    'width': '',
                    'url': ''
                }
            },
            'sales_rank' : '',
            'price' : '',
            'description' : ''
        }        
        
        # Parse features, if they exist
        if 'Feature' in item['ItemAttributes']:
            if isinstance(item['ItemAttributes']['Feature'], list):
                parsed['item_attributes']['features'].extend(item['ItemAttributes']['Feature'])
        else:
            parsed['item_attributes']['features'].append(item['ItemAttributes']['Feature'])

        # Parse item dimensions, if they exist
        item_dimensions = item['ItemAttributes'].get('ItemDimensions', {})
        if item_dimensions:
            if 'Height' in item_dimensions:
                parsed['item_attributes']['item_dimensions']['height'] = '{} ({})'.format(
                    item_dimensions['Height']['#text'], item_dimensions['Height']['@Units'])
            if 'Length' in item_dimensions:
                parsed['item_attributes']['item_dimensions']['length'] = '{} ({})'.format(
                    item_dimensions['Length']['#text'], item_dimensions['Length']['@Units'])
            if 'Weight' in item_dimensions:
                parsed['item_attributes']['item_dimensions']['weight'] = '{} ({})'.format(
                    item_dimensions['Weight']['#text'], item_dimensions['Weight']['@Units'])
            if 'Width' in item_dimensions:
                parsed['item_attributes']['item_dimensions']['width'] = '{} ({})'.format(
                    item_dimensions['Width']['#text'], item_dimensions['Width']['@Units'])
            
        # Parse remaining item attributes, if they exist
        parsed['item_attributes']['title'] = item['ItemAttributes'].get('Title', '')
        parsed['item_attributes']['manufacturer'] = item['ItemAttributes'].get('Manufacturer', '')
        parsed['item_attributes']['model'] = item['ItemAttributes'].get('Model', '')
        parsed['item_attributes']['size'] = item['ItemAttributes'].get('Size', '')
        parsed['item_attributes']['warranty'] = item['ItemAttributes'].get('Warranty', '')
        
        parsed['url'] = item.get('DetailPageURL', '')
        
        # Parse item images, if they exist
        if 'SmallImage' in item:
            parsed['images']['small']['height'] = item['SmallImage']['Height']['#text']
            parsed['images']['small']['width'] = item['SmallImage']['Width']['#text']
            parsed['images']['small']['url'] = item['SmallImage']['URL']
        
        if 'MediumImage' in item:
            parsed['images']['medium']['height'] = item['SmallImage']['Height']['#text']
            parsed['images']['medium']['width'] = item['SmallImage']['Width']['#text']
            parsed['images']['medium']['url'] = item['MediumImage']['URL']
            
        if 'LargeImage' in item:            
            parsed['images']['large']['height'] = item['LargeImage']['Height']['#text']
            parsed['images']['large']['width'] = item['LargeImage']['Width']['#text']
            parsed['images']['large']['url'] = item['LargeImage']['URL']
        
        parsed['sales_rank'] = item.get('SalesRank', '')
        
        # Parse lowest new price, if available'
        if 'OfferSummary' in item and 'LowestNewPrice' in item['OfferSummary']:
            parsed['price'] = item['OfferSummary']['LowestNewPrice'].get('FormattedPrice', '')
        
        # Parse item description, if available'
        if 'EditorialReviews' in item:
            if isinstance(item['EditorialReviews'], list):
                parsed['description'] = item['EditorialReviews'][0]
            else:
                parsed['description'] = item['EditorialReviews']['EditorialReview']['Content']
    
        return parsed
    
    def get_item_info(self, item_id):
        """ Returns a (dict) containing the parsed amazon product api response for a given item_id. """
        url = self.gen_item_lookup_request_url(item_id)
        resp = requests.get(url)
        if resp.status_code == 200:
            info = self.parse_item_response(resp.content)
            return info
        return {}
        
if __name__ == '__main__':    
    # Suggested setting up your Amazon Product API keys in your environment variables,
    # e.g in linux: export AWS_ACCESS_KEY_ID=abcd123
    # to avoid harcoding them in source
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')

    associate_tag = 'xxxxxxxx-20' # appears in top left after you login at https://affiliate-program.amazon.com/
    
    item_lookup = AmazonItemLookup(aws_access_key, aws_secret_key, associate_tag)    
    
    # e.g item_id = 'B00F0RRRCC' for https://www.amazon.com/Mediabridge-Ethernet-Cable-Feet-31-399-10B/dp/B00F0RRRCC/  
    item_id = raw_input('Enter item id to lookup: ')
    while(item_id):
        info = item_lookup.get_item_info(item_id)
        if info:
            print "Title: " + info['item_attributes']['title']
            print "Price: " + info['price']
            print "Features:\n - " + "\n - ".join(info['item_attributes']['features'])
        
        item_id = raw_input('Enter item id: ')