# Copyright 2024 Edward Hope-Morley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os

log = logging.getLogger('propertree')
FORMAT = ("%(asctime)s %(process)d %(levelname)s %(name)s [-] "  # noqa, pylint: disable=W0622
          "%(message)s")

if not log.hasHandlers():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(FORMAT))
    log.addHandler(handler)

if os.environ.get('PROPERTREE_DEBUG', 'false').lower() == 'true':
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.WARNING)
