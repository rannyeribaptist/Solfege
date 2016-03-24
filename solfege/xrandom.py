# GNU Solfege - free ear training software
# Copyright (C) 2005, 2007, 2008, 2011 Tom Cato Amundsen
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
from __future__ import division

import random
from solfege import cfg

class Random(object):
    def __init__(self, choices):
        #TODO add assert that all choices are unique
        self.m_choices = choices
        self.m_choice_count = len(choices) * [0]
        # The number of randoms generated
        self.m_count = 0
        self.m_last_choices = []
    def reset(self):
        self.m_last_choices = []
        self.m_choice_count = len(self.m_choices) * [0]
        self.m_count = 0
    def get_random_by_random_data(self, available_choices):
        not_selected_factor = 2
        data = []
        count = 0.0
        for k in available_choices:
            count += self.m_choice_count[k] / self.m_count
            data.append([k, self.m_choice_count[k] / self.m_count, 0.0])
        maxval = 0.0
        for v in data:
            if v[1] != 0.0:
                v[2] = 1/pow(v[1], cfg.get_float("app/randomness"))
                maxval = max(maxval, v[2])
        # Give the questions that has not been asked any times, twice as
        # big chance to be asked as the question that has been asked
        # fewest times.
        for v in data:
            if v[1] == 0.0:
                v[2] = maxval * not_selected_factor
        return data
    def random_by_random(self, available_choices):
        """
        Select by random, but make it more likely that choices that
        has been selected few times are selected than questions that has
        been selected many times.
        """
        if self.m_count == 0:
            return random.choice(available_choices)
        data = self.get_random_by_random_data(available_choices)
        f = 0.0
        for v in data:
            f += v[2]
            v.append(f)
        selectval = data[-1][3] * random.random()
        for v in data:
            if selectval < v[3]:
                return v[0]
        return data[-1][0]
    def random_by_random2(self, available_choices):
        """
        Select by random, but make it more likely that choices that
        has been selected few times are selected than questions that has
        been selected many times.
        """
        if self.m_count == 0:
            return random.choice(available_choices)
        data = self.get_random_by_random_data(available_choices)
        if self.m_last_choices:
            data[self.m_last_choices[-1]][2] *= 0.5
        if len(self.m_last_choices) >= 2 and self.m_last_choices[-1] == self.m_last_choices[-2]:
            data[self.m_last_choices[-1]][2] *= 0.5
        f = 0.0
        for v in data:
            f += v[2]
            v.append(f)
        selectval = data[-1][3] * random.random()
        for v in data:
            if selectval < v[3]:
                return v[0]
        return data[-1][0]
    def random_by_selection(self, available_choices):
        """
        The smallest randomness value is 1
        Larger value make things more even.
        Smaller value make things more random.
        """
        v = []
        if self.m_count > len(self.m_choices):
            for k in available_choices:
                if self.m_choice_count[k] / self.m_count < 1 / (len(self.m_choices) * self.get_float("app/randomness")):
                    v.append(k)
            if v:
                return random.choice(v)
        return random.choice(self.m_choices)
    def add(self, idx):
        self.m_choice_count[idx] += 1
        self.m_count += 1
        self.m_last_choices.append(idx)
        if len(self.m_last_choices) > len(self.m_choices) * 2:
            self.m_last_choices.pop(0)

