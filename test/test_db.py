# This file is part of beets.
# Copyright 2010, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

"""Tests for non-query database functions of Item.
"""

import unittest
import sys
import os
import sqlite3
import ntpath
import posixpath
sys.path.append('..')
import beets.library

def lib(): return beets.library.Library('rsrc' + os.sep + 'test.blb')
def boracay(l): return beets.library.Item(l.conn.execute('select * from items '
    'where id=3').fetchone())
def item(): return beets.library.Item({
    'title':            u'the title',
    'artist':           u'the artist',
    'albumartist':      u'the album artist',
    'album':            u'the album',
    'genre':            u'the genre',
    'composer':         u'the composer',
    'grouping':         u'the grouping',
    'year':             1,
    'month':            2,
    'day':              3,
    'track':            4,
    'tracktotal':       5,
    'disc':             6,
    'disctotal':        7,
    'lyrics':           u'the lyrics',
    'comments':         u'the comments',
    'bpm':              8,
    'comp':             True,
    'path':             'somepath',
    'length':           60.0,
    'bitrate':          128000,
    'format':           'FLAC',
    'mb_trackid':       'someID-1',
    'mb_albumid':       'someID-2',
    'mb_artistid':      'someID-3',
    'mb_albumartistid': 'someID-4',
    'album_id':         None,
})
np = beets.library._normpath

class LoadTest(unittest.TestCase):
    def setUp(self):
        self.lib = lib()
        self.i = boracay(self.lib)
    def tearDown(self):
        self.lib.conn.close()
    
    def test_load_restores_data_from_db(self):
        original_title = self.i.title
        self.i.title = 'something'
        self.lib.load(self.i)
        self.assertEqual(original_title, self.i.title)
    
    def test_load_clears_dirty_flags(self):
        self.i.artist = 'something'
        self.lib.load(self.i)
        self.assertTrue(not self.i.dirty['artist'])

class StoreTest(unittest.TestCase):
    def setUp(self):
        self.lib = lib()
        self.i = boracay(self.lib)
    def tearDown(self):
        self.lib.conn.close()
    
    def test_store_changes_database_value(self):
        self.i.year = 1987
        self.lib.store(self.i)
        new_year = self.lib.conn.execute('select year from items where '
            'title="Boracay"').fetchone()['year']
        self.assertEqual(new_year, 1987)
    
    def test_store_only_writes_dirty_fields(self):
        original_genre = self.i.genre
        self.i.record['genre'] = 'beatboxing' # change value w/o dirtying
        self.lib.store(self.i)
        new_genre = self.lib.conn.execute('select genre from items where '
            'title="Boracay"').fetchone()['genre']
        self.assertEqual(new_genre, original_genre)
    
    def test_store_clears_dirty_flags(self):
        self.i.composer = 'tvp'
        self.lib.store(self.i)
        self.assertTrue(not self.i.dirty['composer'])

class AddTest(unittest.TestCase):
    def setUp(self):
        self.lib = beets.library.Library(':memory:')
        self.i = item()
    def tearDown(self):
        self.lib.conn.close()
    
    def test_item_add_inserts_row(self):
        self.lib.add(self.i)
        new_grouping = self.lib.conn.execute('select grouping from items '
            'where composer="the composer"').fetchone()['grouping']
        self.assertEqual(new_grouping, self.i.grouping)
    
    def test_library_add_path_inserts_row(self):
        i = beets.library.Item.from_path(os.path.join('rsrc', 'full.mp3'))
        self.lib.add(i)
        new_grouping = self.lib.conn.execute('select grouping from items '
            'where composer="the composer"').fetchone()['grouping']
        self.assertEqual(new_grouping, self.i.grouping)
        
class RemoveTest(unittest.TestCase):
    def setUp(self):
        self.lib = lib()
        self.i = boracay(self.lib)
    def tearDown(self):
        self.lib.conn.close()
    
    def test_remove_deletes_from_db(self):
        self.lib.remove(self.i)
        c = self.lib.conn.execute('select * from items where id=3')
        self.assertEqual(c.fetchone(), None)

class GetSetTest(unittest.TestCase):
    def setUp(self):
        self.i = item()
    
    def test_set_changes_value(self):
        self.i.bpm = 4915
        self.assertEqual(self.i.bpm, 4915)
    
    def test_set_sets_dirty_flag(self):
        self.i.comp = not self.i.comp
        self.assertTrue(self.i.dirty['comp'])
    
    def test_set_does_not_dirty_if_value_unchanged(self):
        self.i.title = self.i.title
        self.assertTrue(not self.i.dirty['title'])
    
    def test_invalid_field_raises_attributeerror(self):
        self.assertRaises(AttributeError, getattr, self.i, 'xyzzy')

