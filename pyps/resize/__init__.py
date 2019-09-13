# -*- coding: utf-8 -*- 
# @Time     : 2019-09-10 10:16
# @Author   : binger

import logging
from pyps.cluster.feature import filter_feature_vector
from pyps.algorithm.transfer import find_similar_layout
from pyps.cluster.transfer import layout_transform, relative_transfer, extend_rect_range
from pyps.layer import constant
from pyps.layer.position import get_scrap_edge, is_inclusion_relation
from pyps.layer.img import layer_paste, resize_by_target
from PIL import Image

logger = logging.getLogger("resize")


class Resize(object):
    def __init__(self, psd_model, target_size, max_similar_value=1):
        self.psd_model = psd_model
        self.target_size = target_size
        self._max_similar_value = max_similar_value
        self._frames = []

    def load_frame_by_cluster_tag(self, tag):
        from pyps import PsdModel
        import os

        def init_psd(path):
            model = PsdModel()
            model.init_by_file(path)
            model.build_cluster()
            return model

        frames = []
        root_path = "/Users/yangshujun/self/pyps/data/LH_44_5.21"
        for name in os.listdir(root_path):
            path = os.path.join(root_path, name)
            model = init_psd(path)
            if model.cluster.tag == tag:
                frames.append(model)
        return frames

    def select_frame(self):
        frames = self.load_frame_by_cluster_tag(self.psd_model.cluster.tag)
        # 过滤出大于 self._max_similar_value 的模板
        filter_feature_vector(self.psd_model, frames, self._max_similar_value)

        # 查找相同尺寸向量值最小的所有情况
        cache = dict()
        i = 0
        while i < len(frames):
            frame = frames[i]
            key = "{}_{}".format(*frame.size)
            old_i = cache.get(key)
            if old_i:
                frames.pop(i)
                if frame.feature_value < frames[old_i].feature_value:
                    frames[old_i] = frame
            else:
                cache[key] = i
                i += 1

        # 通过三角剖析法过滤出最接近的尺寸的框架
        find_index_list = find_similar_layout([frame.size for frame in frames], self.target_size)
        for i in range(len(frames) - 1, -1, -1):
            if i not in find_index_list:
                frames.pop(i)
        self._frames = frames

    def transform_frame(self):
        pass

    def transform_region(self):
        """
        针对区域装饰和单图层的图层进行变换映射
        :return:
        """
        cluster_list = self.psd_model.cluster.area.cluster_info_list
        for cluster in cluster_list:
            rect2 = [10000, 10000, 0, 0]
            [extend_rect_range(rect2, layer.rect) for layer in cluster["layers"]]
            rect1 = cluster["rect"]

            layer = cluster["layer"]
            temp_rect = relative_transfer(layer.rect, rect1, rect2)
            layer.update_rect(temp_rect)
        return

    def transform_bg(self, layer, use_valid_bg=False):

        pil = layer.pil
        if not use_valid_bg and self.target_size[0] >= pil.width and self.target_size[1] >= pil.height:
            pass
        else:
            if use_valid_bg:
                layer.cut_for_show_area(self.psd_model.size, is_apply=True)
            pil = layer.pil
            pil = resize_by_target(pil, self.target_size, use_small=False)
        xmin = self.target_size[0] / 2 - pil.width / 2
        ymin = self.target_size[1] / 2 - pil.height / 2
        layer.replace_pil_at_rect(pil, xmin, ymin)
        return pil, xmin, ymin

    def auto_layouts(self, to_pil=False):
        """
        对图层布局进行映射
        :return:
        """
        # 对psd各簇的layers，进行变换映射
        layout_transform(self.psd_model.cluster, self.target_size,
                         [psd_cluster.cluster for psd_cluster in self._frames])
        # 对区域簇layer进行变换映射
        self.transform_region()

        if to_pil:
            img_obj = Image.new('RGBA', self.target_size, (255, 255, 255, 0))
        else:
            img_obj = None
        # 添加剩余装饰图层和背景
        for layer in self.psd_model.layers:
            pil = layer.pil
            if layer.core.group == constant.TYPE_BACKGROUND:
                self.transform_bg(layer, use_valid_bg=True)
            else:
                if layer.core.tag == constant.TYPE_GRAPH_DECORATION:
                    self.attach_decoration(layer, use_valid_bg=True)
                else:
                    pil = resize_by_target(pil, target_size=layer.size, use_small=True)
                    # if layer.width / pil.width < layer.height / pil.height:
                    #     pil = resize_to_width_or_height(pil, to_width=layer.width)
                    # else:
                    #     pil = resize_to_width_or_height(pil, to_height=layer.height)
                    layer.replace_pil(pil, is_center_align=True)
            if img_obj:
                img_obj = layer_paste(img_obj, layer.pil, layer.core.xmin, layer.core.ymin)

        self.psd_model.set_size(self.target_size)
        img_obj and img_obj.show()
        return img_obj

    def attach_decoration(self, layer, use_valid_bg=False):
        """
        目前只是根据位置，放到什么位置，没有做拉伸变换（以后可以更新）
        :return:
        """

        if use_valid_bg and not is_inclusion_relation(layer.rect,
                                                      [0, 0, self.psd_model.size[0], self.psd_model.size[1]]):
            layer.cut_for_show_area(self.target_size, is_apply=True)
        width_scale = self.target_size[0] / self.psd_model.size[0]
        height_scale = self.target_size[1] / self.psd_model.size[1]

        center = layer.center
        new_row = center[1] * height_scale
        new_col = center[0] * width_scale
        # 判断元素是否贴边
        element_scrap = get_scrap_edge(layer, self.psd_model.size)
        if element_scrap[1]:
            new_row = (layer.pil.height - 1) / 2
        elif element_scrap[3]:
            new_row = self.target_size[1] - (layer.pil.height - 1) / 2

        if element_scrap[0]:
            new_col = (layer.pil.width - 1) / 2
        elif element_scrap[2]:
            new_col = self.target_size[0] - (layer.pil.width - 1) / 2

        xmin = new_col - (layer.pil.width - 1) / 2
        ymin = new_row - (layer.pil.height - 1) / 2

        layer.replace_pil_at_rect(pil=layer.pil, xmin=xmin, ymin=ymin)

    def run(self, to_pil=False):
        # 筛选框架
        self.select_frame()
        # 通过旋转或翻转方式增加目标框架数量
        self.transform_frame()
        # 自动布局
        self.auto_layouts(to_pil)


if __name__ == "__main__":
    from pyps import PsdModel

    model = PsdModel()
    psd_path = "/Users/yangshujun/self/pyps/data/LH_42_5.21/LH_42_5.21_520x280.psd"
    psd_path = "/Users/yangshujun/self/pyps/data/LH_42_5.21/LH_42_5.21_p_1125x762.psd"
    model.init_by_file(psd_path)
    model.build_cluster()

    app = Resize(psd_model=model, target_size=(700, 1000))
    app.run(to_pil=True)
    print("111")
