from datetime import timezone
from typing import Dict, Tuple, Union

import dateparser
import urllib3

from CommonServerPython import *

''' IMPORTS '''

# Disable insecure warnings
urllib3.disable_warnings()

FETCH_PARAM_ID_KEY = 'field_time_id'
LAST_FETCH_TIME_KEY = 'last_fetch'
OCCURRED_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

REQUEST_HEADERS = {
    'Accept': 'application/json,text/html,application/xhtml +xml,application/xml;q=0.9,*/*;q=0.8',
    'Content-Type': 'application/json'
}

FIELD_TYPE_DICT = {
    1: 'Text', 2: 'Numeric', 3: 'Date', 4: 'Values List', 6: 'TrackingID', 7: 'External Links',
    8: 'Users/Groups List', 9: 'Cross-Reference', 11: 'Attachment', 12: 'Image',
    14: 'Cross-Application Status Tracking (CAST)', 16: 'Matrix', 19: 'IP Address', 20: 'Record Status',
    21: 'First Published', 22: 'Last Updated Field', 23: 'Related Records', 24: 'Sub-Form',
    25: 'History Log', 26: 'Discussion', 27: 'Multiple Reference Display Control',
    28: 'Questionnaire Reference', 29: 'Access History', 30: 'V oting', 31: 'Scheduler',
    1001: 'Cross-Application Status Tracking Field Value'
}

ACCOUNT_STATUS_DICT = {1: 'Active', 2: 'Inactive', 3: 'Locked'}

API_ENDPOINT = demisto.params().get('api_endpoint', 'rsaarcher/api').replace('rsaarcher', '')


def parser(date_str, date_formats=None, languages=None, locales=None, region=None, settings=None) -> datetime:
    """Wrapper of dateparser.parse to support return type value
    """
    date_obj = dateparser.parse(
        date_str, date_formats=date_formats, languages=languages, locales=locales, region=region, settings=settings
    )
    assert isinstance(date_obj, datetime), f'Could not parse date {date_str}'  # MYPY Fix
    return date_obj.replace(tzinfo=timezone.utc)


def get_token_soap_request(user, password, instance):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<soap:Envelope xmlns:xsi="http://www.w3.orecord_to_incidentrg/2001/XMLSchema-instance" ' \
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' + \
           '    <soap:Body>' + \
           '        <CreateUserSessionFromInstance xmlns="http://archer-tech.com/webservices/">' + \
           f'            <userName>{user}</userName>' + \
           f'            <instanceName>{instance}</instanceName>' + \
           f'            <password>{password}</password>' + \
           '        </CreateUserSessionFromInstance>' + \
           '    </soap:Body>' + \
           '</soap:Envelope>'


def terminate_session_soap_request(token):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' \
           ' xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' + \
           '    <soap:Body>' + \
           '        <TerminateSession xmlns="http://archer-tech.com/webservices/">' + \
           f'            <sessionToken>{token}</sessionToken>' + \
           '        </TerminateSession>' + \
           '    </soap:Body>' + \
           '</soap:Envelope>'


def get_reports_soap_request(token):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' + \
           '    <soap:Body>' + \
           '        <GetReports xmlns="http://archer-tech.com/webservices/">' + \
           f'            <sessionToken>{token}</sessionToken>' + \
           '        </GetReports>' + \
           '    </soap:Body>' + \
           '</soap:Envelope>'


def get_statistic_search_report_soap_request(token, report_guid, max_results):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"' \
           ' xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' + \
           '    <soap:Body>' + \
           '        <ExecuteStatisticSearchByReport xmlns="http://archer-tech.com/webservices/">' + \
           f'            <sessionToken>{token}</sessionToken>' + \
           f'            <reportIdOrGuid>{report_guid}</reportIdOrGuid>' + \
           f'            <pageNumber>{max_results}</pageNumber>' + \
           '        </ExecuteStatisticSearchByReport>' + \
           '    </soap:Body>' + \
           '</soap:Envelope>'


def get_search_options_soap_request(token, report_guid):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' + \
           '    <soap:Body>' + \
           '        <GetSearchOptionsByGuid xmlns="http://archer-tech.com/webservices/">' + \
           f'            <sessionToken>{token}</sessionToken>' + \
           f'            <searchReportGuid>{report_guid}</searchReportGuid>' + \
           '        </GetSearchOptionsByGuid>' + \
           '    </soap:Body>' + \
           '</soap:Envelope>'


def search_records_by_report_soap_request(token, report_guid):
    return '<?xml version="1.0" encoding="utf-8"?>' + \
           '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' \
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">' + \
           '    <soap:Body>' + \
           '        <SearchRecordsByReport xmlns="http://archer-tech.com/webservices/">' + \
           f'            <sessionToken>{token}</sessionToken>' + \
           f'            <reportIdOrGuid>{report_guid}</reportIdOrGuid>' + \
           '            <pageNumber>1</pageNumber>' + \
           '        </SearchRecordsByReport>' + \
           '    </soap:Body>' + \
           '</soap:Envelope>'


