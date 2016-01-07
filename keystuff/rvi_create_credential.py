#!/usr/bin/python

#
# Copyright (C) 2015, Jaguar Land Rover
#
# This program is licensed under the terms and conditions of the
# Mozilla Public License, version 2.0.  T full text of the
# Mozilla Public License is at https://www.mozilla.org/MPL/2.0/
#
#  Create a certificate giving the sender the right to invoke and
#

import getopt
import sys
from Crypto.PublicKey import RSA

# apt-get install python-dev
# apt-get install libffi-dev
# pip install cryptography
# pip install PyJWT

import jwt
import time
import json
import base64
import struct

def long2intarr(long_int):
    _bytes = []
    while long_int:
        long_int, r = divmod(long_int, 256)
        _bytes.insert(0, r)
    return _bytes

# copied from https://github.com/rohe/pyjwkest
def long_to_base64(n):
    bys = long2intarr(n)
    data = struct.pack('%sB' % len(bys), *bys)
    if not len(data):
        data = '\x00'
    s = base64.urlsafe_b64encode(data).rstrip(b'=')
    return s


def read_x509_cert_pem_file(file_name):
    CONST_PEM_CERT_BEGIN="-----BEGIN CERTIFICATE-----\n"
    CONST_PEM_CERT_END="-----END CERTIFICATE-----\n"

    try:
        fp = open(file_name, "r")
        dev_pem = fp.read()
        fp.close()

    except IOError as e:
        print "Could read device certificate from {0}: {1}".format(a, e.strerror)
        sys.exit(255)

    # Check that cert file starts with the correct tag
    pem_start = dev_pem.find(CONST_PEM_CERT_BEGIN)
    if pem_start != 0:
        print "Device certificate file {} does not start".format(file_name)
        print "with certificate identifier."
        sys.exit(255)

    # Move to first character after start tag.
    pem_start += len(CONST_PEM_CERT_BEGIN)

    # Find end tag.
    pem_end = dev_pem.find(CONST_PEM_CERT_END)
    if pem_end == -1:
        print "Device certificate file {} does not end".format(file_name)
        print "with certificate identifier."
        sys.exit(255)

    # Return string between tags, stripped of \r and \n
    return dev_pem[pem_start: pem_end].replace("\n", "").replace("\r", "")


def usage():
    print "Usage:", sys.argv[0], "--id=<id> --invoke='<services>' -register='<services>' \\"
    print "                       --root_key=<file> --start='<date/time>' --stop='<date/time>' \\"
    print "                       --out=<file>"
    print
    print "  --id=<id>                       System-wide unique credential ID"
    print
    print "  --invoke='<services>'           Right to invoke service. Space separate multiple services."
    print
    print "  --register='<services>'         Right to register service. Space separate multiple services."
    print "                                  At least one --invoke or --register must be given."
    print
    print "  --root_key=<file>               Private, PEM-encoded root key to sign credential with"
    print "                                  Mandatory"
    print
    print "  --device_cert=<file>            Device X.509 certificate to include in credential"
    print "                                  Mandatory"
    print
    print "  --start='<YYYY-MM-DD HH:MM:SS>' Date and time when certificate is activated."
    print "                                  Default: current time."
    print
    print "  --stop='<YYYY-MM-DD HH:MM:SS>'  Date and time when certificate is deactivated."
    print "                                  Default: 365 days from current time"
    print
    print "  --jwt_out=<file>                File name to store JWT-encoded certificate in."
    print "                                  Default: stdout"
    print
    print "  --cred_out=<file>               File name to unencoded JSON credential in."
    print "                                  Default: Do not store certificate"
    print
    print "  --issuer=issuer                 Name of the issuer."
    print "                                  Mandatory"
    print
    print "Root key file is generated by steps described in doc/rvi_protocol.md"
    print
    print "Device X.509 certificate is generated by steps described in doc/rvi_protocol.md"
    print
    print "Credentials file specified by out should be placed in 'priv/credentials'"
    print
    print
    print "Example:"
    print "./rvi_create_credential.py --id=317624d8-2ccf-11e5-993c-7f3b5182c649 \\"
    print "                            --device_cert=device_cert.crt \\"
    print "                            --start='2014-12-01 00:00:00' \\"
    print "                            --stop='2020-12-31 23:59:59' \\"
    print "                            --root_key=root_key.pem \\"
    print "                            --issuer=GENIVI \\"
    print "                            --register='genivi.org/vin/abc/unlock genivi.org/vin/abc/lock' \\"
    print "                            --invoke='genivi.org/backend/report genivi.org/backend/set_state' \\"
    print "                            --jwt_out=lock_cert.jwt \\"
    print "                            --cred_out=lock_credential.json"
    sys.exit(255)

