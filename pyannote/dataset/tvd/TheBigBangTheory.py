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


from pyannote.dataset.tvd import TVD, Season
from pyannote import Unknown


class TheBigBangTheory(TVD):

    SERIES = 'TheBigBangTheory'

    # ==== Labels provided by KIT manual annotations =========
    # Main characters
    MANUAL_MAIN_CHAR = [
        'leonard', 'sheldon', 'penny', 'howard', 'raj']
    # Other characters
    MANUAL_OTHR_CHAR = ['other']
    # Other audio labels
    MANUAL_OTHR_LBLS = [
        'laugh', 'sil', 'titlesong', 'ns', 'laughclap', 'mix']
    # ========================================================

    def __init__(self, tvd_dir=None):
        super(TheBigBangTheory, self).__init__(tvd_dir=tvd_dir)

    def get_season(self, season):
        return Season(self.__class__.__name__, season)

    def get_reference_speech_nonspeech(self, episode, language=None):
        """Get reference (manual, KIT) speech activity detection

        Parameters
        ----------
        episode : pyannote.dataset.tvd.Episode
        language : str, optional, not supported

        Returns
        -------
        sad : Annotation
            Speech activity detection. Contains 2 labels
            ('speech' and 'non_speech')
        """

        kit = self.get_annotation(episode, 'KIT_sid_manual', 'mdtm')

        translation = {}
        for label in self.MANUAL_MAIN_CHAR + self.MANUAL_OTHR_CHAR:
            translation[label] = 'speech'
        for label in self.MANUAL_OTHR_LBLS:
            translation[label] = 'non_speech'

        return kit % translation

    def get_reference_speech_activity_detection(self, episode, language=None):
        sns = self.get_reference_speech_nonspeech(episode, language=language)
        return sns.subset(set(['speech'])).get_timeline()

    def get_reference_speaker_identification(self, episode, language=None):
        """Get reference (manual, KIT) speaker identification

        Parameters
        ----------
        episode : pyannote.dataset.tvd.Episode
        language : str, optional, not supported

        Returns
        -------
        sid : Annotation
            Annotated speech turns. Contains 6 different labels
            (5 main characters + one Unknown instance for all other characters)
        """

        # load raw manual audio annotation
        kit = self.get_annotation(episode, 'KIT_sid_manual', 'mdtm')
        # only keep speaker-related labels (5 mains characters + other)
        kit = kit.subset(set(self.MANUAL_MAIN_CHAR + self.MANUAL_OTHR_CHAR))
        # rename other to Unknown
        kit = kit % {'other': Unknown()}
        return kit

    def get_reference_speaker_segmentation(self, episode, language=None):
        """Get reference (manual, KIT) speech turn segmentation

        Parameters
        ----------
        episode : pyannote.dataset.tvd.Episode
        language : str, optional, not supported

        Returns
        -------
        segmentation : Annotation
            Speech turns with one Unknown instance label per track.
        """
        sid = self.get_reference_speaker_identification(episode)
        return sid.anonymize_tracks()
