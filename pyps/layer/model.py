# -*- coding: utf-8 -*- 
# @Time     : 2019-08-01 14:31
# @Author   : binger
from funcy import project
from .img import get_outer_rect


class LayerCore(object):
    _fields = {"xmin", "ymin", "xmax", "ymax", "tag", "name", "group", "data"}

    def __init__(self, info):
        assert self._fields.issubset(set(info.keys()))
        self.__dict__.update(info)

    def update(self, info):
        self.__dict__.update(info)

    def __setattr__(self, name, value):
        if name in self.__dict__:
            self.__dict__[name] = value
        else:
            raise ValueError("New variables are not allowed!")

    def __getattr__(self, name):
        try:
            value = self.__dict__[name]
        except KeyError as e:
            # if name in LayerCore._fields:
            #     raise e
            # else:
            #     value = None
            value = None

        return value

    def __getitem__(self, name):
        return self.__dict__[name]

    def to_dict(self):
        return self.__dict__


class LayerBase(object):

    def __init__(self, layer=None):
        self.core = None
        layer and self.init_conf(conf=layer)

    def init_conf(self, conf: dict, is_replace=True):
        if is_replace:
            self.core = LayerCore(conf)
        else:
            self.core.update(conf)

    @property
    def size(self):
        return self.width, self.height

    @property
    def width(self):
        return self.core.xmax - self.core.xmin + 1

    @property
    def height(self):
        return self.core.ymax - self.core.ymin + 1

    @property
    def pil(self):
        return self.core.data

    @property
    def center(self):
        return (self.core.xmax + self.core.xmin) / 2, (self.core.ymax + self.core.ymin) / 2

    def replace_pil_at_rect(self, pil, xmin, ymin):
        self.update_rect([xmin, ymin, xmin + pil.width, ymin + pil.height])
        self.core.data = pil

    def replace_pil(self, pil, is_start_align=False, is_center_align=False):
        """
        更新图层的 image 信息，从起点或者中心点开始对齐（二选一）
        :param pil: image 对象
        :param is_start_align: 以起点对齐方式更新
        :param is_center_align: 以中心点方式不动进行对齐
        :return:
        """
        if is_start_align:
            self.replace_pil_at_rect(pil, self.core.xmin, self.core.ymin)
        if is_center_align:
            xmin = self.core.xmin + (self.width - pil.width) / 2
            ymin = self.core.ymin + (self.height - pil.height) / 2
            self.replace_pil_at_rect(pil, xmin, ymin)

    @property
    def rect_info(self):
        return project(self.core.to_dict(), self.core._fields)

    def copy(self):
        return self.rect_info

    def update_rect_info(self, info):
        self.core.update(info)

    @property
    def rect(self):
        return self.core.xmin, self.core.ymin, self.core.xmax, self.core.ymax

    def update_rect(self, rect):
        self.core.xmin, self.core.ymin, self.core.xmax, self.core.ymax = rect


class Layer(LayerBase):
    def __init__(self, layer=None):
        super(Layer, self).__init__(layer)
        self.state = []

    def move(self, offset: tuple, size: tuple, is_apply=True):
        """
        从起点按尺寸（长宽）进行移动
        :param offset:
        :param size:
        :param is_apply:
        :return:
        """

        xmin = self.core.xmin + offset[0]
        ymin = self.core.ymin + offset[1]
        xmax = xmin + size[0] - 1
        ymax = ymin + size[1] - 1
        if is_apply:
            self.update_rect_info(dict(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
        return xmin, ymin, xmax, ymax

    def cut_for_show_area(self, psd_size: tuple, is_apply=False):
        """
        剪切图层在psd中可显示的区域
        :param psd_size: psd 画布可显示的区域
        :param is_apply: 是否更新到图层
        :return:
        """
        xmin = max(0, - self.core.xmin)
        ymin = max(0, - self.core.xmin)
        width = min(self.width - 1, psd_size[0] - 1 - self.core.xmin)
        height = min(self.height - 1, psd_size[1] - 1 - self.core.ymin)
        if is_apply:
            self.replace_pil_at_rect(self.pil.crop((xmin, ymin, width, height)), max(0, self.core.xmin),
                                     max(0, self.core.ymin))
        return xmin, ymin, width, height

    def get_external_boundary(self, is_apply=False):
        xmin, ymin, crop_width, crop_height = get_outer_rect(self.pil)

        is_apply and self.move(offset=(xmin, ymin), size=(crop_width, crop_height))
        return xmin, ymin, crop_width, crop_height

    def resize_by_center(self, width, height, is_apply=False):
        return self.move(offset=((self.width - width) / 2, (self.height - height) / 2), size=(width, height),
                         is_apply=is_apply)


if __name__ == "__main__":
    layer = Layer()
    layer.init_conf({"xmin": 1, "ymin": 2, "xmax": 33, "ymax": 35})
    layer2 = Layer()
    layer2.init_conf({"xmin": 11, "ymin": 22, "xmax": 333, "ymax": 355})
    print(layer2.width)
    print(layer2.core.xmin)
    print(layer2.rect)
    print(layer2.rect_info)

    print(layer.width)
    print(layer.core.xmin)
    layer.update_rect_info({"xmin": 0, "ymin": 22, "xmax": 333, "ymax": 355})
    print(1111, layer.core.xmin)
    print(layer.rect)
    print(layer.rect_info)
    print(layer.__dict__)
