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
        self.connected_future = asyncio.Future()
        self.add_event_handler('session_start', self.on_session_start)
        self.register_plugin('xep_0054')

    def fetch_vcard(self, jid_to):
        "Send a vcard request to a specific JID"
        return self['xep_0054'].get_vcard(jid=jid_to, timeout=10)

    def on_session_start(self, *args, **kwargs):
        "Unblock when the session is established"
        self.connected_future.set_result(True)

    def reset_future(self):
        "Reset the future in case of disconnection"
        self.connected_future = asyncio.Future()

def parse_vcard(vcard):
    img_type = vcard.find('{vcard-temp}vCard/{vcard-temp}PHOTO/{vcard-temp}TYPE')
    img_val = vcard.find('{vcard-temp}vCard/{vcard-temp}PHOTO/{vcard-temp}BINVAL')

    if None in (img_type, img_val) or None in (img_type.text, img_val.text):
        reply = {
            'status': 404,
            'content_type': 'image/svg+xml',
            'text': EMPTY_AVATAR
        }
    else:
        try:
            img_val = base64.decodebytes(img_val.text.encode('ascii'))
            reply = {
                'body': img_val,
                 'content_type': img_type.text
            }
        except Exception as e:
            log.warning("Failed decoding base64 for %s (%s)", jid, e)
            reply = {
                'status': 404,
                 'content_type': 'image/svg+xml',
                 'text': EMPTY_AVATAR
            }
    return reply

async def handle(request):
    "Handle the HTTP request and block until the vcard is fetched"
    err_404 = web.Response(status=404, text='Not found')
    try:
        jid = slixmpp.JID(request.match_info.get('jid', ""))
    except slixmpp.InvalidJID:
        return err_404
    else:
        if not jid:
            return err_404
    try:
        vcard = await XMPP.fetch_vcard(jid_to=jid)
    except Exception:
        log.warning("Failed to fetch vcard for %s", jid, exc_info=True)
        return err_404

    reply = parse_vcard(vcard)
    return web.Response(**reply)

async def init(loop, host: str, port: str, avatar_prefix: str):
    "Initialize the HTTP server"
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/%s{jid}' % avatar_prefix, handle)
    srv = await loop.create_server(app.make_handler(), host, port)
    log.info("Server started at http://%s:%s", host, port)
    return srv

def main(namespace):
    "Start the xmpp client and delegate the main loop to asyncio"
    loop = asyncio.get_event_loop()
    global XMPP
    XMPP = VCardFetcher(namespace.jid, namespace.password)
    XMPP.connect()
    loop.run_until_complete(XMPP.connected_future)
    XMPP.reset_future()
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
    parser.add_argument('--jid', '-j', dest='jid', default=JID,
                        help='JID to use for fetching the vcards')
    parser.add_argument('--password', '-p', dest='password', default=PASSWORD,
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

