#!/usr/bin/env python
# encoding: utf-8

# Copyright 2013 Herve BREDIN (bredin@limsi.fr)

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


from pyannote.base.segment import Segment
from pyannote.base import URI, MODALITY, LABEL
from base import BaseTextualAnnotationParser, BaseTextualFormat


class REFMixin(BaseTextualFormat):

    START = 'start'
    END = 'end'

    def get_comment(self):
        return ';'

    def get_separator(self):
        return ' '

    def get_fields(self):
        return [URI,
                self.START,
                self.END,
                MODALITY,
                LABEL]

    def get_segment(self, row):
        return Segment(row[self.START], row[self.END])

    def _append(self, annotation, f, uri, modality):

        try:
            format = '%s %%g %%g %s %%s\n' % (uri, modality)
            for segment, track, label in annotation.itertracks(label=True):
                f.write(format % (segment.start, segment.end, label))
        except Exception, e:
            print "Error @ %s%s %s" % (uri, segment, label)
            raise e


class REFParser(BaseTextualAnnotationParser, REFMixin):
    pass


if __name__ == "__main__":
    import doctest
    doctest.testmod()
