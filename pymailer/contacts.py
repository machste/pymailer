import logging
import re

from csv import DictReader

_log = logging.getLogger(__name__)

EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'


class Contact(dict):

    def _get_field(self, key):
        if key in self and len(self[key]):
            return self[key]
        return None

    @property
    def email(self):
        return self._get_field("EMAIL")

    @property
    def name(self):
        return self._get_field("NAME")

    @property
    def firstname(self):
        return self._get_field("FIRSTNAME")

    @property
    def display_name(self):
        dname  = "" if self.firstname is None else self.firstname
        dname += "" if self.name is None else f" {self.name}"
        return dname

    @property
    def mailbox(self):
        if len(self.display_name) == 0:
            return self.email
        return f"{self.display_name} <{self.email}>"

    def __str__(self):
        return self.mailbox

    @staticmethod
    def parse_contatct(data):
        c = Contact()
        for k, v in data.items():
            c[k] = v.strip()
        if c.email is None:
            _log.warn("No e-mail found in contact data!")
            return None
        if not re.fullmatch(EMAIL_REGEX, c.email):
            _log.warn(f"The e-mail address '{c.email}' is not valid!")
            return None
        return c


class Contacts(list):

    def load(self, filename):
        with open(filename, newline="") as contacts_file:
            rows = DictReader(contacts_file)
            # Validate contact information
            for row in rows:
                contact = Contact.parse_contatct(row)
                if contact is None:
                    continue
                _log.debug(f"Found: {contact}")
                self.append(contact)
