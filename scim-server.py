#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2016, Okta, Inc.
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import flask
from flask import Flask
from flask import render_template
from flask import request
from flask import url_for
import re
import boto3


USER_POOL_ID = 'us-west-2_iloZUQ8lJ'

app = Flask(__name__)


class ListResponse():
    def __init__(self, list, start_index=1, count=None, total_results=0):
        self.list = list
        self.start_index = start_index
        self.count = count
        self.total_results = total_results

    def to_scim_resource(self):
        rv = {
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
            "totalResults": self.total_results,
            "startIndex": self.start_index,
            "Resources": []
        }
        resources = []
        for item in self.list:
            user = CognitoUser(item)
            resources.append(user.to_scim_resource())
        if self.count:
            rv['itemsPerPage'] = self.count
        rv['Resources'] = resources
        return rv


class CognitoUser:
    def __init__(self, resource):
        self.update(resource)

    def update(self, resource):
        setattr(self, 'userName', resource['Username'])
        setattr(self, 'active', resource['Enabled'])

        displayName = resource['Username']
        if 'Attributes' in resource:
            for pair in resource['Attributes']:
                if pair['Name'] == 'name':
                    setattr(self, 'displayName', pair['Value'])
        if 'UserAttributes' in resource:
            for pair in resource['UserAttributes']:
                if pair['Name'] == 'name':
                    setattr(self, 'displayName', pair['Value'])

        setattr(self, 'displayName', displayName)

    def to_scim_resource(self):
        rv = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": self.userName,
            "userName": self.userName,
            "name": {
                "displayName": self.displayName
            },
            "active": self.active,
            "meta": {
                "resourceType": "User",
                "location": url_for('user_get',
                                    user_id=self.userName,
                                    _external=True),
                # "created": "2010-01-23T04:56:22Z",
                # "lastModified": "2011-05-13T04:42:34Z",
            }
        }
        return rv


class User:
    def __init__(self, resource):
        self.update(resource)

    def update(self, resource):
        for attribute in ['userName', 'active']:
            if attribute in resource:
                setattr(self, attribute, resource[attribute])
        for attribute in ['givenName', 'middleName', 'familyName']:
            if attribute in resource['name']:
                setattr(self, attribute, resource['name'][attribute])

    def to_scim_resource(self):
        rv = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": self.userName,
            "userName": self.userName,
            "name": {
                "familyName": self.familyName,
                "givenName": self.givenName,
                "middleName": self.middleName
            },
            "active": self.active,
            "meta": {
                "resourceType": "User",
                "location": url_for('user_get',
                                    user_id=self.userName,
                                    _external=True),
                # "created": "2010-01-23T04:56:22Z",
                # "lastModified": "2011-05-13T04:42:34Z",
            }
        }
        return rv


def scim_error(message, status_code=500):
    rv = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "detail": message,
        "status": str(status_code)
    }
    return flask.jsonify(rv), status_code


# def send_to_browser(obj):
#     socketio.emit('user',
#                   {'data': obj},
#                   broadcast=True,
#                   namespace='/test')


def render_json(obj):
    user = CognitoUser(obj)
    rv = user.to_scim_resource()
    return flask.jsonify(rv)


# @socketio.on('connect', namespace='/test')
# def test_connect():
#     for user in User.query.filter_by(active=True).all():
#         emit('user', {'data': user.to_scim_resource()})
#
#
# @socketio.on('disconnect', namespace='/test')
# def test_disconnect():
#     print('Client disconnected')


@app.route('/')
def hello():
    return render_template('base.html')


@app.route("/scim/v2/Users/<user_id>", methods=['GET'])
def user_get(user_id):
    try:
        cognito_cli = boto3.client('cognito-idp')
        response = cognito_cli.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        print('response = {}'.format(response))
    except:
        return scim_error("User not found", 404)
    return render_json(response)


