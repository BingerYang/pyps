# -*- coding: utf-8 -*- 
# @Time     : 2019-09-10 15:29
# @Author   : binger

from pyps.algorithm.transfer import coordinate_transfer, relative_transfer
from pyps.layer import constant


def load_cluster_layers(cluster):
    layer_list = cluster["layers"]
    if cluster["type"] == constant.TYPE_RELATION:
        layer_list = layer_list.copy()
        layer_list.append(cluster["layer"])
    return layer_list


def extend_rect_range(rect, merged_rect):
    rect[0] = min(rect[0], merged_rect[0], 99999)
    rect[1] = min(rect[1], merged_rect[1], 99999)
    rect[2] = max(rect[2], merged_rect[2], 0)
    rect[3] = max(rect[3], merged_rect[3], 0)
    return rect


def _load_out_rect(cluster):
    if cluster["type"] == constant.TYPE_RELATION:
        # rect = [10000, 10000, 0, 0]
        # [extend_rect_range(rect, layer.rect) for layer in cluster["layers"] + [cluster["layer"],]]
        rect = extend_rect_range(list(cluster["layer"].rect), cluster["rect"])
    else:
        # rect = [10000, 10000, 0, 0]
        # [extend_rect_range(rect, layer.rect) for layer in cluster["layers"]]
        rect = cluster["rect"]
    return rect


def barycentric_interpolation(inputs, target_size, templates_cluster):
    """
    三角插值
    :param inputs: 输入图层信息
    :param target_size: 目标尺寸
    :param templates_cluster: 模板图层信息
    :return:
    """
    assert len(templates_cluster) == 3

    def triangle_area(pt1, pt2, pt3):
        """
        已知三角形顶点计算面积
        :param pt1: (x1,y1)
        :param pt2: (x2,y2)
        :param pt3: (x3,y3)
        :return:
        """
        x1, y1 = pt1
        x2, y2 = pt2
        x3, y3 = pt3
        return abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2

    size1, size2, size3 = [psd_cluster.size for psd_cluster in templates_cluster]
    frame1_info = {cluster["name"]: _load_out_rect(cluster) for cluster in templates_cluster[0].to_list()}
    frame2_info = {cluster["name"]: _load_out_rect(cluster) for cluster in templates_cluster[1].to_list()}
    frame3_info = {cluster["name"]: _load_out_rect(cluster) for cluster in templates_cluster[2].to_list()}

    d1 = triangle_area(size1, size2, target_size)
    d2 = triangle_area(size1, size3, target_size)
    d3 = triangle_area(size2, size3, target_size)

    beta1 = d3 / (d1 + d2 + d3)
    beta2 = d2 / (d1 + d2 + d3)
    beta3 = d1 / (d1 + d2 + d3)

    for cluster in inputs.to_list():

        cluster_name = cluster["name"]
        rect = _load_out_rect(cluster)

        if cluster_name in frame1_info:
            rect1 = frame1_info[cluster_name]
            rect1 = coordinate_transfer(rect1, size1, target_size)
            output_rect = [beta1 * v for v in rect1]

        if cluster_name in frame2_info:
            rect2 = frame2_info[cluster_name]
            rect2 = coordinate_transfer(rect2, size2, target_size)
            output_rect += [beta2 * v for v in rect2]

        if cluster_name in frame3_info:
            rect3 = frame3_info[cluster_name]
            rect3 = coordinate_transfer(rect3, size3, target_size)
            output_rect += [beta3 * v for v in rect3]

        for layer in load_cluster_layers(cluster):
            temp_rect = relative_transfer(layer.rect, rect, output_rect)
            layer.update_rect(temp_rect)

    return inputs


def line_interpolation(inputs, target_size, templates_cluster):
    """
    线性内插
    :param inputs: 输入图层信息
    :param target_size: 目标尺寸
    :param templates_cluster: 模板图层信息
    :return:
    """
    assert len(templates_cluster) == 2

    def get_distance(points, pt):
        """
        计算点pt与输入点集的距离
        :param points: 已知输入点集 [(x1, y1), ..., ]
        :param pt: 目标点 (xt, yt)
        :return: 目标点与输入点集的距离（复数）[d1, ..., ]
        """
        distances = []
        for x, y in points:
            distances.append(((x - pt[0]) ** 2 + (y - pt[1]) ** 2) ** 0.5)
        return distances

    templates_size = [psd_cluster.size for psd_cluster in templates_cluster]
    size1, size2 = templates_size[0], templates_size[1]
    frame1_info = {cluster["name"]: _load_out_rect(cluster) for cluster in templates_cluster[0].to_list()}
    frame2_info = {cluster["name"]: _load_out_rect(cluster) for cluster in templates_cluster[1].to_list()}

    d = get_distance(templates_size, target_size)
    beta = d[1] / (d[0] + d[1])
    print("距离: ", beta, 1 - beta)

    for cluster in inputs.to_list():
        # 外接矩形
        cluster_name = cluster["name"]
        rect = _load_out_rect(cluster)

        if cluster_name in frame1_info:
            rect1 = frame1_info[cluster_name]
            rect1 = coordinate_transfer(rect1, size1, target_size)
            output_rect = [beta * v for v in rect1]

        if cluster_name in frame2_info:
            rect2 = frame2_info[cluster_name]
            rect2 = coordinate_transfer(rect2, size2, target_size)
            output_rect[0] += (1 - beta) * rect2[0]
            output_rect[1] += (1 - beta) * rect2[1]
            output_rect[2] += (1 - beta) * rect2[2]
            output_rect[3] += (1 - beta) * rect2[3]

        for layer in load_cluster_layers(cluster):
            temp_rect = relative_transfer(layer.rect, rect, output_rect)
            layer.update_rect(temp_rect)

    return inputs


def vertex_interpolation(inputs, target_size, templates_cluster):
    """
    最近点插值
    :param inputs: 输入图层信息
    :param target_size: 目标尺寸
    :param templates_cluster: 模板图层信息
    :return:
    """
    assert len(templates_cluster) == 1

    size = templates_cluster[0].size
    frame_info = {cluster["name"]: _load_out_rect(cluster) for cluster in templates_cluster[0].to_list()}

    for cluster in inputs.to_list():
        cluster_name = cluster["name"]
        rect = _load_out_rect(cluster)

        if cluster_name in frame_info:
            rect1 = frame_info[cluster_name]
            rect1 = coordinate_transfer(rect1, size, target_size)

            for layer in load_cluster_layers(cluster):
                temp_rect = relative_transfer(layer.rect, rect, rect1)
                layer.update_rect(temp_rect)
    return inputs


def layout_transform(inputs, target_size, templates_cluster):
    """
    选择插值方法
    :param inputs: 输入图层信息
    :param target_size: 目标尺寸
    :param templates_cluster: 模板图层信息
    :return: 插值结果
    """
    if len(templates_cluster) == 1:
        return vertex_interpolation(inputs, target_size, templates_cluster)
    elif len(templates_cluster) == 2:
        return line_interpolation(inputs, target_size, templates_cluster)
    elif len(templates_cluster) >= 3:
        return barycentric_interpolation(inputs, target_size, templates_cluster)
    else:
        return inputs


if __name__ == "__main__":
    pass
