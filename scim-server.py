#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright © 2016, Okta, Inc.

import flask
from flask import Flask
from flask import render_template
from flask import request
from flask import url_for
import re
import json
import boto3


app = Flask(__name__)

config = None
with open('.config.json') as config_file:
    config_json = json.load(config_file)
    config = config_json['config']

USER_POOL_ID = config['aws']['user_pool_id']
ACCESS_KEY = config['aws']['access_key']
SECRET_KEY = config['aws']['secret_key']

cognito_client = boto3.client(
    'cognito-idp',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


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


# Conforms the cognito user object to a SCIM format
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


def scim_error(message, status_code=500):
    rv = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "detail": message,
        "status": str(status_code)
    }
    return flask.jsonify(rv), status_code


def render_json(obj):
    user = CognitoUser(obj)
    rv = user.to_scim_resource()
    return flask.jsonify(rv)


@app.route('/')
def hello():
    return render_template('base.html')


@app.route("/scim/v2/Users/<user_id>", methods=['GET'])
def user_get(user_id):
    try:
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
    except:
        return scim_error("User not found", 404)
    return render_json(response)


@app.route("/scim/v2/Users", methods=['POST'])
def users_post():
    user_resource = request.get_json(force=True)

    username = user_resource['userName']
    name = user_resource['name']['givenName'] + ' ' + user_resource['name']['familyName']

    response = cognito_client.admin_create_user(
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
    user = CognitoUser(response['User'])
    rv = user.to_scim_resource()
    resp = flask.jsonify(rv)
    resp.headers['Location'] = url_for('user_get', user_id=username, _external=True)
    return resp, 201


@app.route("/scim/v2/Users/<user_id>", methods=['PUT'])
def users_put(user_id):
    user_resource = request.get_json(force=True)
    # TODO: Implement update user attributes

    try:
        user = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
    except:
        return scim_error("User not found", 404)

    return render_json(user)


@app.route("/scim/v2/Users/<user_id>", methods=['PATCH'])
def users_patch(user_id):
    patch_resource = request.get_json(force=True)
    for attribute in ['schemas', 'Operations']:
        if attribute not in patch_resource:
            message = "Payload must contain '{}' attribute.".format(attribute)
            return message, 400
    schema_patchop = 'urn:ietf:params:scim:api:messages:2.0:PatchOp'
    if schema_patchop not in patch_resource['schemas']:
        return "The 'schemas' type in this request is not supported.", 501

    deactivate = None
    reactivate = None
    for operation in patch_resource['Operations']:
        if 'op' not in operation and operation['op'] != 'replace':
            continue
        value = operation['value']
        for key in value.keys():
            if key == 'active':
                val = str(value[key])
                if val == ''.join('False'):
                    deactivate = True
                else:
                    reactivate = True
    if deactivate:
        try:
            response = cognito_client.admin_disable_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
        except:
            return scim_error("User not found", 404)
    if reactivate:
        try:
            response = cognito_client.admin_enable_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
        except:
            return scim_error("User not found", 404)

    try:
        user = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
    except:
        return scim_error("User not found", 404)
    return render_json(user)


@app.route("/scim/v2/Users", methods=['GET'])
def users_get():
    count = int(request.args.get('count', 100))
    start_index = int(request.args.get('startIndex', 1))
    if start_index < 1:
        start_index = 1
    start_index -= 1

    match = None
    filter = None
    search_key_name = None
    request_filter = request.args.get('filter')
    # Handling the filter users requirement...
    # see more info at: https://github.com/oktadeveloper/okta-scim-beta#filtering-on-id-username-and-emails
    if request_filter:
        match = re.match('(\w+) eq "([^"]*)"', request_filter)
    if match:
        (search_key_name, search_value) = match.groups()
        if search_key_name == 'userName':
            search_key_name = 'username'
        elif search_key_name == 'emails':
            search_key_name = 'email'
        elif search_key_name == 'id':
            search_key_name = 'username'
    if search_key_name:
        filter = search_key_name + ' = ' + '"' + search_value + '"'

    if filter:
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            AttributesToGet=[
                'name', 'email'
            ],
            Limit=60,
            Filter=filter
        )
    else:
        response = cognito_client.list_users(
            UserPoolId=USER_POOL_ID,
            AttributesToGet=[
                'name', 'email'
            ],
            Limit=60
        )

    found = response['Users']
    total_results = len(found)
    rv = ListResponse(found,
                      start_index=start_index,
                      count=count,
                      total_results=total_results)
    return flask.jsonify(rv.to_scim_resource())


@app.route("/scim/v2/Groups", methods=['GET'])
def groups_get():
    # TODO: implement GET Groups
    rv = ListResponse([])
    return flask.jsonify(rv.to_scim_resource())


if __name__ == "__main__":
    app.run()