"""Map variable names and string names to unique integers.

Used in the Logic Simulator project. Most of the modules in the project
use this module either directly or indirectly.

Classes
-------
Names - maps variable names and string names to unique integers.
"""

import uuid


class Names:
    """Map variable names and string names to unique integers."""

    def __init__(self):
        """Initialise names list, dictionary and error code count."""
        self.error_code_count = 0
        self.names_list = []   # index is the ID, value is the string
        self.names_dict = {}   # key is the string, value is the ID

    def unique_error_codes(self, num_error_codes):
        """Return a list of unique integer error codes."""
        if not isinstance(num_error_codes, int):
            raise TypeError("Expected num_error_codes to be an integer.")
        self.error_code_count += num_error_codes
        return range(self.error_code_count - num_error_codes,
                     self.error_code_count)

    def query(self, name_string):
        """Return the ID of name_string, or None if not present."""
        if not isinstance(name_string, str):
            raise TypeError("Expected a string.")
        return self.names_dict.get(name_string, None)

    def lookup(self, name_string_or_list):
        """Return name ID(s) for the given string or list of strings.

        If a single string is given, returns a single ID.
        If a list is given, returns a list of IDs.
        Adds any new names automatically.
        """
        if isinstance(name_string_or_list, str):
            return self._lookup_single(name_string_or_list)
        elif isinstance(name_string_or_list, list):
            return [self._lookup_single(s) for s in name_string_or_list]
        else:
            raise TypeError("Expected a string or list of strings.")

    def _lookup_single(self, name_string):
        """Look up or add a single name string and return its ID."""
        if not isinstance(name_string, str):
            raise TypeError("Name must be a string.")
        if name_string not in self.names_dict:
            name_id = len(self.names_list)
            self.names_list.append(name_string)
            self.names_dict[name_string] = name_id
        return self.names_dict[name_string]

    def get_name_string(self, name_id):
        """Return the name string for name_id, or None if invalid."""
        if not isinstance(name_id, int):
            raise TypeError("Name ID must be an integer.")
        if 0 <= name_id < len(self.names_list):
            return self.names_list[name_id]
        return None
