# GNU Solfege - free ear training software
# vim: set fileencoding=utf-8 :
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2011 Tom Cato Amundsen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import absolute_import

import hashlib
import logging
import os
import pickle
import shutil
import sqlite3
import time

from solfege import filesystem
from solfege import lessonfile
from solfege import mpd
from solfege import utils

import solfege


def hash_lessonfile_text(s):
    """
    Return the hashvalue of the string s, after filtering out:
    * lines starting with '#'
    * empty lines
    """
    lines = s.split("\n")
    lines = [x for x in lines if (not x.startswith("#") and bool(x))]
    sha1 = hashlib.sha1()
    sha1.update("\n".join(lines))
    return sha1.hexdigest()


def hash_of_lessonfile(filename):
    assert isinstance(filename, unicode)
    return hash_lessonfile_text(open(lessonfile.uri_expand(filename), 'r').read())


class DB(object):
    type_int_dict = {int: 0, unicode: 1, float: 2}
    int_type_dict = {0: int, 1: unicode, 2: float}
    class VariableTypeError(Exception): pass
    class VariableUndefinedError(Exception): pass
    class FileNotInDB(Exception): pass
    def __init__(self, callback=None, profile=None):
        """
        callback is called to display progress when scanning lesson files.
        profile None is the default profile stored in app_data(),
        if profile is PROFILENAME, this is the profile stored in
        app_data()/profiles/PROFILENAME
        """
        self.m_profile = profile
        try:
            if testsuite_is_running:
                statistics_filename = ":memory:"
        except NameError:
            statistics_filename = self.get_statistics_filename()
            # We make a backup of the statistics file since Solfege 3.21.2 will
            # delete the statistics for the elembuilder exercise.
            bk_filename = u"%s.pre-3.21.2.backup" % statistics_filename
            if os.path.exists(statistics_filename) and not os.path.exists(bk_filename):
                shutil.copyfile(statistics_filename, bk_filename)
            head, tail = os.path.split(statistics_filename)
            if not os.path.exists(head):
                os.makedirs(head)
        self.conn = sqlite3.connect(statistics_filename)
        # Solfege 3.15.0-3.15.2
        if self.drop_if_has_uuid_column():
            db_ver = 3
        elif self.sanity_check():
            db_ver = 3
        try:
            db_ver = self.get_variable("database_version")
        except self.VariableUndefinedError:
            # We did not set database_version to 2, ever...
            db_ver = 1
        if db_ver < 2:
            # upgrade_to_version_2() should have deleted the tests table,
            # but unfortunately it did not. So we cannot test for that
            # table to check if we are at version 1. But
            self.upgrade_to_version_2()
        if db_ver < 3:
            self.upgrade_to_version_3()
        self.set_variable("database_version", 3)
        self.conn.commit()
    def insert_file(self, filename):
        assert lessonfile.is_uri(filename) or os.path.isabs(filename)
        self.conn.execute("insert into lessonfiles "
                "(filename, hash) "
                "values (?, ?)",
                (filename, hash_of_lessonfile(filename)))
        return self.get_fileid(filename)
    @staticmethod
    def get_noprofile_statistics_filename():
        return os.path.join(filesystem.app_data(), "statistics.sqlite")
    def get_statistics_filename(self):
        if self.m_profile:
            return os.path.join(filesystem.app_data(), "profiles", self.m_profile, "statistics.sqlite")
        else:
            return self.get_noprofile_statistics_filename()
    def reset_database(self):
        self.conn.close()
        os.remove(self.get_statistics_filename())
        self.conn = sqlite3.connect(self.get_statistics_filename())
        self.create_tables()
    def remove_tables(self):
        """
        Remove the tables if they exist.
        """
        self.conn.execute("drop table if exists sessions")
        self.conn.execute("drop table if exists sessioninfo")
        self.conn.execute("drop table if exists lessonfiles")
        self.conn.execute("drop table if exists variables")
        # Current Solfege does not use this table, but we did until
        # the 3.17.0 release. So we remove it if it exists.
        self.conn.execute("drop table if exists tests")
    def create_tables(self):
        self.conn.execute(
            "create table if not exists lessonfiles ( "
            " fileid integer primary key autoincrement, "
            " hash text not null, "
            # The test result of the last time the exercise was tested.
            " test_result float default None, "
            # Did we pass?
            # None is not test taken. True if passed, False if not
            " test_passed int default None, "
            " filename text unique not null "
            ")")
        self.conn.execute('''create table if not exists sessions
            (fileid int, timestamp int, answerkey text, guessed text, count int, unique (fileid, timestamp, answerkey, guessed) )''')
        self.conn.execute('''create table if not exists variables
            (variable_name text primary key not null,
             type int not null,
             value text not null)''')
        self.conn.execute("create table if not exists sessioninfo "
            "(fileid int, timestamp int, sessiontype int, "
            "unique (fileid, timestamp))")
        self.set_variable("database_version", 3)
    def drop_if_has_uuid_column(self):
        """
        Drop the database and return True if the lessonfiles table
        has a uuid column.
        We started using sqlite to store statistics in Solfege 3.15.0.
        Solfege 3.15.0-3.15.2 had this column, but it was a bad idea.
        """
        columns = [x[1] for x in
            self.conn.execute('pragma table_info(lessonfiles)').fetchall()]
        # true if the database is created by solfege 3.15.0 - 3.15.2
        if u'uuid' in columns:
            logging.debug("statistics: dropping tables because the database is from solfege-3.15.0-3.15.2")
            self.remove_tables()
            self.create_tables()
            return True
    def _get_table_names(self):
        """
        Return a set of all table names in the database.
        """
        tables = self.conn.execute('select name from sqlite_master where type="table";').fetchall()
        return set([x[0] for x in tables])
    def sanity_check(self):
        """
        The content of the tables 'sessions', 'sessioninfo' and 'lessonfiles'
        depend of neach other. So we neeed to delete and recreate all tables
        if any of them are missing. Just to be safe, we delete if the
        'variables' table are missing tooo.

        A table 'tests' existed until version 3.17, but we don't check for
        that since we don't use it any more.

        Return True if the tables where deleted and recreated.
        """
        tables = self._get_table_names()
        for t in ('lessonfiles', 'sessions', 'sessioninfo', 'variables'):
            if t not in tables:
                missing_table = True
                break    
        else:
            missing_table = False
        # This is a sanity check. If one of the tables are missing, then
        # we cannot trust anything, so lets just drop and recreate the database.
        if missing_table:
            self.remove_tables()
            self.create_tables()
            return True
    def get_fileid(self, filename):
        assert lessonfile.is_uri(filename) or os.path.isabs(filename), filename
        row = self.conn.execute(
                "select fileid from lessonfiles "
                "where filename=?",
                (filename,)).fetchone()
        if row:
            return row[0]
        else:
            raise self.FileNotInDB(filename)
    def get_session_count(self, fileid):
        """
        Return an int telling the number of practise sessions we have
        stored for the given fileid.
        """
        count = self.conn.execute("select count(distinct timestamp) from sessions where fileid=?", (fileid,)).fetchone()[0]
        return count if count is not None else 0
    def get_first_timestamp(self, fileid):
        """
        Return the timestamp (as a python datetime object) of the first
        practise session recorded for this fileid.
        Return None if no sessions are found.
        """
        return self.conn.execute("select min(timestamp) from sessions where fileid=?",
                          (fileid,)).fetchone()[0]
    def get_last_timestamp(self, fileid):
        """
        Return the timestamp (as a python datetime object) of the last
        practise session recorded for this fileid.
        Return None if no sessions are found.
        """
        return self.conn.execute("select max(timestamp) from sessions where fileid=?",
                          (fileid,)).fetchone()[0]
    def delete_statistics(self, filename):
        fileid = self.get_fileid(filename)
        cursor = self.conn.cursor()
        cursor.execute("delete from sessions where fileid=?", (fileid,))
        cursor.execute("delete from sessioninfo where fileid=?", (fileid,))
        self.conn.commit()
    def upgrade_to_version_3(self):
        try:
            if self.get_variable("database_version") >= 3:
                return
        except self.VariableUndefinedError:
            pass
        for fn in lessonfile.infocache.iter_parse_all_files():
            if lessonfile.infocache.get(fn, 'module') == 'elembuilder':
                try:
                    self.delete_statistics(fn)
                except self.FileNotInDB:
                    pass
    def upgrade_to_version_2(self):
        """
        After releasing 3.16.0 I found that having separate tests and
        sessions table was a bad idea since we may want to add different
        tests later. Also tests and practise sessions in one table make
        it even easier to see which questions needs most practise.
        """
        try:
            if self.get_variable("database_version") >= 2:
                return
        except self.VariableUndefinedError:
            pass
        # This should not happen, but the database_version variable was
        # not set at the same time as we changed this behaviour, so lets just
        # return if the table does not exist.
        if 'test' not in self._get_table_names():
            return
        # Insert all tests into sessioninfo
        for fileid, timestamp in self.conn.execute("select distinct fileid, timestamp from tests"):
            # This should always succeed since we have just created sessioninfo.
            # But let us try: just to be safe.
            try:
                self.conn.execute("insert into sessioninfo "
                    "(fileid, timestamp, sessiontype) "
                    "values (?, ?, ?)",
                    (fileid, timestamp, 1))
            except sqlite3.IntegrityError, e:
                logging.error(u"%s, %s, %s", e, fileid, timestamp)
        # Insert all practise sessions into sessioninfo
        for fileid, timestamp in self.conn.execute("select distinct fileid, timestamp from sessions"):
            # This can fail because 3.14.11 and earlier had a bug where the same
            # session was created in both statistics and testresult.
            try:
                self.conn.execute("insert into sessioninfo "
                    "(fileid, timestamp, sessiontype) "
                    "values (?, ?, ?)",
                    (fileid, timestamp, 0))
            except sqlite3.IntegrityError, e:
                logging.error(u"%s, %s, %s", e, fileid, timestamp)
        # Copy all tests from the obsolete "tests" table to "sessions"
        for a, b, c, d in self.conn.execute("select fileid, timestamp, answerkey, guessed from tests"):
            # This can fail because 3.14.11 and earlier had a bug where the same
            # session was create in both statistics and testresult.
            try:
                self.conn.execute("insert into sessions "
                    "(fileid, timestamp, answerkey, guessed) "
                    "values (?, ?, ?, ?)",
                    (a, b, c, d))
            except sqlite3.IntegrityError, e:
                logging.error(u"%s, %s, %s", e, fileid, timestamp)
        for fileid, filename in self.conn.execute(
                "select sessioninfo.fileid, lessonfiles.filename "
                "from sessioninfo, lessonfiles "
                "where sessioninfo.fileid=lessonfiles.fileid "
                "      and sessioninfo.sessiontype<>0 "):
            for timestamp in self.conn.execute(
                "select timestamp from sessioninfo where fileid=? "
                "order by -timestamp",
                (fileid,)).fetchone():
                module = lessonfile.infocache.get(filename, "module")
                if module == 'melodicinterval':
                    parserclass = lessonfile.IntervalsLessonfile
                else:
                    parserclass = None
                if parserclass:
                    p = parserclass()
                    p.parse_file(filename)
                    self.cache_new_test_result(filename, timestamp,
                        p.get_test_requirement(), p.get_test_num_questions())
    def cache_new_test_result(self, filename, timestamp,
                              required, num_questions):
        """
        Save the test result in the "lessonfiles" table for faster
        access later.
        """
        logging.debug("cache_new_test_result(%s, %s, %s, %s)",
            filename, timestamp, required, num_questions)
        fileid = self.get_fileid(filename)
        count_correct = self.conn.execute("select sum(count) from sessions where fileid=? and timestamp=? and answerkey=guessed", (fileid, timestamp)).fetchone()[0]
        if not count_correct:
            count_correct = 0
        count_total = self.conn.execute("select sum(count) from sessions where fileid=? and timestamp=?", (fileid, timestamp)).fetchone()[0]
        # count_total is 0 if the user click cancel before answering
        # any questions. If so, we returns without saving anything. I don't
        # see the point in saving tests where no questions where answered.
        if not count_total:
            return
        if count_total < num_questions:
            count_total = num_questions
        if count_total:
            test_result = count_correct * 1.0 / count_total
        else:
            test_result = 0.0
        self.conn.execute("update lessonfiles "
                        "set test_result=?, test_passed=? where fileid=?",
            (test_result,
             test_result >= required,
             fileid,))
        self.conn.commit()
    def get_test_status(self, filename):
        """
        Return a tuple saying if the test was passed or not, and the result:
        (bool, float)
        If no test have been made, we return (None, None)
        """
        logging.debug("get_test_status(%s)", filename)
        try:
            fileid = self.get_fileid(filename)
            row = self.conn.execute("select test_passed, test_result "
                "from lessonfiles "
                "where fileid=?", (fileid,)).fetchone()
            return row
        except self.FileNotInDB:
            return None, None
    def validate_stored_statistics(self, filename):
        """
        Insert the filename and hash of the file into the lessonfiles
        table if it is not registered there already.

        If already there, compare the hash value of the file with what
        we have in the database. Remove all saved statistics and insert
        the new hash value if they do not match.

        Return doing nothing if the file does not exist.
        """
        logging.debug("validate_stored_statistics(%s)", filename)
        if not os.path.isfile(lessonfile.uri_expand(filename)):
            logging.debug("validate_stored_statistics: file does not exist.")
            return
        cursor = self.conn.cursor()
        row = cursor.execute("select hash, fileid from lessonfiles "
            "where filename=?", (filename,)).fetchone()
        cur_lessonfile_hash_value = hash_of_lessonfile(filename)
        if not row:
            # Ususally the filename exists in the database, but when running
            # the test suite, it does not, so we have the code here to add it.
            self.insert_file(filename)
            self.conn.commit()
        else:
            hashvalue, fileid = row
            if hashvalue != cur_lessonfile_hash_value:
                replaces = solfege.lessonfile.infocache.get(filename, 'replaces')
                if not isinstance(replaces, list):
                    replaces = [replaces]
                if not hashvalue in replaces:
                    solfege.db.delete_statistics(filename)
                    cursor.execute("update lessonfiles "
                        "set hash=?, test_passed=?, test_result=0.0 where fileid=?",
                        (cur_lessonfile_hash_value, None, fileid))
                    self.conn.commit()
    def get_statistics_info(self):
        """
        Return information about the data installed.
        Return a tuple (number of different exercises practised,
                        number of times we have practised,
                        number of times we have taken a test)
        """
        session_count = self.conn.execute('select count(fileid) '
            'from sessioninfo '
            'where sessiontype=0').fetchone()[0]
        test_count = self.conn.execute('select count(fileid) '
            'from sessioninfo '
            'where sessiontype=1').fetchone()[0]
        different_ex = len(self.conn.execute('select fileid from sessioninfo group by fileid').fetchall())
        return {'exercises': different_ex,
                'practise_count': session_count,
                'test_count': test_count}
    def _recent(self, count, sessiontype):
        """
        sessiontype 0 == normal statistics
        sessiontype 1 == test results
        """
        filenames = []
        for fileid, timestamp in self.conn.execute(
                'select fileid, timestamp from sessioninfo '
                'where sessiontype=? '
                'order by -timestamp',
                (sessiontype,)):
            filename = self.conn.execute('select filename from lessonfiles where fileid=?', (fileid,)).fetchone()[0]
            if filename not in filenames:
                filenames.append(filename)
            if len(filenames) == count:
                break
        return filenames
    def recent(self, count):
        return self._recent(count, 0)
    def recent_tests(self, count):
        return self._recent(count, 1)
    def set_variable(self, name, value):
        """
        raise DB.VariableTypeError if the type we set is different from
        the one already stored.
        """
        row = self.conn.execute('select type, value from variables where variable_name=?', (name,)).fetchone()
        if row:
            saved_type = self.int_type_dict[row[0]]
        else:
            saved_type = type(value)
        if saved_type != type(value):
            raise DB.VariableTypeError()
        if type(value) not in self.type_int_dict:
            raise DB.VariableTypeError()
        if not row:
            self.conn.execute("insert into variables "
                    "(variable_name, type, value) "
                    "values (?, ?, ?)",
                    (name, self.type_int_dict[type(value)], unicode(value)))
        else:
            self.conn.execute("update variables "
                "set value=? where variable_name=?",
                (unicode(value), name))
    def get_variable(self, name):
        cursor = self.conn.execute('select type, value from variables where variable_name=?', (name,))
        try:
            type, value = cursor.fetchone()
        except TypeError:
            raise self.VariableUndefinedError()
        return self.int_type_dict[type](value)
    def del_variable(self, name):
        """
        Delete the variable, raise DB.VariableUndefinedError if the variable
        is not found.
        """
        cursor = self.conn.execute('delete from variables where variable_name=?', (name,))
        if not cursor.rowcount:
            # rowcount is 0 if no variables where deleted. We raise an
            # error, since I'd like to know if we tries to do this.
            raise self.VariableUndefinedError()


