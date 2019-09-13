# -*- coding: utf-8 -*- 
# @Time     : 2019-07-30 17:32
# @Author   : binger


"""
只要实现图层信息的位置变化
"""


def get_scrap_edge(layer, size, edge=2):
    """
    判断区域(x1, y1, x2, y2)是否为切边元素，切住哪个边
    :param layer: 图层
    :param size:  区域
    :param edge:  区域起始行
    :return:    0：不切边，1：切边
    """

    width, height = size
    scrap = [0, 0, 0, 0]  # [左, 上 ，右, 下]

    if 0 <= layer.core.xmin <= edge:
        scrap[0] = 1
    if width - 1 - edge <= layer.core.xmax <= width - 1:
        scrap[2] = 1

    if 0 <= layer.core.ymin <= edge:
        scrap[1] = 1
    if height - 1 - edge <= layer.core.ymax <= height - 1:
        scrap[3] = 1
    return scrap


def cut_psd_show_area(rect: tuple, psd_size: tuple):
    """
    获取 psd 中可显示的区域
    :param rect:
    :param psd_size:
    :return:

    """
    return cut_layer_area(rect, range_rect=(0, 0, psd_size[0] - 1, psd_size[1] - 1))


def cut_layer_area(rect: tuple, range_rect: tuple):
    """
    获取 rect 位于 range_rect 的区域
    :param rect:
    :param range_rect:
    :return:
    """

    xmin = max(range_rect[0], rect[0])
    ymin = max(range_rect[1], rect[1])
    xmax = min(rect[2], range_rect[2])
    ymax = min(rect[3], range_rect[3])

    return xmin, ymin, xmax, ymax


def replace_at_same_center(center: tuple, new_size: tuple):
    """

    :param center: 元素区域图层信息的中心
    :param new_size: 新替换的尺寸
    :return:
    """
    new_width, new_height = new_size
    xmin = int(center[0] - (new_width - 1) / 2)
    ymin = int(center[0] - (new_height - 1) / 2)
    xmax = xmin + new_width - 1
    ymax = ymin + new_height - 1
    return xmin, ymin, xmax, ymax


def resize_by_rate_to_target(size: tuple, to_size: tuple, use_small=True):
    """
    按前后的尺寸比率（尽可能适应扩展后的目标）等比例目标的定宽或者定高进行扩展
    :param size:
    :param to_size:
    :param use_small:
    :return:
    """
    width, height = size
    to_w, to_h = to_size
    w_rate = to_w / float(width)
    h_rate = to_h / float(height)
    if w_rate > h_rate:  # 目标图形比较宽
        if use_small:
            dim = (max(int(width * h_rate), 1), max(int(to_h), 1))
        else:
            dim = (max(int(to_w), 1), max(int(height * w_rate), 1))
    else:
        if use_small:
            dim = (max(int(to_w), 1), max(int(height * w_rate), 1))
        else:
            dim = (max(int(width * h_rate), 1), max(int(to_h), 1))
    return dim


def extend_rect_info_range(rect_info, merged_rect_info):
    rect_info['xmin'] = min(rect_info['xmin'], merged_rect_info['xmin'], 99999)
    rect_info['ymin'] = min(rect_info['ymin'], merged_rect_info['ymin'], 99999)
    rect_info['xmax'] = max(rect_info['xmax'], merged_rect_info['xmax'], 0)
    rect_info['ymax'] = max(rect_info['ymax'], merged_rect_info['ymax'], 0)
    return rect_info


def is_inclusion_relation(included_rect, rect):
    """
    获取 included_rect 是否位于 rect 中
    :param included_rect:
    :param rect:
    :return:
    """
    v_list = list(map(lambda v: v[0] > v[1], zip(included_rect, rect)))
    # 包含的情况：True，True，False，False
    return all(v_list[:2]) and not any(v_list[2:])


def layer_to_width_or_height(w_h_ratio, to_width=None, to_height=None):
    """
    size扩展到定宽或者定高
    :param w_h_ratio: 按照照定长宽比扩展
    :param to_height:
    :param to_width:
    :return:
    """

    if to_height:
        size = (max(int(w_h_ratio * to_height), 1), max(int(to_height), 1))
    else:
        size = (max(int(to_width), 1), max(int(to_width / w_h_ratio), 1))
    return size


# old


def move_by_img(layer: dict, move_info: dict, is_replace=False):
    """
    对图层（layer）区域进行移动，移动变量 move
    layer, move 都包含xmin, ymin, xmax, ymax, width, height
    :param layer:
    :param move_info:
    :param is_replace: 是否替换 layer 对应的信息
    :return:
    """
    move_x = move_info["xmin"]
    move_y = move_info["ymin"]

    info = dict()
    info['xmin'] = layer['xmin'] + move_x
    info['ymin'] = layer['ymin'] + move_y
    info['xmax'] = info['xmin'] + move_info["width"] - 1
    info['ymax'] = info['ymin'] + move_info["height"] - 1

    info['width'] = move_info["width"]
    info['height'] = move_info["height"]
    is_replace or layer.update(info)
    return info


def display_region_in_img(layer: dict, psd_size: tuple):
    """
    计算图层位于image中可显示的区域
    :return:
    """
    xmin = max(0, - layer['xmin'])
    ymin = max(0, - layer['ymin'])
    width = min(layer['xmax'] - layer['xmin'], psd_size[0] - 1 - layer['xmin'])
    height = min(layer['ymax'] - layer['ymin'], psd_size[1] - 1 - layer['ymin'])
    return xmin, ymin, width, height


if __name__ == "__main__":
    pass
