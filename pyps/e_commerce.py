# -*- coding: utf-8 -*- 
# @Time     : 2019-07-31 18:48
# @Author   : binger
from pyps.layer.constant import TYPE_OTHER

mapper_info = {
    "背景": "B1",
    "商品主图形": "G1",
    "人物主图形": "G1",
    "主标题": "T1",
    "副标题": "T2",
    "互动文案": "T3",
    "段落文案": "T3",
    "互动背景": "R1",
    "活动标签": "L2",
    "LOGO": "L1",
    "贴边装饰": "G3",
    "碎片装饰": "G3",
    "平铺装饰": "G3",
    "区域装饰": "R1",
    "线框装饰": "R1",
    "线条装饰": "R2",
}


def get_type(name):
    return mapper_info.get(name, TYPE_OTHER)[0]


def mapper(name):
    return mapper_info.get(name, TYPE_OTHER)


if __name__ == "__main__":
    pass
