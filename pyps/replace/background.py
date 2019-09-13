# -*- coding: utf-8 -*- 
# @Time     : 2019-09-04 15:23
# @Author   : binger
from pyps.utils.common import read_image
from pyps.layer import img


class BackGround(object):
    def __init__(self, size, layer):
        self.size = size
        self.layer = layer

    def replace(self, replace_element):
        pil = read_image(replace_element.file_path)
        pil, _ = img.cut_nonzero(pil)
        pil = img.crop_blank_region(pil)
        pil = img.resize_by_target(pil, self.size, use_small=False)

        self.layer.replace_pil(pil, is_center_align=True)


if __name__ == "__main__":
    pass
