from datetime import datetime
import calendar
import hashlib
import subprocess
import os
from flask import Flask, request, make_response, jsonify

app = Flask('git-trigger')
app.config.from_object('config')

def make_error(msg, httpcode=500, data={}):
    response = { 'error': { 'msg': msg } }
    response['error'].update( data )
    app.logger.error('Error response [%d]: %s - Data: %s' % (httpcode, msg, data))
    return make_response(jsonify(response), httpcode)

def run_shell(cmd):
    app.logger.debug('Running command in shell: %s' % cmd)
    try:
        o = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        )
        app.logger.debug(o)
        return o
    except subprocess.CalledProcessError as e:
        app.logger.error('Unable to run command: %s' % cmd)
        app.logger.debug(e.output)

@app.route('/<repo>-<branch>')
def trigger(repo, branch):
    ####
    ## Auth
    ####
    repokey = '%s:%s' % (repo, branch)
    if repokey not in app.config['TRIGGERS'].keys():
        return make_error('No trigger for repo: %s' % repo, 404)

    trigger = app.config['TRIGGERS'][repokey]

    signature = request.headers.get('X-Signature', None)
    timestamp = request.headers.get('X-Signature-Timestamp', None)

    if not signature or not timestamp:
        return make_error('Missing signature and timestamp headers', 400)

    try:
        timestamp = datetime.fromtimestamp( int(timestamp) )
    except ValueError:
        return make_error('Timestamp must be in seconds since UNIX epoch.', 400)

    timestamp_delta = datetime.utcnow()-timestamp

    if timestamp_delta.total_seconds() > app.config['SIG_TIMESTAMP_EXPIRATION']:
        return make_error('Timestamp is too old: %d' % timestamp_delta.total_seconds(), 400)

    if timestamp_delta.total_seconds() < app.config['SIG_TIMESTAMP_FUTURE']:
        return make_error('Timestamp cannot be in future: %d' % timestamp_delta.total_seconds(), 400)

    timestamp = calendar.timegm( timestamp.timetuple() )

    hash_ = '%s:%s:%s' % (timestamp, repokey, trigger['token'])

    i = 0
    while i < trigger['iterations'] if 'iterations' in trigger.keys() else app.config['SIG_HASH_ITERATIONS']:
        hash_ = hashlib.sha256(hash_).hexdigest()
        i += 1

    if hash_ != signature:
        return make_error('Invalid signature', 401)

    ####
    ## PROCESSING
    ####

    try:
        run_shell( trigger['cmd'] )
    except subprocess.CalledProcessError:
        return make_error('Cannot run command', 500)

    return jsonify({'success': {'msg': 'Trigger received and processed successfully'}})

if __name__ == '__main__':
    app.run(debug=True)
