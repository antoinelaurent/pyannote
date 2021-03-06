#!/usr/bin/env python
# encoding: utf-8

# Copyright 2012-2013 Herve BREDIN (bredin@limsi.fr)

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
SRT (SubRip Text) is a file format to specify subtitles for a recorded video.

References
----------
http://en.wikipedia.org/wiki/SubRip
"""


import pysrt
from pyannote.base.segment import Segment
from base import BaseTimelineParser


class SRTParser(BaseTimelineParser):

    def subRipTimeToSeconds(self, subRipTime):
        h = subRipTime.hours
        m = subRipTime.minutes
        s = subRipTime.seconds
        u = subRipTime.milliseconds
        return 1e-3*u+s+60.*m+3600.*h

    def read(self, path, uri=None, **kwargs):

        self.reset()

        items = pysrt.SubRipFile.open(path, encoding='utf8')
        for item in items:

            start = self.subRipTimeToSeconds(item.start)
            end = self.subRipTimeToSeconds(item.end)
            segment = Segment(start, end)

            self._add(segment, uri)

        return self

# from datetime import datetime, timedelta

# def __segment_to_srt(segment):
#     """
#     00:00:20,000 --> 00:00:24,400
#     """
#     dt = datetime(1,1,1)

#     td = timedelta(seconds=segment.start)
#     t = (dt + td).time()
#     text = '%02d:%02d:%02d,%03d' % (t.hour, t.minute, t.second, \
#                                     int(t.microsecond/1000))
#     text += " --> "

#     td = timedelta(seconds=segment.end)
#     t = (dt + td).time()
#     text += '%02d:%02d:%02d,%03d' % (t.hour, t.minute, t.second, \
#                                     int(t.microsecond/1000))
#     return text


# def toSRT(annotation):
#     """
#     1
#     00:00:20,000 --> 00:00:24,400
#     Altocumulus clouds occur between six thousand

#     2
#     00:00:24,600 --> 00:00:27,800
#     and twenty thousand feet above ground level.

#     """
#     text = ""

#     subtitle_number = 0
#     for segment in annotation:

#         subtitle_number += 1
#         subtitle_segment = __segment_to_srt(segment)
#         subtitle = ""

#         identifiers = annotation.ids(segment)

#         subtitle = identifiers.pop()

#         if len(identifiers) > 0:
#             for identifier in identifiers:
#                 subtitle += " / %s" % identifier

#         text += '%d\n' % subtitle_number
#         text += '%s\n' % subtitle_segment
#         text += '%s\n' % subtitle
#         text += '\n'

#     return text

# if __name__ == "__main__":
#     import doctest
#     doctest.testmod()
