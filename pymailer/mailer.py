#!/usr/bin/env python
import logging
import sys
import os
import jinja2
import smtplib

from string import Template

from pymailer.config import Config
from pymailer.contacts import Contacts
from pymailer.stitcher import Stitcher
from pymailer.email import Email

_log = logging.getLogger(__name__)

cfg = Config()
template_folder = ""

def generate_email(contact, mail, subject=None):
    # Gather variables for templates
    template_vars = {
        "FROM": cfg.from_mailbox,
        "TO": contact.mailbox,
        "SENDER": cfg.display_name,
        **contact
    }
    mail_template = jinja2.Template(mail)
    mail = mail_template.render(template_vars)
    # Stitch mail into plain text and html
    stitcher = Stitcher(mail, template_folder)
    mail_plain = stitcher.stitch("plain")
    mail_html = stitcher.stitch("html", suppress_subject=False)
    if subject is None:
        subject = stitcher.get_subject()
    template_vars["SUBJECT"] = subject
    # Create templates
    plain_template = Template(mail_plain)
    html_template = Template(mail_html)
    # Generate individual e-mails
    plain = plain_template.safe_substitute(template_vars)
    html = html_template.safe_substitute(template_vars)
    # Save plain and html templates (for debugging)
    if cfg.dbg_folder is not None:
        basename = os.path.join(cfg.dbg_folder, contact.email)
        if not os.path.isdir(cfg.dbg_folder):
            os.makedirs(cfg.dbg_folder)
        with open(f"{basename}.txt", "w+") as f:
            f.write(plain)
        with open(f"{basename}.html", "w+") as f:
            f.write(html)
    try:
        email = Email(cfg.from_mailbox, contact.mailbox, subject, plain)
        email.set_html_content(html, os.path.join(template_folder, "html"))
    except Email.Error as error:
        _log.debug(error)
        return None
    # Save generated e-mail (for debugging)
    if cfg.dbg_folder is not None:
        with open(os.path.join(cfg.dbg_folder, contact.email), "w+") as f:
            f.write(email.get_data())
    return email


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
    cfg.load("./pymailer.cfg")
    # Set log level according to config file
    logging.getLogger().setLevel(cfg.log_level)
    # Open mail file
    with open(sys.argv[1], "r") as f:
        mail_fname = f.name
        mail = f.read()
        tmpl_dir = os.path.dirname(f.name)
    _log.debug(f"mail: {mail_fname}, templates: {tmpl_dir}")
    # Load contacts from CSV file
    contacts = Contacts()
    contacts.load(sys.argv[2])
    # Generate e-mail for each contact
    emails = []
    for contact in contacts:
        email = generate_email(contact, mail)
        if email is None:
            _log.error(f"Unable to generate e-mail for '{contact}'!")
            continue
        emails.append(email)
    # Connect and login to SMTP server
    try:
        smtp = smtplib.SMTP_SSL(cfg.host, cfg.port, context=cfg.ssl_context)
        if cfg.password is not None:
            smtp.login(cfg.email, cfg.password)
    except smtplib.SMTPAuthenticationError:
        _log.error(f"Unable to login '{cfg.email}' at {cfg.host}!")
        exit(-1)
    except Exception as error:
        _log.debug(error)
        _log.error(f"Unable to connect to {cfg.host}!")
        exit(-1)
    # Send all e-mails
    for email in emails:
        email_ok = False
        crit_error = None
        sys.stdout.write(f"{email.to_mailbox} -> ")
        # Send email
        try:
            if not cfg.dry_run:
                email_ok = email.send(smtp)
            else:
                email_ok = True
        except smtplib.SMTPSenderRefused as error:
            crit_error = f"Sender '{cfg.from_mailbox}' got refused!"
        except Exception as error:
            _log.debug(error)
        result = "OK" if email_ok else "ERR"
        sys.stdout.write((f"({result})" if cfg.dry_run else result) + "\n")
        # Stop sending emails if a critical error occured
        if crit_error is not None:
            _log.error(crit_error)
            break
    smtp.close()

if __name__ == "__main__":
    main()