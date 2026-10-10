"""好用例：规范的 API 客户端（冒烟测试用，应零 blocker、exit 0）。"""
import os
import time

import requests


class ApiError(Exception):
    """API 错误：人话 message + 原始 code 保留排查用。"""

    def __init__(self, message, code=None):
        """初始化错误对象。"""
        super().__init__(message)
        self.code = code


class ApiClient:
    """示例 API 客户端：凭证走环境变量，超时/重试/限流收敛在内部。"""

    def __init__(self, timeout=30):
        """初始化客户端，读取环境变量中的凭证与地址。"""
        self.base_url = os.environ.get("API_BASE_URL", "https://api.example.com/v1").rstrip("/")
        self.api_token = os.environ.get("API_TOKEN")
        if not self.api_token:
            raise ValueError("缺 API_TOKEN 环境变量")
        self.timeout = timeout
        self._last_request = 0.0
        self.session = requests.Session()
        self.session.headers.update({"Authorization": "Bearer %s" % self.api_token})

    def _throttle(self):
        """本地节流：两次请求间隔至少 200ms，留出限流余量。"""
        gap = 0.2 - (time.time() - self._last_request)
        if gap > 0:
            time.sleep(gap)
        self._last_request = time.time()

    def _request(self, method, path, **kwargs):
        """唯一出口：节流、超时、429 退避、错误分级收敛在这里（retry with exponential backoff）。"""
        self._throttle()
        kwargs.setdefault("timeout", self.timeout)
        url = self.base_url + path
        last = None
        for attempt in range(4):  # 1 次尝试 + 3 次重试（指数退避）
            try:
                resp = self.session.request(method, url, **kwargs)
            except (requests.Timeout, requests.ConnectionError) as e:
                last = e
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(wait)
                continue
            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                raise ApiError("请求失败（HTTP %s）" % resp.status_code,
                               code=resp.status_code) from e
            return resp.json()
        raise ApiError("重试 3 次仍失败：%s" % last)

    def list_items(self, page=1, per_page=20):
        """列表接口：分页参数显式暴露。"""
        return self._request("GET", "/items", params={"page": page, "per_page": per_page})

    def iter_all_items(self):
        """全量拉取：分页循环，有 has_more 终止条件。"""
        page = 1
        while True:
            data = self.list_items(page=page)
            items = data.get("items", [])
            if not items:
                break
            yield from items
            if not data.get("has_more"):
                break
            page += 1