class DestinationTest(unittest.TestCase):
    def setUp(self):
        self.lib = beets.library.Library(':memory:')
        self.i = item()
    def tearDown(self):
        self.lib.conn.close()
    
    def test_directory_works_with_trailing_slash(self):
        self.lib.directory = 'one/'
        self.lib.path_formats = {'default': 'two'}
        self.assertEqual(self.lib.destination(self.i), np('one/two'))
    
    def test_directory_works_without_trailing_slash(self):
        self.lib.directory = 'one'
        self.lib.path_formats = {'default': 'two'}
        self.assertEqual(self.lib.destination(self.i), np('one/two'))
    
    def test_destination_substitues_metadata_values(self):
        self.lib.directory = 'base'
        self.lib.path_formats = {'default': '$album/$artist $title'}
        self.i.title = 'three'
        self.i.artist = 'two'
        self.i.album = 'one'
        self.assertEqual(self.lib.destination(self.i),
                         np('base/one/two three'))
    
    def test_destination_preserves_extension(self):
        self.lib.directory = 'base'
        self.lib.path_formats = {'default': '$title'}
        self.i.path = 'hey.audioFormat'
        self.assertEqual(self.lib.destination(self.i),
                         np('base/the title.audioFormat'))
    
    def test_destination_pads_some_indices(self):
        self.lib.directory = 'base'
        self.lib.path_formats = {'default': '$track $tracktotal ' \
            '$disc $disctotal $bpm $year'}
        self.i.track = 1
        self.i.tracktotal = 2
        self.i.disc = 3
        self.i.disctotal = 4
        self.i.bpm = 5
        self.i.year = 6
        self.assertEqual(self.lib.destination(self.i),
                         np('base/01 02 03 04 5 6'))
    
    def test_destination_escapes_slashes(self):
        self.i.album = 'one/two'
        dest = self.lib.destination(self.i)
        self.assertTrue('one' in dest)
        self.assertTrue('two' in dest)
        self.assertFalse('one/two' in dest)
    
    def test_destination_escapes_leading_dot(self):
        self.i.album = '.something'
        dest = self.lib.destination(self.i)
        self.assertTrue('something' in dest)
        self.assertFalse('/.' in dest)
    
    def test_destination_preserves_legitimate_slashes(self):
        self.i.artist = 'one'
        self.i.album = 'two'
        dest = self.lib.destination(self.i)
        self.assertTrue(os.path.join('one', 'two') in dest)
    
    def test_destination_long_names_truncated(self):
        self.i.title = 'X'*300
        self.i.artist = 'Y'*300
        for c in self.lib.destination(self.i).split(os.path.sep):
            self.assertTrue(len(c) <= 255)
    
    def test_destination_long_names_keep_extension(self):
        self.i.title = 'X'*300
        self.i.path = 'something.extn'
        dest = self.lib.destination(self.i)
        self.assertEqual(dest[-5:], '.extn')
    
    def test_distination_windows_removes_both_separators(self):
        self.i.title = 'one \\ two / three.mp3'
        p = self.lib.destination(self.i, ntpath)
        self.assertFalse('one \\ two' in p)
        self.assertFalse('one / two' in p)
        self.assertFalse('two \\ three' in p)
        self.assertFalse('two / three' in p)
    
    def test_sanitize_unix_replaces_leading_dot(self):
        p = beets.library._sanitize_path('one/.two/three', posixpath)
        self.assertFalse('.' in p)
    
    def test_sanitize_windows_replaces_trailing_dot(self):
        p = beets.library._sanitize_path('one/two./three', ntpath)
        self.assertFalse('.' in p)
    
    def test_sanitize_windows_replaces_illegal_chars(self):
        p = beets.library._sanitize_path(':*?"<>|', ntpath)
        self.assertFalse(':' in p)
        self.assertFalse('*' in p)
        self.assertFalse('?' in p)
        self.assertFalse('"' in p)
        self.assertFalse('<' in p)
        self.assertFalse('>' in p)
        self.assertFalse('|' in p)
    
    def test_sanitize_replaces_colon_with_dash(self):
        p = beets.library._sanitize_path(u':', posixpath)
        self.assertEqual(p, u'-')
    
    def test_path_with_format(self):
        self.lib.path_formats = {'default': '$artist/$album ($format)'}
        p = self.lib.destination(self.i)
        self.assert_('(FLAC)' in p)

    def test_heterogeneous_album_gets_single_directory(self):
        i1, i2 = item(), item()
        self.lib.add_album([i1, i2])
        i1.year, i2.year = 2009, 2010
        self.lib.path_formats = {'default': '$album ($year)/$track $title'}
        dest1, dest2 = self.lib.destination(i1), self.lib.destination(i2)
        self.assertEqual(os.path.dirname(dest1), os.path.dirname(dest2))
    
    def test_comp_path(self):
        self.i.comp = True
        self.lib.directory = 'one'
        self.lib.path_formats = {'default': 'two',
                                 'comp': 'three'}
        self.assertEqual(self.lib.destination(self.i), np('one/three'))

    def test_syspath_windows_format(self):
        path = ntpath.join('a', 'b', 'c')
        outpath = beets.library._syspath(path, ntpath)
        self.assertTrue(isinstance(outpath, unicode))
        self.assertTrue(outpath.startswith(u'\\\\?\\'))

    def test_syspath_posix_unchanged(self):
        path = posixpath.join('a', 'b', 'c')
        outpath = beets.library._syspath(path, posixpath)
        self.assertEqual(path, outpath)

    def test_sanitize_windows_replaces_trailing_space(self):
        p = beets.library._sanitize_path('one/two /three', ntpath)
        self.assertFalse(' ' in p)


