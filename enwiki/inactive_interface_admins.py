#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script reports inactive interface admins.
"""
# Author : JJMC89
# License: MIT
from itertools import chain

import pywikibot
from dateutil.relativedelta import relativedelta


def get_inactive_users(site=None):
    """
    Get a set of inactive interface admins.

    @param site: site to work on
    @type site: L{pywikibot.Site}

    @rtype: set
    """
    users = set()
    if not site:
        site = pywikibot.Site()
    for user_dict in site.allusers(group='interface-admin'):
        user = User(site, user_dict['name'])
        if not user.is_active:
            users.add(user)
    return users


class User(pywikibot.User):
    """Extended L{pywikibot.User}."""

    def __init__(self, source, title):
        """
        Initializer for a User object.

        All parameters are the same as for L{pywikibot.User}.
        """
        super().__init__(source, title)
        self._is_active = None
        self._last_edit = None
        self._last_event = None
        self._has_cssjs_edit = None

    @property
    def is_active(self):
        """
        True if the user is active, False otherwise.

        A user is active if they have both
         1) a CSS/JS edit in the last 6 months
         2) an edit or log entry in the last 2 months

        @rtype: bool
        """
        if self._is_active is None:
            cutoff = self.site.getcurrenttime() + relativedelta(months=-2)
            if self.has_cssjs_edit is False:
                self._is_active = False
            elif self.last_edit and self.last_edit[2] >= cutoff:
                self._is_active = True
            elif self.last_event and self.last_event.timestamp() >= cutoff:
                self._is_active = True
            else:
                self._is_active = False
        return self._is_active

    @property
    def last_edit(self):
        """
        The user's last edit.

        @rtype: tuple or None
        """
        if self._last_edit is None:
            self._last_edit = super().last_edit
        return self._last_edit

    @property
    def last_event(self):
        """
        The user's last log entry.

        @rtype: L{pywikibot.LogEntry} or None
        """
        if self._last_event is None:
            self._last_event = super().last_event
        return self._last_event

    @property
    def has_cssjs_edit(self):
        """
        True if the user has edited a CSS/JS page in the last 6 months.

        None if the user has not been an interface-admin for 6 months.
        False otherwise.

        @rtype: bool or None
        """
        if self._has_cssjs_edit is None:
            kwa = dict(
                namespaces=(2, 8),
                end=self.site.getcurrenttime() + relativedelta(months=-6),
            )
            for page, _, _, summary in self.contributions(total=None, **kwa):
                if not (
                    page.content_model not in ('css', 'javascript')
                    or page.title().startswith('{}/'.format(self.title()))
                    or 'while renaming the user' in summary
                ):
                    self._has_cssjs_edit = True
                    return self._has_cssjs_edit
            pywikibot.log('{}: No CSS/JS edit'.format(self.username))
            got_group = kwa['end']
            rights_events = sorted(
                chain(
                    self.site.logevents(logtype='rights', page=self),
                    pywikibot.Site('meta', 'meta').logevents(
                        logtype='rights',
                        page='{}@{}'.format(self.title(), self.site.dbName()),
                    ),
                ),
                key=lambda logevent: logevent.timestamp(),
                reverse=True,
            )
            for logevent in rights_events:
                added_groups = set(logevent.newgroups)-set(logevent.oldgroups)
                if 'interface-admin' in added_groups:
                    got_group = logevent.timestamp()
                    break
            if kwa['end'] < got_group:
                pywikibot.log('{}: Not iadmin for 6 mo.'.format(self.username))
                self._has_cssjs_edit = None
            else:
                self._has_cssjs_edit = False
        return self._has_cssjs_edit


def main(*args):
    """
    Process command line arguments and invoke bot.

    @param args: command line arguments
    @type args: list of unicode
    """
    pywikibot.handle_args(args)
    site = pywikibot.Site()
    site.login()
    users = get_inactive_users(site=site)
    if not users:
        return
    heading = 'Inactive interface administrators {}'.format(
        site.getcurrenttime().date()
    )
    text = 'The following interface administrator(s) are inactive:'
    for user in sorted(users):
        text += '\n* {{{{admin|1={}}}}}'.format(user.username)
    text += '\n~~~~'
    pywikibot.Page(
        site, "Wikipedia:Interface administrators' noticeboard"
    ).save(text=text, section='new', summary=heading, botflag=False)


if __name__ == "__main__":
    main()
