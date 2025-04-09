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


def decode_utf8_bytestring(s):
    try:
        # 找到所有的转义字节字符串
        matches = re.findall(r'(\\x[0-9a-fA-F]{2})+', s)
        for m in matches:
            # 转换字节串为可读字符串
            byte_seq = bytes(m, "utf-8").decode("unicode_escape").encode("latin1")
            decoded = codecs.decode(byte_seq, "utf-8")
            s = s.replace(m, decoded)
        return s
    except Exception:
        return s  # 如果失败就返回原始内容


def decode_log_file(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            decoded_line = decode_utf8_bytestring(line)
            print(decoded_line, end='')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Decode Apache UTF-8 escaped log lines.")
    parser.add_argument("log_path", nargs="?", default="/var/log/apache2/error.log",
                        help="Path to the Apache error log file (default: /var/log/apache2/error.log)")

    args = parser.parse_args()
    decode_log_file(args.log_path)
