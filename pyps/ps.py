# -*- coding: utf-8 -*-
from PIL import Image
from layer.img import layer_paste
from cluster import PsdCluster


class PsdModel(object):
    def __init__(self):
        self._size = None
        self._cluster = None
        self._edge_area = None
        self.layers = None

        self.feature_value = 0  # cluster 的特征向量

    @staticmethod
    def _get_safe_region(size: tuple):
        edge = int(max(min(size) * 0.03, 5))  # 获取边缘安全距离，长宽使用相同的安全距离
        return [edge, edge, size[0] - 1 - edge, size[1] - 1 - edge]

    @property
    def edge_area(self):
        if not self._edge_area:
            self._edge_area = self._get_safe_region(self._size)
        return self._edge_area

    def init_by_file(self, filename):
        from e_commerce import mapper
        from utils.common import load_object
        from parse import PsdParser
        from collections import defaultdict
        from layer.model import Layer
        from layer import img

        DEBUG = True
        psd = load_object(filename, with_token=DEBUG)
        inputs, self._size = PsdParser(psd).parse()

        cache = defaultdict(int)
        layers_info = []
        for index, l in enumerate(inputs):
            l_name = l["name"].split("_")[0]
            if l_name == "logo":
                l_name = l["name"] = l_name.upper()

            l_name = mapper(l_name)
            l["group"] = l_name[0]
            l["tag"] = l_name

            # 重名了layer name
            cache[l_name] += 1
            l["name"] = "{}_{}".format(l_name, cache[l_name])

            # 剪切空白区域
            l["data"], area = img.cut_nonzero(l["data"])
            l["xmin"] += area[0]
            l["ymin"] += area[1]
            l["xmax"] = l["xmin"] + l["data"].width - 1
            l["ymax"] = l["ymin"] + l["data"].height - 1
            layers_info.append(Layer(l))
        self.layers = layers_info

    def init_by_layers_info(self, layers_info):
        pass

    def init_by_layers(self, layers):
        pass

    def build_cluster(self):
        self._cluster = PsdCluster(self.layers, size=self.size)
        self._cluster.run()

    @property
    def size(self):
        return self._size

    def set_size(self, size):
        self._size = size

    def compose(self):  # 合成
        image = Image.new('RGBA', self._size, (255, 255, 255, 0))
        for l in self.layers:
            image = layer_paste(image, l.core.data, l.core.xmin, l.core.ymin)

        return image

    @property
    def cluster(self):
        return self._cluster

    def get_cluster_feature(self, clusters_order_name):
        from pyps.cluster.feature import get_cluster_feature
        feature = get_cluster_feature(self.cluster.to_list(), clusters_order_name)
        return feature
