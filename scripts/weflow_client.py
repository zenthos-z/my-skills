#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeFlow API 客户端
封装 WeFlow HTTP API，提供消息获取、成员统计、链接卡片解析等功能
"""

import json
import re
import sys
import html
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("Error: requests module not installed. Run: pip install requests")
    sys.exit(1)


class WeFlowClient:
    """WeFlow HTTP API 客户端

    提供对 WeFlow 本地 API 的完整封装，包括：
    - 消息获取（支持时间范围、分页）
    - 群成员列表及发言统计
    - 媒体文件导出
    - 链接卡片解析
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5031", timeout: int = 30):
        """初始化客户端

        Args:
            base_url: WeFlow API 基础地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'qunribao/1.0'
        })

    def health_check(self) -> bool:
        """检查 API 服务是否可用

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

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
        media_types: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """获取指定会话的消息

        Args:
            chatroom_id: 群聊 ID (如 "12345678@chatroom")
            start: 开始时间戳（秒）或 YYYYMMDD 格式字符串
            end: 结束时间戳（秒）或 YYYYMMDD 格式字符串
            limit: 返回条数（1-10000）
            offset: 分页偏移
            keyword: 关键词过滤
            chatlab_format: 是否返回 ChatLab 格式
            export_media: 是否导出媒体文件
            media_types: 媒体类型过滤，如 {"image": True, "voice": False}

        Returns:
            API 响应数据，包含 messages 列表
        """
        params = {
            "talker": chatroom_id,
            "limit": limit,
            "offset": offset
        }

        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        if keyword:
            params["keyword"] = keyword
        if chatlab_format:
            params["chatlab"] = "1"
        if export_media:
            params["media"] = "1"

        # 媒体类型过滤
        if media_types:
            type_mapping = {
                "image": "image",
                "voice": "voice",
                "video": "video",
                "emoji": "emoji"
            }
            for key, value in media_types.items():
                if key in type_mapping and value:
                    params[type_mapping[key]] = "1"
                elif key in type_mapping and not value:
                    params[type_mapping[key]] = "0"

        response = self.session.get(
            f"{self.base_url}/api/v1/messages",
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

        Args:
            chatroom_id: 群聊 ID
            start: 开始时间戳
            end: 结束时间戳
            **kwargs: 其他 get_messages 参数

        Returns:
            完整消息列表
        """
        all_messages = []
        offset = 0
        limit = 1000  # 每页最大数量

        # 从 kwargs 中移除 limit/offset 避免重复传递
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

            if not result.get("success"):
                raise Exception(f"API error: {result}")

            messages = result.get("messages", [])
            all_messages.extend(messages)

            # 检查是否还有更多
            if not result.get("hasMore", False) or len(messages) < limit:
                break

            offset += limit

        return all_messages

    def get_group_members(
        self,
        chatroom_id: str,
        include_counts: bool = True,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """获取群成员列表

        Args:
            chatroom_id: 群聊 ID
            include_counts: 是否包含发言统计
            force_refresh: 是否强制刷新缓存

        Returns:
            包含 members 列表的响应数据
        """
        params = {
            "chatroomId": chatroom_id
        }

        if include_counts:
            params["includeMessageCounts"] = "1"
        if force_refresh:
            params["forceRefresh"] = "1"

        response = self.session.get(
            f"{self.base_url}/api/v1/group-members",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_sessions(
        self,
        keyword: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取会话列表

        Args:
            keyword: 关键词过滤
            limit: 返回条数

        Returns:
            包含 sessions 列表的响应数据
        """
        params = {"limit": limit}
        if keyword:
            params["keyword"] = keyword

        response = self.session.get(
            f"{self.base_url}/api/v1/sessions",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_contacts(
        self,
        keyword: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取联系人列表

        Args:
            keyword: 关键词过滤
            limit: 返回条数

        Returns:
            包含 contacts 列表的响应数据
        """
        params = {"limit": limit}
        if keyword:
            params["keyword"] = keyword

        response = self.session.get(
            f"{self.base_url}/api/v1/contacts",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def download_media(
        self,
        media_url: str,
        local_path: str,
        overwrite: bool = False
    ) -> bool:
        """下载媒体文件

        Args:
            media_url: 媒体文件 URL（如 /api/v1/media/xxx/images/abc.jpg）
            local_path: 本地保存路径
            overwrite: 是否覆盖已存在文件

        Returns:
            True if success
        """
        local_path = Path(local_path)

        if local_path.exists() and not overwrite:
            return True

        # 确保目录存在
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # 构建完整 URL
        if media_url.startswith('/'):
            full_url = f"{self.base_url}{media_url}"
        elif media_url.startswith('http'):
            full_url = media_url
        else:
            full_url = f"{self.base_url}/api/v1/media/{media_url}"

        try:
            response = self.session.get(full_url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except Exception as e:
            print(f"Failed to download media: {e}")
            return False

    @staticmethod
    def parse_quote(raw_content: str) -> Optional[Dict[str, Any]]:
        """解析引用消息 XML

        从 rawContent 中提取引用回复的详细信息，包括：
        - display_name: 被引用消息发送者显示名
        - content: 被引用消息内容（已解码 HTML 实体）
        - type: 被引用消息类型
        - refer_wxid: 被引用消息发送者的 wxid
        - server_msg_id: 被引用消息的服务器 ID

        Args:
            raw_content: 消息的 rawContent 字段（XML 格式）

        Returns:
            解析后的引用信息字典，如果不是引用消息则返回 None
        """
        if not raw_content or '<refermsg>' not in raw_content:
            return None

        result = {
            "display_name": None,
            "content": None,
            "type": None,
            "refer_wxid": None,
            "server_msg_id": None,
            "create_time": None
        }

        try:
            # 提取被引用消息的发送者显示名
            display_name_match = re.search(r'<displayname>([^<]*)</displayname>', raw_content)
            if display_name_match:
                result["display_name"] = html.unescape(display_name_match.group(1).strip()) or None

            # 提取被引用消息的内容（需要解码 HTML 实体）
            content_match = re.search(r'<content>(.*?)</content>', raw_content, re.DOTALL)
            if content_match:
                content = content_match.group(1).strip()
                # 解码 HTML 实体（如 &lt; → <, &gt; → >, &amp; → &）
                content = html.unescape(content)
                # 如果内容是 XML 格式（如图片、文件等），提取有意义的文本
                if content.startswith('<?xml') or content.startswith('<msg'):
                    # 尝试提取 title 或纯文本内容
                    title_match = re.search(r'<title>([^<]*)</title>', content)
                    if title_match:
                        content = html.unescape(title_match.group(1).strip())
                    else:
                        # 对于媒体类型，返回类型描述
                        if '<img' in content or 'imgdatahash' in content:
                            content = "[图片]"
                        elif '<fileupload' in content or '<appattach' in content:
                            content = "[文件]"
                        elif '<url>' in content:
                            content = "[链接]"
                        else:
                            # 无法识别时返回空
                            content = "[媒体内容]"
                result["content"] = content or None

            # 提取被引用消息的类型
            type_match = re.search(r'<type>(\d+)</type>', raw_content)
            if type_match:
                result["type"] = int(type_match.group(1))

            # 提取被引用消息发送者的 wxid
            refer_wxid_match = re.search(r'<chatusr>([^<]*)</chatusr>', raw_content)
            if refer_wxid_match:
                result["refer_wxid"] = refer_wxid_match.group(1).strip() or None

            # 提取被引用消息的服务器 ID
            svrid_match = re.search(r'<svrid>([^<]*)</svrid>', raw_content)
            if svrid_match:
                result["server_msg_id"] = svrid_match.group(1).strip() or None

            # 提取被引用消息的创建时间
            create_time_match = re.search(r'<createtime>(\d+)</createtime>', raw_content)
            if create_time_match:
                result["create_time"] = int(create_time_match.group(1))

        except Exception as e:
            print(f"Error parsing quote: {e}")

        return result

    @staticmethod
    def parse_file(raw_content: str) -> Optional[Dict[str, Any]]:
        """解析文件分享 XML

        从 rawContent 中提取文件分享的详细信息，包括：
        - title: 文件名
        - file_size: 文件大小（字节）
        - file_ext: 文件扩展名
        - file_id: 文件 ID

        Args:
            raw_content: 消息的 rawContent 字段（XML 格式）

        Returns:
            解析后的文件信息字典，如果不是文件分享则返回 None
        """
        if not raw_content:
            return None

        # 检查是否是文件类型
        if '<fileupload>' not in raw_content and '<appattach>' not in raw_content:
            return None

        result = {
            "title": None,
            "file_size": None,
            "file_ext": None,
            "file_id": None
        }

        try:
            # 提取文件名
            title_match = re.search(r'<title>([^<]*)</title>', raw_content)
            if title_match:
                result["title"] = title_match.group(1).strip() or None

            # 提取文件大小（在 <totallen> 或 <filesize> 中）
            size_match = re.search(r'<(?:totallen|filesize)>(\d+)</(?:totallen|filesize)>', raw_content)
            if size_match:
                result["file_size"] = int(size_match.group(1))

            # 提取文件扩展名
            ext_match = re.search(r'<fileext>([^<]*)</fileext>', raw_content)
            if ext_match:
                result["file_ext"] = ext_match.group(1).strip() or None

            # 提取文件 ID
            file_id_match = re.search(r'<attachid>([^<]*)</attachid>', raw_content)
            if file_id_match:
                result["file_id"] = file_id_match.group(1).strip() or None

        except Exception as e:
            print(f"Error parsing file: {e}")

        return result

    @staticmethod
    def parse_link(raw_content: str) -> Optional[Dict[str, Any]]:
        """解析链接卡片 XML（不含文件和引用）

        从 rawContent 中提取链接卡片的详细信息，包括：
        - title: 卡片标题
        - url: 分享链接（自动解码 &amp; → &）
        - source: 来源名称（如公众号名称）
        - description: 描述文本
        - type: 链接类型（wechat_article/link/miniapp）

        Args:
            raw_content: 消息的 rawContent 字段（XML 格式）

        Returns:
            解析后的链接信息字典，如果不是链接卡片则返回 None
        """
        if not raw_content or '<appmsg' not in raw_content:
            return None

        # 排除文件和引用类型
        # 注意：链接卡片的缩略图也使用 <appattach>，所以不能仅通过 <appattach> 判断
        # 真正的文件有 <attachid> 或 <filename>，而缩略图只有 <cdnthumburl>
        if '<fileupload>' in raw_content or '<refermsg>' in raw_content:
            return None

        # 如果有 <appattach>，检查是否为真正的文件（有 filename/attachid）
        if '<appattach>' in raw_content:
            has_real_file = bool(re.search(r'<attachid>[^<]+</attachid>', raw_content) or
                                 re.search(r'<filename>[^<]+</filename>', raw_content))
            if has_real_file:
                return None  # 是真正的文件，不是链接

        result = {
            "type": "unknown",
            "title": None,
            "url": None,
            "source": None,
            "description": None
        }

        try:
            # 提取 title（兼容 CDATA：<title><![CDATA[...]]></title>）
            title_match = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', raw_content)
            if title_match:
                result["title"] = title_match.group(1).strip() or None

            # 提取 url（解码 HTML entities，兼容 CDATA）
            url_match = re.search(r'<url>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</url>', raw_content)
            if url_match:
                url = url_match.group(1).strip()
                if url:
                    result["url"] = url.replace('&amp;', '&')

            # 提取来源（公众号/应用名称，兼容 CDATA）
            source_match = re.search(r'<sourcedisplayname>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</sourcedisplayname>', raw_content)
            if source_match:
                result["source"] = source_match.group(1).strip() or None

            # 提取描述（兼容 CDATA）
            desc_match = re.search(r'<des>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</des>', raw_content, re.DOTALL)
            if desc_match:
                result["description"] = desc_match.group(1).strip() or None

            # 判断链接类型
            if result["url"] and 'mp.weixin.qq.com' in result["url"]:
                result["type"] = "wechat_article"  # 微信公众号文章
            elif result["url"]:
                result["type"] = "link"  # 普通链接
            elif result["title"] and not result["url"]:
                result["type"] = "miniapp"  # 小程序卡片（无 URL）

        except Exception as e:
            print(f"Error parsing link: {e}")

        return result

    @staticmethod
    def parse_link_card(raw_content: str) -> Dict[str, Any]:
        """解析链接卡片 XML

        从 rawContent 中提取链接卡片的详细信息，包括：
        - title: 卡片标题
        - url: 分享链接（自动解码 &amp; → &）
        - source: 来源名称（如公众号名称）
        - description: 描述文本
        - type: 卡片类型（quote/wechat_article/link/file/miniapp/unknown）

        Args:
            raw_content: 消息的 rawContent 字段（XML 格式）

        Returns:
            解析后的链接卡片信息字典
        """
        result = {
            "type": "unknown",
            "title": None,
            "url": None,
            "source": None,
            "description": None,
            "raw_type": None  # XML 中的 type 字段
        }

        if not raw_content or '<appmsg' not in raw_content:
            return result

        try:
            # 提取 title（兼容 CDATA：<title><![CDATA[...]]></title>）
            title_match = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', raw_content)
            if title_match:
                result["title"] = title_match.group(1).strip() or None

            # 提取 url（解码 HTML entities，兼容 CDATA）
            url_match = re.search(r'<url>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</url>', raw_content)
            if url_match:
                url = url_match.group(1).strip()
                if url:
                    result["url"] = url.replace('&amp;', '&')

            # 提取来源（公众号/应用名称，兼容 CDATA）
            source_match = re.search(r'<sourcedisplayname>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</sourcedisplayname>', raw_content)
            if source_match:
                result["source"] = source_match.group(1).strip() or None

            # 提取描述（兼容 CDATA）
            desc_match = re.search(r'<des>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</des>', raw_content, re.DOTALL)
            if desc_match:
                result["description"] = desc_match.group(1).strip() or None

            # 提取 XML 中的 type 字段
            type_match = re.search(r'<type>(\d+)</type>', raw_content)
            if type_match:
                result["raw_type"] = int(type_match.group(1))

            # 判断卡片类型（引用优先于文件，避免引用+附件消息被误判为文件）
            if '<refermsg>' in raw_content:
                result["type"] = "quote"  # 引用回复（优先检测）
            elif '<fileupload>' in raw_content or '<appattach>' in raw_content:
                result["type"] = "file"  # 文件分享
            elif result["url"] and 'mp.weixin.qq.com' in result["url"]:
                result["type"] = "wechat_article"  # 微信公众号文章
            elif result["url"]:
                result["type"] = "link"  # 普通链接
            elif result["title"] and not result["url"]:
                result["type"] = "miniapp"  # 小程序卡片（无 URL）

        except Exception as e:
            print(f"Error parsing link card: {e}")

        return result

    @staticmethod
    def format_link_card(parsed: Dict[str, Any]) -> str:
        """格式化链接卡片为可读文本

        Args:
            parsed: parse_link_card 返回的解析结果

        Returns:
            格式化后的文本
        """
        lines = []
        card_type = parsed.get("type", "unknown")

        # 文件类型特殊处理
        if card_type == "file":
            title = parsed.get("title", "")
            lines.append(f"📎 [文件] {title}" if title else "📎 [文件]")
            return "\n".join(lines)

        # 类型图标映射
        type_icons = {
            "quote": "💬",
            "wechat_article": "📰",
            "link": "🔗",
            "file": "📎",
            "miniapp": "📱",
            "unknown": "📎"
        }
        icon = type_icons.get(card_type, "📎")

        # 标题行
        title = parsed.get("title")
        if title:
            lines.append(f"{icon} [链接卡片] {title}")
        else:
            lines.append(f"{icon} [链接卡片]")

        # URL
        url = parsed.get("url")
        if url:
            lines.append(f"🔗 URL: {url}")

        # 来源
        source = parsed.get("source")
        if source:
            lines.append(f"📰 来源: {source}")

        # 描述（可选，如果与标题不同）
        description = parsed.get("description")
        if description and description != title:
            lines.append(f"📝 {description}")

        return "\n".join(lines)

    def convert_to_standard_format(
        self,
        messages: List[Dict[str, Any]],
        export_media: bool = False,
        media_export_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """将 WeFlow API 消息格式转换为标准格式

        统一字段命名，与现有处理流程兼容

        Args:
            messages: WeFlow API 返回的消息列表
            export_media: 是否导出媒体文件
            media_export_path: 媒体文件导出目录

        Returns:
            标准化后的消息列表
        """
        standardized = []

        for msg in messages:
            std_msg = {
                "id": msg.get("localId"),
                "server_id": msg.get("serverId"),
                "type": msg.get("localType"),
                "timestamp": msg.get("createTime"),
                "is_send": msg.get("isSend", 0) == 1,
                "sender": msg.get("senderUsername"),
                "content": msg.get("content", ""),
                "raw_content": msg.get("rawContent", ""),
                "parsed_content": msg.get("parsedContent", ""),
                "media_type": msg.get("mediaType"),
                "media_file": msg.get("mediaFileName"),
                "media_url": msg.get("mediaUrl"),
                "media_local_path": msg.get("mediaLocalPath"),
            }

            # 处理链接卡片
            raw_content = msg.get("rawContent", "")
            if '<appmsg' in raw_content:
                link_info = self.parse_link_card(raw_content)
                std_msg["link_card"] = link_info

                # 更新 content 为格式化后的链接卡片信息
                if link_info.get("type") != "quote":  # 引用回复保持原样
                    formatted = self.format_link_card(link_info)
                    if formatted:
                        std_msg["content"] = formatted

            # 处理媒体文件路径（转换为 file:/// 格式）
            media_local_path = msg.get("mediaLocalPath")
            if media_local_path:
                # 将 Windows 路径转换为 file:/// URL 格式
                path_obj = Path(media_local_path)
                if path_obj.exists():
                    std_msg["media_local_path"] = f"file:///{path_obj.resolve().as_posix()}"
                else:
                    std_msg["media_local_path"] = media_local_path

            # 处理媒体文件导出（下载到指定目录）
            if export_media and std_msg["media_url"] and media_export_path:
                media_filename = std_msg["media_file"] or Path(std_msg["media_url"]).name
                local_path = Path(media_export_path) / media_filename

                if self.download_media(std_msg["media_url"], str(local_path)):
                    std_msg["media_local_path"] = str(local_path.resolve())

            standardized.append(std_msg)

        return standardized


class WeFlowError(Exception):
    """WeFlow API 错误"""
    pass


# 消息类型映射（WeFlow localType → 可读类型）
MESSAGE_TYPE_NAMES = {
    1: "text",
    3: "image",
    34: "voice",
    43: "video",
    47: "emoji",
    49: "appmsg",  # 链接卡片、小程序等
    10000: "system",
    21474836529: "appmsg",  # 链接卡片（另一种类型值）
    244813135921: "appmsg",  # 链接卡片（引用回复）
}


def timestamp_to_datetime(ts: int) -> datetime:
    """将时间戳转换为 datetime"""
    return datetime.fromtimestamp(ts)


def datetime_to_timestamp(dt: datetime) -> int:
    """将 datetime 转换为时间戳"""
    return int(dt.timestamp())


if __name__ == "__main__":
    # 简单测试
    client = WeFlowClient()

    if client.health_check():
        print("✅ WeFlow API 连接正常")

        # 测试获取会话列表
        sessions = client.get_sessions()
        print(f"\n会话列表 ({sessions.get('count', 0)} 个):")
        for s in sessions.get("sessions", [])[:5]:
            print(f"  - {s.get('displayName')} ({s.get('username')})")
    else:
        print("❌ WeFlow API 连接失败")
        print("   请确认 WeFlow 已启动并启用了 HTTP API 服务")
