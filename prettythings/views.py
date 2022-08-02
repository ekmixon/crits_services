import json

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import HttpResponse, render

from crits.core.user_tools import user_can_view_data
from . import handlers

@user_passes_test(user_can_view_data)
def main(request):
    return render(request, 'pt_main.html',
                              {})

@user_passes_test(user_can_view_data)
def campaign_heatmap(request):
    if request.method != "POST" or not request.is_ajax():
        return render(request, 'pt_campaign_heatmap.html',
                                  {})
    results = handlers.campaign_heatmap(request)
    return HttpResponse(json.dumps(results),
                        content_type="application/json")
