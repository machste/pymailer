#!/usr/bin/env python
import logging
import sys
import os
import smtplib

from string import Template

from pymailer.config import Config
from pymailer.contacts import Contacts
from pymailer.stitcher import Stitcher
from pymailer.email import Email

_log = logging.getLogger(__name__)

def main():
    # Check arguments
    if len(sys.argv) != 3:
        prog_name = os.path.split(sys.argv[0])[1]
        sys.stderr.write(f"usage: {prog_name} <mail> <contacts>\n")
        exit(-1)
    # Setup Logging
    logging.getLogger().setLevel(logging.ERROR)
    logging.info("Mail Generator")
    # Load config
    cfg = Config()
    cfg.load("./pymailer.cfg")
    # Set log level according to config file
    logging.getLogger().setLevel(cfg.log_level)
    # Open mail file
    with open(sys.argv[1], "r") as mail_file:
        mail_filename = mail_file.name
        tmpl_dir = os.path.dirname(mail_file.name)
        mail = mail_file.read()
    # Load contacts from CSV file
    contacts = Contacts()
    contacts.load(sys.argv[2])
    # Stitch mail into plain text and html
    _log.debug(f"mail: {mail_filename}, templates: {tmpl_dir}")
    stitcher = Stitcher(mail, tmpl_dir)
    mail_plain = stitcher.stitch("plain")
    mail_html = stitcher.stitch("html", suppress_subject=False)
    # Save plain and html templates (for debugging)
    if cfg.dbg_folder is not None:
        if not os.path.isdir(cfg.dbg_folder):
            os.makedirs(cfg.dbg_folder)
        with open(os.path.join(cfg.dbg_folder, "template.txt"), "w+") as plain:
            plain.write(mail_plain)
        with open(os.path.join(cfg.dbg_folder, "template.html"), "w+") as html:
            html.write(mail_html)
    # Gather global variables for templates
    email_vars = {}
    email_vars["FROM"] = cfg.from_mailbox
    email_vars["SUBJECT"] = stitcher.get_subject()
    email_vars["SENDER"] = cfg.display_name
    # Create templates
    plain_template = Template(mail_plain)
    html_template = Template(mail_html)
    # Generate individual e-mails
    emails = []
    for c in contacts:
        mapping = {**email_vars, **c}
        subject = mapping["SUBJECT"]
        plain = plain_template.safe_substitute(mapping)
        html_data = html_template.safe_substitute(mapping)
        html = Email.Html(html_data, os.path.join(tmpl_dir, "html"))
        try:
            email = Email(cfg.from_mailbox, c.mailbox, subject, plain, html)
        except Email.Error as err:
            _log.error(f"Unable to generate e-mail for '{c}'!")
        # Save generated e-mail (for debugging)
        if cfg.dbg_folder is not None:
            with open(os.path.join(cfg.dbg_folder, c.email), "w+") as f:
                f.write(email.get_data())
        emails.append(email)
    # Connect and login to SMTP server
    try:
        smtp = smtplib.SMTP_SSL(cfg.host, cfg.port, context=cfg.ssl_context)
    except:
        _log.error(f"Unable to connect to {cfg.host}!")
        exit(-1)
    smtp.login(cfg.email, cfg.password)
    # Send all e-mails
    for email in emails:
        email_ok = True
        sys.stdout.write(f"{email.to_mailbox} -> ")
        if cfg.dry_run:
            sys.stdout.write("(")
        else:
            # Send email
            try:
                email.send(smtp)
            except Exception as err:
                _log.debug(err)
                email_ok = False
        sys.stdout.write("OK" if email_ok else "ERR")
        if cfg.dry_run:
            sys.stdout.write(")")
        sys.stdout.write("\n")
    smtp.close()

if __name__ == "__main__":
    main()