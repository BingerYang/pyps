# -*- coding: utf-8 -*- 
# @Time     : 2019-08-20 09:59
# @Author   : binger

from pyps.layer import constant


class LineAutoAlign(object):
    def __init__(self, limit: tuple):
        self.factory = [self.front, self.middle, self.back]
        self.limit = limit

    @staticmethod
    def front(length, start, limit):
        return start, start + length - 1

    @staticmethod
    def middle(length, start, limit):
        start += (limit - length) / 2
        return start, start + length - 1

    @staticmethod
    def back(length, start, limit):
        end = start + limit
        start += limit - length
        return start, end

    @property
    def length(self):
        return self.limit[1] - self.limit[0] + 1

    def run(self, align: int, length):
        return self.factory[align](length, self.limit[0], self.length)


class AutoAlign(object):
    def __init__(self, area, rect_size, align=(2, 2)):
        self.area = area
        self.rect_size = rect_size
        self.align = align
        self.factory = [self.front, self.middle, self.back]

    def front(self, length, start, limit):
        return start, start + length - 1

    def middle(self, length, start, limit):
        start += (limit - length) / 2
        return start, start + length - 1

    def back(self, length, start, limit):
        end = start + limit
        start += limit - length
        return start, end

    @staticmethod
    def length(rect):
        return rect[2] - rect[0] + 1, rect[3] - rect[1] + 1

    def run(self):
        width_area, heigth_area = self.length(self.area)
        width_rect, heigth_rect = self.rect_size
        xmin, xmax = self.factory[self.align[0]](width_rect, self.area[0], width_area)
        ymin, ymax = self.factory[self.align[1]](heigth_rect, self.area[1], heigth_area)

        return xmin, xmax, ymin, ymax


from .logo import Logo
from .text import Text
from .graph import Graph
from .background import BackGround
from pyps.layer.multi import get_elements_overlap


class ReplaceElement(object):
    __slots__ = ("name", "path", "info", "tag", "type")

    def __init__(self, name, path, type="icon", tag=None, info=None):
        self.name = name
        self.tag = tag
        self.path = path
        self.type = type
        self.info = info


class Replace(object):
    def __init__(self, psd_model):
        self.psd_model = psd_model

    def init(self):
        self.psd_model.build_cluster()

    def run(self, replace_list):
        replace_cache = {}
        for index, c in enumerate(replace_list):
            replace_cache[c.tag] = c

        elements_overlap = get_elements_overlap(self.psd_model.layers, list(replace_cache.keys()),
                                                *self.psd_model.size)

        for layer in self.psd_model.layers:
            tag = layer.core.tag
            element = replace_cache.get(tag, None)
            if not element:
                continue
            group = layer.core.group

            if group == constant.TYPE_TEXT:
                if element.type == "text":
                    obj = Text(layer=layer, psd_cluster=self.psd_model.cluster, edge_area=self.psd_model.edge_area)
                    obj.replace(replace_element=element)
                else:
                    obj = Graph(layer=layer, psd_cluster=self.psd_model.cluster, edge_area=self.psd_model.edge_area)
                    obj.replace(replace_element=element, elements_overlap=elements_overlap)

            elif group == constant.TYPE_LOGO:
                obj = Logo(layer=layer, psd_cluster=self.psd_model.cluster, edge_area=self.psd_model.edge_area)
                obj.replace(replace_element=element, elements_overlap=elements_overlap)
            elif group == constant.TYPE_BACKGROUND:
                obj = BackGround(self.psd_model.size, layer=layer)
                obj.replace(replace_element=element)

            elif tag == constant.TYPE_GRAPH_MAIN:
                obj = Graph(layer=layer, psd_cluster=self.psd_model.cluster, edge_area=self.psd_model.edge_area)
                obj.replace(replace_element=element, elements_overlap=elements_overlap)


if __name__ == "__main__":
    from pyps import PsdModel

    model = PsdModel()
    psd_path = "/Users/yangshujun/workspace/AI2Design/image/tiger/5.21/LH_40_5.21/LH_40_5.21_520x280.psd"
    model.init_by_file(psd_path)

    obj = Replace(model)
    obj.init()
    replace_list = [
        # ReplaceElement(name="L1_1",
        #                path="https://tezign.oss-cn-shanghai.aliyuncs.com/357467a8790e48f0b9c35b402ec28a1c.png",
        #                tag="L1",
        #                type="icon",
        #                info={}),
        # ReplaceElement(name="L2_1",
        #                path="https://tezign.oss-cn-shanghai.aliyuncs.com/730c369ad055f9572cb514d9446a4721.png",
        #                tag="L2",
        #                type="icon",
        #                info={}),
        ReplaceElement(name="T1_1",
                       path="https://tezign.oss-cn-shanghai.aliyuncs.com/0ed83e67ed23402d8d30e3230dac3ab4.png?Expires=1565689997&OSSAccessKeyId=LTAIiH7NZflLSZy3&Signature=Tw%2FW0W9Y%2F6dn0TOvC0XKEgmtq8Y%3D",
                       tag="T1",
                       type="icon",
                       info={}),
        # ReplaceElement(name="G1_1",
        #                path="https://tezign.oss-cn-shanghai.aliyuncs.com/9d01d7202dde4fd0bee1a9fad4928422.png?Expires=1565689997&OSSAccessKeyId=LTAIiH7NZflLSZy3&Signature=RAMaj48XqQcDp002qzRfxAt4Kqc%3D",
        #                tag="G1",
        #                type="icon",
        #                info={}),
        # ReplaceElement(name="T1_1",
        #                path="/Users/yangshujun/workspace/AI2Design/Font/fonts汉仪瘦金书.ttf",
        #                type="text", tag="T1",
        #                info={"FontSize": 85, "FontType": "\u6c49\u4eea\u4e2d\u5706\u7b80",
        #                      "text": "\u62a268\u5143\u793c\u5305\r\r\r"}),
        ReplaceElement(name="T2_1",
                       path="/Users/yangshujun/workspace/AI2Design/Font/fonts汉仪瘦金书.ttf",
                       type="text",
                       tag="T2",
                       info={"FontSize": 40, "FontType": "\u6c49\u4eea\u4e2d\u5706\u7b80",
                             "text": "2\u4ef6\u51cf10\r\r\r"}),
    ]
    obj.run(replace_list=replace_list)
    model.compose().show()
    pass
