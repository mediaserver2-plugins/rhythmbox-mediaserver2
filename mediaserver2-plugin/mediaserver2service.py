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

import dbus
import gobject
from threading import Thread
import Queue
import gtk

class MediaServer2Service(gobject.GObject):

    CONTAINER_TYPE = 'container'
    AUDIO_TYPE = 'audio'
    VIDEO_TYPE = 'video'

    NAME_PROPERTY = 'DisplayName'
    ARTIST_PROPERTY = 'Artist'
    ALBUM_PROPERTY = 'Album'
    DURATION_PROPERTY = 'Duration'
    URLS_PROPERTY = 'URLs'
    TYPE_PROPERTY = 'Type'
    PATH_PROPERTY = 'Path'

    _MEDIA_RETRIEVED_SIGNAL = 'media-retrieved'
    __gsignals__ = {_MEDIA_RETRIEVED_SIGNAL: (gobject.SIGNAL_RUN_LAST,
                                             gobject.TYPE_NONE,
                                             (gobject.TYPE_PYOBJECT,)),
                    }

    _MEDIA_OBJECT_INFO_LIST = [URLS_PROPERTY, ARTIST_PROPERTY,
                               ALBUM_PROPERTY, DURATION_PROPERTY]

    _DBUS_MEDIA_SERVER_1_NAME_PREFIX = 'org.gnome.UPnP.MediaServer2.'
    _DBUS_MEDIA_SERVER_1_PATH_PREFIX = '/org/gnome/UPnP/MediaServer2/'

    _MEDIA_SERVER_1_DBUS_NAME_PREFIX = 'org.gnome.UPnP.MediaServer2.'

    _DBUS_MEDIA_CONTAINER_1_INTERFACE = 'org.gnome.UPnP.MediaContainer2'
    _DBUS_MEDIA_OBJECT_1_INTERFACE = 'org.gnome.UPnP.MediaObject2'
    _DBUS_MEDIA_ITEM_1_INTERFACE = 'org.gnome.UPnP.MediaItem2'

    def __init__(self):
        gobject.GObject.__init__(self)
        self.bus = dbus.SessionBus()
        self.max_chidlren_to_get = 50
        self.media_retriever_thread = Thread(target =
                                             self._media_retriever_worker)
        self.stopped = False
        self.media_retriever_queue = Queue.Queue()
        self.media_retriever_thread.setDaemon(True)
        self.media_retriever_thread.start()

    def _media_retriever_worker(self):
        while True:
            if self.stopped:
                return
            media_obj, tree_iter = self.media_retriever_queue.get()
            if media_obj:
                self._get_media_async(media_obj, tree_iter)

    def get_media(self, media_obj, tree_iter):
        if media_obj:
            self.media_retriever_queue.put((media_obj, tree_iter))
            return
        get_services_thread = Thread(target =
                                     self._get_services_media_objects)
        get_services_thread.start()

    def _get_services_media_objects(self):
        media_obj_list = []
        for service in self._get_available_services():
            service_name = service.split('.')[-1]
            full_service_name = self._DBUS_MEDIA_SERVER_1_NAME_PREFIX + \
                                service_name
            full_service_path = self._DBUS_MEDIA_SERVER_1_PATH_PREFIX + \
                                service_name
            try:
                proxy = self.bus.get_object(full_service_name,
                                            full_service_path)
                name = proxy.Get(self._DBUS_MEDIA_OBJECT_1_INTERFACE,
                                 self.NAME_PROPERTY)
                media_obj = MediaObject(name,
                                        full_service_name,
                                        full_service_path,
                                        self.CONTAINER_TYPE,
                                        None)
            except Exception, exception:
                print exception
            else:
                media_obj_list.append(media_obj)
        gtk.gdk.threads_enter()
        self.emit(self._MEDIA_RETRIEVED_SIGNAL, media_obj_list)
        gtk.gdk.threads_leave()

    def _get_available_services(self):
        services = []
        for name in self.bus.list_names():
            if name.startswith(self._MEDIA_SERVER_1_DBUS_NAME_PREFIX):
                services.append(name)
        return services

    def _get_media_async(self, media_obj, tree_iter):
        if media_obj.obj_type == self.CONTAINER_TYPE:
            self._get_container_children(media_obj, tree_iter)

    def _get_container_children(self, media_obj, tree_iter):
        children = []
        proxy = self._get_media_object_proxy(media_obj)
        try:
            items = proxy.ListChildren(0, self.max_chidlren_to_get,
                                       [self.PATH_PROPERTY,
                                        self.TYPE_PROPERTY,
                                        self.NAME_PROPERTY],
                                       dbus_interface =
                                       self._DBUS_MEDIA_CONTAINER_1_INTERFACE)
        except Exception, exception:
            print exception
            return
        for item in items:
            child_media_obj = MediaObject(item[self.NAME_PROPERTY],
                                          media_obj.dbus_name,
                                          item[self.PATH_PROPERTY],
                                          item[self.TYPE_PROPERTY],
                                          tree_iter)
            try:
                if child_media_obj.obj_type != self.CONTAINER_TYPE:
                    self._get_info_for_object(child_media_obj,
                                              self._MEDIA_OBJECT_INFO_LIST)
            except Exception, exception:
                print exception
            else:
                children.append(child_media_obj)
        gtk.gdk.threads_enter()
        self.emit(self._MEDIA_RETRIEVED_SIGNAL, children)
        gtk.gdk.threads_leave()

    def _get_info_for_object(self, media_obj, info_list):
        proxy = self._get_media_object_proxy(media_obj)
        info_gathered = proxy.GetAll(self._DBUS_MEDIA_ITEM_1_INTERFACE)
        for info in info_list:
            media_obj.properties[info] = info_gathered.get(info)

    def _get_media_object_proxy(self, media_obj):
        return self.bus.get_object(media_obj.dbus_name,
                                   media_obj.dbus_path)

class MediaObject(object):

    def __init__(self, name, dbus_name, dbus_path, obj_type, parent_iter):
        self.name = name
        self.dbus_name = dbus_name
        self.dbus_path = dbus_path
        self.obj_type = obj_type
        self.parent_iter = parent_iter
        self.properties = {}
