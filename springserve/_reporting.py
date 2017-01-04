
from . import _VDAPIService, _VDAPIResponse, _VDAPIMultiResponse

from datetime import datetime

from time import sleep

import pandas

from link import lnk

msg = lnk.msg

class _ReportingResponse(_VDAPIMultiResponse):

    def to_dataframe(self):
        if self.dataframe is None:
            self.dataframe = pandas.DataFrame(self.raw['data'])
        return self.dataframe

    def _is_last_page(self, resp):
        self.all_pages_gotten = not resp.data
        return self.all_pages_gotten

    def get_next_page(self, clear_previous=True):

        if self.all_pages_gotten:
            return False

        self._payload['page'] = self.current_page+1
        if self._payload:
            resp = self._service.post(data=self._payload)
        else:
            raise('Original report paramaters are missing')

        if self._is_last_page(resp):
            self.all_pages_gotten = True
            return False

        new_data = pandas.DataFrame(resp.raw['data'])
        #clear previous data
        if clear_previous:
            self.dataframe = new_data
        else:
            self.dataframe = self.dataframe.append(new_data)
        self.current_page += 1
        return True

    def get_all_pages(self):
        while not self.all_pages_gotten:
            self.get_next_page(clear_previous=False)
        return None

class _ReportingAPI(_VDAPIService):

    __API__ = "report"
    __RESPONSES_OBJECT__ = _ReportingResponse

    INTERVALS = ("hour", "day", "cumulative")

    def _format_date(self, date):

        if isinstance(date, datetime):
            return date.strftime("%Y-%m-%d")
        return date

    def _get_report(self, payload):
        response = self.post(data=payload)
        self._report_id = response.raw['report_id']
        payload['report_id'] = self._report_id
        if 'status' not in response.raw:
            raise('status field not in response: {}'.format(response.raw))

        #poll the api untill we get a completed report
        while response.raw['status'] != 'COMPLETE':
            sleep(1)
            response = self.post(data=payload)
        return response




    def run(self, start_date=None, end_date=None, interval=None, dimensions=None,
            account_id=None, **kwargs):
        """
        parameter     options (if applicable)  notes
        ===================================================
        start_date:  "2015-12-01 00:00:00" or "2015-12-01"
        end_date:    "2015-12-02 00:00:00" or "2015-12-01"
        interval:    "hour", "day", "cumulative"
        timezone:    "UTC", "America/New_York"   defaults to America/New_York
        date_range:  Today, Yesterday, Last 7 Days   date_range takes precedence over start_date/end_date
        dimensions:  supply_tag_id, demand_tag_id, detected_domain, declared_domain, demand_type, supply_type, supply_partner_id, demand_partner_id, supply_group  domain is only available when using date_range of Today, Yesterday, or Last 7 Days

        the following parameters act as filters; pass an array of values (usually IDs)
        =================================================================================

        supply_tag_ids:  [22423,22375, 25463]
        demand_tag_ids:  [22423,22375, 25463]
        detected_domains:         ["nytimes.com", "weather.com"]
        declared_domains:         ["nytimes.com", "weather.com"]
        supply_types     ["Syndicated","Third-Party"]
        supply_partner_ids:  [30,42,41]
        supply_group_ids:    [13,15,81]
        demand_partner_ids:  [3,10,81]
        demand_types:    ["Vast Only","FLASH"]
        """
        self.payload = {
            'start_date': self._format_date(start_date),
            'end_date': self._format_date(end_date),
            'report_service': True,
            'async': True
        }

        if interval:
            if interval not in self.INTERVALS:
                raise Exception("not a valid interval")
            self.payload['interval'] = interval

        if dimensions:
            self.payload['dimensions'] = dimensions

        if account_id:
            self.payload['account_id'] = account_id

        if kwargs:
            self.payload.update(kwargs)

        return self._get_report(self.payload)


class _TrafficQualityReport(_ReportingAPI):

    __API__ = "traffic_quality_reports"
    __RESPONSES_OBJECT__ = _ReportingResponse