class MigrationTest(unittest.TestCase):
    """Tests the ability to change the database schema between
    versions.
    """
    def setUp(self):
        # Three different "schema versions".
        self.older_fields = [('field_one', 'int')]
        self.old_fields = self.older_fields + [('field_two', 'int')]
        self.new_fields = self.old_fields + [('field_three', 'int')]
        self.newer_fields = self.new_fields + [('field_four', 'int')]
        
        # Set up a library with old_fields.
        self.libfile = os.path.join('rsrc', 'templib.blb')
        old_lib = beets.library.Library(self.libfile,
                                        item_fields=self.old_fields)
        # Add an item to the old library.
        old_lib.conn.execute(
            'insert into items (field_one, field_two) values (4, 2)'
        )
        old_lib.save()
        del old_lib
        
    def tearDown(self):
        os.unlink(self.libfile)
    
    def test_open_with_same_fields_leaves_untouched(self):
        new_lib = beets.library.Library(self.libfile,
                                        item_fields=self.old_fields)
        c = new_lib.conn.cursor()
        c.execute("select * from items")
        row = c.fetchone()
        self.assertEqual(len(row), len(self.old_fields))
    
    def test_open_with_new_field_adds_column(self):
        new_lib = beets.library.Library(self.libfile,
                                        item_fields=self.new_fields)
        c = new_lib.conn.cursor()
        c.execute("select * from items")
        row = c.fetchone()
        self.assertEqual(len(row), len(self.new_fields))
    
    def test_open_with_fewer_fields_leaves_untouched(self):
        new_lib = beets.library.Library(self.libfile,
                                        item_fields=self.older_fields)
        c = new_lib.conn.cursor()
        c.execute("select * from items")
        row = c.fetchone()
        self.assertEqual(len(row), len(self.old_fields))
    
    def test_open_with_multiple_new_fields(self):
        new_lib = beets.library.Library(self.libfile,
                                        item_fields=self.newer_fields)
        c = new_lib.conn.cursor()
        c.execute("select * from items")
        row = c.fetchone()
        self.assertEqual(len(row), len(self.newer_fields))

    def test_open_old_db_adds_album_table(self):
        conn = sqlite3.connect(self.libfile)
        conn.execute('drop table albums')
        conn.close()

        conn = sqlite3.connect(self.libfile)
        self.assertRaises(sqlite3.OperationalError, conn.execute,
                         'select * from albums')
        conn.close()

        new_lib = beets.library.Library(self.libfile,
                                        item_fields=self.newer_fields)
        try:
            new_lib.conn.execute("select * from albums")
        except sqlite3.OperationalError:
            self.fail("select failed")

class AlbumInfoTest(unittest.TestCase):
    def setUp(self):
        self.lib = beets.library.Library(':memory:')
        self.i = item()
        self.lib.add_album((self.i,))

    def test_albuminfo_reflects_metadata(self):
        ai = self.lib.get_album(self.i)
        self.assertEqual(ai.mb_albumartistid, self.i.mb_albumartistid)
        self.assertEqual(ai.albumartist, self.i.albumartist)
        self.assertEqual(ai.album, self.i.album)
        self.assertEqual(ai.year, self.i.year)

    def test_albuminfo_stores_art(self):
        ai = self.lib.get_album(self.i)
        ai.artpath = '/my/great/art'
        new_ai = self.lib.get_album(self.i)
        self.assertEqual(new_ai.artpath, '/my/great/art')
    
    def test_albuminfo_for_two_items_doesnt_duplicate_row(self):
        i2 = item()
        self.lib.add(i2)
        self.lib.get_album(self.i)
        self.lib.get_album(i2)
        
        c = self.lib.conn.cursor()
        c.execute('select * from albums where album=?', (self.i.album,))
        # Cursor should only return one row.
        self.assertNotEqual(c.fetchone(), None)
        self.assertEqual(c.fetchone(), None)

    def test_individual_tracks_have_no_albuminfo(self):
        i2 = item()
        i2.album = 'aTotallyDifferentAlbum'
        self.lib.add(i2)
        ai = self.lib.get_album(i2)
        self.assertEqual(ai, None)

    def test_get_album_by_id(self):
        ai = self.lib.get_album(self.i)
        ai = self.lib.get_album(self.i.id)
        self.assertNotEqual(ai, None)

    def test_album_items_consistent(self):
        ai = self.lib.get_album(self.i)
        for item in ai.items():
            if item.id == self.i.id:
                break
        else:
            self.fail("item not found")

    def test_albuminfo_changes_affect_items(self):
        ai = self.lib.get_album(self.i)
        ai.album = 'myNewAlbum'
        i = self.lib.items().next()
        self.assertEqual(i.album, 'myNewAlbum')

    def test_albuminfo_remove_removes_items(self):
        item_id = self.i.id
        self.lib.get_album(self.i).remove()
        c = self.lib.conn.execute('SELECT id FROM items WHERE id=?', (item_id,))
        self.assertEqual(c.fetchone(), None)

