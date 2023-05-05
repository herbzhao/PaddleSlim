# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
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

import argparse
import os
import sys

import numpy as np
import paddle
from paddleslim.common import load_config as load_slim_config
from post_process import PPYOLOEPostProcess
from ppdet.core.workspace import create, load_config, merge_config
from ppdet.metrics import COCOMetric


def argsparser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--config_path',
        type=str,
        default=None,
        help="path of compression strategy config.",
        required=True)
    parser.add_argument(
        '--devices',
        type=str,
        default='gpu',
        help="which device used to compress.")

    return parser


def eval():

    place = paddle.CUDAPlace(0) if FLAGS.devices == 'gpu' else paddle.CPUPlace()
    exe = paddle.static.Executor(place)

    val_program, feed_target_names, fetch_targets = paddle.static.load_inference_model(
        global_config["model_dir"].rstrip('/'),
        exe,
        model_filename=global_config["model_filename"],
        params_filename=global_config["params_filename"])
    print('Loaded model from: {}'.format(global_config["model_dir"]))

    metric = global_config['metric']
    for batch_id, data in enumerate(val_loader):
        data_all = {k: np.array(v) for k, v in data.items()}
        data_input = {}
        for k, v in data.items():
            if k in feed_target_names:
                data_input[k] = np.array(v)

        outs = exe.run(val_program,
                       feed=data_input,
                       fetch_list=fetch_targets,
                       return_numpy=False)
        res = {}
        if 'exclude_nms' in global_config and global_config['exclude_nms']:
            postprocess = PPYOLOEPostProcess(
                score_threshold=0.01, nms_threshold=0.6)
            res = postprocess(np.array(outs[0]), data_all['scale_factor'])
        else:
            for out in outs:
                v = np.array(out)
                if len(v.shape) > 1:
                    res['bbox'] = v
                else:
                    res['bbox_num'] = v
        metric.update(data_all, res)
        if batch_id % 100 == 0:
            print('Eval iter:', batch_id)
    metric.accumulate()
    metric.log()
    metric.reset()


def main():
    global global_config
    all_config = load_slim_config(FLAGS.config_path)
    global_config = all_config["Global"]
    reader_cfg = load_config(global_config['reader_config'])

    dataset = reader_cfg['EvalDataset']
    global val_loader
    val_loader = create('EvalReader')(reader_cfg['EvalDataset'],
                                      reader_cfg['worker_num'],
                                      return_list=True)
    metric = None
    clsid2catid = {v: k for k, v in dataset.catid2clsid.items()}
    anno_file = dataset.get_anno()
    metric = COCOMetric(
        anno_file=anno_file, clsid2catid=clsid2catid, IouType='bbox')
    global_config['metric'] = metric

    eval()


if __name__ == '__main__':
    paddle.enable_static()
    parser = argsparser()
    FLAGS = parser.parse_args()
    assert FLAGS.devices in ['cpu', 'gpu', 'xpu', 'npu']
    paddle.set_device(FLAGS.devices)

    main()
