#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天上下文文档生成器
统一生成 temp 文档，支持链接卡片增强解析
"""

import sys
import re
import html
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 直接导入底层客户端
from weflow_client import WeFlowClient
from config_loader import get_config as _load_config

# Date format constants (single source of truth)
DATE_FMT_COMPACT = '%Y%m%d'            # filenames: chat_context_20260325.md
DATE_FMT_CLI = '%Y-%m-%d'              # CLI args: --date 2026-03-25
TIME_FMT_RANGE = '%Y-%m-%d %H:%M'      # time ranges in logs/CLI
TIME_FMT_FULL = '%Y-%m-%d %H:%M:%S'    # markdown output timestamps


class ChatContextGenerator:
    """聊天上下文文档生成器

    职责：
    1. 封装数据源逻辑（原 WeFlowDataSource 功能内联）
    2. 生成 Markdown 文档
    """

    # 消息类型名称映射
    MSG_TYPE_NAMES = {
        1: "文本",
        3: "图片",
        34: "语音",
        43: "视频",
        47: "表情",
        49: "链接卡片",
        10000: "系统消息",
        21474836529: "链接卡片",
        244813135921: "引用回复",
    }

    def __init__(
        self,
        client: WeFlowClient,
        chatroom_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """初始化生成器

        Args:
            client: WeFlowClient 实例
            chatroom_id: 群聊 ID
            config: 配置字典
        """
        self.client = client
        self.chatroom_id = chatroom_id
        self.config = config or {}
        self.parse_link_cards = self.config.get("features", {}).get("parseLinkCards", True)
        self._group_info: Optional[Dict] = None
        self._member_map: Optional[Dict[str, Dict[str, Any]]] = None

    def health_check(self) -> bool:
        """检查 API 连接状态"""
        return self.client.health_check()

    def get_messages(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        export_media: bool = False,
    ) -> List[Dict[str, Any]]:
        """获取消息（原 WeFlowDataSource.get_messages 内联）

        自动处理分页，返回完整消息列表

        Args:
            start: 开始时间
            end: 结束时间
            export_media: 是否导出媒体文件

        Returns:
            标准化后的消息列表
        """
        # 转换 datetime 为时间戳
        start_ts = int(start.timestamp()) if start else None
        end_ts = int(end.timestamp()) if end else None

        # 获取所有消息（自动分页）
        messages = self.client.get_all_messages(
            chatroom_id=self.chatroom_id,
            start=start_ts,
            end=end_ts,
            export_media=export_media,
        )

        # 转换为标准格式（确保图片能下载到本地）
        media_export_path = None
        if export_media:
            media_dir = Path(self.config.get("tempDir", "temp")) / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            media_export_path = str(media_dir)

        return self.client.convert_to_standard_format(
            messages,
            export_media=export_media,
            media_export_path=media_export_path
        )

    def get_group_info(self) -> Dict[str, Any]:
        """获取群聊信息（原 WeFlowDataSource.get_group_info 内联）

        从会话列表中查找匹配的群聊信息

        Returns:
            包含群名称、ID 等信息的字典
        """
        if self._group_info is None:
            result = self.client.get_sessions()

            for session in result.get("sessions", []):
                if session.get("username") == self.chatroom_id:
                    self._group_info = {
                        "id": session.get("username"),
                        "name": session.get("displayName", "Unknown"),
                        "type": "group" if session.get("type") == 2 else "private",
                        "last_timestamp": session.get("lastTimestamp"),
                        "unread_count": session.get("unreadCount", 0)
                    }
                    break

            if self._group_info is None:
                self._group_info = {
                    "id": self.chatroom_id,
                    "name": "Unknown Group",
                    "type": "group"
                }

        return self._group_info

    def _load_member_map(self) -> Dict[str, Dict[str, Any]]:
        """加载群成员映射表

        从 WeFlow API 获取群成员列表，建立 wxid -> 成员信息的映射

        Returns:
            wxid 到成员信息的字典
        """
        if self._member_map is None:
            result = self.client.get_group_members(self.chatroom_id)
            self._member_map = {}

            for member in result.get("members", []):
                wxid = member.get("wxid")
                if wxid:
                    self._member_map[wxid] = member

        return self._member_map

    def _get_sender_display_name(self, wxid: str) -> str:
        """获取发送者的显示名称

        优先级：群昵称 > 昵称 > 备注 > 微信号 > wxid

        Args:
            wxid: 发送者的 wxid

        Returns:
            显示名称
        """
        if not wxid:
            return "Unknown"

        # 加载成员映射
        member_map = self._load_member_map()
        member = member_map.get(wxid, {})

        # 按优先级获取显示名
        display_name = (
            member.get("groupNickname")  # 1. 群昵称
            or member.get("nickname")     # 2. 昵称
            or member.get("remark")       # 3. 备注
            or member.get("alias")        # 4. 微信号
            or wxid                       # 5. 回退到 wxid
        )

        return display_name

    def generate(
        self,
        start: datetime,
        end: datetime,
        output_path: str,
        inline_images: bool = False,
        include_stats: bool = False,
        sender_filter: Optional[str] = None
    ) -> str:
        """生成聊天上下文文档

        Args:
            start: 开始时间
            end: 结束时间
            output_path: 输出文件路径
            inline_images: 是否将图片嵌入为 file:// 路径（默认 False，使用 describe 模式）
            include_stats: 是否包含统计信息
            sender_filter: 发送者过滤（模糊匹配）

        Returns:
            生成的文档内容
        """
        print(f"📄 生成聊天上下文文档...")
        print(f"   时间范围: {start.strftime(TIME_FMT_RANGE)} ~ {end.strftime(TIME_FMT_RANGE)}")

        # 获取数据（直接调用内联方法）
        group_info = self.get_group_info()
        messages = self.get_messages(
            start=start,
            end=end,
            export_media=True  # direct 和 describe 模式都需要下载图片
        )

        # 发送者过滤
        if sender_filter:
            messages = [
                m for m in messages
                if sender_filter.lower() in (m.get("sender_name") or "").lower()
                or sender_filter.lower() in (m.get("sender") or "").lower()
            ]
            print(f"   过滤后: {len(messages)} 条消息（发送者: {sender_filter}）")
        else:
            print(f"   获取到 {len(messages)} 条消息")

        # 按时间戳升序排序（从早到晚），相同时间按 ID 升序（小号在前）
        messages.sort(key=lambda m: (
            m.get("timestamp", 0),
            int(m.get("localId") or m.get("id") or 0)
        ))

        # 建立 server_id -> 消息缓存（用于引用消息查找与内容反查）
        self._messages_by_server_id: Dict[str, Dict[str, Any]] = {}
        for m in messages:
            server_id = m.get("serverId") or m.get("server_id")
            if server_id:
                self._messages_by_server_id[str(server_id)] = m

        # 风格：跨日期引用检测与获取
        cross_date_refs = self._fetch_cross_date_refs(messages, start, end)

        # 构建文档
        lines = []

        # 跨日期引用区块（排在消息列表之前）
        if cross_date_refs:
            # 收集引用来源日期
            ref_dates = set()
            for ref_msg in cross_date_refs.values():
                ts = ref_msg.get("timestamp", 0)
                if isinstance(ts, (int, float)) and ts > 0:
                    ref_dates.add(datetime.fromtimestamp(ts).strftime(DATE_FMT_CLI))
            dates_str = ", ".join(sorted(ref_dates))
            lines.append(f"## Referenced Messages (from {dates_str})")
            lines.append("")
            for ref_msg in cross_date_refs.values():
                ref_formatted = self._format_message(ref_msg, inline_images)
                if ref_formatted:
                    lines.append(ref_formatted)
                    lines.append("")
            lines.append("---")
            lines.append("")

        # 文档头部
        lines.append(f"# Chat Report: {group_info.get('name', 'Unknown')}")
        lines.append("")
        lines.append(f"**Time Range**: {start.strftime(TIME_FMT_FULL)} ~ {end.strftime(TIME_FMT_FULL)}")
        lines.append(f"**Total Messages**: {len(messages)}")
        lines.append("")

        # 统计信息（扩展功能，可选）
        if include_stats:
            stats = self._calculate_stats(messages)
            lines.append("## Statistics")
            lines.append("")
            lines.append(f"- 发送者数量: {stats.get('sender_count', 0)}")
            lines.append(f"- 图片消息: {stats.get('image_count', 0)}")
            lines.append(f"- 链接卡片: {stats.get('link_count', 0)}")
            lines.append("")

        # 消息列表
        lines.append("## Messages")
        lines.append("")

        for msg in messages:
            formatted = self._format_message(msg, inline_images)
            if formatted:
                lines.append(formatted)
                lines.append("")

        # 写入文件
        content = "\n".join(lines)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 文档已保存: {output_path}")

        # Export data-end date for memory file naming
        if messages:
            last_ts = messages[-1].get("timestamp", 0)
            if isinstance(last_ts, (int, float)) and last_ts > 0:
                print(f"DATA_END_DATE={datetime.fromtimestamp(last_ts).strftime(DATE_FMT_COMPACT)}")

        # describe 模式额外输出图片路径列表
        if not inline_images:
            image_paths = []
            for msg in messages:
                media_path = msg.get("media_local_path", "")
                media_type = msg.get("media_type", "")
                if media_path and media_type in ("image", "emoji"):
                    if not media_path.startswith("file:///"):
                        media_path = f"file:///{media_path}"
                    image_paths.append(media_path)
            if image_paths:
                paths_file = output_path.with_name(output_path.stem + '_images.txt')
                with open(paths_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(image_paths))
                print(f"   图片路径列表: {paths_file} ({len(image_paths)} 张)")

        return content

    def _format_message(self, msg: Dict[str, Any], inline_images: bool = False) -> str:
        """格式化单条消息

        三种特殊类型独立处理：
        1. 引用消息（<refermsg>）→ 💬 引用格式
        2. 文件分享（<appattach>/<fileupload>）→ 📎 [文件] 格式
        3. 链接卡片（其他 <appmsg>）→ 🔗 链接卡片格式

        Args:
            msg: 消息字典
            inline_images: 是否嵌入图片路径

        Returns:
            格式化后的消息文本
        """
        # 时间戳
        ts = msg.get("timestamp", 0)
        if isinstance(ts, (int, float)):
            time_str = datetime.fromtimestamp(ts).strftime(TIME_FMT_FULL)
        else:
            time_str = str(ts)

        # 发送者名称（使用群成员映射获取显示名）
        sender_wxid = msg.get("sender") or ""
        sender = self._get_sender_display_name(sender_wxid)
        if len(sender) > 20:
            sender = sender[:17] + "..."

        # 消息头部：统一使用 serverId，无 serverId 时回退到 localId
        msg_id = msg.get("serverId") or msg.get("server_id") or msg.get("localId") or msg.get("id", "")
        lines = [f"### {time_str} | {sender} | svrid:{msg_id}"]

        # 消息内容处理
        msg_type = msg.get("type", 0)
        content = msg.get("content", "")
        raw_content = msg.get("raw_content", "")
        media_path = msg.get("media_local_path")
        media_type = msg.get("media_type")

        # ========== 特殊类型处理（按优先级顺序）==========

        # 1. 引用消息（最高优先级）
        if self.parse_link_cards and '<refermsg>' in raw_content:
            quote_info = self.client.parse_quote(raw_content)
            if quote_info:
                # 1a. 构建引用行
                lines.append(self._build_quote_ref(quote_info))

                # 空行分隔引用行和正文（防止 markdown 将正文吸入引用块）
                lines.append("")

                # 1b. 检测回复中的文件附件
                has_file = False
                if '<fileupload>' in raw_content:
                    has_file = True
                elif '<appattach>' in raw_content:
                    has_file = bool(re.search(r'<attachid>[^<]+</attachid>', raw_content) or
                                    re.search(r'<filename>[^<]+</filename>', raw_content))
                if has_file:
                    file_info = self.client.parse_file(raw_content)
                    if file_info:
                        lines.append(self._format_file(file_info))
                        return "\n".join(lines)

                # 1c. 检测回复中的图片/表情
                if media_path and media_type == "image":
                    if inline_images:
                        if not media_path.startswith("file:///"):
                            media_path = f"file:///{media_path}"
                        lines.append(media_path)
                    else:
                        lines.append(f"[图片|{media_path}]")
                    return "\n".join(lines)
                if media_path and media_type == "emoji":
                    lines.append(f"[表情|{media_path}]")
                    return "\n".join(lines)

                # 1d. 纯文本回复 — 多源提取回复文本
                reply_text = ""
                quoted_text = quote_info.get("content") or ""

                # 源1: 从 raw_content 提取 <title>
                title_match = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', raw_content)
                if title_match:
                    candidate = html.unescape(title_match.group(1).strip())
                    if candidate and candidate != quoted_text:
                        reply_text = candidate

                # 源2: fallback 到 content 字段
                if not reply_text:
                    fallback = (content or "").strip()
                    if fallback and fallback != quoted_text:
                        # 处理合并内容：content 可能以 quoted_text 开头
                        if quoted_text and fallback.startswith(quoted_text):
                            remainder = fallback[len(quoted_text):].strip()
                            if remainder:
                                reply_text = remainder
                        else:
                            reply_text = fallback

                if reply_text:
                    lines.append(reply_text)
                return "\n".join(lines)

        # 2. 链接卡片（在文件之前判断，避免链接被误判为文件）
        if self.parse_link_cards and '<appmsg' in raw_content:
            link_info = self.client.parse_link(raw_content)
            if link_info:
                formatted = self._format_link(link_info)
                lines.append(formatted)
                return "\n".join(lines)

        # 3. 文件分享（最后判断）
        # 真正的文件有 <fileupload> 或 <appattach> 包含 <attachid> 或 <filename>
        is_file = False
        if '<fileupload>' in raw_content:
            is_file = True
        elif '<appattach>' in raw_content:
            # 检查是否为真正的文件（有 filename/attachid），而不是链接缩略图
            has_file_id = bool(re.search(r'<attachid>[^<]+</attachid>', raw_content))
            has_file_name = bool(re.search(r'<filename>[^<]+</filename>', raw_content))
            is_file = has_file_id or has_file_name

        if self.parse_link_cards and is_file:
            file_info = self.client.parse_file(raw_content)
            if file_info:
                formatted = self._format_file(file_info)
                lines.append(formatted)
                return "\n".join(lines)

        # ========== 普通消息处理 ==========

        # 处理图片
        if inline_images and media_path and media_type == "image":
            # 检查 file:// 前缀
            if not media_path.startswith("file:///"):
                media_path = f"file:///{media_path}"
            lines.append(media_path)
        elif msg_type in [3, 47] or (msg_type == 1 and not content.strip()):
            # 图片/表情
            if media_path:
                tag = "表情" if msg_type == 47 else "图片"
                lines.append(f"[{tag}|{media_path}]")
            elif msg.get("media_url"):
                print(f"警告: 图片未能下载到本地: {msg.get('media_url', '')[:80]}")
                lines.append(f"[图片|{msg.get('media_url')}]")
            else:
                lines.append("[图片]" if msg_type == 3 else "[表情]")
        elif content:
            # 普通文本
            lines.append(content)
        else:
            # 其他类型
            type_name = self.MSG_TYPE_NAMES.get(msg_type, f"类型{msg_type}")
            lines.append(f"[{type_name}]")

        return "\n".join(lines)

    def _fetch_cross_date_refs(
        self,
        messages: List[Dict[str, Any]],
        start: datetime,
        end: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        """预扫描跨日引用，获取被引用消息

        Args:
            messages: 当天消息列表
            start: 查询开始时间
            end: 查询结束时间

        Returns:
            {ref_id: message_dict} 跨日引用消息映射
        """
        cross_date_refs: Dict[str, Dict[str, Any]] = {}
        seen_create_times: set = set()

        for msg in messages:
            raw_content = msg.get("raw_content") or msg.get("rawContent") or ""
            if '<refermsg>' not in raw_content:
                continue

            quote_info = self.client.parse_quote(raw_content)
            if not quote_info:
                continue

            svr_id = quote_info.get("server_msg_id", "")
            # 如果在当天缓存中（通过 serverId 或 create_time 匹配），不是跨日引用
            if svr_id and str(svr_id) in self._messages_by_server_id:
                continue

            create_time = quote_info.get("create_time")
            if not create_time:
                continue

            # serverId 精度丢失时，通过 create_time 在缓存中查找
            found_in_cache = False
            for cached_msg in self._messages_by_server_id.values():
                cached_ts = cached_msg.get("timestamp", 0)
                if isinstance(cached_ts, (int, float)) and abs(cached_ts - create_time) < 5:
                    found_in_cache = True
                    break
            if found_in_cache:
                continue

            # 避免重复获取同一时间戳的消息
            if create_time in seen_create_times:
                continue
            seen_create_times.add(create_time)

            # 判断是否为跨日引用
            ref_dt = datetime.fromtimestamp(create_time)
            day_start = datetime.combine(ref_dt.date(), datetime.min.time())
            day_end = datetime.combine(ref_dt.date(), datetime.max.time().replace(microsecond=0))

            # 如果引用的消息日期就在当前查询范围内，不是跨日
            if day_start >= start and day_end <= end:
                continue

            # 获取跨日消息
            try:
                ref_messages = self.get_messages(start=day_start, end=day_end, export_media=False)
                # 通过 create_time 精确匹配
                for ref_msg in ref_messages:
                    ref_ts = ref_msg.get("timestamp", 0)
                    if isinstance(ref_ts, (int, float)) and abs(ref_ts - create_time) < 5:
                        ref_id = f"REF-{len(cross_date_refs) + 1}"
                        cross_date_refs[ref_id] = ref_msg
                        # 同时加入缓存，这样 _build_quote_ref 能找到它
                        ref_server_id = str(ref_msg.get("serverId") or ref_msg.get("server_id") or "")
                        if ref_server_id:
                            self._messages_by_server_id[ref_server_id] = ref_msg
                        # 别名缓存：用 XML 中的原始 svrid 映射到该消息
                        if svr_id and str(svr_id) != ref_server_id:
                            self._messages_by_server_id[str(svr_id)] = ref_msg
                        break
            except Exception as e:
                print(f"  ⚠️ 获取跨日引用失败 (create_time={create_time}): {e}")

        if cross_date_refs:
            print(f"   发现 {len(cross_date_refs)} 条跨日引用消息")

        return cross_date_refs

    def _build_quote_ref(self, quote_info: Dict[str, Any]) -> str:
        """构建引用行（显示被引用者+20字预览+svrid）

        输出格式: > 💬 引用 张三: 前20字预览... (svrid:9210117274123674000)
        """
        svr_id = quote_info.get("server_msg_id", "")
        quoted_sender = quote_info.get("display_name", "")
        quoted_content = quote_info.get("content", "")
        resolved_svr_id = ""  # 最终显示给用户的 svrid（取自 API）

        need_content = not quoted_content
        need_sender = not quoted_sender

        # 始终查缓存：即使 XML 已有内容/发送者，也需要获取 API 的 serverId
        ref_msg = None
        if svr_id:
            ref_msg = self._messages_by_server_id.get(str(svr_id))

        # 策略2: create_time 匹配（兜底，解决 serverId 精度丢失）
        if ref_msg is None:
            create_time = quote_info.get("create_time")
            if create_time:
                for cached_msg in self._messages_by_server_id.values():
                    cached_ts = cached_msg.get("timestamp", 0)
                    if isinstance(cached_ts, (int, float)) and abs(cached_ts - create_time) < 5:
                        ref_msg = cached_msg
                        # 别名缓存：下次用 XML svrid 直接命中
                        if svr_id:
                            self._messages_by_server_id[str(svr_id)] = cached_msg
                        break

        if ref_msg:
            if need_sender:
                ref_sender_wxid = ref_msg.get("sender") or ref_msg.get("senderName", "")
                if ref_sender_wxid:
                    quoted_sender = self._get_sender_display_name(ref_sender_wxid)
            if need_content:
                ref_type = ref_msg.get("type", 0)
                ref_media_type = ref_msg.get("media_type", "")
                ref_content = ref_msg.get("content", "")
                if ref_media_type == "image" or ref_type == 3:
                    quoted_content = "[图片]"
                elif ref_media_type == "emoji" or ref_type == 47:
                    quoted_content = "[表情]"
                elif ref_content:
                    quoted_content = ref_content
            # 取 API 的 serverId 用于显示（确保与消息头一致）
            resolved_svr_id = str(ref_msg.get("serverId") or ref_msg.get("server_id") or "")

        # 构建引用行
        ref = "> 💬 引用"
        if quoted_sender:
            ref += f" {quoted_sender}"
        if quoted_content:
            flat = quoted_content.replace("\n", " ").replace("\r", "")
            preview = flat if len(flat) <= 20 else flat[:17] + "..."
            ref += f": {preview}"
        elif not ref_msg:
            ref += " [引用消息未找到]"

        # 始终显示 svrid
        display_id = resolved_svr_id or (str(svr_id) if svr_id else "")
        if display_id:
            ref += f" (svrid:{display_id})"

        return ref

    def _format_file(self, file_info: Dict[str, Any]) -> str:
        """格式化文件分享

        输出格式示例:
        📎 [文件] 文件名.pdf (2.5 MB)
        """
        title = file_info.get("title", "")
        file_size = file_info.get("file_size")

        # 格式化文件大小
        size_str = ""
        if file_size:
            if file_size >= 1024 * 1024 * 1024:
                size_str = f" ({file_size / (1024 * 1024 * 1024):.2f} GB)"
            elif file_size >= 1024 * 1024:
                size_str = f" ({file_size / (1024 * 1024):.2f} MB)"
            elif file_size >= 1024:
                size_str = f" ({file_size / 1024:.2f} KB)"
            else:
                size_str = f" ({file_size} B)"

        if title:
            return f"📎 [文件] {title}{size_str}"
        else:
            return f"📎 [文件]{size_str}"

    def _format_link(self, link_info: Dict[str, Any]) -> str:
        """格式化链接卡片

        输出格式示例:
        📰 [链接卡片] 文章标题
        🔗 URL: https://mp.weixin.qq.com/s/...
        📰 来源: 公众号名称
        """
        lines = []
        link_type = link_info.get("type", "unknown")

        # 类型图标映射
        type_icons = {
            "wechat_article": "📰",
            "link": "🔗",
            "miniapp": "📱",
            "unknown": "📎"
        }
        icon = type_icons.get(link_type, "📎")

        # 标题行
        title = link_info.get("title", "")
        if title:
            lines.append(f"{icon} [链接卡片] {title}")
        else:
            lines.append(f"{icon} [链接卡片]")

        # URL
        url = link_info.get("url")
        if url:
            lines.append(f"🔗 URL: {url}")

        # 来源
        source = link_info.get("source")
        if source:
            lines.append(f"📰 来源: {source}")

        # 描述（如果与标题不同且不为空）
        description = link_info.get("description")
        if description and description != title and len(description) > 5:
            desc = description if len(description) < 100 else description[:97] + "..."
            lines.append(f"📝 {desc}")

        return "\n".join(lines)

    def _calculate_stats(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算消息统计信息（扩展功能）

        Args:
            messages: 消息列表

        Returns:
            统计信息字典
        """
        stats = {
            "total": len(messages),
            "sender_count": len(set(m.get("sender") for m in messages if m.get("sender"))),
            "image_count": 0,
            "link_count": 0,
            "text_count": 0,
        }

        for msg in messages:
            msg_type = msg.get("type", 0)
            raw_content = msg.get("raw_content", "")

            if msg_type == 3 or msg.get("media_type") == "image":
                stats["image_count"] += 1
            elif '<appmsg>' in raw_content or msg.get("link_card"):
                stats["link_count"] += 1
            elif msg_type == 1:
                stats["text_count"] += 1

        return stats


