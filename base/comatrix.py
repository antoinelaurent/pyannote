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

import numpy as np
import warnings

class CoMatrix(object):
    
    def __init__(self, ilabels, jlabels, Mij, default=0.):
        
        super(CoMatrix, self).__init__()
        
        self.__ilabels = ilabels
        self.__jlabels = jlabels
        self.__Mij = np.array(Mij).reshape((len(ilabels), len(jlabels)))
        
        self.__label2i = {ilabel:i for i, ilabel in enumerate(ilabels)}
        self.__label2j = {jlabel:i for i, jlabel in enumerate(jlabels)}
        
        self.__default = default
    
    # ------------------------------------------------------------------- #
    
    def __get_default(self):
        return self.__default
    default = property(fget=__get_default, \
                       fset=None, \
                       fdel=None, \
                       doc="Default value.")
    
    # ------------------------------------------------------------------- #

    def __get_T(self): 
        return CoMatrix(self.__jlabels, self.__ilabels, self.__Mij.T)
    T = property(fget=__get_T, \
                     fset=None, \
                     fdel=None, \
                     doc="Matrix transposition.")
    
    def __get_shape(self):
        return self.__Mij.shape
    shape = property(fget=__get_shape, \
                     fset=None, \
                     fdel=None, \
                     doc="Matrix shape.")

    # ------------------------------------------------------------------- #

    def __get_M(self):
        return self.__Mij
    M = property(fget=__get_M, \
                 fset=None, \
                 fdel=None, \
                 doc="numpy matrix.")
                 
    def __get_labels(self):
        return self.__ilabels, self.__jlabels
    labels = property(fget=__get_labels, \
                      fset=None, \
                      fdel=None,
                      doc="Matrix labels.")
    
    # =================================================================== #

    def __getitem__(self, key):
        """
        """
        if isinstance(key, tuple) and len(key) == 2:
            
            ilabel = key[0]
            jlabel = key[1]
            
            if ilabel in self.__label2i and \
               jlabel in self.__label2j:
                return self.__Mij[self.__label2i[ilabel], \
                                  self.__label2j[jlabel]]
            else:
                return self.default
        else:
            raise KeyError('')
    
    # =================================================================== #
    
    def __add_ilabel(self, ilabel):
        n, m = self.shape
        self.__ilabels.append(ilabel)
        self.__label2i[ilabel] = n
        self.__Mij = np.append(self.__Mij, \
                               self.default*np.ones((1, m)), \
                               axis=0)

    # ------------------------------------------------------------------- #

    def __add_jlabel(self, jlabel):
        n, m = self.shape
        self.__jlabels.append(jlabel)
        self.__label2j[jlabel] = m
        self.__Mij = np.append(self.__Mij, \
                               self.default*np.ones((n, 1)), \
                               axis=1)
        
    # ------------------------------------------------------------------- #

    def __setitem__(self, key, value):
        """
        """
        if isinstance(key, tuple) and len(key) == 2:
            ilabel = key[0]
            jlabel = key[1]
            
            if ilabel not in self.__label2i:
                self.__add_ilabel(ilabel)
            if jlabel not in self.__label2j:
                self.__add_jlabel(jlabel)
            
            i = self.__label2i[ilabel]
            j = self.__label2j[jlabel]
            self.__Mij[i, j] = value
        
        else:
            raise KeyError('')
    
    # =================================================================== #
    
    def __delitem__(self, key):
        raise NotImplementedError('')
    
    # =================================================================== #
    
    # def __call__(self, ilabel):
    #     if ilabel in self.__label2i:
    #         i = self.__label2i[ilabel]
    #         return {jlabel: self.__Mij[i, self.__label2j[jlabel]] \
    #                 for jlabel in self.__label2j}
    #     else:
    #         return {}
    
    # =================================================================== #
    
    def iter_ilabels(self, index=False):
        for ilabel in self.__ilabels:
            if index:
                yield self.__label2i[ilabel], ilabel
            else:
                yield ilabel
    
    def iter_jlabels(self, index=False):
        for jlabel in self.__jlabels:
            if index:
                yield self.__label2j[jlabel], jlabel
            else:
                yield jlabel
    
    def iter_pairs(self, data=False):
        for ilabel in self.__ilabels:
            for jlabel in self.__jlabels:
                if data:
                    yield ilabel, jlabel, self[ilabel, jlabel]
                else:
                    yield ilabel, jlabel
    
    # ------------------------------------------------------------------- #
    
    def copy(self):
        ilabels, jlabels = self.labels
        C = CoMatrix(list(ilabels), \
                     list(jlabels), \
                     np.copy(self.M), \
                     default=self.default)
        return C
        
    # ------------------------------------------------------------------- #

    def __iadd__(self, other):

        if self.default != other.default:
            warnings.warn('Incompatible default value. Uses %g.' % self.default)

        for ilabel, jlabel, value in other.iter_pairs(data=True):
            self[ilabel, jlabel] += value
        
        return self 

    # ------------------------------------------------------------------- #

    def __add__(self, other):
        C = self.copy()        
        C += other
        return C
    
    # =================================================================== #
    
    
    # =================================================================== #
    
    def argmin(self, threshold=None, axis=None):
        """
        :param threshold: threshold on minimum value
        :type threshold: float
        
        :returns: list of label pairs corresponding to minimum value in matrix.
        In case :data:`threshold` is provided and is smaller than minimum value,
        then, returns an empty list.
        """
        if axis == 0:
            pairs = {}
            for i, ilabel in self.iter_ilabels(index=True):
                M = self.M[i,:]
                m = np.min(M)
                if threshold is None or m < threshold:
                    pairs[ilabel] = [self.__jlabels[j] for j in np.argmin(M)]
                else:
                    pairs[ilabel] = []
            return pairs
        elif axis == 1:
            pairs = {}
            for j, jlabel in self.iter_jlabels(index=True):
                M = self.M[:,j]
                m = np.min(M)
                if threshold is None or m < threshold:
                    pairs[jlabel] = [self.__ilabels[i] for i in np.argmin(M)]
                else:
                    pairs[jlabel] = []
            return pairs
        else:
            m = np.min(self.M)
            if (threshold is None) or (m < threshold):
                pairs = np.argwhere(self.M == m)
            else:
                pairs = []
            return [(self.__ilabels[i], self.__jlabels[j]) for i, j in pairs]

    # ------------------------------------------------------------------- #

    def argmax(self, axis=None, threshold=None):
        """
        :param threshold: threshold on maximum value
        :type threshold: float
        
        :returns: list of label pairs corresponding to maximum value in matrix.
        In case :data:`threshold` is provided and is higher than maximum value,
        then, returns an empty list.
        """
        
        if axis == 0:
            pairs = {}
            for i, ilabel in self.iter_ilabels(index=True):
                M = self.M[i,:]
                m = np.max(M)
                if threshold is None or m > threshold:
                    pairs[ilabel] = [self.__jlabels[j[0]] \
                                    for j in np.argwhere(M == m)]
                else:
                    pairs[ilabel] = []
            return pairs
        elif axis == 1:
            pairs = {}
            for j, jlabel in self.iter_jlabels(index=True):
                M = self.M[:,j]
                m = np.max(M)
                if threshold is None or m > threshold:
                    pairs[jlabel] = [self.__ilabels[i[0]] \
                                     for i in np.argwhere(M == m)]
                else:
                    pairs[jlabel] = []
            return pairs
        else:
            m = np.max(self.M)
            if (threshold is None) or (m > threshold):
                pairs = np.argwhere(self.M == m)
            else:
                pairs = []
            return [(self.__ilabels[i], self.__jlabels[j]) for i, j in pairs]
    
    # =================================================================== #

    def __str__(self):
        
        ilabels, jlabels = self.labels
        
        len_i = max([len(label) for label in ilabels])
        len_j = max([len(label) for label in jlabels])
        
        fmt_label_i = "%%%ds" % len_i 
        fmt_label_j = "%%%ds" % len_j
        fmt_value = "%%%d.1f" % len_j
        
        string = fmt_label_i % " "
        string += " "
        string += " ".join([fmt_label_j % j for j in jlabels])
        
        for i in ilabels:
            string += "\n"
            string += fmt_label_i % i
            string += " "
            string += " ".join([fmt_value % self[i, j] for j in jlabels])
        
        return string
            

