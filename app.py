#!/usr/bin/python3

import os
import json
import flask
import hashlib
import urllib.parse

from bridge import Bridge


CONFIG = 'config.yaml'
CLIENT = os.getenv('CLIENTID') if os.getenv('CLIENTID') is not None else 'google'
TOKEN = hashlib.md5(CLIENT.encode('utf8')).hexdigest()


app = flask.Flask(__name__)


@app.errorhandler(400)
def error400(error):
    return flask.make_response(flask.jsonify({'error': 'Bad Request'}), 400)


@app.errorhandler(401)
def error401(error):
    return flask.make_response(flask.jsonify({'error': 'Bad Client'}), 401)


@app.errorhandler(404)
def error404(error):
    return flask.make_response(flask.jsonify({'error': 'Not Found'}), 404)


@app.route('/')
def root():
    flask.abort(404)


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    rtype = flask.request.values.get('response_type')
    client = flask.request.values.get('client_id')
    redirect = flask.request.values.get('redirect_uri')
    state = flask.request.values.get('state')

    if rtype != 'token' or redirect is None or \
       not redirect.startswith('https://oauth-redirect.googleusercontent.com/r/'):
        flask.abort(400)

    if client != CLIENT:
        flask.abort(401)

    args = urllib.parse.urlencode({
        'access_token': TOKEN,
        'token_type': 'bearer',
        'state': state
    })

    return flask.redirect('{}#{}'.format(redirect, args), code=302)


@app.route('/devices', methods=['GET', 'POST'])
def devices():
    auth = flask.request.headers.get('authorization')
    if auth is None:
        flask.abort(401)

    auth = auth.split()
    if len(auth) != 2 or auth[0].lower() != 'bearer':
        flask.abort(401)

    if auth[1] != TOKEN:
        flask.abort(401)

    try:
        req = flask.request.json
        req_id = req['requestId']
        inputs = req['inputs']
        if len(inputs):
            intent = inputs[0]['intent']
            payload = inputs[0]['payload'] if 'payload' in inputs[0] else None
        else:
            intent = None
            payload = None
    except Exception:
        flask.abort(400)

    print('  <<<', json.dumps(req))

    if intent is None:
        reply = { 'requestId': req_id }
        print('>>>', json.dumps(reply))
        return flask.jsonify(reply)

    if intent == 'action.devices.SYNC':
        reply = {
            'requestId': req_id,
            'payload': {
                'agentUserId': '12345',
                'devices': Bridge(CONFIG).sync()
            }
        }
        print('  >>>', json.dumps(reply))
        return flask.jsonify(reply)

    if intent == 'action.devices.QUERY':
        reply = {
            'requestId': req_id,
            'payload': {
                'devices': Bridge(CONFIG).query(list(map(lambda x: x['id'], payload['devices'])))
            }
        }
        print('  >>>', json.dumps(reply))
        return flask.jsonify(reply)

    if intent == 'action.devices.EXECUTE':
        reply = {
            'requestId': req_id,
            'payload': {
                'commands': list()
            }
        }

        bridge = Bridge(CONFIG)
        for command in payload['commands']:
            for execution in command['execution']:
                params = execution['params']
                for device in command['devices']:
                    try:
                        reply['payload']['commands'].append({
                            'ids': [device['id']],
                            'status': 'SUCCESS',
                            'states': bridge.execute(device['id'], execution['command'], params)
                        })
                    except Exception as e:
                        reply['payload']['commands'].append({
                            'ids': [device['id']],
                            'status': 'ERROR',
                            'errorCode': str(e)
                        })

        print('  >>>', json.dumps(reply))
        return flask.jsonify(reply)

    if intent == 'action.devices.DISCONNECT':
        print('  >>> {}')
        return flask.jsonify({})

    flask.abort(400)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
