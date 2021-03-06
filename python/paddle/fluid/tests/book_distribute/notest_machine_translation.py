#  Copyright (c) 2018 PaddlePaddle Authors. All Rights Reserved.
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

import numpy as np
import paddle.v2 as paddle
import paddle.fluid as fluid
import paddle.fluid.core as core
import paddle.fluid.framework as framework
import paddle.fluid.layers as layers
from paddle.fluid.executor import Executor
import os

dict_size = 30000
source_dict_dim = target_dict_dim = dict_size
src_dict, trg_dict = paddle.dataset.wmt14.get_dict(dict_size)
hidden_dim = 32
word_dim = 16
IS_SPARSE = True
batch_size = 10
max_length = 50
topk_size = 50
trg_dic_size = 10000

decoder_size = hidden_dim


def encoder_decoder():
    # encoder
    src_word_id = layers.data(
        name="src_word_id", shape=[1], dtype='int64', lod_level=1)
    src_embedding = layers.embedding(
        input=src_word_id,
        size=[dict_size, word_dim],
        dtype='float32',
        is_sparse=IS_SPARSE,
        param_attr=fluid.ParamAttr(name='vemb'))

    fc1 = fluid.layers.fc(input=src_embedding, size=hidden_dim * 4, act='tanh')
    lstm_hidden0, lstm_0 = layers.dynamic_lstm(input=fc1, size=hidden_dim * 4)
    encoder_out = layers.sequence_last_step(input=lstm_hidden0)

    # decoder
    trg_language_word = layers.data(
        name="target_language_word", shape=[1], dtype='int64', lod_level=1)
    trg_embedding = layers.embedding(
        input=trg_language_word,
        size=[dict_size, word_dim],
        dtype='float32',
        is_sparse=IS_SPARSE,
        param_attr=fluid.ParamAttr(name='vemb'))

    rnn = fluid.layers.DynamicRNN()
    with rnn.block():
        current_word = rnn.step_input(trg_embedding)
        mem = rnn.memory(init=encoder_out)
        fc1 = fluid.layers.fc(input=[current_word, mem],
                              size=decoder_size,
                              act='tanh')
        out = fluid.layers.fc(input=fc1, size=target_dict_dim, act='softmax')
        rnn.update_memory(mem, fc1)
        rnn.output(out)

    return rnn()


def to_lodtensor(data, place):
    seq_lens = [len(seq) for seq in data]
    cur_len = 0
    lod = [cur_len]
    for l in seq_lens:
        cur_len += l
        lod.append(cur_len)
    flattened_data = np.concatenate(data, axis=0).astype("int64")
    flattened_data = flattened_data.reshape([len(flattened_data), 1])
    res = core.LoDTensor()
    res.set(flattened_data, place)
    res.set_lod([lod])
    return res


def main():
    rnn_out = encoder_decoder()
    label = layers.data(
        name="target_language_next_word", shape=[1], dtype='int64', lod_level=1)
    cost = layers.cross_entropy(input=rnn_out, label=label)
    avg_cost = fluid.layers.mean(x=cost)

    optimizer = fluid.optimizer.Adagrad(learning_rate=1e-4)
    optimize_ops, params_grads = optimizer.minimize(avg_cost)

    train_data = paddle.batch(
        paddle.reader.shuffle(
            paddle.dataset.wmt14.train(dict_size), buf_size=1000),
        batch_size=batch_size)

    place = core.CPUPlace()
    exe = Executor(place)

    t = fluid.DistributeTranspiler()
    # all parameter server endpoints list for spliting parameters
    pserver_endpoints = os.getenv("PSERVERS")
    # server endpoint for current node
    current_endpoint = os.getenv("SERVER_ENDPOINT")
    # run as trainer or parameter server
    training_role = os.getenv(
        "TRAINING_ROLE", "TRAINER")  # get the training role: trainer/pserver
    t.transpile(
        optimize_ops, params_grads, pservers=pserver_endpoints, trainers=2)

    if training_role == "PSERVER":
        if not current_endpoint:
            print("need env SERVER_ENDPOINT")
            exit(1)
        pserver_prog = t.get_pserver_program(current_endpoint)
        pserver_startup = t.get_startup_program(current_endpoint, pserver_prog)
        exe.run(pserver_startup)
        exe.run(pserver_prog)
    elif training_role == "TRAINER":
        trainer_prog = t.get_trainer_program()
        exe.run(framework.default_startup_program())

        batch_id = 0
        for pass_id in xrange(2):
            for data in train_data():
                word_data = to_lodtensor(map(lambda x: x[0], data), place)
                trg_word = to_lodtensor(map(lambda x: x[1], data), place)
                trg_word_next = to_lodtensor(map(lambda x: x[2], data), place)
                outs = exe.run(trainer_prog,
                               feed={
                                   'src_word_id': word_data,
                                   'target_language_word': trg_word,
                                   'target_language_next_word': trg_word_next
                               },
                               fetch_list=[avg_cost])
                avg_cost_val = np.array(outs[0])
                print('pass_id=' + str(pass_id) + ' batch=' + str(batch_id) +
                      " avg_cost=" + str(avg_cost_val))
                if batch_id > 3:
                    exit(0)
                batch_id += 1
    else:
        print("environment var TRAINER_ROLE should be TRAINER os PSERVER")


if __name__ == '__main__':
    main()
