# -*- coding: utf-8 -*- 
# @Time     : 2019-09-04 14:39
# @Author   : binger


class CrossLine(object):
    def __init__(self, comparator, comparatee):
        self.comparator = comparator
        self.comparatee = comparatee
        self.cross = self.load_location_info()
        self.align = self.get_align()

    @property
    def is_cross(self):
        return self.cross[1] > self.cross[0]

    def load_location_info(self):
        return max(self.comparator[0], self.comparatee[0]), min(self.comparator[1], self.comparatee[1])

    def get_align(self):
        cross = self.load_location_info()

        if cross[0] == self.comparatee[0] and cross[1] != self.comparatee[1]:
            align = 0
        elif cross[0] != self.comparatee[0] and cross[1] == self.comparatee[1]:
            align = 2
        else:
            align = 1
        return align

    def replace(self, width):
        cross_len = (self.cross[1] - self.cross[0] + 1) / (self.comparator[1] - self.comparator[0] + 1) * width
        if self.align == 2:
            start = self.comparatee[1] - (cross_len - 1)
            return start, start + width - 1
        elif self.align == 0:
            end = self.comparatee[0] + cross_len - 1
            return end - width + 1, end
        else:
            center = (self.cross[0] + self.cross[1]) / 2
            return center - width / 2, center + width / 2


class CrossReplaceRule(object):
    def __init__(self, area, rect):
        self.area = area
        self.rect = rect
        self._cross_x = CrossLine((self.rect[0], self.rect[2]), (self.area[0], self.area[2]))
        self._cross_y = CrossLine((self.rect[1], self.rect[3]), (self.area[1], self.area[3]))

    def replace(self, size: tuple):
        new_rect = [0] * 4
        new_rect[0], new_rect[2] = self._cross_x.replace(size[0])
        new_rect[1], new_rect[3] = self._cross_y.replace(size[1])
        return new_rect


if __name__ == "__main__":
    pass
