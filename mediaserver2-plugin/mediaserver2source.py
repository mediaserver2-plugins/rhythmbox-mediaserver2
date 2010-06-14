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
import dbus
import gobject
import gtk
import rhythmdb
from mediaserver2service import MediaServer2Service

class MediaServer2Source(rb.BrowserSource):

    _TEXT_COLUMN = 0
    _PIXBUF_COLUMN = 1
    _MEDIA_OBJECT_COLUMN = 2

    _MEDIA_OBJECT_TYPE_ICON_MAP = {MediaServer2Service.CONTAINER_TYPE: 'folder',
                                   MediaServer2Service.AUDIO_TYPE: 'media-audio',
                                   MediaServer2Service.VIDEO_TYPE: 'video'}

    def __init__(self):
        self.is_activated = False
        rb.BrowserSource.__init__(self, name="MediaServer2")
        self.bus = dbus.SessionBus()
        self.mediaserver2_service = MediaServer2Service()
        self.mediaserver2_service.connect('media-retrieved', self._media_retrieved_cb)
        self._icons_dict = self._get_icons()

    def do_impl_activate(self):
        if self.is_activated:
            rb.BrowserSource.do_impl_activate(self)
            return
        self.is_activated = True
        self._db = self.props.shell.props.db

        self.tree_model = gtk.TreeStore(str,
                                        gtk.gdk.Pixbuf,
                                        gobject.TYPE_PYOBJECT)
        self.media_folders_view = gtk.TreeView(self.tree_model)
        renderer = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn('Media')
        column.pack_start(renderer, False)
        column.set_attributes(renderer, pixbuf=self._PIXBUF_COLUMN)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_attributes(renderer, text=self._TEXT_COLUMN)
        self.media_folders_view.append_column(column)
        self.media_folders_view.connect('row-activated',
                                        self._tree_row_activated_cb)

        folders_scrolled_window = gtk.ScrolledWindow()
        folders_scrolled_window.add_with_viewport(self.media_folders_view)
        self.pack_start(folders_scrolled_window)
        self.reorder_child(folders_scrolled_window, 0)

        self.show_all()
        self.mediaserver2_service.get_media(None, None)
        rb.BrowserSource.do_impl_activate(self)

    def _tree_row_activated_cb(self, tree_view, path, view_column):
        iter = self.tree_model.get_iter(path)
        media_obj = self.tree_model.get_value(iter,
                                              self._MEDIA_OBJECT_COLUMN)
        if media_obj.obj_type == MediaServer2Service.CONTAINER_TYPE and \
           not self.tree_model.iter_has_child(iter):
            self.mediaserver2_service.get_media(media_obj, iter)
            return
        self._add_to_db(media_obj)

    def _add_to_db(self, media_obj):
        urls = media_obj.properties.get(MediaServer2Service.URLS_PROPERTY)
        if not urls:
            return
        location = urls[0]
        entry = self._db.entry_lookup_by_location(location)
        if entry is None:
            entry = self._db.entry_new(self.props.entry_type, location)
            self._db.set(entry, rhythmdb.PROP_TITLE, media_obj.name)
            artist = media_obj.properties.get(MediaServer2Service.ARTIST_PROPERTY)
            if artist:
                self._db.set(entry, rhythmdb.PROP_ARTIST, artist)
            album = media_obj.properties.get(MediaServer2Service.ALBUM_PROPERTY)
            if album:
                self._db.set(entry, rhythmdb.PROP_ALBUM, album)
            duration = media_obj.properties.get(MediaServer2Service.DURATION_PROPERTY)
            if duration is not None:
                self._db.set(entry, rhythmdb.PROP_DURATION, duration)
            self._db.commit()

    def _media_retrieved_cb(self, mediaserver2_service, media_obj_list):
        for media_obj in media_obj_list:
            parent_iter = media_obj.parent_iter
            icon = self._get_icon_for_media_object(media_obj)
            self.tree_model.insert(parent_iter, 0, [media_obj.name,
                                                    icon,
                                                    media_obj])
            if parent_iter:
                self.media_folders_view.expand_row(self.tree_model.get_path(parent_iter), False)

    def _get_icon_for_media_object(self, media_obj):
        icon_name = self._MEDIA_OBJECT_TYPE_ICON_MAP.get(media_obj.obj_type)
        if not icon_name:
            return None
        return self._icons_dict.get(icon_name)

    def _get_icons(self):
        icons_dict = {}
        icon_theme = gtk.icon_theme_get_default()
        for name in self._MEDIA_OBJECT_TYPE_ICON_MAP.values():
            icons_dict[name] = self._get_icon_from_name(icon_theme,
                                                        name)
        return icons_dict

    def _get_icon_from_name(self, icon_theme, name):
        icon_info = icon_theme.lookup_icon(name, gtk.ICON_SIZE_BUTTON, 0)
        if icon_info:
            return gtk.gdk.pixbuf_new_from_file(icon_info.get_filename())
        return None

    def do_impl_delete_thyself(self):
        self.mediaserver2_service.stopped = True
        rb.BrowserSource.do_impl_delete_thyself(self)

gobject.type_register(MediaServer2Source)
