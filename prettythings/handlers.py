from crits.campaigns.campaign import Campaign
from crits.events.event import Event
from crits.emails.email import Email

def campaign_heatmap(request):
    campaigns = Campaign.objects().only('name', 'aliases', 'locations')
    events = Event.objects().only('title', 'created', 'locations', 'campaign')
    emails = Email.objects().only('created', 'locations', 'campaign')

    # list of countries in alphabetical order. set 0 for the amount of campaign
    # associated with this country for the next step.
    country_list = []
    for c in campaigns:
        if len(c.locations):
            for l in c.locations:
                if [l.location,0] not in country_list:
                    country_list.append([l.location,0])
    country_list.sort()
    # For those campaigns with no location assigned, have an Unknown location.
    country_list.append(['Unknown', 0])

    # list of campaigns in order of country, then alphabetical by name
    campaign_list = []
    # for each country we build a tmp list, find all campaigns for that country,
    # sort the list, then append it to the campaign list. bump the count so we
    # know how many columns to span.
    for c in country_list:
        tmp = []
        for cam in campaigns:
            if len(cam.locations):
                for l in cam.locations:
                    if l.location == c[0]:
                        c[1] += 1
                        if cam.name not in tmp:
                            tmp.append(cam.name)
                        break
            elif c[0] == 'Unknown':
                c[1] += 1
                if cam.name not in tmp:
                    tmp.append(cam.name)
        # If we haven't added a campaign to this location, show "No Campaigns".
        # This also prevents a left-shift in the counting and header rows.
        if not tmp:
            tmp.append("No Campaigns")
        tmp.sort()
        campaign_list += tmp

    # for each campaign, find associated events and emails. For each event and
    # email, use the created date to put it into the appropriate list.
    month_d = {}
    # this is a default row in the heatmap with all values set to 0.
    pad_list = [0 for _ in range(len(campaign_list))]
    for idx, c in enumerate(campaign_list):
        build_month_d(pad_list, month_d, c, idx, events)
        build_month_d(pad_list, month_d, c, idx, emails)
    month_list = [[key, month_d[key]] for key in sorted(month_d, reverse=True)]
    return {
        'country_list': country_list,
        'campaign_list': campaign_list,
        'month_list': month_list,
    }

def build_month_d(pad_list, month_d, campaign, idx, elist):
    for e in elist:
        created = e.created.strftime("%Y-%m")
        # If the month doesn't exist in the dictionary already, create it.
        if not month_d.get(created, None):
            month_d[created] = list(pad_list)
        if len(e.campaign):
            for cam in e.campaign:
                if cam.name == campaign:
                    month_d[created][idx] += 1
