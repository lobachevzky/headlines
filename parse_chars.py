from __future__ import print_function
import argparse
import string
import os
import pickle

import numpy as np
from collections import defaultdict, namedtuple

import shutil

from print_data_stats import print_stats

os.environ["THEANO_FLAGS"] = "device=gpu"
PAD = chr(0)
GO = chr(1)
OOV = chr(2)
DATA_OBJ_FILE = 'data.pkl'


def get_bucket_idx(length):
    return int(np.math.ceil(np.math.log(length, s.bucket_factor)))


""" namedtuples """

Instance = namedtuple("instance", "article title")
Datasets = namedtuple("datasets", "train test")
ConfusionMatrix = namedtuple("confusion_matrix", "f1 precision recall")
Score = namedtuple("score", "value epoch")

class Data:
    def __init__(self):
        vocab = PAD + GO + OOV + '\n ' + string.lowercase + string.punctuation + string.digits
        self.from_int = dict(enumerate(vocab))
        self.to_int = {char: i for i, char in enumerate(vocab)}
        self.nclasses = len(self.to_int)
        self.vocsize = self.nclasses
        self.num_train = 0
        self.PAD, self.GO = PAD, GO
        self.SEP = ''

""" functions """


def to_array(string, doc_type):
    length = len(string) + 1
    size = s.bucket_factor ** get_bucket_idx(length)
    if doc_type == 'title':
        string = GO + string
    sentence_vector = np.zeros(size, dtype='int32') + data.to_int[PAD]
    for i, char in enumerate(string):
        if char not in data.to_int:
            char = OOV
        char_code = data.to_int[char]
        sentence_vector[i] = char_code
    return sentence_vector


def fill_buckets(instances):
    lengths = map(len, instances)
    assert lengths[0] == lengths[1]
    buckets = defaultdict(list)
    for article, title in zip(*instances):
        bucket_id = tuple(map(get_bucket_idx, [article.size, title.size]))
        buckets[bucket_id].append(Instance(article, title))
    return buckets


def save_buckets(num_train, buckets, set_name):
    print('Bucket allocation:')
    print('\nNumber of buckets: ', len(buckets))
    for key in buckets:
        bucket = buckets[key]
        size_bucket = len(bucket)

        # we only keep buckets with more than 10 instances for optimization
        if size_bucket < 10:
            num_train -= size_bucket
        else:
            bucket_folder = os.path.join(set_name, '-'.join(map(str, key)))
            if not os.path.exists(bucket_folder):
                os.mkdir(bucket_folder)
            print(key, size_bucket)
            instance = Instance(*map(np.array, zip(*bucket)))
            for doc_type in Instance._fields:
                filepath = os.path.join(bucket_folder, doc_type)
                np.save(filepath, instance.__getattribute__(doc_type))


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--num_instances', type=int, default=100000,
                        help='number of instances to use in Jeopardy dataset')
    parser.add_argument('--data_dir', type=str, default='/data2/jsedoc/fb_headline_first_sent/',
                        help='path to data')
    parser.add_argument('--bucket_factor', type=int, default=2,
                        help='factor by which to multiply exponent when determining bucket size')

    s = parser.parse_args()
    print(s)
    print('-' * 80)

    data = Data()
    for set_name in Datasets._fields:

        # start fresh every time
        if os.path.exists(set_name):
            shutil.rmtree(set_name)
        os.mkdir(set_name)
        instances = Instance([], [])
        for doc_type in Instance._fields:
            data.num_instances = 0
            data_filename = '.'.join([set_name, doc_type, 'txt'])
            with open(os.path.join(s.data_dir, data_filename)) as data_file:
                for line in data_file:
                    data.num_instances += 1
                    if set_name == 'train':
                        data.num_train += 1
                    array = to_array(line, doc_type)
                    instances.__getattribute__(doc_type).append(array)
                    if data.num_instances == s.num_instances:
                        break

        buckets = fill_buckets(instances)
        save_buckets(data.num_train, buckets, set_name)
        print_stats(data)
        with open(DATA_OBJ_FILE, 'w') as handle:
            pickle.dump(data, handle)
