#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天上下文文档生成器
统一生成 temp 文档，支持链接卡片增强解析
"""

import sys
import re
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
        inline_images: bool = True,
        include_stats: bool = False,
        sender_filter: Optional[str] = None
    ) -> str:
        """生成聊天上下文文档

        Args:
            start: 开始时间
            end: 结束时间
            output_path: 输出文件路径
            inline_images: 是否将图片嵌入为 file:// 路径
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

        # 按时间戳升序排序（从早到晚）
        messages.sort(key=lambda m: m.get("timestamp", 0))

        # 建立 server_id -> local_id 映射（用于引用消息查找）
        self._server_to_local_id: Dict[str, str] = {}
        for m in messages:
            server_id = m.get("serverId") or m.get("server_id")
            local_id = m.get("localId") or m.get("id")
            if server_id and local_id:
                self._server_to_local_id[str(server_id)] = str(local_id)

        # 构建文档
        lines = []

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
                if media_path and media_type == "image":
                    if not media_path.startswith("file:///"):
                        media_path = f"file:///{media_path}"
                    image_paths.append(media_path)
            if image_paths:
                paths_file = output_path.with_name(output_path.stem + '_images.txt')
                with open(paths_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(image_paths))
                print(f"   图片路径列表: {paths_file} ({len(image_paths)} 张)")

        return content

    def _format_message(self, msg: Dict[str, Any], inline_images: bool = True) -> str:
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

        # 消息头部：添加 local ID
        local_id = msg.get("localId") or msg.get("id", "")
        lines = [f"### {time_str} | {sender} | ID:{local_id}"]

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
                formatted = self._format_quote(quote_info, content)
                lines.append(formatted)
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
                lines.append(f"[图片|{media_path}]")
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

    def _format_quote(self, quote_info: Dict[str, Any], current_content: str) -> str:
        """格式化引用消息

        输出格式示例:
        > 💬 引用 ID:1234
        当前消息内容
        """
        lines = []

        # 获取被引用消息的 server ID，并查找对应的 local ID
        svr_id = quote_info.get("server_msg_id", "")
        if svr_id:
            local_id = self._server_to_local_id.get(str(svr_id), "unknown")
        else:
            local_id = "unknown"

        # 引用信息放在 markdown 引用块中
        lines.append(f"> 💬 引用 ID:{local_id}")

        # 当前消息内容（正常文本，不在引用块中）
        if current_content and current_content.strip():
            lines.append(current_content.strip())

        return "\n".join(lines)

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
    inline_images: bool = True,
    sender_filter: Optional[str] = None,
    include_stats: bool = False
) -> str:
    """便捷函数：生成指定日期的聊天上下文文档

    Args:
        config: 配置字典
        date: 日期
        output_dir: 输出目录
        inline_images: 是否嵌入图片
        sender_filter: 发送者过滤
        include_stats: 是否包含统计信息

    Returns:
        生成的文件路径
    """
    # 创建客户端
    weflow_config = config.get("weflow", {})
    client = WeFlowClient(
        base_url=weflow_config.get("baseUrl", "http://127.0.0.1:5031")
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
    parser.add_argument('--describe', action='store_true',
                       help='使用 describe 模式（不嵌入图片）')
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
    inline_images = not args.describe

    # 检查 WeFlow 配置（二次校验，提供友好错误提示）
    weflow_config = config.get('weflow', {})
    if not weflow_config.get('chatroomId'):
        print("❌ 配置错误: 未设置 weflow.chatroomId")
        sys.exit(1)

    # 创建客户端和生成器
    client = WeFlowClient(
        base_url=weflow_config.get('baseUrl', 'http://127.0.0.1:5031')
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