def generate_chat_context(
    config: Dict[str, Any],
    date: datetime,
    output_dir: str,
    inline_images: bool = False,
    sender_filter: Optional[str] = None,
    include_stats: bool = False
) -> str:
    """便捷函数：生成指定日期的聊天上下文文档

    Args:
        config: 配置字典
        date: 日期
        output_dir: 输出目录
        inline_images: 是否嵌入图片（默认 False，使用 describe 模式）
        sender_filter: 发送者过滤
        include_stats: 是否包含统计信息

    Returns:
        生成的文件路径
    """
    # 创建客户端
    weflow_config = config.get("weflow", {})
    client = WeFlowClient(
        base_url=weflow_config.get("baseUrl", "http://127.0.0.1:5031"),
        token=weflow_config.get("token")
    )

    # 创建生成器
    generator = ChatContextGenerator(
        client=client,
        chatroom_id=weflow_config["chatroomId"],
        config=config
    )

    # 计算时间范围（当天 00:00:00 ~ 23:59:59）
    start = datetime.combine(date, datetime.min.time())
    end = datetime.combine(date, datetime.max.time().replace(microsecond=0))

    # 生成文件名
    date_str = date.strftime(DATE_FMT_COMPACT)
    output_path = Path(output_dir) / f"chat_context_{date_str}.md"

    # 生成文档
    generator.generate(
        start=start,
        end=end,
        output_path=str(output_path),
        inline_images=inline_images,
        sender_filter=sender_filter,
        include_stats=include_stats
    )

    return str(output_path)


