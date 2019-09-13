# -*- coding: utf-8 -*- 
# @Time     : 2019-08-08 15:36
# @Author   : binger
from PIL import Image
from pyps.layer import constant
from pyps.layer.position import is_inclusion_relation
from pyps.layer.img import layer_paste
import numpy as np
import cv2


def get_alignment_type(layers, offset=20):
    """
    获取元素之间的对齐关系
    :param layers:
    :param offset:
    :return: 0 中心，1 左边，2右边
    """

    # 0: Center, 1: Left, 2: Right, 3: Keep, -1: None
    index = 0
    left_col, center_col, right_col = [], [], []
    distance = []
    for l in layers:
        left_col.append(l.core.xmin)
        center_col.append(l.center[0])
        right_col.append(l.core.xmax)
        if index > 0:
            distance.append([
                abs(left_col[index] - left_col[0]),
                abs(center_col[index] - center_col[0]),
                abs(right_col[index] - right_col[0]),
                offset
            ])  # 因为align=True, 说明需要取的是组之间的对齐关系，所以使用传进来的默认参数
        index += 1
    if len(distance) == 0:
        return 0
    distance = np.asarray(distance)
    distance = np.mean(distance, axis=0)
    alignment = np.argmin(distance)
    return alignment


def layer_distance(rect1, rect2):
    """
    计算两个图层在水平X和垂直Y方向的距离与两图层长度之和的占比：
    :param rect1: 图层1
    :param rect2: 图层2
    :return: distx, disty
    """
    distx = max(rect1[0] - rect2[2], rect2[1] - rect1[2])
    disty = max(rect1[1] - rect2[3], rect2[1] - rect1[2])

    return distx, disty


def having_bind_relationship(rect1, rect2, direct=0, iou=0.8, dist=None):
    """
    比较两个图层在水平或垂直方向是否存在绑定关系：
    :param rect1: 区域
    :param rect2: 区域
    :param direct: 水平为0，垂直为1
    :param iou: 重叠度百分比
    :param dist: 两图层中心距相对于两图层宽度/高度之和的比例
    :return: True 绑定, False 非绑定
    """
    if direct == 0:
        intersect = min(rect1[3], rect2[3]) - max(rect1[1], rect2[1]) + 1
        union = min(rect1[3] - rect1[1] + 1, rect2[3] - rect2[1] + 1)
        distance, _ = layer_distance(rect1, rect2)

    else:
        intersect = min(rect1[2], rect2[2]) - max(rect1[1], rect2[1]) + 1
        union = min(rect1[2] - rect1[1] + 1, rect2[2] - rect2[1] + 1)
        _, distance = layer_distance(rect1, rect2)

    if dist is None:
        return True if intersect / union >= iou else False
    else:

        return True if intersect / union >= iou and abs(distance) <= dist else False


def load_intersect_size(rect1, rect2):
    """
    载入相交尺寸的大小
    :param rect1:
    :param rect2:
    :return:
    """
    # 0: row1, 1: col1, 2: row2, 3: col2
    left_line = max(rect1[0], rect2[0])
    right_line = min(rect1[2], rect2[2])
    top_line = max(rect1[1], rect2[1])
    bottom_line = min(rect1[3], rect2[3])

    intersect_width, intersect_height = max(right_line - left_line + 1, 0), max(bottom_line - top_line + 1, 0)
    return intersect_width, intersect_height


def get_element_title_background(layer, layers, bg_size: tuple):
    """
    获取元素的文字背景空白区域
    :param layers: PSD所有层信息
    :param layer:   要替换的层
    :param bg_size:   画布PSD的尺寸
    :return:    black:  背景空白区域图
    """
    data = Image.new('RGBA', bg_size, (255, 255, 255, 0))
    for l in layers:
        if l == layer or l.pil is None:
            continue
        if l.core.tag == constant.TYPE_GRAPH_MAIN or l.core.group in [constant.TYPE_TEXT, constant.TYPE_LOGO]:
            data = layer_paste(data, l.pil, l.core.xmin, l.core.ymin)
    return data


def load_background_pil(layer, layers, size):
    """
    粘贴生成与文本图层相关的背景图片
    :param layer: 文本图层
    :param layers: 与文本图层先关的图层
    :param size: 待生成的背景图的大小
    :return: 背景图对象
    """
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    for l in layers:
        if l != layer:
            img = layer_paste(img, l.core.data, l.core.xmin, l.core.ymin)
    return img


