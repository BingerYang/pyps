# -*- coding: utf-8 -*- 
# @Time     : 2019-09-03 15:36
# @Author   : binger
from pyps.utils.common import read_image
from pyps.layer import img, position
from pyps.layer import multi
from pyps.layer import constant


class LogoBase(object):
    def __init__(self):
        pass


THRESHOLD_BETWEEN = 5
THRESHOLD_BETWEEN_RATIO = 0.01


class Logo(object):
    def __init__(self, layer, psd_cluster, edge_area):
        self.layer = layer
        self._edge_area = edge_area
        self.psd_cluster = psd_cluster
        self.cluster = psd_cluster.load_cluster_by_layer(name=layer.core.name)
        # self.bg_pil = get_title_background(layer, self.psd_cluster.layers, *self.psd_cluster.size)  # 获取背景画布（带新思路优化）
        self.bg_pil = self.load_background()

    def load_background(self):
        if self.cluster:
            layers = self.cluster["layers"]
            if self.cluster["type"] == constant.TYPE_RELATION:
                layers.append(self.cluster["layer"])
        else:
            layers = self.psd_cluster.psd_layers
        return multi.load_background_pil(self.layer, layers, self.psd_cluster.size)

    def get_size_by_intersection(self, size):
        """
        根据一个簇内相关图层的位置关系，适应的变化大小
        如果位于水平方向上，等比延展到相同的高，如果位于垂直方向上，等比延展到相同的宽
        会造成的新的宽和高和size，一边相同，一边可大可小
        :param size:
        :return:
        """
        if self.cluster["type"] == constant.TYPE_RELATION:
            return size

        self.psd_cluster.logo.get_cluster_intersection(self.cluster)
        w, h = size
        direction = self.cluster["intersection"]
        if direction == constant.INTERSECTION_HORI:
            h_range = self.cluster["rect"]["ymax"] - self.cluster["rect"]["ymin"]
            w, h = position.layer_to_width_or_height(w / h, to_height=h_range)
        elif direction == constant.INTERSECTION_VERI:
            w_range = self.cluster["rect"]["xmax"] - self.cluster["rect"]["xmin"]
            w, h = position.layer_to_width_or_height(w / h, to_width=w_range)
        else:
            pass
        return w, h

    def update_rect_by_intersection(self, rect):
        """
        通过一个簇内的相关图层的位置关系，调整位置
        :param rect:
        :return:
        """
        if self.cluster["type"] == constant.TYPE_RELATION:
            return

        w = rect[2] - rect[0] + 1
        h = rect[3] - rect[1] + 1

        direction = self.cluster["intersection"]
        if self.layer.margin[1] < 0 < self.layer.margin[0]:
            if direction == constant.INTERSECTION_HORI:
                rect[2] = self.layer.core.xmin + w - 1
                rect[0] = self.layer.core.xmin
            else:
                rect[3] = self.layer.core.ymin + h - 1
                rect[1] = self.layer.core.ymin
        elif self.layer.margin[0] < 0 < self.layer.margin[1]:
            if direction == constant.INTERSECTION_HORI:
                rect[0] = self.layer.core.xmax - (w - 1)
                rect[2] = self.layer.core.xmax
            else:
                rect[1] = self.layer.core.ymax - (h - 1)
                rect[3] = self.layer.core.ymax

    def replace(self, replace_element, elements_overlap=None, have_edge_limit=True, have_overlap_limit=True):
        extend_thresh = int(min(THRESHOLD_BETWEEN, THRESHOLD_BETWEEN_RATIO * min(self.psd_cluster.size)))

        """
        # 图层预处理
        # 获取其压边情况
        # 输入预处理
        # 根据图层与相关图层的对齐关系获取其在对齐情况的延展大小

        # 循环减少
        #   获取新的区域
        #   区域判断是否符合条件（压边，超出边界范围）
        """
        # 获取要替换的图层信息
        pil = read_image(replace_element.path, with_token=True)
        pil, _ = img.cut_nonzero(pil)

        # 根据对齐关系延展图片宽高
        pil_w, pil_h = self.get_size_by_intersection(pil.size)

        if have_overlap_limit:
            source_overlap = []
            source_overlap_area = []
            for element_overlap in elements_overlap or []:
                if element_overlap['name'] == self.layer.core.name:
                    source_overlap = element_overlap['overlap_layer']
                    source_overlap_area = element_overlap['overlap_area']
                    break

        is_first = True
        while True:
            if not is_first:
                max_length = max(pil_w, pil_h) - 2  # 偏移量每次范围缩小 2 进行匹配
                key = "to_height" if pil_w < pil_h else "to_width"
                pil_w, pil_h = position.layer_to_width_or_height(w_h_ratio=pil.width / pil.height, **{key: max_length})

            is_first = False

            rect = list(self.layer.resize_by_center(width=pil_w, height=pil_h, is_apply=False))
            # 根据对齐关系启动区域
            self.update_rect_by_intersection(rect)

            # 开始 => 判断条件
            if have_edge_limit and not position.is_inclusion_relation(rect, self._edge_area):
                continue

            if have_overlap_limit:
                # 在正常的画布范围内
                new_overlap, new_overlap_area = multi.get_region_overlap(self.bg_pil, self.layer,
                                                                         self.psd_cluster.psd_layers,
                                                                         rect[0] - extend_thresh,
                                                                         rect[1] - extend_thresh,
                                                                         rect[2] + extend_thresh,
                                                                         rect[3] + extend_thresh)
                if not new_overlap or set(new_overlap) < set(source_overlap):
                    pass  # 覆盖小于原覆盖数，满足条件
                elif set(new_overlap) == set(source_overlap):  # 覆盖数相同，需要覆盖面积小于原来
                    if_ok = True
                    for i in range(len(new_overlap)):
                        if new_overlap_area[i] > source_overlap_area[i]:
                            if_ok = False
                            break
                    if not if_ok:
                        continue
                else:
                    continue

            if self.cluster["type"] != constant.TYPE_RELATION:
                outer_rect = self.cluster["rect"]
                if not position.is_inclusion_relation(rect, [outer_rect["xmin"], outer_rect["ymin"],
                                                             outer_rect["xmax"],
                                                             outer_rect["ymax"]]):
                    continue  # 安全区域(簇)外有东西继续处理
            # 结束 <= 判断条件
            break

        key = "to_height" if pil_w < pil_h else "to_width"
        pil = img.resize_to_width_or_height(img=pil, **{key: max(pil_w, pil_h)})
        # 重置LOGO&活动标签的位置

        # TODO: 需要重新处理
        self.psd_cluster.update_layer_at_cluster(self.cluster, self.layer, new_pil=pil, start_pos=rect[0:2])


if __name__ == "__main__":
    pass