class AbstractStatistics(object):
    def __init__(self, teacher):
        self.m_t = teacher
        self.m_timestamp = None
        self.m_test_mode = False
    def int_if_int(self, s):
        """
        Return an int if the can be converted to an int.
        Return unchanged if not.
        """
        try:
            return int(s)
        except ValueError:
            return s
    def get_keys(self, all_keys=False):
        """
        Return the keys for all questions that have been answered correctly.
        If all_keys are True, it should also return the correct key for all
        questions that only have been answered wrongly.
        """
        try:
            fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        except DB.FileNotInDB:
            return []
        if all_keys:
            c = set()
            for colname in "answerkey", "guessed":
                c1 = list(solfege.db.conn.execute("select distinct(%s) from sessions where fileid=?" % colname, (fileid,)))
                if c1:
                    [c.add(x[0]) for x in c1]
            c = list(c)
        else:
            c = solfege.db.conn.execute("select distinct(answerkey) from sessions where fileid=? and answerkey=guessed", (fileid,))
            c = [x[0] for x in list(c)]
        v = [self.int_if_int(x) for x in c]
        v.sort()
        return [unicode(x) for x in v]
    def get_statistics(self, seconds):
        """
        return a dict with statistics more recent than 'seconds' seconds.
        The keys of dict are the correct answers for the lesson file.
        And the values of dict are new dicts where the keys are all the
        answers the user have given and the values are the number of times
        that particular answer has been given.
        Special values of second:
        -1: all history
        0: statistics from the current session
        """
        try:
            fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        except DB.FileNotInDB:
            return {}
        if seconds == -1:
            q = solfege.db.conn.execute("select answerkey, guessed, sum(count) from sessions where fileid=? group by answerkey, guessed", (fileid,))
        elif seconds == 0:
            q = solfege.db.conn.execute("select answerkey, guessed, sum(count) from sessions where fileid=? and timestamp=? group by answerkey, guessed", (fileid, self.m_timestamp))
        else:
            q = solfege.db.conn.execute("select answerkey, guessed, sum(count) from sessions where fileid=? and timestamp>? group by answerkey, guessed", (fileid, self.m_timestamp - seconds))
        ret = {}
        for answer, guess, count in q.fetchall():
            ret.setdefault(answer, {})
            ret[answer][guess] = count
        return ret
    def reset_session(self):
        """
        Start a new practise session.
        """
        self.m_timestamp = int(time.time())
    def reset_custom_mode_session(self, filename):
        """
        Exercises that show statistics in custom_mode should call this
        method instead of reset_session.
        """
        self.m_timestamp = 1
        fileid = solfege.db.get_fileid(filename)
        solfege.db.conn.execute("delete from sessions "
                          "where fileid=? and timestamp=1", (fileid,))
    def enter_test_mode(self):
        self.m_test_mode = True
    def exit_test_mode(self):
        """
        If the user cancels a test, the answers give will be recorded.
        So clicking cancel right after starting a test will set the the
        latest score to 0.0%
        """
        self.m_test_mode = False
        solfege.db.cache_new_test_result(self.m_t.m_P.m_filename,
                self.m_timestamp,
                self.m_t.m_P.get_test_requirement(),
                self.m_t.m_P.get_test_num_questions())
        self.reset_session()
    def _add(self, question, answer):
        """
        Register that for the question 'question' the user answered 'answer'.
        """
        assert self.m_timestamp
        # tuples must be converted to str to store them in sqlite. Integers
        # and probably some other types will automatically be converted to
        # strings by sqlite before storing then in the database.
        if isinstance(question, tuple):
            question = str(question)
        if isinstance(answer, tuple):
            answer = str(answer)
        cursor = solfege.db.conn.cursor()
        fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        # Let us check if the session has been added to "sessioninfo"
        # We don't add the session to the "sessioninfo" table before we have
        # an answer to store, to avoid empty sessions because users start
        # an exercise and the descides it was the wrong exercise.
        if not cursor.execute("select * from sessioninfo where fileid=? and timestamp=?", (fileid, self.m_timestamp)).fetchone():
            cursor.execute("insert into sessioninfo"
                    "(fileid, timestamp, sessiontype) "
                    "values (?, ?, ?)",
                    (fileid, self.m_timestamp, 1 if self.m_test_mode else 0))

        row = cursor.execute(
                "select count from sessions where fileid=? and timestamp=? "
                "and answerkey=? and guessed=?",
                (fileid, self.m_timestamp, unicode(question), unicode(answer))).fetchone()
        if not row:
            cursor.execute(
                "insert into sessions "
                "(fileid, timestamp, answerkey, guessed, count) "
                "values(?, ?, ?, ?, ?)",
                (fileid, self.m_timestamp,
                 unicode(question), unicode(answer), 1))
        else:
            assert cursor.fetchone() is None
            cursor.execute(
                "update sessions set count=? where "
                "fileid=? and timestamp=? and answerkey=? and guessed=?",
                (row[0] + 1, fileid,
                 self.m_timestamp, unicode(question), unicode(answer)))
        solfege.db.conn.commit()
    def add_wrong(self, question, answer):
        self._add(question, answer)
    def add_correct(self, answer):
        self._add(answer, answer)
    def get_last_test_result(self):
        """
        Return the test result of the last test ran for this lesson file.
        """
        return solfege.db.last_test_result(self.m_t.m_P.m_filename)
    def get_percentage_correct(self):
        """Will return a 0 <= value <= 100.0 that say how many percent is
        correct in this session.
        """
        fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        num_correct = solfege.db.conn.execute("select sum(count) from sessions where answerkey=guessed and timestamp=? and fileid=?", (self.m_timestamp, fileid)).fetchone()[0]
        num_asked = solfege.db.conn.execute("select sum(count) from sessions where timestamp=? and  fileid=?", (self.m_timestamp, fileid)).fetchone()[0]
        if not num_correct:
            num_correct = 0
        if not num_asked:
            num_asked = 0
            return 0
        return 100.0 * num_correct / num_asked
    def get_num_correct_for_key(self, seconds, key):
        """
        Return the number of correct answers for the given key 'key' the
        last 'seconds' seconds.
        Special meanings of 'seconds':
            -1  all statistics
             0  statistics from this session
        """
        fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        if seconds == -1:
            ret = solfege.db.conn.execute("select sum(count) from sessions where answerkey=? and guessed=? and fileid=?", (key, key, fileid)).fetchone()[0]
        elif seconds == 0:
            ret = solfege.db.conn.execute("select sum(count) from sessions where answerkey=? and guessed=? and timestamp=? and fileid=?", (key, key, self.m_timestamp, fileid)).fetchone()[0]
        else:
            ret = solfege.db.conn.execute("select sum(count) from sessions where answerkey=? and guessed=? and timestamp>? and fileid=?", (key, key, self.m_timestamp - seconds, fileid)).fetchone()[0]
        if ret:
            return ret
        return 0
    def get_num_guess_for_key(self, seconds, key):
        """
        See get_num_correct_for_key docstring.
        """
        fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        if seconds == -1:
            ret = solfege.db.conn.execute("select sum(count) from sessions where answerkey=? and fileid=?", (key, fileid)).fetchone()[0]
        elif seconds == 0:
            ret = solfege.db.conn.execute("select sum(count) from sessions where answerkey=? and timestamp=? and fileid=?", (key, self.m_timestamp, fileid)).fetchone()[0]
        else:
            ret = solfege.db.conn.execute("select sum(count) from sessions where answerkey=? and timestamp>? and fileid=?", (key, self.m_timestamp - seconds, fileid)).fetchone()[0]
        if ret:
            return ret
        return 0
    def get_num_guess(self, seconds):
        fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        if seconds == -1:
            ret = solfege.db.conn.execute("select sum(count) from sessions where fileid=?", (fileid,)).fetchone()[0]
        elif seconds == 0:
            ret = solfege.db.conn.execute("select sum(count) from sessions where timestamp=? and fileid=?", (self.m_timestamp, fileid,)).fetchone()[0]
        else:
            ret = solfege.db.conn.execute("select sum(count) from sessions where timestamp>? and fileid=?", (self.m_timestamp - seconds, fileid)).fetchone()[0]
        if ret:
            return ret
        return 0
    def get_num_correct(self, seconds):
        fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        if seconds == -1:
            ret = solfege.db.conn.execute("select sum(count) from sessions where fileid=? and answerkey=guessed", (fileid,)).fetchone()[0]
        elif seconds == 0:
            ret = solfege.db.conn.execute("select sum(count) from sessions where timestamp=? and fileid=? and answerkey=guessed", (self.m_timestamp, fileid,)).fetchone()[0]
        else:
            ret = solfege.db.conn.execute("select sum(count) from sessions where timestamp>? and fileid=? and answerkey=guessed", (self.m_timestamp - seconds, fileid,)).fetchone()[0]
        if ret:
            return ret
        return 0
    def iter_test_results(self):
        """
        Iterate test results for the associated lesson file, newest
        results first.
        """
        try:
            fileid = solfege.db.get_fileid(self.m_t.m_P.m_filename)
        except DB.FileNotInDB:
            return
        for [timestamp] in solfege.db.conn.execute("select timestamp from sessioninfo where fileid=? and sessiontype=? order by -timestamp", (fileid, 1)):
            ret = {}
            for answerkey, guessed, count in solfege.db.conn.execute("select answerkey, guessed, count from sessions where fileid=? and timestamp=?", (fileid, timestamp)):
                ret.setdefault(answerkey, {})
                ret[answerkey][guessed] = count
            # More necessary than one would expect because we want to handle
            # the possibility that that ret[key1][key2] == None
            # A user has reported that this can happen, but I don't know
            # what could insert a None into the database.
            f = (100.0 * sum([y for y in [ret[x].get(x, 0) for x in ret] if y is not None])
                 / self.m_t.m_P.get_test_num_questions())
            yield timestamp, f, ret


