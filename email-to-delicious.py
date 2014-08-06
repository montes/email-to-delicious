#!/usr/bin/python
#
#   Copyright (C) 2014 Javier Montes @montesjmm montesjmm.com
#   License: http://opensource.org/licenses/MIT
#
#   What does this script do?
#
#   All of your emails with a subject like:
#   "d>tag_name"
#   and with an url in the body, will be saved to delicious.com with that tag
#
#   In other words, you can save links to delicious simply sending emails
#   to yourself!!!! ;)
#
#   More info at: http://montesjmm.es/2014/08/05/conectar-gmail-imap-python/
#

import imaplib
import email
import re
import urllib
import urllib2
import sys
from unicodedata import normalize
from email.header import decode_header
from email.header import make_header


def connect_to_gmail(username, password):
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.login(username, password)
    imap.select("inbox")

    return imap


# this function from: http://i2bskn.hateblo.jp/entry/20120322/1332421932
def get_subject(email):
    h = decode_header(email.get('subject'))
    return unicode(make_header(h)).encode('utf-8')


# this function from: https://gist.github.com/miohtama/5389146
def get_decoded_email_body(message_body):
    """ Decode email body.
    Detect character set if the header is not set.
    We try to get text/plain, but if there is not one then fallback to text/html.
    :param message_body: Raw 7-bit message body input e.g. from imaplib. Double encoded in quoted-printable and latin-1
    :return: Message body as unicode string
    """

    msg = email.message_from_string(message_body)

    text = ""
    if msg.is_multipart():
        html = None
        for part in msg.get_payload():

            #print "%s, %s" % (part.get_content_type(), part.get_content_charset())

            if part.get_content_charset() is None:
                # We cannot know the character set, so return decoded "something"
                text = part.get_payload(decode=True)
                continue

            charset = part.get_content_charset()

            if part.get_content_type() == 'text/plain':
                text = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

            if part.get_content_type() == 'text/html':
                html = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

        if text is not None:
            return text.strip()
        else:
            return html.strip()
    else:
        text = unicode(msg.get_payload(decode=True), msg.get_content_charset(), 'ignore').encode('utf8', 'replace')
        return text.strip()


def save_to_delicious(save_url, username, password, tag):
    req = urllib2.Request(save_url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36')
    html = urllib2.urlopen(req)

    if (html):
        html = html.read()
    if (html):
        match_title = re.match(r'.*?<title>(.*?)</title>', html, re.I | re.M | re.DOTALL)
        title = match_title.group(1)
        title = title.decode('utf-8')
        title = normalize('NFD', unicode(title)).encode('ascii', 'ignore')
        delicious_url = "https://api.del.icio.us/v1/posts/add?&shared=no&url=" + urllib.quote_plus(save_url) + "&tags=" + tag + "&description=" + urllib.quote_plus(title.encode('ascii', 'ignore'))
    else:
        delicious_url = "https://api.del.icio.us/v1/posts/add?&shared=no&url=" + urllib.quote_plus(save_url) + "&tags=" + tag

    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, delicious_url, username, password)
    urllib2.install_opener(urllib2.build_opener(urllib2.HTTPBasicAuthHandler(passman)))

    req = urllib2.Request(delicious_url)
    urllib2.urlopen(req)


def process_command_line_parameters():
    if (len(sys.argv) < 5):
        print "Use: ./email-to-delicious.py gmail_username gmail_password delicious_username delicious_password"
        sys.exit()

    parameters = {}

    if (sys.argv[1]):
        parameters['gmail_username'] = sys.argv[1]

    if (sys.argv[2]):
        parameters['gmail_password'] = sys.argv[2]

    if (sys.argv[3]):
        parameters['delicious_username'] = sys.argv[3]

    if (sys.argv[4]):
        parameters['delicious_password'] = sys.argv[4]

    return parameters


def main():
    parameters = process_command_line_parameters()

    imap = connect_to_gmail(parameters['gmail_username'], parameters['gmail_password'])
    result, mails_data = imap.search(None, "(UNSEEN)")

    mails_ids = mails_data[0]
    mails_id_list = mails_ids.split()

    mail_count = 40
    for i in reversed(mails_id_list):

        result, mail_data = imap.fetch(i, "(RFC822)")
        raw_email = mail_data[0][1]
        this_email = email.message_from_string(raw_email)

        subject = get_subject(this_email)
        match_subject = re.match(r'd>([^<]+)', subject, re.I | re.S)
        print subject
        if (match_subject):
            tag = match_subject.group(1)
            body = get_decoded_email_body(raw_email) + " "

            url = re.match(r'.*?(https?://[\w\d/\.#_\-=\&\?\n\r]+)', body, re.I | re.M | re.DOTALL)

            if (url):
                url = ''.join(url.group(1).split())
                print 'Match found! >' + tag + '>' + url + '<'
                save_to_delicious(url, parameters['delicious_username'], parameters['delicious_password'], tag)

                imap.copy(i, '[Gmail]/Trash')
                imap.store(i, '+FLAGS', r'(\Deleted)')
                imap.expunge()

        imap.store(i, '-FLAGS', r'(\Seen)')

        mail_count -= 1
        if mail_count < 1:
            break


if __name__ == '__main__':
    main()
