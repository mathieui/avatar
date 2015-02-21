#!/usr/bin/env python3
"""
Simple web service which fetches avatars from XMPP vcards
"""

import logging
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

import asyncio
import base64
import slixmpp
from aiohttp import web

# Image shown when the avatar is not found (e.g. empty vcard)
EMPTY_AVATAR = """<svg xmlns="http://www.w3.org/2000/svg" version="1.1">
<rect width="150" height="150" fill="rgb(125, 125, 125)" stroke-width="1" stroke="rgb(0, 0, 0)"/>
<text x="75" y="100" text-anchor="middle" font-size="100">?</text>
</svg>"""

XMPP = None

class VCardFetcher(slixmpp.ClientXMPP):
    """
    Global XMPP client object
    """
    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid=jid, password=password)
        self.register_plugin('xep_0054')

    def fetch_vcard(self, jid_to, callback):
        "Send a vcard request to a specific JID"
        self['xep_0054'].get_vcard(jid=jid_to, callback=callback)

@asyncio.coroutine
def handle(request):
    "Handle the HTTP request and block until the vcard is fetched"
    err_404 = web.Response(status=404, text='Not found')
    try:
        jid = slixmpp.JID(request.match_info.get('jid', ""))
    except slixmpp.InvalidJID:
        return err_404
    else:
        if not jid:
            return err_404

    queue = asyncio.Queue(maxsize=1)

    def vcard_callback(result):
        "Parse the vcard result"
        img_type = result.find('{vcard-temp}vCard/{vcard-temp}PHOTO/{vcard-temp}TYPE')
        img_val = result.find('{vcard-temp}vCard/{vcard-temp}PHOTO/{vcard-temp}BINVAL')

        if None in (img_type, img_val) or None in (img_type.text, img_val.text):
            queue.put_nowait({'status': 404,
                              'content_type': 'image/svg+xml',
                              'text': EMPTY_AVATAR})
        else:
            try:
                img_val = base64.decodebytes(img_val.text.encode('ascii'))
                queue.put_nowait({'body': img_val,
                                  'content_type': img_type.text})
            except:
                queue.put_nowait({'status': 404,
                                  'content_type': 'image/svg+xml',
                                  'text': EMPTY_AVATAR})
    try:
        XMPP.fetch_vcard(jid_to=jid, callback=vcard_callback)
    except slixmpp.xmlstream.xmlstream.NotConnectedError:
        log.error('XMPP Client Not connected')
        return err_404
    result = yield from queue.get()
    return web.Response(**result)

@asyncio.coroutine
def init(loop, host: str, port: str, avatar_prefix: str):
    "Initialize the HTTP server"
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/%s{jid}' % avatar_prefix, handle)
    srv = yield from loop.create_server(app.make_handler(), host, port)
    log.info("Server started at http://%s:%s", host, port)
    return srv

def main(namespace):
    "Start the xmpp client and delegate the main loop to asyncio"
    loop = asyncio.get_event_loop()
    global XMPP
    XMPP = VCardFetcher(namespace.jid, namespace.password)
    XMPP.connect()
    loop.run_until_complete(init(loop, namespace.host, namespace.port,
                                 namespace.avatar_prefix))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        import sys
        sys.exit(0)

def parse_args():
    "Parse the command-line arguments"
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--jid', dest='jid', default=JID,
                        help='JID to use for fetching the vcards')
    parser.add_argument('--password', dest='password', default=PASSWORD,
                        help='Password linked to the JID')
    parser.add_argument('--host', dest='host', default=HOST,
                        help='Host on which the HTTP server will listen')
    parser.add_argument('--port', dest='port', default=PORT,
                        help='Port on which the HTTP server will listen')
    parser.add_argument('--avatar_prefix', dest='avatar_prefix',
                        default=AVATAR_PREFIX,
                        help='Prefix path for the avatar request')
    return parser.parse_args()

# static settings, to avoid using command-line args
HOST = '127.0.0.1'
PORT = 8765
JID = 'changeme@example.com'
PASSWORD = 'changemetoo'
AVATAR_PREFIX = 'avatar/'

if __name__ == "__main__":
    main(parse_args())

