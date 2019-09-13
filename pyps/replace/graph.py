# -*- coding: utf-8 -*- 
# @Time     : 2019-09-04 11:46
# @Author   : binger

from pyps.utils.common import read_image
from pyps.layer import img, position
from pyps.layer import constant
from pyps.layer import multi
from pyps.replace.cross_rule import CrossReplaceRule


class GraphBase(object): pass


class Graph(GraphBase):
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

    def replace(self, replace_element, elements_overlap=None, have_overlap_limit=True, layer_mask=False, is_jd=False):
        """
        # 图层预处理
        # 获取其压边情况
        # 输入预处理
        # 根据图层与相关图层的对齐关系获取其在对齐情况的延展大小

        # 循环减少
        #   获取新的区域
        #   区域判断是否符合条件（压边，超出边界范围）
        """

        # 图层预处理 => 开始
        self.layer.cut_for_show_area(self.psd_cluster.size, is_apply=True)
        self.layer.get_external_boundary(is_apply=True)
        out_safe_region = position.is_inclusion_relation(self.layer.rect, self._edge_area)
        is_relation_cluster = True if self.cluster["type"] == constant.TYPE_RELATION else False
        if is_relation_cluster:
            crop_ = img.get_outer_rect(self.cluster["layer"].pil)
            area_rect = self.cluster["layer"].move(offset=crop_[0:2], size=crop_[2:], is_apply=False)
            area_rect = position.cut_psd_show_area(area_rect, self.psd_cluster.size)
            # 紧挨着 或者重合（输入的目标图层位于当前遍历的图层内部）
            cross_rule_app = CrossReplaceRule(area_rect, self.layer.rect)
            # if not self.layer.is_included:
            #     # 交叉
            #     cross_rule_app.load_position()

        if have_overlap_limit:
            source_overlap = []
            source_overlap_area = []
            for element_overlap in elements_overlap or []:
                if element_overlap['name'] == self.layer.core.name:
                    source_overlap = element_overlap['overlap_layer']
                    source_overlap_area = element_overlap['overlap_area']
                    break

        # 获取要替换的图层信息
        pil = read_image(replace_element.path, with_token=True)
        pil, _ = img.cut_nonzero(pil)

        new_w, new_h = pil.size
        max_length = max(new_w, new_h)  # 偏移量每次范围缩小 2 进行匹配
        key = "to_height" if new_w < new_h else "to_width"
        new_w, new_h = position.layer_to_width_or_height(w_h_ratio=pil.width / pil.height, **{key: max_length})
        new_w, new_h = position.resize_by_rate_to_target(size=(new_w, new_h),
                                                         to_size=(self.layer.width, self.layer.height),
                                                         use_small=True)

        is_first = True
        while True:
            # 递增条件
            if not is_first:
                max_length = max(new_w, new_h) - 2  # 偏移量每次范围缩小 2 进行匹配
                key = "to_height" if new_w < new_h else "to_width"
                new_w, new_h = position.layer_to_width_or_height(w_h_ratio=pil.width / pil.height, **{key: max_length})

            is_first = False

            # 获取区域
            if is_relation_cluster:
                cur_rect = cross_rule_app.replace(size=(new_w, new_h))
            else:
                cur_rect = self.layer.resize_by_center(width=new_w, height=new_h, is_apply=False)

            # 替换条件 => 开始
            if out_safe_region:
                if not position.is_inclusion_relation(cur_rect, self._edge_area):
                    continue

            if have_overlap_limit:
                new_overlap, new_overlap_area = multi.get_region_overlap(self.bg_pil, self.layer,
                                                                         self.psd_cluster.psd_layers, *cur_rect)
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

            if is_jd:
                # 京东首焦banner的安全边距：上264，下70（京东首焦尺寸1125x762）
                if self.psd_cluster.size == (1125, 762):
                    if (cur_rect[1] < 264) or (cur_rect[3] > self.psd_cluster.size[1] - 1 - 70):
                        continue

            if position.is_inclusion_relation(cur_rect, [0, 0, self.psd_cluster.size[0], self.psd_cluster.size[1]]):
                if new_w < self.layer.width and new_h < self.layer.width:
                    break
                else:
                    continue

        # 执行替换
        key = "to_height" if new_w < new_h else "to_width"
        pil = img.resize_to_width_or_height(img=pil, **{key: max(new_w, new_h)})

        # 当人物主图形全身进入画布内时，进行蒙版处理
        if layer_mask and self.layer.ymax < self.psd_cluster.size[1] - 3:
            pil = img.layer_mask(pil)

        self.psd_cluster.update_layer_at_cluster(self.cluster, self.layer, new_pil=pil, start_pos=cur_rect[:2])
        # pil.show()


if __name__ == "__main__":
    pass
