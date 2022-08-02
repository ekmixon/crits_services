import json

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import HttpResponse, render

from crits.core.user_tools import user_can_view_data
from . import handlers
from . import forms

@user_passes_test(user_can_view_data)
def run_filecarver(request, pcap_md5):
    if request.method != "POST" or not request.is_ajax():
        return render(request, 'error.html', {'error': "Must be AJAX."})
    form = forms.FileCarverForm(request.POST)
    data = (
        handlers.chopshop_carver(
            pcap_md5, form.cleaned_data, request.user.username
        )
        if form.is_valid()
        else {'success': False, 'message': "Invalid form data"}
    )

    return HttpResponse(json.dumps(data), content_type="application/json")

@user_passes_test(user_can_view_data)
def get_filecarver_config_form(request):
    if request.method != "GET" or not request.is_ajax():
        return render(request, 'error.html', {'error': "Must be AJAX."})
    tcp_form = {'form': forms.FileCarverForm().as_table()}
    return HttpResponse(json.dumps(tcp_form), content_type="application/json")