def get_title_background(layer, layers, width, height):
    """
    获取背景空白区域
    :param layers: PSD所有层信息
    :param layer:   要替换的层
    :param width:   PSD宽
    :param height:  PSD高
    :return:    black:  背景空白区域图
    """
    data = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    find_bind_area = False
    # 获取替换层在当前组背景的空白区域
    for l in layers:
        if not find_bind_area:
            if l.core.tag == constant.TYPE_RELATION_AREA:
                if is_inclusion_relation(layer.rect, l.rect) and l.core.data:
                    # 创造元素字体背景
                    data = layer_paste(data, l.core.data, l.core.xmin, l.core.ymin)
                    find_bind_area = True
        else:
            # if l.name != layer.name and l['generate'] and l.data is not None:
            if l.core.name != layer.core.name and l.core.data is not None:
                data = layer_paste(data, l.core.data, l.core.xmin, l.core.ymin)
    # 获取替换层在整体背景的空白区域
    if not find_bind_area:
        for l in layers:
            if l.core.group == constant.TYPE_BACKGROUND or l.core.tag in [constant.TYPE_GRAPH_SUB,
                                                                          constant.TYPE_GRAPH_DECORATION] or l.core.data is None:
                continue
            # elif l.name != layer.name and l['generate'] and l['data'] is not None:
            elif l.core.name != layer.core.name and l.core.data is not None:
                data = layer_paste(data, l.core.data, l.core.xmin, l.core.ymin)

    return data


def get_element_title_background(layer, layers, width, height):
    """
    可以从簇中实现
    获取元素的文字背景空白区域
    :param layers: PSD所有层信息
    :param layer:   要替换的层
    :param width:   PSD宽
    :param height:  PSD高
    :return:    black:  背景空白区域图
    """
    data = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    for l in layers:
        if l == layer or l.core.data is None:
            continue
        if l.core.group in [constant.TYPE_TEXT, constant.TYPE_LOGO] or l.core.tag == constant.TYPE_GRAPH_MAIN:
            data = layer_paste(data, l.core.data, l.core.xmin, l.core.ymin)
    return data


def get_region_overlap(bg_im, layer, layers, x1, y1, x2, y2):
    """
    获取区域(x1, y1, x2, y2)内所有与layer重叠的主元素
    :param bg_im: 背景图片
    :param layer: 主图层
    :param layers: 所有图层
    :param x1:  区域起始列
    :param y1:  区域起始行
    :param x2:  区域结束列
    :param y2:  区域结束行
    :return: 重叠的图层名字列表，重叠的面积列表
    """
    overlap_layers = []
    overlap_area = []
    img = cv2.cvtColor(np.asarray(bg_im), cv2.COLOR_RGBA2BGRA)
    height, width = img.shape[0], img.shape[1]
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(width - 1, x2), min(height - 1, y2)
    if x1 < 0 or y1 < 0 or x2 > width - 1 or y2 > height - 1 or x1 > x2 or y1 > y2:
        overlap_layers.append("背景")
        overlap_area.append(0)
        return overlap_layers, overlap_area

    def is_related(l, layer):
        is_find = False
        T_L_TYPE_LIST = (constant.TYPE_TEXT, constant.TYPE_LOGO)
        if layer.core.group in T_L_TYPE_LIST:
            if l.core.group in T_L_TYPE_LIST or l.core.tag in (constant.TYPE_GRAPH_MAIN, constant.TYPE_RELATION_AREA):
                is_find = True
        else:
            if l.core.group in T_L_TYPE_LIST or l.core.tag == constant.TYPE_GRAPH_MAIN:
                is_find = True
        return is_find

    for l in layers:
        if l == layer:
            continue
        if is_related(l, layer):
            left = int(max(x1, l.core.xmin))
            right = int(min(x2, l.core.xmax))
            top = int(max(y1, l.core.ymin))
            bottom = int(min(y2, l.core.ymax))
            if right >= left and bottom >= top:
                # 正常相交
                box_intersection = img[top:bottom + 1, left:right + 1, :]
                canny_box_intersection = cv2.Canny(box_intersection, 100, 200)
                point = np.argwhere(canny_box_intersection == 255)
                if point.size > 0:
                    y, x, h, w = cv2.boundingRect(point)
                    overlap_layers.append(l.core.name)
                    overlap_area.append((h + 1) * (w + 1))

    return overlap_layers, overlap_area


def get_elements_overlap(layers, element_names, width, height):
    """
    获取需要替换的元素最初始的重叠关系
    :param layers:
    :param element_names:
    :param width:
    :param height:
    :return:
    """
    element_overlap = []
    if element_names:
        for layer in layers:
            if layer.core.name in element_names and layer.core.data:
                overlap_info = {}
                # 获取除了当前元素以外的背景图片
                if layer.core.group == [constant.TYPE_TEXT, constant.TYPE_LOGO]:
                    layer_bg = get_title_background(layer, layers, width, height)
                else:
                    layer_bg = get_element_title_background(layer, layers, width, height)
                overlap_layers, overlap_area = get_region_overlap(layer_bg, layer, layers,
                                                                  layer.core.xmin,
                                                                  layer.core.ymin,
                                                                  layer.core.xmax,
                                                                  layer.core.ymax)
                overlap_info['name'] = layer.core.name
                overlap_info['overlap_layer'] = overlap_layers
                overlap_info['overlap_area'] = overlap_area

                element_overlap.append(overlap_info)

    return element_overlap


if __name__ == "__main__":
    pass
