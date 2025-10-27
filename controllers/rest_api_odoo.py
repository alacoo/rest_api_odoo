# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Ayana KP (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import json
import logging
from odoo import http
from odoo.http import request
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class RestApi(http.Controller):
    """This is a controller which is used to generate responses based on the
    api requests"""

    def auth_api_key(self, api_key):
        """This function is used to authenticate the api-key when sending a
        request"""
        user_id = request.env['res.users'].sudo().search([('api_key', '=', api_key)])
        if api_key is not None and user_id:
             response = True
        elif not user_id:
            response = ('<html><body><h2>Invalid <i>API Key</i> '
                        '!</h2></body></html>')
        else:
            response = ("<html><body><h2>No <i>API Key</i> Provided "
                        "!</h2></body></html>")
        return response

    def generate_response(self, method, model, rec_id):
        """This function is used to generate the response based on the type
        of request and the parameters given"""
        option = request.env['connection.api'].search(
            [('model_id', '=', model)], limit=1)
        if not option:
            return ("<html><body><h2>No Record Created for the model"
                    "</h2></body></html>")
        model_name = option.model_id.model

        # Helper to format records
        def format_records(records):
            for record in records:
                for key, value in record.items():
                    if isinstance(value, (datetime, date)):
                        record[key] = value.isoformat()
            return records

        # Handle GET request
        if method == 'GET':
            if not option.is_get:
                return ("<html><body><h2>Method Not Allowed</h2></body></html>")
            try:
                # For GET, data can be in body (for tools) or not (for browsers)
                data = json.loads(
                    request.httprequest.data) if request.httprequest.data else {}
                fields = data.get('fields', [])
                if not fields:
                    return ("<html><body><h2>No fields selected for the model"
                            "</h2></body></html>")
                domain = data.get('domain', [])
                if rec_id != 0:
                    domain.append(('id', '=', rec_id))

                records = request.env[str(model_name)].search_read(
                    domain=domain, fields=fields)
                response_data = json.dumps(
                    {'records': format_records(records)})
                return request.make_response(data=response_data)
            except Exception as e:
                _logger.error(f"Error processing GET request: {e}")
                return ("<html><body><h2>Invalid JSON Data</h2></body></html>")

        # Handle POST request (for Create or Read)
        if method == 'POST':
            try:
                data = json.loads(request.httprequest.data)
                # Case 1: Read request (using POST for browser compatibility)
                if 'values' not in data:
                    if not option.is_get:
                        return ("<html><body><h2>Read (via POST) Not Allowed"
                                "</h2></body></html>")
                    fields = data.get('fields', [])
                    if not fields:
                        return (
                            "<html><body><h2>No fields selected for the model"
                            "</h2></body></html>")
                    domain = data.get('domain', [])
                    if rec_id != 0:
                        domain.append(('id', '=', rec_id))
                    records = request.env[str(model_name)].search_read(
                        domain=domain, fields=fields)
                    response_data = json.dumps(
                        {'records': format_records(records)})
                    return request.make_response(data=response_data)
                # Case 2: Create request
                else:
                    if not option.is_post:
                        return ("<html><body><h2>Create (POST) Not Allowed"
                                "</h2></body></html>")
                    fields = data.get('fields', [])
                    new_resource = request.env[str(model_name)].create(
                        data['values'])
                    if fields:
                        new_records = request.env[
                            str(model_name)].search_read(
                            domain=[('id', '=', new_resource.id)],
                            fields=fields)
                        response_data = json.dumps(
                            {'New resource': format_records(new_records)})
                    else:
                        response_data = json.dumps(
                            {'New resource ID': new_resource.id})
                    return request.make_response(data=response_data)
            except Exception as e:
                _logger.error(f"Error processing POST request: {e}")
                return ("<html><body><h2>Invalid JSON Data</h2></body></html>")

        # Handle PUT request
        if method == 'PUT':
            if not option.is_put:
                return ("<html><body><h2>Method Not Allowed</h2></body></html>")
            if rec_id == 0:
                return ("<html><body><h2>No ID Provided</h2></body></html>")
            resource = request.env[str(model_name)].browse(int(rec_id))
            if not resource.exists():
                return ("<html><body><h2>Resource not found</h2></body></html>")
            try:
                data = json.loads(request.httprequest.data)
                fields = data.get('fields', [])
                resource.write(data['values'])
                if fields:
                    updated_records = request.env[
                        str(model_name)].search_read(
                        domain=[('id', '=', resource.id)], fields=fields)
                    response_data = json.dumps(
                        {'Updated resource': format_records(updated_records)})
                else:
                    response_data = json.dumps(
                        {'Updated resource ID': resource.id})
                return request.make_response(data=response_data)
            except Exception as e:
                _logger.error(f"Error processing PUT request: {e}")
                return ("<html><body><h2>Invalid JSON Data</h2></body></html>")

        # Handle DELETE request
        if method == 'DELETE':
            if not option.is_delete:
                return ("<html><body><h2>Method Not Allowed</h2></body></html>")
            if rec_id == 0:
                return ("<html><body><h2>No ID Provided</h2></body></html>")
            resource = request.env[str(model_name)].browse(int(rec_id))
            if not resource.exists():
                return ("<html><body><h2>Resource not found</h2></body></html>")

            records = request.env[str(model_name)].search_read(
                domain=[('id', '=', resource.id)],
                fields=['id', 'display_name'])
            resource.unlink()
            response_data = json.dumps(
                {"Resource deleted": format_records(records)})
            return request.make_response(data=response_data)

    @http.route(['/send_request'], type='http',
                auth='none',
                methods=['GET', 'POST', 'PUT', 'DELETE'], csrf=False)
    def fetch_data(self, **kw):
        """This controller will be called when sending a request to the
        specified url, and it will authenticate the api-key and then will
        generate the result"""
        http_method = request.httprequest.method

        api_key = request.httprequest.headers.get('api-key')
        auth_api = self.auth_api_key(api_key)
        model = kw.get('model')
        username = request.httprequest.headers.get('login')
        password = request.httprequest.headers.get('password')
        credential = {'login': username, 'password': password, 'type': 'password'}
        request.session.authenticate(request.session.db, credential)
        model_id = request.env['ir.model'].search(
            [('model', '=', model)])
        if not model_id:
            return ("<html><body><h3>Invalid model, check spelling or maybe "
                    "the related "
                    "module is not installed"
                    "</h3></body></html>")

        if auth_api == True:
            if not kw.get('Id'):
                rec_id = 0
            else:
                rec_id = int(kw.get('Id'))
            result = self.generate_response(http_method, model_id.id, rec_id)
            return result
        else:
            return auth_api

    @http.route(['/odoo_connect'], type="http", auth="none", csrf=False,
                methods=['GET'])
    def odoo_connect(self, **kw):
        """This is the controller which initializes the api transaction by
        generating the api-key for specific user and database"""
        username = request.httprequest.headers.get('login')
        password = request.httprequest.headers.get('password')
        db = request.httprequest.headers.get('db')
        try:
            request.session.update(http.get_default_session(), db=db)
            credential = {'login': username, 'password': password,
                          'type': 'password'}

            auth = request.session.authenticate(db, credential)
            user = request.env['res.users'].browse(auth['uid'])
            api_key = request.env.user.generate_api(username)
            datas = json.dumps({"Status": "auth successful",
                                "User": user.name,
                                "api-key": api_key})
            return request.make_response(data=datas)
        except:
            return ("<html><body><h2>wrong login credentials"
                    "</h2></body></html>")
