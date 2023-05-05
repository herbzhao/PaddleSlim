import logging

import numpy as np
import paddle
from paddleslim.common import get_logger

from .filter_pruner import FilterPruner
from .pruning_plan import *
from .var_group import *

__all__ = ['L2NormFilterPruner']

_logger = get_logger(__name__, logging.INFO)


class L2NormFilterPruner(FilterPruner):
    def __init__(self,
                 model,
                 inputs,
                 sen_file=None,
                 opt=None,
                 skip_leaves=True,
                 prune_type='conv',
                 input_dtype="float32",
                 num_head=-1):
        super(L2NormFilterPruner, self).__init__(
            model,
            inputs,
            sen_file=sen_file,
            opt=opt,
            skip_leaves=skip_leaves,
            prune_type=prune_type,
            input_dtype=input_dtype,
            num_head=num_head)

    def cal_mask(self, pruned_ratio, collection, num_head=-1):
        var_name = collection.master_name
        pruned_axis = collection.master_axis
        value = collection.values[var_name]

        if (value.shape[1] == 3 * value.shape[0] or
                value.shape[1] == value.shape[0]) and num_head != -1:
            num_head = num_head
            assert value.size % (
                value.shape[0] * num_head
            ) == 0, "weight shape must be divisible by num_head"
            _logger.debug(
                "fused-qkv or query/key/value weight detected, we will prune on num_head: {} -> {}"
                .format(num_head, int(num_head * (1 - pruned_ratio))))
        else:
            num_head = -1

        groups = 1
        for _detail in collection.all_pruning_details():
            assert (isinstance(_detail.axis, int))
            if _detail.axis == 1:
                _groups = _detail.op.attr('groups')
                if _groups is not None and _groups > 1:
                    groups = _groups
                    break

        if num_head != -1:
            k = int(value.size / value.shape[0] / num_head)
            value = value.reshape((value.shape[0], num_head, k))

        reduce_dims = [i for i in range(len(value.shape)) if i != pruned_axis]
        scores = np.sqrt(np.sum(np.square(value), axis=tuple(reduce_dims)))
        if groups > 1:
            scores = scores.reshape([groups, -1])
            scores = np.mean(scores, axis=1)

        sorted_idx = scores.argsort()
        pruned_num = int(round(len(sorted_idx) * pruned_ratio))
        pruned_num = min(len(sorted_idx) - 1, pruned_num)
        pruned_idx = sorted_idx[:pruned_num]

        mask_shape = [value.shape[pruned_axis]]
        mask = np.ones(mask_shape, dtype="int32")
        if groups > 1:
            mask = mask.reshape([groups, -1])
        mask[pruned_idx] = 0

        if num_head != -1:
            mask = np.repeat(mask[:, np.newaxis], k, axis=1)
            return mask.flatten()

        return mask.reshape(mask_shape)
