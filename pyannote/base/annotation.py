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

# Ignore Banyan warning
import warnings
warnings.filterwarnings(
    "ignore",
    "Key-type optimization unimplemented with callback metadata.",
    Warning,
    "pyannote.base.annotation"
)

from pyannote.util import deprecated


from segment import Segment
from timeline import Timeline
from banyan import SortedDict
from interval_tree import TimelineUpdator
from mapping import Mapping, ManyToOneMapping
import operator
import numpy as np
from pyannote.base import URI, MODALITY, SEGMENT, TRACK, LABEL


class Unknown(object):
    nextID = 0

    @classmethod
    def reset(cls):
        cls.nextID = 0

    @classmethod
    def next(cls):
        cls.nextID += 1
        return cls.nextID

    def __init__(self, format='Inconnu_%05d'):
        super(Unknown, self).__init__()
        self.ID = Unknown.next()
        self.format = format

    def __str__(self):
        return self.format % self.ID

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(self.ID)

    def __eq__(self, other):
        if isinstance(other, Unknown):
            return self.ID == other.ID
        else:
            return False


class Annotation(object):
    """
    Parameters
    ----------
    uri : string, optional
        uniform resource identifier of annotated document
    modality : string, optional
        name of annotated modality

    Returns
    -------
    annotation : BaseAnnotation
        New empty annotation
    """

    @classmethod
    def from_df(cls, df, uri=None, modality=None, aggfunc=np.mean):
        """

        Parameters
        ----------
        df : DataFrame
            Must contain the following columns: 'segment', 'track' and 'label'
        uri : str, optional
            Resource identifier
        modality : str, optional
            Modality
        aggfunc : func
            Value aggregation function in case of duplicate (segment, track,
            label) tuples

        Returns
        -------

        """
        annotation = cls(uri=uri, modality=modality)
        for _, (segment, track, label) in df[[SEGMENT, TRACK, LABEL]].iterrows():
            annotation[segment, track] = label
        return annotation

    def __init__(self, uri=None, modality=None):
        super(Annotation, self).__init__()

        self.uri = uri
        self.modality = modality

        # sorted dictionary
        # keys: annotated segments
        # values: {track: label} dictionary
        self._tracks = SortedDict(key_type=(float, float),
                                  updator=TimelineUpdator)

        # dictionary
        # key: label
        # value: timeline
        self._labels = {}
        self._labelNeedsUpdate = {}

        self._timelineNeedsUpdate = True

    def _updateLabels(self):

        # (re-)initialize changed label timeline
        for l, needsUpdate in self._labelNeedsUpdate.iteritems():
            if needsUpdate:
                self._labels[l] = Timeline(uri=self.uri)

        # fill changed label timeline
        for segment, track, l in self.itertracks(label=True):
            if self._labelNeedsUpdate[l]:
                self._labels[l].add(segment)

        self._labelNeedsUpdate = {l: False for l in self._labels}

        # remove "ghost" labels (i.e. label with empty timeline)
        labels = self._labels.keys()
        for l in labels:
            if not self._labels[l]:
                self._labels.pop(l)
                self._labelNeedsUpdate.pop(l)

    def __len__(self):
        """Number of segments"""
        return self._tracks.length()

    def __nonzero__(self):
        return self._tracks.length() > 0

    def itersegments(self):
        """Segment iterator"""
        return iter(self._tracks)

    @deprecated(itersegments)
    def __iter__(self):
        return iter(self._tracks)

    def itertracks(self, label=False):
        for segment, tracks in self._tracks.items():
            for track, lbl in tracks.iteritems():
                if label:
                    yield segment, track, lbl
                else:
                    yield segment, track

    @deprecated(itertracks)
    def iterlabels(self):
        for segment, tracks in self._tracks.items():
            for track, label in tracks.iteritems():
                yield segment, track, label

    def _updateTimeline(self):
        self._timeline = Timeline(segments=self._tracks, uri=self.uri)
        self._timelineNeedsUpdate = False

    def get_timeline(self):
        """Get timeline made of annotated segments"""
        if self._timelineNeedsUpdate:
            self._updateTimeline()
        return self._timeline

    def __eq__(self, other):
        return self._tracks == other._tracks

    def __ne__(self, other):
        return self._tracks != other._tracks

    def __contains__(self, included):
        """Inclusion

        Use expression 'segment in annotation' or 'timeline in annotation'

        Parameters
        ----------
        included : `Segment` or `Timeline`

        Returns
        -------
        contains : bool
            True if every segment in `included` exists in annotation
            False otherwise

        """
        return included in self.get_timeline()

    def crop(self, other, mode='intersection'):
        """Crop annotation

        Parameters
        ----------
        other : `Segment` or `Timeline`

        mode : {'strict', 'loose', 'intersection'}
            In 'strict' mode, only segments fully included in focus coverage
            are kept. In 'loose' mode, any intersecting segment is kept
            unchanged. In 'intersection' mode, only intersecting segments are
            kept and replaced by their actual intersection with the focus.

        Returns
        -------
        cropped : Annotation

        Remarks
        -------
        In 'intersection' mode, the best is done to keep the track names
        unchanged. However, in some cases where two original segments are
        cropped into the same resulting segments, conflicting track names are
        modified to make sure no track is lost.
        """

        if isinstance(other, Segment):
            other = Timeline(segments=[other], uri=self.uri)
            cropped = self.crop(other, mode=mode)

        elif isinstance(other, Timeline):

            cropped = self.__class__(uri=self.uri, modality=self.modality)

            if mode == 'loose':
                # TODO
                # update co_iter to yield (segment, tracks), (segment, tracks)
                # instead of segment, segment
                # This would avoid calling ._tracks.get(segment)
                for segment, _ in self.get_timeline().co_iter(other):
                    for track, label in self._tracks[segment].iteritems():
                        cropped[segment, track] = label

            elif mode == 'strict':
                # TODO
                # see above
                for segment, other_segment in self.get_timeline().co_iter(other):
                    if segment in other_segment:
                        for track, label in self._tracks[segment].iteritems():
                            cropped[segment, track] = label

            elif mode == 'intersection':
                # see above
                for segment, other_segment in self.get_timeline().co_iter(other):
                    intersection = segment & other_segment
                    for track, label in self._tracks[segment].iteritems():
                        track = cropped.new_track(intersection,
                                                  candidate=track)
                        cropped[intersection, track] = label

            else:
                raise NotImplementedError("unsupported mode: '%s'" % mode)

        return cropped

    def get_tracks(self, segment):
        """Set of tracks for query segment

        Parameters
        ----------
        segment : `Segment`
            Query segment

        Returns
        -------
        tracks : set
            Set of tracks for query segment
        """
        return set(self._tracks.get(segment, {}))

    @deprecated(get_tracks)
    def tracks(self, segment):
        """Set of tracks for query segment

        Parameters
        ----------
        segment : `Segment`
            Query segment

        Returns
        -------
        tracks : set
            Set of tracks for query segment
        """
        return set(self._tracks.get(segment, {}))


    def has_track(self, segment, track):
        """Check whether a given track exists

        Parameters
        ----------
        segment : `Segment`
            Query segment
        track :
            Query track

        Returns
        -------
        exists : bool
            True if track exists for segment
        """
        return track in self._tracks.get(segment, {})

    def get_track_by_name(self, track):
        """Get all tracks with given name

        Parameters
        ----------
        track : any valid track name
            Requested name track

        Returns
        -------
        tracks : list
            List of (segment, track) tuples
        """
        raise NotImplementedError('')

    def copy(self):

        # create new empty annotation
        copied = self.__class__(uri=self.uri, modality=self.modality)

        # deep copy internal track dictionary
        _tracks = [(key, dict(value)) for (key, value) in self._tracks.items()]
        copied._tracks = SortedDict(items=_tracks,
                                    key_type=(float, float),
                                    updator=TimelineUpdator)

        # deep copy internal label timelines
        _labels = {key: timeline.copy()
                   for (key, timeline) in self._labels.iteritems()}
        copied._labels = _labels

        # deep copy need-update indicator
        copied._labelNeedsUpdate = dict(self._labelNeedsUpdate)

        copied._timelineNeedsUpdate = self._timelineNeedsUpdate

        return copied

    def retrack(self):
        """
        """
        retracked = self.__class__(uri=self.uri, modality=self.modality)
        for n, (s, _, label) in enumerate(self.itertracks(label=True)):
            retracked[s, n] = label
        return retracked

    def new_track(self, segment, candidate=None, prefix=None):
        """Track name generator

        Parameters
        ----------
        segment : Segment
        prefix : str, optional
        candidate : any valid track name

        Returns
        -------
        track : str
            New track name
        """

        # obtain list of existing tracks for segment
        existing_tracks = set(self._tracks.get(segment, {}))

        # if candidate is provided, check whether it already exists
        # in case it does not, use it
        if candidate and (candidate not in existing_tracks):
            return candidate

        # no candidate was provided or the provided candidate already exists
        # we need to create a brand new one

        # by default (if prefix is not provided)
        # use modality as prefix (eg. speaker1, speaker2, ...)
        if prefix is None:
            prefix = '' if self.modality is None else str(self.modality)

        # find first non-existing track name for segment
        # eg. if speaker1 exists, try speaker2, then speaker3, ...
        count = 1
        while ('%s%d' % (prefix, count)) in existing_tracks:
            count += 1

        # return first non-existing track name
        return '%s%d' % (prefix, count)

    def __str__(self):
        """Human-friendly representation"""
        # TODO: use pandas.DataFrame
        return "\n".join(["%s %s %s" % (s, t, l)
                          for s, t, l in self.itertracks(label=True)])

    def __delitem__(self, key):

        # del annotation[segment]
        if isinstance(key, Segment):

            # Pop segment out of dictionary
            # and get corresponding tracks
            # Raises KeyError if segment does not exist
            tracks = self._tracks.pop(key)

            # mark timeline as modified
            self._timelineNeedsUpdate = True

            # mark every label in tracks as modified
            for track, label in tracks.iteritems():
                self._labelNeedsUpdate[label] = True

        # del annotation[segment, track]
        elif isinstance(key, tuple) and len(key) == 2:

            # get segment tracks as dictionary
            # if segment does not exist, get empty dictionary
            # Raises KeyError if segment does not exist
            tracks = self._tracks[key[0]]

            # pop track out of tracks dictionary
            # and get corresponding label
            # Raises KeyError if track does not exist
            label = tracks.pop(key[1])

            # mark label as modified
            self._labelNeedsUpdate[label] = True

            # if tracks dictionary is now empty,
            # remove segment as well
            if not tracks:
                self._tracks.pop(key[0])
                self._timelineNeedsUpdate = True

        else:
            raise KeyError('')

    # label = annotation[segment, track]
    def __getitem__(self, key):
        return self._tracks[key[0]][key[1]]

    # annotation[segment, track] = label
    def __setitem__(self, key, label):

        if key[0] not in self._tracks:
            self._tracks[key[0]] = {}
            self._timelineNeedsUpdate = True

        self._tracks[key[0]][key[1]] = label
        self._labelNeedsUpdate[label] = True

    def empty(self):
        return self.__class__(uri=self.uri, modality=self.modality)

    def labels(self, unknown=True):
        """List of labels

        Parameters
        ----------
        unknown : bool, optional
            When False, do not return Unknown instances
            When True, return any label (even Unknown instances)

        Returns
        -------
        labels : list
            Sorted list of labels

        Remarks
        -------
            Labels are sorted based on their string representation.
        """

        if any([lnu for lnu in self._labelNeedsUpdate.values()]):
            self._updateLabels()

        labels = sorted(self._labels, key=str)

        if not unknown:
            labels = [l for l in labels if not isinstance(l, Unknown)]

        return labels

    def get_labels(self, segment, unknown=True, unique=True):
        """Local set of labels

        Parameters
        ----------
        segment : Segment
            Segments to get label from.
        unknown : bool, optional
            When False, do not return Unknown instances
            When True, return any label (even Unknown instances)
        unique : bool, optional
            When False, return the list of (possibly repeated) labels.
            When True (default), return the set of labels
        Returns
        -------
        labels : set
            Set of labels for `segment` if it exists, empty set otherwise.

        Examples
        --------

            >>> annotation = Annotation()
            >>> segment = Segment(0, 2)
            >>> annotation[segment, 'speaker1'] = 'Bernard'
            >>> annotation[segment, 'speaker2'] = 'John'
            >>> print sorted(annotation.get_labels(segment))
            set(['Bernard', 'John'])
            >>> print annotation.get_labels(Segment(1, 2))
            set([])

        """

        labels = self._tracks.get(segment, {}).values()

        if not unknown:
            labels = [l for l in labels if not isinstance(l, Unknown)]

        if unique:
            labels = set(labels)

        return labels

    def subset(self, labels, invert=False):
        """Annotation subset

        Extract annotation subset based on labels

        Parameters
        ----------
        labels : set
            Set of labels
        invert : bool, optional
            If invert is True, extract all but requested `labels`

        Returns
        -------
        subset : `Annotation`
            Annotation subset.
        """

        if not isinstance(labels, set):
            raise TypeError('labels must be provided as a set of labels.')

        if invert:
            labels = set(self.labels()) - labels
        else:
            labels = labels & set(self.labels())

        sub = self.__class__(uri=self.uri, modality=self.modality)
        for segment, track, label in self.itertracks(label=True):
            if label in labels:
                sub[segment, track] = label

        return sub

    def label_timeline(self, label):
        """Get timeline for a given label

        Parameters
        ----------
        label :

        Returns
        -------
        timeline : :class:`Timeline`
            Timeline made of all segments annotated with `label`

        """
        if self._labelNeedsUpdate[label]:
            self._updateLabels()

            for l, hasChanged in self._labelNeedsUpdate.iteritems():
                if hasChanged:
                    self._labels[l] = Timeline(uri=self.uri)

            for segment, track, l in self.itertracks(label=True):
                if self._labelNeedsUpdate[l]:
                    self._labels[l].add(segment)

            self._labelNeedsUpdate = {l: False for l in self._labels}

        return self._labels[label]

    def label_coverage(self, label):
        return self.label_timeline(label).coverage()

    def label_duration(self, label):
        return self.label_timeline(label).duration()

    def label_chart(self, percent=False):
        """
        Label chart based on their duration

        Parameters
        ----------
        percent : bool, optional
            Return total duration percentage (rather than raw duration)

        Returns
        -------
        chart : (label, duration) iterable
            Sorted from longest to shortest.

        """

        chart = sorted([(label, self.label_duration(label))
                        for label in self.labels()],
                       key=lambda x: x[1], reverse=True)

        if percent:
            total = np.sum([duration for _, duration in chart])
            chart = [(label, duration/total) for (label, duration) in chart]

        return chart

    def argmax(self, segment=None, known_first=False):
        """Get most frequent label


        Parameters
        ----------
        segment : Segment, optional
            Section of annotation where to look for the most frequent label.
            Defaults to whole annotation extent.
        known_first: bool, optional
            If True, artificially reduces the duration of intersection of
            `Unknown` labels so that 'known' labels are returned first.

        Returns
        -------
        label : any existing label or None
            Label with longest intersection

        Examples
        --------

            >>> annotation = Annotation(modality='speaker')
            >>> annotation[Segment(0, 10), 'speaker1'] = 'Alice'
            >>> annotation[Segment(8, 20), 'speaker1'] = 'Bob'
            >>> print "%s is such a talker!" % annotation.argmax()
            Bob is such a talker!
            >>> segment = Segment(22, 23)
            >>> if not annotation.argmax(segment):
            ...    print "No label intersecting %s" % segment
            No label intersection [22 --> 23]

        """

        # if annotation is empty, obviously there is no most frequent label
        if not self:
            return None

        # if segment is not provided, just look for the overall most frequent
        # label (ie. set segment to the extent of the annotation)
        if segment is None:
            segment = self.get_timeline().extent()

        # compute intersection duration for each label
        durations = {lbl: self.label_timeline(lbl).crop(segment, mode='intersection').duration()
                     for lbl in self.labels()}

        # artifically reduce intersection duration of Unknown labels
        # so that 'known' labels are returned first
        if known_first:
            maxduration = max(durations.values())
            for lbl in durations.keys():
                if isinstance(lbl, Unknown):
                    durations[lbl] = durations[lbl] - maxduration

        # find the most frequent label
        label = max(durations.iteritems(), key=operator.itemgetter(1))[0]

        # in case all durations were zero, there is no most frequent label
        return label if durations[label] > 0 else None

    def __rshift__(self, timeline):
        """Tag a timeline

        Use expression 'tagged = annotation >> timeline'

        Shortcut for :
            >>> tagger = DirectTagger()
            >>> tagged = tagger(annotation, timeline)

        Parameters
        ----------
        timeline : :class:`pyannote.base.timeline.Timeline`

        Returns
        -------
        tagged : :class:`pyannote.base.annotation.Annotation`
            Tagged timeline - one track per intersecting label.

        """
        from pyannote.algorithm.tagging import DirectTagger
        if not isinstance(timeline, Timeline):
            raise TypeError('direct tagging (>>) only works with timelines.')
        return DirectTagger()(self, timeline)

    def translate(self, translation):
        """Translate labels

        Parameters
        ----------
        translation: dict or ManyToOneMapping
            Label translation.
            Labels with no associated translation are kept unchanged.

        Returns
        -------
        translated : :class:`Annotation`
            New annotation with translated labels.
        """

        if not (hasattr(translation, '__call__') or
                isinstance(translation, (dict, Mapping))):
            raise TypeError("unsupported operand types(s) for '\%': "
                            "Annotation and %s" % type(translation).__name__)

        # translation is provided as a {'original' --> 'translated'} dict.
        if isinstance(translation, dict):

            # only transform labels that have an actual translation
            # stored in the provided dictionary, keep the others as they are.
            translate = lambda x: translation[x] if x in translation else x

        # translation is provided as a ManyToOneMapping
        elif isinstance(translation, Mapping):

            try:
                translation = ManyToOneMapping.fromMapping(translation)
            except Exception:
                raise ValueError('expected N-to-1 mapping.')

            # only transform labels that actually have a mapping
            # see ManyToOneMapping.__call__() API
            translate = lambda x: translation(x) if translation(x) is not None else x

        else:
            translate = translation

        # create copy
        translated = self.empty()
        for segment, track, label in self.itertracks(label=True):
            translated[segment, track] = translate(label)

        return translated

    def __mod__(self, translation):
        return self.translate(translation)

    def anonymize_labels(self):
        """Anonmyize labels

        Create a new annotation where labels are anonymized, ie. each label
        is replaced by a unique `Unknown` instance.

        Returns
        -------
        anonymized : :class:`Annotation`
            New annotation with anonymized labels.

        """
        translation = {label: Unknown() for label in self.labels()}
        return self % translation

    def anonymize_tracks(self):
        """
        Anonymize tracks

        Create a new annotation where each track is anonymized, i.e. the label
        of each track is set to a unique `Unknown` instance

        Returns
        -------
        anonymized : `Annotation`
            Anonymized annotation

        """
        anonymized = self.empty()
        for s, t, _ in self.itertracks(label=True):
            anonymized[s, t] = Unknown()
        return anonymized

    def smooth(self):
        """Smooth annotation

        Create new annotation where contiguous tracks with same label are
        merged into one longer track.

        Returns
        -------
        annotation : Annotation
            New annotation where contiguous tracks with same label are merged
            into one long track.

        Remarks
        -------
            Track names are lost in the process.

        """

        smoothed = self.empty()

        n = 0
        for label in self.labels():
            coverage = self.label_coverage(label)
            for segment in coverage:
                smoothed[segment, n] = label
                n = n+1

        return smoothed

    def to_json(self):
        annotation = [{SEGMENT: s.to_json(), TRACK: t, LABEL: l}
                      for s, t, l in self.itertracks(label=True)]
        return {URI: self.uri, MODALITY: self.modality, 'tracks': annotation}


if __name__ == "__main__":
    import doctest
    doctest.testmod()
