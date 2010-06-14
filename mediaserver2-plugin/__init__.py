###########################################################################
#    MediaServer2 Plugin for Rhythmbox
#    Copyright (C) 2010 Igalia, S.L.
#        * Author: Joaquim Rocha <jrocha@igalia.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###########################################################################

import rb
from mediaserver2source import MediaServer2Source
import gobject

class MediaServer2(rb.Plugin):

    def __init__(self):
        rb.Plugin.__init__(self)

    def activate(self, shell):
        self.shell = shell
        self.db = self.shell.props.db
        self.entry_type = self.db.entry_register_type('MediaServer2EntryType')
        self.source = gobject.new (MediaServer2Source,
                                   shell=self.shell,
                                   name="MediaServer2",
                                   entry_type=self.entry_type)
        self.shell.register_entry_type_for_source(self.source,
                                                  self.entry_type)

        self.shell.append_source(self.source, None)

    def deactivate(self, shell):
        self.db.entry_delete_by_type(self.entry_type)
        self.db.commit()
        del self.shell
        del self.entry_type
        self.source.delete_thyself()
        del self.source
