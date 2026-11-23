"""会话内结果缓存；按完整参数与后端区分，体积受限，不写入磁盘。"""
from collections import OrderedDict
from dataclasses import asdict
import json


class ResultCache:
    def __init__(self, budget=128 * 1024**2):
        self.budget = budget
        self.entries = OrderedDict()
        self.bytes = 0

    def key(self, project, backend, preview=False):
        return json.dumps([asdict(project), backend, preview], sort_keys=True)

    def clear(self):
        """释放缓存引用；当前显示的结果由界面继续持有。"""
        self.entries.clear()
        self.bytes = 0

    def get(self, key):
        if key not in self.entries:
            return None
        self.entries.move_to_end(key)
        return self.entries[key][0]

    def put(self, key, result):
        size = sum(getattr(result, name).nbytes for name in
                   ("z", "x", "intensity", "gaussian_w", "r86", "transmission"))
        if size > self.budget:
            return
        if key in self.entries:
            self.bytes -= self.entries.pop(key)[1]
        while self.entries and self.bytes + size > self.budget:
            self.bytes -= self.entries.popitem(last=False)[1][1]
        self.entries[key] = result, size
        self.bytes += size
