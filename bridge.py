import requests
import yaml
import os


try:
    import uwsgi
    import pickle

    def load():
        uwsgi.lock(0)
        size = uwsgi.sharedarea_readlong(0, 0)
        data = uwsgi.sharedarea_read(0, 8, size)
        uwsgi.unlock(0)
        return pickle.loads(data)

    def save(obj):
        data = pickle.dumps(obj, -1)
        uwsgi.lock(0)
        uwsgi.sharedarea_writelong(0, 0, len(data))
        uwsgi.sharedarea_write(0, 8, data)
        uwsgi.unlock(0)

    save(dict())

except ImportError:
    cache = dict()

    def load():
        global cache
        return cache

    def save(obj):
        global cache
        cache = obj


class Bridge:
    def __init__(self, path):
        data = load()
        if 'path' in data and data['path'] == path and os.stat(path).st_mtime == data['mtime']:
            config = data['config']
        else:
            data['path'] = path
            with open(path, 'r') as f:
                config = yaml.load(f)
                data['mtime'] = os.fstat(f.fileno()).st_mtime
            data['config'] = config
            save(data)

        self.url = config['openhab'].rstrip('/')
        self.devices = config['devices']
        self.timeout = config['timeout'] if 'timeout' in config else 5

    def _items(self):
        r = requests.get('{}/rest/items'.format(self.url), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _exec(self, item, state):
        r = requests.post('{}/rest/items/{}'.format(self.url, item), data=state, timeout=self.timeout)
        r.raise_for_status()

    def sync(self):
        r = list()

        for devid, device in self.devices.items():
            d = {
                'id': devid,
                'type': 'action.devices.types.{}'.format(device['type']),
                'name': { 'name': device['name'] },
                'traits': [],
                'willReportState': False,
                'deviceInfo': {
                    'manufacturer': 'PyProxy',
                    'model': device['type'],
                    'hwVersion': '1',
                    'swVersion': '1'
                }
            }

            if 'room' in device:
                d['roomHint'] = device['room']

            if 'attributes' in device:
                d['attributes'] = device['attributes']

            for trait, item in device['traits'].items():
                d['traits'].append('action.devices.traits.{}'.format(trait))

            r.append(d)

        return r

    def query(self, ids):
        devices = dict()
        items = dict()

        for item in self._items():
            items[item['name']] = item

        for devid in ids:
            if devid not in self.devices:
                continue

            device = self.devices[devid]

            d = {
                'online': True
            }

            for trait, itemid in device['traits'].items():
                if itemid not in items:
                    continue

                if 'state' not in items[itemid]:
                    continue

                state = items[itemid]['state']

                if trait == 'OnOff':
                    d['on'] = bool(state.lower() == 'on')
                    continue

                if trait == 'Brightness' and state.isdigit():
                    d['brightness'] = int(state) if int(state) > 0 else 1
                    continue

                if trait == 'ColorTemperature' and state.isdigit():
                    if 'color' not in d:
                        d['color'] = dict()
                    d['color']['temperature'] = int(state)
                    continue

            devices[devid] = d

        return devices

    def execute(self, devid, command, params):
        states = { 'online': True }

        if devid not in self.devices:
            return states

        traits = self.devices[devid]['traits']

        if command == 'action.devices.commands.OnOff':
            if 'OnOff' in traits:
                value = params['on']
                self._exec(traits['OnOff'], 'ON' if value else 'OFF')
                states['on'] = value

            return states

        if command == 'action.devices.commands.BrightnessAbsolute':
            if 'Brightness' in traits:
                value = str(params['brightness'])
                self._exec(traits['Brightness'], value)
                states['brightness'] = value

            return states

        if command == 'action.devices.commands.ColorAbsolute':
            if 'ColorTemperature' in traits and 'temperature' in params['color']:
                value = str(params['color']['temperature'])
                self._exec(traits['ColorTemperature'], value)
                if 'color' in states:
                    states['color']['temperature'] = value
                else:
                    states['color'] = { 'temperature': value }

            return states

        raise Exception('Unsupported command')
