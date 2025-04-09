"""
#!/usr/bin/env python
# -*- coding:utf-8 -*-
@Project : CollectIp
@File : decode_apache_log.py
@Author : 帅张张
@Time : 2025/4/9 9:17

"""
import re
import codecs
import argparse

def decode_utf8_hex_sequences(line: str) -> str:
    def decode_match(match):
        hex_str = match.group(0)  # 例如：\xe4\xbd\xa0\xe5\xa5\xbd
        try:
            # 将字符串中的 \x 转为字节串
            raw_bytes = bytes(hex_str, "utf-8").decode("unicode_escape").encode("latin1")
            return raw_bytes.decode("utf-8")
        except Exception:
            return hex_str  # 解码失败就返回原样

    # 匹配连续的 UTF-8 字节转义序列
    return re.sub(r'(\\x[0-9a-fA-F]{2}){3,}', decode_match, line)

def decode_log_file(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            decoded = decode_utf8_hex_sequences(line)
            print(decoded, end='')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode Apache error log lines with UTF-8 escape sequences.")
    parser.add_argument("log_path", nargs="?", default="/var/log/apache2/error.log",
                        help="Path to the Apache error log file (default: /var/log/apache2/error.log)")
    args = parser.parse_args()
    decode_log_file(args.log_path)
