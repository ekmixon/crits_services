import hashlib

from django.template.loader import render_to_string

from crits.core.user_tools import get_user_info
from crits.samples.handlers import handle_file
from crits.services.core import Service, ServiceConfigError
from crits.vocabulary.relationships import RelationshipTypes
from crits.vocabulary.acls import SampleACL

from . import forms

class CarverService(Service):
    name = "carver"
    version = '0.0.2'
    supported_types = ['Sample']
    description = "Carve a chunk out of a sample."

    @staticmethod
    def get_config(existing_config):
        # This service no longer uses config options, so blow away any existing
        # configs.
        return {}

    @staticmethod
    def valid_for(obj):
        if obj.filedata.grid_id is None:
            raise ServiceConfigError("Missing filedata.")

    @staticmethod
    def bind_runtime_form(analyst, config):
        if config:
            # The values are submitted as a list for some reason.
            data = {'start': config['start'][0], 'end': config['end'][0]}
        else:
            fields = forms.CarverRunForm().fields
            data = {name: field.initial for name, field in fields.iteritems()}
        return forms.CarverRunForm(data)

    @classmethod
    def generate_runtime_form(cls, analyst, config, crits_type, identifier):
        return render_to_string(
            'services_run_form.html',
            {
                'name': cls.name,
                'form': forms.CarverRunForm(),
                'crits_type': crits_type,
                'identifier': identifier,
            },
        )

    def run(self, obj, config):
        start_offset = config['start']
        end_offset = config['end']
        user = self.current_task.user

        if not user.has_access_to(SampleACL.WRITE):
            self._info("User does not have permission to add Samples to CRITs")
            self._add_result("Service Canceled", "User does not have permission to add Samples to CRITs")
            return

        # Start must be 0 or higher. If end is greater than zero it must
        # also be greater than start_offset.
        if start_offset < 0 or (end_offset > 0 and start_offset > end_offset):
            self._error("Invalid offsets.")
            return


        if data := obj.filedata.read()[start_offset:end_offset]:
            filename = hashlib.md5(data).hexdigest()
            handle_file(filename, data, obj.source,
                        related_id=str(obj.id),
                        related_type=str(obj._meta['crits_type']),
                        campaign=obj.campaign,
                        source_method=self.name,
                        relationship=RelationshipTypes.CONTAINS,
                        user=self.current_task.user)
            # Filename is just the md5 of the data...
            self._add_result("file_added", filename, {'md5': filename})
        else:
            self._error("No data.")
        return
