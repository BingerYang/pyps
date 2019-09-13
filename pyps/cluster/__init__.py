# -*- coding: utf-8 -*- 
# @Time     : 2019-07-11 16:55
from pyps.layer import constant
from pyps.layer.position import extend_rect_info_range
from pyps.algorithm.transfer import layer_compare
from pyps.layer.multi import load_intersect_size
from copy import deepcopy
from funcy import project


def rect_dict_to_list(rect_info):
    return [rect_info["xmin"], rect_info["ymin"], rect_info["xmax"], rect_info["ymax"]]


def extend_rect_range(rect, merged_rect):
    rect[0] = min(rect[0], merged_rect[0], 99999)
    rect[1] = min(rect[1], merged_rect[1], 99999)
    rect[2] = max(rect[2], merged_rect[2], 0)
    rect[3] = max(rect[3], merged_rect[3], 0)
    return rect


def create_cluster_info(group, rect, name=None, area_layer=None):
    """
    :param name: 簇的名称
    :param group: 簇的类型
    :param rect: 外部矩形区域
    :param area_layer: 区域装饰的图层信息
    :return:
    """

    return dict(name=name or group,
                type=group,
                layer=area_layer,
                rect=rect,
                layer_names=[],
                layers=[])


class Dict2Obj(dict):
    def __init__(self, *args, **kwargs):
        super(Dict2Obj, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        value = self[key]
        if isinstance(value, dict):
            value = Dict2Obj(value)
        return value


class RuleBuildCluster(object):
    def __init__(self, layer_list, compare_rule):
        self.layer_list = layer_list
        self.compare_rule = compare_rule

    @staticmethod
    def load_layer_identifier(layer):
        return layer["name"]

    @staticmethod
    def load_rect_info(layer):
        return project(layer, ["xmin", "ymin", "xmax", "ymax"])

    @classmethod
    def list_sub(cls, l_list1, l_list2):
        n = 0
        while n < len(l_list1):
            if cls.load_layer_identifier(l_list1[n]) in l_list2:
                l_list1.pop(n)
            else:
                n += 1

    @classmethod
    def sync_layer_cluster(cls, layer, layer_list, cluster_compare_rule):
        """
        用 layer 的区域信息，递归轮训分别于 layer_list 中的图层进行判断是否有规则关系
        :param layer:
        :param layer_list:
        :param cluster_compare_rule:
        :return: 外接矩形区域，一个簇信息
        """
        name_cluster_list = [cls.load_layer_identifier(layer), ]
        temp_layer_pool = layer_list.copy()

        rect_info = deepcopy(cls.load_rect_info(layer))  # 不改变layer原有信息的基础之上对外接矩形进行传递
        while len(temp_layer_pool):
            find_count = 0
            for l in temp_layer_pool:
                l_rect_info = cls.load_rect_info(l)
                if cluster_compare_rule(rect_info, l_rect_info):
                    extend_rect_info_range(rect_info, l_rect_info)
                    name_cluster_list.append(cls.load_layer_identifier(l))
                    find_count += 1
            if find_count:
                cls.list_sub(temp_layer_pool, name_cluster_list)
            else:
                break

        return rect_info, name_cluster_list

    @classmethod
    def sync_cluster(cls, layer_list, cluster_compare_rule):
        """
        对 layer_list 以此取出一个与其余的执行 sync_layer_cluster
        :param layer_list:
        :param cluster_compare_rule:
        :return:
        """
        layer_pool = layer_list.copy()

        cluster_name_list = []  # 已经添加到簇的图层名字
        cluster_rect_list = []
        while len(layer_pool):
            layer = layer_pool.pop(0)

            rect_info = cls.load_rect_info(layer)
            if len(layer_pool) == 0:
                cluster_rect_list.append(rect_info)
                cluster_name_list.append([cls.load_layer_identifier(layer)])
                break
            cluster_rect_info, cluster = cls.sync_layer_cluster(layer, layer_pool, cluster_compare_rule)
            if cluster:
                cluster_rect_list.append(cluster_rect_info)
                cluster_name_list.append(cluster)
                cls.list_sub(layer_pool, cluster)

        return cluster_name_list, cluster_rect_list

    def result(self, is_index=False, is_dict=True):
        """
        执行图形间规则聚组
        :param is_index: 结果簇中由索引组成
        :param is_dict: 输入参数是字典还是类
        :return: 聚簇结果
        """
        layer_name_infos = dict(
            [(layer.core.name, (index, layer)) for index, layer in enumerate(self.layer_list)]
        )
        if is_dict:
            layer_rect_list = self.layer_list
        else:
            layer_rect_list = [layer.copy() for layer in self.layer_list]

        cluster_list, cluster_size_list = self.sync_cluster(layer_rect_list, self.compare_rule)
        for cluster in cluster_list:
            for index, layer_name in enumerate(cluster):
                layer_tuple = layer_name_infos[layer_name]
                value = layer_tuple[0] if is_index else layer_tuple[1]
                cluster[index] = value
        return cluster_list, cluster_size_list

    def run(self, cluster_type, is_dict=True):
        layer_name_infos = dict(
            [(layer.core.name, (index, layer)) for index, layer in enumerate(self.layer_list)]
        )
        if is_dict:
            layer_rect_list = self.layer_list
        else:
            layer_rect_list = [layer.copy() for layer in self.layer_list]

        cluster_list, cluster_size_list = self.sync_cluster(layer_rect_list, self.compare_rule)

        cluster_info_list = []
        for i, cluster in enumerate(cluster_list):
            info = create_cluster_info(group=cluster_type, rect=rect_dict_to_list(cluster_size_list[i]))
            for layer_name in cluster:
                layer_tuple = layer_name_infos[layer_name]
                info["layer_names"].append(layer_name)
                info["layers"].append(layer_tuple[1])
            cluster_info_list.append(info)

        return cluster_info_list


class LogoCluster(object):
    cluster_type = constant.TYPE_LOGO

    def __init__(self, main_distance, layer_list):
        self._main_distance = main_distance
        self.layer_list = layer_list
        self.cluster_info_list = None

    @classmethod
    def rule_cluster(cls, layers, cluster_compare_rule):
        """
        按规则查找图层关系（实行回滚聚簇）
        :param layers:
        :param cluster_compare_rule:
        :return:
        """
        obj = RuleBuildCluster(layers, cluster_compare_rule)
        return obj.run(cls.cluster_type, is_dict=False)

    def compare_rule(self, l1, l2):
        horizontal = layer_compare(l1, l2, 0, 0.9, self._main_distance * 0.08)
        vertical = layer_compare(l1, l2, 1, 0.9, self._main_distance * 0.06)
        return horizontal or vertical

    def add_line_cluster(self, cluster_info_list, line_layer_list):
        for cluster_info in cluster_info_list:
            rect = cluster_info["rect"]
            n = 0
            while n < len(line_layer_list):  # 仅线条装饰
                layer = line_layer_list[n]

                center_col = (layer.core.xmin + layer.core.xmax) / 2
                center_row = (layer.core.ymin + layer.core.ymax) / 2

                if rect[0] < center_col < rect[2] and \
                        rect[1] < center_row < rect[3]:
                    cluster_info["layers"].append(layer)
                    cluster_info["layer_names"].append(layer.core.name)
                    line_layer_list.pop(n)
                    break
                n += 1

    def all_name_set(self, is_single=False):
        all_name_set_ = set()
        for cluster_info in self.cluster_info_list:
            layer_name_list = cluster_info["layer_names"]
            if is_single and len(layer_name_list) == 1:
                all_name_set_.add(layer_name_list[0])
                continue
            all_name_set_ |= set(layer_name_list)
        return all_name_set_

    def remove_single_cluster(self, name_list):
        n = 0
        while n != len(self.cluster_info_list):
            if self.cluster_info_list[n]["layer_names"][0] in name_list:
                self.cluster_info_list.pop(n)
            else:
                n += 1

    def load_multi_and_simple_cluster(self):
        multi_cluster_names, single_cluster_names = [], []
        for cluster_info in self.cluster_info_list:
            layer_name_list = cluster_info["layer_names"]
            if len(layer_name_list) > 1:
                multi_cluster_names.extend(layer_name_list)
            else:
                single_cluster_names.extend(layer_name_list)
        return set(multi_cluster_names), set(single_cluster_names)

    def get_cluster_intersection(self, cluster):
        layer_list = cluster["layers"]
        cluster["intersection"] = -1
        if len(layer_list) > 1:
            l1, l2 = list(filter(lambda l: l.core.group == constant.TYPE_LOGO, layer_list))
            l1.margin, l2.margin = [-1, -1], [-1, -1]
            horizontal = layer_compare(l1.rect_info, l2.rect_info, 0, 0.9, self._main_distance * 0.08)
            if horizontal:
                cluster["intersection"] = 0
                layer_list = cluster["layers"] = sorted(layer_list, key=lambda l: l.center[0])
                layer_list[0].margin[1] = layer_list[1].core.xmin - layer_list[0].core.xmax
                layer_list[-1].margin[0] = layer_list[-1].core.xmin - layer_list[-2].core.xmax
            else:
                cluster["intersection"] = 1
                layer_list = cluster["layers"] = sorted(layer_list, key=lambda l: l.center[1])
                layer_list[0].margin[1] = layer_list[1].core.ymin - layer_list[0].core.ymax
                layer_list[-1].margin[0] = layer_list[-1].core.ymin - layer_list[-2].core.ymax
        else:
            layer_list[0].margin = [-1, -1]

    def load_align_and_margin(self):
        """
        对于 簇中只有一个图层的 设置相交性为-1，不为0，分为水平（0）和垂直（1）
        margin = (1.0, 2.0) 分别为到左边元素的边距为1.0, 到右边元素的边距为2.0
        :return:
        """
        for cluster_info in self.cluster_info_list:
            self.get_cluster_intersection(cluster_info)

    @staticmethod
    def update_layer_at_cluster(cluster_info, old_layer, new_pil, start_pos: tuple):
        _intersection = cluster_info["intersection"]
        if _intersection == -1:
            old_layer.replace_pil_at_rect(new_pil, xmin=start_pos[0], ymin=start_pos[1])
            cluster_info["rect"] = old_layer.rect
        else:

            xmax = start_pos[0] + new_pil.width
            ymax = start_pos[1] + new_pil.height
            if _intersection == 0:
                if old_layer.margin[1] > 0:
                    old_layer.margin[1] += old_layer.core.xmax - xmax
                if old_layer.margin[0] > 0:
                    old_layer.margin[0] -= (old_layer.core.xmin - start_pos[0])
            else:
                if old_layer.margin[1] > 0:
                    old_layer.margin[1] += old_layer.core.ymax - ymax
                if old_layer.margin[0] > 0:
                    old_layer.margin[0] -= (old_layer.core.ymin - start_pos[1])
            old_layer.replace_pil_at_rect(new_pil, xmin=start_pos[0], ymin=start_pos[1])
            extend_rect_range(cluster_info["rect"], old_layer.rect)

    def run(self, include_layer_list=None):
        self.cluster_info_list = self.rule_cluster(self.layer_list, self.compare_rule)
        if include_layer_list:
            self.add_line_cluster(self.cluster_info_list, line_layer_list=include_layer_list)
        return self.cluster_info_list


class TextCluster(object):
    cluster_type = constant.TYPE_TEXT

    def __init__(self, main_distance, layer_list):
        self._main_distance = main_distance
        self.layer_list = layer_list
        self.cluster_info_list = None

    @classmethod
    def rule_cluster(cls, layers, cluster_compare_rule):
        """
        按规则查找图层关系（实行回滚聚簇）
        :param layers:
        :param cluster_compare_rule:
        :return:
        """
        obj = RuleBuildCluster(layers, cluster_compare_rule)
        return obj.run(cls.cluster_type, is_dict=False)

    def compare_rule(self, l1, l2):
        interval = max(l1["ymax"] - l1["ymin"] + 1, l2["ymax"] - l2["ymin"] + 1)
        horizontal = layer_compare(l1, l2, 0, 0.9, interval * 0.618)
        vertical = layer_compare(l1, l2, 1, 0.9, interval * 0.618)
        return horizontal or vertical

    @classmethod
    def update_layer_at_cluster(cls, cluster_info, old_layer, new_pil, start_pos: tuple):
        old_layer.replace_pil_at_rect(new_pil, xmin=start_pos[0], ymin=start_pos[1])
        cluster_info["rect"] = old_layer.rect

    def load_multi_and_simple_cluster(self):
        multi_cluster_names, single_cluster_names = [], []
        for cluster_info in self.cluster_info_list:
            layer_name_list = cluster_info["layer_names"]
            if len(layer_name_list) > 1:
                multi_cluster_names.extend(layer_name_list)
            else:
                single_cluster_names.extend(layer_name_list)
        return set(multi_cluster_names), set(single_cluster_names)

    def remove_single_cluster(self, name_list):
        n = 0
        while n != len(self.cluster_info_list):
            if self.cluster_info_list[n]["layer_names"][0] in name_list:
                self.cluster_info_list.pop(n)
            else:
                n += 1

    def run(self, exclude_name_list=None):
        exclude_name_list = exclude_name_list or []
        layer_list = list(filter(lambda layer: layer.core.name not in exclude_name_list, self.layer_list))
        self.cluster_info_list = self.rule_cluster(layer_list, self.compare_rule)
        return self.cluster_info_list


class RelationCluster(object):
    cluster_type = constant.TYPE_RELATION

    def __init__(self, layer_list, psd_layers):
        self.psd_layers = psd_layers
        self.layer_list = layer_list
        self.all_name_set = set()
        self.cluster_info_list = None

    @staticmethod
    def positional_relationship(g_rect, e_rect):
        """
        区域装饰（g_rect）和主元素（e_rect）的关系
        :param g_rect: 区域装饰图层坐标信息
        :param e_rect: 主元素图层坐标信息
        :return: 0: 区域相离，1：区域相交， 2： 区域包含（位于区域装饰内）
        """
        intersect_width, intersect_height = load_intersect_size(g_rect, e_rect)
        w1, h1 = g_rect[2] - g_rect[0] + 1, g_rect[3] - g_rect[1] + 1
        w2, h2 = e_rect[2] - e_rect[0] + 1, e_rect[3] - e_rect[1] + 1
        if intersect_width / w2 < intersect_height / h2:
            if 0.75 * w2 < intersect_width < w2 and 0 < intersect_height <= h2:
                return 1
        elif intersect_width / w2 > intersect_height / h2:
            if (0.75 * h2 < intersect_height < h2 or (
                    intersect_width / w2 > 0.9 and 0.2 * h2 < intersect_height < h2)) and 0 < intersect_width <= w2:
                return 1
        if intersect_width == w2 and intersect_height == h2:
            return 2
        else:
            return 0

    @classmethod
    def get_region_relations(cls, region, psd_layers, exclude_name_list=None):
        """
        获取位于区域组(区域装饰/线框装饰)内主元素的集合（呈现：包含/覆盖关系）
        :param psd_layers: 主元素图层序列
        :param region: 区域装饰图层 G1
        :param exclude_name_list: 不包含的图层
        :return: 位于区域组内图层的名字，区域组
        """

        exclude_name_list = exclude_name_list or []
        layer_names = []
        region_groups = []
        region_rect = region.rect

        for l in psd_layers:
            if l is region or l.core.name in exclude_name_list:
                continue

            element_rect = l.rect

            type_name = l.core.group
            if type_name == constant.TYPE_TEXT:
                intersect = cls.positional_relationship(region_rect, element_rect)
                if intersect == 2:
                    layer_names.append(l.core.name)
                    region_groups.append(l)
                    l.is_included = True

            elif type_name == constant.TYPE_LOGO:
                intersect = cls.positional_relationship(region_rect, element_rect)
                if intersect == 2:
                    layer_names.append(l.core.name)
                    region_groups.append(l)
                    l.is_included = True

            elif type_name == constant.TYPE_GRAPH:
                if l.core.tag != constant.TYPE_GRAPH_DECORATION:
                    intersect = cls.positional_relationship(region_rect, element_rect)
                    if intersect > 0:
                        layer_names.append(l.core.name)
                        region_groups.append(l)
                        l.is_included = True if intersect == 2 else False

            elif l.core.tag == constant.TYPE_RELATION_AREA:
                intersect = cls.positional_relationship(region_rect, element_rect)
                if intersect == 2:
                    layer_names.append(l.core.name)
                    region_groups.append(l)
                    l.is_included = True
            else:
                # other 和线条装饰
                intersect = cls.positional_relationship(region_rect, element_rect)
                if intersect > 0:
                    layer_names.append(l.core.name)
                    region_groups.append(l)
                    l.is_included = True if intersect == 2 else False

        # 聚簇
        cluster_info = create_cluster_info(group=cls.cluster_type, rect=None, area_layer=region)
        cluster_info["layer_names"].extend(layer_names)
        cluster_info["layers"].extend(region_groups)

        if not region_groups:
            rect = region.rect
        else:
            rect = [99999, 99999, 0, 0]
            for layer in region_groups:
                rect = extend_rect_range(rect, layer.rect)
        cluster_info["rect"] = rect
        return cluster_info

    @classmethod
    def update_layer_at_cluster(cls, cluster_info, old_layer, new_pil, start_pos: tuple):
        old_layer.replace_pil_at_rect(new_pil, xmin=start_pos[0], ymin=start_pos[1])
        rect = (cluster_info["layer"].core.xmin, cluster_info["layer"].core.ymin, cluster_info["layer"].core.xmax,
                cluster_info["layer"].core.ymax)
        intersect = cls.positional_relationship(rect, old_layer.rect)
        old_layer.is_included = True if intersect == 2 else False

    def run(self, exclude_name_list=None):

        cluster_info_list = []
        for layer_info in self.layer_list:
            cluster_info = self.get_region_relations(layer_info, self.psd_layers, exclude_name_list=exclude_name_list)
            # 需要判断该区域装饰属于那种类型的元素：0：文案，1：图标，2：混合，3：主图形
            cluster_info_list.append(cluster_info)
            self.all_name_set |= set(cluster_info["layer_names"])

        self.cluster_info_list = cluster_info_list
        return cluster_info_list


class GraphCluster(object):
    cluster_type = constant.TYPE_GRAPH

    def __init__(self, layer_list):
        self.layer_list = layer_list
        self.cluster_info_list = []

    @classmethod
    def update_layer_at_cluster(cls, cluster_info, old_layer, new_pil, start_pos: tuple):
        old_layer.replace_pil_at_rect(new_pil, xmin=start_pos[0], ymin=start_pos[1])
        cluster_info["rect"] = old_layer.rect

    def run(self):
        for layer in self.layer_list:
            cluster_info = create_cluster_info(group=self.cluster_type, rect=layer.rect)
            cluster_info["layer_names"].append(layer.core.name)
            cluster_info["layers"].append(layer)
            self.cluster_info_list.append(cluster_info)
        return self.cluster_info_list


def load_cluster_by_layer(name, cluster_info_list):
    find_cluster = None
    for cluster_info in cluster_info_list:
        if name in cluster_info["layer_names"]:
            find_cluster = cluster_info
            break
    return find_cluster


class PsdCluster(object):
    def __init__(self, psd_layers, size=None):
        self.psd_layers = psd_layers
        self._size = size
        self._main_distance = 0.
        self._logo_type_list = []
        self._line_type_list = []
        self._area_type_list = []
        self._text_type_list = []
        self._graph_type_list = []
        self._other_type_list = []

        self.graph = None
        self.area = None
        self.logo = None
        self.text = None
        self.bg_layer = None

        self._tag = None
        self._to_list = []
        self._expand_region_to_list = []

    @property
    def size(self):
        if self._size is None:
            self._size = self.bg_layer.pil.size
        return self._size

    def load_cluster_by_layer(self, name):
        find = load_cluster_by_layer(name, self.text.cluster_info_list)
        find = find or load_cluster_by_layer(name, self.area.cluster_info_list)
        find = find or load_cluster_by_layer(name, self.logo.cluster_info_list)
        find = find or load_cluster_by_layer(name, self.graph.cluster_info_list)
        return find

    def update_layer_at_cluster(self, cluster_info, old_layer, new_pil, start_pos: tuple):
        cache = {
            constant.TYPE_RELATION: self.area.update_layer_at_cluster,
            constant.TYPE_GRAPH: self.graph.update_layer_at_cluster,
            constant.TYPE_LOGO: self.logo.update_layer_at_cluster,
            constant.TYPE_TEXT: self.text.update_layer_at_cluster,
        }
        cache[cluster_info["type"]](cluster_info, old_layer, new_pil, start_pos)

    def init_process(self):
        for layer in self.psd_layers:
            layer_type = layer.core.group
            if layer_type in constant.TYPE_BACKGROUND:
                self._main_distance = (layer.width ** 2 + layer.height ** 2) ** 0.5
                self.bg_layer = layer
            elif layer_type == constant.TYPE_LOGO:
                self._logo_type_list.append(layer)
            elif layer_type == constant.TYPE_TEXT:
                self._text_type_list.append(layer)
            elif layer_type == constant.TYPE_OTHER:
                self._other_type_list.append(layer)
            else:
                tag = layer.core.tag
                if tag == constant.TYPE_RELATION_LINE:
                    self._line_type_list.append(layer)
                elif tag == constant.TYPE_RELATION_AREA:
                    self._area_type_list.append(layer)
                elif tag == constant.TYPE_GRAPH_MAIN:
                    self._graph_type_list.append(layer)

        return

    def run2(self):
        """
        目前 other 和 图形的G2和G3没有做处理
        :return:
        """
        self.init_process()
        self.graph = GraphCluster(self._graph_type_list)
        self.graph.run()
        self.logo = LogoCluster(self._main_distance, self._logo_type_list)
        self.logo.run(self._line_type_list)
        existed_name_list, waitting_name_list = self.logo.load_multi_and_simple_cluster()

        self.area = RelationCluster(self._area_type_list, self.psd_layers)
        self.area.run(exclude_name_list=existed_name_list)
        waitting_name_list -= self.area.all_name_set
        self.logo.remove_single_cluster(waitting_name_list)
        self.text = TextCluster(self._main_distance, self._text_type_list + self._line_type_list)
        self.text.run(exclude_name_list=self.area.all_name_set)
        return

    def run(self):
        """
        目前 other 和 图形的G2和G3没有做处理
        :return:
        """
        self.init_process()
        self.graph = GraphCluster(self._graph_type_list)
        self.graph.run()
        if self._logo_type_list:
            self.logo = LogoCluster(self._main_distance, self._logo_type_list)
            self.logo.run(self._line_type_list)
            existed_name_set, waitting_name_set = self.logo.load_multi_and_simple_cluster()
        else:
            existed_name_set, waitting_name_set = set(), set()

        if self._text_type_list:
            self.text = TextCluster(self._main_distance, self._text_type_list + self._line_type_list)
            self.text.run()
            text_existed_name_list, text_waitting_name_list = self.text.load_multi_and_simple_cluster()

            existed_name_set.update(text_existed_name_list)
            waitting_name_set.update(text_waitting_name_list)

        self.area = RelationCluster(self._area_type_list, self.psd_layers)
        self.area.run(exclude_name_list=existed_name_set)
        if waitting_name_set:
            waitting_remove_set = waitting_name_set & self.area.all_name_set
            self.logo.remove_single_cluster(waitting_remove_set)
            self.text.remove_single_cluster(waitting_remove_set)

        return

    @property
    def tag(self):
        if self._tag:
            return self._tag
        else:
            # def update_cluster_name(psd_cluster):
            #     for i, cluster in enumerate(psd_cluster.cluster_info_list):
            #         cluster["name"] = "{}{}".format(cluster["type"], i + 1)

            from operator import itemgetter
            from collections import defaultdict
            c_cache = defaultdict(int)
            g_cache = defaultdict(int)

            cluster_type_list = [self.graph, self.logo, self.text]

            def count(cluster_type):
                for cluster in cluster_type.cluster_info_list:
                    n = len(cluster["layers"])
                    if n >= 2:
                        c_cache[cluster["type"]] += 1
                    else:
                        g_cache[cluster["type"]] += 1

            list(map(count, cluster_type_list))
            c_tag = "&"
            for k, v in sorted(c_cache.items(), key=itemgetter(0)):
                c_tag = "{}_{}{}".format(c_tag, k, v)

            def region_count(cluster):
                for layer in cluster["layers"]:
                    g_cache[layer.core.group] += 1

            list(map(region_count, self.area.cluster_info_list))
            g_tag = "|"
            for k, v in sorted(g_cache.items(), key=itemgetter(0)):
                g_tag = "{}_{}{}".format(g_tag, k, v)

            self._tag = tag = f"{c_tag}{g_tag}"
            return tag

    def to_list1(self):
        if self._to_list:
            return self._to_list
        cluster_type_list = [self.graph, self.logo, self.area, self.text]

        for cluster in cluster_type_list:
            cluster = cluster or []
            self._to_list.extend(cluster.cluster_info_list)
        return self._to_list

    def to_list(self):

        if self._expand_region_to_list:
            return self._expand_region_to_list

        from collections import defaultdict
        cache = defaultdict(int)

        def update_cluster_name(cluster_list):
            for cluster in cluster_list:
                c_type = cluster["type"]
                index = cache[c_type]
                cluster["name"] = "{}{}".format(c_type, index + 1)
                cache[c_type] += 1

        cluster_type_list = [self.graph, self.logo, self.text]

        to_list = []
        for cluster_obj in cluster_type_list:
            cluster_obj = cluster_obj or []
            to_list.extend(cluster_obj.cluster_info_list)
        update_cluster_name(to_list)

        simple_list = []
        for cluster in self.area.cluster_info_list:
            for layer in cluster["layers"]:
                cluster_info = create_cluster_info(group=layer.core.group, rect=layer.rect)
                cluster_info["layer_names"].append(layer.core.name)
                cluster_info["layers"].append(layer)
                simple_list.append(cluster_info)

        update_cluster_name(simple_list)
        self._expand_region_to_list.extend(to_list)
        self._expand_region_to_list.extend(simple_list)
        return self._expand_region_to_list


if __name__ == "__main__":
    pass