try:
    opts, args = getopt.getopt(sys.argv[1:], "", [ 'issuer=', 'invoke=', 'register=',
                                                   'root_key=', 'start=',
                                                   'stop=', 'cred_out=', 'id=',
                                                   'jwt_out=', 'device_cert='])
except getopt.GetoptError as e:
    print
    print e
    print
    usage()

start=int(time.time())
stop=int(time.time()) + 86400 * 365

issuer=None
invoke=None
register=None
root_key=None
device_cert=None
jwt_out_file=None
cred_out_file=None
id_string=None
for o, a in opts:
    if o == "--start":
        try:
            start = int(time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S")))
        except:
            print
            print "Incorrect start time: {}".format(a)
            print
            usage()

    elif o == '--root_key':
        try:
            root_key_fname = a
            root_key_file = open(root_key_fname, "r")
            root_key = RSA.importKey(root_key_file.read())
            root_key_file.close()
        except IOError as e:
            print "Coould read root cert from {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    elif o == '--device_cert':
            device_cert = read_x509_cert_pem_file(a)

    elif o == "--stop":
        try:
            stop = int(time.mktime(time.strptime(a, "%Y-%m-%d %H:%M:%S")))
        except:
            print
            print "Incorrect stop time: {}".format(a)
            print
            usage()

    elif o == '--invoke':
        invoke=a.split(' ')

    elif o == '--register':
        register=a.split(' ')

    elif o == '--id':
        id_string=a

    elif o == '--issuer':
        issuer=a

    elif o == '--jwt_out':
        try:
            jwt_out_file = open(a, "w")
        except IOError as e:
            print "Could not write to JWT file {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    elif o == '--cred_out':
        try:
            cred_out_file = open(a, "w")
        except IOError as e:
            print "Could not write to credentials file {0}: {1}".format(a, e.strerror)
            sys.exit(255)

    else:
        print
        print "Unknown command line argument: {}".format(o)
        print
        usage()

if jwt_out_file == None:
    jwt_out_file = sys.stdout

if not invoke and not register:
    print
    print "At least one --invoke or --register service must be specified."
    print
    usage()

if not root_key:
    print
    print "No --root_key=<root_key_file.pem> specified"
    print
    usage()

if not issuer:
    print
    print "No --issuer=<credential issuer> specified"
    print
    usage()

if not device_cert:
    print
    print "No --device_cert=<device_public_key_file.pem> specified"
    print
    usage()

if not id_string:
    print
    print "No --id=<id_string> specified"
    print
    usage()


# Create a JSON Web Key based off our public device key PEM file


cred = {
    'iss': issuer,
    'id': id_string,
    'right_to_register': register,
    'right_to_invoke': invoke,
    'create_timestamp': int(time.time()),
    'device_cert': device_cert,
    'validity': {
        'start': start,
        'stop': stop
    }
}



encoded = jwt.encode(cred, root_key.exportKey("PEM"), algorithm='RS256')

# Validate
try:
    jwt.decode(encoded, root_key.publickey().exportKey("PEM"))
except:
    print "FAILED: Could not verify signed JSON Web Token using public part of"
    print "        root key {}".format(root_key_fname)

jwt_out_file.write(encoded)
jwt_out_file.close()

if cred_out_file:
    cred_out_file.write(json.dumps(cred, sort_keys=True, indent=4, separators=(',', ': ')) + '\n')
    cred_out_file.close()