class ArtDestinationTest(unittest.TestCase):
    def setUp(self):
        self.lib = beets.library.Library(':memory:')
        self.i = item()
        self.i.path = self.lib.destination(self.i)
        self.lib.art_filename = 'artimage'
        self.ai = self.lib.add_album((self.i,))
        
    def test_art_filename_respects_setting(self):
        art = self.ai.art_destination('something.jpg')
        self.assert_('%sartimage.jpg' % os.path.sep in art)
        
    def test_art_path_in_item_dir(self):
        art = self.ai.art_destination('something.jpg')
        track = self.lib.destination(self.i)
        self.assertEqual(os.path.dirname(art), os.path.dirname(track))

class PathStringTest(unittest.TestCase):
    def setUp(self):
        self.lib = beets.library.Library(':memory:')
        self.i = item()
        self.lib.add(self.i)

    def test_item_path_is_bytestring(self):
        self.assert_(isinstance(self.i.path, str))

    def test_fetched_item_path_is_bytestring(self):
        i = list(self.lib.items())[0]
        self.assert_(isinstance(i.path, str))

    def test_unicode_path_becomes_bytestring(self):
        self.i.path = u'unicodepath'
        self.assert_(isinstance(self.i.path, str))

    def test_unicode_in_database_becomes_bytestring(self):
        self.lib.conn.execute("""
        update items set path=? where id=?
        """, (self.i.id, u'somepath'))
        i = list(self.lib.items())[0]
        self.assert_(isinstance(i.path, str))

    def test_special_chars_preserved_in_database(self):
        path = 'b\xe1r'
        self.i.path = path
        self.lib.store(self.i)
        i = list(self.lib.items())[0]
        self.assertEqual(i.path, path)

    def test_special_char_path_added_to_database(self):
        self.lib.remove(self.i)
        path = 'b\xe1r'
        i = item()
        i.path = path
        self.lib.add(i)
        i = list(self.lib.items())[0]
        self.assertEqual(i.path, path)

    def test_destination_returns_bytestring(self):
        self.i.artist = u'b\xe1r'
        dest = self.lib.destination(self.i)
        self.assert_(isinstance(dest, str))

    def test_art_destination_returns_bytestring(self):
        self.i.artist = u'b\xe1r'
        alb = self.lib.add_album([self.i])
        dest = alb.art_destination(u'image.jpg')
        self.assert_(isinstance(dest, str))

    def test_artpath_stores_special_chars(self):
        path = 'b\xe1r'
        alb = self.lib.add_album([self.i])
        alb.artpath = path
        alb = self.lib.get_album(self.i)
        self.assertEqual(path, alb.artpath)

    def test_sanitize_path_with_special_chars(self):
        path = 'b\xe1r?'
        new_path = beets.library._sanitize_path(path)
        self.assert_(new_path.startswith('b\xe1r'))

    def test_sanitize_path_returns_bytestring(self):
        path = 'b\xe1r?'
        new_path = beets.library._sanitize_path(path)
        self.assert_(isinstance(new_path, str))

    def test_unicode_artpath_becomes_bytestring(self):
        alb = self.lib.add_album([self.i])
        alb.artpath = u'somep\xe1th'
        self.assert_(isinstance(alb.artpath, str))

    def test_unicode_artpath_in_database_decoded(self):
        alb = self.lib.add_album([self.i])
        self.lib.conn.execute(
            "update albums set artpath=? where id=?",
            (u'somep\xe1th', alb.id)
        )
        alb = self.lib.get_album(alb.id)
        self.assert_(isinstance(alb.artpath, str))

def suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

