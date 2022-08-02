import time
import logging
import simplejson
import urllib2

from django.conf import settings
from django.template.loader import render_to_string

from crits.services.core import Service, ServiceConfigError

from . import forms

logger = logging.getLogger(__name__)


class FarsightService(Service):
    """
    Check the Farsight DNSDB.

    Requires an API key available from Farsight
    """

    name = "farsight_lookup"
    version = '1.0.0'
    supported_types = ['Domain', 'IP']
    required_fields = []
    description = "Look up a Domain or IP in Farsight"

    @staticmethod
    def save_runtime_config(config):
        del config['farsight_api_key']
        del config['farsight_api_url']

    @staticmethod
    def get_config(existing_config):
        fields = forms.FarsightConfigForm().fields
        config = {name: field.initial for name, field in fields.iteritems()}
        # If there is a config in the database, use values from that.
        if existing_config:
            for key, value in existing_config.iteritems():
                config[key] = value
        return config

    @staticmethod
    def parse_config(config):
        if not config['farsight_api_key']:
            raise ServiceConfigError("API key required.")
        if not config['farsight_api_url']:
            raise ServiceConfigError('API url required.')

    @classmethod
    def generate_config_form(cls, config):
        # Convert sigfiles to newline separated strings
        html = render_to_string(
            'services_config_form.html',
            {
                'name': cls.name,
                'form': forms.FarsightConfigForm(initial=config),
                'config_error': None,
            },
        )

        form = forms.FarsightConfigForm
        return form, html

    @staticmethod
    def get_config_details(config):
        # Rename keys so they render nice.
        fields = forms.FarsightConfigForm().fields
        return {field.label: config[name] for name, field in fields.iteritems()}

    def run(self, obj, config):
        key = config.get('farsight_api_key', '')
        url = config.get('farsight_api_url', '')

        if not key:
            self._error("No valid Farsight key found")
            return

        if obj._meta['crits_type'] == 'IP':
            url = f'{url}/lookup/rdata/ip/{obj.ip}?limit=1000'
        elif obj._meta['crits_type'] == 'Domain':
            url = f'{url}/lookup/rrset/name/{obj.domain}?limit=1000'

        req = urllib2.Request(
            url, headers={'X-API-Key': f'{key}', 'Accept': 'application/json'}
        )


        if settings.HTTP_PROXY:
            proxy = urllib2.ProxyHandler({'https': settings.HTTP_PROXY})
            opener = urllib2.build_opener(proxy)
            urllib2.install_opener(opener)
        try:
            response = urllib2.urlopen(req)
            res = []
            while True:
                if line := response.readline():
                    res.append(simplejson.loads(line))

                else:
                    break
        except Exception as e:
            logger.error(f"Farsight: network connection error ({e})")
            self._error(f"Network connection error checking Farsight ({e})")
            return

        if not res:
            return

        # Results are stored in a dict, where the key is the rrtype and the
        # value is a list of dictionaries. They look like this:
        #
        # Domains:
        #
        # {'A': [{'Count': 1538,
        #         'First Time': '2010-10-03 21:58:57',
        #         'Last Time': '2016-03-04 07:18:33',
        #         'data': ['129.21.49.45']},
        #        {'Count': 3,
        #         'First Time': '2010-07-31 10:26:24',
        #         'Last Time': '2010-09-15 08:00:17',
        #         'data': ['129.21.50.215']}],
        #  'MX': [{'Count': 2006,
        #         'First Time': '2010-06-25 09:49:57',
        #         'Last Time': '2014-12-28 23:20:04',
        #         'data': ['10 syn.atarininja.org']},
        #         {'Count': 12,
        #         'First Time': '2016-01-03 00:32:46',
        #         'Last Time': '2016-03-02 21:52:27',
        #         'data': ['5 gmr-smtp-in.l.google.com',
        #                  '10 alt1.gmr-smtp-in.l.google.com',
        #                  '20 alt2.gmr-smtp-in.l.google.com',
        #                  '30 alt3.gmr-smtp-in.l.google.com',
        #                  '40 alt4.gmr-smtp-in.l.google.com']}],
        #
        # IPs:
        #
        # {'A': [{'Count': 417,
        #         'First Time': '2010-09-29 05:41:11',
        #         'Last Time': '2016-02-27 09:18:20',
        #         'data': ['syn.csh.rit.edu']},
        #        {'Count': 1538,
        #         'First Time': '2010-10-03 21:58:57',
        #         'Last Time': '2016-03-04 07:18:33',
        #         'data': ['atarininja.org']},
        #        {'Count': 8520,
        #         'First Time': '2010-09-29 02:26:51',
        #         'Last Time': '2016-03-03 16:43:34',
        #         'data': ['syn.atarininja.org']},
        #        {'Count': 206,
        #         'First Time': '2010-10-02 16:17:14',
        #         'Last Time': '2016-02-23 03:43:16',
        #         'data': ['donkeyonawaffle.org']},
        #        {'Count': 4598,
        #         'First Time': '2010-09-29 03:45:21',
        #         'Last Time': '2016-03-04 09:31:33',
        #         'data': ['syn.donkeyonawaffle.org']}]}
        results = {}
        for itm in res:
            if obj._meta['crits_type'] == 'Domain':
                key = 'rdata'
            elif obj._meta['crits_type'] == 'IP':
                key = 'rrname'

            stats = {
                'Count': itm.get('count', ''),
                'First Time': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(itm.get('zone_time_first', itm.get('time_first')))),
                'Last Time': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(itm.get('zone_time_last', itm.get('time_last')))),
                'data': [],
              }
            entry = itm.get(key, [])
            if isinstance(entry, list):
                for d in entry:
                    # Chop the trailing period.
                    if d[-1] == '.':
                        stats['data'].append(d[:-1])
                    else:
                        stats['data'].append(d)
            elif isinstance(entry, basestring):
                # Chop the trailing period.
                if entry[-1] == '.':
                    stats['data'].append(entry[:-1])
                else:
                    stats['data'].append(entry)
            else:
                # Not going to process this.
                continue

            rrtype = itm.get('rrtype', 'Unknown')
            if rrtype in results:
                results[rrtype].append(stats)
            else:
                results[rrtype] = [stats]

        for rrtype, stats_list in results.iteritems():
            for stats in stats_list:
                data = stats['data']
                del stats['data']
                for d in data:
                    self._add_result(rrtype, d, stats)
