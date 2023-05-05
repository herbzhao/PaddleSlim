#   Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserve.
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

from __future__ import absolute_import

from .analysis import *
from .compressor import *
from .config_helpers import *
from .strategy_config import *
from .utils import *

__all__ = [
    "AutoCompression", "QuantAware", "QuantPost", "Distillation",
    "MultiTeacherDistillation", "HyperParameterOptimization", "Prune",
    "UnstructurePrune", "ProgramInfo", "TrainConfig",
    "predict_compressed_model", "analysis_prune"
]
