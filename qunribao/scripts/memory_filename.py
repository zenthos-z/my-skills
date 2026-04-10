#!/usr/bin/env python3
"""生成记忆文件名: topic_tracker_YYYYMMDD_VVVVVV.md

YYYYMMDD = 聊天数据截止日期（最后一条消息的日期）
VVVVVV = 当天版本序号（000001, 000002, ...），自动递增
"""
import argparse
import re
import sys
from pathlib import Path

# 支持从 scripts/ 目录直接运行
sys.path.insert(0, str(Path(__file__).parent))
from config_loader import get_config


def main():
    parser = argparse.ArgumentParser(description='生成记忆文件名')
    parser.add_argument('--date', required=True, help='数据截止日期 YYYYMMDD')
    parser.add_argument('--memory-dir', help='覆盖配置中的 memoryDir')
    args = parser.parse_args()

    config = get_config()
    memory_dir = Path(args.memory_dir or config['memoryDir'])

    # 查找当天已有文件，计算下一个序号
    pattern = re.compile(rf'^topic_tracker_{re.escape(args.date)}_(\d{{6}})\.md$')
    max_seq = 0
    if memory_dir.exists():
        for f in memory_dir.iterdir():
            m = pattern.match(f.name)
            if m:
                seq = int(m.group(1))
                if seq > max_seq:
                    max_seq = seq

    filename = f"topic_tracker_{args.date}_{max_seq + 1:06d}.md"
    print(filename)


if __name__ == '__main__':
    main()
