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

from pyannote import Segment
from pyannote import Annotation, Unknown
from pyannote.parser.base import BaseAnnotationParser
try:
    import cvhcistandards
except Exception, e:
    pass
from pyannote.base import SEGMENT, TRACK, LABEL
from pandas import DataFrame


class FACETRACKSParser(BaseAnnotationParser):

    def __init__(self, load_ids=False):
        """
        KIT .facetracks file parser

        Parameters
        ----------
        load_ids : bool
            When True, parser will try to load track ids from corresponding
            facetracks.ids file.

        """
        super(FACETRACKSParser, self).__init__()
        self.load_ids = load_ids

    def read(self, path, uri=None, **kwargs):

        modality = 'head'
        facetracks, _, _ = cvhcistandards.read_tracks(
            path, load_ids=self.load_ids)

        segments = []
        tracks = []
        labels = []

        for track, data in facetracks.iteritems():

            start = data['state'][0][1]
            end = data['state'][-1][1]
            if start >= end:
                end = start + 0.040
            segment = Segment(start, end)
            # if not segment:
            #     continue

            if self.load_ids:
                label = data['label']
                if label is None:
                    label = Unknown()
            else:
                label = track

            segments.append(segment)
            tracks.append(track)
            labels.append(label)

        df = DataFrame(data={SEGMENT: segments,
                             TRACK: tracks,
                             LABEL: labels})
        annotation = Annotation.from_df(df, uri=uri, modality='head')
        self._loaded = {(uri, modality): annotation}

        return self

if __name__ == "__main__":
    import doctest
    doctest.testmod()