class LessonStatistics(AbstractStatistics):
    def key_to_pretty_name(self, key):
        def ff(x):
            try:
                t = eval(x)
                if type(t) == tuple:
                    return lessonfile.LabelObject(t[0], t[1])
            except Exception:
                return x
            return x
        for question in self.m_t.m_P.m_questions:
            if question.name.cval == key:
                return ff(question.name)
        return ff(key)

class IntervalStatistics(AbstractStatistics):
    def get_keys(self, all_keys=False):
        # FIXME we have to check that all keys are integers, and filter
        # out those that are not. I don't know how, but I ended up with
        # the key None inserted into the database. Without that bug this
        # whole method would be unnecessary and AbstractStatistics.get_keys
        # would be enough.
        def isinteger(s):
            try:
                int(s)
                return True
            except ValueError:
                return False
        v = AbstractStatistics.get_keys(self, all_keys)
        return [x for x in v if isinteger(x)]
    def key_to_pretty_name(self, key):
        return utils.int_to_intervalname(int(key), 1, 1)

class HarmonicIntervalStatistics(IntervalStatistics):
    def key_to_pretty_name(self, key):
        return utils.int_to_intervalname(int(key), 1, 0)

class IdToneStatistics(LessonStatistics):
    def key_to_pretty_name(self, key):
        return mpd.MusicalPitch.new_from_notename(key).get_user_notename()


