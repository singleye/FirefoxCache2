import hashlib
import struct
import glob
import os


class Cache2Index(object):
    def __init__(self, filepath):
        self.raw_data = None
        with open(filepath, 'rb') as fd:
            self.raw_data = fd.read()

        self.version = None
        self.last_written = None
        self.dirty = None

        self.entries = []
        self._load()

    def _parse_entry(self, data):
        frequency, \
        expire, \
        app, \
        last = struct.unpack('>IIII', data)
        flags = last >> 24
        size = last & 0x00FFFFFF

        return {'frequency':frequency,
                'expire':expire,
                'app':app,
                'flags':flags,
                'size':size}

    def _load(self):
        self.version, \
        self.last_written, \
        self.dirty = struct.unpack('>III', self.raw_data[:12])

        offset = 12

        hash_size = 20
        frequency_size = 4
        expire_size = 4
        app_size = 4
        flags_size = 1
        file_size = 3
        entry_size = hash_size + frequency_size + expire_size + \
            app_size + flags_size + file_size

        size = len(self.raw_data)
        while offset + entry_size < size:
            hash = self.raw_data[offset:offset+hash_size]
            entry_metadata = self.raw_data[offset+hash_size:offset+entry_size]
            entry = self._parse_entry(entry_metadata)
            entry['hash'] = hash.hex()
            self.entries.append(entry)
            offset += entry_size


class Cache2Entry(object):
    def __init__(self, filepath):
        self.raw_data = None
        with open(filepath, 'rb') as fd:
            self.raw_data = fd.read()

        self.data = None
        self.size = 0

        # metadata
        self.version = None
        self.fetch_count = 0
        self.last_fetch = None
        self.frequency = 0
        self.expire = None
        self.key = None
        self.key_len = 0
        self.url = ''
        self.entry_name = ''

        self._parse_metadata()

    def _parse_metadata(self):
        self.size = struct.unpack('>I', self.raw_data[-4:])[0]
        self.data = self.raw_data[:self.size]
        chunk_size = 1024*256
        chunks = (self.size + chunk_size - 1)//chunk_size
        skip_bytes = 4 + chunks*2

        metadata_size = 32
        metadata_start = self.size + skip_bytes

        metadata = self.raw_data[metadata_start:metadata_start+metadata_size]

        self.version, \
        self.fetch_count, \
        self.last_fetch, \
        self.last_modify, \
        self.frequency, \
        self.expire, \
        self.key_len, \
        flags = struct.unpack('>IIIIIIII', metadata)
        self.flags = flags if self.version >= 2 else 0

        self.key = self.raw_data[metadata_start+metadata_size:\
                                 metadata_start+metadata_size+self.key_len]
        self.url = self.key[1:].decode('utf-8')

        # may be used to verify the entry
        self.entry_name = hashlib.sha1(self.key).hexdigest().upper()


    def __repr__(self):
        return 'Ver[%d], fetched[%d], key[%s]' % (self.version, \
                                                  self.fetch_count, \
                                                  self.key)

    def extract(self, savepath):
        with open(savepath, 'wb') as fd:
            fd.write(self.data)


class Cache2(object):
    def __init__(self, profile_dir):
        self.profile_dir = os.path.abspath(os.path.expanduser(profile_dir))
        self.cache2_dir = self.profile_dir + '/cache2'
        self.index_file = self.cache2_dir + '/index'
        self.entries_dir = self.cache2_dir + '/entries'
        self.entries = []

        self.index = Cache2Index(self.index_file)

        self._load()

    def _load(self):
        files = glob.glob('%s/*' % self.entries_dir)
        for f in files:
            self.entries.append(Cache2Entry(f))
