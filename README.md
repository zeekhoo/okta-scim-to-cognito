# Introduction
Based on the [okta-scim-beta](https://github.com/oktadeveloper/okta-scim-beta) project,
this example shows how to use Okta's cloud-based SCIM connector to automatically provision 
and deprovision users managed by Okta into a single Cognito user-pool.

This example code was written for **Python 2.7** and uses the excellent [Boto python interface
to AWS](https://boto3.readthedocs.io/en/latest/guide/quickstart.html), which has support for Cognito.


# Running the sample project

`git checkout` this repository, then:

1.  `cd` to the directory you just checked out:

        $ cd okta-scim-to-cognito
2.  Create an isolated Python environment named "venv" using [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/):

        $ virtualenv venv
3.  Next, activate the newly created virtualenv:

        $ source venv/bin/activate
4.  Then, install the dependencies for the sample SCIM server using
    Python's ["pip" package manager](https://en.wikipedia.org/wiki/Pip_%28package_manager%29):

        $ pip install -r requirements.txt
5.  Rename .sample.config.json to .sample.json

        $ mv .sample.config.json .sample.json

6.  Edit .sample.json and provide the values for user_pool_id, access_key and secret_key.
    This project only provisions into a single user-pool, so you must supply the name for
    that user-pool. 
    Boto requires AWS credentials in order to make requests. Create security credentials
    for an IAM user that has the AmazonCognitoPowerUser policy and enter the access_key
    and secret_key values from the credentials into this file.
    
7.  Start the example SCIM server using this command:

        $ python scim-server.py

8.  Make this service reachable by the internet with [ngrok](https://ngrok.com/). 
    Download and install ngrok, then start it up

        $ ngrok http 5000

## AWS Cognito User-pool requirements
The sample project provisions and deprovisions users into a single congnito user-pool.
At the minimum, the pool must have the following attributes:
1.  email
2.  name

For simplicity's sake, the sample project creates users staged with
the temporary password '123456'. In your user-pool's policy configuration: 
1.  Set password minimum length = 6
2.  Do not require special characters, uppercase or lowercase letters
 


## Okta setup
If you don't already have an Okta org, create an 
[Okta Developer account](https://www.okta.com/developer/signup/). 

Once you have access to your account, from the Admin UI:
1.  Navigate to Applications > Applications. 
Click on the green button [Add Application]
 
2.  In the search box, search for "SCIM 2.0 Test App (Header Auth)"
and click [Add]

3.  During the Provisioning setup step, check the "Enable Provisioning features" box.

4.  In the SCIM 2.0 Base Url field, enter https://your-ngrok-https-forwarding-url/scim/v2

    e.g https://d0aafa9e.ngrok.io/scim/v2
    
5.  Enter any random value for API Token. The field is required, 
    but the sample project will not be using it. In production, protect your
    endpoints with an API Key. (Or Basic Auth or OAuth2. Recall from the previous steps, 
    there are SCIM templates for each of the 3 types of auth protocols)

6.  Click [Test API Credentials]. 

If you receive a success message in the last step above, your configuration
is complete. Now you can assign and unassign users to your app and watch it
automatically provision and deprovision users to your Cognito user-pool.



# Appendix
## Understanding of User Provisioning in Okta

Okta is a universal directory with the main focus in storing
identity related information.  Users can be created in Okta directly
as local users or imported from external system like Active
Directory or a [Human Resource Management Software](https://en.wikipedia.org/wiki/Category:Human_resource_management_software) system.

An Okta user schema contains many different user attributes,
but always contains a user name, first name, last name, and
email address. This schema can be extended.

Okta user attributes can be mapped from a source into Okta and can
be mapped from Okta to a target.

Below are the main operations in Okta's SCIM user provisioning lifecycle:

1.  Create a user account.
2.  Read a list of accounts, with support for searching for a preexisting account.
3.  Update an account (user profile changes, entitlement changes, etc).
4.  Deactivate an account.

In Okta, an application instance is a connector that provides Single Sign-On
and provisioning functionality with the target application.


## Required SCIM Capabilities

Okta supports provisioning to both SCIM 1.1 and SCIM 2.0 APIs.

If you haven't implemented SCIM, Okta recommends that you implement
SCIM 2.0.

Okta implements SCIM 2.0 as described in RFCs [7642](https://tools.ietf.org/html/rfc7642), [7643](https://tools.ietf.org/html/rfc7643), [7644](https://tools.ietf.org/html/rfc7644).

If you are writing a SCIM implementation for the first time, an
important part of the planning process is determining which of
Okta's provisioning features your SCIM API can or should support and
which features you do not need to support.

Specifically, you do not need to implement the SCIM 2.0
specification fully to work with Okta. At a minimum, Okta requires that
your SCIM 2.0 API implement the features described below:

### Base URL

The API endpoint for your SCIM API **MUST** be secured via [TLS](https://tools.ietf.org/html/rfc5246)
(`https://`), Okta *does not* connect to unsecured API endpoints.

You can choose any Base URL for your API endpoint. If you
are implementing a brand new SCIM API, we suggest using `/scim/v2`
as your Base URL; for example: `https://example.com/scim/v2` -
however, you must support the URL structure described in the
["SCIM Endpoints and HTTP Methods" section of RFC7644](https://tools.ietf.org/html/rfc7644#section-3.2).

### Authentication

Your SCIM API **MUST** be secured against anonymous access. At the
moment, Okta supports authentication against SCIM APIs with one of
the following methods:

1.  [OAuth 2.0](http://oauth.net/2/)
2.  [Basic Authentication](https://en.wikipedia.org/wiki/Basic_access_authentication)
3.  Custom HTTP Header

### Basic User Schema

Your service must be capable of storing the following four user
attributes:

1.  User ID (`userName`)
2.  First Name (`name.givenName`)
3.  Last Name (`name.familyName`)
4.  Email (`emails`)

Note that Okta supports more than the four user attributes listed
above. However, these four attributes are the base attributes that
you must support.  The full user schema for SCIM 2.0 is described
in [section 4 of RFC 7643](https://tools.ietf.org/html/rfc7643#section-4).

> **Best Practice:** Keep your User ID distinct from the User Email
> Address. Many systems use an email address as a user identifier,
> but this is not recommended, as email addresses often change. Using
> a unique User ID to identify user resources prevents future
> complications.

If your service supports user attributes beyond those four base
attributes, add support for those additional
attributes to your SCIM API. In some cases, you might need to
configure Okta to map non-standard user attributes into the user
profile for your application.


# License information

    Copyright © 2016, Okta, Inc.
    
    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software and associated documentation files (the
    "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish,
    distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to
    the following conditions:
    
    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.