if __name__ == "__main__":
    import argparse
    from datetime import date as dt_date

    parser = argparse.ArgumentParser(description='生成聊天上下文文档')
    parser.add_argument('--date', '-d', help='目标日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--start', help='开始时间 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--end', help='结束时间 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--output', '-o', help='输出目录，默认使用配置中的 tempDir')
    parser.add_argument('--direct', action='store_true',
                       help='使用 direct 模式（嵌入图片为 file:// 路径，不可靠）')
    parser.add_argument('--sender', help='按发送者名称过滤（模糊匹配）')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')

    args = parser.parse_args()

    # 通过 config_loader 加载配置（优先级：环境变量 > config.local.json > config.json）
    config = _load_config()

    # 解析时间范围
    if args.start and args.end:
        start = datetime.strptime(args.start, TIME_FMT_RANGE)
        end = datetime.strptime(args.end, TIME_FMT_RANGE)
        target_date = start.date()
    elif args.date:
        target_date = datetime.strptime(args.date, DATE_FMT_CLI).date()
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time().replace(microsecond=0))
    else:
        target_date = dt_date.today()
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time().replace(microsecond=0))

    # 确定输出目录和图片模式
    output_dir = args.output or config.get('tempDir', 'temp')
    inline_images = args.direct

    # 检查 WeFlow 配置（二次校验，提供友好错误提示）
    weflow_config = config.get('weflow', {})
    if not weflow_config.get('chatroomId'):
        print("❌ 配置错误: 未设置 weflow.chatroomId")
        sys.exit(1)

    # 创建客户端和生成器
    client = WeFlowClient(
        base_url=weflow_config.get('baseUrl', 'http://127.0.0.1:5031'),
        token=weflow_config.get('token')
    )

    generator = ChatContextGenerator(
        client=client,
        chatroom_id=weflow_config['chatroomId'],
        config=config
    )

    # 检查连接
    if not generator.health_check():
        print("❌ WeFlow API 连接失败")
        print("   请确认：")
        print("   1. WeFlow 应用已启动")
        print("   2. HTTP API 服务已启用（端口 5031）")
        sys.exit(1)

    print("✅ WeFlow API 连接正常\n")

    # 生成文件名
    date_str = target_date.strftime(DATE_FMT_COMPACT)
    output_path = Path(output_dir) / f"chat_context_{date_str}.md"

    try:
        # 生成文档
        generator.generate(
            start=start,
            end=end,
            output_path=str(output_path),
            inline_images=inline_images,
            sender_filter=args.sender,
            include_stats=args.stats
        )
        print(f"\n✅ 生成成功: {output_path}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
