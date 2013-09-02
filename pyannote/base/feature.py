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

Features.

"""

import numpy as np
from pyannote.base.segment import Segment, SlidingWindow
from pyannote.base.timeline import Timeline


class BaseSegmentFeature(object):

    """
    Base class for any segment/feature iterator.
    """

    def __init__(self, uri=None):
        super(BaseSegmentFeature, self).__init__()
        self.__uri = uri

    def __get_uri(self):
        return self.__uri

    def __set_uri(self, value):
        self.__uri = value
    uri = property(fget=__get_uri, fset=__set_uri)
    """Path to (or any identifier of) described resource"""

    def __iter__(self):
        """Segment/feature vector iterator

        Use expression 'for segment, feature_vector in segment_feature'

        This method must be implemented by subclass.

        """
        raise NotImplementedError('Missing method "__iter__".')


class BasePrecomputedSegmentFeature(BaseSegmentFeature):

    """'Segment iterator'-driven precomputed feature iterator.

    Parameters
    ----------
    data : numpy array
        Feature vectors stored in such a way that data[i] is ith feature vector.
    segment_iterator : :class:`SlidingWindow` or :class:`Timeline`
        Segment iterator.
        Its length must correspond to `data` length.
    uri : string, optional
        name of (audio or video) described resource

    """

    def __init__(self, data, segment_iterator, uri=None):
        # make sure data does not contain NaN nor inf
        data = np.asarray_chkfinite(data)

        # make sure segment_iterator is actually one of those
        if not isinstance(segment_iterator, (SlidingWindow, Timeline)):
            raise TypeError("segment_iterator must 'Timeline' or "
                            "'SlidingWindow'.")

        # make sure it iterates the correct number of segments
        try:
            N = len(segment_iterator)
        except Exception:
            # an exception is raised by `len(sliding_window)`
            # in case sliding window has infinite end.
            # this is acceptable, no worry...
            pass
        else:
            n = data.shape[0]
            if n != N:
                raise ValueError("mismatch between number of segments (%d) "
                                 "and number of feature vectors (%d)." % (N, n))

        super(BasePrecomputedSegmentFeature, self).__init__(uri=uri)
        self.__data = data
        self._segment_iterator = segment_iterator

    def __get_data(self):
        return self.__data
    data = property(fget=__get_data)
    """Raw feature data (numpy array)"""

    def __iter__(self):
        """Feature vector iterator

        Use expression 'for segment, feature_vector in periodic_feature'

        """

        # get number of feature vectors
        n = self.__data.shape[0]

        for i, segment in enumerate(self._segment_iterator):

            # make sure we do not iterate too far...
            if i >= n:
                break

            # yield current segment and corresponding feature vector
            yield segment, self.__data[i]

    def _segmentToRange(self, segment):
        """
        Parameters
        ----------
        segment : :class:`pyannote.base.segment.Segment`

        Returns
        -------
        i, n : int

        """
        raise NotImplementedError('Missing method "_segmentToRange".')

    def _rangeToSegment(self, i, n):
        """
        Parameters
        ----------
        i, n : int

        Returns
        -------
        segment : :class:`pyannote.base.segment.Segment`

        """
        raise NotImplementedError('Missing method "_rangeToSegment".')

    def __call__(self, subset, mode='loose'):
        """
        Use expression 'feature(subset)'

        Parameters
        ----------
        subset : :class:`pyannote.base.segment.Segment` or
                 :class:`pyannote.base.timeline.Timeline`

        Returns
        -------
        data : numpy array

        """

        if not isinstance(subset, (Segment, Timeline)):
            raise TypeError('')

        if isinstance(subset, Segment):
            i, n = self._segmentToRange(subset)
            indices = range(i, i + n)

        elif isinstance(subset, Timeline):
            indices = []
            for segment in subset.coverage():
                i, n = self._segmentToRange(segment)
                indices += range(i, i + n)

        return np.take(self.__data, indices, axis=0, out=None, mode='clip')


class PeriodicPrecomputedFeature(BasePrecomputedSegmentFeature):

    """'Sliding window'-driven precomputed feature iterator.

    Parameters
    ----------
    data : numpy array
        Feature vectors stored in such a way that data[i] is ith feature vector.
    sliding_window : :class:`SlidingWindow`
        Sliding window. Its length must correspond to `data` length
        (or it can be infinite -- ie. sliding_window.end = None)
    uri : string, optional
        name of (audio or video) described resource

    Examples
    --------
        >>> data = ...
        >>> sliding_window = SlidingWindow( ... )
        >>> feature_iterator = PeriodicPrecomputedFeature(data, sliding_window)
        >>> for segment, feature_vector in feature_iterator:
        ...     pass

    """

    def __init__(self, data, sliding_window, uri=None):

        super(PeriodicPrecomputedFeature, self).__init__(
            data, sliding_window, uri=uri
        )

    def __get_sliding_window(self):
        return self._segment_iterator
    sliding_window = property(fget=__get_sliding_window)

    def _segmentToRange(self, segment):
        """
        Parameters
        ----------
        segment : :class:`pyannote.base.segment.Segment`

        Returns
        -------
        i, n : int

        """
        return self.sliding_window.segmentToRange(segment)

    def _rangeToSegment(self, i, n):
        """
        Parameters
        ----------
        i, n : int

        Returns
        -------
        segment : :class:`pyannote.base.segment.Segment`

        """
        return self.sliding_window.rangeToSegment(i, n)


class TimelinePrecomputedFeature(BasePrecomputedSegmentFeature):

    """Timeline-driven precomputed feature iterator.

    Parameters
    ----------
    data : numpy array
        Feature vectors stored in such a way that data[i] is ith feature vector.
    timeline : :class:`Timeline`
        Timeline whose length must correspond to `data` length
    uri : string, optional
        name of (audio or video) described resource

    Examples
    --------
        >>> data = ...
        >>> timeline = Timeline( ... )
        >>> feature_iterator = TimelinePrecomputedFeature(data, timeline)
        >>> for segment, feature_vector in feature_iterator:
        ...     pass


    """

    def __init__(self, data, timeline, uri=None):
        super(TimelinePrecomputedFeature, self).__init__(data, timeline,
                                                         uri=uri)

    def __get_timeline(self):
        return self._segment_iterator
    timeline = property(fget=__get_timeline)

    def _segmentToRange(self, segment):
        timeline = self.timeline.crop(segment, mode='loose')
        if timeline:
            # index of first segment in sub-timeline
            first_segment = timeline[0]
            i = self.timeline.index(first_segment)
            # number of segments in sub-timeline
            n = len(timeline)
        else:
            i = 0
            n = 0

        return i, n

    def _rangeToSegment(self, i, n):
        first_segment = self.timeline[i]
        last_segment = self.timeline[i + n]
        return first_segment | last_segment


class SlidingWindowFeature(object):

    """Periodic feature vectors

    Parameters
    ----------
    data : (nSamples, nFeatures) numpy array

    sliding_window : SlidingWindow


    """

    def __init__(self, data, sliding_window):
        super(SlidingWindowFeature, self).__init__()
        self.sliding_window = sliding_window
        self.data = data

    def getNumber(self):
        """Number of feature vectors"""
        return self.data.shape[0]

    def getDimension(self):
        """Dimension of feature vectors"""
        return self.data.shape[1]

    def __getitem__(self, i):
        """Get ith feature vector"""
        return self.data[i]

    def iterfeatures(self, window=False):
        """Feature vector iterator

        Parameters
        ----------
        window : bool, optional
            When True, yield both feature vector and corresponding window.
            Default is to only yield feature vector

        """
        nSamples = self.data.shape[0]
        for i in xrange(nSamples):
            if window:
                yield self.data[i], self.sliding_window[i]
            else:
                yield self.data[i]

    def crop(self, segment):
        """Get set of feature vector for given segment

        Parameters
        ----------
        segment : Segment

        Returns
        -------
        data : numpy array
            (nSamples, nFeatures) numpy array
        """
        firstFrame, frameNumber = self.sliding_window.segmentToRange(segment)
        return self.data[firstFrame:firstFrame + frameNumber]


if __name__ == "__main__":
    import doctest
    doctest.testmod()
