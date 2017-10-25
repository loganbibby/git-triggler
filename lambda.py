##########################################
## AWS Lambda Script
##  * Runtime: Python 2.7
##  * Handler: index.handler
##########################################

import hashlib
import urllib
import urllib2
import calendar
import time

HASH_ITERATIONS = 1000
TRIGGERS = {
    # repo-branch
    'stello:master': {
        # same token from server config
        'token': 'W9STlWYxY2hati4m71*X2SZFKgb^0UD2N^z^0PdjOp$EQ6@^bR',
        # server URL
        'url': 'http://0.0.0.0:5000',
        # hash iterations
        'iterations': 1000
    }
}

def handler(event, context):
    event = event['Records'][0]
    reponame = event['eventSourceARN'].split(':')[5]
    branch = event['codecommit']['references'][0]['ref'].split('/')[2]
    repokey = '%s:%s' % (reponame, branch)
    trigger = TRIGGERS[repokey]

    timestamp = calendar.timegm( time.gmtime() )

    signature = '%s:%s:%s' % (timestamp, repokey, trigger['token'])
    i = 0
    while i < trigger['iterations'] if 'iterations' in trigger.keys() else HASH_ITERATIONS:
        signature = hashlib.sha256(signature).hexdigest()
        i += 1

    request = urllib2.Request('%s/%s-%s' % (trigger['url'], reponame, branch))
    request.add_header('X-Signature', signature)
    request.add_header('X-Signature-Timestamp', timestamp)

    r = urllib2.urlopen(request)

    if r.getcode() == 200:
        return True
    else:
        print r.readlines()
        return False
