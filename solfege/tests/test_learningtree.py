# Solfege - free ear training software
# Copyright (C) 2007, 2008, 2011 Tom Cato Amundsen
# License is GPL, see file COPYING

from __future__ import absolute_import
import unittest
from solfege.frontpage import *

class TestLearningTree(unittest.TestCase):
    def test_create_page(self):
        page = Page(u'noname')
        self.assertEquals(len(page), 0)
        self.assertEquals(page.m_name, u'noname')
        page2 = Page(u'noname', [Column()])
        self.assertEquals(len(page2), 1)
        page3 = Page()
    def test_page(self):
        page = Page(u'noname')
    def test_column(self):
        # empty col
        col = Column()
        linklist = LinkList(u'Intervals', [])
        # can also construct with children
        col = Column(linklist)
        self.assertEqual(len(col), 1)
    def test_add_linklist(self):
        page = Page(u'noname', [Column()])
        column = page[-1]
        ll = column.add_linklist(u'Intervals')
        self.assertEqual(ll.m_name, u'Intervals')
        self.assertFalse(ll)
    def test_linklist(self):
        ll = LinkList(u'Intervals', [])
        self.assertEquals(len(ll), 0)
        ll = LinkList(u'Intervals', [u'sdfsf23'])
        self.assertEquals(len(ll), 1)
        self.assertEquals(ll[0], u'sdfsf23')
        self.assertEquals(ll, [u'sdfsf23'])
        ll.append(u'47d82-f32sd93-f8sd9s32')
        ll.append(Page(u'noname'))
        self.assertEquals(ll.m_name, u'Intervals')
        self.assertEquals(len(ll), 3)
    def test_is_empty(self):
        p = Page()
        self.assertEquals(p.is_empty(), True)
        p.append(Column())
        self.assertEquals(p.is_empty(), True)
        p[0].append(LinkList(u'test', []))
        self.assertEquals(p.is_empty(), True)
    def test_load_tree(self):
        load_tree("exercises/standard/learningtree.txt")
    def test_iterate_filenames(self):
        p = Page(u'noname', [
            Column(
                LinkList(u'heading', [
                    u'id1', u'id2', u'id3',]),
            ),
        ])
        self.assertEquals(list(p.iterate_filenames()),
                [u'id1', u'id2', u'id3'])
        p[0].append(LinkList(u'heading', [u'id1', u'id5']))
        self.assertEquals(list(p.iterate_filenames()),
                [u'id1', u'id2', u'id3', u'id1', u'id5'])
    def test_use_count(self):
        p = Page(u'noname', [
            Column(
                LinkList(u'heading', [
                    u'id1', u'id2', u'id3',]),
            ),
        ])
        d = p.get_use_dict()
        self.assertEquals(p.get_use_dict(), {u'id1': 1, u'id2': 1, u'id3': 1})
        p[0].append(LinkList(u'heading', [u'id1', u'id5']))
        self.assertEquals(p.get_use_dict(), {u'id1': 2, u'id2': 1, u'id3': 1, u'id5': 1})
    def test_iterate_topics_for_file(self):
        p = Page(u'noname', [
            Column(
                LinkList(u'heading', [
                    u'id1', u'id2', u'id3',]),
            ),
        ])
        p[0].append(LinkList(u'heading2', [u'id1', u'id5']))
        self.assertEquals(list(p.iterate_topics_for_file(u'id1')),
                [u'heading', 'heading2'])
        self.assertEquals(list(p.iterate_topics_for_file(u'id3')),
                [u'heading'])
        self.assertEquals(list(p.iterate_topics_for_file(u'id5')),
                [u'heading2'])


suite = unittest.makeSuite(TestLearningTree)