@app.route("/scim/v2/Users", methods=['POST'])
def users_post():
    user_resource = request.get_json(force=True)
    print('user_resource = {}'.format(user_resource))

    username = user_resource['userName']
    name = user_resource['name']['givenName'] + ' ' + user_resource['name']['familyName']

    cognito_cli = boto3.client('cognito-idp')
    response = cognito_cli.admin_create_user(
        UserPoolId=USER_POOL_ID,
        Username=username,
        UserAttributes=[
            {'Name': 'name', 'Value': name},
            {'Name': 'email', 'Value': username}
        ],
        TemporaryPassword='123456',
        ForceAliasCreation=False,
        MessageAction='SUPPRESS',
        DesiredDeliveryMediums=['EMAIL']
    )
    print('response = {}'.format(response))
    user = CognitoUser(response['User'])
    rv = user.to_scim_resource()
    resp = flask.jsonify(rv)
    resp.headers['Location'] = url_for('user_get', user_id=username, _external=True)
    return resp, 201

# @app.route("/scim/v2/Users", methods=['POST'])
# def users_post():
#     user_resource = request.get_json(force=True)
#     user = User(user_resource)
#     user.id = str(uuid.uuid4())
#     db.session.add(user)
#     db.session.commit()
#     rv = user.to_scim_resource()
#     send_to_browser(rv)
#     resp = flask.jsonify(rv)
#     resp.headers['Location'] = url_for('user_get',
#                                        user_id=user.userName,
#                                        _external=True)
#     return resp, 201

# to-do
# @app.route("/scim/v2/Users/<user_id>", methods=['PUT'])
# def users_put(user_id):
#     user_resource = request.get_json(force=True)
#     user = User.query.filter_by(id=user_id).one()
#     user.update(user_resource)
#     db.session.add(user)
#     db.session.commit()
#     return render_json(user)


# to-do
# @app.route("/scim/v2/Users/<user_id>", methods=['PATCH'])
# def users_patch(user_id):
#     patch_resource = request.get_json(force=True)
#     for attribute in ['schemas', 'Operations']:
#         if attribute not in patch_resource:
#             message = "Payload must contain '{}' attribute.".format(attribute)
#             return message, 400
#     schema_patchop = 'urn:ietf:params:scim:api:messages:2.0:PatchOp'
#     if schema_patchop not in patch_resource['schemas']:
#         return "The 'schemas' type in this request is not supported.", 501
#     user = User.query.filter_by(id=user_id).one()
#     for operation in patch_resource['Operations']:
#         if 'op' not in operation and operation['op'] != 'replace':
#             continue
#         value = operation['value']
#         for key in value.keys():
#             setattr(user, key, value[key])
#     db.session.add(user)
#     db.session.commit()
#     return render_json(user)


# to-do
@app.route("/scim/v2/Users", methods=['GET'])
def users_get():
    print('request = {}'.format(request))
    count = int(request.args.get('count', 100))
    start_index = int(request.args.get('startIndex', 1))
    if start_index < 1:
        start_index = 1
    start_index -= 1

    match = None
    filter = None
    request_filter = request.args.get('filter')
    if request_filter:
        match = re.match('(\w+) eq "([^"]*)"', request_filter)
    if match:
        (search_key_name, search_value) = match.groups()
        if search_key_name == 'userName':
            search_key_name = 'username'
        else:
            search_key_name = search_key_name.lower()
        filter = search_key_name + ' = ' + '"' + search_value + '"'

    print('filter = {}'.format(filter))
    cognito_cli = boto3.client('cognito-idp')
    if filter:
        response = cognito_cli.list_users(
            UserPoolId=USER_POOL_ID,
            AttributesToGet=[
                'name', 'email'
            ],
            Limit=60,
            Filter=filter
        )
    else:
        response = cognito_cli.list_users(
            UserPoolId=USER_POOL_ID,
            AttributesToGet=[
                'name', 'email'
            ],
            Limit=60
        )

    found = response['Users']
    print('found = {}'.format(found))

    total_results = len(found)
    print('total_results = {}'.format(total_results))

    rv = ListResponse(found,
                      start_index=start_index,
                      count=count,
                      total_results=total_results)
    return flask.jsonify(rv.to_scim_resource())


# to-do
# @app.route("/scim/v2/Groups", methods=['GET'])
# def groups_get():
#     rv = ListResponse([])
#     return flask.jsonify(rv.to_scim_resource())


# if __name__ == "__main__":
#     try:
#         User.query.one()
#     except:
#         db.create_all()
#     app.debug = True
#     socketio.run(app)


if __name__ == "__main__":
    app.run()