class Confusion(CoMatrix):
    """
    Confusion matrix between two (ID-based) annotations
    
    :param I: first (ID-based) annotation
    :type I: :class:`TrackIDAnnotation`

    :param J: second (ID-based) annotation
    :type J: :class:`TrackIDAnnotation`
    
    >>> M = Confusion(A, B)

    Get total confusion duration (in seconds) between id_A and id_B::
    
    >>> confusion = M[id_A, id_B]
    
    Get confusion dictionary for id_A::
    
    >>> confusions = M(id_A)
    
    
    """
    def __init__(self, I, J, normalize=False):
                
        n_i = len(I.IDs)
        n_j = len(J.IDs)
        Mij = np.zeros((n_i, n_j))
        super(Confusion, self).__init__(I.IDs, J.IDs, Mij, default=0.)
        
        if normalize:
            raise ValueError('normalize = True no longer supported ')
            # iduration = np.zeros((n_i,))
        
        ilabels, jlabels = self.labels
        
        for i, ilabel in self.iter_ilabels(index=True):
            i_coverage = I(ilabel).timeline.coverage()
            # if normalize:
            #     iduration[i] = i_coverage.duration()
            
            for j, jlabel in self.iter_jlabels(index=True):
                j_coverage = J(jlabel).timeline.coverage()
                self[ilabel, jlabel] = i_coverage(j_coverage, \
                                              mode='intersection').duration()
        
        # if normalize:
        #     for i in range(n_i):
        #         self[ilabel, jlabel]
        #         self.__Mij[i, :] = self.__Mij[i, :] / iduration[i]

class AutoConfusion(Confusion):
    """
    Auto confusion matrix 
    
    :param I: (ID-based) annotation
    :type I: :class:`TrackIDAnnotation`

    :param neighborhood:
    :type neighborhood: 
    
    >>> M = AutoConfusion(A, neighborhood=10)

    Get total confusion duration (in seconds) between id_A and id_B::
    
    >>> confusion = M[id_A, id_B]
    
    Get confusion dictionary for id_A::
    
    >>> confusions = M(id_A)
    
    
    """
    def __init__(self, I, neighborhood=0., normalize=False):
        
        map_func = lambda segment : neighborhood << segment >> neighborhood
        
        xI = I.toTrackIDAnnotation().copy(map_func=map_func)        
        super(AutoConfusion, self).__init__(xI, xI, normalize=normalize)
            
        
