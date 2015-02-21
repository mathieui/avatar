==================================
avatar.py: XMPP avatars on the web
==================================

This script is a simple web service used to link HTTP URLs to XMPP avatars
(used with vcard-temp).

Demo
----

A demo service is available at http://avatar.jeproteste.info/.

Images are available at ``http://avatar.jeproteste.info/avatar/<jid>``; example:

.. image:: http://avatar.jeproteste.info/avatar/avatar@jeproteste.info
  :target: http://avatar.jeproteste.info/avatar/avatar@jeproteste.info
  :alt: Simple avatar displayed with the avatar service.

Run
---

::

    ./avatar.py --jid service_jid@example --password service_password --port 8765 --host 127.0.0.1

will start a HTTP server listening on http://127.0.0.1:8765 and make a
XMPP client connect to the account ``service_jid@example.com`` using
``service_password`` as a password.

A ``--avatar_prefix`` can be set, to add a URL prefix (by default ``avatar/``)
for the request (so the URL will be ``/avatar/jid@example.com``).


Deploy
------

Avatars are mostly static, so it is a waste of CPU time and network
resources to fetch them at every request. If is therefore highly
beneficial to put the HTTP server behind nginx, which will act as
a caching proxy.

::

    proxy_cache_path /path/to/your/cache/dir keys_zone=avatar:20m max_size=200m;

    server {
        proxy_cache avatar;
        proy_cache_valid 200 1h;
        proxy_cache_valid any 5m;

        listen 80;
        server_name avatar.example.com;

        location / {
            proxy_pass http://127.0.0.1:8765;
        }
    }

Licence
-------

This code is licenced under the WTFPL.