def search_records_soap_request(
        token, app_id, display_fields, field_id, field_name, search_value, date_operator='',
        numeric_operator='', max_results=10,
        sort_type: str = 'Ascending'
):
    request_body = '<?xml version="1.0" encoding="UTF-8"?>' + \
                   '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" ' \
                   'xmlns:xsd="http://www.w3.org/2001/XMLSchema"' \
                   ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' + \
                   '    <soap:Body>' + \
                   '        <ExecuteSearch xmlns="http://archer-tech.com/webservices/">' + \
                   f'            <sessionToken>{token}</sessionToken>' + \
                   '            <searchOptions>' + \
                   '                <![CDATA[<SearchReport>' + \
                   f'                <PageSize>{max_results}</PageSize>' + \
                   '                 <PageNumber>1</PageNumber>' + \
                   f'                <MaxRecordCount>{max_results}</MaxRecordCount>' + \
                   '                <ShowStatSummaries>false</ShowStatSummaries>' + \
                   f'                <DisplayFields>{display_fields}</DisplayFields>' + \
                   f'             <Criteria><ModuleCriteria><Module name="appname">{app_id}</Module></ModuleCriteria>'

    if search_value:
        request_body += '<Filter><Conditions>'

        if date_operator:
            request_body += '<DateComparisonFilterCondition>' + \
                            f'        <Operator>{date_operator}</Operator>' + \
                            f'        <Field name="{field_name}">{field_id}</Field>' + \
                            f'        <Value>{search_value}</Value>' + \
                            '        <TimeZoneId>UTC Standard Time</TimeZoneId>' + \
                            '        <IsTimeIncluded>TRUE</IsTimeIncluded>' + \
                            '</DateComparisonFilterCondition >'
        elif numeric_operator:
            request_body += '<NumericFilterCondition>' + \
                            f'        <Operator>{numeric_operator}</Operator>' + \
                            f'        <Field name="{field_name}">{field_id}</Field>' + \
                            f'        <Value>{search_value}</Value>' + \
                            '</NumericFilterCondition >'
        else:
            request_body += '<TextFilterCondition>' + \
                            '        <Operator>Contains</Operator>' + \
                            f'        <Field name="{field_name}">{field_id}</Field>' + \
                            f'        <Value>{search_value}</Value>' + \
                            '</TextFilterCondition >'

        request_body += '</Conditions></Filter>'

    if date_operator:  # Fetch incidents must present date_operator
        request_body += '<Filter>' + \
                        '<Conditions>' + \
                        '    <DateComparisonFilterCondition>' + \
                        f'        <Operator>{date_operator}</Operator>' + \
                        f'        <Field name="{field_name}">{field_id}</Field>' + \
                        f'        <Value>{search_value}</Value>' + \
                        '        <TimeZoneId>UTC Standard Time</TimeZoneId>' + \
                        '        <IsTimeIncluded>TRUE</IsTimeIncluded>' + \
                        '    </DateComparisonFilterCondition >' + \
                        '</Conditions>' + \
                        '</Filter>'

    if field_id:
        request_body += '<SortFields>' + \
                        '    <SortField>' + \
                        f'        <Field>{field_id}</Field>' + \
                        f'        <SortType>{sort_type}</SortType>' + \
                        '    </SortField >' + \
                        '</SortFields>'

    request_body += ' </Criteria></SearchReport>]]>' + \
                    '</searchOptions>' + \
                    '<pageNumber>1</pageNumber>' + \
                    '</ExecuteSearch>' + \
                    '</soap:Body>' + \
                    '</soap:Envelope>'

    return request_body


SOAP_COMMANDS = {
    'archer-get-reports': {'soapAction': 'http://archer-tech.com/webservices/GetReports', 'urlSuffix': 'ws/search.asmx',
                           'soapBody': get_reports_soap_request,
                           'outputPath': 'Envelope.Body.GetReportsResponse.GetReportsResult'},
    'archer-execute-statistic-search-by-report': {
        'soapAction': 'http://archer-tech.com/webservices/ExecuteStatisticSearchByReport',
        'urlSuffix': 'ws/search.asmx',
        'soapBody': get_statistic_search_report_soap_request,
        'outputPath': 'Envelope.Body.ExecuteStatisticSearchByReportResponse.ExecuteStatistic'
                      'SearchByReportResult'
    },
    'archer-get-search-options-by-guid':
        {'soapAction': 'http://archer-tech.com/webservices/GetSearchOptionsByGuid',
         'urlSuffix': 'ws/search.asmx',
         'soapBody': get_search_options_soap_request,
         'outputPath': 'Envelope.Body.GetSearchOptionsByGuidResponse.GetSearchOptionsByGuidResult'
         },
    'archer-search-records':
        {'soapAction': 'http://archer-tech.com/webservices/ExecuteSearch',
         'urlSuffix': 'ws/search.asmx',
         'soapBody': search_records_soap_request,
         'outputPath': 'Envelope.Body.ExecuteSearchResponse.ExecuteSearchResult'},
    'archer-search-records-by-report': {
        'soapAction': 'http://archer-tech.com/webservices/SearchRecordsByReport',
        'urlSuffix': 'ws/search.asmx',
        'soapBody': search_records_by_report_soap_request,
        'outputPath': 'Envelope.Body.SearchRecordsByReportResponse.SearchRecordsByReportResult'
    }
}


def get_occurred_time(fields: Union[List[dict], dict], field_id: str) -> str:
    """
    Occurred time is part of the raw 'Field' key in the response.
    It should be under @xmlConvertedValue, but field can be both a list or a dict.

    Arguments:
        fields: Field to find the occurred utc time on
        field_id: The @id in the response the time should be on

    Returns:
         Time of occurrence according to the field ID.
    """
    try:
        field_id = str(field_id)  # In case it passed as a integer
        if isinstance(fields, dict):
            return fields['@xmlConvertedValue']
        else:
            for field in fields:
                if str(field['@id']) == field_id:  # In a rare case @id is an integer
                    return str(field['@xmlConvertedValue'])
        raise KeyError('Could not find @xmlConvertedValue in record.')  # No xmlConvertedValue
    except KeyError as exc:
        raise DemistoException(
            f'Could not find the property @xmlConvertedValue in field id {field_id}. Is that a date field?'
        ) from exc


class Client(BaseClient):
    def __init__(self, base_url, username, password, instance_name, domain, **kwargs):
        self.username = username
        self.password = password
        self.instance_name = instance_name
        self.domain = domain
        super(Client, self).__init__(base_url=base_url, headers=REQUEST_HEADERS, **kwargs)

    def do_request(self, method, url_suffix, data=None, params=None):
        if not REQUEST_HEADERS.get('Authorization'):
            self.update_session()

        res = self._http_request(method, url_suffix, headers=REQUEST_HEADERS, json_data=data, params=params,
                                 resp_type='response', ok_codes=(200, 401), timeout=20)

        if res.status_code == 401:
            self.update_session()
            res = self._http_request(method, url_suffix, headers=REQUEST_HEADERS, json_data=data,
                                     resp_type='response', ok_codes=(200, 401))

        return res.json()

    def update_session(self):
        body = {
            'InstanceName': self.instance_name,
            'Username': self.username,
            'UserDomain': self.domain,
            'Password': self.password
        }
        try:
            res = self._http_request('POST', f'{API_ENDPOINT}/core/security/login', json_data=body, timeout=20)
        except DemistoException as e:
            if '<html>' in str(e):
                raise DemistoException(f"Check the given URL, it can be a redirect issue. Failed with error: {str(e)}")
            raise e
        is_successful_response = res.get('IsSuccessful')
        if not is_successful_response:
            return_error(res.get('ValidationMessages'))
        session = res.get('RequestedObject', {}).get('SessionToken')
        REQUEST_HEADERS['Authorization'] = f'Archer session-id={session}'

    def get_token(self):
        body = get_token_soap_request(self.username, self.password, self.instance_name)
        headers = {'SOAPAction': 'http://archer-tech.com/webservices/CreateUserSessionFromInstance',
                   'Content-Type': 'text/xml; charset=utf-8'}
        res = self._http_request('POST'
                                 '', 'ws/general.asmx', headers=headers, data=body, resp_type='content')

        return extract_from_xml(res,
                                'Envelope.Body.CreateUserSessionFromInstanceResponse.'
                                'CreateUserSessionFromInstanceResult')

    def destroy_token(self, token):
        body = terminate_session_soap_request(token)
        headers = {'SOAPAction': 'http://archer-tech.com/webservices/TerminateSession',
                   'Content-Type': 'text/xml; charset=utf-8'}
        self._http_request('POST', 'ws/general.asmx', headers=headers, data=body, resp_type='content')

    def do_soap_request(self, command, **kwargs):
        req_data = SOAP_COMMANDS[command]
        headers = {'SOAPAction': req_data['soapAction'], 'Content-Type': 'text/xml; charset=utf-8'}
        token = self.get_token()
        body = req_data['soapBody'](token, **kwargs)  # type: ignore
        res = self._http_request('POST', req_data['urlSuffix'], headers=headers, data=body, resp_type='content')
        self.destroy_token(token)
        return extract_from_xml(res, req_data['outputPath']), res

    def get_level_by_app_id(self, app_id, specify_level_id=None):
        levels = []
        cache = get_integration_context()

        if cache.get(app_id):
            levels = cache[app_id]
        else:
            all_levels_res = self.do_request('GET', f'{API_ENDPOINT}/core/system/level/module/{app_id}')
            for level in all_levels_res:
                if level.get('RequestedObject') and level.get('IsSuccessful'):
                    level_id = level.get('RequestedObject').get('Id')

                    fields = {}
                    level_res = self.do_request('GET', f'{API_ENDPOINT}/core/system/fielddefinition/level/{level_id}')
                    for field in level_res:
                        if field.get('RequestedObject') and field.get('IsSuccessful'):
                            field_item = field.get('RequestedObject')
                            field_id = str(field_item.get('Id'))
                            fields[field_id] = {'Type': field_item.get('Type'),
                                                'Name': field_item.get('Name'),
                                                'FieldId': field_id,
                                                'IsRequired': field_item.get('IsRequired', False),
                                                'RelatedValuesListId': field_item.get('RelatedValuesListId')}

                    levels.append({'level': level_id, 'mapping': fields})
            if levels:
                cache[int(app_id)] = levels
                set_integration_context(cache)

        level_data = None
        if specify_level_id:
            level_data = next((level for level in levels if level.get('level') == int(specify_level_id)), None)
        elif levels:
            level_data = levels[0]

        if not level_data:
            raise DemistoException('Got no level by app id. You might be using the wrong application id or level id.')

        return level_data

    def get_record(self, app_id, record_id):
        res = self.do_request('GET', f'{API_ENDPOINT}/core/content/{record_id}')

        if not isinstance(res, dict):
            res = res.json()

        errors = get_errors_from_res(res)
        record = {}
        if res.get('RequestedObject') and res.get('IsSuccessful'):
            content_obj = res.get('RequestedObject')
            level_id = content_obj.get('LevelId')
            level = self.get_level_by_app_id(app_id, level_id)
            if level:
                level_fields = level['mapping']
            else:
                return {}, res, errors

            for _id, field in content_obj.get('FieldContents').items():
                field_data = level_fields.get(str(_id))  # type: ignore
                field_type = field_data.get('Type')

                # when field type is IP Address
                if field_type == 19:
                    field_value = field.get('IpAddressBytes')
                # when field type is Values List
                elif field_type == 4 and field.get('Value') and field['Value'].get('ValuesListIds'):
                    list_data = self.get_field_value_list(_id)
                    list_ids = field['Value']['ValuesListIds']
                    list_ids = list(filter(lambda x: x['Id'] in list_ids, list_data['ValuesList']))
                    field_value = list(map(lambda x: x['Name'], list_ids))
                else:
                    field_value = field.get('Value')

                if field_value:
                    record[field_data.get('Name')] = field_value

            record['Id'] = content_obj.get('Id')
        return record, res, errors

    @staticmethod
    def record_to_incident(
            record_item, app_id, fetch_param_id
    ) -> Tuple[dict, datetime]:
        """Transform a record to incident

        Args:
            record_item: The record item dict
            app_id: ID of the app
            fetch_param_id: ID of the fetch param.

        Returns:
            incident, incident created time (UTC Time)
        """
        labels = []
        raw_record = record_item['raw']
        record_item = record_item['record']
        try:
            occurred_time = get_occurred_time(raw_record['Field'], fetch_param_id)
        except KeyError as exc:
            raise DemistoException(
                f'Could not find occurred time in record {record_item.get("Id")=}'
            ) from exc
        # Will convert value to strs
        for k, v in record_item.items():
            if isinstance(v, str):
                labels.append({
                    'type': k,
                    'value': v
                })
            else:
                labels.append({
                    'type': k,
                    'value': json.dumps(v)
                })

        labels.append({'type': 'ModuleId', 'value': app_id})
        labels.append({'type': 'ContentId', 'value': record_item.get("Id")})
        labels.append({'type': 'rawJSON', 'value': json.dumps(raw_record)})
        incident = {
            'name': f'RSA Archer Incident: {record_item.get("Id")}',
            'details': json.dumps(record_item),
            'occurred': occurred_time,
            'labels': labels,
            'rawJSON': json.dumps(raw_record)
        }
        return incident, parser(occurred_time)

    def search_records(
            self, app_id, fields_to_display=None, field_to_search='', search_value='',
            numeric_operator='', date_operator='', max_results=10,
            sort_type: str = 'Ascending'
    ):
        demisto.debug(f'searching for records {field_to_search}:{search_value}')
        if fields_to_display is None:
            fields_to_display = []

        level_data = self.get_level_by_app_id(app_id)

        # Building request fields
        fields_xml = ''
        search_field_name = ''
        search_field_id = ''
        fields_mapping = level_data['mapping']
        for field in fields_mapping.keys():
            field_name = fields_mapping[field]['Name']
            if field_name in fields_to_display:
                fields_xml += f'<DisplayField name="{field_name}">{field}</DisplayField>'
            if field_name == field_to_search:
                search_field_name = field_name
                search_field_id = field

        res, raw_res = self.do_soap_request(
            'archer-search-records',
            app_id=app_id, display_fields=fields_xml,
            field_id=search_field_id, field_name=search_field_name,
            numeric_operator=numeric_operator,
            date_operator=date_operator, search_value=search_value,
            max_results=max_results,
            sort_type=sort_type,
        )

        if not res:
            return [], raw_res

        records = self.xml_to_records(res, fields_mapping)
        return records, raw_res

    def xml_to_records(self, xml_response, fields_mapping):
        res = json.loads(xml2json(xml_response))
        records = []
        if res.get('Records') and res['Records'].get('Record'):
            records_data = res['Records']['Record']
            if isinstance(records_data, dict):
                records_data = [records_data]

            for item in records_data:
                record = {'Id': item.get('@contentId')}
                record_fields = item.get('Field')

                if isinstance(record_fields, dict):
                    record_fields = [record_fields]

                for field in record_fields:
                    field_name = fields_mapping[field.get('@id')]['Name']
                    field_type = field.get('@type')
                    field_value = ''
                    if field_type == '3':
                        field_value = field.get('@xmlConvertedValue')
                    elif field_type == '4':
                        if field.get('ListValues'):
                            field_value = field['ListValues']['ListValue']['@displayName']
                    elif field_type == '8':
                        field_value = json.dumps(field)
                    else:
                        field_value = field.get('#text')

                    record[field_name] = field_value
                records.append({'record': record, 'raw': item})
        return records

    def get_field_value_list(self, field_id):
        cache = get_integration_context()

        if cache['fieldValueList'].get(field_id):
            return cache.get('fieldValueList').get(field_id)

        res = self.do_request('GET', f'{API_ENDPOINT}/core/system/fielddefinition/{field_id}')

        errors = get_errors_from_res(res)
        if errors:
            return_error(errors)

        if res.get('RequestedObject') and res.get('IsSuccessful'):
            list_id = res['RequestedObject']['RelatedValuesListId']
            values_list_res = self.do_request('GET', f'{API_ENDPOINT}/core/system/valueslistvalue/valueslist/{list_id}')
            if values_list_res.get('RequestedObject') and values_list_res.get('IsSuccessful'):
                values_list = []
                for value in values_list_res['RequestedObject'].get('Children'):
                    values_list.append({'Id': value['Data']['Id'],
                                        'Name': value['Data']['Name'],
                                        'IsSelectable': value['Data']['IsSelectable']})
                field_data = {'FieldId': field_id, 'ValuesList': values_list}

                cache['fieldValueList'][field_id] = field_data
                set_integration_context(cache)
                return field_data
        return {}

    def get_field_id(self, app_id: str, field_name: str) -> str:
        """Get field ID by field name

        Args:
            app_id: app id to search on
            field_name: field name to search on

        Raises:
            DemistoException: If could not find field ID

        Returns:
            The ID of the field
        """
        fields, _ = self.get_application_fields(app_id)
        for field in fields:
            if field_name == field.get('FieldName'):
                try:
                    return str(field['FieldId'])
                except KeyError:
                    raise DemistoException(f'Could not find FieldId for {field_name=}')
        raise DemistoException(f'Could not find field ID {field_name}')

    def get_application_fields(self, app_id: str) -> Tuple[list, list]:
        """Getting all fields in the application

        Args:
            app_id: Application to find the fields on

        Returns:
            fields, raw response
        """
        res = self.do_request('GET', f'{API_ENDPOINT}/core/system/fielddefinition/application/{app_id}')

        fields = []
        for field in res:
            if field.get('RequestedObject') and field.get('IsSuccessful'):
                field_obj = field['RequestedObject']
                field_type = field_obj.get('Type')
                fields.append({
                    'FieldId': field_obj.get('Id'),
                    'FieldType': FIELD_TYPE_DICT.get(field_type, 'Unknown'),
                    'FieldName': field_obj.get('Name'),
                    'LevelID': field_obj.get('LevelId')
                })
            else:
                errors = get_errors_from_res(field)
                if errors:
                    raise DemistoException(errors)
        return fields, res


def extract_from_xml(xml, path):
    xml = json.loads(xml2json(xml))
    path = path.split('.')

    for item in path:
        if xml.get(item):
            xml = xml[item]
            continue
        return ''
    return xml


def generate_field_contents(client, fields_values, level_fields):
    if fields_values and not isinstance(fields_values, dict):
        try:
            fields_values = json.loads(fields_values)
        except Exception:
            raise Exception('Failed to parese fields-values argument')

    field_content = {}
    for field_name in fields_values.keys():
        field_data = None

        for _id, field in level_fields.items():
            if field.get('Name') == field_name:
                field_data = field
                break

        if field_data:
            field_key, field_value = generate_field_value(client, field_name, field_data, fields_values[field_name])

            field_content[_id] = {'Type': field_data['Type'],
                                  field_key: field_value,
                                  'FieldId': _id}
    return field_content


def generate_field_value(client, field_name, field_data, field_val):
    field_type = field_data['Type']

    # when field type is Values List, call get_field_value_list method to get the value ID
    # for example: {"Type":["Switch"], fieldname:[value1, value2]}
    if field_type == 4:
        field_data = client.get_field_value_list(field_data['FieldId'])
        list_ids = []
        if not isinstance(field_val, list):
            field_val = [field_val]
        for item in field_val:
            tmp_id = next(f for f in field_data['ValuesList'] if f['Name'] == item)
            if tmp_id:
                list_ids.append(tmp_id['Id'])
            else:
                raise Exception(f'Failed to create field {field_name} with the value {field_data}')
        return 'Value', {'ValuesListIds': list_ids}

    # when field type is External Links
    # for example: {"Patch URL":[{"value":"github", "link": "https://github.com"}]}
    elif field_type == 7:
        list_urls = []
        for item in field_val:
            list_urls.append({'Name': item.get('value'), 'URL': item.get('link')})
        return 'Value', list_urls

    # when field type is Users/Groups List
    # for example: {"Policy Owner":{"users":[20],"groups":[30]}}
    elif field_type == 8:
        try:
            users = field_val.get('users')
            groups = field_val.get('groups')
        except AttributeError:
            raise DemistoException(f"The value of the field: {field_name} must be a dictionary type and include a list"
                                   f" under \"users\" key or \"groups\" key e.g: {{\"Policy Owner\":{{\"users\":[20],"
                                   f"\"groups\":[30]}}}}")

        field_val = {'UserList': [], 'GroupList': []}
        if users:
            for user in users:
                field_val['UserList'].append({'ID': user})
        if groups:
            for group in groups:
                field_val['GroupList'].append({'ID': group})
        return 'Value', field_val

    # when field type is Cross- Reference
    # for example: {"Area Reference(s)":[20]}
    elif field_type == 9:
        list_cross_reference = []
        if isinstance(field_val, list):
            for content in field_val:
                list_cross_reference.append({'ContentID': content})

        else:
            list_cross_reference = [{'ContentID': field_val}]
        return 'Value', list_cross_reference

    elif field_type == 19:
        return 'IpAddressBytes', field_val

    else:
        return 'Value', field_val


def get_errors_from_res(res):
    if isinstance(res, dict) and res.get('ValidationMessages'):
        messages = []
        for message in res.get('ValidationMessages'):  # type: ignore
            messages.append(message.get('ResourcedMessage'))
        return '\n'.join(messages)


def get_file(entry_id):
    get_file_path_res = demisto.getFilePath(entry_id)
    file_path = get_file_path_res["path"]
    file_name = get_file_path_res["name"]
    with open(file_path, 'rb') as fopen:
        file_bytes = fopen.read()

    file_bytes = base64.b64encode(file_bytes)
    return file_name, file_bytes.decode('utf-8')


def test_module(client: Client, params: dict) -> str:
    if params.get('isFetch', False):
        last_run = {
            FETCH_PARAM_ID_KEY: get_fetch_param_id(
                client, {}, params['applicationId'], params['applicationDateField']
            )}
        fetch_incidents_command(client, params, last_run)

        return 'ok'

    return 'ok' if client.do_request('GET', f'{API_ENDPOINT}/core/system/application') else 'Connection failed.'


def search_applications_command(client: Client, args: Dict[str, str]):
    app_id = args.get('applicationId')
    limit = args.get('limit')
    endpoint_url = f'{API_ENDPOINT}/core/system/application/'

    if app_id:
        endpoint_url = f'{API_ENDPOINT}/core/system/application/{app_id}'
        res = client.do_request('GET', endpoint_url)
    elif limit:
        res = client.do_request('GET', endpoint_url, params={"$top": limit})

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    if isinstance(res, dict):
        res = [res]

    applications = []
    for app in res:
        if app.get('RequestedObject') and app.get('IsSuccessful'):
            app_obj = app['RequestedObject']
            applications.append({'Id': app_obj.get('Id'),
                                 'Type': app_obj.get('Type'),
                                 'Name': app_obj.get('Name'),
                                 'LanguageId': app_obj.get('LanguageId'),
                                 'Status': app_obj.get('Status'),
                                 'Guid': app_obj.get('Guid')})

    markdown = tableToMarkdown('Search applications results', applications)
    context: dict = {
        'Archer.Application(val.Id && val.Id == obj.Id)': applications}
    return_outputs(markdown, context, res)


def get_application_fields_command(client: Client, args: Dict[str, str]):
    app_id = args['applicationId']
    fields, res = client.get_application_fields(app_id)

    markdown = tableToMarkdown('Application fields', fields)
    context: dict = {'Archer.ApplicationField(val.FieldId && val.FieldId == obj.FieldId)': fields}
    return_outputs(markdown, context, res)


def get_field_command(client: Client, args: Dict[str, str]):
    field_id = args.get('fieldID')

    res = client.do_request('GET', f'{API_ENDPOINT}/core/system/fielddefinition/{field_id}')

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    field = {}
    if res.get('RequestedObject') and res.get('IsSuccessful'):
        field_obj = res['RequestedObject']
        item_type = field_obj.get('Type')
        item_type = FIELD_TYPE_DICT.get(item_type, 'Unknown')
        field = {'FieldId': field_obj.get('Id'),
                 'FieldType': item_type,
                 'FieldName': field_obj.get('Name'),
                 'LevelID': field_obj.get('LevelId')}

    markdown = tableToMarkdown('Application field', field)
    context: dict = {
        'Archer.ApplicationField(val.FieldId && val.FieldId == obj.FieldId)':
            field
    }
    return_outputs(markdown, context, res)


def get_mapping_by_level_command(client: Client, args: Dict[str, str]):
    level = args.get('level')

    res = client.do_request('GET', f'{API_ENDPOINT}/core/system/fielddefinition/level/{level}')

    items = []
    for item in res:
        if item.get('RequestedObject') and item.get('IsSuccessful'):
            item_obj = item['RequestedObject']
            item_type = item_obj.get('Type')
            if item_type:
                item_type = FIELD_TYPE_DICT.get(item_type, 'Unknown')
            else:
                item_type = 'Unknown'
            items.append({'Id': item_obj.get('Id'),
                          'Name': item_obj.get('Name'),
                          'Type': item_type,
                          'LevelId': item_obj.get('LevelId')})
        else:
            errors = get_errors_from_res(item)
            if errors:
                return_error(errors)

    markdown = tableToMarkdown(f'Level mapping for level {level}', items)
    context: dict = {'Archer.LevelMapping(val.Id && val.Id == obj.Id)': items}
    return_outputs(markdown, context, res)


def get_record_command(client: Client, args: Dict[str, str]):
    record_id = args.get('contentId')
    app_id = args.get('applicationId')

    record, res, errors = client.get_record(app_id, record_id)
    if errors:
        return_error(errors)

    markdown = tableToMarkdown('Record details', record)
    context: dict = {
        'Archer.Record(val.Id && val.Id == obj.Id)':
            record
    }
    return_outputs(markdown, context, res)


def create_record_command(client: Client, args: Dict[str, str]):
    app_id = args.get('applicationId')
    fields_values = args.get('fieldsToValues')
    level_id = args.get('levelId')
    level_data = client.get_level_by_app_id(app_id, level_id)

    field_contents = generate_field_contents(client, fields_values, level_data['mapping'])

    body = {'Content': {'LevelId': level_data['level'], 'FieldContents': field_contents}}

    res = client.do_request('Post', f'{API_ENDPOINT}/core/content', data=body)

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    if res.get('RequestedObject') and res.get('IsSuccessful'):
        rec_id = res['RequestedObject']['Id']
        return_outputs(f'Record created successfully, record id: {rec_id}', {'Archer.Record.Id': rec_id}, res)


def delete_record_command(client: Client, args: Dict[str, str]):
    record_id = args.get('contentId')
    res = client.do_request('Delete', f'{API_ENDPOINT}/core/content/{record_id}')

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)
    return_outputs(f'Record {record_id} deleted successfully', {}, res)


def update_record_command(client: Client, args: Dict[str, str]):
    app_id = args.get('applicationId')
    record_id = args.get('contentId')
    fields_values = args.get('fieldsToValues')
    level_id = args.get('levelId')
    level_data = client.get_level_by_app_id(app_id, level_id)

    field_contents = generate_field_contents(client, fields_values, level_data['mapping'])

    body = {'Content': {'Id': record_id, 'LevelId': level_data['level'], 'FieldContents': field_contents}}
    res = client.do_request('Put', f'{API_ENDPOINT}/core/content', data=body)

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    if res.get('IsSuccessful'):
        return_outputs(f'Record {record_id} updated successfully', {}, res)
    else:
        raise DemistoException('Update record failed')


def execute_statistics_command(client: Client, args: Dict[str, str]):
    report_guid = args.get('reportGuid')
    max_results = args.get('maxResults')
    res, raw_res = client.do_soap_request('archer-execute-statistic-search-by-report',
                                          report_guid=report_guid, max_results=max_results)
    if res:
        res = json.loads(xml2json(res))
    return_outputs(res, {}, {})


def get_reports_command(client: Client, args: Dict[str, str]):
    res, raw_res = client.do_soap_request('archer-get-reports')
    res = json.loads(xml2json(res))
    ec = res.get('ReportValues').get('ReportValue')

    context: dict = {
        'Archer.Report(val.ReportGUID && val.ReportGUID == obj.ReportGUID)': ec
    }
    return_outputs(ec, context, {})


def search_options_command(client: Client, args: Dict[str, str]):
    report_guid = args.get('reportGuid')
    res, raw_res = client.do_soap_request('archer-get-search-options-by-guid', report_guid=report_guid)
    if res.startswith('<'):
        res = json.loads(xml2json(res))
    return_outputs(res, {}, {})


def reset_cache_command(client: Client, args: Dict[str, str]):
    set_integration_context({})
    return_outputs('', {}, '')


def get_value_list_command(client: Client, args: Dict[str, str]):
    field_id = args.get('fieldID')
    field_data = client.get_field_value_list(field_id)

    markdown = tableToMarkdown(f'Value list for field {field_id}', field_data['ValuesList'])

    context: dict = {
        'Archer.ApplicationField(val.FieldId && val.FieldId == obj.FieldId)':
            field_data
    }
    return_outputs(markdown, context, {})


def upload_file_command(client: Client, args: Dict[str, str]) -> str:
    """Uploading a file to archer as an attachment

    Arguments:
        client: A client to use in order to send the api callarcher-get-file
        args: demisto args

    Returns:
        An attachment id from Archer
    """
    entry_id = args.get('entryId')
    file_name, file_bytes = get_file(entry_id)
    body = {'AttachmentName': file_name, 'AttachmentBytes': file_bytes}

    res = client.do_request('POST', f'{API_ENDPOINT}/core/content/attachment', data=body)

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    if res.get('RequestedObject') and res.get('IsSuccessful'):
        attachment_id = res['RequestedObject'].get('Id')
    else:
        raise DemistoException('Upload file failed')

    return_outputs(f'File uploaded successfully, attachment ID: {attachment_id}', {}, res)
    return attachment_id


def upload_and_associate_command(client: Client, args: Dict[str, str]):
    """Uploading an entry to archer. than, if needed, associate it to a record.
    """
    app_id = args.get('applicationId')
    content_id = args.get('contentId')
    associate_field = args.get('associatedField')

    should_associate_to_record = app_id and content_id
    if not should_associate_to_record:  # If both app_id and content_id
        if app_id or content_id:  # If one of them, raise error. User's mistake
            raise DemistoException(
                'Found arguments to associate an attachment to a record, but not all required arguments supplied'
            )

    attachment_id = upload_file_command(client, args)
    if should_associate_to_record:
        args['fieldsToValues'] = json.dumps({associate_field: [attachment_id]})
        update_record_command(client, args)


def download_file_command(client: Client, args: Dict[str, str]):
    attachment_id = args.get('fileId')
    res = client.do_request('GET', f'{API_ENDPOINT}/core/content/attachment/{attachment_id}')

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    if res.get('RequestedObject') and res.get('IsSuccessful'):
        content = base64.b64decode(res['RequestedObject'].get('AttachmentBytes'))
        filename = res['RequestedObject'].get('AttachmentName')
        return demisto.results(fileResult(filename, content))
    else:
        return_error('File downloading failed', outputs=res)


def list_users_command(client: Client, args: Dict[str, str]):
    user_id = args.get('userId')
    if user_id:
        res = client.do_request('GET', f'{API_ENDPOINT}/core/system/user/{user_id}')
    else:
        res = client.do_request('GET', f'{API_ENDPOINT}/core/system/user')

    errors = get_errors_from_res(res)
    if errors:
        return_error(errors)

    if isinstance(res, dict):
        res = [res]

    users = []
    for user in res:
        if user.get('RequestedObject') and user.get('IsSuccessful'):
            user_obj = user['RequestedObject']
            users.append({'Id': user_obj.get('Id'),
                          'DisplayName': user_obj.get('DisplayName'),
                          'FirstName': user_obj.get('FirstName'),
                          'MiddleName': user_obj.get('MiddleName'),
                          'LastName': user_obj.get('LastName'),
                          'AccountStatus': ACCOUNT_STATUS_DICT[user_obj.get('AccountStatus')],
                          'LastLoginDate': user_obj.get('LastLoginDate'),
                          'UserName': user_obj.get('UserName')})

    markdown = tableToMarkdown('Users list', users)
    context: dict = {
        'Archer.User(val.Id && val.Id == obj.Id)':
            users
    }
    return_outputs(markdown, context, res)


def search_records_command(client: Client, args: Dict[str, str]):
    app_id = args.get('applicationId')
    field_to_search = args.get('fieldToSearchOn')
    search_value = args.get('searchValue')
    max_results = args.get('maxResults', 10)
    date_operator = args.get('dateOperator')
    numeric_operator = args.get('numericOperator')
    fields_to_display = argToList(args.get('fieldsToDisplay'))
    fields_to_get = argToList(args.get('fieldsToGet'))
    full_data = argToBoolean(args.get('fullData'))
    sort_type = 'Descending' if argToBoolean(args.get('isDescending', 'false')) else 'Ascending'
    level_id = args.get('levelId')

    if fields_to_get and 'Id' not in fields_to_get:
        fields_to_get.append('Id')

    if not all(f in fields_to_get for f in fields_to_display):
        return_error('fields-to-display param should have only values from fields-to-get')

    if full_data:
        level_data = client.get_level_by_app_id(app_id, level_id)
        fields_mapping = level_data['mapping']
        fields_to_get = [fields_mapping[next(iter(fields_mapping))]['Name']]

    records, raw_res = client.search_records(
        app_id, fields_to_get, field_to_search, search_value,
        numeric_operator, date_operator, max_results=max_results,
        sort_type=sort_type,
    )

    records = list(map(lambda x: x['record'], records))

    if full_data:
        records_full = []
        for rec in records:
            record_item, _, errors = client.get_record(app_id, rec['Id'])
            if not errors:
                records_full.append(record_item)
        records = records_full

    hr = []

    if full_data:
        hr = records
    else:
        for record in records:
            hr.append({f: record[f] for f in fields_to_display})

    markdown = tableToMarkdown('Search records results', hr)
    context: dict = {'Archer.Record(val.Id && val.Id == obj.Id)': records}
    return_outputs(markdown, context, {})


def search_records_by_report_command(client: Client, args: Dict[str, str]):
    report_guid = args.get('reportGuid')
    res, raw_res = client.do_soap_request('archer-search-records-by-report', report_guid=report_guid)
    if not res:
        return_outputs(f'No records found for report {report_guid}', {}, json.loads(xml2json(raw_res)))
        return

    raw_records = json.loads(xml2json(res))
    records = []
    ec = {}
    if raw_records.get('Records') and raw_records['Records'].get('Record'):
        if isinstance(raw_records['Records'].get('Record'), list):
            level_id = raw_records['Records']['Record'][0]['@levelId']
        else:
            level_id = raw_records['Records']['Record']['@levelId']

        level_res = client.do_request('GET', f'{API_ENDPOINT}/core/system/fielddefinition/level/{level_id}')
        fields = {}
        for field in level_res:
            if field.get('RequestedObject') and field.get('IsSuccessful'):
                field_item = field.get('RequestedObject')
                field_id = str(field_item.get('Id'))
                fields[field_id] = {'Type': field_item.get('Type'),
                                    'Name': field_item.get('Name')}

        records = client.xml_to_records(res, fields)
        records = list(map(lambda x: x['record'], records))

        ec = {'Record': records, 'RecordsAmount': len(records), 'ReportGUID': report_guid}

    markdown = tableToMarkdown('Search records by report results', records)
    context: dict = {'Archer.SearchByReport(val.ReportGUID && val.ReportGUID == obj.ReportGUID)': ec}

    return_outputs(markdown, context, json.loads(xml2json(raw_res)))


def print_cache_command(client: Client, args: Dict[str, str]):
    cache = get_integration_context()
    return_outputs(cache, {}, {})


def fetch_incidents(
        client: Client, params: dict, from_time: datetime, fetch_param_id: str
) -> Tuple[list, datetime]:
    """Fetches incidents.

    Args:
        client: Client derived from BaseClient
        params: demisto.params dict.
        from_time: Time to start the fetch from
        fetch_param_id: Param ID to find occurred time. can be acquired by get_fetch_param_id

    Returns:
        incidents, next_run datetime in archer's local time
    """
    # Not using get method as those params are a must
    app_id = params['applicationId']
    date_field = params['applicationDateField']
    max_results = params.get('fetch_limit', 10)
    fields_to_display = argToList(params.get('fields_to_fetch'))
    fields_to_display.append(date_field)
    # API Call
    records, _ = client.search_records(
        app_id, fields_to_display, date_field,
        from_time.strftime(OCCURRED_FORMAT),
        date_operator='GreaterThan',
        max_results=max_results
    )
    demisto.debug(f'Found {len(records)=}.')
    # Build incidents
    incidents = list()
    # Encountered that sometimes, somehow, on of next_fetch is not UTC.
    last_fetch_time = from_time.replace(tzinfo=timezone.utc)
    next_fetch = last_fetch_time
    for record in records:
        incident, incident_created_time = client.record_to_incident(record, app_id, fetch_param_id)
        # Encountered that sometimes, somehow, incident_created_time is not UTC.
        incident_created_time = incident_created_time.replace(tzinfo=timezone.utc)
        if last_fetch_time < incident_created_time:
            incidents.append(incident)
            if next_fetch < incident_created_time:
                next_fetch = incident_created_time
        else:
            demisto.debug(
                f'The newly fetched incident is older than last fetch. {incident_created_time=} {next_fetch=}'
            )
    demisto.debug(f'Going out fetch incidents with {next_fetch=}, {len(incidents)=}')
    return incidents, next_fetch


def get_fetch_time(last_fetch: dict, first_fetch_time: str) -> datetime:
    """Gets lastRun object and first fetch time (str, 3 days) and returns
    a datetime object of the last run if exists, else datetime of the first fetch time

    Args:
        last_fetch: a dict that may contain 'last_fetch'
        first_fetch_time: time back in simple format (3 days)

    Returns:
        Time to start fetch from. UTC timezone.
    """
    if next_run := last_fetch.get(LAST_FETCH_TIME_KEY):
        start_fetch = parser(next_run)
    else:
        start_fetch, _ = parse_date_range(first_fetch_time)
    start_fetch.replace(tzinfo=timezone.utc)
    return start_fetch


def get_fetch_param_id(client: Client, last_run: dict, app_id: str, app_date_field: str) -> str:
    """ Get the from lastRun if available. Else ask the instance for the ID
    Args:
        client: Archer's client
        last_run: Last run object
        app_id: app id to search on
        app_date_field: the name of the date_field
    Returns:
        ID of the field
    """
    try:  # If exists
        fetch_param_id = last_run[FETCH_PARAM_ID_KEY]
    except KeyError:  # If not, search for it
        fetch_param_id = client.get_field_id(app_id, app_date_field)
    demisto.debug(f'Found a field ID {fetch_param_id=}')
    return fetch_param_id


def fetch_incidents_command(client: Client, params: dict, last_run: dict) -> Tuple[list, datetime]:
    """Fetches incidents
    Arguments:
        client: Archer's client
        params: demisto.params()
        last_run: demisto.getLastRun()
    Returns:
        incidents, next fetch
    """
    from_time = get_fetch_time(last_run, params.get('fetch_time', '3 days'))
    fetch_param_id = last_run[FETCH_PARAM_ID_KEY]
    demisto.debug(f'Starting fetch incidents with {from_time=} and {fetch_param_id=}')
    return fetch_incidents(
        client=client,
        params=params,
        from_time=from_time,
        fetch_param_id=fetch_param_id
    )


def main():
    params = demisto.params()
    credentials = params.get('credentials')
    base_url = params.get('url').strip('/').replace('rsaarcher', '')
    api_endpoint = params.get('api_endpoint') or 'rsaarcher/api'
    if 'rsaarcher' in api_endpoint:
        base_url = urljoin(base_url, 'rsaarcher')

    cache = get_integration_context()
    if not cache.get('fieldValueList'):
        cache['fieldValueList'] = {}
        set_integration_context(cache)

    client = Client(
        base_url,
        credentials.get('identifier'), credentials.get('password'),
        params.get('instanceName'),
        params.get('userDomain'),
        verify=not params.get('insecure', False),
        proxy=params.get('proxy', False),
    )
    commands = {
        'archer-search-applications': search_applications_command,
        'archer-get-application-fields': get_application_fields_command,
        'archer-get-field': get_field_command,
        'archer-get-mapping-by-level': get_mapping_by_level_command,
        'archer-get-record': get_record_command,
        'archer-create-record': create_record_command,
        'archer-delete-record': delete_record_command,
        'archer-update-record': update_record_command,
        'archer-execute-statistic-search-by-report': execute_statistics_command,
        'archer-get-reports': get_reports_command,
        'archer-get-search-options-by-guid': search_options_command,
        'archer-reset-cache': reset_cache_command,
        'archer-get-valuelist': get_value_list_command,
        'archer-upload-file': upload_and_associate_command,
        'archer-get-file': download_file_command,
        'archer-list-users': list_users_command,
        'archer-search-records': search_records_command,
        'archer-search-records-by-report': search_records_by_report_command,
        'archer-print-cache': print_cache_command,
    }

    command = demisto.command()
    LOG(f'Command being called is {command}')
    try:
        if command == 'fetch-incidents':
            last_run = demisto.getLastRun()
            last_run[FETCH_PARAM_ID_KEY] = get_fetch_param_id(
                client, last_run, params['applicationId'], params['applicationDateField']
            )
            incidents, next_fetch = fetch_incidents_command(client, params, last_run)
            demisto.debug(f'Setting next run to {next_fetch}')
            last_run[LAST_FETCH_TIME_KEY] = next_fetch.strftime(OCCURRED_FORMAT)
            demisto.setLastRun(last_run)
            demisto.incidents(incidents)
        elif command == 'test-module':
            demisto.results(test_module(client, params))
        elif command in commands:
            return commands[command](client, demisto.args())
        else:
            return_error('Command not found.')
    except Exception as e:
        return_error(f'Unexpected error: {str(e)}, traceback: {traceback.format_exc()}')


if __name__ in ('__builtin__', 'builtins', '__main__'):
    main()
