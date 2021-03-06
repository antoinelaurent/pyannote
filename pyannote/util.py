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

import warnings
import traceback
from decorator import decorator


def deprecated(replacedByFunc):

    def _d(f, *args, **kwargs):

        warnings.warn(
            '"%s" is deprecated. use "%s" instead.' % (
                f.func_name, replacedByFunc.__name__)
        )
        traceback.print_stack(limit=3)
        return f(*args, **kwargs)

    return decorator(_d)
