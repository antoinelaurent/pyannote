#!/usr/bin/env python
# encoding: utf-8

# Copyright 2012 Herve BREDIN (bredin@limsi.fr)

# This file is part of PyAnnote.
#
#     PyAnnote is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     PyAnnote is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with PyAnnote.  If not, see <http://www.gnu.org/licenses/>.

"""
SEG (segmentation) is a file format to specify segmentations for a recorded
waveform.
"""

from pyannote.base.segment import SlidingWindow
from pyannote.base import URI, LABEL
from base import BaseTextualAnnotationParser, BaseTextualFormat


class SEGMixin(BaseTextualFormat):

    START = 'start'
    DURATION = 'duration'
    CHANNEL = 'channel'

    def get_comment(self):
        return '#'

    def get_separator(self):
        return ' '

    def get_fields(self):
        return [URI,
                LABEL,
                self.CHANNEL,
                self.START,
                self.DURATION]

    def get_segment(self, row):
        return self.sliding_window.rangeToSegment(row[self.START],
                                                  row[self.DURATION])

    def _append(self, annotation, f, uri, modality):

        try:
            format = '%s %%d 1 %%d %%d\n' % uri

            labels = annotation.labels()
            for l, label in enumerate(labels):
                A = annotation.subset(set([label]))
                for segment, _ in A.itertracks():
                    i0, n = self.sliding_window.segmentToRange(segment)
                    f.write(format % (l+1, i0, n))
        except Exception, e:
            print "Error @ %s%s %s" % (uri, segment, label)
            raise e


class SEGParser(BaseTextualAnnotationParser, SEGMixin):
    def __init__(self, sliding_window=None):

        super(SEGParser, self).__init__()

        if sliding_window is None:
            self.sliding_window = SlidingWindow()
        else:
            assert isinstance(sliding_window, SlidingWindow), \
                "%r is not a sliding window" % sliding_window
            self.sliding_window = sliding_window


if __name__ == "__main__":
    import doctest
    doctest.testmod()
