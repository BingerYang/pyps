# -*- coding: utf-8 -*- 
# @Time     : 2019-09-12 15:53
# @Author   : binger

from psd_tools import PSDImage
from psd_tools.constants import ChannelID, ColorMode
from psd_tools.api.pil_io import _create_channel as create_channel
from PIL import Image
import math
import numpy as np


class PsdParser(object):
    def __init__(self, path):
        self._path = path
        self._size = None
        self._pil_data_list = []

    def parse(self, is_crop=False, is_cache=False, is_include_pil=True):
        psd_img = PSDImage.open(self._path)
        self._size = psd_img.size

        layer_info_list = []
        for layer in psd_img:
            if layer.visible:
                info = self.parse_layer(layer, is_crop, is_cache, is_include_pil)
                layer_info_list.append(info)
        return layer_info_list, self._size

    def parse_layer(self, layer, is_crop=False, is_cache=False, is_include_pil=True):
        # 解析图层及该图层父级的图层名
        layer_name = layer.name.strip()
        layer_parent_name = layer.parent.name.strip()
        if layer_parent_name == 'Root':
            layer_parent_name = None
        layer_info = {'name': layer_name, 'group_name': layer_parent_name}

        layer_image = layer.topil()
        if layer_image is None:
            # 空图层过滤掉
            return
        if layer_image.mode == 'CMYK':
            layer_image = self._convert_cmyk_to_rgba(layer, layer_image)

        if is_crop:
            layer_image, rect = self.cut_layer_at_rect(layer_image, layer.bbox,
                                                       [0, 0, self._size[0], self._size[1]])
            if layer_image.mode == 'CMYK':
                layer_image = layer_image.convert('RGBA')
            from pyps.layer.img import cut_nonzero
            layer_image, tmp_rect = cut_nonzero(layer_image)
            xmin = rect[0] + tmp_rect[0]
            ymin = rect[1] + tmp_rect[1]
            xmax = xmin + layer_image.width
            ymax = ymin + layer_image.height
        else:
            xmin, ymin, xmax, ymax = layer.bbox
        layer_info["xmin"] = xmin
        layer_info["ymin"] = ymin
        layer_info["xmax"] = xmax
        layer_info["ymax"] = ymax
        if is_include_pil:
            layer_info["data"] = layer_image
        self._pil_data_list.append(layer_image)

        if layer.kind == "type":
            layer_info.update({'type': 'text', 'text': layer.text})
            layer_info.update(self.retrieve_font(layer))
        else:
            layer_info.update({"type": "image"})

        # 是否对图层信息进行缓存
        if is_cache:
            layer_info["path"] = ""
        else:
            layer_info["path"] = ""
        # 其他
        layer_info.update({'generate': False})
        is_optional_layer = not layer_info['group_name'] and not layer.is_visible()
        layer_info.update({'is_optional_layer': is_optional_layer})

        return layer_info

    @property
    def pil_data_list(self):
        return self._pil_data_list

    def _get_cmyk_alpha(self, layer, header):
        """

        :param layer:
        :param header:
        :return:
        """
        if header.color_mode == ColorMode.BITMAP:
            raise NotImplementedError
        width, height = layer.width, layer.height
        alpha = None
        for ci, cd in zip(layer._record.channel_info, layer._channels):
            if ci.id in (
                    ChannelID.USER_LAYER_MASK, ChannelID.REAL_USER_LAYER_MASK
            ):
                continue
            channel = cd.get_data(width, height, header.depth, header.version)
            channel_image = create_channel((width, height), channel, header.depth)
            if ci.id == ChannelID.TRANSPARENCY_MASK:
                alpha = channel_image
        return alpha

    def _convert_cmyk_to_rgba(self, layer, layer_image):
        """
        将cmyk格式的图片转成RGBA格式之后尽量保存alpha通道
        :param layer:
        :param layer_image:
        :return:
        """
        header = layer._psd._record.header
        if header.channels >= 4:
            layer_image = layer_image.convert('RGB')
            alpha = self._get_cmyk_alpha(layer, header)
            # alpha = alpha.crop((max(0, -xmin),
            #                     max(0, -ymin),
            #                     min(xmax - xmin, psd_width - 1 - xmin),
            #                     min(ymax - ymin, psd_height - 1 - ymin)))
            if alpha is None:
                return layer_image.convert('RGBA')
            try:
                layer_image.putalpha(alpha)
            except:
                import cv2
                layer_image = np.asarray(layer_image)
                alpha = np.asarray(alpha)
                channels_layer_image = len(layer_image.shape) - 1 if len(layer_image.shape) == 2 else layer_image.shape[
                    2]
                channels_alpha = len(alpha.shape) - 1 if len(alpha.shape) == 2 else alpha.shape[2]
                if channels_layer_image == 1:
                    layer_image = cv2.cvtColor(layer_image, cv2.COLOR_GRAY2RGB)
                elif channels_layer_image == 4:
                    layer_image = cv2.cvtColor(layer_image, cv2.COLOR_RGBA2RGB)

                if channels_alpha == 3:
                    alpha = cv2.cvtColor(alpha, cv2.COLOR_RGB2GRAY)
                elif channels_alpha == 4:
                    alpha = cv2.cvtColor(alpha, cv2.COLOR_RGBA2GRAY)
                alpha = np.expand_dims(alpha, axis=-1)
                layer_image = np.concatenate((layer_image, alpha), axis=2)
                layer_image = Image.fromarray(layer_image)
            return layer_image
        return layer_image.convert('RGBA')

    @classmethod
    def retrieve_font(cls, layer):
        """
        解析图层中的字体信息
        :param layer: 图层对象
        :return: 字体信息字典
        """
        font_set = layer._engine_data['DocumentResources']['FontSet'][0]
        font_info = layer._engine_data['EngineDict']['StyleRun']['RunArray'][0]['StyleSheet']['StyleSheetData']
        if 'FontSize' in font_info.keys():
            font_size = font_info['FontSize']
        else:
            font_size = 0
        if 'FillColor' in font_info:
            font_color = font_info['FillColor']['Values']
        else:
            font_color = [1.0, 1.0, 1.0, 1.0]

        if len(font_color) == 5:
            r = (1 - font_color[4]) * (1 - font_color[1])
            g = (1 - font_color[4]) * (1 - font_color[2])
            b = (1 - font_color[4]) * (1 - font_color[3])
            a = font_color[0]
            font_color = [a, r, g, b]
        for i in [0, 1, 2, 3]:
            font_color[i] = int(255 * font_color[i])

        font = str(font_set['Name'].value)

        # 防止出现负数的情况
        if layer.transform[0] > 0 and layer.transform[3] > 0:
            font_size = int(font_size * math.sqrt(layer.transform[0] * layer.transform[3]))
        else:
            font_size = int(font_size)
        return {'fontFamily': font, 'fontSize': font_size, 'color': font_color}

    @staticmethod
    def cut_layer_at_rect(layer_image, layer_rect, rect):
        from pyps.layer.position import cut_layer_area
        cross = cut_layer_area(layer_rect, rect)
        xmin_at_image = max(0, rect[0] - layer_rect[0])
        ymin_at_image = max(0, rect[1] - layer_rect[1])
        xmax_at_image = xmin_at_image + cross[2] - cross[0]
        ymax_at_image = ymin_at_image + cross[3] - cross[1]
        layer_image = layer_image.crop((xmin_at_image, ymin_at_image,
                                        xmax_at_image, ymax_at_image))
        return layer_image, cross


if __name__ == "__main__":
    pass
