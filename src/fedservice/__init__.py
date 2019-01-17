from cryptojwt.key_jar import KeyJar, init_key_jar

from fedservice.entity_statement.collect import Collector
from fedservice.entity_statement.create import create_entity_statement
from fedservice.utils import eval_paths, load_json

__author__ = 'Roland Hedberg'
__version__ = '0.2.0'


class FederationEntity(object):
    def __init__(self, entity_id, trusted_roots, authority_hints=None, 
                 key_jar=None, default_lifetime=86400, httpd=None, 
                 priority=None, entity_type='', opponent_entity_type='',
                 registration_type=''):
        self.collector = Collector(trusted_roots=trusted_roots, httpd=httpd)
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.opponent_entity_type = opponent_entity_type
        self.key_jar = key_jar or KeyJar()
        for iss, jwks in trusted_roots.items():
            self.key_jar.import_jwks(jwks, iss)
        self.authority_hints = authority_hints
        self.default_lifetime = default_lifetime
        self.tr_priority = priority or sorted(set(trusted_roots.keys()))
        self.registration_type = registration_type

    def collect_entity_statements(self, response):
        return self.collector.collect_entity_statements(response)

    def eval_paths(self, node, entity_type='', flatten=True):
        if not entity_type:
            entity_type = self.opponent_entity_type

        return eval_paths(node, self.key_jar, entity_type, flatten)

    def create_entity_statement(self, metadata, iss, sub, key_jar=None,
                                authority_hints=None, lifetime=0, **kwargs):
        if not key_jar:
            key_jar = self.key_jar
        if not authority_hints:
            authority_hints = self.authority_hints
        if not lifetime:
            lifetime = self.default_lifetime

        return create_entity_statement(metadata, iss, sub, key_jar,
                                       authority_hints, lifetime, **kwargs)

    def load_entity_statements(self, iss, sub, op='', aud='', prefetch=False):
        return self.collector.load_entity_statements(iss, sub, op, aud,
                                                     prefetch)

    def pick_metadata(self, paths):
        """

        :param paths:
        :return:
        """
        if len(paths) == 1:
            fid = list(paths.keys())[0]
            # right now just pick the first:
            statement = paths[fid][0]
            return fid, statement.claims()
        else:
            for fid in self.tr_priority:
                try:
                    return fid, paths[fid][0]
                except KeyError:
                    pass

        # Can only arrive here if the federations I got back and trust are not
        # in the priority list. So, just pick one
        fid = list(paths.keys())[0]
        statement = paths[fid][0]
        return fid, statement.claims()


def create_federation_entity(entity_id, **kwargs):
    args = {}
    for param in ['trusted_roots', 'authority_hints']:
        try:
            args[param] = load_json(kwargs[param])
        except KeyError:
            pass

    if 'signing_keys' in kwargs:
        args['key_jar'] = init_key_jar(**kwargs['signing_keys'],
                                       owner=entity_id)

    for param in ['entity_type', 'priority', 'opponent_entity_type',
                  'registration_type']:
        try:
            args[param] = kwargs[param]
        except KeyError:
            pass

    return FederationEntity(entity_id, **args)
