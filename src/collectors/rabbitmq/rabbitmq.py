# coding=utf-8

"""
Collects data from RabbitMQ through the admin interface

#### Notes
 * if two vhosts have the queues with the same name, the metrics will collide

#### Dependencies

 * pyrabbit

"""

import diamond.collector
from diamond.collector import str_to_bool

try:
    from numbers import Number
    Number  # workaround for pyflakes issue #13
    import pyrabbit.api
except ImportError:
    Number = None


class RabbitMQCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(RabbitMQCollector, self).get_default_config_help()
        config_help.update({
            'host': 'Hostname and port to collect from',
            'user': 'Username',
            'password': 'Password',
            'ssl': 'Use SSL',
            'ignore_cert': 'Ignore certificate errors',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(RabbitMQCollector, self).get_default_config()
        config.update({
            'path':        'rabbitmq',
            'host':        'localhost:55672',
            'user':        'guest',
            'password':    'guest',
            'ssl':         'False',
            'ignore_cert': 'False',
        })
        return config

    def collect(self):
        if Number is None:
            self.log.error('Unable to import either Number or pyrabbit.api')
            return {}

        try:
            client = pyrabbit.api.Client(self.config['host'],
                                         self.config['user'],
                                         self.config['password'],
                                         ssl=str_to_bool(self.config['ssl']),
                                         no_verify=str_to_bool(self.config['ignore_cert']))

            for vhost in client.get_all_vhosts():
                for queue in client.get_queues(vhost=vhost['name']):
                    for key in queue:
                        name = '{0}.{1}'.format('queues', queue['name'])
                        self._publish_metrics(name, [], key, queue)

            overview = client.get_overview()
            for key in overview:
                self._publish_metrics('', [], key, overview)
        except Exception, e:
            self.log.error('Couldnt connect to rabbitmq %s', e)
            return {}

    def _publish_metrics(self, name, prev_keys, key, data):
        """Recursively publish keys"""
        value = data[key]
        keys = prev_keys + [key]
        if isinstance(value, dict):
            for new_key in value:
                self._publish_metrics(name, keys, new_key, value)
        elif isinstance(value, Number):
            joined_keys = '.'.join(keys)
            if name:
                publish_key = '{0}.{1}'.format(name, joined_keys)
            else:
                publish_key = joined_keys
            self.publish(publish_key, value)
