import logging
import json
import requests

from django.template.loader import render_to_string

from crits.services.core import Service, ServiceConfigError

from . import forms

logger = logging.getLogger(__name__)

class OpenDNSService(Service):
    """
    Request more information about an artifacts from OpenDNS
    """

    name = "opendns_investigate"
    version = '1.0.0'
    template = "opendns_service_template.html"
    supported_types = [ 'Domain', 'IP' ]
    description = "Lookup domains and IPs in OpenDNS."

    @staticmethod
    def get_config(existing_config):
        fields = forms.OpenDNSConfigForm().fields
        config = {name: field.initial for name, field in fields.iteritems()}
        # If there is a config in the database, use values from that.
        if existing_config:
            for key, value in existing_config.iteritems():
                config[key] = value
        return config

    @staticmethod
    def parse_config(config):
        if not config['Investigate_API_Token']:
            raise ServiceConfigError("API token required.")

    @staticmethod
    def get_config_details(config):
        # Rename keys so they render nice.
        fields = forms.OpenDNSConfigForm().fields
        return {field.label: config[name] for name, field in fields.iteritems()}

    @classmethod
    def generate_config_form(cls, config):
        html = render_to_string(
            'services_config_form.html',
            {
                'name': cls.name,
                'form': forms.OpenDNSConfigForm(initial=config),
                'config_error': None,
            },
        )

        form = forms.OpenDNSConfigForm
        return form, html

    @staticmethod
    def save_runtime_config(config):
        del config['Investigate_API_Token']

    def _replace(self, string):
        return string.replace("_", " ")

    def run(self, obj, config):
        token = config.get('Investigate_API_Token', '')
        uri = config.get('Investigate_URI', '')
        headers = {'Authorization': f'Bearer {token}'}
        reqs = {}
        resps = {}
        scores = {u'-1': 'Bad', u'0': 'Unknown', u'1': 'Good'}

        if not token:
            self._error("A valid API token is required to use this service.")

        if obj._meta['crits_type'] == 'Domain':
            thing = obj.domain
            reqs["categorization"] = f"/domains/categorization/{thing}?showLabels"
            reqs["score"] = f"/domains/score/{thing}"
            reqs["recommendations"] = f"/recommendations/name/{thing}.json"
            reqs["links"] = f"/links/name/{thing}.json"
            reqs["security"] = f"/security/name/{thing}.json"
            reqs["latest_tags"] = f"/domains/{thing}/latest_tags"
            reqs["dnsdb"] = f"/dnsdb/name/a/{thing}.json"
        elif obj._meta['crits_type'] == 'IP':
            thing = obj.ip
            reqs["dnsdb"] = f"/dnsdb/ip/a/{thing}.json"
            reqs["latest_domains"] = f"/ips/{thing}/latest_domains"
        else:
            logger.error("Unsupported type.")
            self._error("Unsupported type.")
            return

        try:
            for r in reqs:
                resp = requests.get(uri + reqs[r], headers=headers)

                if resp.status_code == 204:
                    logger.error(f"No content status returned from request: {r}")
                    self._error(f"No content status returned from request: {r}")
                    resps[r] = f"No content status returned from request: {r}"
                elif resp.status_code != 200:
                    logger.error(f"Request: {r}, error, {resp.reason}")
                    self._error(f"Request: {r}, error, {resp.reason}")
                    resps[r] = f"Request: {r}, error, {resp.reason}"
                else:
                    resps[r] = json.loads(self._replace(resp.content))

        except Exception as e:
            logger.error(f"Network connection or HTTP request error ({e})")
            self._error(f"Network connection or HTTP request error ({e})")
            return

        for r, value in resps.items():
            if r == 'categorization':
                self._add_result(r, thing, value[thing])
            elif r == 'score':
                self._add_result(r, thing, {'Score': scores[resps[r][thing]]})
            elif r == 'dnsdb':
                self._add_result(r, thing, resps[r]['features'])
            elif r == 'security':
                self._add_result(r, thing, resps[r])
            elif r == 'latest_tags':
                for tag in resps[r]:
                    self._add_result(r, thing, tag)
            elif r == 'recommendations':
                self._add_result(r, thing, resps[r])
            elif r == 'links':
                self._add_result(r, thing, resps[r])
            elif r == 'latest_domains':
                for domain in resps[r]:
                    self._add_result(r, domain['name'], domain)
            else:
                self._add_result(r, thing, {str(type(resps[r])): str(resps[r])})
                logger.error(f"Unsure how to handle {str(resps[r])}")
                self._error(f"Unsure how to handle {str(resps[r])}")
