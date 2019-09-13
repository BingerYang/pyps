# -*- coding: utf-8 -*-
import numpy as np


def get_cluster_feature(psd_cluster, clusters_order_name):
    # 1、计算主kv: 主元素的特征分析（长宽比、占框架的面积比）
    # 2、计算目标框架: 主元素长宽比、对齐方式（文字部分）
    # 3、针对各个特征维度给出加权分
    # 4、与每条框架计算匹配相似度：欧式距离

    bg_area = psd_cluster.size[0] * psd_cluster.size[1]
    cluster_feature_num = 7
    cluster_list = psd_cluster.to_list()
    feature_psd = np.zeros((len(cluster_list), cluster_feature_num), dtype=float)

    clusters_info = {cluster["name"]: cluster["layers"] for cluster in cluster_list}

    for i, name in enumerate(clusters_order_name):
        layer_list = clusters_info.get(name, None)
        if layer_list:
            rect = [99999, 99999, 0, 0]
            element_area = 0
            cluster_rect = [0, 0, 0, 0]
            for layer in layer_list:
                rect[0] = min(layer.core.xmin, rect[0])
                rect[1] = min(layer.core.ymin, rect[1])
                rect[2] = max(layer.core.xmax, rect[2])
                rect[3] = max(layer.core.ymax, rect[3])
                element_area += layer.width * layer.height

            for layer in layer_list:
                cluster_rect[0] += (layer.core.xmin - rect[0]) / (rect[2] - rect[0] + 1)
                cluster_rect[1] += (layer.core.ymin - rect[1]) / (rect[3] - rect[1] + 1)
                cluster_rect[2] += (layer.core.xmax - rect[0]) / (rect[2] - rect[0] + 1)
                cluster_rect[3] += (layer.core.ymax - rect[1]) / (rect[3] - rect[1] + 1)

            rect_area = (rect[2] - rect[0] + 1) * (rect[3] - rect[1] + 1)

            # 元素组占画布面积比
            element_ratio = round(rect_area / bg_area, 4)

            # 元素组宽高比
            w_h_ratio = round((rect[2] - rect[0] + 1) / (rect[3] - rect[1] + 1), 4)

            # 元素组成员占元素组外接矩形面积比
            element_area_ratio = round(element_area / rect_area, 4)

            # 元素组成员坐标平均值
            mean_list = [round(v / len(layer_list), 4) for v in cluster_rect]
            feature_psd[i] = [element_ratio, w_h_ratio, element_area_ratio] + mean_list

    return feature_psd.flatten()


def filter_feature_vector(psd, frames, max_similar_value=1):
    """
    计算输入psd与模板相似度值
    :param psd: 输入psd组信息
    :param frames: 输入模板组信息
    :param max_similar_value: 输入模板组信息
    :return:
    """
    psd_cluster = psd.cluster
    clusters_order_name = [cluster["name"] for cluster in psd_cluster.to_list()]
    psd_vector = get_cluster_feature(psd_cluster, clusters_order_name)
    for i in range(len(frames) - 1, -1, -1):
        frame_cluster = frames[i].cluster
        frame_vector = get_cluster_feature(frame_cluster, clusters_order_name)
        value = np.linalg.norm(psd_vector - frame_vector)
        if value >= max_similar_value:
            frames.pop(i)
        else:
            frames[i].feature_value = frame_vector
