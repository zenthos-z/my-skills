#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CipherTalk API 客户端

CipherTalk 是与 WeFlow 类似的微信本地数据信号源（HTTP API），但接口细节有差异。
本客户端继承 WeFlowClient，复用其全部 XML 解析逻辑（引用/链接卡片/文件，二者
rawContent XML 格式完全一致），仅重写 HTTP 交互层以适配 CipherTalk 的差异。

与 WeFlow 的主要差异（均已在本客户端内部适配，对外接口契约与 WeFlowClient 一致）：

  基础
    - BaseURL: http://127.0.0.1:5033/v1 （WeFlow: http://127.0.0.1:5031，无 /v1）
    - 响应包裹: {success, data:{...}, meta:{...}} （WeFlow: {success, messages:[...]}）
    - 鉴权: Authorization: Bearer <token> （CipherTalk auth 非必需，但可带）

  /v1/messages
    - 会话参数: sessionId          （WeFlow: talker）
    - 起始时间: startTime（毫秒）   （WeFlow: start，秒）
    - 结束时间: endTime（毫秒）     （WeFlow: end，秒）
    - 原始 XML: 需 includeRaw=true  （WeFlow: 默认含 rawContent）
    - 类型过滤: messageKind=image   （WeFlow: image=1）

  端点差异
    - 无 /group-members 端点 → get_group_members 改由 ChatLab 端点
      （/chatlab/sessions/{id}/messages?format=chatlab）的 members 字段提供，
      accountName 即真正的群昵称（实测与消息 sender 匹配率 100%）
    - 无 /media 下载端点   → 媒体直接使用 media.imageCachePath 本地路径（已在本地，
      无需 HTTP 下载；download_media 改为本地拷贝，兼容 url 下载）
    - 新增 /v1/sns（朋友圈）；ChatLab 端点（/chatlab/*）用于获取群昵称

  消息字段映射（convert_to_standard_format 输出与 WeFlowClient 完全一致）：
    localId/serverId/localType/createTime/isSend/senderUsername → 同名
    content         ← parsedContent（CipherTalk 无独立 content 字段）
    raw_content     ← rawContent（需 includeRaw=true）
    parsed_content  ← parsedContent
    media_type      ← messageKind
    media_local_path← media.imageCachePath
    link_card       ← parse_link_card(rawContent)（继承自 WeFlowClient）
"""

import sys
import os
import glob
import shutil
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 复用 WeFlowClient：继承其 session 初始化、health_check 与全部 XML 解析静态方法
from weflow_client import WeFlowClient


class CipherTalkClient(WeFlowClient):
    """CipherTalk HTTP API 客户端

    继承 WeFlowClient，对外接口契约完全一致（health_check / get_all_messages /
    convert_to_standard_format / get_sessions / get_group_members 等），内部适配
    CipherTalk 的 URL、参数名、毫秒时间戳、响应包裹与媒体处理差异。

    下游代码（如 chat_context.py）只需把 WeFlowClient 换成 CipherTalkClient 即可，
    convert_to_standard_format 输出的标准格式与 WeFlow 完全相同，无需改动。
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5033/v1",
        timeout: int = 30,
        token: Optional[str] = None
    ):
        """初始化 CipherTalk 客户端

        Args:
            base_url: CipherTalk API 基础地址（需含 /v1 前缀）
            timeout: 请求超时时间（秒）
            token: API 鉴权 token（CipherTalk 鉴权非必需，但推荐带上）
        """
        # 确保以 /v1 结尾（与 weflow 不同，ciphertalk 的 base_url 含 /v1）
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = base_url + '/v1'
        super().__init__(base_url=base_url, timeout=timeout, token=token)

        # 群成员/联系人缓存（get_group_members 需拉取 contacts，避免重复请求）
        self._members_cache: Optional[Dict[str, Any]] = None
        self._contacts_cache: Optional[Dict[str, Any]] = None
        # HEVC 兜底转码用：最近一次 get_all_messages 的群 ID
        self._last_chatroom_id: Optional[str] = None
        self._ciphertalk_data_root: Optional[str] = None

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _unwrap(response_json: Dict[str, Any]) -> Dict[str, Any]:
        """解包 CipherTalk 的 {success, data, meta} 响应，返回 data 层

        CipherTalk 所有成功响应把业务数据放在 data 字段里。本方法统一解包，
        失败时抛出异常（与 weflow 的 raise_for_status + 直接取 messages 风格对齐）。
        """
        if not response_json.get("success", False):
            err = response_json.get("error") or response_json
            raise Exception(f"CipherTalk API error: {err}")
        return response_json.get("data") or {}

    # ------------------------------------------------------------------
    # 消息获取
    # ------------------------------------------------------------------

    def get_messages(
        self,
        chatroom_id: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        limit: int = 1000,
        offset: int = 0,
        keyword: Optional[str] = None,
        chatlab_format: bool = False,
        export_media: bool = False,
        media_types: Optional[Dict[str, bool]] = None,
        include_raw: bool = True
    ) -> Dict[str, Any]:
        """获取指定会话的消息

        Args:
            chatroom_id: 会话 ID（如 "12345678@chatroom"，对应 CipherTalk sessionId）
            start: 开始时间戳（秒）—— 内部自动 ×1000 转毫秒传给 CipherTalk
            end: 结束时间戳（秒）—— 内部自动 ×1000 转毫秒
            limit: 返回条数
            offset: 分页偏移
            keyword: 关键词过滤
            chatlab_format: 兼容参数（CipherTalk 用独立 /chatlab 端点，此处忽略）
            export_media: 是否解析媒体路径（CipherTalk 默认已解析）
            media_types: 媒体类型过滤，如 {"image": True}
            include_raw: 是否包含 rawContent（解析引用/链接卡片所需，默认 True）

        Returns:
            CipherTalk 原始响应（{success, data:{messages, total, hasMore, ...}, meta}）
        """
        params: Dict[str, Any] = {
            "sessionId": chatroom_id,
            "limit": limit,
            "offset": offset,
        }

        # 秒级 → 毫秒级（CipherTalk 时间参数为毫秒，WeFlow 为秒）
        if start is not None:
            params["startTime"] = int(start) * 1000
        if end is not None:
            params["endTime"] = int(end) * 1000

        if keyword:
            params["keyword"] = keyword

        # rawContent 默认不含，需显式开启（引用/链接卡片解析依赖）
        if include_raw:
            params["includeRaw"] = "true"

        # 媒体路径解析（CipherTalk 默认 resolveMediaPath=true，显式开启以示明确）
        if export_media:
            params["resolveMediaPath"] = "true"

        # 类型过滤：WeFlow 风格的 media_types → CipherTalk 的 messageKind
        if media_types:
            for key, value in media_types.items():
                if value:
                    params["messageKind"] = key
                    break

        response = self.session.get(
            f"{self.base_url}/messages",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_all_messages(
        self,
        chatroom_id: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """获取所有消息（自动分页）

        与 WeFlowClient.get_all_messages 行为一致：自动翻页直到无更多数据。
        start/end 为秒级时间戳（由调用方传入，与 WeFlow 契约一致）。

        Args:
            chatroom_id: 会话 ID
            start: 开始时间戳（秒）
            end: 结束时间戳（秒）
            **kwargs: 其他 get_messages 参数

        Returns:
            完整消息列表（CipherTalk 原始消息字典）
        """
        # 记录群 ID，供 convert_to_standard_format 的 HEVC 兜底转码推断本地路径
        self._last_chatroom_id = chatroom_id

        all_messages: List[Dict[str, Any]] = []
        offset = 0
        limit = 1000

        kwargs.pop('limit', None)
        kwargs.pop('offset', None)

        while True:
            result = self.get_messages(
                chatroom_id=chatroom_id,
                start=start,
                end=end,
                limit=limit,
                offset=offset,
                **kwargs
            )

            data = self._unwrap(result)
            messages = data.get("messages", [])
            all_messages.extend(messages)

            # 分页终止条件：无更多 / 本页未满
            if not data.get("hasMore", False) or len(messages) < limit:
                break

            offset += limit

        return all_messages

    # ------------------------------------------------------------------
    # 会话 / 联系人
    # ------------------------------------------------------------------

    def get_sessions(
        self,
        keyword: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取会话列表

        返回结构兼容 WeFlow（顶层含 sessions/count/hasMore），同时每个 session 保留
        CipherTalk 原始字段，并补充 WeFlow 兼容字段（type: 群聊=2），以便
        chat_context.get_group_info() 用 session.get("type") == 2 判定群聊。
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if keyword:
            params["q"] = keyword

        response = self.session.get(
            f"{self.base_url}/sessions",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = self._unwrap(response.json())

        sessions: List[Dict[str, Any]] = []
        for s in data.get("sessions", []):
            compat = dict(s)
            # 补 WeFlow 兼容字段：type（2=群聊），name，username
            compat["type"] = 2 if s.get("sessionType") == "group" else 1
            compat["name"] = s.get("displayName")
            compat["username"] = s.get("username")
            sessions.append(compat)

        return {
            "success": True,
            "sessions": sessions,
            "count": data.get("total", len(sessions)),
            "hasMore": data.get("hasMore", False),
        }

    def get_contacts(
        self,
        keyword: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        contact_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取联系人列表

        Args:
            keyword: 关键词过滤（按名称/wxid 搜索）
            limit: 返回条数
            offset: 分页偏移
            contact_type: 类型过滤（"friend"/"official"/...）

        Returns:
            兼容 WeFlow 的结构：{success, contacts:[...], count, hasMore}
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if keyword:
            params["q"] = keyword
        if contact_type:
            params["type"] = contact_type

        response = self.session.get(
            f"{self.base_url}/contacts",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = self._unwrap(response.json())

        return {
            "success": True,
            "contacts": data.get("contacts", []),
            "count": data.get("total", 0),
            "hasMore": data.get("hasMore", False),
        }

    def _chatlab_base(self) -> str:
        """ChatLab 端点基础地址（/chatlab，与 /v1 同级）

        CipherTalk 的 base_url 为 .../v1，而 ChatLab 端点挂在 /chatlab 下
        （status.chatlabBaseUrl = http://host:port/chatlab）。
        """
        if self.base_url.endswith("/v1"):
            return self.base_url[:-3] + "/chatlab"
        return self.base_url.rstrip("/") + "/chatlab"

    def _fetch_chatlab_data(
        self,
        chatroom_id: str,
        limit: int = 1
    ) -> Dict[str, Any]:
        """拉取 ChatLab 格式数据（含完整群成员列表与群昵称）

        ChatLab 端点 GET /chatlab/sessions/{id}/messages?format=chatlab 的响应里：
          - members: 完整群成员 [{platformId(wxid), accountName(群昵称), avatar}]
          - messages: ChatLab 格式消息（每条带 sender + accountName）
          - meta: 群信息（name/groupId/type）

        这是 CipherTalk 获取「真正群昵称」的唯一途径——标准 /v1/messages 的
        sender 只有 {username, isSelf}，7 个 sender 增强参数均无效；而 ChatLab
        members 的 accountName 与消息 sender 匹配率 100%。
        """
        url = f"{self._chatlab_base()}/sessions/{chatroom_id}/messages"
        response = self.session.get(
            url,
            params={"format": "chatlab", "limit": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        # ChatLab 响应结构不同于 /v1：无 {success, data} 包裹，
        # 直接是 {chatlab, meta, members, messages, sync}
        return response.json()

    def get_group_members(
        self,
        chatroom_id: str,
        include_counts: bool = True,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """获取群成员列表（含真正的群昵称）

        通过 ChatLab 端点的 members 字段获取群成员（platformId + accountName），
        组装成 WeFlow 兼容结构。accountName 即群内昵称。

        结果带实例缓存（首次 1 次 HTTP 请求即拿到全部成员，后续直接命中）。

        Args:
            chatroom_id: 群聊 ID
            include_counts: 兼容参数（CipherTalk 不提供发言统计）
            force_refresh: 是否强制刷新缓存

        Returns:
            兼容 WeFlow 的结构：{members: [{wxid, groupNickname, nickname,
            displayName, remark, alias}], count}
        """
        if self._members_cache is not None and not force_refresh:
            return self._members_cache

        data = self._fetch_chatlab_data(chatroom_id, limit=1)
        members: List[Dict[str, Any]] = []
        for m in data.get("members", []):
            wxid = m.get("platformId")
            if not wxid:
                continue
            name = m.get("accountName") or ""
            members.append({
                "wxid": wxid,
                "groupNickname": name or None,   # 真正的群昵称
                "nickname": name or None,
                "displayName": name or None,
                "remark": None,
                "alias": None,
            })

        self._members_cache = {"members": members, "count": len(members)}
        return self._members_cache

    # ------------------------------------------------------------------
    # 媒体
    # ------------------------------------------------------------------

    def download_media(
        self,
        media_source: str,
        local_path: str,
        overwrite: bool = False
    ) -> bool:
        """获取媒体文件到本地

        CipherTalk 的媒体文件通常已在本地（media.imageCachePath），无需 HTTP 下载：
        - 若 media_source 是已存在的本地路径 → 直接拷贝
        - 若 media_source 是 http(s) URL（如表情 cdn）→ HTTP 下载

        Args:
            media_source: 本地路径或 URL
            local_path: 本地保存路径
            overwrite: 是否覆盖已存在文件

        Returns:
            True if success
        """
        local_path = Path(local_path)

        if local_path.exists() and not overwrite:
            return True

        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 本地路径：直接拷贝（CipherTalk 媒体已下载到 imageCachePath）
        if media_source and not media_source.startswith(('http://', 'https://')):
            src = Path(media_source)
            if src.exists():
                try:
                    shutil.copy2(src, local_path)
                    return True
                except Exception as e:
                    print(f"Failed to copy media: {e}")
                    return False
            return False

        # URL：HTTP 下载（兼容表情 cdn 等）
        if media_source and media_source.startswith(('http://', 'https://')):
            # 去掉 file:/// 前缀干扰
            try:
                response = self.session.get(
                    media_source, timeout=self.timeout, stream=True
                )
                response.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            except Exception as e:
                print(f"Failed to download media: {e}")
                return False

        return False

    # ------------------------------------------------------------------
    # 标准化（核心：CipherTalk 字段 → WeFlow 标准格式）
    # ------------------------------------------------------------------

    def convert_to_standard_format(
        self,
        messages: List[Dict[str, Any]],
        export_media: bool = False,
        media_export_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """将 CipherTalk API 消息转换为标准格式

        输出字段与 WeFlowClient.convert_to_standard_format 完全一致，下游
        chat_context.py 无需改动。字段映射见模块 docstring。

        Args:
            messages: CipherTalk API 返回的消息列表
            export_media: 是否把媒体拷贝到 media_export_path
            media_export_path: 媒体导出目录

        Returns:
            标准化后的消息列表
        """
        standardized: List[Dict[str, Any]] = []

        for msg in messages:
            raw_content = msg.get("rawContent", "") or ""
            parsed_content = msg.get("parsedContent", "") or ""
            media = msg.get("media") or {}

            # CipherTalk 媒体本地路径（图片缩略图通常已存在）
            cache_path = (
                media.get("imageCachePath")
                or media.get("localPath")
                or media.get("filePath")
            )
            # HEVC 兜底：ciphertalk 对 HEVC/HEIF 编码图不产出 imageCachePath（缺 HEVC
            # 解码器），但本地存了 {dat}_hd.hevc 裸流 → 用 ffmpeg 解码取内容最丰富的
            # 帧转 JPG。没装 ffmpeg / 路径不存在 / 转码失败则跳过（不影响主流程）。
            if not cache_path and media.get("imageDatName"):
                cache_path = self._hevc_to_jpg(
                    media["imageDatName"], msg.get("createTime"), media_export_path)

            std_msg: Dict[str, Any] = {
                "id": msg.get("localId"),
                "server_id": msg.get("serverId"),
                "type": msg.get("localType"),
                "timestamp": msg.get("createTime"),
                "is_send": msg.get("isSend", 0) == 1,
                "sender": msg.get("senderUsername"),
                # CipherTalk 无 content 字段，用 parsedContent 填充
                "content": parsed_content,
                "raw_content": raw_content,
                "parsed_content": parsed_content,
                "media_type": msg.get("messageKind"),
                "media_file": media.get("imageDatName") or media.get("fileName"),
                "media_url": media.get("emojiCdnUrl") or media.get("url"),
                "media_local_path": None,
            }

            # 媒体本地路径 → file:/// 格式（与 WeFlow 一致）
            if cache_path:
                path_obj = Path(cache_path)
                if path_obj.exists():
                    std_msg["media_local_path"] = f"file:///{path_obj.resolve().as_posix()}"
                else:
                    std_msg["media_local_path"] = cache_path

            # 导出媒体（拷贝到 media_export_path，保持与 WeFlow 行为一致）
            if export_media and cache_path and media_export_path:
                path_obj = Path(cache_path)
                if path_obj.exists():
                    media_filename = std_msg["media_file"] or path_obj.name
                    export_target = Path(media_export_path) / media_filename
                    if self.download_media(cache_path, str(export_target)):
                        std_msg["media_local_path"] = str(export_target.resolve())

            # 链接卡片/引用/文件解析（rawContent XML 与 WeFlow 完全一致，复用继承方法）
            if '<appmsg' in raw_content:
                link_info = self.parse_link_card(raw_content)
                std_msg["link_card"] = link_info

                # 非引用类型：用格式化文本覆盖 content
                if link_info.get("type") != "quote":
                    formatted = self.format_link_card(link_info)
                    if formatted:
                        std_msg["content"] = formatted

            standardized.append(std_msg)

        return standardized

    def _hevc_to_jpg(
        self,
        image_dat_name: str,
        create_time: Any,
        media_export_path: Optional[str] = None
    ) -> Optional[str]:
        """HEVC 兜底：把 ciphertalk 未转码的 HEVC 图转成 JPG

        ciphertalk 对 HEVC/HEIF 编码的图不产出 imageCachePath（缺 HEVC 解码器），
        但本地存了 {imageDatName}_hd.hevc 裸流。本方法用 ffmpeg 解码，取内容最
        丰富的帧（HEVC 静态图首帧常为空白占位）转成 JPG，让 describe_images 能识别。

        路径推断：{CipherTalkData}/Images/{chatroom}/YYYY-MM/{dat}_hd.hevc

        没装 ffmpeg / 路径不存在 / 转码失败 → 返回 None（静默跳过，不影响主流程）。
        """
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg or not (image_dat_name and create_time and self._last_chatroom_id):
            return None

        # CipherTalkData 根：默认 ~/Documents/CipherTalkData（可按需改成配置项）
        data_root = self._ciphertalk_data_root or str(
            Path.home() / "Documents" / "CipherTalkData")
        try:
            month = datetime.fromtimestamp(int(create_time)).strftime("%Y-%m")
        except (TypeError, ValueError, OSError):
            return None

        hevc_path = (Path(data_root) / "Images" / self._last_chatroom_id
                     / month / f"{image_dat_name}_hd.hevc")
        if not hevc_path.exists():
            return None

        out_dir = (Path(media_export_path) if media_export_path
                   else Path(tempfile.gettempdir()))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_jpg = out_dir / f"{image_dat_name}_hd.jpg"

        # 解全部帧，取文件最大（内容最丰富）的一帧
        try:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(
                    [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                     "-f", "hevc", "-i", str(hevc_path),
                     "-vsync", "0", str(Path(td) / "f_%03d.jpg")],
                    capture_output=True, timeout=30,
                )
                frames = sorted(glob.glob(str(Path(td) / "f_*.jpg")))
                if not frames:
                    return None
                shutil.copy2(max(frames, key=os.path.getsize), out_jpg)
        except Exception:
            return None

        return str(out_jpg)


if __name__ == "__main__":
    # 简单连通性测试
    client = CipherTalkClient()

    if client.health_check():
        print("✅ CipherTalk API 连接正常")

        sessions = client.get_sessions()
        print(f"\n会话列表 ({sessions.get('count', 0)} 个):")
        for s in sessions.get("sessions", [])[:5]:
            print(f"  - {s.get('displayName')} ({s.get('username')}) "
                  f"type={'群聊' if s.get('type') == 2 else '私聊'}")
    else:
        print("❌ CipherTalk API 连接失败")
        print("   请确认 CipherTalk 已启动并启用了 HTTP API 服务（默认端口 5033）")
